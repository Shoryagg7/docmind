import logging
from contextvars import ContextVar
from dataclasses import dataclass

logger = logging.getLogger("docmind.usage")

# Confirmed empirically from Groq's 429 response during Phase 7 eval runs:
# "Limit 200000, Used 199707" for openai/gpt-oss-20b on the free tier.
FREE_TIER_DAILY_TOKENS = 200_000


@dataclass
class UsageTotals:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def percent_of_daily_quota(self) -> float:
        return 100.0 * self.total_tokens / FREE_TIER_DAILY_TOKENS


# A ContextVar rather than a module global: FastAPI serves requests concurrently on
# one event loop, and a global counter would blend two users' usage together. Each
# request gets its own accumulator, isolated automatically.
_usage: ContextVar[UsageTotals | None] = ContextVar("docmind_usage", default=None)


def start_request() -> UsageTotals:
    totals = UsageTotals()
    _usage.set(totals)
    return totals


def current() -> UsageTotals | None:
    return _usage.get()


def record(model: str, prompt_tokens: int, completion_tokens: int, label: str = "") -> None:
    logger.info(
        "llm_call model=%s label=%s prompt=%d completion=%d total=%d",
        model,
        label or "-",
        prompt_tokens,
        completion_tokens,
        prompt_tokens + completion_tokens,
    )

    totals = _usage.get()
    if totals is None:
        return

    totals.calls += 1
    totals.prompt_tokens += prompt_tokens
    totals.completion_tokens += completion_tokens
