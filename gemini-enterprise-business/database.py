
"""
数据库模型和配置
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 北京时间 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_time():
    """获取当前北京时间（naive，用于数据库存储）"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)

# SQLite 数据库
DATABASE_URL = "sqlite:///./geminibusiness.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Admin(Base):
    """管理员账号表"""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=get_beijing_time)


class APIKey(Base):
    """API 密钥表"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(100), unique=True, nullable=False, index=True)
    encrypted_key = Column(String(200), nullable=False)  # 存储加密后的密钥
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=get_beijing_time)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)


class APICallLog(Base):
    """API 调用日志表"""
    __tablename__ = "api_call_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, nullable=False, index=True)  # 关联的 API Key ID
    timestamp = Column(DateTime, default=get_beijing_time, index=True)  # 调用时间
    model = Column(String(50), nullable=True)  # 使用的模型
    status = Column(String(20), nullable=False)  # success 或 error
    error_message = Column(String(500), nullable=True)  # 错误信息
    ip_address = Column(String(50), nullable=True)  # 客户端 IP
    endpoint = Column(String(100), nullable=True)  # 调用的端点
    response_time = Column(Integer, nullable=True)  # 响应时间（毫秒）


class KeepAliveTask(Base):
    """保活任务表"""
    __tablename__ = "keep_alive_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    is_enabled = Column(Boolean, default=True)  # 是否启用
    schedule_time = Column(String(10), default="00:00")  # 执行时间（HH:MM格式，北京时间）
    # API 保活配置
    api_keepalive_enabled = Column(Boolean, default=True)  # 是否启用 API 保活
    api_keepalive_interval = Column(Integer, default=30)  # API 保活间隔（分钟）
    # 自动检查配置
    auto_check_enabled = Column(Boolean, default=False)  # 是否启用自动检查
    auto_check_interval = Column(Integer, default=60)  # 自动检查间隔（分钟）
    auto_check_auto_fix = Column(Boolean, default=True)  # 检测到无效时自动修复
    last_run_at = Column(DateTime, nullable=True)  # 上次执行时间
    last_status = Column(String(20), nullable=True)  # 上次执行状态：success, error, running
    last_message = Column(String(500), nullable=True)  # 上次执行消息
    last_api_keepalive_at = Column(DateTime, nullable=True)  # 上次 API 保活时间
    last_auto_check_at = Column(DateTime, nullable=True)  # 上次自动检查时间
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)


class KeepAliveLog(Base):
    """保活任务执行日志表"""
    __tablename__ = "keep_alive_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)  # 关联的任务ID
    started_at = Column(DateTime, default=get_beijing_time, index=True)  # 开始时间
    finished_at = Column(DateTime, nullable=True)  # 结束时间
    status = Column(String(20), nullable=False)  # success, error, running, cancelled
    message = Column(String(1000), nullable=True)  # 执行消息
    accounts_count = Column(Integer, nullable=True)  # 处理的账号数量
    success_count = Column(Integer, nullable=True)  # 成功数量
    fail_count = Column(Integer, nullable=True)  # 失败数量


class KeepAliveAccountLog(Base):
    """保活账号级别日志表"""
    __tablename__ = "keep_alive_account_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_log_id = Column(Integer, nullable=False, index=True)  # 关联的任务日志ID
    account_name = Column(String(200), nullable=False)  # 账号名称
    account_email = Column(String(200), nullable=True)  # 账号邮箱
    started_at = Column(DateTime, default=get_beijing_time, index=True)  # 开始时间
    finished_at = Column(DateTime, nullable=True)  # 结束时间
    status = Column(String(20), nullable=False)  # success, error, running, cancelled
    message = Column(String(500), nullable=True)  # 执行消息


class AccountCookieStatus(Base):
    """账号 Cookie 状态表"""
    __tablename__ = "account_cookie_status"
    
    id = Column(Integer, primary_key=True, index=True)
    account_name = Column(String(200), unique=True, nullable=False, index=True)  # 账号名称（唯一）
    cookie_status = Column(String(20), nullable=True)  # valid, expired, forbidden, rate_limited, unknown
    last_check_at = Column(DateTime, nullable=True)  # 最后检查时间
    expires_at = Column(DateTime, nullable=True)  # 预估到期时间
    error_message = Column(String(500), nullable=True)  # 错误信息
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)


def migrate_db():
    """数据库迁移 - 添加新列（如果不存在）"""
    from sqlalchemy import inspect, text
    
    inspector = inspect(engine)
    conn = engine.connect()
    
    try:
        # 检查 keep_alive_tasks 表是否存在
        if 'keep_alive_tasks' in inspector.get_table_names():
            # 获取现有列
            existing_columns = [col['name'] for col in inspector.get_columns('keep_alive_tasks')]
            
            # 需要添加的列
            columns_to_add = {
                'api_keepalive_enabled': 'BOOLEAN DEFAULT 1',
                'api_keepalive_interval': 'INTEGER DEFAULT 30',
                'last_api_keepalive_at': 'DATETIME',
                'auto_check_enabled': 'BOOLEAN DEFAULT 0',
                'auto_check_interval': 'INTEGER DEFAULT 60',
                'auto_check_auto_fix': 'BOOLEAN DEFAULT 1',
                'last_auto_check_at': 'DATETIME'
            }
            
            # 添加缺失的列
            for column_name, column_def in columns_to_add.items():
                if column_name not in existing_columns:
                    try:
                        # SQLite 不支持 IF NOT EXISTS，所以需要先检查
                        conn.execute(text(f'ALTER TABLE keep_alive_tasks ADD COLUMN {column_name} {column_def}'))
                        conn.commit()
                        print(f"✅ 已添加列: keep_alive_tasks.{column_name}")
                    except Exception as e:
                        # 如果列已存在（可能是并发情况），忽略错误
                        if 'duplicate column' not in str(e).lower():
                            print(f"⚠️ 添加列 {column_name} 时出错: {e}")
                        conn.rollback()
    except Exception as e:
        print(f"⚠️ 数据库迁移时出错: {e}")
        conn.rollback()
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
    # 执行迁移
    migrate_db()


def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
