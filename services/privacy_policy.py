"""Decide what a request may send to Groq. Deterministic, local, no model calls.

ALLOW / MINIMIZE are settled at the gate (did anything get pseudonymized?).
This module handles the two up-front outcomes:

- REQUIRE_CONSENT: the question needs the model to reason over the *content* of
  a sensitive value ("is her email a gmail address?"). A placeholder can't
  answer that, so the user must opt in with `allow_sensitive: true`. Consent then
  releases only the entity types the question is about.
- BLOCK: the detector itself failed. Nothing may be sent (fail closed).

Lookups ("what is her email?") need no consent: the model copies <EMAIL_1>
into the answer and the real value is restored locally.
"""

import re
from dataclasses import dataclass, field

from core.enums import PrivacyAction, PrivacyMode
from services import pii

# The model would have to look *inside* a value, not just copy it.
_CONTENT_RE = re.compile(
    r"\b(valid|invalid|gmail|domain|provider|starts? with|begins? with|ends? with|"
    r"contains?|digits?|letters?|characters?|length|longer|shorter|prefix|suffix|"
    r"format|compare|same|identical|match(es)?|equal|greater|less|sum|add|"
    r"country code|area code|real|fake|belongs?)\b",
    re.IGNORECASE,
)

# Words that point at a sensitive type even when the value itself isn't in the question.
_TYPE_WORDS = {
    "EMAIL_ADDRESS": re.compile(r"\b(e-?mails?|gmail|mail address)\b", re.IGNORECASE),
    "PHONE_NUMBER": re.compile(r"\b(phones?|mobile|telephone|country code|area code)\b", re.IGNORECASE),
    "CREDIT_CARD": re.compile(r"\b(credit cards?|cards?|visa|mastercard)\b", re.IGNORECASE),
    "IN_PAN": re.compile(r"\bPAN\b", re.IGNORECASE),
    "IN_AADHAAR": re.compile(r"\b(aadhaar|aadhar)\b", re.IGNORECASE),
    "PERSON": re.compile(r"\b(name|names|initials|surname)\b", re.IGNORECASE),
}

CONSENT_MESSAGE = (
    "This question needs the model to read the actual value of: {types}. Those values "
    "are normally hidden from the model. Re-send with allow_sensitive: true to send only "
    "those values in clear. The answer will not be cached."
)
BLOCK_MESSAGE = "PII detection failed, so nothing was sent to the model."


@dataclass
class Decision:
    action: PrivacyAction | None  # None when privacy mode is off
    types: list[str] = field(default_factory=list)  # types the question needs in clear
    consent_given: bool = False

    @property
    def stops_request(self) -> bool:
        """True when the pipeline must not run: blocked, or consent needed but not given."""
        if self.action == PrivacyAction.BLOCK:
            return True
        return self.action == PrivacyAction.REQUIRE_CONSENT and not self.consent_given

    def message(self) -> str:
        if self.action == PrivacyAction.BLOCK:
            return BLOCK_MESSAGE
        return CONSENT_MESSAGE.format(types=", ".join(self.types))


def referenced_types(question: str) -> set[str]:
    """Sensitive types the question is about.

    A type named by keyword wins ("is Ananya's email a gmail address?" is about
    EMAIL, not PERSON). Otherwise, the types of values written in the question.
    """
    in_question = {entity_type for _, _, entity_type in pii.detect(question)}
    named = {entity_type for entity_type, pattern in _TYPE_WORDS.items() if pattern.search(question)}
    return named or in_question


def begin_request(question: str, allow_sensitive: bool = False) -> Decision:
    """Start this request's privacy context and decide what it may send."""
    ctx = pii.start_request()
    if ctx.mode == PrivacyMode.OFF:
        return Decision(action=None)

    try:
        types = referenced_types(question)
    except Exception:  # noqa: BLE001 — any detector failure must fail closed
        ctx.record.action = PrivacyAction.BLOCK
        return Decision(action=PrivacyAction.BLOCK)

    if not (_CONTENT_RE.search(question) and types):
        return Decision(action=ctx.record.action)

    decision = Decision(
        action=PrivacyAction.REQUIRE_CONSENT, types=sorted(types), consent_given=allow_sensitive
    )
    ctx.record.action = PrivacyAction.REQUIRE_CONSENT
    ctx.record.consent_types = decision.types
    if allow_sensitive:
        ctx.clear_types = set(decision.types)
        ctx.record.sent_in_clear = decision.types
    return decision
