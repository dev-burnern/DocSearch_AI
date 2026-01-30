"""
Embedding Service
BGE-M3 기반 Dense + Sparse 임베딩
"""
from __future__ import annotations

import numpy as np
from typing import Any

from app.core.config import settings


class EmbeddingService:
    """
    Embedding service using BGE-M3
    Supports both dense and sparse (lexical) embeddings
    """
    
    def __init__(self):
        self._model = None
    
    @property
    def model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            from FlagEmbedding import BGEM3FlagModel
            
            self._model = BGEM3FlagModel(
                settings.embed_model,
                use_fp16=settings.embed_use_fp16,
                device=settings.embed_device,
            )
        return self._model
    
    def encode_query(
        self,
        query: str,
        return_dense: bool = True,
        return_sparse: bool = True,
    ) -> dict[str, Any]:
        """
        Encode a query for search
        
        Args:
            query: The query text
            return_dense: Whether to return dense embedding
            return_sparse: Whether to return sparse embedding
        
        Returns:
            Dict with 'dense' and/or 'sparse' embeddings
        """
        result = self.model.encode(
            [query],
            max_length=settings.embed_max_length,
            return_dense=return_dense,
            return_sparse=return_sparse,
            return_colbert_vecs=False,
        )
        
        output = {}
        
        if return_dense:
            output["dense"] = np.asarray(result["dense_vecs"][0], dtype=np.float32)
        
        if return_sparse:
            lexical = result["lexical_weights"][0]
            output["sparse"] = self._convert_sparse(lexical)
        
        return output
    
    def encode_documents(
        self,
        texts: list[str],
        return_dense: bool = True,
        return_sparse: bool = True,
        batch_size: int | None = None,
    ) -> dict[str, Any]:
        """
        Encode documents for indexing
        
        Args:
            texts: List of document texts
            return_dense: Whether to return dense embeddings
            return_sparse: Whether to return sparse embeddings
            batch_size: Batch size for encoding
        
        Returns:
            Dict with 'dense' and/or 'sparse' embeddings arrays
        """
        bs = batch_size or settings.embed_batch_size
        all_dense = []
        all_sparse = []
        
        for i in range(0, len(texts), bs):
            batch = texts[i:i + bs]
            
            result = self.model.encode(
                batch,
                max_length=settings.embed_max_length,
                return_dense=return_dense,
                return_sparse=return_sparse,
                return_colbert_vecs=False,
            )
            
            if return_dense:
                all_dense.extend(result["dense_vecs"])
            
            if return_sparse:
                for lw in result["lexical_weights"]:
                    all_sparse.append(self._convert_sparse(lw))
        
        output = {}
        
        if return_dense:
            output["dense"] = np.asarray(all_dense, dtype=np.float32)
        
        if return_sparse:
            output["sparse"] = all_sparse
        
        return output
    
    def _convert_sparse(self, lexical_weights: dict) -> dict:
        """
        Convert BGE-M3 lexical weights to sparse vector format
        
        Args:
            lexical_weights: Dict of token_id -> weight
        
        Returns:
            Dict with 'indices' and 'values' lists
        """
        indices = []
        values = []
        
        for token_id, weight in lexical_weights.items():
            indices.append(int(token_id))
            values.append(float(weight))
        
        return {"indices": indices, "values": values}


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get embedding service singleton"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
