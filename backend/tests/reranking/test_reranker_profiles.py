from backend.app.core.config import Settings
from backend.app.reranking.profiles import get_default_reranker_profile


def test_default_reranker_profile이_BGE_기본값을_사용한다(monkeypatch) -> None:
    monkeypatch.delenv("RERANKER_BASE_URL", raising=False)
    monkeypatch.delenv("RERANKER_MODEL", raising=False)
    monkeypatch.delenv("RERANKER_API_KEY", raising=False)

    profile = get_default_reranker_profile(Settings())

    assert profile.provider == "bge"
    assert profile.base_url == "http://reranker:8001/v1"
    assert profile.model == "BAAI/bge-reranker-v2-m3"
    assert profile.api_key is None
    assert profile.timeout_seconds == 10.0


def test_default_reranker_profile이_환경변수_override를_반영한다(monkeypatch) -> None:
    monkeypatch.setenv("RERANKER_BASE_URL", "http://localhost:8101/v1/")
    monkeypatch.setenv("RERANKER_MODEL", "custom/reranker")
    monkeypatch.setenv("RERANKER_API_KEY", "local-secret")
    monkeypatch.setenv("RERANKER_TIMEOUT_SECONDS", "2.5")

    profile = get_default_reranker_profile(Settings())

    assert profile.base_url == "http://localhost:8101/v1"
    assert profile.model == "custom/reranker"
    assert profile.api_key == "local-secret"
    assert profile.timeout_seconds == 2.5
