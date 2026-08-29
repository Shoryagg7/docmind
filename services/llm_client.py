from groq import Groq

from core.config import get_settings

MODEL = "openai/gpt-oss-20b"


def generate(prompt: str) -> str:
    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    print(generate("Say 'DocMind is alive' and nothing else."))
