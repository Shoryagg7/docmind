from pydantic import BaseModel


class UploadResponse(BaseModel):
    source: str
    chunks_stored: int
