import json

import httpx
import pytest

from backend.app.indexing.embedder import BGEEmbeddingClient, EmbeddingProviderError
from backend.app.indexing.embedding_profiles import EmbeddingProfile


def _profile(**overrides) -> EmbeddingProfile:
    values = {
        "provider": "bge",
        "base_url": "http://embedding:8002/v1/",
        "model": "BAAI/bge-m3",
        "api_key": "local-secret",
        "timeout_seconds": 5.0,
        "vector_size": 3,
    }
    values.update(overrides)
    return EmbeddingProfile(**values)


def test_bge_embedding_client_sends_openai_compatible_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "model": "BAAI/bge-m3",
                "data": [
                    {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                ],
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = BGEEmbeddingClient(profile=_profile(), http_client=http_client)

    embeddings = client.embed_texts(["alpha", "beta"])

    assert captured["url"] == "http://embedding:8002/v1/embeddings"
    assert captured["headers"]["authorization"] == "Bearer local-secret"
    assert captured["payload"] == {
        "model": "BAAI/bge-m3",
        "input": ["alpha", "beta"],
    }
    assert embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert client.vector_size == 3


def test_bge_embedding_client_returns_empty_list_without_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("empty embedding request should not call backend")

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = BGEEmbeddingClient(profile=_profile(), http_client=http_client)

    assert client.embed_texts([]) == []


def test_bge_embedding_client_raises_provider_error_for_http_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "model loading"}})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = BGEEmbeddingClient(profile=_profile(), http_client=http_client)

    with pytest.raises(EmbeddingProviderError, match="HTTP 503"):
        client.embed_texts(["alpha"])


def test_bge_embedding_client_rejects_wrong_vector_size() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = BGEEmbeddingClient(profile=_profile(vector_size=3), http_client=http_client)

    with pytest.raises(EmbeddingProviderError, match="vector size"):
        client.embed_texts(["alpha"])
