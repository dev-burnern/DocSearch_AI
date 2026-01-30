"""
SQLAlchemy Database Models
온프레미스 문서 검색 RAG 시스템 데이터 모델
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


# ====================
# Enums
# ====================

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"
    VIEWER = "VIEWER"


class Classification(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"


class JobType(str, enum.Enum):
    EXTRACT = "extract"
    OCR = "ocr"
    ASR = "asr"
    EMBED = "embed"
    REINDEX = "reindex"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Permission(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    VIEW = "view"
    SEARCH = "search"
    CHAT = "chat"
    DELETE = "delete"
    UPDATE = "update"
    PERMISSION_CHANGE = "permission_change"


# ====================
# Models
# ====================

class Department(Base):
    """부서 테이블"""
    __tablename__ = "departments"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    parent: Mapped[Optional["Department"]] = relationship(
        "Department", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Department"]] = relationship(
        "Department", back_populates="parent"
    )
    users: Mapped[list["User"]] = relationship("User", back_populates="department")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="department")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="department")


class User(Base):
    """사용자 테이블"""
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole", native_enum=True, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.USER, nullable=False
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    max_classification: Mapped[Classification] = mapped_column(
        Enum(Classification, name="classification", native_enum=True, values_callable=lambda x: [e.value for e in x]),
        default=Classification.INTERNAL, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="users"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="uploaded_by_user"
    )
    access_policies: Mapped[list["AccessPolicy"]] = relationship(
        "AccessPolicy", foreign_keys="AccessPolicy.user_id", back_populates="user"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )
    search_logs: Mapped[list["SearchLog"]] = relationship(
        "SearchLog", back_populates="user"
    )
    
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
        Index("ix_users_department", "department_id"),
    )


class Project(Base):
    """프로젝트 테이블"""
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="projects"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="project"
    )
    access_policies: Mapped[list["AccessPolicy"]] = relationship(
        "AccessPolicy", back_populates="project"
    )


class Document(Base):
    """문서 테이블"""
    __tablename__ = "documents"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)  # MinIO key
    
    # Classification
    classification: Mapped[Classification] = mapped_column(
        Enum(Classification), default=Classification.INTERNAL, nullable=False
    )
    
    # Organization
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    
    # Metadata
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    document_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    doc_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Processing status
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Version control
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    
    # Audit
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Relationships
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="documents"
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project", back_populates="documents"
    )
    uploaded_by_user: Mapped["User"] = relationship(
        "User", back_populates="documents"
    )
    parent: Mapped[Optional["Document"]] = relationship(
        "Document", remote_side=[id], back_populates="versions"
    )
    versions: Mapped[list["Document"]] = relationship(
        "Document", back_populates="parent"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    access_policies: Mapped[list["AccessPolicy"]] = relationship(
        "AccessPolicy", back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="document", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("ix_documents_file_hash", "file_hash"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_department", "department_id"),
        Index("ix_documents_project", "project_id"),
        Index("ix_documents_classification", "classification"),
        Index("ix_documents_created", "created_at"),
        UniqueConstraint("file_hash", "version", name="uq_document_hash_version"),
    )


class DocumentChunk(Base):
    """문서 청크 테이블"""
    __tablename__ = "document_chunks"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Location
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sheet_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    slide_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Vector DB reference
    qdrant_point_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Metadata
    heading: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    has_table: Mapped[bool] = mapped_column(Boolean, default=False)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index("ix_chunks_document", "document_id"),
        Index("ix_chunks_text_hash", "text_hash"),
        Index("ix_chunks_qdrant_id", "qdrant_point_id"),
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_index"),
    )


class AccessPolicy(Base):
    """접근 정책 테이블"""
    __tablename__ = "access_policies"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Target user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    
    # Resource (either document or project)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    
    # Permission
    permission: Mapped[Permission] = mapped_column(
        Enum(Permission), default=Permission.READ, nullable=False
    )
    
    # Audit
    granted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="access_policies"
    )
    document: Mapped[Optional["Document"]] = relationship(
        "Document", back_populates="access_policies"
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project", back_populates="access_policies"
    )
    
    __table_args__ = (
        Index("ix_access_user", "user_id"),
        Index("ix_access_document", "document_id"),
        Index("ix_access_project", "project_id"),
    )


class AuditLog(Base):
    """감사 로그 테이블"""
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Request details
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Additional data
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index("ix_audit_user", "user_id"),
        Index("ix_audit_action", "action"),
        Index("ix_audit_created", "created_at"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
    )


class SearchLog(Base):
    """검색 로그 테이블"""
    __tablename__ = "search_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    
    # Query
    query: Mapped[str] = mapped_column(Text, nullable=False)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rewritten_queries: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    
    # Results
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    top_doc_ids: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    
    # Performance
    latency_ms: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Feedback
    feedback: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="search_logs")
    
    __table_args__ = (
        Index("ix_search_user", "user_id"),
        Index("ix_search_query_hash", "query_hash"),
        Index("ix_search_created", "created_at"),
    )


class ProcessingJob(Base):
    """처리 작업 테이블"""
    __tablename__ = "processing_jobs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    
    # Celery task
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="processing_jobs"
    )
    
    __table_args__ = (
        Index("ix_jobs_document", "document_id"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_celery", "celery_task_id"),
    )
