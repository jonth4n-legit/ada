"""
Gemini Ultra Gateway - Database Models
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Admin(Base):
    """Admin user model"""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Admin(username={self.username})>"


class APIKey(Base):
    """API Key model"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    key_prefix = Column(String(10), nullable=False)  # First few chars for identification
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    
    # Rate limiting
    rate_limit_rpm = Column(Integer, default=60)  # Requests per minute
    rate_limit_rpd = Column(Integer, default=1000)  # Requests per day
    
    # Usage tracking
    total_requests = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    logs = relationship("APICallLog", back_populates="api_key")
    
    def __repr__(self):
        return f"<APIKey(name={self.name}, prefix={self.key_prefix})>"
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class APICallLog(Base):
    """API call log model"""
    __tablename__ = "api_call_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True, index=True)
    
    # Request details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    model = Column(String(50), nullable=True)
    
    # Response details
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    
    # Token usage
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Metadata
    account_used = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Client info
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    # Relationships
    api_key = relationship("APIKey", back_populates="logs")
    
    def __repr__(self):
        return f"<APICallLog(endpoint={self.endpoint}, status={self.status_code})>"


class AccountCookieStatus(Base):
    """Account cookie status tracking"""
    __tablename__ = "account_cookie_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_name = Column(String(100), unique=True, nullable=False, index=True)
    cookie_status = Column(String(20), default="unknown")  # valid, expired, unknown
    last_check_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AccountCookieStatus(account={self.account_name}, status={self.cookie_status})>"


class Account(Base):
    """Account model - Stores Gemini Business account credentials"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    
    # Credentials (encrypted in real deployment)
    secure_c_ses = Column(Text, nullable=False)
    csesidx = Column(String(255), nullable=False)
    config_id = Column(String(255), nullable=False)
    host_c_oses = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Cookie status
    cookie_status = Column(String(20), default="unknown")  # valid, expired, unknown, rate_limited
    cookie_expires_at = Column(DateTime, nullable=True)
    last_check_at = Column(DateTime, nullable=True)
    
    # Runtime stats (not persisted in pool, just for display)
    fail_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0)
    
    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    
    def __repr__(self):
        return f"<Account(name={self.name}, status={self.cookie_status})>"
    
    def to_dict(self, include_sensitive: bool = False):
        """Convert to dictionary"""
        result = {
            "id": self.id,
            "name": self.name,
            "csesidx": self.csesidx,
            "config_id": self.config_id,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "cookie_status": self.cookie_status,
            "cookie_expires_at": self.cookie_expires_at.isoformat() if self.cookie_expires_at else None,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "fail_count": self.fail_count,
            "last_error": self.last_error,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "total_requests": self.total_requests,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_sensitive:
            result["secure_c_ses"] = self.secure_c_ses
            result["host_c_oses"] = self.host_c_oses
        else:
            result["secure_c_ses"] = self.secure_c_ses[:20] + "..." if self.secure_c_ses else None
            result["host_c_oses"] = self.host_c_oses[:20] + "..." if self.host_c_oses else None
        return result


class Settings(Base):
    """System settings model - Stores configurable settings"""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, int, bool, json
    description = Column(Text, nullable=True)
    category = Column(String(50), default="general")  # general, proxy, limits, etc.
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Settings(key={self.key}, value={self.value[:50] if self.value else None})>"
    
    def get_typed_value(self):
        """Get value with proper type conversion"""
        if self.value is None:
            return None
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        return self.value


class KeepAliveTask(Base):
    """Keep-alive task model"""
    __tablename__ = "keep_alive_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), default="default")
    is_enabled = Column(Boolean, default=False)
    schedule_time = Column(String(10), default="03:00")  # HH:MM format, Beijing time
    
    # Status
    last_run_at = Column(DateTime, nullable=True)
    last_status = Column(String(20), nullable=True)  # success, error, running
    last_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<KeepAliveTask(name={self.name}, enabled={self.is_enabled})>"


class KeepAliveLog(Base):
    """Keep-alive execution log"""
    __tablename__ = "keep_alive_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("keep_alive_tasks.id"), nullable=True)
    
    status = Column(String(20), nullable=False)  # success, error, running, cancelled
    message = Column(Text, nullable=True)
    
    # Statistics
    accounts_total = Column(Integer, default=0)
    accounts_success = Column(Integer, default=0)
    accounts_failed = Column(Integer, default=0)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<KeepAliveLog(status={self.status}, success={self.accounts_success}/{self.accounts_total})>"


class KeepAliveAccountLog(Base):
    """Keep-alive per-account log"""
    __tablename__ = "keep_alive_account_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(Integer, ForeignKey("keep_alive_logs.id"), nullable=False, index=True)
    account_name = Column(String(100), nullable=False)
    
    status = Column(String(20), nullable=False)  # success, error, running, cancelled
    message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<KeepAliveAccountLog(account={self.account_name}, status={self.status})>"


class GeneratedMedia(Base):
    """Generated media (images/videos) tracking"""
    __tablename__ = "generated_media"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    media_type = Column(String(10), nullable=False)  # image, video
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=True)
    
    # Generation details
    prompt = Column(Text, nullable=True)
    model = Column(String(50), nullable=True)
    generation_params = Column(Text, nullable=True)  # JSON string
    
    # Metadata
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<GeneratedMedia(type={self.media_type}, file={self.file_name})>"
