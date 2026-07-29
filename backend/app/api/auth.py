"""认证相关 API 路由。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshRequest, ChangePasswordRequest, UserResponse,
)
from app.services.auth_service import (
    get_user_by_username, get_user_by_id, create_user, verify_password,
    create_access_token, create_refresh_token, decode_token,
    hash_password,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册。"""
    existing = await get_user_by_username(db, req.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    user = await create_user(db, req.username, req.password)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.username, user.role),
        refresh_token=create_refresh_token(user.id),
        username=user.username,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录。"""
    user = await get_user_by_username(db, req.username)
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    return TokenResponse(
        access_token=create_access_token(user.id, user.username, user.role),
        refresh_token=create_refresh_token(user.id),
        username=user.username,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """刷新 access token。"""
    payload = decode_token(req.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token 无效或已过期")

    user_id = payload.get("sub")
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")

    return TokenResponse(
        access_token=create_access_token(user.id, user.username, user.role),
        refresh_token=create_refresh_token(user.id),
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return current_user
