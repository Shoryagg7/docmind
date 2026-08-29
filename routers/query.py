from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from schemas.query import QueryResponse, QueryRequest
from services.rag import answer_question

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, session: AsyncSession = Depends(get_session)):
    return await answer_question(session, request.question, k=request.k, source=request.source)
