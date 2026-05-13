from typing import Protocol

from pydantic import BaseModel, Field

from backend.app.retrieval.qdrant_store import RetrievedChunk


class RerankRequest(BaseModel):
    query: str = Field(min_length=1)
    chunks: list[RetrievedChunk]
    top_k: int = Field(gt=0)


class RerankedChunk(BaseModel):
    chunk: RetrievedChunk
    rerank_score: float


class RerankerProviderError(RuntimeError):
    pass


class Reranker(Protocol):
    def rerank(self, request: RerankRequest) -> list[RerankedChunk]:
        raise NotImplementedError


class ScorePreservingReranker:
    def rerank(self, request: RerankRequest) -> list[RerankedChunk]:
        return [
            RerankedChunk(chunk=chunk, rerank_score=chunk.score)
            for chunk in request.chunks[: request.top_k]
        ]
