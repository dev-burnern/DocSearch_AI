import hashlib
from typing import Any, Protocol

import httpx

from backend.app.indexing.embedding_profiles import EmbeddingProfile


class Embedder(Protocol):
    @property
    def vector_size(self) -> int:
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class EmbeddingProviderError(Exception):
    pass


class DeterministicEmbedder:
    def __init__(self, *, vector_size: int) -> None:
        if vector_size <= 0:
            raise ValueError("vector_size must be positive.")
        self._vector_size = vector_size

    @property
    def vector_size(self) -> int:
        return self._vector_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = [round(byte / 255, 6) for byte in digest[: self._vector_size]]
            vectors.append(vector)
        return vectors


class BGEEmbeddingClient:
    def __init__(
        self,
        *,
        profile: EmbeddingProfile,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._profile = profile
        self._http_client = http_client or httpx.Client(
            timeout=profile.timeout_seconds,
        )

    @property
    def vector_size(self) -> int:
        return self._profile.vector_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            response = self._http_client.post(
                f"{self._profile.base_url}/embeddings",
                json={
                    "model": self._profile.model,
                    "input": texts,
                },
                headers=self._build_headers(),
                timeout=self._profile.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(f"BGE embedding request failed: {exc}") from exc

        if response.status_code >= 400:
            raise EmbeddingProviderError(
                f"BGE embedding request failed with HTTP {response.status_code}: "
                f"{_extract_error_message(response)}",
            )

        try:
            response_body = response.json()
        except ValueError as exc:
            raise EmbeddingProviderError(
                "BGE embedding response was not valid JSON",
            ) from exc

        return _parse_embedding_response(
            response_body,
            expected_count=len(texts),
            vector_size=self._profile.vector_size,
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._profile.api_key:
            headers["Authorization"] = f"Bearer {self._profile.api_key}"
        return headers


def _parse_embedding_response(
    response_body: dict[str, Any],
    *,
    expected_count: int,
    vector_size: int,
) -> list[list[float]]:
    data = response_body.get("data")
    if not isinstance(data, list) or len(data) != expected_count:
        raise EmbeddingProviderError("BGE embedding response data was invalid")

    vectors: list[list[float] | None] = [None] * expected_count
    for item in data:
        if not isinstance(item, dict):
            raise EmbeddingProviderError("BGE embedding response item was invalid")

        index = item.get("index")
        if not isinstance(index, int) or index < 0 or index >= expected_count:
            raise EmbeddingProviderError("BGE embedding response index was invalid")

        if vectors[index] is not None:
            raise EmbeddingProviderError("BGE embedding response index was duplicated")

        embedding = item.get("embedding")
        if not isinstance(embedding, list) or len(embedding) != vector_size:
            raise EmbeddingProviderError("BGE embedding vector size was invalid")

        vector: list[float] = []
        for value in embedding:
            if not isinstance(value, int | float):
                raise EmbeddingProviderError("BGE embedding vector value was invalid")
            vector.append(float(value))
        vectors[index] = vector

    if any(vector is None for vector in vectors):
        raise EmbeddingProviderError("BGE embedding response data was incomplete")

    return [vector for vector in vectors if vector is not None]


def _extract_error_message(response: httpx.Response) -> str:
    try:
        response_body = response.json()
    except ValueError:
        return response.text

    if isinstance(response_body, dict):
        error = response_body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
        if isinstance(error, str):
            return error

    return response.text
