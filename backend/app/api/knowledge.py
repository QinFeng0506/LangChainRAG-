"""知识库管理 API 路由 —— 仅管理员可访问。"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_admin
from app.models.user import User
from app.models.document import Document
from app.schemas.knowledge import DocumentResponse, DocumentListResponse, DocumentStatusResponse, KnowledgeStatsResponse
from app.services.knowledge_service import (
    get_documents, get_document, process_document, delete_document, get_stats,
)
from app.utils.file_storage import save_upload, validate_file_type

router = APIRouter(prefix="/api/knowledge", tags=["知识库管理"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传文档（管理员专属）—— 后台异步处理。"""
    # 校验文件类型
    if not validate_file_type(file.filename or ""):
        raise HTTPException(400, f"不支持的文件类型。支持: PDF, TXT, CSV, MD, DOCX, XLSX, PNG, JPG, WEBP")

    # 保存文件（含大小校验）
    try:
        file_info = await save_upload(file)
    except ValueError as e:
        raise HTTPException(413, str(e))

    # 创建数据库记录
    doc = Document(
        filename=file_info["filename"],
        file_type=file_info["file_type"],
        file_size=file_info["file_size"],
        file_path=file_info["file_path"],
        status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 后台异步处理文档
    background_tasks.add_task(process_document, None, doc.id)

    return doc


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """文档列表（管理员专属）—— 分页 + 状态筛选。"""
    docs, total = await get_documents(db, page, page_size, status)
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    doc_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询文档处理状态。"""
    doc = await get_document(db, doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    return DocumentStatusResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
    )


@router.delete("/documents/{doc_id}")
async def remove_document(
    doc_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除文档及关联向量。"""
    success = await delete_document(db, doc_id)
    if not success:
        raise HTTPException(404, "文档不存在")
    return {"message": "文档已删除"}


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_knowledge_stats(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """知识库统计信息。"""
    return await get_stats(db)
