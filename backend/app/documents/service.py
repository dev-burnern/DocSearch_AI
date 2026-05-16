from datetime import UTC, datetime
import mimetypes
from uuid import uuid4

from backend.app.auth.models import WorkspaceContext
from backend.app.documents.models import (
    DocumentDeleteResponse,
    DocumentRecord,
    DocumentUploadResponse,
)
from backend.app.documents.store import DocumentMetadataStore
from backend.app.jobs.base import IndexDocumentJob, JobQueue
from backend.app.parsers.base import DocumentTooLargeError, ParserRegistry
from backend.app.retrieval.qdrant_store import QdrantVectorStore
from backend.app.storage.minio import StorageService


class DocumentNotFoundError(ValueError):
    pass


class DocumentService:
    def __init__(
        self,
        parser_registry: ParserRegistry,
        storage_service: StorageService,
        job_queue: JobQueue,
        document_metadata_store: DocumentMetadataStore,
        vector_store: QdrantVectorStore,
        max_document_bytes: int,
    ) -> None:
        self._parser_registry = parser_registry
        self._storage_service = storage_service
        self._job_queue = job_queue
        self._document_metadata_store = document_metadata_store
        self._vector_store = vector_store
        self._max_document_bytes = max_document_bytes

    def upload_document(
        self,
        *,
        workspace_context: WorkspaceContext,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> DocumentUploadResponse:
        document_id = uuid4().hex
        indexing_job_id = uuid4().hex
        filename = _normalize_filename(filename)
        content_type = _normalize_content_type(content_type, filename)
        self._validate_document_size(data)
        parsed = self._parser_registry.parse(filename=filename, data=data)
        storage_key = self._storage_service.upload_document(
            workspace_id=workspace_context.workspace_id,
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            data=data,
        )
        dispatch = self._job_queue.enqueue(
            IndexDocumentJob(
                job_id=indexing_job_id,
                workspace_id=workspace_context.workspace_id,
                workspace_name=workspace_context.workspace_name,
                document_id=document_id,
                filename=filename,
                content_type=content_type,
                storage_key=storage_key,
            ),
        )

        response = DocumentUploadResponse(
            document_id=document_id,
            workspace_id=workspace_context.workspace_id,
            workspace_name=workspace_context.workspace_name,
            filename=filename,
            parser=parsed.parser_name,
            character_count=parsed.character_count,
            text_preview=parsed.preview,
            storage_key=storage_key,
            indexing_job_id=dispatch.job_id,
            indexing_status=dispatch.status,
            indexing_error=dispatch.failure_reason,
            chunk_count=dispatch.chunk_count,
        )
        self._document_metadata_store.record_document(
            DocumentRecord(
                **response.model_dump(),
                uploaded_at=datetime.now(UTC),
            )
        )

        return response

    def delete_document(
        self,
        *,
        workspace_context: WorkspaceContext,
        document_id: str,
    ) -> DocumentDeleteResponse:
        record = self._document_metadata_store.get_document(
            workspace_id=workspace_context.workspace_id,
            document_id=document_id,
        )
        if record is None:
            raise DocumentNotFoundError(f"Document not found: {document_id}")

        self._vector_store.delete_document(
            workspace_id=workspace_context.workspace_id,
            document_id=document_id,
        )
        self._storage_service.delete_document(storage_key=record.storage_key)
        self._document_metadata_store.delete_document(
            workspace_id=workspace_context.workspace_id,
            document_id=document_id,
        )

        return DocumentDeleteResponse(
            document_id=document_id,
            workspace_id=workspace_context.workspace_id,
            deleted=True,
        )

    def reindex_document(
        self,
        *,
        workspace_context: WorkspaceContext,
        document_id: str,
    ) -> DocumentRecord:
        record = self._document_metadata_store.get_document(
            workspace_id=workspace_context.workspace_id,
            document_id=document_id,
        )
        if record is None:
            raise DocumentNotFoundError(f"Document not found: {document_id}")

        data = self._storage_service.download_document(storage_key=record.storage_key)
        self._validate_document_size(data)
        parsed = self._parser_registry.parse(filename=record.filename, data=data)
        indexing_job_id = uuid4().hex
        self._vector_store.delete_document(
            workspace_id=workspace_context.workspace_id,
            document_id=document_id,
        )
        dispatch = self._job_queue.enqueue(
            IndexDocumentJob(
                job_id=indexing_job_id,
                workspace_id=workspace_context.workspace_id,
                workspace_name=workspace_context.workspace_name,
                document_id=document_id,
                filename=record.filename,
                content_type=_guess_content_type(record.filename),
                storage_key=record.storage_key,
            ),
        )
        updated = record.model_copy(
            update={
                "workspace_name": workspace_context.workspace_name,
                "parser": parsed.parser_name,
                "character_count": parsed.character_count,
                "text_preview": parsed.preview,
                "indexing_job_id": dispatch.job_id,
                "indexing_status": dispatch.status,
                "indexing_error": dispatch.failure_reason,
                "chunk_count": dispatch.chunk_count,
            }
        )
        self._document_metadata_store.record_document(updated)

        return updated

    def _validate_document_size(self, data: bytes) -> None:
        if len(data) > self._max_document_bytes:
            raise DocumentTooLargeError(
                f"Document exceeds maximum size of {self._max_document_bytes} bytes."
            )


def _guess_content_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def _normalize_filename(filename: str) -> str:
    normalized = filename.replace("\\", "/").split("/")[-1].strip()
    return normalized or "document"


def _normalize_content_type(content_type: str, filename: str) -> str:
    normalized = content_type.strip().lower()
    if normalized:
        return normalized
    return _guess_content_type(filename)
