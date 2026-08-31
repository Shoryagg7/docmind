from pydantic import BaseModel


class UploadResponse(BaseModel):
    source: str
    chunks_stored: int


class DocumentSummary(BaseModel):
    source: str
    chunks: int
