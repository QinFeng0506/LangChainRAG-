"""用户相关 API 路由。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, UserResponse
from app.services.auth_service import verify_password, hash_password

router = APIRouter(prefix="/api/user", tags=["用户"])


@router.put("/password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码 —— 需提供旧密码。"""
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")

    current_user.password_hash = hash_password(req.new_password)
    await db.commit()

    return {"message": "密码修改成功"}


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取个人信息。"""
    return current_user
