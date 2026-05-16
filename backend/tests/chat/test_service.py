from backend.app.audit.models import ChatAuditEvent
from backend.app.auth.models import WorkspaceContext
from backend.app.chat.models import ChatRequest
from backend.app.chat.service import ChatService
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
    def __init__(
        self,
        *,
        content: str = "정책 문서 기준 답변입니다. [1]",
    ) -> None:
        self.content = content
        self.request: LLMRequest | None = None

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.request = request
        return LLMResponse(
            content=self.content,
            model="google/gemma-4-E4B-it",
            finish_reason="stop",
            prompt_tokens=20,
            completion_tokens=8,
            total_tokens=28,
        )


class FakeReranker:
    def __init__(
        self,
        document_order: list[str],
        *,
        rerank_scores: dict[str, float] | None = None,
    ) -> None:
        self.document_order = document_order
        self.rerank_scores = rerank_scores or {}
        self.request: RerankRequest | None = None

    def rerank(self, request: RerankRequest) -> list[RerankedChunk]:
        self.request = request
        by_document_id = {chunk.document_id: chunk for chunk in request.chunks}
        return [
            RerankedChunk(
                chunk=by_document_id[document_id],
                rerank_score=self.rerank_scores.get(
                    document_id,
                    1.0 - (index * 0.1),
                ),
            )
            for index, document_id in enumerate(self.document_order)
        ]


class FakeAuditLog:
    def __init__(self) -> None:
        self.events: list[ChatAuditEvent] = []

    def record_chat_event(self, event: ChatAuditEvent) -> None:
        self.events.append(event)


def test_chat_service_answers_with_reranked_citations() -> None:
    chunk = _chunk(
        document_id="doc-1",
        filename="policy.md",
        chunk_index=2,
        text="내부 보안 정책은 API Key와 권한 필터를 요구한다.",
        score=0.91,
    )
    retriever = FakeRetriever([chunk])
    reranker = FakeReranker(["doc-1"])
    llm_client = FakeLLMClient()
    audit_log = FakeAuditLog()
    service = _service(
        retriever=retriever,
        reranker=reranker,
        llm_client=llm_client,
        audit_log=audit_log,
        retrieval_limit=3,
        rerank_top_k=3,
    )

    response = service.answer(
        workspace_context=_workspace_context(),
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
    assert response.citations[0].snippet == (
        "내부 보안 정책은 API Key와 권한 필터를 요구한다."
    )

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


def test_chat_service_uses_reranker_order() -> None:
    chunks = [
        _chunk(
            document_id="doc-a",
            filename="a.md",
            chunk_index=0,
            text="일반 보안 정책",
            score=0.9,
        ),
        _chunk(
            document_id="doc-b",
            filename="b.md",
            chunk_index=1,
            text="API Key 권한 정책",
            score=0.7,
        ),
    ]
    llm_client = FakeLLMClient(content="두 문서를 모두 참고했습니다. [1] [2]")
    service = _service(
        retriever=FakeRetriever(chunks),
        reranker=FakeReranker(["doc-b", "doc-a"]),
        llm_client=llm_client,
        audit_log=FakeAuditLog(),
        retrieval_limit=5,
        rerank_top_k=2,
    )

    response = service.answer(
        workspace_context=_workspace_context(),
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


def test_chat_service_returns_only_answer_referenced_citations() -> None:
    chunks = [
        _chunk(
            document_id="doc-a",
            filename="a.md",
            chunk_index=0,
            text="일반 보안 정책",
            score=0.9,
        ),
        _chunk(
            document_id="doc-b",
            filename="b.md",
            chunk_index=1,
            text="API Key 권한 정책",
            score=0.8,
        ),
    ]
    audit_log = FakeAuditLog()
    service = _service(
        retriever=FakeRetriever(chunks),
        reranker=FakeReranker(["doc-a", "doc-b"]),
        llm_client=FakeLLMClient(
            content="두 번째 근거만 답변에 사용합니다. [2] [2] [99] [0]"
        ),
        audit_log=audit_log,
        retrieval_limit=5,
        rerank_top_k=2,
    )

    response = service.answer(
        workspace_context=_workspace_context(),
        chat_request=ChatRequest(question="API Key 권한은?"),
    )

    assert response.retrieved_chunk_count == 2
    assert [citation.citation_id for citation in response.citations] == [2]
    assert [citation.document_id for citation in response.citations] == ["doc-b"]
    assert [citation.citation_id for citation in audit_log.events[0].citations] == [2]
    assert [citation.document_id for citation in audit_log.events[0].citations] == [
        "doc-b"
    ]


def test_chat_service_filters_low_relevance_chunks() -> None:
    chunks = [
        _chunk(
            document_id="doc-a",
            filename="a.md",
            chunk_index=0,
            text="관련 없는 공지",
            score=0.7,
        ),
        _chunk(
            document_id="doc-b",
            filename="b.md",
            chunk_index=1,
            text="API Key 권한 정책",
            score=0.8,
        ),
    ]
    llm_client = FakeLLMClient()
    service = _service(
        retriever=FakeRetriever(chunks),
        reranker=FakeReranker(
            ["doc-a", "doc-b"],
            rerank_scores={"doc-a": 0.1, "doc-b": 0.8},
        ),
        llm_client=llm_client,
        audit_log=FakeAuditLog(),
        retrieval_limit=5,
        rerank_top_k=2,
        min_relevance_score=0.5,
    )

    response = service.answer(
        workspace_context=_workspace_context(),
        chat_request=ChatRequest(question="API Key 권한은?"),
    )

    assert llm_client.request is not None
    user_prompt = llm_client.request.messages[1].content
    assert "[1] b.md#1" in user_prompt
    assert "관련 없는 공지" not in user_prompt
    assert [citation.document_id for citation in response.citations] == ["doc-b"]
    assert response.retrieved_chunk_count == 1


def test_chat_service_returns_no_answer_without_chunks() -> None:
    llm_client = FakeLLMClient()
    audit_log = FakeAuditLog()
    service = _service(
        retriever=FakeRetriever([]),
        reranker=FakeReranker([]),
        llm_client=llm_client,
        audit_log=audit_log,
        retrieval_limit=3,
        rerank_top_k=3,
    )

    response = service.answer(
        workspace_context=_workspace_context(),
        chat_request=ChatRequest(question="없는 문서 질문"),
    )

    assert llm_client.request is None
    assert response.answer == "모르겠습니다. 제공된 문서에서 답변 근거를 찾지 못했습니다."
    assert response.model == "grounding-policy"
    assert response.citations == []
    assert response.retrieved_chunk_count == 0
    assert audit_log.events[0].model == "grounding-policy"
    assert audit_log.events[0].citations == []


def test_chat_service_returns_no_answer_when_relevance_is_too_low() -> None:
    chunk = _chunk(
        document_id="doc-1",
        filename="policy.md",
        chunk_index=0,
        text="관련도가 낮은 문서",
        score=0.1,
    )
    llm_client = FakeLLMClient()
    service = _service(
        retriever=FakeRetriever([chunk]),
        reranker=FakeReranker(["doc-1"], rerank_scores={"doc-1": 0.1}),
        llm_client=llm_client,
        audit_log=FakeAuditLog(),
        retrieval_limit=3,
        rerank_top_k=3,
        min_relevance_score=0.5,
    )

    response = service.answer(
        workspace_context=_workspace_context(),
        chat_request=ChatRequest(question="정책 알려줘"),
    )

    assert llm_client.request is None
    assert response.answer == "모르겠습니다. 제공된 문서에서 답변 근거를 찾지 못했습니다."
    assert response.citations == []
    assert response.retrieved_chunk_count == 0


def _service(
    *,
    retriever: FakeRetriever,
    reranker: FakeReranker,
    llm_client: FakeLLMClient,
    audit_log: FakeAuditLog,
    retrieval_limit: int,
    rerank_top_k: int,
    min_relevance_score: float = 0.2,
) -> ChatService:
    return ChatService(
        retriever=retriever,
        reranker=reranker,
        llm_client=llm_client,
        audit_log=audit_log,
        retrieval_limit=retrieval_limit,
        rerank_top_k=rerank_top_k,
        min_relevance_score=min_relevance_score,
    )


def _workspace_context() -> WorkspaceContext:
    return WorkspaceContext(
        request_id="request-1",
        workspace_id="workspace-alpha",
        workspace_name="Workspace Alpha",
    )


def _chunk(
    *,
    document_id: str,
    filename: str,
    chunk_index: int,
    text: str,
    score: float,
) -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="workspace-alpha",
        document_id=document_id,
        filename=filename,
        parser="markdown",
        chunk_index=chunk_index,
        chunk_text=text,
        score=score,
    )
