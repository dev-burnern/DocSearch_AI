import hashlib
import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="DocSearch AI local stub")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None


class EmbeddingRequest(BaseModel):
    model: str
    input: str | list[str]


@app.get("/v1/models")
def list_models() -> dict[str, list[dict[str, str]]]:
    return {
        "data": [
            {"id": _llm_model(), "object": "model"},
            {"id": _embedding_model(), "object": "model"},
        ],
    }


@app.post("/v1/chat/completions")
def create_chat_completion(request: ChatCompletionRequest) -> dict[str, Any]:
    question = _extract_question(_last_user_message(request.messages))
    content = (
        "로컬 개발용 AI stub 응답입니다. 실제 모델 품질 검증이 아니라 "
        f"노트북 통합 테스트용 응답입니다. 질문: {question} [1]"
    )
    return {
        "id": "chatcmpl-local-stub",
        "object": "chat.completion",
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(question.split()),
            "completion_tokens": len(content.split()),
            "total_tokens": len(question.split()) + len(content.split()),
        },
    }


@app.post("/v1/embeddings")
def create_embedding(request: EmbeddingRequest) -> dict[str, Any]:
    inputs = [request.input] if isinstance(request.input, str) else request.input
    return {
        "object": "list",
        "model": request.model,
        "data": [
            {
                "object": "embedding",
                "index": index,
                "embedding": _embedding_vector(text),
            }
            for index, text in enumerate(inputs)
        ],
    }


def _last_user_message(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


def _extract_question(content: str) -> str:
    if not content.startswith("질문:\n"):
        return content

    question = content.removeprefix("질문:\n").split("\n\n문서 컨텍스트:", 1)[0]
    return question.strip()


def _embedding_vector(text: str) -> list[float]:
    vector_size = int(os.getenv("AI_STUB_EMBEDDING_VECTOR_SIZE", "8"))
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [round(digest[index % len(digest)] / 255, 6) for index in range(vector_size)]


def _llm_model() -> str:
    return os.getenv("AI_STUB_LLM_MODEL", "local-dev-llm")


def _embedding_model() -> str:
    return os.getenv("AI_STUB_EMBEDDING_MODEL", "local-dev-embedding")
