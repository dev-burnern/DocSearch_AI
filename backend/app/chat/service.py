from typing import Protocol

from backend.app.auth.models import WorkspaceContext
from backend.app.chat.models import (
    ChatCitation,
    ChatRequest,
    ChatResponse,
    ChatUsage,
)
from backend.app.llm.base import ChatMessage, LLMClient, LLMRequest
from backend.app.retrieval.filters import RetrievalFilter
from backend.app.retrieval.qdrant_store import RetrievedChunk


SYSTEM_PROMPT = (
    "허용된 문서 컨텍스트만 사용해서 한국어로 답변하세요. "
    "컨텍스트에 없는 내용은 모른다고 답하고, 답변에는 [1] 형식의 출처 번호를 포함하세요."
)


class Retriever(Protocol):
    def retrieve(
        self,
        *,
        query_text: str,
        filters: RetrievalFilter,
        limit: int,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


class ChatContextNotFoundError(RuntimeError):
    pass


class ChatService:
    def __init__(
        self,
        *,
        retriever: Retriever,
        llm_client: LLMClient,
        retrieval_limit: int,
    ) -> None:
        self._retriever = retriever
        self._llm_client = llm_client
        self._retrieval_limit = retrieval_limit

    def answer(
        self,
        *,
        workspace_context: WorkspaceContext,
        chat_request: ChatRequest,
    ) -> ChatResponse:
        chunks = self._retriever.retrieve(
            query_text=chat_request.question,
            filters=RetrievalFilter(
                workspace_id=workspace_context.workspace_id,
                document_ids=chat_request.document_ids,
            ),
            limit=chat_request.top_k or self._retrieval_limit,
        )
        if not chunks:
            raise ChatContextNotFoundError("질문에 사용할 수 있는 문서 컨텍스트가 없습니다.")

        llm_response = self._llm_client.generate(
            LLMRequest(
                messages=[
                    ChatMessage(role="system", content=SYSTEM_PROMPT),
                    ChatMessage(
                        role="user",
                        content=_build_user_prompt(
                            question=chat_request.question,
                            chunks=chunks,
                        ),
                    ),
                ],
            )
        )

        return ChatResponse(
            answer=llm_response.content,
            model=llm_response.model,
            citations=_build_citations(chunks),
            usage=ChatUsage(
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                total_tokens=llm_response.total_tokens,
            ),
            retrieved_chunk_count=len(chunks),
        )


def _build_user_prompt(*, question: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(
        f"[{index}] {chunk.filename}#{chunk.chunk_index}\n{chunk.chunk_text}"
        for index, chunk in enumerate(chunks, start=1)
    )
    return (
        f"질문:\n{question}\n\n"
        f"문서 컨텍스트:\n{context}\n\n"
        "위 컨텍스트만 근거로 답변하고, 문장 끝에 관련 출처 번호를 붙이세요."
    )


def _build_citations(chunks: list[RetrievedChunk]) -> list[ChatCitation]:
    return [
        ChatCitation(
            citation_id=index,
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            score=chunk.score,
            snippet=_build_snippet(chunk.chunk_text),
        )
        for index, chunk in enumerate(chunks, start=1)
    ]


def _build_snippet(chunk_text: str) -> str:
    normalized = " ".join(chunk_text.split())
    if len(normalized) <= 240:
        return normalized
    return f"{normalized[:237]}..."
