import pytest

from backend.app.auth.models import WorkspaceContext
from backend.app.chat.models import ChatRequest
from backend.app.chat.service import ChatContextNotFoundError, ChatService
from backend.app.llm.base import LLMRequest, LLMResponse
from backend.app.retrieval.filters import RetrievalFilter
from backend.app.retrieval.qdrant_store import RetrievedChunk


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks
        self.query_text: str | None = None
        self.filters: RetrievalFilter | None = None
        self.limit: int | None = None

    def retrieve(
        self,
        *,
        query_text: str,
        filters: RetrievalFilter,
        limit: int,
    ) -> list[RetrievedChunk]:
        self.query_text = query_text
        self.filters = filters
        self.limit = limit
        return self.chunks


class FakeLLMClient:
    def __init__(self) -> None:
        self.request: LLMRequest | None = None

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.request = request
        return LLMResponse(
            content="정책 문서 기준 답변입니다. [1]",
            model="google/gemma-4-E4B-it",
            finish_reason="stop",
            prompt_tokens=20,
            completion_tokens=8,
            total_tokens=28,
        )


def test_채팅_서비스가_검색_결과로_답변과_출처를_반환한다() -> None:
    chunk = RetrievedChunk(
        workspace_id="workspace-alpha",
        document_id="doc-1",
        filename="policy.md",
        parser="markdown",
        chunk_index=2,
        chunk_text="내부 보안 정책은 API Key와 권한 필터를 요구한다.",
        score=0.91,
    )
    retriever = FakeRetriever([chunk])
    llm_client = FakeLLMClient()
    service = ChatService(
        retriever=retriever,
        llm_client=llm_client,
        retrieval_limit=3,
    )

    response = service.answer(
        workspace_context=WorkspaceContext(
            request_id="request-1",
            workspace_id="workspace-alpha",
            workspace_name="Workspace Alpha",
        ),
        chat_request=ChatRequest(
            question="보안 정책 요약해줘",
            document_ids=["doc-1"],
        ),
    )

    assert retriever.query_text == "보안 정책 요약해줘"
    assert retriever.filters == RetrievalFilter(
        workspace_id="workspace-alpha",
        document_ids=["doc-1"],
    )
    assert retriever.limit == 3
    assert llm_client.request is not None
    assert llm_client.request.messages[0].role == "system"
    assert "허용된 문서 컨텍스트" in llm_client.request.messages[0].content
    assert llm_client.request.messages[1].role == "user"
    assert "[1] policy.md#2" in llm_client.request.messages[1].content
    assert "내부 보안 정책" in llm_client.request.messages[1].content

    assert response.answer == "정책 문서 기준 답변입니다. [1]"
    assert response.model == "google/gemma-4-E4B-it"
    assert response.usage.total_tokens == 28
    assert response.retrieved_chunk_count == 1
    assert response.citations[0].citation_id == 1
    assert response.citations[0].document_id == "doc-1"
    assert response.citations[0].filename == "policy.md"
    assert response.citations[0].chunk_index == 2
    assert response.citations[0].score == 0.91
    assert response.citations[0].snippet == "내부 보안 정책은 API Key와 권한 필터를 요구한다."


def test_채팅_서비스는_검색_결과가_없으면_컨텍스트_오류를_낸다() -> None:
    service = ChatService(
        retriever=FakeRetriever([]),
        llm_client=FakeLLMClient(),
        retrieval_limit=3,
    )

    with pytest.raises(ChatContextNotFoundError):
        service.answer(
            workspace_context=WorkspaceContext(
                request_id="request-1",
                workspace_id="workspace-alpha",
                workspace_name="Workspace Alpha",
            ),
            chat_request=ChatRequest(question="없는 문서 질문"),
        )
