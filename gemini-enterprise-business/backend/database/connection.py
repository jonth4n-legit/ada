"""
Gemini Ultra Gateway - Database Connection
"""

import os
import logging
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

logger = logging.getLogger("gemini.database")

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """Get database URL from environment or default"""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    
    # Default to SQLite
    from ..core.config import Config
    db_path = Config.PROJECT_ROOT if hasattr(Config, 'PROJECT_ROOT') else "."
    return f"sqlite:///{db_path}/geminibusiness.db"


def get_engine():
    """Get or create database engine"""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        
        # SQLite specific settings
        if database_url.startswith("sqlite"):
            _engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                echo=False,
            )
        else:
            _engine = create_engine(database_url, echo=False)
        
        logger.info(f"Database engine created: {database_url.split('://')[0]}")
    
    return _engine


def get_session_factory():
    """Get or create session factory"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _SessionLocal


def init_db() -> None:
    """Initialize database, create tables"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized, tables created")
    
    # Create default admin if not exists
    _create_default_admin()


def _create_default_admin() -> None:
    """Create default admin user if not exists"""
    from passlib.hash import bcrypt
    from .models import Admin
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # Check if admin exists
        admin = db.query(Admin).filter(Admin.username == "admin").first()
        if admin is None:
            # Create default admin
            admin = Admin(
                username="admin",
                password_hash=bcrypt.hash("admin123456"),
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Default admin user created (username: admin, password: admin123456)")
    except Exception as e:
        logger.error(f"Failed to create default admin: {e}")
        db.rollback()
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """Get database session (dependency for FastAPI)"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Get database session as context manager"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
