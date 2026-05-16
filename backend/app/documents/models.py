from datetime import UTC, datetime

from pydantic import BaseModel, Field


DocumentSecurityLevel = str
GENERAL_SECURITY_LEVEL = "general"
INTERNAL_SECURITY_LEVEL = "internal"
CONFIDENTIAL_SECURITY_LEVEL = "confidential"
RESTRICTED_SECURITY_LEVEL = "restricted"
SUPPORTED_DOCUMENT_SECURITY_LEVELS = {
    GENERAL_SECURITY_LEVEL,
    INTERNAL_SECURITY_LEVEL,
    CONFIDENTIAL_SECURITY_LEVEL,
    RESTRICTED_SECURITY_LEVEL,
}


class DocumentMetadata(BaseModel):
    document_id: str
    workspace_id: str
    workspace_name: str
    uploaded_by_employee_id: str | None = None
    security_level: DocumentSecurityLevel = INTERNAL_SECURITY_LEVEL
    filename: str
    parser: str
    character_count: int
    text_preview: str
    storage_key: str
    indexing_job_id: str
    indexing_status: str
    indexing_error: str | None = None
    chunk_count: int


class DocumentUploadResponse(DocumentMetadata):
    pass


class DocumentRecord(DocumentMetadata):
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DocumentListResponse(BaseModel):
    documents: list[DocumentRecord]
    total: int


class DocumentDeleteResponse(BaseModel):
    document_id: str
    workspace_id: str
    deleted: bool
