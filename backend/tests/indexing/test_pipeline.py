from backend.app.parsers.base import ParserRegistry


class InMemoryStorage:
    def __init__(self, documents: dict[str, bytes]) -> None:
        self.documents = documents

    def download_document(self, *, storage_key: str) -> bytes:
        return self.documents[storage_key]


def test_인덱싱_파이프라인이_문서를_청킹하고_Qdrant에_저장한다() -> None:
    from backend.app.indexing.chunker import CharacterChunker
    from backend.app.indexing.embedder import DeterministicEmbedder
    from backend.app.indexing.pipeline import IndexingPipeline
    from backend.app.jobs.base import IndexDocumentJob
    from backend.app.retrieval.filters import RetrievalFilter
    from backend.app.retrieval.qdrant_store import QdrantVectorStore
    from qdrant_client import QdrantClient

    storage_key = "workspace-alpha/doc-1/memo.txt"
    storage = InMemoryStorage({storage_key: b"abcdefghij1234567890"})
    vector_store = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="docsearch_chunks",
        vector_size=4,
    )
    pipeline = IndexingPipeline(
        storage_service=storage,
        parser_registry=ParserRegistry(),
        chunker=CharacterChunker(max_characters=10, overlap_characters=0),
        embedder=DeterministicEmbedder(vector_size=4),
        vector_store=vector_store,
    )

    result = pipeline.run(
        IndexDocumentJob(
            job_id="job-1",
            workspace_id="workspace-alpha",
            workspace_name="Workspace Alpha",
            document_id="doc-1",
            filename="memo.txt",
            content_type="text/plain",
            storage_key=storage_key,
        ),
    )

    assert result.job_id == "job-1"
    assert result.document_id == "doc-1"
    assert result.parser == "text"
    assert result.chunk_count == 2
    assert result.chunks == ["abcdefghij", "1234567890"]
    assert len(result.embeddings) == 2
    assert result.embedding_count == 2
    assert result.embedding_dimensions == 4

    stored = vector_store.search(
        query_vector=result.embeddings[0],
        filters=RetrievalFilter(workspace_id="workspace-alpha"),
        limit=2,
    )

    assert len(stored) == 2
    assert stored[0].document_id == "doc-1"
    assert stored[0].chunk_text == "abcdefghij"
