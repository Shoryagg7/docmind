from groq import Groq

from core.config import get_settings
from core.usage import record

MODEL = "openai/gpt-oss-120b"


def generate(prompt: str, system: str | None = None, label: str = "") -> str:
    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    if response.usage is not None:
        record(
            MODEL,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            label=label,
        )

    return response.choices[0].message.content


def generate_stream(prompt: str, system: str | None = None, label: str = ""):
    """Yield answer text chunk by chunk as Groq produces them."""
    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        # Groq attaches usage totals to the final chunk automatically.
        if chunk.usage is not None:
            record(MODEL, chunk.usage.prompt_tokens, chunk.usage.completion_tokens, label=label)
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


if __name__ == "__main__":
    print(generate("Say 'DocMind is alive' and nothing else."))
