import re
from dataclasses import replace
from typing import TYPE_CHECKING, Protocol

from backend.app.indexing.embedder import Embedder
from backend.app.retrieval.filters import RetrievalFilter
from backend.app.retrieval.qdrant_store import QdrantVectorStore, RetrievedChunk

if TYPE_CHECKING:
    from backend.app.core.config import Settings


class Retriever(Protocol):
    def retrieve(
        self,
        *,
        query_text: str,
        filters: RetrievalFilter,
        limit: int,
    ) -> list[RetrievedChunk]:
        ...


class DenseRetriever:
    def __init__(
        self,
        *,
        embedder: Embedder,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store

    def retrieve(
        self,
        *,
        query_text: str,
        filters: RetrievalFilter,
        limit: int,
    ) -> list[RetrievedChunk]:
        vector = self._embedder.embed_texts([query_text])[0]
        return self._vector_store.search(
            query_vector=vector,
            filters=filters,
            limit=limit,
        )


class HybridRetriever:
    def __init__(
        self,
        *,
        embedder: Embedder,
        vector_store: QdrantVectorStore,
        dense_weight: float,
        lexical_weight: float,
        candidate_limit: int,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._dense_weight = dense_weight
        self._lexical_weight = lexical_weight
        self._candidate_limit = candidate_limit

    def retrieve(
        self,
        *,
        query_text: str,
        filters: RetrievalFilter,
        limit: int,
    ) -> list[RetrievedChunk]:
        candidate_limit = max(limit, self._candidate_limit)
        vector = self._embedder.embed_texts([query_text])[0]
        dense_chunks = self._vector_store.search(
            query_vector=vector,
            filters=filters,
            limit=candidate_limit,
        )
        lexical_chunks = self._vector_store.list_chunks(
            filters=filters,
            limit=candidate_limit,
        )

        dense_scores = {_chunk_key(chunk): chunk.score for chunk in dense_chunks}
        query_terms = _tokenize(query_text)
        candidates: dict[tuple[str, int], RetrievedChunk] = {}
        for chunk in dense_chunks + lexical_chunks:
            candidates.setdefault(_chunk_key(chunk), chunk)

        scored = [
            replace(
                chunk,
                score=round(
                    (dense_scores.get(_chunk_key(chunk), 0.0) * self._dense_weight)
                    + (
                        _lexical_score(query_terms, chunk.chunk_text)
                        * self._lexical_weight
                    ),
                    6,
                ),
            )
            for chunk in candidates.values()
        ]
        scored.sort(
            key=lambda chunk: (
                -chunk.score,
                chunk.filename,
                chunk.chunk_index,
                chunk.document_id,
            )
        )
        return scored[:limit]


def build_retriever(
    *,
    settings: "Settings",
    embedder: Embedder,
    vector_store: QdrantVectorStore,
) -> Retriever:
    if settings.retrieval_mode == "hybrid":
        return HybridRetriever(
            embedder=embedder,
            vector_store=vector_store,
            dense_weight=settings.hybrid_dense_weight,
            lexical_weight=settings.hybrid_lexical_weight,
            candidate_limit=settings.hybrid_candidate_limit,
        )

    return DenseRetriever(embedder=embedder, vector_store=vector_store)


def _chunk_key(chunk: RetrievedChunk) -> tuple[str, int]:
    return (chunk.document_id, chunk.chunk_index)


def _lexical_score(query_terms: set[str], chunk_text: str) -> float:
    if not query_terms:
        return 0.0
    chunk_terms = _tokenize(chunk_text)
    if not chunk_terms:
        return 0.0
    return len(query_terms & chunk_terms) / len(query_terms)


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"\w+", value.lower()))
