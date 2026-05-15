from functools import lru_cache
from typing import Callable

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext
from backend.app.core.config import Settings, get_settings
from backend.app.documents.models import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentRecord,
    DocumentUploadResponse,
)
from backend.app.documents.postgres_store import PostgresDocumentMetadataStore
from backend.app.documents.service import DocumentNotFoundError, DocumentService
from backend.app.documents.store import DocumentMetadataStore, InMemoryDocumentMetadataStore
from backend.app.indexing.chunker import CharacterChunker
from backend.app.indexing.embedder import DeterministicEmbedder
from backend.app.indexing.pipeline import IndexingPipeline
from backend.app.jobs.base import JobQueue
from backend.app.jobs.inprocess import InProcessJobQueue
from backend.app.jobs.redis_queue import RedisJobQueue
from backend.app.parsers.base import ParserRegistry
from backend.app.retrieval.qdrant_store import QdrantVectorStore
from backend.app.storage.minio import StorageService, create_minio_storage_service
from qdrant_client import QdrantClient

router = APIRouter(prefix="/v1/documents", tags=["documents"])


def get_parser_registry() -> ParserRegistry:
    return ParserRegistry()


def get_runtime_settings() -> Settings:
    return get_settings()


def create_document_metadata_store(
    settings: Settings,
    *,
    connection_factory: Callable[[], object] | None = None,
) -> DocumentMetadataStore:
    if settings.document_metadata_backend == "postgres":
        return PostgresDocumentMetadataStore(
            database_url=settings.database_url,
            connection_factory=connection_factory,
        )

    return InMemoryDocumentMetadataStore()


@lru_cache(maxsize=1)
def get_document_metadata_store() -> DocumentMetadataStore:
    return create_document_metadata_store(get_settings())


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return create_minio_storage_service()


def get_chunker(
    settings: Settings = Depends(get_runtime_settings),
) -> CharacterChunker:
    return CharacterChunker(
        max_characters=settings.chunk_max_characters,
        overlap_characters=settings.chunk_overlap_characters,
    )


def get_embedder(
    settings: Settings = Depends(get_runtime_settings),
) -> DeterministicEmbedder:
    return DeterministicEmbedder(vector_size=settings.embedding_vector_size)


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def get_qdrant_store(
    settings: Settings = Depends(get_runtime_settings),
) -> QdrantVectorStore:
    return QdrantVectorStore(
        client=get_qdrant_client(),
        collection_name=settings.qdrant_collection,
        vector_size=settings.embedding_vector_size,
    )


def get_indexing_pipeline(
    storage_service: StorageService = Depends(get_storage_service),
    parser_registry: ParserRegistry = Depends(get_parser_registry),
    chunker: CharacterChunker = Depends(get_chunker),
    embedder: DeterministicEmbedder = Depends(get_embedder),
    vector_store: QdrantVectorStore = Depends(get_qdrant_store),
) -> IndexingPipeline:
    return IndexingPipeline(
        storage_service=storage_service,
        parser_registry=parser_registry,
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
    )


def get_job_queue(
    pipeline: IndexingPipeline = Depends(get_indexing_pipeline),
    settings: Settings = Depends(get_runtime_settings),
) -> JobQueue:
    if settings.indexing_queue_backend == "redis":
        return RedisJobQueue()

    return InProcessJobQueue(processor=pipeline.run)


def get_document_service(
    parser_registry: ParserRegistry = Depends(get_parser_registry),
    storage_service: StorageService = Depends(get_storage_service),
    job_queue: JobQueue = Depends(get_job_queue),
    document_metadata_store: DocumentMetadataStore = Depends(get_document_metadata_store),
    vector_store: QdrantVectorStore = Depends(get_qdrant_store),
) -> DocumentService:
    return DocumentService(
        parser_registry=parser_registry,
        storage_service=storage_service,
        job_queue=job_queue,
        document_metadata_store=document_metadata_store,
        vector_store=vector_store,
    )


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    try:
        data = await file.read()
        return document_service.upload_document(
            workspace_context=workspace_context,
            filename=file.filename or "document",
            content_type=file.content_type or "application/octet-stream",
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "DOCUMENT_UNSUPPORTED_TYPE",
                "message": str(exc),
            },
        ) from exc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(default=100, ge=1, le=200),
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    document_metadata_store: DocumentMetadataStore = Depends(get_document_metadata_store),
) -> DocumentListResponse:
    documents = document_metadata_store.list_documents(
        workspace_id=workspace_context.workspace_id,
        limit=limit,
    )
    return DocumentListResponse(documents=documents, total=len(documents))


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    try:
        return document_service.delete_document(
            workspace_context=workspace_context,
            document_id=document_id,
        )
    except DocumentNotFoundError as exc:
        raise _document_not_found(document_id) from exc


@router.post("/{document_id}/reindex", response_model=DocumentRecord)
async def reindex_document(
    document_id: str,
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentRecord:
    try:
        return document_service.reindex_document(
            workspace_context=workspace_context,
            document_id=document_id,
        )
    except DocumentNotFoundError as exc:
        raise _document_not_found(document_id) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "DOCUMENT_UNSUPPORTED_TYPE",
                "message": str(exc),
            },
        ) from exc


def _document_not_found(document_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "DOCUMENT_NOT_FOUND",
            "message": f"Document not found: {document_id}",
        },
    )
