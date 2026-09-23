"""The only module that talks to Groq, so it is also the privacy gate.

Every outbound message is pseudonymized here before the HTTP call, and every
response is restored here before other code sees it. If PII detection fails for
any reason, the call is not made (fail closed). tests/test_privacy.py asserts
that no other module imports the Groq SDK.
"""

from groq import Groq

from core.config import get_settings
from core.errors import PrivacyBlockedError
from core.usage import record
from services import pii

MODEL = "openai/gpt-oss-120b"


def _client() -> Groq:
    # Free-tier rate limits (429) are routine during eval bursts; the SDK waits out
    # Groq's retry-after header between attempts.
    return Groq(api_key=get_settings().groq_api_key, max_retries=6)


def _sampling() -> dict:
    # Temperature 0 makes eval runs as repeatable as the API allows. It's not a
    # guarantee: the provider can still return different outputs for the same input.
    return {"temperature": 0} if get_settings().eval_mode else {}


def _gate(prompt: str, system: str | None, label: str) -> list[dict]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        outbound = [{**m, "content": pii.pseudonymize(m["content"])} for m in messages]
    except Exception as exc:  # noqa: BLE001 — any detector failure must fail closed
        raise PrivacyBlockedError("PII detection failed; nothing was sent") from exc

    pii.record_call(label, outbound)
    return outbound


def generate(prompt: str, system: str | None = None, label: str = "") -> str:
    messages = _gate(prompt, system, label)
    response = _client().chat.completions.create(model=MODEL, messages=messages, **_sampling())

    if response.usage is not None:
        record(
            MODEL,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            label=label,
        )

    return pii.restore(response.choices[0].message.content)


def generate_stream(prompt: str, system: str | None = None, label: str = ""):
    """Yield restored answer text chunk by chunk as Groq produces it."""
    messages = _gate(prompt, system, label)
    stream = _client().chat.completions.create(
        model=MODEL, messages=messages, stream=True, **_sampling()
    )

    restorer = pii.StreamRestorer()
    for chunk in stream:
        # Groq attaches usage totals to the final chunk automatically.
        if chunk.usage is not None:
            record(MODEL, chunk.usage.prompt_tokens, chunk.usage.completion_tokens, label=label)
        if chunk.choices and chunk.choices[0].delta.content:
            text = restorer.feed(chunk.choices[0].delta.content)
            if text:
                yield text

    tail = restorer.flush()
    if tail:
        yield tail


if __name__ == "__main__":
    print(generate("Say 'DocMind is alive' and nothing else."))
