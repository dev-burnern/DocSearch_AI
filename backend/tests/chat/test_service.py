import pytest

from backend.app.audit.models import ChatAuditEvent
from backend.app.auth.models import WorkspaceContext
from backend.app.chat.models import ChatRequest
from backend.app.chat.service import ChatContextNotFoundError, ChatService
from backend.app.llm.base import LLMRequest, LLMResponse
from backend.app.reranking.base import RerankRequest, RerankedChunk
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


class FakeReranker:
    def __init__(self, document_order: list[str]) -> None:
        self.document_order = document_order
        self.request: RerankRequest | None = None

    def rerank(self, request: RerankRequest) -> list[RerankedChunk]:
        self.request = request
        by_document_id = {chunk.document_id: chunk for chunk in request.chunks}
        return [
            RerankedChunk(
                chunk=by_document_id[document_id],
                rerank_score=1.0 - (index * 0.1),
            )
            for index, document_id in enumerate(self.document_order)
        ]


class FakeAuditLog:
    def __init__(self) -> None:
        self.events: list[ChatAuditEvent] = []

    def record_chat_event(self, event: ChatAuditEvent) -> None:
        self.events.append(event)


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
    reranker = FakeReranker(["doc-1"])
    llm_client = FakeLLMClient()
    audit_log = FakeAuditLog()
    service = ChatService(
        retriever=retriever,
        reranker=reranker,
        llm_client=llm_client,
        audit_log=audit_log,
        retrieval_limit=3,
        rerank_top_k=3,
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
    assert reranker.request is not None
    assert reranker.request.query == "보안 정책 요약해줘"
    assert reranker.request.top_k == 3
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
    assert response.citations[0].rerank_score == 1.0
    assert response.citations[0].snippet == "내부 보안 정책은 API Key와 권한 필터를 요구한다."

    assert len(audit_log.events) == 1
    event = audit_log.events[0]
    assert event.request_id == "request-1"
    assert event.workspace_id == "workspace-alpha"
    assert event.workspace_name == "Workspace Alpha"
    assert event.question == "보안 정책 요약해줘"
    assert event.document_ids == ["doc-1"]
    assert event.retrieval_limit == 3
    assert event.rerank_top_k == 3
    assert event.retrieved_chunk_count == 1
    assert event.model == "google/gemma-4-E4B-it"
    assert event.answer_preview == "정책 문서 기준 답변입니다. [1]"
    assert event.answer_character_count == len("정책 문서 기준 답변입니다. [1]")
    assert event.total_tokens == 28
    assert event.citations[0].document_id == "doc-1"
    assert event.citations[0].rerank_score == 1.0


def test_채팅_서비스가_리랭커_순서대로_컨텍스트와_출처를_구성한다() -> None:
    chunks = [
        RetrievedChunk(
            workspace_id="workspace-alpha",
            document_id="doc-a",
            filename="a.md",
            parser="markdown",
            chunk_index=0,
            chunk_text="일반 보안 정책",
            score=0.9,
        ),
        RetrievedChunk(
            workspace_id="workspace-alpha",
            document_id="doc-b",
            filename="b.md",
            parser="markdown",
            chunk_index=1,
            chunk_text="API Key 권한 정책",
            score=0.7,
        ),
    ]
    llm_client = FakeLLMClient()
    service = ChatService(
        retriever=FakeRetriever(chunks),
        reranker=FakeReranker(["doc-b", "doc-a"]),
        llm_client=llm_client,
        audit_log=FakeAuditLog(),
        retrieval_limit=5,
        rerank_top_k=2,
    )

    response = service.answer(
        workspace_context=WorkspaceContext(
            request_id="request-1",
            workspace_id="workspace-alpha",
            workspace_name="Workspace Alpha",
        ),
        chat_request=ChatRequest(question="API Key 권한은?"),
    )

    assert llm_client.request is not None
    user_prompt = llm_client.request.messages[1].content
    assert user_prompt.index("[1] b.md#1") < user_prompt.index("[2] a.md#0")
    assert [citation.document_id for citation in response.citations] == [
        "doc-b",
        "doc-a",
    ]
    assert [citation.rerank_score for citation in response.citations] == [1.0, 0.9]


def test_채팅_서비스는_검색_결과가_없으면_컨텍스트_오류를_낸다() -> None:
    service = ChatService(
        retriever=FakeRetriever([]),
        reranker=FakeReranker([]),
        llm_client=FakeLLMClient(),
        audit_log=FakeAuditLog(),
        retrieval_limit=3,
        rerank_top_k=3,
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
