"""
Hybrid Search Pipeline
하이브리드 검색 + 리랭킹 + RAG 파이프라인
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.config import settings
from .embedding import get_embedding_service
from .reranker import get_reranker_service
from .vector_store import get_vector_store


@dataclass
class SearchResult:
    """Search result with all metadata"""
    chunk_id: str
    doc_id: str
    text: str
    score: float
    source: str
    page: Optional[int] = None
    sheet: Optional[str] = None
    slide: Optional[int] = None
    chunk_index: int = 0
    heading: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchMetrics:
    """Search performance metrics"""
    embed_ms: float = 0.0
    search_ms: float = 0.0
    rerank_ms: float = 0.0
    total_ms: float = 0.0


class SearchPipeline:
    """
    Hybrid search pipeline with:
    - Dense + Sparse (BM25) retrieval
    - RRF fusion
    - Cross-encoder reranking
    - Access control filtering
    """
    
    def __init__(self):
        self.embedding = get_embedding_service()
        self.reranker = get_reranker_service()
        self.vector_store = get_vector_store()
    
    def search(
        self,
        query: str,
        top_k: int | None = None,
        top_n: int | None = None,
        use_rerank: bool | None = None,
        use_hybrid: bool | None = None,
        filter_params: dict | None = None,
        accessible_doc_ids: list[str] | None = None,
    ) -> tuple[list[SearchResult], SearchMetrics]:
        """
        Execute search pipeline
        
        Args:
            query: Search query
            top_k: Number of candidates for initial retrieval
            top_n: Number of final results after reranking
            use_rerank: Whether to use reranking
            use_hybrid: Whether to use hybrid search
            filter_params: Additional filter parameters
            accessible_doc_ids: List of document IDs user can access (None = no filter)
        
        Returns:
            Tuple of (results, metrics)
        """
        metrics = SearchMetrics()
        t_start = time.perf_counter()
        
        top_k = top_k or settings.retrieval_dense_top_k
        top_n = top_n or settings.retrieval_final_top_n
        use_rerank = use_rerank if use_rerank is not None else settings.retrieval_use_rerank
        use_hybrid = use_hybrid if use_hybrid is not None else settings.retrieval_use_hybrid
        
        # 1. Encode query
        t0 = time.perf_counter()
        query_vectors = self.embedding.encode_query(
            query,
            return_dense=True,
            return_sparse=use_hybrid,
        )
        metrics.embed_ms = (time.perf_counter() - t0) * 1000
        
        # 2. Build filters
        filter_conditions = None
        if filter_params or accessible_doc_ids:
            filter_params = filter_params or {}
            if accessible_doc_ids:
                filter_params["doc_ids"] = [str(d) for d in accessible_doc_ids]
            filter_conditions = self.vector_store.build_filter(**filter_params)
        
        # 3. Search
        t0 = time.perf_counter()
        if use_hybrid and "sparse" in query_vectors:
            raw_results = self.vector_store.search_hybrid(
                dense_vector=query_vectors["dense"],
                sparse_vector=query_vectors["sparse"],
                limit=top_k,
                filter_conditions=filter_conditions,
            )
        else:
            raw_results = self.vector_store.search_dense(
                vector=query_vectors["dense"],
                limit=top_k,
                filter_conditions=filter_conditions,
            )
        metrics.search_ms = (time.perf_counter() - t0) * 1000
        
        # 4. Rerank if enabled
        if use_rerank and raw_results:
            t0 = time.perf_counter()
            passages = [r["payload"].get("text", "") for r in raw_results]
            rerank_scores = self.reranker.rerank(query, passages)
            
            for r, score in zip(raw_results, rerank_scores):
                r["rerank_score"] = score
            
            raw_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            metrics.rerank_ms = (time.perf_counter() - t0) * 1000
        
        # 5. Take top_n and build results
        results = []
        for r in raw_results[:top_n]:
            payload = r["payload"]
            results.append(SearchResult(
                chunk_id=r["id"],
                doc_id=payload.get("doc_id", ""),
                text=payload.get("text", ""),
                score=r.get("rerank_score", r.get("score", 0)),
                source=payload.get("source", ""),
                page=payload.get("page"),
                sheet=payload.get("sheet"),
                slide=payload.get("slide"),
                chunk_index=payload.get("chunk_index", 0),
                heading=payload.get("heading"),
                metadata={
                    k: v for k, v in payload.items()
                    if k not in ("text", "doc_id", "source", "page", "sheet", "slide", "chunk_index", "heading")
                },
            ))
        
        metrics.total_ms = (time.perf_counter() - t_start) * 1000
        
        return results, metrics
    
    def multi_query_search(
        self,
        queries: list[str],
        top_k: int | None = None,
        top_n: int | None = None,
        **kwargs,
    ) -> tuple[list[SearchResult], SearchMetrics]:
        """
        Search with multiple queries (for query expansion)
        Merges results using RRF
        """
        all_results: dict[str, dict] = {}  # chunk_id -> result with rrf score
        total_metrics = SearchMetrics()
        
        for query in queries:
            results, metrics = self.search(
                query,
                top_k=top_k,
                top_n=top_k,  # Get more for merging
                use_rerank=False,  # Rerank after merge
                **kwargs,
            )
            
            # Accumulate metrics
            total_metrics.embed_ms += metrics.embed_ms
            total_metrics.search_ms += metrics.search_ms
            
            # RRF merge
            for rank, r in enumerate(results):
                chunk_id = r.chunk_id
                rrf_score = 1.0 / (settings.retrieval_rrf_k + rank + 1)
                
                if chunk_id in all_results:
                    all_results[chunk_id]["rrf_score"] += rrf_score
                else:
                    all_results[chunk_id] = {
                        "result": r,
                        "rrf_score": rrf_score,
                    }
        
        # Sort by RRF score
        merged = sorted(
            all_results.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )
        
        # Take top candidates for reranking
        top_n = top_n or settings.retrieval_final_top_n
        candidates = [m["result"] for m in merged[:top_k or 50]]
        
        # Rerank with first query
        if candidates and settings.retrieval_use_rerank:
            t0 = time.perf_counter()
            passages = [c.text for c in candidates]
            rerank_scores = self.reranker.rerank(queries[0], passages)
            
            for c, score in zip(candidates, rerank_scores):
                c.score = score
            
            candidates.sort(key=lambda x: x.score, reverse=True)
            total_metrics.rerank_ms = (time.perf_counter() - t0) * 1000
        
        return candidates[:top_n], total_metrics


# Search module exports
from .embedding import EmbeddingService, get_embedding_service
from .reranker import RerankerService, get_reranker_service
from .vector_store import VectorStore, get_vector_store

__all__ = [
    "SearchPipeline",
    "SearchResult",
    "SearchMetrics",
    "EmbeddingService",
    "get_embedding_service",
    "RerankerService",
    "get_reranker_service",
    "VectorStore",
    "get_vector_store",
]
