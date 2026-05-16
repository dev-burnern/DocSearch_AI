from backend.app.reranking.base import (
    RerankRequest,
    RerankedChunk,
    ScorePreservingReranker,
)
from backend.app.retrieval.qdrant_store import RetrievedChunk


def _chunk(document_id: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        workspace_id="workspace-alpha",
        document_id=document_id,
        filename=f"{document_id}.md",
        parser="markdown",
        chunk_index=0,
        chunk_text=f"{document_id} content",
        score=score,
    )


def test_score_preserving_reranker_정렬된_검색_결과를_top_k까지_유지한다() -> None:
    reranker = ScorePreservingReranker()

    result = reranker.rerank(
        RerankRequest(
            query="보안 정책",
            chunks=[
                _chunk("doc-a", 0.8),
                _chunk("doc-b", 0.7),
                _chunk("doc-c", 0.6),
            ],
            top_k=2,
        )
    )

    assert result == [
        RerankedChunk(chunk=_chunk("doc-a", 0.8), rerank_score=0.8),
        RerankedChunk(chunk=_chunk("doc-b", 0.7), rerank_score=0.7),
    ]
