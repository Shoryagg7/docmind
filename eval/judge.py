from services.llm_client import generate

JUDGE_SYSTEM_PROMPT = (
    "You judge whether a candidate answer conveys the same factual information as a "
    "reference answer, for a given question. Minor differences in wording don't matter. "
    "Reply with exactly one word: 'correct' or 'incorrect'."
)


def llm_as_judge(question: str, reference_answer: str, actual_answer: str) -> bool:
    prompt = (
        f"Question: {question}\n\n"
        f"Reference answer: {reference_answer}\n\n"
        f"Candidate answer: {actual_answer}\n\n"
        "Does the candidate answer convey the same information as the reference answer?"
    )
    verdict = generate(prompt, system=JUDGE_SYSTEM_PROMPT, label="judge")
    return verdict.strip().lower().startswith("correct")
