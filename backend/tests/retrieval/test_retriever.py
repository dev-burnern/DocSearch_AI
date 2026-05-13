from qdrant_client import QdrantClient

from backend.app.jobs.base import IndexDocumentJob


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
