"""聊天/会话相关 Pydantic 模型。"""
from datetime import datetime
from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    title: str | None = Field(None, max_length=200, description="会话标题，不传则自动生成")


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="新标题")


class SourceInfo(BaseModel):
    """知识库引用来源。"""
    doc_name: str
    chunk_text: str
    score: float
    image_path: str | None = None  # 图片类来源时有值


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: list[SourceInfo] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatQueryRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题")


class FeedbackRequest(BaseModel):
    message_id: str = Field(..., description="消息 ID")
    rating: str = Field(..., description="评分: 'like' 或 'dislike'")
    comment: str | None = Field(None, description="可选反馈文字")
