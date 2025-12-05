"""
Gemini Ultra Gateway - Automation Module
Auto-login and cookie refresh functionality
"""

from .cookie_refresh import CookieRefreshManager, get_cookie_refresh_manager
from .tempmail_api import TempMailClient

__all__ = [
    "CookieRefreshManager",
    "get_cookie_refresh_manager",
    "TempMailClient",
]
