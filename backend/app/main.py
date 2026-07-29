"""FastAPI 应用入口 —— 生命周期管理 + 路由注册。"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import get_settings
from app.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和管理员账号，关闭时清理资源。"""
    # === 启动 ===
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CACHE_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

    await init_db()

    # 创建预设管理员账号
    from app.database import async_session
    from app.models.user import User
    from app.services.auth_service import hash_password

    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
        admin = result.scalar_one_or_none()
        if admin is None:
            admin = User(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            await db.commit()
            print(f"[启动] 管理员账号已创建: {settings.ADMIN_USERNAME} (密码已隐藏)")
        else:
            print(f"[启动] 管理员账号已存在: {settings.ADMIN_USERNAME}")

    print(f"[启动] {settings.APP_NAME} v{settings.APP_VERSION} 已启动")
    print(f"[启动] API 文档: http://{settings.HOST}:{settings.PORT}/docs")

    yield

    # === 关闭 ===
    print("[关闭] 应用已停止")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS 中间件 —— 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载上传文件目录为静态文件服务
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ===== 注册路由 =====
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.knowledge import router as knowledge_router
from app.api.chat import router as chat_router

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(knowledge_router)
app.include_router(chat_router)


# ===== 健康检查 =====
@app.get("/api/health", tags=["系统"])
async def health_check():
    """健康检查接口，用于前后端联调验证。"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
