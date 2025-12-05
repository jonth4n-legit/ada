"""
Gemini Ultra Gateway - Admin API
Admin panel endpoints for account and API key management
"""

import os
import time
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from ..database import get_db, Admin, APIKey, APICallLog, Account, Settings
from ..core.config import Config
from ..core.account_pool import get_account_pool, reset_account_pool

logger = logging.getLogger("gemini.api.admin")

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============== Models ==============

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: Optional[str] = None


class CreateAPIKeyRequest(BaseModel):
    name: str
    expires_days: Optional[int] = None
    rate_limit_rpm: int = 60
    rate_limit_rpd: int = 1000


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    total_requests: int
    last_used_at: Optional[datetime]


class AccountResponse(BaseModel):
    name: str
    is_available: bool
    fail_count: int
    last_error: Optional[str]
    remaining_cooldown: int
    cookie_status: str


class StatsResponse(BaseModel):
    total_accounts: int
    available_accounts: int
    total_api_keys: int
    active_api_keys: int
    total_requests_today: int
    total_tokens_today: int


# Database Account Models
class CreateAccountRequest(BaseModel):
    name: str
    secure_c_ses: str
    csesidx: str
    config_id: str
    host_c_oses: str
    is_default: bool = False
    notes: Optional[str] = None


class UpdateAccountRequest(BaseModel):
    name: Optional[str] = None
    secure_c_ses: Optional[str] = None
    csesidx: Optional[str] = None
    config_id: Optional[str] = None
    host_c_oses: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    notes: Optional[str] = None


class DbAccountResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    is_default: bool
    cookie_status: str
    cookie_expires_at: Optional[datetime]
    fail_count: int
    last_error: Optional[str]
    last_used_at: Optional[datetime]
    total_requests: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


# Settings Models
class UpdateSettingRequest(BaseModel):
    value: str
    value_type: str = "string"  # string, int, bool, json


class SettingResponse(BaseModel):
    id: int
    key: str
    value: str
    value_type: str
    description: Optional[str]
    updated_at: datetime


# ============== Auth ==============

def generate_admin_token(admin_id: int) -> str:
    """Generate a simple admin token"""
    import hashlib
    import json
    import base64
    
    payload = {
        "admin_id": admin_id,
        "exp": int(time.time()) + 86400,  # 24 hours
        "iat": int(time.time()),
    }
    
    payload_str = json.dumps(payload)
    payload_b64 = base64.urlsafe_b64encode(payload_str.encode()).decode().rstrip("=")
    
    # Simple signature
    secret = Config.SECRET_KEY.encode()
    sig = hashlib.sha256(secret + payload_b64.encode()).hexdigest()[:32]
    
    return f"{payload_b64}.{sig}"


def verify_admin_token(token: str) -> Optional[int]:
    """Verify admin token and return admin_id"""
    import hashlib
    import json
    import base64
    
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        
        payload_b64, sig = parts
        
        # Verify signature
        secret = Config.SECRET_KEY.encode()
        expected_sig = hashlib.sha256(secret + payload_b64.encode()).hexdigest()[:32]
        
        if sig != expected_sig:
            return None
        
        # Decode payload
        padding = "=" * (4 - len(payload_b64) % 4)
        payload_str = base64.urlsafe_b64decode(payload_b64 + padding).decode()
        payload = json.loads(payload_str)
        
        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None
        
        return payload.get("admin_id")
    except Exception:
        return None


async def get_current_admin(
    request: Request,
    db: Session = Depends(get_db)
) -> Admin:
    """Get current admin from token"""
    # Get token from header or cookie
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        token = request.cookies.get("admin_token", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_id = verify_admin_token(token)
    if admin_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    admin = db.query(Admin).filter(Admin.id == admin_id, Admin.is_active == True).first()
    if admin is None:
        raise HTTPException(status_code=401, detail="Admin not found")
    
    return admin


# ============== Auth Endpoints ==============

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Admin login"""
    admin = db.query(Admin).filter(
        Admin.username == request.username,
        Admin.is_active == True
    ).first()
    
    if admin is None or not bcrypt.verify(request.password, admin.password_hash):
        return LoginResponse(success=False, message="Invalid username or password")
    
    # Update last login
    admin.last_login_at = datetime.utcnow()
    db.commit()
    
    # Generate token
    token = generate_admin_token(admin.id)
    
    return LoginResponse(success=True, token=token)


@router.post("/logout")
async def logout():
    """Admin logout"""
    return {"success": True, "message": "Logged out"}


@router.get("/me")
async def get_me(admin: Admin = Depends(get_current_admin)):
    """Get current admin info"""
    return {
        "id": admin.id,
        "username": admin.username,
        "created_at": admin.created_at,
        "last_login_at": admin.last_login_at,
    }


# ============== API Key Management ==============

@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all API keys"""
    keys = db.query(APIKey).order_by(APIKey.created_at.desc()).all()
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            created_at=k.created_at,
            expires_at=k.expires_at,
            is_active=k.is_active,
            total_requests=k.total_requests,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]


@router.post("/api-keys")
async def create_api_key(
    request: CreateAPIKeyRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new API key"""
    # Generate key
    raw_key = f"sk-{secrets.token_urlsafe(32)}"
    key_prefix = raw_key[:10]
    key_hash = bcrypt.hash(raw_key)
    
    # Calculate expiration
    expires_at = None
    if request.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
    
    # Create key
    api_key = APIKey(
        name=request.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        expires_at=expires_at,
        rate_limit_rpm=request.rate_limit_rpm,
        rate_limit_rpd=request.rate_limit_rpd,
        created_by=admin.id,
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    logger.info(f"API key created: {request.name} by {admin.username}")
    
    # Return the raw key (only shown once!)
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": raw_key,  # Only returned on creation!
        "key_prefix": key_prefix,
        "expires_at": expires_at,
        "message": "Save this key! It will only be shown once.",
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete an API key"""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(api_key)
    db.commit()
    
    logger.info(f"API key deleted: {api_key.name} by {admin.username}")
    
    return {"success": True, "message": "API key deleted"}


@router.post("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    key_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Toggle API key active status"""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = not api_key.is_active
    db.commit()
    
    status = "activated" if api_key.is_active else "deactivated"
    logger.info(f"API key {status}: {api_key.name} by {admin.username}")
    
    return {"success": True, "is_active": api_key.is_active}


# ============== Account Management ==============

@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(admin: Admin = Depends(get_current_admin)):
    """List all Gemini accounts"""
    pool = get_account_pool()
    
    return [
        AccountResponse(
            name=acc.name,
            is_available=acc.is_available(),
            fail_count=acc.fail_count,
            last_error=acc.last_error,
            remaining_cooldown=acc.get_remaining_cooldown(),
            cookie_status=acc.cookie_status,
        )
        for acc in pool.accounts
    ]


@router.post("/accounts/{account_name}/reset")
async def reset_account(
    account_name: str,
    admin: Admin = Depends(get_current_admin)
):
    """Reset account cooldown"""
    pool = get_account_pool()
    account = pool.get_account(account_name)
    
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.reset_cooldown()
    logger.info(f"Account reset: {account_name} by {admin.username}")
    
    return {"success": True, "message": f"Account {account_name} cooldown reset"}


# ============== Stats ==============

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get system statistics"""
    pool = get_account_pool()
    
    # Account stats
    total_accounts = len(pool.accounts)
    available_accounts = sum(1 for acc in pool.accounts if acc.is_available())
    
    # API key stats
    total_api_keys = db.query(APIKey).count()
    active_api_keys = db.query(APIKey).filter(APIKey.is_active == True).count()
    
    # Today's usage
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_logs = db.query(APICallLog).filter(APICallLog.created_at >= today_start).all()
    
    total_requests_today = len(today_logs)
    total_tokens_today = sum(log.total_tokens for log in today_logs)
    
    return StatsResponse(
        total_accounts=total_accounts,
        available_accounts=available_accounts,
        total_api_keys=total_api_keys,
        active_api_keys=active_api_keys,
        total_requests_today=total_requests_today,
        total_tokens_today=total_tokens_today,
    )


@router.get("/logs")
async def get_logs(
    limit: int = 100,
    offset: int = 0,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get API call logs"""
    logs = db.query(APICallLog).order_by(
        APICallLog.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "endpoint": log.endpoint,
            "method": log.method,
            "model": log.model,
            "status_code": log.status_code,
            "response_time_ms": log.response_time_ms,
            "total_tokens": log.total_tokens,
            "account_used": log.account_used,
            "error_message": log.error_message,
            "created_at": log.created_at,
        }
        for log in logs
    ]


# ============== Database Account Management ==============

@router.get("/db-accounts", response_model=List[DbAccountResponse])
async def list_db_accounts(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all database-managed accounts"""
    accounts = db.query(Account).order_by(Account.created_at.desc()).all()
    return [
        DbAccountResponse(
            id=acc.id,
            name=acc.name,
            is_active=acc.is_active,
            is_default=acc.is_default,
            cookie_status=acc.cookie_status,
            cookie_expires_at=acc.cookie_expires_at,
            fail_count=acc.fail_count,
            last_error=acc.last_error,
            last_used_at=acc.last_used_at,
            total_requests=acc.total_requests,
            notes=acc.notes,
            created_at=acc.created_at,
            updated_at=acc.updated_at,
        )
        for acc in accounts
    ]


@router.get("/db-accounts/{account_id}")
async def get_db_account(
    account_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a single database account with credentials (masked)"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account.to_dict()


@router.post("/db-accounts")
async def create_db_account(
    request: CreateAccountRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new database-managed account"""
    # Check for duplicate name
    existing = db.query(Account).filter(Account.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account name already exists")
    
    # If setting as default, unset other defaults
    if request.is_default:
        db.query(Account).filter(Account.is_default == True).update({"is_default": False})
    
    account = Account(
        name=request.name,
        secure_c_ses=request.secure_c_ses,
        csesidx=request.csesidx,
        config_id=request.config_id,
        host_c_oses=request.host_c_oses,
        is_default=request.is_default,
        notes=request.notes,
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    logger.info(f"Database account created: {request.name} by {admin.username}")
    
    return {
        "success": True,
        "id": account.id,
        "name": account.name,
        "message": "Account created successfully. Reload accounts to apply changes.",
    }


@router.put("/db-accounts/{account_id}")
async def update_db_account(
    account_id: int,
    request: UpdateAccountRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a database-managed account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Update fields if provided
    if request.name is not None:
        # Check for duplicate name
        existing = db.query(Account).filter(
            Account.name == request.name,
            Account.id != account_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Account name already exists")
        account.name = request.name
    
    if request.secure_c_ses is not None:
        account.secure_c_ses = request.secure_c_ses
        account.cookie_status = "valid"  # Reset status when updating credentials
    
    if request.csesidx is not None:
        account.csesidx = request.csesidx
    
    if request.config_id is not None:
        account.config_id = request.config_id
    
    if request.host_c_oses is not None:
        account.host_c_oses = request.host_c_oses
    
    if request.is_active is not None:
        account.is_active = request.is_active
    
    if request.is_default is not None:
        if request.is_default:
            # Unset other defaults
            db.query(Account).filter(Account.is_default == True).update({"is_default": False})
        account.is_default = request.is_default
    
    if request.notes is not None:
        account.notes = request.notes
    
    account.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Database account updated: {account.name} by {admin.username}")
    
    return {
        "success": True,
        "message": "Account updated successfully. Reload accounts to apply changes.",
    }


@router.delete("/db-accounts/{account_id}")
async def delete_db_account(
    account_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a database-managed account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    
    name = account.name
    db.delete(account)
    db.commit()
    
    logger.info(f"Database account deleted: {name} by {admin.username}")
    
    return {
        "success": True,
        "message": f"Account '{name}' deleted. Reload accounts to apply changes.",
    }


@router.post("/db-accounts/{account_id}/test")
async def test_db_account(
    account_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Test a database account's credentials"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Create a temporary GeminiAccount to test
    from ..core.account_pool import GeminiAccount
    from ..core.http_client import get_http_client
    
    test_account = GeminiAccount(
        name=account.name,
        secure_1psid=account.secure_c_ses,
        secure_1psidts=account.csesidx,
        config_id=account.config_id,
        host_oses=account.host_c_oses,
        client=get_http_client(),
    )
    
    # Try to test the account
    try:
        # Simple validation - check if cookies are set
        if not test_account.secure_1psid or not test_account.secure_1psidts:
            return {
                "success": False,
                "message": "Missing required credentials",
                "cookie_status": "invalid",
            }
        
        # Update account status
        account.cookie_status = "valid"
        account.last_error = None
        db.commit()
        
        return {
            "success": True,
            "message": "Account credentials appear valid",
            "cookie_status": "valid",
        }
    except Exception as e:
        account.cookie_status = "invalid"
        account.last_error = str(e)
        db.commit()
        
        return {
            "success": False,
            "message": f"Test failed: {str(e)}",
            "cookie_status": "invalid",
        }


@router.post("/accounts/reload")
async def reload_accounts(admin: Admin = Depends(get_current_admin)):
    """Reload accounts from database"""
    # Reset and reload the account pool
    reset_account_pool()
    pool = get_account_pool()
    
    logger.info(f"Accounts reloaded by {admin.username}")
    
    return {
        "success": True,
        "total_accounts": len(pool.accounts),
        "source": "database" if pool.accounts else "environment",
        "message": f"Loaded {len(pool.accounts)} accounts",
    }


# ============== Settings Management ==============

@router.get("/settings")
async def list_settings(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all configurable settings"""
    settings = db.query(Settings).order_by(Settings.key).all()
    return [
        {
            "id": s.id,
            "key": s.key,
            "value": s.value,
            "value_type": s.value_type,
            "description": s.description,
            "updated_at": s.updated_at,
        }
        for s in settings
    ]


@router.get("/settings/{key}")
async def get_setting(
    key: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific setting"""
    setting = db.query(Settings).filter(Settings.key == key).first()
    if setting is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    return {
        "key": setting.key,
        "value": setting.get_value(),
        "value_type": setting.value_type,
        "description": setting.description,
    }


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    request: UpdateSettingRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update or create a setting"""
    setting = db.query(Settings).filter(Settings.key == key).first()
    
    if setting is None:
        # Create new setting
        setting = Settings(
            key=key,
            value=request.value,
            value_type=request.value_type,
        )
        db.add(setting)
    else:
        # Update existing
        setting.value = request.value
        setting.value_type = request.value_type
        setting.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Setting updated: {key} by {admin.username}")
    
    return {
        "success": True,
        "key": key,
        "value": setting.get_value(),
    }


@router.delete("/settings/{key}")
async def delete_setting(
    key: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a setting"""
    setting = db.query(Settings).filter(Settings.key == key).first()
    if setting is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    db.delete(setting)
    db.commit()
    
    logger.info(f"Setting deleted: {key} by {admin.username}")
    
    return {"success": True, "message": f"Setting '{key}' deleted"}


# ============== Migration Helper ==============

@router.post("/migrate-env-accounts")
async def migrate_env_accounts(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Migrate accounts from environment variables to database"""
    migrated = []
    errors = []
    
    # Scan for ACCOUNT{n}_ prefixed environment variables
    i = 1
    while True:
        prefix = f"ACCOUNT{i}_"
        name = os.environ.get(f"{prefix}NAME")
        
        if not name:
            break
        
        # Check if account already exists in DB
        existing = db.query(Account).filter(Account.name == name).first()
        if existing:
            errors.append(f"Account '{name}' already exists in database")
            i += 1
            continue
        
        # Get credentials from env
        secure_c_ses = os.environ.get(f"{prefix}SECURE_1PSID", "")
        csesidx = os.environ.get(f"{prefix}SECURE_1PSIDTS", "")
        config_id = os.environ.get(f"{prefix}CONFIG_ID", "")
        host_c_oses = os.environ.get(f"{prefix}HOST_OSES", "")
        
        if not secure_c_ses or not csesidx:
            errors.append(f"Account '{name}' missing required credentials")
            i += 1
            continue
        
        # Create account in database
        account = Account(
            name=name,
            secure_c_ses=secure_c_ses,
            csesidx=csesidx,
            config_id=config_id,
            host_c_oses=host_c_oses,
            is_default=(i == 1),  # First account is default
            notes=f"Migrated from environment at {datetime.utcnow().isoformat()}",
        )
        
        db.add(account)
        migrated.append(name)
        i += 1
    
    db.commit()
    
    logger.info(f"Migrated {len(migrated)} accounts from env by {admin.username}")
    
    return {
        "success": True,
        "migrated": migrated,
        "migrated_count": len(migrated),
        "errors": errors,
        "message": f"Migrated {len(migrated)} accounts. Errors: {len(errors)}",
    }
