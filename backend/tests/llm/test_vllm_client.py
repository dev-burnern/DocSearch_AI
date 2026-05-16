import json

import httpx
import pytest

from backend.app.llm.base import ChatMessage, LLMProviderError, LLMRequest
from backend.app.llm.profiles import LLMProfile
from backend.app.llm.vllm_client import VLLMClient


def _profile(**overrides) -> LLMProfile:
    values = {
        "provider": "vllm",
        "base_url": "http://llm:8000/v1/",
        "model": "google/gemma-4-E4B-it",
        "api_key": "local-secret",
        "timeout_seconds": 5.0,
        "max_tokens": 512,
        "temperature": 0.1,
        "max_retries": 0,
        "retry_backoff_seconds": 0.0,
    }
    values.update(overrides)
    return LLMProfile(**values)


def _chat_response(content: str = "answer") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "google/gemma-4-E4B-it",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                },
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 7,
                "total_tokens": 19,
            },
        },
    )


def test_vllm_client_sends_openai_compatible_chat_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return _chat_response()

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = VLLMClient(profile=_profile(), http_client=http_client)

    response = client.generate(
        LLMRequest(
            messages=[ChatMessage(role="user", content="question")],
            max_tokens=128,
            temperature=0.0,
        ),
    )

    assert captured["url"] == "http://llm:8000/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer local-secret"
    assert captured["payload"] == {
        "model": "google/gemma-4-E4B-it",
        "messages": [{"role": "user", "content": "question"}],
        "max_tokens": 128,
        "temperature": 0.0,
    }
    assert response.content == "answer"
    assert response.model == "google/gemma-4-E4B-it"
    assert response.finish_reason == "stop"
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 7
    assert response.total_tokens == 19


def test_vllm_client_raises_provider_error_for_http_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "model loading"}})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = VLLMClient(profile=_profile(), http_client=http_client)

    with pytest.raises(LLMProviderError, match="vLLM"):
        client.generate(
            LLMRequest(messages=[ChatMessage(role="user", content="question")]),
        )


def test_vllm_client_raises_provider_error_for_invalid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = VLLMClient(profile=_profile(), http_client=http_client)

    with pytest.raises(LLMProviderError, match="choices"):
        client.generate(
            LLMRequest(messages=[ChatMessage(role="user", content="question")]),
        )


def test_vllm_client_retries_transient_http_failure() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": {"message": "model loading"}})
        return _chat_response(content="retried")

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = VLLMClient(
        profile=_profile(max_retries=1),
        http_client=http_client,
    )

    response = client.generate(
        LLMRequest(messages=[ChatMessage(role="user", content="question")]),
    )

    assert response.content == "retried"
    assert attempts == 2


def test_vllm_client_does_not_retry_validation_failure() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, json={"error": {"message": "bad request"}})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = VLLMClient(
        profile=_profile(max_retries=2),
        http_client=http_client,
    )

    with pytest.raises(LLMProviderError, match="HTTP 400"):
        client.generate(
            LLMRequest(messages=[ChatMessage(role="user", content="question")]),
        )

    assert attempts == 1


def test_vllm_client_retries_transport_errors() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("connection failed", request=request)
        return _chat_response(content="connected")

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = VLLMClient(
        profile=_profile(max_retries=1),
        http_client=http_client,
    )

    response = client.generate(
        LLMRequest(messages=[ChatMessage(role="user", content="question")]),
    )

    assert response.content == "connected"
    assert attempts == 2
