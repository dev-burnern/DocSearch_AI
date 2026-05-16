from backend.app.core.config import Settings
from backend.app.llm.profiles import get_default_llm_profile


def test_default_llm_profile_uses_vllm_gemma_defaults(monkeypatch) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MAX_RETRIES", raising=False)
    monkeypatch.delenv("LLM_RETRY_BACKOFF_SECONDS", raising=False)

    profile = get_default_llm_profile(Settings())

    assert profile.provider == "vllm"
    assert profile.base_url == "http://llm:8000/v1"
    assert profile.model == "google/gemma-4-E4B-it"
    assert profile.api_key is None
    assert profile.timeout_seconds == 30.0
    assert profile.max_tokens == 1024
    assert profile.temperature == 0.2
    assert profile.max_retries == 2
    assert profile.retry_backoff_seconds == 0.5


def test_default_llm_profile_uses_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:8100/v1/")
    monkeypatch.setenv("LLM_MODEL", "custom/model")
    monkeypatch.setenv("LLM_API_KEY", "local-secret")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("LLM_MAX_TOKENS", "256")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.05")
    monkeypatch.setenv("LLM_MAX_RETRIES", "4")
    monkeypatch.setenv("LLM_RETRY_BACKOFF_SECONDS", "0.25")

    profile = get_default_llm_profile(Settings())

    assert profile.base_url == "http://localhost:8100/v1"
    assert profile.model == "custom/model"
    assert profile.api_key == "local-secret"
    assert profile.timeout_seconds == 12.5
    assert profile.max_tokens == 256
    assert profile.temperature == 0.05
    assert profile.max_retries == 4
    assert profile.retry_backoff_seconds == 0.25
