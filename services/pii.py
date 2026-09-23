"""Local PII detection and reversible pseudonymization.

Everything here runs in-process: Microsoft Presidio (spaCy NER + regex
recognizers) finds entities, and each distinct value is swapped for a typed
placeholder such as <PERSON_1>. The value <-> placeholder map lives only in a
request-scoped ContextVar. It is never logged, sent, or cached.
"""

import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider

from core.config import get_settings
from core.enums import PrivacyAction, PrivacyMode

SPACY_MODEL = "en_core_web_md"

# Presidio entity type -> placeholder label. ORG and LOCATION are deliberately
# absent: nearly every answer names a company or city, and hiding them would
# destroy utility. See docs/DECISIONS.md.
LABELS = {
    "PERSON": "PERSON",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "CREDIT_CARD": "CARD",
    "IN_PAN": "PAN",
    "IN_AADHAAR": "AADHAAR",
}

# Appended to the system prompt of every grade / rewrite / generate call.
PLACEHOLDER_INSTRUCTION = (
    "Tokens like <PERSON_1>, <EMAIL_1> are real values that were hidden for privacy. "
    "Treat them as the actual values. Copy them exactly, character for character, when "
    "they are part of the answer. Never invent new ones, never say a value is missing "
    "because it is a placeholder."
)

# Tolerant on purpose: models sometimes write <PHONE 1>, <phone_1> or [PHONE_1].
# All of those normalize to the canonical <PHONE_1> before lookup.
_PLACEHOLDER_RE = re.compile(
    r"[<\[]\s*(" + "|".join(LABELS.values()) + r")[\s_\-]*(\d*)\s*[>\]]",
    re.IGNORECASE,
)


def _custom_recognizers() -> list[PatternRecognizer]:
    return [
        # Presidio's own email recognizer rejects unknown TLDs (".example", internal
        # domains), which would let those addresses through. A plain regex does not.
        PatternRecognizer(
            supported_entity="EMAIL_ADDRESS",
            name="docmind_email",
            patterns=[Pattern("email", r"\b[\w.%+-]+@[\w-]+(\.[\w-]+)+\b", 0.9)],
        ),
        # PAN: 5 letters, 4 digits, 1 letter (e.g. ABCPK1234Z).
        PatternRecognizer(
            supported_entity="IN_PAN",
            name="docmind_in_pan",
            patterns=[Pattern("pan", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", 0.85)],
        ),
        # Aadhaar-like: exactly 12 digits, optionally grouped 4-4-4. The look-arounds
        # stop it matching the middle of a longer number such as a 16-digit card.
        PatternRecognizer(
            supported_entity="IN_AADHAAR",
            name="docmind_in_aadhaar",
            patterns=[
                Pattern(
                    "aadhaar",
                    r"(?<!\d)(?<!\d[ -])\d{4}[ -]?\d{4}[ -]?\d{4}(?![ -]?\d)",
                    0.6,
                )
            ],
        ),
        # +91 mobile numbers, as a deterministic backstop to Presidio's phonenumbers check.
        PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            name="docmind_in_phone",
            patterns=[Pattern("in_mobile", r"\+91[ -]?[6-9]\d{4}[ -]?\d{5}\b", 0.85)],
        ),
    ]


@lru_cache
def get_analyzer() -> AnalyzerEngine:
    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": SPACY_MODEL}],
        }
    )
    analyzer = AnalyzerEngine(nlp_engine=provider.create_engine())
    for recognizer in _custom_recognizers():
        analyzer.registry.add_recognizer(recognizer)
    return analyzer


def detect(text: str) -> list[tuple[int, int, str]]:
    """Return (start, end, entity_type) spans. Raises if the detector fails."""
    spans = []
    for result in get_analyzer().analyze(text=text, language="en", entities=list(LABELS)):
        start, end = result.start, result.end
        if result.entity_type == "PERSON":
            # spaCy spans can run across a line break ("Maya Chen\nPersonal")...
            newline = text.find("\n", start, end)
            end = newline if newline != -1 else end
            # ...or include the possessive: "Ananya Kulkarni's" -> "Ananya Kulkarni".
            if text[start:end].endswith(("'s", "’s")):
                end -= 2
            # A name starts with a capital letter; this drops tags like "bin".
            if not text[start:end][:1].isupper():
                continue
        spans.append((start, end, result.entity_type))
    return spans


@dataclass
class EgressRecord:
    """What left the machine for one request. Holds placeholders, never raw values."""

    mode: str
    action: str | None = None  # None when privacy mode is off
    consent_types: list[str] = field(default_factory=list)  # set on REQUIRE_CONSENT
    sent_in_clear: list[str] = field(default_factory=list)  # types released by consent
    entities: dict[str, int] = field(default_factory=dict)  # type -> distinct values hidden
    calls: list[dict] = field(default_factory=list)  # {"label", "messages"} as sent
    restored: int = 0
    restore_failures: list[str] = field(default_factory=list)  # unknown/malformed placeholders


@dataclass
class PrivacyContext:
    mode: PrivacyMode
    record: EgressRecord
    clear_types: set[str] = field(default_factory=set)
    by_value: dict[str, tuple[str, str]] = field(default_factory=dict)  # value -> (placeholder, type)
    by_placeholder: dict[str, str] = field(default_factory=dict)  # placeholder -> value
    counters: dict[str, int] = field(default_factory=dict)  # label -> last number used

    def placeholder_for(self, value: str, entity_type: str) -> str:
        if value in self.by_value:
            return self.by_value[value][0]
        label = LABELS[entity_type]
        self.counters[label] = self.counters.get(label, 0) + 1
        placeholder = f"<{label}_{self.counters[label]}>"
        self.by_value[value] = (placeholder, entity_type)
        self.by_placeholder[placeholder] = value
        self.record.entities[entity_type] = self.record.entities.get(entity_type, 0) + 1
        return placeholder


# Same pattern as core/usage.py: one context per request, so concurrent requests
# on the same event loop never see each other's values.
_context: ContextVar[PrivacyContext | None] = ContextVar("docmind_privacy", default=None)


def start_request(mode: PrivacyMode | None = None, clear_types: set[str] | None = None) -> PrivacyContext:
    mode = mode or get_settings().privacy_mode
    record = EgressRecord(
        mode=mode.value, action=PrivacyAction.ALLOW if mode == PrivacyMode.MINIMIZE else None
    )
    ctx = PrivacyContext(mode=mode, record=record, clear_types=clear_types or set())
    _context.set(ctx)
    return ctx


def current() -> PrivacyContext:
    ctx = _context.get()
    # Code that calls the LLM outside a request (the eval judge, smoke tests) still
    # goes through the gate. It just gets a fresh context.
    return ctx if ctx is not None else start_request()


def _known_value_spans(text: str, ctx: PrivacyContext) -> list[tuple[int, int, str]]:
    """Find values already seen in this request, even where NER misses them now.

    This keeps "same value -> same placeholder" across the query and every chunk.
    For names it also matches each part ("Ananya" of "Ananya Kulkarni").
    """
    spans = []
    for value, (_, entity_type) in list(ctx.by_value.items()):
        needles = [value]
        if entity_type == "PERSON":
            needles += [part for part in value.split() if len(part) >= 3]
        for needle in needles:
            for match in re.finditer(rf"(?<!\w){re.escape(needle)}(?!\w)", text):
                spans.append((match.start(), match.end(), entity_type))
    return spans


def _drop_overlaps(spans: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    # Longest span wins, so a 16-digit card beats a 12-digit sub-match inside it.
    kept: list[tuple[int, int, str]] = []
    for start, end, entity_type in sorted(spans, key=lambda s: (s[0] - s[1], s[0])):
        if all(end <= k_start or start >= k_end for k_start, k_end, _ in kept):
            kept.append((start, end, entity_type))
    return kept


def pseudonymize(text: str) -> str:
    ctx = current()
    if ctx.mode == PrivacyMode.OFF:
        return text

    detected = [s for s in detect(text) if s[1] > s[0]]
    for start, end, entity_type in detected:
        if entity_type not in ctx.clear_types:
            ctx.placeholder_for(text[start:end], entity_type)

    spans = [s for s in detected + _known_value_spans(text, ctx) if s[2] not in ctx.clear_types]
    for start, end, entity_type in sorted(_drop_overlaps(spans), reverse=True):
        value = text[start:end]
        placeholder = ctx.by_value[value][0] if value in ctx.by_value else _name_part_placeholder(value, ctx)
        text = text[:start] + placeholder + text[end:]

    if ctx.by_value and ctx.record.action == PrivacyAction.ALLOW:
        ctx.record.action = PrivacyAction.MINIMIZE
    return text


def _name_part_placeholder(part: str, ctx: PrivacyContext) -> str:
    # "Ananya" alone maps to the placeholder of the full name it came from.
    for value, (placeholder, entity_type) in ctx.by_value.items():
        if entity_type == "PERSON" and part in value.split():
            return placeholder
    return ctx.placeholder_for(part, "PERSON")


def record_call(label: str, messages: list[dict]) -> None:
    ctx = current()
    if ctx.mode == PrivacyMode.OFF:
        # Raw text went out; the record must not copy raw values, so it notes that instead.
        contents = ["[privacy off: raw text sent, not recorded]"]
    else:
        contents = [_mask_consented(m["content"], ctx) for m in messages]
    ctx.record.calls.append({"label": label or "-", "messages": contents})


def _mask_consented(text: str, ctx: PrivacyContext) -> str:
    # Values released by consent really did leave, but the record never stores raw
    # values, so it names them instead.
    if not ctx.clear_types:
        return text
    spans = [s for s in detect(text) if s[2] in ctx.clear_types]
    for start, end, entity_type in sorted(_drop_overlaps(spans), reverse=True):
        text = text[:start] + f"[{LABELS[entity_type]} sent in clear]" + text[end:]
    return text


def restore(text: str) -> str:
    """Swap placeholders back to real values, locally. Unknown ones stay as-is and are flagged."""
    ctx = current()

    def swap(match: re.Match) -> str:
        canonical = f"<{match.group(1).upper()}_{match.group(2)}>"
        value = ctx.by_placeholder.get(canonical)
        if value is None:
            ctx.record.restore_failures.append(match.group(0))
            return match.group(0)
        ctx.record.restored += 1
        return value

    return _PLACEHOLDER_RE.sub(swap, text)


class StreamRestorer:
    """Restore placeholders in streamed text, where one can be split: "<PER" + "SON_1>".

    Text from the last unclosed '<' or '[' onward is held back until it either
    closes or grows too long to be a placeholder, then released.
    """

    MAX_PLACEHOLDER_LEN = 24

    def __init__(self) -> None:
        self.buffer = ""

    def feed(self, piece: str) -> str:
        self.buffer += piece
        cut = self._safe_cut()
        ready, self.buffer = self.buffer[:cut], self.buffer[cut:]
        return restore(ready) if ready else ""

    def flush(self) -> str:
        ready, self.buffer = self.buffer, ""
        return restore(ready) if ready else ""

    def _safe_cut(self) -> int:
        opening = max(self.buffer.rfind("<"), self.buffer.rfind("["))
        if opening == -1:
            return len(self.buffer)
        tail = self.buffer[opening:]
        if ">" in tail or "]" in tail or len(tail) > self.MAX_PLACEHOLDER_LEN:
            return len(self.buffer)
        return opening
