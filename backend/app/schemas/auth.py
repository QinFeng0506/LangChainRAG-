"""认证相关 Pydantic 请求/响应模型。"""
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
