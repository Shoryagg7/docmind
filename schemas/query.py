from pydantic import BaseModel, field_validator


class QueryRequest(BaseModel):
    question: str
    k: int = 3
    source: str | None = None
    bypass_cache: bool = False

    @field_validator("source")
    @classmethod
    def add_pdf_extension(cls, value: str | None) -> str | None:
        if value is not None and not value.lower().endswith(".pdf"):
            value = f"{value}.pdf"
        return value


class Source(BaseModel):
    id: int
    source: str
    content: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    cached: bool = False
    tokens: int = 0
    llm_calls: int = 0
