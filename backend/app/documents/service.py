from uuid import uuid4

from backend.app.auth.models import WorkspaceContext
from backend.app.documents.models import DocumentUploadResponse
from backend.app.parsers.base import ParserRegistry
from backend.app.storage.minio import StorageService


class DocumentService:
    def __init__(
        self,
        parser_registry: ParserRegistry,
        storage_service: StorageService,
    ) -> None:
        self._parser_registry = parser_registry
        self._storage_service = storage_service

    def upload_document(
        self,
        *,
        workspace_context: WorkspaceContext,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> DocumentUploadResponse:
        document_id = uuid4().hex
        parsed = self._parser_registry.parse(filename=filename, data=data)
        storage_key = self._storage_service.upload_document(
            workspace_id=workspace_context.workspace_id,
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            data=data,
        )

        return DocumentUploadResponse(
            document_id=document_id,
            workspace_id=workspace_context.workspace_id,
            workspace_name=workspace_context.workspace_name,
            filename=filename,
            parser=parsed.parser_name,
            character_count=parsed.character_count,
            text_preview=parsed.preview,
            storage_key=storage_key,
        )
