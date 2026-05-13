from backend.app.indexing.embedder import Embedder
from backend.app.retrieval.filters import RetrievalFilter
from backend.app.retrieval.qdrant_store import QdrantVectorStore, RetrievedChunk


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
