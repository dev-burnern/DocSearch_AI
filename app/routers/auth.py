"""
Authentication API Router
인증 관련 API 엔드포인트
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User, UserRole, Classification
from app.services.auth import AuthService
from app.dependencies import get_auth_service, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response Models
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    department_id: str | None
    department_name: str | None
    max_classification: str
    is_active: bool
    
    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


# Endpoints
@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """로그인하여 액세스 토큰을 받습니다"""
    user, error = await auth_service.authenticate_user(
        data.username,
        data.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
        )
    
    tokens = await auth_service.create_tokens(user)
    return TokenResponse(**tokens)


@router.post("/register", response_model=UserResponse)
async def register(
    data: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """새 사용자를 등록합니다 (관리자 승인 필요)"""
    # Check if username or email exists
    from sqlalchemy import select
    from app.db.models import User
    
    existing = await db.execute(
        select(User).where(
            (User.username == data.username) | (User.email == data.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 사용자명 또는 이메일입니다",
        )
    
    user = await auth_service.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
    )
    
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        department_id=str(user.department_id) if user.department_id else None,
        department_name=None,
        max_classification=user.max_classification.value,
        is_active=user.is_active,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """리프레시 토큰으로 새 액세스 토큰을 발급합니다"""
    tokens = await auth_service.refresh_tokens(data.refresh_token)
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 리프레시 토큰입니다",
        )
    
    return TokenResponse(**tokens)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """현재 로그인한 사용자 정보를 조회합니다"""
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        department_id=str(current_user.department_id) if current_user.department_id else None,
        department_name=current_user.department.name if current_user.department else None,
        max_classification=current_user.max_classification.value,
        is_active=current_user.is_active,
    )


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """비밀번호를 변경합니다"""
    from app.core.security import verify_password, hash_password
    
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다",
        )
    
    current_user.password_hash = hash_password(data.new_password)
    await db.commit()
    
    return {"message": "비밀번호가 변경되었습니다"}


@router.post("/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """로그아웃합니다 (클라이언트에서 토큰 삭제 필요)"""
    # In a stateless JWT setup, logout is handled client-side
    # For enhanced security, you could add token to a blacklist in Redis
    return {"message": "로그아웃되었습니다"}
