from typing import Literal, Protocol

from pydantic import BaseModel, Field


MessageRole = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class LLMRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    max_tokens: int | None = None
    temperature: float | None = None


class LLMResponse(BaseModel):
    content: str
    model: str
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMProviderError(RuntimeError):
    pass


class LLMClient(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError
