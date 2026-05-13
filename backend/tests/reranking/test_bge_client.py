import json

import httpx
import pytest

from backend.app.reranking.base import RerankRequest, RerankerProviderError
from backend.app.reranking.bge_client import BGERerankerClient
from backend.app.reranking.profiles import RerankerProfile
from backend.app.retrieval.qdrant_store import RetrievedChunk


def _profile(**overrides) -> RerankerProfile:
    values = {
        "provider": "bge",
        "base_url": "http://reranker:8001/v1/",
        "model": "BAAI/bge-reranker-v2-m3",
        "api_key": "reranker-secret",
        "timeout_seconds": 3.0,
    }
    values.update(overrides)
    return RerankerProfile(**values)


def _chunk(document_id: str, text: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="workspace-alpha",
        document_id=document_id,
        filename=f"{document_id}.md",
        parser="markdown",
        chunk_index=0,
        chunk_text=text,
        score=score,
    )


def test_bge_reranker_client가_표준_rerank_요청을_보내고_점수순으로_반환한다() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 1, "relevance_score": 0.94},
                    {"index": 0, "relevance_score": 0.51},
                ]
            },
        )

    client = BGERerankerClient(
        profile=_profile(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    chunks = [
        _chunk("doc-a", "보안 정책 개요", 0.8),
        _chunk("doc-b", "API Key 권한 정책", 0.7),
    ]

    result = client.rerank(
        RerankRequest(
            query="API Key 권한은?",
            chunks=chunks,
            top_k=2,
        )
    )

    assert captured["url"] == "http://reranker:8001/v1/rerank"
    assert captured["headers"]["authorization"] == "Bearer reranker-secret"
    assert captured["payload"] == {
        "model": "BAAI/bge-reranker-v2-m3",
        "query": "API Key 권한은?",
        "documents": ["보안 정책 개요", "API Key 권한 정책"],
        "top_n": 2,
    }
    assert [item.chunk.document_id for item in result] == ["doc-b", "doc-a"]
    assert [item.rerank_score for item in result] == [0.94, 0.51]


def test_bge_reranker_client는_HTTP_실패를_provider_error로_변환한다() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "model loading"}})

    client = BGERerankerClient(
        profile=_profile(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(RerankerProviderError, match="BGE"):
        client.rerank(
            RerankRequest(
                query="질문",
                chunks=[_chunk("doc-a", "본문", 0.8)],
                top_k=1,
            )
        )


def test_bge_reranker_client는_잘못된_index를_거부한다() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"results": [{"index": 10, "relevance_score": 0.9}]},
        )

    client = BGERerankerClient(
        profile=_profile(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(RerankerProviderError, match="index"):
        client.rerank(
            RerankRequest(
                query="질문",
                chunks=[_chunk("doc-a", "본문", 0.8)],
                top_k=1,
            )
        )
