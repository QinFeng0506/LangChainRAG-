"""知识库管理相关 Pydantic 模型。"""
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentStatusResponse(BaseModel):
    id: str
    filename: str
    status: str
    chunk_count: int
    error_message: str | None = None


class KnowledgeStatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_size_bytes: int
    documents_by_type: dict[str, int]
    documents_by_status: dict[str, int]
