"""
Chat API Router
RAG 기반 채팅 API 엔드포인트
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_text
from app.db.base import get_db
from app.db.models import AuditAction, AuditLog, SearchLog, User
from app.dependencies import get_current_user, get_auth_service
from app.services.auth import AuthService
from app.search import SearchPipeline, SearchResult
from app.llm import get_llm_service, build_rag_prompt

router = APIRouter(prefix="/chat", tags=["Chat"])


# Request/Response Models
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(50, ge=1, le=200)
    top_n: int = Field(5, ge=1, le=20)
    use_rerank: bool = True
    use_hybrid: bool = True
    use_query_rewrite: bool = False
    model: str | None = None
    stream: bool = False
    
    # Filters
    department_id: str | None = None
    project_id: str | None = None


class Citation(BaseModel):
    chunk_id: str
    doc_id: str
    source: str
    page: int | None = None
    sheet: str | None = None
    slide: int | None = None
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    query: str
    rewritten_queries: list[str] | None = None
    metrics: dict


# Endpoints
@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    문서 기반 질의응답 (RAG)
    
    1. 질의 재작성 (선택)
    2. 하이브리드 검색 + 리랭킹
    3. LLM 응답 생성
    4. 출처 표시
    """
    if request.stream:
        # Return streaming response
        return StreamingResponse(
            stream_chat_response(request, current_user, auth_service, db),
            media_type="text/event-stream",
        )
    
    # Get accessible document IDs
    accessible_doc_ids = await auth_service.get_accessible_document_ids(current_user)
    accessible_str_ids = [str(d) for d in accessible_doc_ids] if accessible_doc_ids else None
    
    # Build filters
    filter_params = {}
    if request.department_id:
        filter_params["department_id"] = request.department_id
    if request.project_id:
        filter_params["project_id"] = request.project_id
    
    pipeline = SearchPipeline()
    llm = get_llm_service()
    
    # Query rewriting
    queries = [request.query]
    if request.use_query_rewrite:
        queries = llm.rewrite_query(request.query)
    
    # Search
    if len(queries) > 1:
        results, search_metrics = pipeline.multi_query_search(
            queries=queries,
            top_k=request.top_k,
            top_n=request.top_n,
            use_hybrid=request.use_hybrid,
            filter_params=filter_params if filter_params else None,
            accessible_doc_ids=accessible_str_ids,
        )
    else:
        results, search_metrics = pipeline.search(
            query=request.query,
            top_k=request.top_k,
            top_n=request.top_n,
            use_rerank=request.use_rerank,
            use_hybrid=request.use_hybrid,
            filter_params=filter_params if filter_params else None,
            accessible_doc_ids=accessible_str_ids,
        )
    
    # Generate response
    llm_response = llm.rag_generate(
        query=request.query,
        contexts=results,
        model=request.model,
    )
    
    # Build citations
    citations = [
        Citation(
            chunk_id=r.chunk_id,
            doc_id=r.doc_id,
            source=r.source,
            page=r.page,
            sheet=r.sheet,
            slide=r.slide,
            text=r.text[:500] + "..." if len(r.text) > 500 else r.text,
            score=round(r.score, 4),
        )
        for r in results
    ]
    
    # Log search
    await log_search(
        db=db,
        user_id=current_user.id,
        query=request.query,
        rewritten_queries=queries if len(queries) > 1 else None,
        results_count=len(results),
        top_doc_ids=[r.doc_id for r in results[:5]],
        latency={
            "search_ms": search_metrics.total_ms,
            "llm_ms": llm_response.latency_ms,
            "total_ms": search_metrics.total_ms + llm_response.latency_ms,
        },
    )
    
    return ChatResponse(
        answer=llm_response.answer,
        citations=citations,
        query=request.query,
        rewritten_queries=queries if len(queries) > 1 else None,
        metrics={
            "embed_ms": round(search_metrics.embed_ms, 2),
            "search_ms": round(search_metrics.search_ms, 2),
            "rerank_ms": round(search_metrics.rerank_ms, 2),
            "llm_ms": round(llm_response.latency_ms, 2),
            "total_ms": round(search_metrics.total_ms + llm_response.latency_ms, 2),
            "prompt_tokens": llm_response.prompt_tokens,
            "completion_tokens": llm_response.completion_tokens,
        },
    )


async def stream_chat_response(
    request: ChatRequest,
    current_user: User,
    auth_service: AuthService,
    db: AsyncSession,
) -> AsyncIterator[str]:
    """
    Stream chat response using Server-Sent Events
    """
    import json
    
    # Get accessible documents
    accessible_doc_ids = await auth_service.get_accessible_document_ids(current_user)
    accessible_str_ids = [str(d) for d in accessible_doc_ids] if accessible_doc_ids else None
    
    # Build filters
    filter_params = {}
    if request.department_id:
        filter_params["department_id"] = request.department_id
    if request.project_id:
        filter_params["project_id"] = request.project_id
    
    pipeline = SearchPipeline()
    llm = get_llm_service()
    
    # Search first
    results, search_metrics = pipeline.search(
        query=request.query,
        top_k=request.top_k,
        top_n=request.top_n,
        use_rerank=request.use_rerank,
        use_hybrid=request.use_hybrid,
        filter_params=filter_params if filter_params else None,
        accessible_doc_ids=accessible_str_ids,
    )
    
    # Send citations first
    citations = [
        {
            "chunk_id": r.chunk_id,
            "doc_id": r.doc_id,
            "source": r.source,
            "page": r.page,
            "text": r.text[:300] + "..." if len(r.text) > 300 else r.text,
        }
        for r in results
    ]
    yield f"data: {json.dumps({'type': 'citations', 'data': citations})}\n\n"
    
    # Stream LLM response
    prompt = build_rag_prompt(request.query, results)
    
    async for chunk in llm.generate_stream(prompt, model=request.model):
        yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"
    
    # Send done signal
    yield f"data: {json.dumps({'type': 'done', 'metrics': {'search_ms': search_metrics.total_ms}})}\n\n"


async def log_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    rewritten_queries: list[str] | None,
    results_count: int,
    top_doc_ids: list[str],
    latency: dict,
) -> None:
    """Log search for analytics"""
    log = SearchLog(
        user_id=user_id,
        query=query,
        query_hash=hash_text(query),
        rewritten_queries=rewritten_queries,
        results_count=results_count,
        top_doc_ids=top_doc_ids,
        latency_ms=latency,
    )
    db.add(log)
    # Don't await commit - will be committed with the request


@router.post("/feedback")
async def submit_feedback(
    search_log_id: str,
    helpful: bool,
    comment: str | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    검색/응답에 대한 피드백을 제출합니다
    """
    result = await db.execute(
        select(SearchLog).where(SearchLog.id == uuid.UUID(search_log_id))
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="검색 로그를 찾을 수 없습니다")
    
    log.feedback = {
        "helpful": helpful,
        "comment": comment,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.commit()
    
    return {"message": "피드백이 제출되었습니다"}
