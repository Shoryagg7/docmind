from groq import Groq

from core.config import get_settings

MODEL = "openai/gpt-oss-120b"


def generate(prompt: str, system: str | None = None) -> str:
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

    return response.choices[0].message.content


if __name__ == "__main__":
    print(generate("Say 'DocMind is alive' and nothing else."))
