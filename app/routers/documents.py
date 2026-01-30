"""
Documents API Router
문서 업로드, 조회, 관리 API
"""
from __future__ import annotations

import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import hash_file, hash_text
from app.db.base import get_db
from app.db.models import (
    Classification,
    Document,
    DocumentChunk,
    DocumentStatus,
    Permission,
    ProcessingJob,
    User,
)
from app.dependencies import get_current_user, get_auth_service, require_read_access
from app.services.auth import AuthService
from app.services.storage import get_storage_service
from app.worker.tasks import process_document, delete_document_vectors

router = APIRouter(prefix="/documents", tags=["Documents"])


# Response Models
class DocumentResponse(BaseModel):
    id: str
    filename: str
    title: str | None
    author: str | None
    file_size: int
    mime_type: str
    classification: str
    status: str
    chunk_count: int
    page_count: int | None
    version: int
    tags: list[str] | None
    department_id: str | None
    project_id: str | None
    uploaded_by: str
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DocumentDetailResponse(DocumentResponse):
    chunks: list[dict] | None = None
    processing_jobs: list[dict] | None = None


class ProcessingJobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    progress: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


# Endpoints
@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    title: str | None = Form(None),
    classification: Classification = Form(Classification.INTERNAL),
    department_id: str | None = Form(None),
    project_id: str | None = Form(None),
    tags: str | None = Form(None),  # Comma-separated
):
    """
    문서를 업로드하고 처리를 시작합니다
    
    지원 형식: PDF, DOCX, XLSX, PPTX, TXT, MD, PNG, JPG, HWP
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일명이 없습니다",
        )
    
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 파일 형식입니다: {ext}",
        )
    
    # Read file
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"파일 크기가 제한({settings.max_file_size_mb}MB)을 초과합니다",
        )
    
    # Calculate hash
    file_hash = hash_text(content.decode("latin-1"))  # Binary-safe hash
    
    # Check for duplicate
    existing = await db.execute(
        select(Document).where(
            Document.file_hash == file_hash,
            Document.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="동일한 파일이 이미 존재합니다",
        )
    
    # Detect MIME type
    mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    
    # Create document record
    doc_id = uuid.uuid4()
    
    doc = Document(
        id=doc_id,
        filename=file.filename,
        file_hash=file_hash,
        file_size=file_size,
        mime_type=mime_type,
        storage_key="",  # Will be updated after upload
        title=title,
        classification=classification,
        department_id=uuid.UUID(department_id) if department_id else current_user.department_id,
        project_id=uuid.UUID(project_id) if project_id else None,
        tags=tags.split(",") if tags else None,
        status=DocumentStatus.PENDING,
        uploaded_by=current_user.id,
    )
    
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    
    # Upload to storage
    storage = get_storage_service()
    storage_key = storage.upload_document(
        file_data=content,
        document_id=doc.id,
        filename=file.filename,
        version=1,
        content_type=mime_type,
    )
    
    doc.storage_key = storage_key
    await db.commit()
    await db.refresh(doc)
    
    # Start processing task
    process_document.delay(str(doc.id), storage_key)
    
    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        title=doc.title,
        author=doc.author,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        classification=doc.classification.value,
        status=doc.status.value,
        chunk_count=doc.chunk_count,
        page_count=doc.page_count,
        version=doc.version,
        tags=doc.tags,
        department_id=str(doc.department_id) if doc.department_id else None,
        project_id=str(doc.project_id) if doc.project_id else None,
        uploaded_by=str(doc.uploaded_by),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: DocumentStatus | None = None,
    classification_filter: Classification | None = None,
    department_id: str | None = None,
    project_id: str | None = None,
    search: str | None = None,
):
    """
    문서 목록을 조회합니다 (권한에 따라 필터링)
    """
    # Get accessible document IDs
    accessible_ids = await auth_service.get_accessible_document_ids(current_user)
    
    # Build query
    query = select(Document).where(Document.deleted_at.is_(None))
    
    # Apply access filter
    if accessible_ids is not None:
        query = query.where(Document.id.in_(accessible_ids))
    
    # Apply filters
    if status_filter:
        query = query.where(Document.status == status_filter)
    
    if classification_filter:
        query = query.where(Document.classification == classification_filter)
    
    if department_id:
        query = query.where(Document.department_id == uuid.UUID(department_id))
    
    if project_id:
        query = query.where(Document.project_id == uuid.UUID(project_id))
    
    if search:
        query = query.where(
            Document.filename.ilike(f"%{search}%") |
            Document.title.ilike(f"%{search}%")
        )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginate
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return DocumentListResponse(
        items=[
            DocumentResponse(
                id=str(doc.id),
                filename=doc.filename,
                title=doc.title,
                author=doc.author,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                classification=doc.classification.value,
                status=doc.status.value,
                chunk_count=doc.chunk_count,
                page_count=doc.page_count,
                version=doc.version,
                tags=doc.tags,
                department_id=str(doc.department_id) if doc.department_id else None,
                project_id=str(doc.project_id) if doc.project_id else None,
                uploaded_by=str(doc.uploaded_by),
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                error_message=doc.error_message,
            )
            for doc in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_chunks: bool = False,
):
    """
    문서 상세 정보를 조회합니다
    """
    # Check access
    has_access = await auth_service.check_document_access(
        current_user, document_id, Permission.READ
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 문서에 대한 접근 권한이 없습니다",
        )
    
    # Get document
    query = select(Document).where(
        Document.id == document_id,
        Document.deleted_at.is_(None),
    )
    
    if include_chunks:
        query = query.options(selectinload(Document.chunks))
    
    query = query.options(selectinload(Document.processing_jobs))
    
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다",
        )
    
    chunks = None
    if include_chunks and doc.chunks:
        chunks = [
            {
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "text": c.text[:500] + "..." if len(c.text) > 500 else c.text,
                "page_number": c.page_number,
                "sheet_name": c.sheet_name,
                "heading": c.heading,
            }
            for c in sorted(doc.chunks, key=lambda x: x.chunk_index)
        ]
    
    jobs = None
    if doc.processing_jobs:
        jobs = [
            {
                "id": str(j.id),
                "job_type": j.job_type.value,
                "status": j.status.value,
                "progress": j.progress,
                "error_message": j.error_message,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in sorted(doc.processing_jobs, key=lambda x: x.created_at, reverse=True)
        ]
    
    return DocumentDetailResponse(
        id=str(doc.id),
        filename=doc.filename,
        title=doc.title,
        author=doc.author,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        classification=doc.classification.value,
        status=doc.status.value,
        chunk_count=doc.chunk_count,
        page_count=doc.page_count,
        version=doc.version,
        tags=doc.tags,
        department_id=str(doc.department_id) if doc.department_id else None,
        project_id=str(doc.project_id) if doc.project_id else None,
        uploaded_by=str(doc.uploaded_by),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        error_message=doc.error_message,
        chunks=chunks,
        processing_jobs=jobs,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: bool = False,
):
    """
    문서를 삭제합니다 (기본: 소프트 삭제)
    """
    # Check access
    has_access = await auth_service.check_document_access(
        current_user, document_id, Permission.DELETE
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 문서를 삭제할 권한이 없습니다",
        )
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다",
        )
    
    if hard_delete:
        # Delete from storage
        storage = get_storage_service()
        storage.delete_document(doc.id)
        
        # Delete vectors
        delete_document_vectors.delay(str(doc.id))
        
        # Hard delete from DB
        await db.delete(doc)
    else:
        # Soft delete
        doc.deleted_at = datetime.now(timezone.utc)
        doc.status = DocumentStatus.DELETED
        
        # Still remove vectors for security
        delete_document_vectors.delay(str(doc.id))
    
    await db.commit()
    
    return {"message": "문서가 삭제되었습니다"}


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    문서 다운로드 URL을 생성합니다
    """
    from fastapi.responses import RedirectResponse
    from datetime import timedelta
    
    # Check access
    has_access = await auth_service.check_document_access(
        current_user, document_id, Permission.READ
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 문서에 대한 접근 권한이 없습니다",
        )
    
    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다",
        )
    
    # Generate presigned URL
    storage = get_storage_service()
    url = storage.get_presigned_url(doc.storage_key, expires=timedelta(minutes=30))
    
    return {"download_url": url, "filename": doc.filename}


@router.get("/{document_id}/status", response_model=ProcessingJobResponse)
async def get_processing_status(
    document_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    문서 처리 상태를 조회합니다
    """
    # Check access
    has_access = await auth_service.check_document_access(
        current_user, document_id, Permission.READ
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없습니다",
        )
    
    # Get latest job
    result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="처리 작업을 찾을 수 없습니다",
        )
    
    return ProcessingJobResponse(
        id=str(job.id),
        job_type=job.job_type.value,
        status=job.status.value,
        progress=job.progress,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )
