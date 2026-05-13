from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
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
