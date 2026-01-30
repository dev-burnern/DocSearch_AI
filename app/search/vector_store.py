"""
Vector Store Service
Qdrant 벡터 데이터베이스 관리
"""
from __future__ import annotations

import uuid
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import settings


class VectorStore:
    """
    Vector store using Qdrant
    Supports both dense and sparse vectors for hybrid search
    """
    
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection
    
    def ensure_collection(self) -> None:
        """Create collection if it doesn't exist"""
        existing = {c.name for c in self.client.get_collections().collections}
        
        if self.collection in existing:
            return
        
        # Create collection with both dense and sparse vectors
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                "dense": qm.VectorParams(
                    size=settings.vector_size,
                    distance=qm.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                "sparse": qm.SparseVectorParams(
                    index=qm.SparseIndexParams(on_disk=False),
                ),
            },
            hnsw_config=qm.HnswConfigDiff(m=16, ef_construct=128),
            on_disk_payload=True,
        )
        
        # Create payload indexes for filtering
        self._create_indexes()
    
    def _create_indexes(self) -> None:
        """Create payload indexes for efficient filtering"""
        indexes = [
            ("doc_id", qm.PayloadSchemaType.KEYWORD),
            ("department_id", qm.PayloadSchemaType.KEYWORD),
            ("project_id", qm.PayloadSchemaType.KEYWORD),
            ("classification", qm.PayloadSchemaType.KEYWORD),
            ("doc_type", qm.PayloadSchemaType.KEYWORD),
            ("source", qm.PayloadSchemaType.KEYWORD),
            ("uploaded_at", qm.PayloadSchemaType.INTEGER),
        ]
        
        for field_name, field_type in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field_name,
                    field_schema=field_type,
                )
            except Exception:
                pass  # Index might already exist
    
    def upsert_points(
        self,
        points: list[dict[str, Any]],
    ) -> None:
        """
        Upsert points to the collection
        
        Args:
            points: List of dicts with 'id', 'dense', 'sparse', 'payload'
        """
        qdrant_points = []
        
        for p in points:
            vectors = {}
            
            if "dense" in p:
                dense = p["dense"]
                if isinstance(dense, np.ndarray):
                    dense = dense.tolist()
                vectors["dense"] = dense
            
            if "sparse" in p:
                sparse = p["sparse"]
                vectors["sparse"] = qm.SparseVector(
                    indices=sparse["indices"],
                    values=sparse["values"],
                )
            
            qdrant_points.append(qm.PointStruct(
                id=p["id"],
                vector=vectors,
                payload=p.get("payload", {}),
            ))
        
        self.client.upsert(
            collection_name=self.collection,
            points=qdrant_points,
        )
    
    def search_dense(
        self,
        vector: np.ndarray | list[float],
        limit: int = 50,
        filter_conditions: qm.Filter | None = None,
    ) -> list[dict]:
        """
        Dense vector search
        
        Args:
            vector: Query vector
            limit: Maximum results
            filter_conditions: Optional Qdrant filter
        
        Returns:
            List of results with id, score, and payload
        """
        if isinstance(vector, np.ndarray):
            vector = vector.tolist()
        
        results = self.client.search(
            collection_name=self.collection,
            query_vector=("dense", vector),
            limit=limit,
            query_filter=filter_conditions,
            with_payload=True,
        )
        
        return [
            {
                "id": str(r.id),
                "score": r.score,
                "payload": r.payload or {},
            }
            for r in results
        ]
    
    def search_sparse(
        self,
        sparse_vector: dict,
        limit: int = 50,
        filter_conditions: qm.Filter | None = None,
    ) -> list[dict]:
        """
        Sparse vector search (BM25-like)
        
        Args:
            sparse_vector: Dict with 'indices' and 'values'
            limit: Maximum results
            filter_conditions: Optional Qdrant filter
        
        Returns:
            List of results with id, score, and payload
        """
        results = self.client.search(
            collection_name=self.collection,
            query_vector=qm.NamedSparseVector(
                name="sparse",
                vector=qm.SparseVector(
                    indices=sparse_vector["indices"],
                    values=sparse_vector["values"],
                ),
            ),
            limit=limit,
            query_filter=filter_conditions,
            with_payload=True,
        )
        
        return [
            {
                "id": str(r.id),
                "score": r.score,
                "payload": r.payload or {},
            }
            for r in results
        ]
    
    def search_hybrid(
        self,
        dense_vector: np.ndarray | list[float],
        sparse_vector: dict,
        limit: int = 50,
        filter_conditions: qm.Filter | None = None,
        fusion: str = "rrf",
    ) -> list[dict]:
        """
        Hybrid search using both dense and sparse vectors
        
        Args:
            dense_vector: Dense query vector
            sparse_vector: Sparse query vector
            limit: Maximum results
            filter_conditions: Optional Qdrant filter
            fusion: Fusion method ('rrf' or 'dbsf')
        
        Returns:
            List of results with id, score, and payload
        """
        if isinstance(dense_vector, np.ndarray):
            dense_vector = dense_vector.tolist()
        
        # Use Qdrant's query API with prefetch for hybrid search
        fusion_method = qm.Fusion.RRF if fusion == "rrf" else qm.Fusion.DBSF
        
        results = self.client.query_points(
            collection_name=self.collection,
            prefetch=[
                qm.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=limit,
                    filter=filter_conditions,
                ),
                qm.Prefetch(
                    query=qm.SparseVector(
                        indices=sparse_vector["indices"],
                        values=sparse_vector["values"],
                    ),
                    using="sparse",
                    limit=limit,
                    filter=filter_conditions,
                ),
            ],
            query=qm.FusionQuery(fusion=fusion_method),
            limit=limit,
            with_payload=True,
        )
        
        return [
            {
                "id": str(p.id),
                "score": p.score,
                "payload": p.payload or {},
            }
            for p in results.points
        ]
    
    def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete all points for a document"""
        self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="doc_id",
                            match=qm.MatchValue(value=doc_id),
                        ),
                    ],
                ),
            ),
        )
    
    def get_collection_info(self) -> dict:
        """Get collection statistics"""
        info = self.client.get_collection(self.collection)
        # Handle version differences - vectors_count was deprecated
        vectors_count = getattr(info, 'vectors_count', None) or info.points_count
        indexed_count = getattr(info, 'indexed_vectors_count', None) or info.points_count
        return {
            "points_count": info.points_count,
            "vectors_count": vectors_count,
            "indexed_vectors_count": indexed_count,
            "status": info.status.value,
        }
    
    def build_filter(
        self,
        department_id: str | None = None,
        project_id: str | None = None,
        classification: list[str] | None = None,
        doc_type: str | None = None,
        doc_ids: list[str] | None = None,
        date_from: int | None = None,
        date_to: int | None = None,
    ) -> qm.Filter | None:
        """
        Build a Qdrant filter from parameters
        
        Args:
            department_id: Filter by department
            project_id: Filter by project
            classification: Filter by classification levels
            doc_type: Filter by document type
            doc_ids: Filter by specific document IDs
            date_from: Filter by upload date (unix timestamp)
            date_to: Filter by upload date (unix timestamp)
        
        Returns:
            Qdrant Filter or None if no conditions
        """
        conditions = []
        
        if department_id:
            conditions.append(qm.FieldCondition(
                key="department_id",
                match=qm.MatchValue(value=department_id),
            ))
        
        if project_id:
            conditions.append(qm.FieldCondition(
                key="project_id",
                match=qm.MatchValue(value=project_id),
            ))
        
        if classification:
            conditions.append(qm.FieldCondition(
                key="classification",
                match=qm.MatchAny(any=classification),
            ))
        
        if doc_type:
            conditions.append(qm.FieldCondition(
                key="doc_type",
                match=qm.MatchValue(value=doc_type),
            ))
        
        if doc_ids:
            conditions.append(qm.FieldCondition(
                key="doc_id",
                match=qm.MatchAny(any=doc_ids),
            ))
        
        if date_from:
            conditions.append(qm.FieldCondition(
                key="uploaded_at",
                range=qm.Range(gte=date_from),
            ))
        
        if date_to:
            conditions.append(qm.FieldCondition(
                key="uploaded_at",
                range=qm.Range(lte=date_to),
            ))
        
        return qm.Filter(must=conditions) if conditions else None


# Singleton instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get vector store singleton"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        _vector_store.ensure_collection()
    return _vector_store
