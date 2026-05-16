from functools import lru_cache
from typing import Callable

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

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
from backend.app.documents.security import validate_document_security_level
from backend.app.documents.service import DocumentNotFoundError, DocumentService
from backend.app.documents.store import DocumentMetadataStore, InMemoryDocumentMetadataStore
from backend.app.indexing.chunker import CharacterChunker
from backend.app.indexing.embedder import (
    BGEEmbeddingClient,
    DeterministicEmbedder,
    Embedder,
)
from backend.app.indexing.embedding_profiles import get_default_embedding_profile
from backend.app.indexing.pipeline import IndexingPipeline
from backend.app.jobs.base import JobQueue
from backend.app.jobs.inprocess import InProcessJobQueue
from backend.app.jobs.redis_queue import create_redis_job_queue
from backend.app.parsers.base import DocumentProcessingError, ParserRegistry
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
) -> Embedder:
    if settings.embedding_backend == "bge":
        return BGEEmbeddingClient(profile=get_default_embedding_profile(settings))
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
    embedder: Embedder = Depends(get_embedder),
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
    request: Request,
    pipeline: IndexingPipeline = Depends(get_indexing_pipeline),
    settings: Settings = Depends(get_runtime_settings),
) -> JobQueue:
    if settings.indexing_queue_backend == "redis":
        return create_redis_job_queue(
            settings,
            operation_event_store=request.app.state.operation_event_store,
        )

    return InProcessJobQueue(
        processor=pipeline.run,
        operation_event_store=request.app.state.operation_event_store,
    )


def get_document_service(
    parser_registry: ParserRegistry = Depends(get_parser_registry),
    storage_service: StorageService = Depends(get_storage_service),
    job_queue: JobQueue = Depends(get_job_queue),
    document_metadata_store: DocumentMetadataStore = Depends(get_document_metadata_store),
    vector_store: QdrantVectorStore = Depends(get_qdrant_store),
    settings: Settings = Depends(get_runtime_settings),
) -> DocumentService:
    return DocumentService(
        parser_registry=parser_registry,
        storage_service=storage_service,
        job_queue=job_queue,
        document_metadata_store=document_metadata_store,
        vector_store=vector_store,
        max_document_bytes=settings.document_max_bytes,
    )


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    security_level: str = Form(default="internal"),
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    try:
        data = await file.read()
        validated_security_level = validate_document_security_level(security_level)
        return document_service.upload_document(
            workspace_context=workspace_context,
            filename=file.filename or "document",
            content_type=file.content_type or "application/octet-stream",
            data=data,
            security_level=validated_security_level,
        )
    except DocumentProcessingError as exc:
        raise _document_processing_error(exc) from exc


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
    except DocumentProcessingError as exc:
        raise _document_processing_error(exc) from exc


def _document_not_found(document_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "DOCUMENT_NOT_FOUND",
            "message": f"Document not found: {document_id}",
        },
    )


def _document_processing_error(exc: DocumentProcessingError) -> HTTPException:
    status_code = (
        status.HTTP_413_CONTENT_TOO_LARGE
        if exc.code == "DOCUMENT_TOO_LARGE"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(
        status_code=status_code,
        detail={
            "code": exc.code,
            "message": str(exc),
        },
    )
