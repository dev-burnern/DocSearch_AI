"""
Reranking Service
BGE-Reranker 기반 Cross-Encoder 리랭킹
"""
from __future__ import annotations

from app.core.config import settings


class RerankerService:
    """
    Reranking service using BGE-Reranker
    Cross-encoder for more accurate relevance scoring
    """
    
    def __init__(self):
        self._model = None
    
    @property
    def model(self):
        """Lazy load the reranker model"""
        if self._model is None:
            from FlagEmbedding import FlagReranker
            
            self._model = FlagReranker(
                settings.rerank_model,
                use_fp16=settings.rerank_use_fp16,
                device=settings.embed_device,
            )
        return self._model
    
    def rerank(
        self,
        query: str,
        passages: list[str],
        batch_size: int | None = None,
    ) -> list[float]:
        """
        Rerank passages by relevance to query
        
        Args:
            query: The search query
            passages: List of passage texts
            batch_size: Batch size for processing
        
        Returns:
            List of relevance scores (normalized 0-1)
        """
        if not passages:
            return []
        
        bs = batch_size or settings.rerank_batch_size
        all_scores: list[float] = []
        
        for i in range(0, len(passages), bs):
            batch = passages[i:i + bs]
            pairs = [[query, p] for p in batch]
            
            scores = self.model.compute_score(pairs, normalize=True)
            
            # Handle single result (returns float instead of list)
            if isinstance(scores, (int, float)):
                all_scores.append(float(scores))
            else:
                all_scores.extend([float(s) for s in scores])
        
        return all_scores
    
    def rerank_with_indices(
        self,
        query: str,
        passages: list[str],
        top_n: int | None = None,
    ) -> list[tuple[int, float]]:
        """
        Rerank and return sorted indices with scores
        
        Args:
            query: The search query
            passages: List of passage texts
            top_n: Number of top results to return
        
        Returns:
            List of (original_index, score) tuples, sorted by score descending
        """
        scores = self.rerank(query, passages)
        
        # Pair with indices
        indexed_scores = list(enumerate(scores))
        
        # Sort by score descending
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        if top_n:
            indexed_scores = indexed_scores[:top_n]
        
        return indexed_scores


# Singleton instance
_reranker_service: RerankerService | None = None


def get_reranker_service() -> RerankerService:
    """Get reranker service singleton"""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
