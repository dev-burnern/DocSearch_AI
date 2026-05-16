from qdrant_client import QdrantClient

from backend.app.jobs.base import IndexDocumentJob
from backend.app.retrieval.qdrant_store import RetrievedChunk


def test_DenseRetriever가_워크스페이스_필터로_검색한다() -> None:
    from backend.app.indexing.embedder import DeterministicEmbedder
    from backend.app.retrieval.filters import RetrievalFilter
    from backend.app.retrieval.qdrant_store import QdrantVectorStore
    from backend.app.retrieval.retriever import DenseRetriever

    embedder = DeterministicEmbedder(vector_size=8)
    store = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="docsearch_chunks",
        vector_size=8,
    )

    store.upsert_chunks(
        job=IndexDocumentJob(
            job_id="job-alpha",
            workspace_id="workspace-alpha",
            workspace_name="Workspace Alpha",
            document_id="doc-1",
            filename="finance.txt",
            content_type="text/plain",
            storage_key="workspace-alpha/doc-1/finance.txt",
        ),
        parser_name="text",
        chunks=["budget q1"],
        embeddings=embedder.embed_texts(["budget q1"]),
    )
    store.upsert_chunks(
        job=IndexDocumentJob(
            job_id="job-beta",
            workspace_id="workspace-beta",
            workspace_name="Workspace Beta",
            document_id="doc-2",
            filename="finance.txt",
            content_type="text/plain",
            storage_key="workspace-beta/doc-2/finance.txt",
        ),
        parser_name="text",
        chunks=["budget q1"],
        embeddings=embedder.embed_texts(["budget q1"]),
    )

    retriever = DenseRetriever(
        embedder=embedder,
        vector_store=store,
    )

    results = retriever.retrieve(
        query_text="budget q1",
        filters=RetrievalFilter(workspace_id="workspace-alpha"),
        limit=3,
    )

    assert len(results) == 1
    assert results[0].workspace_id == "workspace-alpha"
    assert results[0].document_id == "doc-1"
    assert results[0].chunk_text == "budget q1"


def test_hybrid_retriever_blends_dense_and_lexical_scores() -> None:
    from backend.app.retrieval.filters import RetrievalFilter
    from backend.app.retrieval.retriever import HybridRetriever

    semantic_chunk = RetrievedChunk(
        workspace_id="workspace-alpha",
        document_id="doc-semantic",
        filename="semantic.txt",
        parser="text",
        chunk_index=0,
        chunk_text="general policy overview",
        score=0.9,
    )
    exact_chunk = RetrievedChunk(
        workspace_id="workspace-alpha",
        document_id="doc-exact",
        filename="exact.txt",
        parser="text",
        chunk_index=0,
        chunk_text="redis rate limit backend failure",
        score=0.1,
    )
    retriever = HybridRetriever(
        embedder=FixedEmbedder(),
        vector_store=FakeVectorStore(
            dense_results=[semantic_chunk, exact_chunk],
            lexical_results=[semantic_chunk, exact_chunk],
        ),
        dense_weight=0.4,
        lexical_weight=0.6,
        candidate_limit=10,
    )

    results = retriever.retrieve(
        query_text="redis rate limit",
        filters=RetrievalFilter(workspace_id="workspace-alpha"),
        limit=2,
    )

    assert [chunk.document_id for chunk in results] == ["doc-exact", "doc-semantic"]
    assert results[0].score == 0.64
    assert results[1].score == 0.36


def test_hybrid_retriever_includes_lexical_only_candidates() -> None:
    from backend.app.retrieval.filters import RetrievalFilter
    from backend.app.retrieval.retriever import HybridRetriever

    lexical_chunk = RetrievedChunk(
        workspace_id="workspace-alpha",
        document_id="doc-lexical",
        filename="lexical.txt",
        parser="text",
        chunk_index=0,
        chunk_text="dependency health failed",
        score=0.0,
    )
    retriever = HybridRetriever(
        embedder=FixedEmbedder(),
        vector_store=FakeVectorStore(
            dense_results=[],
            lexical_results=[lexical_chunk],
        ),
        dense_weight=0.7,
        lexical_weight=0.3,
        candidate_limit=10,
    )

    results = retriever.retrieve(
        query_text="dependency health",
        filters=RetrievalFilter(workspace_id="workspace-alpha"),
        limit=1,
    )

    assert len(results) == 1
    assert results[0].document_id == "doc-lexical"
    assert results[0].score == 0.3


class FixedEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]


class FakeVectorStore:
    def __init__(
        self,
        *,
        dense_results: list[RetrievedChunk],
        lexical_results: list[RetrievedChunk],
    ) -> None:
        self._dense_results = dense_results
        self._lexical_results = lexical_results

    def search(self, *, query_vector, filters, limit) -> list[RetrievedChunk]:
        return self._dense_results[:limit]

    def list_chunks(self, *, filters, limit) -> list[RetrievedChunk]:
        return self._lexical_results[:limit]
