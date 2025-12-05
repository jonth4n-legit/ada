"""
Gemini Ultra Gateway - Account Pool Manager
Multi-account management with load balancing and failover

Supports loading accounts from:
1. Database (primary, managed via dashboard)
2. Environment variables (fallback for essential config)
"""

import os
import time
import logging
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from .config import Config, BEIJING_TZ
from .jwt_manager import JWTManager

logger = logging.getLogger("gemini.account")

# Database session will be imported lazily to avoid circular imports
_db_session = None

def get_db_session():
    """Get database session (lazy import to avoid circular imports)"""
    global _db_session
    if _db_session is None:
        try:
            from database import get_db
            _db_session = get_db
        except ImportError:
            _db_session = lambda: None
    return _db_session()


@dataclass
class Account:
    """Represents a Gemini Business account"""
    name: str
    secure_c_ses: str
    csesidx: str
    config_id: str
    host_c_oses: Optional[str] = None
    
    # Runtime state
    jwt_mgr: Optional[JWTManager] = field(default=None, repr=False)
    disabled_until: float = 0.0
    fail_count: int = 0
    last_used_at: Optional[datetime] = None
    last_error: Optional[str] = None
    
    # Cookie status
    cookie_status: str = "unknown"  # valid, expired, unknown
    cookie_expires_at: Optional[datetime] = None
    
    def is_available(self) -> bool:
        """Check if the account is available for use"""
        return time.time() >= self.disabled_until and self.fail_count < 3
    
    def mark_quota_error(self, status_code: int, detail: str = "") -> None:
        """Mark the account as temporarily unavailable due to quota error"""
        if status_code in (401, 403):
            cooldown = Config.AUTH_ERROR_COOLDOWN_SECONDS
        elif status_code == 429:
            cooldown = Config.RATE_LIMIT_COOLDOWN_SECONDS
        else:
            cooldown = Config.ACCOUNT_COOLDOWN_SECONDS
        
        self.disabled_until = max(self.disabled_until, time.time() + cooldown)
        self.fail_count += 1
        self.last_error = f"HTTP {status_code}: {detail[:200]}" if detail else f"HTTP {status_code}"
        
        logger.warning(
            f"Account [{self.name}] marked unavailable for {cooldown}s "
            f"(status={status_code}, fail_count={self.fail_count})"
        )
    
    def mark_success(self) -> None:
        """Mark successful use of the account"""
        self.fail_count = 0
        self.last_error = None
        self.last_used_at = datetime.now(BEIJING_TZ)
    
    def reset_cooldown(self) -> None:
        """Reset the cooldown period"""
        self.disabled_until = 0.0
        self.fail_count = 0
        self.last_error = None
    
    def get_remaining_cooldown(self) -> int:
        """Get remaining cooldown time in seconds"""
        remaining = self.disabled_until - time.time()
        return max(0, int(remaining))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert account to dictionary representation"""
        return {
            "name": self.name,
            "secure_c_ses": self.secure_c_ses[:20] + "..." if self.secure_c_ses else "",
            "csesidx": self.csesidx,
            "config_id": self.config_id,
            "host_c_oses": self.host_c_oses[:20] + "..." if self.host_c_oses else "",
            "is_available": self.is_available(),
            "fail_count": self.fail_count,
            "last_error": self.last_error,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "remaining_cooldown": self.get_remaining_cooldown(),
            "cookie_status": self.cookie_status,
            "cookie_expires_at": self.cookie_expires_at.isoformat() if self.cookie_expires_at else None,
        }


class AccountPool:
    """Manages a pool of Gemini Business accounts with load balancing"""
    
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self.accounts: List[Account] = []
        self.http_client = http_client
        self._rr_index = 0
        self._lock = asyncio.Lock()
        
        # Session cache: conversation_key -> {session_id, account_name, updated_at}
        self._session_cache: Dict[str, Dict[str, Any]] = {}
    
    def load_from_env(self) -> None:
        """Load accounts from environment variables"""
        accounts = []
        
        # Support ACCOUNT1_*, ACCOUNT2_*, ... format
        account_indices = set()
        for key in os.environ.keys():
            if key.startswith("ACCOUNT") and key.endswith("_SECURE_C_SES"):
                idx_str = key[len("ACCOUNT"):-len("_SECURE_C_SES")]
                try:
                    idx = int(idx_str)
                    account_indices.add(idx)
                except ValueError:
                    continue
        
        for idx in sorted(account_indices):
            prefix = f"ACCOUNT{idx}_"
            secure = os.getenv(prefix + "SECURE_C_SES")
            csesidx = os.getenv(prefix + "CSESIDX")
            config_id = os.getenv(prefix + "CONFIG_ID")
            host = os.getenv(prefix + "HOST_C_OSES")
            
            if not (secure and csesidx and config_id):
                logger.warning(f"Account index {idx} incomplete, skipping")
                continue
            
            # Clean up values
            secure = secure.strip().strip('"').strip("'") if secure else None
            csesidx = csesidx.strip().strip('"').strip("'") if csesidx else None
            config_id = config_id.strip().strip('"').strip("'") if config_id else None
            if config_id and '?csesidx' in config_id:
                config_id = config_id.split('?csesidx')[0]
            host = host.strip().strip('"').strip("'") if host else None
            
            name = os.getenv(prefix + "NAME") or f"account-{idx}"
            name = name.strip().strip('"').strip("'") if name else f"account-{idx}"
            
            account = Account(
                name=name,
                secure_c_ses=secure,
                csesidx=csesidx,
                config_id=config_id,
                host_c_oses=host,
            )
            account.jwt_mgr = JWTManager(account, self.http_client)
            accounts.append(account)
        
        # Fallback to legacy single account format
        if not accounts:
            secure = os.getenv("SECURE_C_SES")
            csesidx = os.getenv("CSESIDX")
            config_id = os.getenv("CONFIG_ID")
            host = os.getenv("HOST_C_OSES")
            
            if secure and csesidx and config_id:
                account = Account(
                    name="default",
                    secure_c_ses=secure,
                    csesidx=csesidx,
                    config_id=config_id,
                    host_c_oses=host,
                )
                account.jwt_mgr = JWTManager(account, self.http_client)
                accounts.append(account)
        
        self.accounts = accounts
        logger.info(f"Loaded {len(accounts)} accounts from environment")
    
    def load_from_db(self) -> int:
        """Load accounts from database (primary source)"""
        db = get_db_session()
        if not db:
            logger.warning("Database not available, cannot load accounts from DB")
            return 0
        
        try:
            from database.models import Account as AccountModel
            
            # Get all active accounts from database
            db_accounts = db.query(AccountModel).filter(
                AccountModel.is_active == True
            ).order_by(AccountModel.is_default.desc(), AccountModel.id.asc()).all()
            
            loaded = 0
            for db_acc in db_accounts:
                # Check if account already exists in pool
                existing = self.get_account(db_acc.name)
                if existing:
                    # Update existing account credentials
                    existing.secure_c_ses = db_acc.secure_c_ses
                    existing.csesidx = db_acc.csesidx
                    existing.config_id = db_acc.config_id
                    existing.host_c_oses = db_acc.host_c_oses
                    existing.cookie_status = db_acc.cookie_status
                    existing.cookie_expires_at = db_acc.cookie_expires_at
                    logger.debug(f"Updated existing account: {db_acc.name}")
                else:
                    # Create new account
                    account = Account(
                        name=db_acc.name,
                        secure_c_ses=db_acc.secure_c_ses,
                        csesidx=db_acc.csesidx,
                        config_id=db_acc.config_id,
                        host_c_oses=db_acc.host_c_oses,
                        cookie_status=db_acc.cookie_status,
                        cookie_expires_at=db_acc.cookie_expires_at,
                    )
                    account.jwt_mgr = JWTManager(account, self.http_client)
                    self.accounts.append(account)
                    logger.debug(f"Loaded account from DB: {db_acc.name}")
                loaded += 1
            
            logger.info(f"Loaded {loaded} accounts from database")
            return loaded
            
        except Exception as e:
            logger.error(f"Failed to load accounts from database: {e}")
            return 0
    
    def sync_to_db(self, account: Account) -> bool:
        """Sync account runtime state back to database"""
        db = get_db_session()
        if not db:
            return False
        
        try:
            from database.models import Account as AccountModel
            
            db_acc = db.query(AccountModel).filter(
                AccountModel.name == account.name
            ).first()
            
            if db_acc:
                db_acc.cookie_status = account.cookie_status
                db_acc.cookie_expires_at = account.cookie_expires_at
                db_acc.fail_count = account.fail_count
                db_acc.last_error = account.last_error
                db_acc.last_used_at = account.last_used_at
                db.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to sync account to database: {e}")
            db.rollback()
            return False
    
    def reload_accounts(self) -> int:
        """Reload accounts from both database and environment"""
        # First try database
        db_count = self.load_from_db()
        
        # If no accounts from DB, fall back to environment
        if db_count == 0 and len(self.accounts) == 0:
            logger.info("No accounts in database, loading from environment")
            self.load_from_env()
        
        return len(self.accounts)
    
    def add_account(self, account: Account) -> None:
        """Add a new account to the pool"""
        account.jwt_mgr = JWTManager(account, self.http_client)
        self.accounts.append(account)
        logger.info(f"Added account: {account.name}")
    
    def remove_account(self, name: str) -> bool:
        """Remove an account from the pool"""
        for i, acc in enumerate(self.accounts):
            if acc.name == name:
                self.accounts.pop(i)
                logger.info(f"Removed account: {name}")
                return True
        return False
    
    def get_account(self, name: str) -> Optional[Account]:
        """Get an account by name"""
        for acc in self.accounts:
            if acc.name == name:
                return acc
        return None
    
    async def get_next_available(self) -> Optional[Account]:
        """Get the next available account using round-robin"""
        async with self._lock:
            n = len(self.accounts)
            if n == 0:
                return None
            
            # Try round-robin
            for _ in range(n):
                acc = self.accounts[self._rr_index % n]
                self._rr_index = (self._rr_index + 1) % n
                if acc.is_available():
                    return acc
            
            # All accounts unavailable, return the one with shortest cooldown
            return min(self.accounts, key=lambda a: a.disabled_until)
    
    async def get_for_conversation(self, conv_key: str) -> Account:
        """Get account for a specific conversation (session affinity)"""
        cached = self._session_cache.get(conv_key)
        if cached:
            acc_name = cached.get("account")
            for acc in self.accounts:
                if acc.name == acc_name and acc.is_available():
                    return acc
        
        # No cached session or account unavailable, get next available
        account = await self.get_next_available()
        if not account:
            raise RuntimeError("No accounts available")
        return account
    
    def cache_session(self, conv_key: str, session_id: str, account_name: str) -> None:
        """Cache a session for conversation affinity"""
        self._session_cache[conv_key] = {
            "session_id": session_id,
            "account": account_name,
            "updated_at": time.time(),
        }
    
    def get_cached_session(self, conv_key: str) -> Optional[Dict[str, Any]]:
        """Get cached session for a conversation"""
        return self._session_cache.get(conv_key)
    
    def clear_old_sessions(self, max_age_seconds: int = 3600) -> int:
        """Clear sessions older than max_age_seconds"""
        now = time.time()
        old_keys = [
            k for k, v in self._session_cache.items()
            if now - v.get("updated_at", 0) > max_age_seconds
        ]
        for k in old_keys:
            del self._session_cache[k]
        return len(old_keys)
    
    def get_alternative(self, exclude_name: str) -> Optional[Account]:
        """Get an alternative account excluding a specific one"""
        for acc in self.accounts:
            if acc.name != exclude_name and acc.is_available():
                return acc
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        total = len(self.accounts)
        available = sum(1 for acc in self.accounts if acc.is_available())
        return {
            "total_accounts": total,
            "available_accounts": available,
            "unavailable_accounts": total - available,
            "cached_sessions": len(self._session_cache),
            "accounts": [acc.to_dict() for acc in self.accounts],
        }


# Global HTTP client for the account pool
_http_client: Optional[httpx.AsyncClient] = None
_account_pool: Optional[AccountPool] = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create the global HTTP client"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            proxy=Config.PROXY,
            verify=False,
            http2=False,
            timeout=httpx.Timeout(Config.TIMEOUT_SECONDS, connect=60.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
        if Config.PROXY:
            logger.info(f"HTTP client created with proxy: {Config.PROXY}")
        else:
            logger.info("HTTP client created (direct connection)")
    return _http_client


def get_account_pool() -> AccountPool:
    """Get or create the global account pool
    
    Loading priority:
    1. Database accounts (managed via dashboard)
    2. Environment variables (fallback)
    """
    global _account_pool
    if _account_pool is None:
        _account_pool = AccountPool(get_http_client())
        
        # Try loading from database first
        db_count = _account_pool.load_from_db()
        
        # Fall back to environment if no accounts in database
        if db_count == 0:
            logger.info("No accounts in database, loading from environment variables")
            _account_pool.load_from_env()
        
    return _account_pool


def reset_account_pool():
    """Reset the global account pool (forces reload on next get)"""
    global _account_pool
    _account_pool = None
    logger.info("Account pool reset - will reload on next request")


async def close_http_client() -> None:
    """Close the global HTTP client"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
