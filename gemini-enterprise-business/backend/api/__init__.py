"""
Gemini Ultra Gateway - API Module
"""

from .openai_compat import router as openai_router
from .media_studio import router as media_router
from .admin import router as admin_router

__all__ = [
    "openai_router",
    "media_router",
    "admin_router",
]
