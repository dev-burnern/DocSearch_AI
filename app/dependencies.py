"""
FastAPI Dependencies
의존성 주입 모듈
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_db
from app.db.models import Permission, User
from app.services.auth import AuthService

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    """Get authentication service"""
    return AuthService(db)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    x_api_key: Annotated[str | None, Header()] = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """
    Get current authenticated user (authentication disabled - returns first user)
    """
    from sqlalchemy import select
    from app.db.models import User, UserRole, Classification
    import uuid
    
    # Return any user from database (for no-auth mode)
    result = await db.execute(select(User).where(User.is_active == True).limit(1))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create a temporary system user if no users exist
        user = User(
            id=uuid.uuid4(),
            username="system",
            email="system@localhost",
            password_hash="",
            full_name="System User",
            role=UserRole.ADMIN,
            max_classification=Classification.RESTRICTED,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user"""
    return current_user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current admin user"""
    from app.db.models import UserRole
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다",
        )
    return current_user


async def get_optional_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> User | None:
    """Get current user if authenticated (authentication disabled - returns first user)"""
    from sqlalchemy import select
    from app.db.models import User
    
    result = await db.execute(select(User).where(User.is_active == True).limit(1))
    return result.scalar_one_or_none()


class DocumentAccessChecker:
    """Dependency for checking document access"""
    
    def __init__(self, required_permission: Permission = Permission.READ):
        self.required_permission = required_permission
    
    async def __call__(
        self,
        document_id: uuid.UUID,
        current_user: Annotated[User, Depends(get_current_user)],
        auth_service: AuthService = Depends(get_auth_service),
    ) -> uuid.UUID:
        has_access = await auth_service.check_document_access(
            current_user,
            document_id,
            self.required_permission,
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 문서에 대한 접근 권한이 없습니다",
            )
        
        return document_id


# Pre-configured access checkers
require_read_access = DocumentAccessChecker(Permission.READ)
require_write_access = DocumentAccessChecker(Permission.WRITE)
require_delete_access = DocumentAccessChecker(Permission.DELETE)
