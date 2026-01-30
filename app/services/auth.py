"""
Authentication and Authorization Service
인증 및 권한 관리 서비스
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import (
    AccessPolicy,
    AuditAction,
    AuditLog,
    Classification,
    Document,
    Permission,
    User,
    UserRole,
)


class AuthService:
    """Authentication and authorization service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User | None, str | None]:
        """
        Authenticate user with username and password
        Returns (user, error_message)
        """
        # Find user
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None, "사용자를 찾을 수 없습니다"
        
        if not user.is_active:
            return None, "비활성화된 계정입니다"
        
        if not verify_password(password, user.password_hash):
            # Log failed attempt
            await self._log_audit(
                user_id=user.id,
                action=AuditAction.LOGIN,
                resource_type="auth",
                details={"success": False, "reason": "invalid_password"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            return None, "비밀번호가 일치하지 않습니다"
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        
        # Log successful login
        await self._log_audit(
            user_id=user.id,
            action=AuditAction.LOGIN,
            resource_type="auth",
            details={"success": True},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return user, None
    
    async def create_tokens(self, user: User) -> dict:
        """Create access and refresh tokens for user"""
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "department_id": str(user.department_id) if user.department_id else None,
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    
    async def refresh_tokens(self, refresh_token: str) -> dict | None:
        """Refresh access token using refresh token"""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return None
        
        return await self.create_tokens(user)
    
    async def get_current_user(self, token: str) -> User | None:
        """Get current user from access token"""
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        
        user_id = payload.get("sub")
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.department))
            .where(User.id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.USER,
        department_id: uuid.UUID | None = None,
        max_classification: Classification = Classification.INTERNAL,
    ) -> User:
        """Create a new user"""
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            department_id=department_id,
            max_classification=max_classification,
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.flush()
        return user
    
    async def check_document_access(
        self,
        user: User,
        document_id: uuid.UUID,
        required_permission: Permission = Permission.READ,
    ) -> bool:
        """
        Check if user has access to a document
        Access is granted if:
        1. User is admin
        2. User uploaded the document
        3. User has explicit access policy
        4. Document is in user's department
        5. Document classification <= user's max classification
        """
        # Admin has full access
        if user.role == UserRole.ADMIN:
            return True
        
        # Get document with project info
        result = await self.db.execute(
            select(Document)
            .options(selectinload(Document.project))
            .where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            return False
        
        # Check classification level
        classification_order = {
            Classification.PUBLIC: 0,
            Classification.INTERNAL: 1,
            Classification.CONFIDENTIAL: 2,
            Classification.RESTRICTED: 3,
        }
        if classification_order[document.classification] > classification_order[user.max_classification]:
            return False
        
        # User uploaded the document
        if document.uploaded_by == user.id:
            return True
        
        # Same department
        if document.department_id and document.department_id == user.department_id:
            return True
        
        # Check explicit access policy
        result = await self.db.execute(
            select(AccessPolicy)
            .where(
                AccessPolicy.user_id == user.id,
                AccessPolicy.document_id == document_id,
            )
        )
        policy = result.scalar_one_or_none()
        
        if policy:
            # Check expiration
            if policy.expires_at and policy.expires_at < datetime.now(timezone.utc):
                return False
            
            # Check permission level
            permission_order = {
                Permission.READ: 0,
                Permission.WRITE: 1,
                Permission.DELETE: 2,
                Permission.ADMIN: 3,
            }
            return permission_order[policy.permission] >= permission_order[required_permission]
        
        # Check project-level access
        if document.project_id:
            result = await self.db.execute(
                select(AccessPolicy)
                .where(
                    AccessPolicy.user_id == user.id,
                    AccessPolicy.project_id == document.project_id,
                )
            )
            project_policy = result.scalar_one_or_none()
            if project_policy:
                if project_policy.expires_at and project_policy.expires_at < datetime.now(timezone.utc):
                    return False
                permission_order = {
                    Permission.READ: 0,
                    Permission.WRITE: 1,
                    Permission.DELETE: 2,
                    Permission.ADMIN: 3,
                }
                return permission_order[project_policy.permission] >= permission_order[required_permission]
        
        return False
    
    async def get_accessible_document_ids(
        self,
        user: User,
    ) -> list[uuid.UUID] | None:
        """
        Get list of document IDs user can access
        Returns None if user has unrestricted access (admin)
        """
        if user.role == UserRole.ADMIN:
            return None  # No filter needed
        
        # Get documents from:
        # 1. User's department
        # 2. User's uploaded documents
        # 3. Explicit access policies
        # 4. Project access policies
        
        accessible_ids = set()
        
        # User's department documents
        if user.department_id:
            result = await self.db.execute(
                select(Document.id)
                .where(
                    Document.department_id == user.department_id,
                    Document.deleted_at.is_(None),
                )
            )
            for row in result:
                accessible_ids.add(row[0])
        
        # User's uploaded documents
        result = await self.db.execute(
            select(Document.id)
            .where(
                Document.uploaded_by == user.id,
                Document.deleted_at.is_(None),
            )
        )
        for row in result:
            accessible_ids.add(row[0])
        
        # Explicit document access
        result = await self.db.execute(
            select(AccessPolicy.document_id)
            .where(
                AccessPolicy.user_id == user.id,
                AccessPolicy.document_id.isnot(None),
            )
        )
        for row in result:
            if row[0]:
                accessible_ids.add(row[0])
        
        # Project access -> documents in that project
        result = await self.db.execute(
            select(AccessPolicy.project_id)
            .where(
                AccessPolicy.user_id == user.id,
                AccessPolicy.project_id.isnot(None),
            )
        )
        project_ids = [row[0] for row in result if row[0]]
        
        if project_ids:
            result = await self.db.execute(
                select(Document.id)
                .where(
                    Document.project_id.in_(project_ids),
                    Document.deleted_at.is_(None),
                )
            )
            for row in result:
                accessible_ids.add(row[0])
        
        return list(accessible_ids)
    
    async def grant_access(
        self,
        granter: User,
        user_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        permission: Permission = Permission.READ,
        expires_at: datetime | None = None,
    ) -> AccessPolicy:
        """Grant access to a user"""
        policy = AccessPolicy(
            user_id=user_id,
            document_id=document_id,
            project_id=project_id,
            permission=permission,
            granted_by=granter.id,
            expires_at=expires_at,
        )
        self.db.add(policy)
        
        # Log
        await self._log_audit(
            user_id=granter.id,
            action=AuditAction.PERMISSION_CHANGE,
            resource_type="access_policy",
            resource_id=str(document_id or project_id),
            details={
                "target_user": str(user_id),
                "permission": permission.value,
                "action": "grant",
            },
        )
        
        await self.db.flush()
        return policy
    
    async def revoke_access(
        self,
        revoker: User,
        policy_id: uuid.UUID,
    ) -> bool:
        """Revoke access policy"""
        result = await self.db.execute(
            select(AccessPolicy).where(AccessPolicy.id == policy_id)
        )
        policy = result.scalar_one_or_none()
        
        if not policy:
            return False
        
        await self.db.delete(policy)
        
        # Log
        await self._log_audit(
            user_id=revoker.id,
            action=AuditAction.PERMISSION_CHANGE,
            resource_type="access_policy",
            resource_id=str(policy_id),
            details={
                "target_user": str(policy.user_id),
                "action": "revoke",
            },
        )
        
        return True
    
    async def _log_audit(
        self,
        user_id: uuid.UUID | None,
        action: AuditAction,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log an audit event"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
