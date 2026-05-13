from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class ChatCitation(BaseModel):
    citation_id: int
    document_id: str
    filename: str
    chunk_index: int
    score: float
    snippet: str


class ChatUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ChatResponse(BaseModel):
    answer: str
    model: str
    citations: list[ChatCitation]
    usage: ChatUsage
    retrieved_chunk_count: int
