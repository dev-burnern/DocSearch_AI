from dataclasses import dataclass

from backend.app.indexing.chunker import CharacterChunker
from backend.app.indexing.embedder import Embedder
from backend.app.jobs.base import IndexDocumentJob
from backend.app.parsers.base import ParserRegistry
from backend.app.retrieval.qdrant_store import QdrantVectorStore
from backend.app.storage.minio import StorageService


@dataclass(frozen=True)
class IndexingResult:
    job_id: str
    document_id: str
    parser: str
    chunk_count: int
    chunks: list[str]
    embeddings: list[list[float]]
    embedding_count: int
    embedding_dimensions: int


class IndexingPipeline:
    def __init__(
        self,
        *,
        storage_service: StorageService,
        parser_registry: ParserRegistry,
        chunker: CharacterChunker,
        embedder: Embedder,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._storage_service = storage_service
        self._parser_registry = parser_registry
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store

    def run(self, job: IndexDocumentJob) -> IndexingResult:
        data = self._storage_service.download_document(storage_key=job.storage_key)
        parsed = self._parser_registry.parse(filename=job.filename, data=data)
        chunks = self._chunker.chunk(parsed.text)
        embeddings = self._embedder.embed_texts(chunks)
        dimensions = len(embeddings[0]) if embeddings else 0
        self._vector_store.upsert_chunks(
            job=job,
            parser_name=parsed.parser_name,
            chunks=chunks,
            embeddings=embeddings,
        )

        return IndexingResult(
            job_id=job.job_id,
            document_id=job.document_id,
            parser=parsed.parser_name,
            chunk_count=len(chunks),
            chunks=chunks,
            embeddings=embeddings,
            embedding_count=len(embeddings),
            embedding_dimensions=dimensions,
        )
