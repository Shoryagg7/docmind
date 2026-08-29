from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    k: int = 3


class Source(BaseModel):
    id: int
    source: str
    content: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
