"""
Search API Router
검색 API 엔드포인트
"""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.dependencies import get_current_user, get_auth_service
from app.services.auth import AuthService
from app.search import SearchPipeline, SearchResult

router = APIRouter(prefix="/search", tags=["Search"])


# Request/Response Models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(50, ge=1, le=200, description="Number of candidates for retrieval")
    top_n: int = Field(5, ge=1, le=50, description="Number of final results")
    use_rerank: bool = True
    use_hybrid: bool = True
    
    # Filters
    department_id: str | None = None
    project_id: str | None = None
    classification: list[str] | None = None
    doc_type: str | None = None
    date_from: int | None = None  # Unix timestamp
    date_to: int | None = None


class SearchHit(BaseModel):
    chunk_id: str
    doc_id: str
    score: float
    text: str
    source: str
    page: int | None = None
    sheet: str | None = None
    slide: int | None = None
    chunk_index: int
    heading: str | None = None
    highlight: str | None = None


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]
    total: int
    metrics: dict


# Endpoints
@router.post("", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    문서를 검색합니다
    
    하이브리드 검색 (Dense + Sparse) + 리랭킹을 사용합니다.
    """
    # Get accessible document IDs for the user
    accessible_doc_ids = await auth_service.get_accessible_document_ids(current_user)
    
    # Convert to string list if not None
    accessible_str_ids = [str(d) for d in accessible_doc_ids] if accessible_doc_ids else None
    
    # Build filter params
    filter_params = {}
    if request.department_id:
        filter_params["department_id"] = request.department_id
    if request.project_id:
        filter_params["project_id"] = request.project_id
    if request.classification:
        filter_params["classification"] = request.classification
    if request.doc_type:
        filter_params["doc_type"] = request.doc_type
    if request.date_from:
        filter_params["date_from"] = request.date_from
    if request.date_to:
        filter_params["date_to"] = request.date_to
    
    # Execute search
    pipeline = SearchPipeline()
    results, metrics = pipeline.search(
        query=request.query,
        top_k=request.top_k,
        top_n=request.top_n,
        use_rerank=request.use_rerank,
        use_hybrid=request.use_hybrid,
        filter_params=filter_params if filter_params else None,
        accessible_doc_ids=accessible_str_ids,
    )
    
    # Build response
    hits = []
    for r in results:
        # Create simple highlight (bold matching terms)
        highlight = create_highlight(r.text, request.query)
        
        hits.append(SearchHit(
            chunk_id=r.chunk_id,
            doc_id=r.doc_id,
            score=round(r.score, 4),
            text=r.text,
            source=r.source,
            page=r.page,
            sheet=r.sheet,
            slide=r.slide,
            chunk_index=r.chunk_index,
            heading=r.heading,
            highlight=highlight,
        ))
    
    return SearchResponse(
        query=request.query,
        hits=hits,
        total=len(hits),
        metrics={
            "embed_ms": round(metrics.embed_ms, 2),
            "search_ms": round(metrics.search_ms, 2),
            "rerank_ms": round(metrics.rerank_ms, 2),
            "total_ms": round(metrics.total_ms, 2),
        },
    )


@router.get("/quick", response_model=SearchResponse)
async def quick_search(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(5, ge=1, le=20),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
):
    """
    빠른 검색 (GET 요청용)
    """
    request = SearchRequest(
        query=q,
        top_k=limit * 5,
        top_n=limit,
        use_rerank=True,
        use_hybrid=True,
    )
    
    return await search_documents(request, current_user, auth_service)


def create_highlight(text: str, query: str, max_length: int = 300) -> str:
    """
    Create a highlighted snippet from text
    Simple implementation - in production, use proper highlighting library
    """
    import re
    
    # Find relevant part of text
    query_terms = query.lower().split()
    text_lower = text.lower()
    
    # Find first occurrence of any query term
    first_match = len(text)
    for term in query_terms:
        pos = text_lower.find(term)
        if pos != -1 and pos < first_match:
            first_match = pos
    
    # Extract snippet around match
    start = max(0, first_match - 50)
    end = min(len(text), start + max_length)
    
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    # Bold matching terms (for HTML rendering)
    for term in query_terms:
        if len(term) >= 2:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            snippet = pattern.sub(f"**{term}**", snippet)
    
    return snippet
