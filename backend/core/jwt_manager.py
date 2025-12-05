"""
Gemini Ultra Gateway - JWT Manager
Handles JWT token generation and refresh for Gemini Business API
"""

import json
import time
import hmac
import hashlib
import base64
import asyncio
import logging
from typing import Optional, TYPE_CHECKING
from datetime import datetime

import httpx

from .config import Config, GeminiEndpoints, BEIJING_TZ

if TYPE_CHECKING:
    from .account_pool import Account

logger = logging.getLogger("gemini.jwt")


def urlsafe_b64encode(data: bytes) -> str:
    """URL-safe base64 encoding without padding"""
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def kq_encode(s: str) -> str:
    """Custom encoding for JWT payload"""
    b = bytearray()
    for ch in s:
        v = ord(ch)
        if v > 255:
            b.append(v & 255)
            b.append(v >> 8)
        else:
            b.append(v)
    return urlsafe_b64encode(bytes(b))


def create_jwt(key_bytes: bytes, key_id: str, csesidx: str) -> str:
    """Create a JWT token for Gemini Business API"""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {
        "iss": "https://business.gemini.google",
        "aud": "https://biz-discoveryengine.googleapis.com",
        "sub": f"csesidx/{csesidx}",
        "iat": now,
        "exp": now + 300,
        "nbf": now,
    }
    header_b64 = kq_encode(json.dumps(header, separators=(",", ":")))
    payload_b64 = kq_encode(json.dumps(payload, separators=(",", ":")))
    message = f"{header_b64}.{payload_b64}"
    sig = hmac.new(key_bytes, message.encode(), hashlib.sha256).digest()
    return f"{message}.{urlsafe_b64encode(sig)}"


class JWTManager:
    """Manages JWT tokens for a single account"""
    
    def __init__(self, account: "Account", http_client: httpx.AsyncClient) -> None:
        self.account = account
        self.http_client = http_client
        self.jwt: str = ""
        self.expires: float = 0
        self._lock = asyncio.Lock()
        self._cookie_expires_at: Optional[datetime] = None
    
    async def get(self) -> str:
        """Get a valid JWT token, refreshing if necessary"""
        async with self._lock:
            if time.time() > self.expires:
                await self._refresh()
            return self.jwt
    
    async def _refresh(self) -> None:
        """Refresh the JWT token"""
        cookie = f"__Secure-C_SES={self.account.secure_c_ses}"
        if self.account.host_c_oses:
            cookie += f"; __Host-C_OSES={self.account.host_c_oses}"
        
        logger.debug(f"Refreshing JWT for account: {self.account.name}")
        
        try:
            response = await self.http_client.get(
                GeminiEndpoints.GETOXSRF,
                params={"csesidx": self.account.csesidx},
                headers={
                    "cookie": cookie,
                    "user-agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/140.0.0.0 Safari/537.36"
                    ),
                    "referer": "https://business.gemini.google/",
                },
            )
            
            if response.status_code != 200:
                logger.error(
                    f"getoxsrf failed [{self.account.name}]: {response.status_code} {response.text}"
                )
                if response.status_code in (401, 403, 429):
                    self.account.mark_quota_error(response.status_code, response.text)
                raise Exception(f"getoxsrf failed: {response.status_code}")
            
            # Parse cookie expiration from response headers
            self._parse_cookie_expiration(response)
            
            # Parse response
            txt = response.text[4:] if response.text.startswith(")]}'") else response.text
            data = json.loads(txt)
            
            key_bytes = base64.urlsafe_b64decode(data["xsrfToken"] + "==")
            self.jwt = create_jwt(key_bytes, data["keyId"], self.account.csesidx)
            self.expires = time.time() + Config.JWT_TTL_SECONDS
            
            logger.info(f"JWT refreshed successfully [{self.account.name}]")
            
        except Exception as e:
            logger.error(f"JWT refresh failed [{self.account.name}]: {e}")
            raise
    
    def _parse_cookie_expiration(self, response: httpx.Response) -> None:
        """Parse cookie expiration from response headers"""
        try:
            set_cookie_headers = []
            if hasattr(response.headers, 'get_list'):
                set_cookie_headers = response.headers.get_list("set-cookie", [])
            elif hasattr(response.headers, 'getall'):
                set_cookie_headers = response.headers.getall("set-cookie", [])
            else:
                header = response.headers.get("set-cookie")
                if header:
                    set_cookie_headers = [header]
            
            if not set_cookie_headers:
                return
            
            from http.cookies import SimpleCookie
            from email.utils import parsedate_to_datetime
            from datetime import timedelta
            
            for set_cookie in set_cookie_headers:
                try:
                    cookie_obj = SimpleCookie()
                    cookie_obj.load(set_cookie)
                    for cookie_name, cookie_attrs in cookie_obj.items():
                        if cookie_name in ("__Secure-C_SES", "__Host-C_OSES"):
                            if "expires" in cookie_attrs:
                                expires_str = cookie_attrs["expires"]
                                try:
                                    expires_dt = parsedate_to_datetime(expires_str)
                                    if expires_dt.tzinfo:
                                        expires_dt = expires_dt.astimezone(BEIJING_TZ)
                                        self._cookie_expires_at = expires_dt.replace(tzinfo=None)
                                    else:
                                        self._cookie_expires_at = expires_dt
                                    logger.debug(f"Cookie expires at: {self._cookie_expires_at}")
                                    return
                                except (ValueError, TypeError):
                                    pass
                            elif "max-age" in cookie_attrs:
                                try:
                                    max_age = int(cookie_attrs["max-age"])
                                    self._cookie_expires_at = datetime.now(BEIJING_TZ) + timedelta(seconds=max_age)
                                    logger.debug(f"Cookie expires at (from max-age): {self._cookie_expires_at}")
                                    return
                                except (ValueError, TypeError):
                                    pass
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Failed to parse cookie expiration: {e}")
    
    @property
    def cookie_expires_at(self) -> Optional[datetime]:
        """Get the cookie expiration time"""
        return self._cookie_expires_at
    
    def is_token_valid(self) -> bool:
        """Check if the current token is still valid"""
        return self.jwt and time.time() < self.expires
    
    def invalidate(self) -> None:
        """Invalidate the current token"""
        self.jwt = ""
        self.expires = 0
