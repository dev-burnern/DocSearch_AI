from pydantic import BaseModel, Field

from backend.app.documents.models import DocumentSecurityLevel


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] | None = None
    security_levels: list[DocumentSecurityLevel] | None = None
    limit: int = Field(default=5, ge=1, le=20)


class SearchResultChunk(BaseModel):
    document_id: str
    filename: str
    parser: str
    security_level: DocumentSecurityLevel
    chunk_index: int
    score: float
    snippet: str


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResultChunk]
