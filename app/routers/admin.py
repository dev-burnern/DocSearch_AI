"""
Admin API Router
관리자 기능 API 엔드포인트
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import (
    AuditLog,
    Classification,
    Department,
    Document,
    DocumentStatus,
    Permission,
    Project,
    SearchLog,
    User,
    UserRole,
)
from app.dependencies import get_current_admin, get_auth_service
from app.search import get_vector_store
from app.llm import get_llm_service
from app.services.auth import AuthService

router = APIRouter(prefix="/admin", tags=["Admin"])


# Models
class SystemStatsResponse(BaseModel):
    documents: dict
    users: dict
    vector_store: dict
    llm: dict


class UserListResponse(BaseModel):
    items: list[dict]
    total: int


class AuditLogResponse(BaseModel):
    items: list[dict]
    total: int


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    parent_id: str | None = None
    description: str | None = None


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    department_id: str | None = None
    description: str | None = None


class UserUpdate(BaseModel):
    role: UserRole | None = None
    department_id: str | None = None
    max_classification: Classification | None = None
    is_active: bool | None = None


class AccessPolicyCreate(BaseModel):
    user_id: str
    document_id: str | None = None
    project_id: str | None = None
    permission: Permission = Permission.READ
    expires_at: datetime | None = None


# Endpoints
@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """시스템 통계를 조회합니다"""
    
    # Document stats
    total_docs = await db.scalar(
        select(func.count()).select_from(Document).where(Document.deleted_at.is_(None))
    )
    
    ready_docs = await db.scalar(
        select(func.count()).select_from(Document).where(
            Document.status == DocumentStatus.READY,
            Document.deleted_at.is_(None),
        )
    )
    
    processing_docs = await db.scalar(
        select(func.count()).select_from(Document).where(
            Document.status == DocumentStatus.PROCESSING,
            Document.deleted_at.is_(None),
        )
    )
    
    error_docs = await db.scalar(
        select(func.count()).select_from(Document).where(
            Document.status == DocumentStatus.ERROR,
        )
    )
    
    total_chunks = await db.scalar(
        select(func.sum(Document.chunk_count)).where(Document.deleted_at.is_(None))
    )
    
    # User stats
    total_users = await db.scalar(select(func.count()).select_from(User))
    active_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active == True)
    )
    
    # Vector store stats
    try:
        vector_store = get_vector_store()
        vs_info = vector_store.get_collection_info()
    except Exception:
        vs_info = {"status": "unavailable"}
    
    # LLM stats
    try:
        llm = get_llm_service()
        models = llm.list_models()
        llm_healthy = llm.check_health()
    except Exception:
        models = []
        llm_healthy = False
    
    return SystemStatsResponse(
        documents={
            "total": total_docs or 0,
            "ready": ready_docs or 0,
            "processing": processing_docs or 0,
            "error": error_docs or 0,
            "total_chunks": total_chunks or 0,
        },
        users={
            "total": total_users or 0,
            "active": active_users or 0,
        },
        vector_store=vs_info,
        llm={
            "healthy": llm_healthy,
            "models_available": len(models),
            "models": [m.get("name") for m in models[:5]],
        },
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """사용자 목록을 조회합니다"""
    
    # Count
    total = await db.scalar(select(func.count()).select_from(User))
    
    # Query
    result = await db.execute(
        select(User)
        .options(selectinload(User.department))
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()
    
    return UserListResponse(
        items=[
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value,
                "department": u.department.name if u.department else None,
                "max_classification": u.max_classification.value,
                "is_active": u.is_active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        total=total or 0,
    )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """사용자 정보를 수정합니다"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    
    if data.role is not None:
        user.role = data.role
    if data.department_id is not None:
        user.department_id = uuid.UUID(data.department_id) if data.department_id else None
    if data.max_classification is not None:
        user.max_classification = data.max_classification
    if data.is_active is not None:
        user.is_active = data.is_active
    
    await db.commit()
    
    return {"message": "사용자 정보가 수정되었습니다"}


@router.get("/audit-logs", response_model=AuditLogResponse)
async def get_audit_logs(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    """감사 로그를 조회합니다"""
    
    query = select(AuditLog).options(selectinload(AuditLog.user))
    
    if user_id:
        query = query.where(AuditLog.user_id == uuid.UUID(user_id))
    if action:
        query = query.where(AuditLog.action == action)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Query
    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return AuditLogResponse(
        items=[
            {
                "id": log.id,
                "user": log.user.username if log.user else None,
                "action": log.action.value,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        total=total or 0,
    )


@router.post("/departments")
async def create_department(
    data: DepartmentCreate,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """부서를 생성합니다"""
    
    dept = Department(
        name=data.name,
        code=data.code,
        parent_id=uuid.UUID(data.parent_id) if data.parent_id else None,
        description=data.description,
    )
    db.add(dept)
    await db.commit()
    
    return {"id": str(dept.id), "message": "부서가 생성되었습니다"}


@router.get("/departments")
async def list_departments(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """부서 목록을 조회합니다"""
    
    result = await db.execute(
        select(Department).where(Department.is_active == True)
    )
    depts = result.scalars().all()
    
    return [
        {
            "id": str(d.id),
            "name": d.name,
            "code": d.code,
            "parent_id": str(d.parent_id) if d.parent_id else None,
            "description": d.description,
        }
        for d in depts
    ]


@router.post("/projects")
async def create_project(
    data: ProjectCreate,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """프로젝트를 생성합니다"""
    
    project = Project(
        name=data.name,
        code=data.code,
        department_id=uuid.UUID(data.department_id) if data.department_id else None,
        description=data.description,
    )
    db.add(project)
    await db.commit()
    
    return {"id": str(project.id), "message": "프로젝트가 생성되었습니다"}


@router.get("/projects")
async def list_projects(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """프로젝트 목록을 조회합니다"""
    
    result = await db.execute(
        select(Project).where(Project.is_active == True)
    )
    projects = result.scalars().all()
    
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "code": p.code,
            "department_id": str(p.department_id) if p.department_id else None,
            "description": p.description,
        }
        for p in projects
    ]


@router.post("/access-policies")
async def create_access_policy(
    data: AccessPolicyCreate,
    current_admin: Annotated[User, Depends(get_current_admin)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """접근 권한을 부여합니다"""
    
    policy = await auth_service.grant_access(
        granter=current_admin,
        user_id=uuid.UUID(data.user_id),
        document_id=uuid.UUID(data.document_id) if data.document_id else None,
        project_id=uuid.UUID(data.project_id) if data.project_id else None,
        permission=data.permission,
        expires_at=data.expires_at,
    )
    
    return {"id": str(policy.id), "message": "접근 권한이 부여되었습니다"}


@router.delete("/access-policies/{policy_id}")
async def revoke_access_policy(
    policy_id: uuid.UUID,
    current_admin: Annotated[User, Depends(get_current_admin)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """접근 권한을 해제합니다"""
    
    success = await auth_service.revoke_access(current_admin, policy_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="접근 정책을 찾을 수 없습니다")
    
    return {"message": "접근 권한이 해제되었습니다"}


@router.get("/search-analytics")
async def get_search_analytics(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(7, ge=1, le=90),
):
    """검색 분석 데이터를 조회합니다"""
    from datetime import timedelta
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Total searches
    total = await db.scalar(
        select(func.count()).select_from(SearchLog).where(
            SearchLog.created_at >= since
        )
    )
    
    # Average latency
    avg_latency = await db.execute(
        select(
            func.avg(SearchLog.latency_ms['total_ms'].cast(float))
        ).where(SearchLog.created_at >= since)
    )
    
    # Top queries (by hash for privacy)
    top_queries = await db.execute(
        select(
            SearchLog.query,
            func.count().label("count"),
        )
        .where(SearchLog.created_at >= since)
        .group_by(SearchLog.query)
        .order_by(func.count().desc())
        .limit(10)
    )
    
    # Feedback stats
    helpful_count = await db.scalar(
        select(func.count()).select_from(SearchLog).where(
            SearchLog.created_at >= since,
            SearchLog.feedback['helpful'].cast(bool) == True,
        )
    )
    
    not_helpful_count = await db.scalar(
        select(func.count()).select_from(SearchLog).where(
            SearchLog.created_at >= since,
            SearchLog.feedback['helpful'].cast(bool) == False,
        )
    )
    
    return {
        "period_days": days,
        "total_searches": total or 0,
        "average_latency_ms": round(avg_latency.scalar() or 0, 2),
        "top_queries": [
            {"query": q[:100], "count": c}
            for q, c in top_queries.all()
        ],
        "feedback": {
            "helpful": helpful_count or 0,
            "not_helpful": not_helpful_count or 0,
        },
    }
