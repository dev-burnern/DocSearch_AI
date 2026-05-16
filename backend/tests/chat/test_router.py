from fastapi.testclient import TestClient
import pytest

from backend.app.chat.models import ChatCitation, ChatRequest, ChatResponse, ChatUsage
from backend.app.core.config import get_settings
from backend.app.indexing.embedder import EmbeddingProviderError
from backend.app.main import create_app


class FakeChatService:
    def __init__(self) -> None:
        self.workspace_id: str | None = None
        self.chat_request: ChatRequest | None = None

    def answer(self, *, workspace_context, chat_request: ChatRequest) -> ChatResponse:
        self.workspace_id = workspace_context.workspace_id
        self.chat_request = chat_request
        return ChatResponse(
            answer="권한이 확인된 문서 기준 답변입니다. [1]",
            model="google/gemma-4-E4B-it",
            citations=[
                ChatCitation(
                    citation_id=1,
                    document_id="doc-1",
                    filename="policy.md",
                    security_level="internal",
                    chunk_index=0,
                    score=0.88,
                    snippet="문서 일부",
                )
            ],
            usage=ChatUsage(
                prompt_tokens=10,
                completion_tokens=6,
                total_tokens=16,
            ),
            retrieved_chunk_count=1,
        )


class FailingChatService:
    def answer(self, *, workspace_context, chat_request: ChatRequest) -> ChatResponse:
        raise EmbeddingProviderError("embedding unavailable")


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_채팅_API가_워크스페이스_인증_후_답변을_반환한다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    from backend.app.chat.router import get_chat_service

    fake_service = FakeChatService()
    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: fake_service
    client = TestClient(app)

    response = client.post(
        "/v1/chat",
        headers={"X-API-Key": "local-dev-key"},
        json={
            "question": "정책 문서 요약해줘",
            "document_ids": ["doc-1"],
            "security_levels": ["internal"],
        },
    )

    assert response.status_code == 200
    assert fake_service.workspace_id == "workspace-alpha"
    assert fake_service.chat_request is not None
    assert fake_service.chat_request.question == "정책 문서 요약해줘"
    assert fake_service.chat_request.document_ids == ["doc-1"]
    assert fake_service.chat_request.security_levels == ["internal"]
    assert response.json() == {
        "answer": "권한이 확인된 문서 기준 답변입니다. [1]",
        "model": "google/gemma-4-E4B-it",
        "citations": [
            {
                "citation_id": 1,
                "document_id": "doc-1",
                "filename": "policy.md",
                "security_level": "internal",
                "chunk_index": 0,
                "score": 0.88,
                "snippet": "문서 일부",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 6,
            "total_tokens": 16,
        },
        "retrieved_chunk_count": 1,
    }


def test_member_chat_without_security_filter_is_scoped_to_allowed_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha|member",
    )

    from backend.app.chat.router import get_chat_service

    fake_service = FakeChatService()
    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: fake_service
    client = TestClient(app)

    response = client.post(
        "/v1/chat",
        headers={"X-API-Key": "local-dev-key"},
        json={"question": "정책 문서 요약해줘"},
    )

    assert response.status_code == 200
    assert fake_service.chat_request is not None
    assert fake_service.chat_request.security_levels == ["general", "internal"]


def test_member_chat_rejects_restricted_security_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha|member",
    )

    from backend.app.chat.router import get_chat_service

    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post(
        "/v1/chat",
        headers={"X-API-Key": "local-dev-key"},
        json={
            "question": "정책 문서 요약해줘",
            "security_levels": ["restricted"],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "DOCUMENT_SECURITY_FORBIDDEN"


def test_admin_chat_without_security_filter_keeps_unrestricted_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha|admin",
    )

    from backend.app.chat.router import get_chat_service

    fake_service = FakeChatService()
    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: fake_service
    client = TestClient(app)

    response = client.post(
        "/v1/chat",
        headers={"X-API-Key": "local-dev-key"},
        json={"question": "정책 문서 요약해줘"},
    )

    assert response.status_code == 200
    assert fake_service.chat_request is not None
    assert fake_service.chat_request.security_levels is None


def test_채팅_API는_API_Key가_없으면_거부한다() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/v1/chat",
        json={"question": "정책 문서 요약해줘"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_MISSING_CREDENTIALS"


def test_chat_api_returns_502_when_embedding_backend_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    from backend.app.chat.router import get_chat_service

    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: FailingChatService()
    client = TestClient(app)

    response = client.post(
        "/v1/chat",
        headers={"X-API-Key": "local-dev-key"},
        json={"question": "question"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "CHAT_EMBEDDING_UNAVAILABLE",
        "message": "embedding unavailable",
    }
