"""知识库管理服务 —— 文档上传、异步处理、检索。"""
import os
import json
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.embedding import embed_texts
from app.rag.vector_store import add_chunks, delete_by_doc_id, get_collection_stats
from app.utils.file_storage import delete_document_files


async def get_documents(
    db: AsyncSession, page: int = 1, page_size: int = 20, status: str | None = None
) -> tuple[list[Document], int]:
    """分页获取文档列表。"""
    query = select(Document)
    count_query = select(func.count(Document.id))

    if status:
        query = query.where(Document.status == status)
        count_query = count_query.where(Document.status == status)

    query = query.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    documents = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return list(documents), total


async def get_document(db: AsyncSession, doc_id: str) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def update_document_status(db: AsyncSession, doc_id: str, status: str, **kwargs):
    """更新文档处理状态。"""
    doc = await get_document(db, doc_id)
    if doc:
        doc.status = status
        for key, value in kwargs.items():
            setattr(doc, key, value)
        await db.commit()


async def process_document(db: AsyncSession, doc_id: str):
    """后台异步处理：解析 → 分块 → 向量化 → 入库。支持文本和图片。"""
    from app.database import async_session
    from app.config import get_settings
    _settings = get_settings()

    async with async_session() as _db:
        doc = await get_document(_db, doc_id)
        if not doc:
            return

        try:
            # === 图片处理分支 ===
            if doc.file_type == "image":
                from app.rag.multimodal import process_image_document

                await _update_status(_db, doc, "parsing")

                # VL 模型生成描述
                description, image_url = await process_image_document(
                    doc.id, doc.file_path, doc.filename
                )

                if not description:
                    raise ValueError("图片描述生成失败")

                # 将描述文本作为单个 chunk
                await _update_status(_db, doc, "embedding")
                embedding = await embed_texts([description])

                add_chunks(
                    collection_name=_settings.CHROMA_COLLECTION_NAME,
                    texts=[description],
                    embeddings=embedding,
                    metadatas=[{
                        "doc_id": doc.id,
                        "doc_name": doc.filename,
                        "doc_type": "image",
                        "image_path": image_url,
                    }],
                )

                await _update_status(_db, doc, "completed", chunk_count=1)
                return

            # === 文本处理分支 ===
            # 1. 解析
            await _update_status(_db, doc, "parsing")
            documents = load_document(doc.file_path, doc.file_type)

            if not documents:
                raise ValueError("文档内容为空，无法解析")

            # 2. 分块
            await _update_status(_db, doc, "chunking")
            chunks = split_documents(documents)
            if not chunks:
                raise ValueError("文档分块后无内容")

            # 3. 向量化
            await _update_status(_db, doc, "embedding")
            texts = [chunk.page_content for chunk in chunks]

            # 分批向量化（百炼 API 有批量限制，每次最多 25 条）
            batch_size = 20
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                embeddings = await embed_texts(batch)
                all_embeddings.extend(embeddings)

            # 4. 入库
            metadatas = []
            for chunk in chunks:
                meta = chunk.metadata or {}
                meta["doc_id"] = doc.id
                meta["doc_name"] = doc.filename
                meta["doc_type"] = doc.file_type
                metadatas.append(meta)

            add_chunks(
                collection_name=_settings.CHROMA_COLLECTION_NAME,
                texts=texts,
                embeddings=all_embeddings,
                metadatas=metadatas,
            )

            # 5. 完成
            await _update_status(_db, doc, "completed", chunk_count=len(chunks))

        except Exception as e:
            await _update_status(_db, doc, "failed", error_message=str(e))
            raise


async def _update_status(db: AsyncSession, doc: Document, status: str, **kwargs):
    """内部辅助：更新文档状态。"""
    doc.status = status
    for key, value in kwargs.items():
        setattr(doc, key, value)
    await db.commit()


async def delete_document(db: AsyncSession, doc_id: str) -> bool:
    """删除文档：删文件 + 删向量 + 删数据库记录。"""
    from app.config import get_settings
    _settings = get_settings()

    doc = await get_document(db, doc_id)
    if not doc:
        return False

    # 删向量
    delete_by_doc_id(_settings.CHROMA_COLLECTION_NAME, doc_id)

    # 删文件
    doc_dir = os.path.dirname(doc.file_path)
    delete_document_files(doc_dir)

    # 删记录
    await db.delete(doc)
    await db.commit()
    return True


async def get_stats(db: AsyncSession) -> dict:
    """获取知识库统计信息。"""
    # 文档统计
    total_result = await db.execute(select(func.count(Document.id)))
    total_docs = total_result.scalar() or 0

    total_size_result = await db.execute(select(func.coalesce(func.sum(Document.file_size), 0)))
    total_size = total_size_result.scalar() or 0

    # 按类型统计
    type_result = await db.execute(
        select(Document.file_type, func.count(Document.id)).group_by(Document.file_type)
    )
    docs_by_type = {row[0]: row[1] for row in type_result.all()}

    # 按状态统计
    status_result = await db.execute(
        select(Document.status, func.count(Document.id)).group_by(Document.status)
    )
    docs_by_status = {row[0]: row[1] for row in status_result.all()}

    # 向量库统计
    vector_stats = get_collection_stats()

    return {
        "total_documents": total_docs,
        "total_chunks": vector_stats["total_chunks"],
        "total_size_bytes": total_size,
        "documents_by_type": docs_by_type,
        "documents_by_status": docs_by_status,
    }
