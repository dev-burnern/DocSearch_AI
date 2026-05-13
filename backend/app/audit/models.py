from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditCitation(BaseModel):
    citation_id: int
    document_id: str
    filename: str
    chunk_index: int
    score: float
    rerank_score: float | None = None


class ChatAuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = "chat.answer.generated"
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str
    workspace_id: str
    workspace_name: str
    question: str
    document_ids: list[str] | None = None
    retrieval_limit: int
    rerank_top_k: int
    retrieved_chunk_count: int
    model: str
    answer_preview: str
    answer_character_count: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    citations: list[AuditCitation]


class ChatAuditEventListResponse(BaseModel):
    events: list[ChatAuditEvent]
    total: int
