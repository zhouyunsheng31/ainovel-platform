"""
AI小说拆书系统 - 数据库连接模块
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager
import os

from app.config import settings

# 确保数据目录存在
os.makedirs(os.path.dirname(settings.database_url.replace("sqlite+aiosqlite:///", "")), exist_ok=True)

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True
)

# 创建会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 用于后台任务的会话工厂别名
async_session_factory = async_session_maker

# 声明基类
Base = declarative_base()


async def init_db():
    """初始化数据库（创建所有表，并处理必要的表结构迁移）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from sqlalchemy import text, inspect as sa_inspect
        def _migrate(sync_conn):
            inspector = sa_inspect(sync_conn)
            if 'books' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('books')]
                if 'file_hash' not in columns:
                    sync_conn.execute(text('ALTER TABLE books ADD COLUMN file_hash VARCHAR(64)'))
        await conn.run_sync(_migrate)


@asynccontextmanager
async def get_session() -> AsyncSession:
    """获取数据库会话上下文管理器"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
