"""SQLite 异步引擎 + 自动建表。"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# 异步引擎，SQLite WAL 模式开启
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# 异步会话工厂
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """初始化数据库：建表 + 开启 WAL 模式（提升并发性能）。"""
    from sqlalchemy import text

    async with engine.begin() as conn:
        # 开启 WAL 模式
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        # 建表
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话。"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
