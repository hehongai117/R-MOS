"""
数据库连接管理（基础设施）
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # 开发模式下打印SQL
    future=True,
    pool_pre_ping=True,  # 连接前检测可用性
    poolclass=NullPool if settings.DEBUG else None  # 开发模式禁用连接池
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依赖注入：获取数据库会话
    
    用法：
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Model))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"数据库会话异常: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建所有表）
    
    ⚠️ 仅用于开发/测试，生产环境使用Alembic迁移
    """
    from app.models.base import Base
    # 导入所有模型（确保被注册到metadata）
    from app.models import sop, task, event, snapshot, fault
    
    async with engine.begin() as conn:
        logger.info("正在创建数据库表...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表创建完成")


async def close_db():
    """关闭数据库连接池"""
    await engine.dispose()
    logger.info("数据库连接池已关闭")
