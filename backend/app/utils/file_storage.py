"""本地文件存储工具。"""
import os
import uuid
import aiofiles
from fastapi import UploadFile
from app.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {
    # 文档
    "pdf", "txt", "csv", "md", "markdown", "docx", "xlsx",
    # 图片
    "png", "jpg", "jpeg", "webp", "gif",
}

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def get_file_type(extension: str) -> str:
    """根据扩展名判断文件类型。"""
    ext = extension.lower().lstrip(".")
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext == "md":
        return "md"
    return ext


async def save_upload(upload_file: UploadFile) -> dict:
    """保存上传文件到本地，返回文件元信息。"""
    # 创建文档专属目录
    doc_id = str(uuid.uuid4())
    doc_dir = os.path.join(settings.UPLOAD_DIR, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    # 安全文件名
    original_name = upload_file.filename or "untitled"
    safe_name = f"{doc_id}_{original_name}"
    file_path = os.path.join(doc_dir, safe_name)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # 先读取全部内容到内存，校验大小后再写入
    content = await upload_file.read()
    if len(content) > max_bytes:
        raise ValueError(f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE_MB}MB，当前 {len(content) / 1024 / 1024:.1f}MB）")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # 获取文件大小
    file_size = os.path.getsize(file_path)
    ext = original_name.rsplit(".", 1)[-1] if "." in original_name else ""

    return {
        "doc_id": doc_id,
        "filename": original_name,
        "file_type": get_file_type(ext),
        "file_size": file_size,
        "file_path": file_path,
        "doc_dir": doc_dir,
    }


def delete_document_files(doc_dir: str) -> None:
    """删除文档目录及其所有文件。"""
    import shutil
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)


def validate_file_type(filename: str) -> bool:
    """校验文件类型是否允许。"""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def validate_file_size(file_size: int) -> bool:
    """校验文件大小是否在允许范围内。"""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    return 0 < file_size <= max_bytes
