# API Routers
from .auth import router as auth_router
from .documents import router as documents_router
from .search import router as search_router
from .chat import router as chat_router
from .admin import router as admin_router

__all__ = [
    "auth_router",
    "documents_router",
    "search_router",
    "chat_router",
    "admin_router",
]
