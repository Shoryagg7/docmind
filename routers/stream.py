import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.usage import current, start_request
from schemas.query import QueryRequest
from services.graph import build_context, build_graph, filter_cited, initial_state
from services.llm_client import generate_stream
from services.rag import SYSTEM_PROMPT
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


async def event_stream(session: AsyncSession, request: QueryRequest):
    totals = start_request()

    cached = (
        None
        if request.bypass_cache
        else await get_cached_answer(request.question, source=request.source)
    )
    if cached is not None:
        yield sse({"type": "stage", "stage": "cache", "detail": "Semantic cache hit"})
        yield sse({"type": "token", "text": cached["answer"]})
        yield sse(
            {
                "type": "done",
                "cached": True,
                "sources": cached.get("sources", []),
                "tokens": 0,
                "llm_calls": 0,
            }
        )
        return

    yield sse(
        {
            "type": "stage",
            "stage": "cache",
            "detail": "Cache bypassed — running pipeline"
            if request.bypass_cache
            else "Cache miss — running pipeline",
        }
    )

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
        answer = "I don't know — no relevant documents found."
        yield sse({"type": "token", "text": answer})
        yield sse(
            {
                "type": "done",
                "cached": False,
                "sources": [],
                "tokens": totals.total_tokens,
                "llm_calls": totals.calls,
            }
        )
        return

    context, all_sources = build_context(chunks)
    prompt = f"Context:\n{context}\n\nQuestion: {final_state['query']}"

    answer = ""
    for piece in generate_stream(prompt, system=SYSTEM_PROMPT, label="generate"):
        answer += piece
        yield sse({"type": "token", "text": piece})

    sources = filter_cited(answer, all_sources)
    await set_cached_answer(
        request.question, {"answer": answer, "sources": sources}, source=request.source
    )

    totals = current() or totals
    yield sse(
        {
            "type": "done",
            "cached": False,
            "sources": sources,
            "tokens": totals.total_tokens,
            "llm_calls": totals.calls,
        }
    )


@router.post("/query/stream")
async def query_stream(request: QueryRequest, session: AsyncSession = Depends(get_session)):
    return StreamingResponse(
        event_stream(session, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
