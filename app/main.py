"""
FastAPI Main Application
온프레미스 문서 검색 RAG 서버
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.base import init_db, close_db
from app.routers import (
    auth_router,
    documents_router,
    search_router,
    chat_router,
    admin_router,
)

# Logging configuration
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events"""
    logger.info("🚀 Starting DocSearch AI Server...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Initialize vector store connection
    try:
        from app.search import get_vector_store
        vs = get_vector_store()
        info = vs.get_collection_info()
        logger.info(f"✅ Vector store connected: {info.get('points_count', 0)} vectors")
    except Exception as e:
        logger.warning(f"⚠️ Vector store connection failed (will retry): {e}")
    
    # Check LLM service
    try:
        from app.llm import get_llm_service
        llm = get_llm_service()
        if llm.check_health():
            logger.info("✅ LLM service healthy")
        else:
            logger.warning("⚠️ LLM service unhealthy")
    except Exception as e:
        logger.warning(f"⚠️ LLM service check failed: {e}")
    
    logger.info("✅ DocSearch AI Server ready!")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down DocSearch AI Server...")
    await close_db()
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DocSearch AI",
    description="""
온프레미스 문서 검색 RAG/Agent AI 서버

## 주요 기능

* **문서 업로드**: PDF, DOCX, XLSX, PPTX, HWP, 이미지 지원
* **하이브리드 검색**: Dense + Sparse 벡터 결합
* **RAG 채팅**: 문서 기반 질의응답
* **접근 제어**: 부서/프로젝트/보안등급 기반 RBAC

## 기술 스택

* FastAPI + PostgreSQL + Qdrant
* BGE-M3 Embedding + BGE-Reranker
* Ollama + Qwen2.5
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "내부 서버 오류가 발생했습니다"},
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """기본 헬스체크"""
    return {"status": "healthy", "service": "docsearch-ai"}


@app.get("/health/ready")
async def readiness_check():
    """서비스 준비 상태 확인"""
    checks = {}
    
    # Database check
    try:
        from app.db.base import get_engine
        from sqlalchemy import text
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"
    
    # Vector store check
    try:
        from app.search import get_vector_store
        vs = get_vector_store()
        vs.get_collection_info()
        checks["vector_store"] = "healthy"
    except Exception as e:
        checks["vector_store"] = f"unhealthy: {e}"
    
    # LLM check
    try:
        from app.llm import get_llm_service
        llm = get_llm_service()
        checks["llm"] = "healthy" if llm.check_health() else "unhealthy"
    except Exception as e:
        checks["llm"] = f"unhealthy: {e}"
    
    all_healthy = all("healthy" == v for v in checks.values())
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
    }


# Include routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(admin_router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "DocSearch AI",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not settings.is_production,
        workers=1,  # Single worker for GPU models
    )
