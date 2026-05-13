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
    }
    values.update(overrides)
    return LLMProfile(**values)


def test_vllm_client_sends_openai_compatible_chat_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "model": "google/gemma-4-E4B-it",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "권한이 확인된 문서 기준 답변입니다.",
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

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = VLLMClient(profile=_profile(), http_client=http_client)

    response = client.generate(
        LLMRequest(
            messages=[ChatMessage(role="user", content="문서 내용을 요약해줘")],
            max_tokens=128,
            temperature=0.0,
        ),
    )

    assert captured["url"] == "http://llm:8000/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer local-secret"
    assert captured["payload"] == {
        "model": "google/gemma-4-E4B-it",
        "messages": [{"role": "user", "content": "문서 내용을 요약해줘"}],
        "max_tokens": 128,
        "temperature": 0.0,
    }
    assert response.content == "권한이 확인된 문서 기준 답변입니다."
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
            LLMRequest(messages=[ChatMessage(role="user", content="질문")]),
        )


def test_vllm_client_raises_provider_error_for_invalid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = VLLMClient(profile=_profile(), http_client=http_client)

    with pytest.raises(LLMProviderError, match="choices"):
        client.generate(
            LLMRequest(messages=[ChatMessage(role="user", content="질문")]),
        )
