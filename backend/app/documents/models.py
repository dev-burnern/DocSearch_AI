from datetime import UTC, datetime

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    document_id: str
    workspace_id: str
    workspace_name: str
    filename: str
    parser: str
    character_count: int
    text_preview: str
    storage_key: str
    indexing_job_id: str
    indexing_status: str
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
