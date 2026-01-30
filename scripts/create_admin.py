#!/usr/bin/env python3
"""
초기 관리자 계정 생성 스크립트
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.base import async_session_maker
from app.db.models import User, UserRole, Classification
from app.core.security import get_password_hash


async def create_admin():
    """Create initial admin user"""
    admin_username = "admin"
    admin_password = "admin123"  # Change this!
    admin_email = "admin@docsearch.local"
    
    async with async_session_maker() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.username == admin_username)
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"❌ Admin user '{admin_username}' already exists!")
            return
        
        # Create admin user
        admin_user = User(
            username=admin_username,
            email=admin_email,
            full_name="System Administrator",
            password_hash=get_password_hash(admin_password),
            role=UserRole.ADMIN,
            max_classification=Classification.RESTRICTED,
            is_active=True,
        )
        
        session.add(admin_user)
        await session.commit()
        
        print("✅ Initial admin user created successfully!")
        print(f"   Username: {admin_username}")
        print(f"   Password: {admin_password}")
        print(f"   Email: {admin_email}")
        print("\n⚠️  Please change the password after first login!")


if __name__ == "__main__":
    asyncio.run(create_admin())
