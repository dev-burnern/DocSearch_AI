from typing import Any

import httpx

from backend.app.reranking.base import (
    RerankRequest,
    RerankedChunk,
    RerankerProviderError,
)
from backend.app.reranking.profiles import RerankerProfile


class BGERerankerClient:
    def __init__(
        self,
        *,
        profile: RerankerProfile,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._profile = profile
        self._http_client = http_client or httpx.Client(timeout=profile.timeout_seconds)

    def rerank(self, request: RerankRequest) -> list[RerankedChunk]:
        if not request.chunks:
            return []

        payload = {
            "model": self._profile.model,
            "query": request.query,
            "documents": [chunk.chunk_text for chunk in request.chunks],
            "top_n": request.top_k,
        }

        try:
            response = self._http_client.post(
                f"{self._profile.base_url}/rerank",
                json=payload,
                headers=self._build_headers(),
                timeout=self._profile.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise RerankerProviderError(f"BGE reranker request failed: {exc}") from exc

        if response.status_code >= 400:
            raise RerankerProviderError(
                f"BGE reranker request failed with HTTP {response.status_code}: "
                f"{_extract_error_message(response)}",
            )

        try:
            response_body = response.json()
        except ValueError as exc:
            raise RerankerProviderError("BGE reranker response was not valid JSON") from exc

        return self._parse_response(response_body, request)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._profile.api_key:
            headers["Authorization"] = f"Bearer {self._profile.api_key}"
        return headers

    def _parse_response(
        self,
        response_body: dict[str, Any],
        request: RerankRequest,
    ) -> list[RerankedChunk]:
        results = response_body.get("results")
        if not isinstance(results, list):
            raise RerankerProviderError("BGE reranker response did not include results")

        reranked: list[RerankedChunk] = []
        used_indexes: set[int] = set()
        for item in results[: request.top_k]:
            if not isinstance(item, dict):
                raise RerankerProviderError("BGE reranker result item was invalid")

            index = item.get("index")
            score = item.get("relevance_score")
            if not isinstance(index, int) or index < 0 or index >= len(request.chunks):
                raise RerankerProviderError("BGE reranker result index was invalid")
            if index in used_indexes:
                raise RerankerProviderError("BGE reranker result index was duplicated")
            if not isinstance(score, int | float):
                raise RerankerProviderError(
                    "BGE reranker result relevance_score was invalid",
                )

            used_indexes.add(index)
            reranked.append(
                RerankedChunk(
                    chunk=request.chunks[index],
                    rerank_score=float(score),
                )
            )

        return reranked


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
