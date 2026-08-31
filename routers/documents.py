import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.errors import InvalidPDFError
from core.models import Chunk
from schemas.document import DocumentSummary, UploadResponse
from services.ingest import ingest_pdf
from services.vector_store import store_chunks

router = APIRouter()


@router.get("/documents", response_model=list[DocumentSummary])
async def list_documents(session: AsyncSession = Depends(get_session)):
    stmt = select(Chunk.source, func.count()).group_by(Chunk.source).order_by(Chunk.source)
    result = await session.execute(stmt)
    return [DocumentSummary(source=source, chunks=count) for source, count in result.all()]


@router.post("/documents", response_model=UploadResponse)
async def upload_document(file: UploadFile, session: AsyncSession = Depends(get_session)):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp.flush()

        try:
            chunks = ingest_pdf(tmp.name)
        except InvalidPDFError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    await store_chunks(session, chunks, source=file.filename)

    return UploadResponse(source=file.filename, chunks_stored=len(chunks))
