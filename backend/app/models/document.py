"""知识库文档 ORM 模型。"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "pdf", "txt", "image", "docx", etc.
    file_size: Mapped[int] = mapped_column(Integer, default=0)          # 字节
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # 本地存储路径
    status: Mapped[str] = mapped_column(String(20), default="pending")   # pending/parsing/chunking/embedding/completed/failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
