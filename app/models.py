from __future__ import annotations
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    path: str = Field(..., description="문서 디렉토리 또는 파일 경로")
    recursive: bool = True


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class ChatRequest(BaseModel):
    query: str
    top_k: int | None = None
    top_n: int | None = None
    model: str | None = None


class ChunkHit(BaseModel):
    point_id: str
    score: float
    doc_id: str
    source: str
    page: int | None = None
    sheet: str | None = None
    chunk_index: int
    text: str


class SearchResponse(BaseModel):
    hits: list[ChunkHit]
    latency_ms: dict[str, float]


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChunkHit]
    latency_ms: dict[str, float]
