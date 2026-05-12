from functools import lru_cache

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext
from backend.app.documents.models import DocumentUploadResponse
from backend.app.documents.service import DocumentService
from backend.app.parsers.base import ParserRegistry
from backend.app.storage.minio import StorageService, create_minio_storage_service

router = APIRouter(prefix="/v1/documents", tags=["documents"])


def get_parser_registry() -> ParserRegistry:
    return ParserRegistry()


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return create_minio_storage_service()


def get_document_service(
    parser_registry: ParserRegistry = Depends(get_parser_registry),
    storage_service: StorageService = Depends(get_storage_service),
) -> DocumentService:
    return DocumentService(
        parser_registry=parser_registry,
        storage_service=storage_service,
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
