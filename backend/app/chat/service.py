from typing import Protocol

from backend.app.audit.models import AuditCitation, ChatAuditEvent
from backend.app.audit.store import AuditLogStore
from backend.app.auth.models import WorkspaceContext
from backend.app.chat.models import (
    ChatCitation,
    ChatRequest,
    ChatResponse,
    ChatUsage,
)
from backend.app.llm.base import ChatMessage, LLMClient, LLMRequest
from backend.app.reranking.base import RerankRequest, RerankedChunk, Reranker
from backend.app.retrieval.filters import RetrievalFilter
from backend.app.retrieval.qdrant_store import RetrievedChunk


SYSTEM_PROMPT = (
    "허용된 문서 컨텍스트만 사용해서 한국어로 답하세요. "
    "컨텍스트에 없는 내용은 모른다고 답하고, 답변에는 [1] 형식의 출처 번호를 포함하세요."
)
NO_ANSWER_MESSAGE = "모르겠습니다. 제공된 문서에서 답변 근거를 찾지 못했습니다."
NO_ANSWER_MODEL = "grounding-policy"


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
        reranker: Reranker,
        llm_client: LLMClient,
        audit_log: AuditLogStore,
        retrieval_limit: int,
        rerank_top_k: int,
        min_relevance_score: float = 0.2,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._llm_client = llm_client
        self._audit_log = audit_log
        self._retrieval_limit = retrieval_limit
        self._rerank_top_k = rerank_top_k
        self._min_relevance_score = min_relevance_score

    def answer(
        self,
        *,
        workspace_context: WorkspaceContext,
        chat_request: ChatRequest,
    ) -> ChatResponse:
        final_top_k = chat_request.top_k or self._rerank_top_k
        retrieval_limit = max(self._retrieval_limit, final_top_k)
        chunks = self._retriever.retrieve(
            query_text=chat_request.question,
            filters=RetrievalFilter(
                workspace_id=workspace_context.workspace_id,
                document_ids=chat_request.document_ids,
            ),
            limit=retrieval_limit,
        )
        if not chunks:
            return self._no_answer(
                workspace_context=workspace_context,
                chat_request=chat_request,
                retrieval_limit=retrieval_limit,
                rerank_top_k=final_top_k,
            )

        reranked_chunks = self._reranker.rerank(
            RerankRequest(
                query=chat_request.question,
                chunks=chunks,
                top_k=final_top_k,
            )
        )
        supported_chunks = _filter_supported_chunks(
            reranked_chunks,
            min_relevance_score=self._min_relevance_score,
        )
        if not supported_chunks:
            return self._no_answer(
                workspace_context=workspace_context,
                chat_request=chat_request,
                retrieval_limit=retrieval_limit,
                rerank_top_k=final_top_k,
            )

        llm_response = self._llm_client.generate(
            LLMRequest(
                messages=[
                    ChatMessage(role="system", content=SYSTEM_PROMPT),
                    ChatMessage(
                        role="user",
                        content=_build_user_prompt(
                            question=chat_request.question,
                            chunks=[item.chunk for item in supported_chunks],
                        ),
                    ),
                ],
            )
        )

        response = ChatResponse(
            answer=llm_response.content,
            model=llm_response.model,
            citations=_build_citations(supported_chunks),
            usage=ChatUsage(
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                total_tokens=llm_response.total_tokens,
            ),
            retrieved_chunk_count=len(supported_chunks),
        )
        self._record_audit_event(
            workspace_context=workspace_context,
            chat_request=chat_request,
            response=response,
            retrieval_limit=retrieval_limit,
            rerank_top_k=final_top_k,
        )
        return response

    def _no_answer(
        self,
        *,
        workspace_context: WorkspaceContext,
        chat_request: ChatRequest,
        retrieval_limit: int,
        rerank_top_k: int,
    ) -> ChatResponse:
        response = ChatResponse(
            answer=NO_ANSWER_MESSAGE,
            model=NO_ANSWER_MODEL,
            citations=[],
            usage=ChatUsage(),
            retrieved_chunk_count=0,
        )
        self._record_audit_event(
            workspace_context=workspace_context,
            chat_request=chat_request,
            response=response,
            retrieval_limit=retrieval_limit,
            rerank_top_k=rerank_top_k,
        )
        return response

    def _record_audit_event(
        self,
        *,
        workspace_context: WorkspaceContext,
        chat_request: ChatRequest,
        response: ChatResponse,
        retrieval_limit: int,
        rerank_top_k: int,
    ) -> None:
        self._audit_log.record_chat_event(
            ChatAuditEvent(
                request_id=workspace_context.request_id,
                workspace_id=workspace_context.workspace_id,
                workspace_name=workspace_context.workspace_name,
                question=chat_request.question,
                document_ids=chat_request.document_ids,
                retrieval_limit=retrieval_limit,
                rerank_top_k=rerank_top_k,
                retrieved_chunk_count=response.retrieved_chunk_count,
                model=response.model,
                answer_preview=_build_answer_preview(response.answer),
                answer_character_count=len(response.answer),
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                citations=[
                    AuditCitation(
                        citation_id=citation.citation_id,
                        document_id=citation.document_id,
                        filename=citation.filename,
                        chunk_index=citation.chunk_index,
                        score=citation.score,
                        rerank_score=citation.rerank_score,
                    )
                    for citation in response.citations
                ],
            )
        )


def _build_user_prompt(*, question: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(
        f"[{index}] {chunk.filename}#{chunk.chunk_index}\n{chunk.chunk_text}"
        for index, chunk in enumerate(chunks, start=1)
    )
    return (
        f"질문:\n{question}\n\n"
        f"문서 컨텍스트:\n{context}\n\n"
        "위 컨텍스트만 근거로 답하고, 문장 끝에 관련 출처 번호를 붙이세요."
    )


def _build_citations(chunks: list[RerankedChunk]) -> list[ChatCitation]:
    return [
        ChatCitation(
            citation_id=index,
            document_id=item.chunk.document_id,
            filename=item.chunk.filename,
            chunk_index=item.chunk.chunk_index,
            score=item.chunk.score,
            rerank_score=item.rerank_score,
            snippet=_build_snippet(item.chunk.chunk_text),
        )
        for index, item in enumerate(chunks, start=1)
    ]


def _filter_supported_chunks(
    chunks: list[RerankedChunk],
    *,
    min_relevance_score: float,
) -> list[RerankedChunk]:
    return [
        item
        for item in chunks
        if _relevance_score(item) >= min_relevance_score
    ]


def _relevance_score(item: RerankedChunk) -> float:
    return item.rerank_score if item.rerank_score is not None else item.chunk.score


def _build_snippet(chunk_text: str) -> str:
    normalized = " ".join(chunk_text.split())
    if len(normalized) <= 240:
        return normalized
    return f"{normalized[:237]}..."


def _build_answer_preview(answer: str) -> str:
    normalized = " ".join(answer.split())
    if len(normalized) <= 500:
        return normalized
    return f"{normalized[:497]}..."
