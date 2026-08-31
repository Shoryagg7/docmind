import asyncio

from core.db import async_session
from eval.golden_set import GOLDEN_SET
from eval.judge import llm_as_judge
from services.graph import answer_question_graph


async def main():
    passed = 0
    async with async_session() as session:
        for case in GOLDEN_SET:
            result = await answer_question_graph(
                session, case["question"], source=case["source"]
            )
            actual_answer = result["answer"]
            correct = llm_as_judge(case["question"], case["reference_answer"], actual_answer)
            passed += correct

            status = "PASS" if correct else "FAIL"
            print(f"[{status}] {case['question']}")
            print(f"  reference: {case['reference_answer']}")
            print(f"  actual:    {actual_answer}")
            print()

    print(f"{passed}/{len(GOLDEN_SET)} passed")


if __name__ == "__main__":
    asyncio.run(main())
