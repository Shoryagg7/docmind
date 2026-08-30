from services.llm_client import generate

GRADER_SYSTEM_PROMPT = (
    "You judge whether a document excerpt is relevant to a question. "
    "Reply with exactly one word: 'yes' or 'no'. Nothing else."
)


def grade_relevance(query: str, chunk_content: str) -> bool:
    prompt = (
        f"Question: {query}\n\n"
        f"Excerpt: {chunk_content}\n\n"
        "Is this excerpt relevant to answering the question?"
    )
    verdict = generate(prompt, system=GRADER_SYSTEM_PROMPT)
    return verdict.strip().lower().startswith("yes")


if __name__ == "__main__":
    relevant = grade_relevance(
        "What city does Maya Chen work in?",
        "Maya Chen is a backend engineer based in Toronto.",
    )
    irrelevant = grade_relevance(
        "What city does Maya Chen work in?",
        "Nimbus Cloud Storage offers a free tier with 5GB of storage.",
    )
    print(f"relevant chunk graded relevant: {relevant}")
    print(f"irrelevant chunk graded relevant: {irrelevant}")
