import logging
import time

from backend.app.core.config import get_settings
from backend.app.core.operation_events import InMemoryOperationEventStore
from backend.app.documents.router import (
    create_document_metadata_store,
    get_chunker,
    get_embedder,
)
from backend.app.indexing.pipeline import IndexingPipeline
from backend.app.jobs.redis_queue import create_redis_job_queue
from backend.app.jobs.worker import IndexingJobWorker
from backend.app.parsers.base import ParserRegistry
from backend.app.retrieval.qdrant_store import QdrantVectorStore
from backend.app.storage.minio import create_minio_storage_service
from qdrant_client import QdrantClient


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = get_settings()
    logger = logging.getLogger("docsearch.worker")
    logger.info(
        "worker started",
        extra={"queue_backend": settings.indexing_queue_backend},
    )

    if settings.indexing_queue_backend != "redis":
        logger.info("worker idle because indexing queue backend is not redis")
        _sleep_forever()
        return

    worker = _create_indexing_worker()
    while True:
        worker.process_next(timeout_seconds=5)


def _create_indexing_worker() -> IndexingJobWorker:
    settings = get_settings()
    operation_event_store = InMemoryOperationEventStore()
    storage_service = create_minio_storage_service()
    parser_registry = ParserRegistry()
    vector_store = QdrantVectorStore(
        client=QdrantClient(url=settings.qdrant_url),
        collection_name=settings.qdrant_collection,
        vector_size=settings.embedding_vector_size,
    )
    pipeline = IndexingPipeline(
        storage_service=storage_service,
        parser_registry=parser_registry,
        chunker=get_chunker(settings),
        embedder=get_embedder(settings),
        vector_store=vector_store,
    )
    return IndexingJobWorker(
        queue=create_redis_job_queue(
            settings,
            operation_event_store=operation_event_store,
        ),
        pipeline=pipeline,
        document_metadata_store=create_document_metadata_store(settings),
        operation_event_store=operation_event_store,
    )


def _sleep_forever() -> None:
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
