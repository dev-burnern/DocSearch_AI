from qdrant_client import QdrantClient

from backend.app.jobs.base import IndexDocumentJob


def test_Qdrant_저장소가_청크를_저장하고_검색한다() -> None:
    from backend.app.retrieval.filters import RetrievalFilter
    from backend.app.retrieval.qdrant_store import QdrantVectorStore

    store = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="docsearch_chunks",
        vector_size=4,
    )

    store.upsert_chunks(
        job=IndexDocumentJob(
            job_id="job-1",
            workspace_id="workspace-alpha",
            workspace_name="Workspace Alpha",
            document_id="doc-1",
            filename="memo.txt",
            content_type="text/plain",
            storage_key="workspace-alpha/doc-1/memo.txt",
        ),
        parser_name="text",
        chunks=["alpha budget", "beta note"],
        embeddings=[
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ],
    )

    results = store.search(
        query_vector=[1.0, 0.0, 0.0, 0.0],
        filters=RetrievalFilter(workspace_id="workspace-alpha"),
        limit=2,
    )

    assert len(results) == 2
    assert results[0].document_id == "doc-1"
    assert results[0].filename == "memo.txt"
    assert results[0].chunk_index == 0
    assert results[0].chunk_text == "alpha budget"

    listed = store.list_chunks(
        filters=RetrievalFilter(workspace_id="workspace-alpha"),
        limit=10,
    )

    assert [chunk.chunk_text for chunk in listed] == ["alpha budget", "beta note"]
    assert [chunk.score for chunk in listed] == [0.0, 0.0]


def test_Qdrant_저장소가_문서_단위로_청크를_삭제한다() -> None:
    from backend.app.retrieval.filters import RetrievalFilter
    from backend.app.retrieval.qdrant_store import QdrantVectorStore

    store = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="docsearch_chunks",
        vector_size=4,
    )
    store.upsert_chunks(
        job=IndexDocumentJob(
            job_id="job-1",
            workspace_id="workspace-alpha",
            workspace_name="Workspace Alpha",
            document_id="doc-1",
            filename="memo.txt",
            content_type="text/plain",
            storage_key="workspace-alpha/doc-1/memo.txt",
        ),
        parser_name="text",
        chunks=["alpha budget"],
        embeddings=[[1.0, 0.0, 0.0, 0.0]],
    )

    store.delete_document(
        workspace_id="workspace-alpha",
        document_id="doc-1",
    )
    results = store.search(
        query_vector=[1.0, 0.0, 0.0, 0.0],
        filters=RetrievalFilter(workspace_id="workspace-alpha"),
        limit=2,
    )

    assert results == []
