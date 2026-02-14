"""
数据库配置和初始化
支持SQLite和PostgreSQL
"""
import os
from typing import Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./meetings.db"  # 默认使用SQLite
)

# 如果使用SQLite，需要特殊配置
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL或其他数据库
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

# 会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session
)

def get_db():
    """
    依赖注入：获取数据库会话
    用于FastAPI路由中
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库
    创建所有表
    """
    SQLModel.metadata.create_all(engine)
    print("✓ 数据库初始化成功")


def get_engine() -> Engine:
    """获取数据库引擎"""
    return engine


def get_session() -> Session:
    """手动创建会话"""
    return SessionLocal()
