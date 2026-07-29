"""pytest 全局 Fixtures —— 测试数据库 + 异步 HTTP 客户端 + 管理/普通用户 Token。"""
import pytest
import os
import sys
import asyncio

# 确保 app 模块可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from app.database import Base, get_db
from app.main import app
from app.config import get_settings
from app.services.auth_service import hash_password

# === 测试用内存数据库 ===
TEST_DB_URL = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"

_engine = None
_session_factory = None


async def _init_test_db():
    """初始化测试数据库表。"""
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(TEST_DB_URL, echo=False)
        _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _get_test_db():
    """测试用 FastAPI 依赖注入 —— 每次请求独立会话。"""
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# === 替换 FastAPI 数据库依赖为测试数据库 ===
app.dependency_overrides[get_db] = _get_test_db


@pytest.fixture(scope="session")
def event_loop():
    """整个测试会话共享一个 event loop。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    """每个测试前重建数据库表 + 清理向量库（保证数据隔离）。"""
    await _init_test_db()
    # 清空 SQLite 关系型数据
    async with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"DELETE FROM {table.name}"))
    # 清空 ChromaDB 向量数据（避免前一个测试的向量残留）
    try:
        from app.rag.vector_store import clear_collection
        from app.config import get_settings
        settings = get_settings()
        clear_collection(settings.CHROMA_COLLECTION_NAME)
    except Exception:
        pass  # ChromaDB 为空或不存在的测试环境，不影响
    yield


# === HTTP 客户端 Fixtures ===

@pytest.fixture
async def client():
    """普通匿名 HTTP 客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_token(client):
    """创建管理员并返回 Token。"""
    from app.models.user import User
    settings = get_settings()

    async with _session_factory() as db:
        admin = User(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role="admin",
        )
        db.add(admin)
        await db.commit()

    resp = await client.post("/api/auth/login", json={
        "username": settings.ADMIN_USERNAME,
        "password": settings.ADMIN_PASSWORD,
    })
    data = resp.json()
    return data["access_token"]


@pytest.fixture
async def user_token(client):
    """创建普通用户并返回 Token。"""
    await client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "test123",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "test123",
    })
    data = resp.json()
    return data["access_token"]


@pytest.fixture
def auth_headers(admin_token):
    """管理员认证请求头。"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token):
    """普通用户认证请求头。"""
    return {"Authorization": f"Bearer {user_token}"}
