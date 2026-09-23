import json
from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.enums import PrivacyAction
from core.errors import PrivacyBlockedError
from core.usage import current, start_request
from schemas.query import QueryRequest
from services.graph import SYSTEM_PROMPT, build_context, build_graph, filter_cited, initial_state
from services import pii
from services.llm_client import generate_stream
from services.privacy_policy import BLOCK_MESSAGE, begin_request
from services.semantic_cache import get_cached_answer, set_cached_answer

router = APIRouter()

STAGE_LABELS = {
    "retrieve": "Retrieving chunks from pgvector",
    "grade": "Grading chunk relevance",
    "rewrite": "No relevant chunks — rewriting the query",
    "generate": "Generating grounded answer",
}


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def done_event(totals, cached: bool = False, sources: list | None = None) -> str:
    return sse(
        {
            "type": "done",
            "cached": cached,
            "sources": sources or [],
            "tokens": 0 if cached else totals.total_tokens,
            "llm_calls": 0 if cached else totals.calls,
            "privacy": asdict(pii.current().record),
        }
    )


async def event_stream(session: AsyncSession, request: QueryRequest):
    totals = start_request()
    decision = begin_request(request.question, request.allow_sensitive)

    if decision.stops_request:
        yield sse({"type": "stage", "stage": "privacy", "detail": decision.action})
        yield sse({"type": "token", "text": decision.message()})
        yield done_event(totals)
        return

    # Consent answers never touch the cache (see services/graph.py::answer_query).
    use_cache = not decision.consent_given

    cached = (
        await get_cached_answer(request.question, source=request.source)
        if use_cache and not request.bypass_cache
        else None
    )
    if cached is not None:
        yield sse({"type": "stage", "stage": "cache", "detail": "Semantic cache hit"})
        yield sse({"type": "token", "text": cached["answer"]})
        yield done_event(totals, cached=True, sources=cached.get("sources", []))
        return

    yield sse(
        {
            "type": "stage",
            "stage": "cache",
            "detail": "Cache miss — running pipeline" if use_cache and not request.bypass_cache
            else "Cache skipped — running pipeline",
        }
    )

    try:
        async for event in _pipeline(session, request, totals, cache_answer=use_cache):
            yield event
    except PrivacyBlockedError:
        pii.current().record.action = PrivacyAction.BLOCK
        yield sse({"type": "token", "text": BLOCK_MESSAGE})
        yield done_event(totals)


async def _pipeline(session: AsyncSession, request: QueryRequest, totals, cache_answer: bool):
    graph = build_graph(session)
    state = initial_state(request.question, request.k, request.source, defer_generation=True)
    final_state = None

    async for event in graph.astream(state):
        for node, update in event.items():
            # A node that changes no state (generate_node when deferred) streams None.
            update = update or {}
            detail = STAGE_LABELS.get(node, node)
            if node == "grade":
                found = len(update.get("relevant_chunks", []))
                detail = f"Graded chunks — {found} relevant"
            elif node == "retrieve":
                detail = f"Retrieved {len(update.get('chunks', []))} chunks from pgvector"
            elif node == "rewrite":
                detail = f"No relevant chunks — rewrote query to: {update.get('query', '')}"
            yield sse({"type": "stage", "stage": node, "detail": detail})
            final_state = {**(final_state or state), **update}

    chunks = (final_state or {}).get("relevant_chunks", [])

    if not chunks:
        yield sse({"type": "token", "text": "I don't know — no relevant documents found."})
        yield done_event(totals)
        return

    context, all_sources = build_context(chunks)
    prompt = f"Context:\n{context}\n\nQuestion: {final_state['query']}"

    answer = ""
    for piece in generate_stream(prompt, system=SYSTEM_PROMPT, label="generate"):
        answer += piece
        yield sse({"type": "token", "text": piece})

    sources = filter_cited(answer, all_sources)
    if cache_answer:
        # Stored after restore: the cache lives inside the privacy boundary.
        await set_cached_answer(
            request.question, {"answer": answer, "sources": sources}, source=request.source
        )

    yield done_event(current() or totals, sources=sources)


@router.post("/query/stream")
async def query_stream(request: QueryRequest, session: AsyncSession = Depends(get_session)):
    return StreamingResponse(
        event_stream(session, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
