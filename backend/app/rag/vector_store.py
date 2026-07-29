"""ChromaDB 向量存储封装 —— 持久化模式。"""
import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import get_settings

settings = get_settings()

# ChromaDB 持久化客户端
_chroma_client = chromadb.PersistentClient(
    path=settings.CHROMA_PERSIST_DIR,
    settings=ChromaSettings(anonymized_telemetry=False),
)


def get_collection(name: str | None = None):
    """获取或创建 ChromaDB Collection。"""
    collection_name = name or settings.CHROMA_COLLECTION_NAME
    return _chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},  # 余弦相似度
    )


def add_chunks(
    collection_name: str,
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> list[str]:
    """向向量库批量添加文本块。返回分配的 ID 列表。"""
    collection = get_collection(collection_name)
    ids = [str(uuid.uuid4()) for _ in texts]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return ids


def search_similar(
    collection_name: str,
    query_embedding: list[float],
    top_k: int | None = None,
    filter_metadata: dict | None = None,
) -> dict:
    """语义检索 —— 返回最相似的 Top-K 结果。"""
    collection = get_collection(collection_name)
    k = top_k or settings.RETRIEVAL_TOP_K

    where = None
    if filter_metadata:
        where = filter_metadata

    return collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )


def get_collection_stats(collection_name: str | None = None) -> dict:
    """获取 Collection 统计信息。"""
    collection = get_collection(collection_name)
    count = collection.count()
    return {
        "name": collection.name,
        "total_chunks": count,
    }


def delete_by_doc_id(collection_name: str, doc_id: str) -> int:
    """按文档 ID 删除向量。返回删除数量。"""
    collection = get_collection(collection_name)
    # ChromaDB 不支持直接按 metadata 删除，需要先查询再逐个删除
    results = collection.get(
        where={"doc_id": doc_id},
        include=[],
    )
    if results["ids"]:
        collection.delete(ids=results["ids"])
    return len(results["ids"])


def delete_collection(name: str):
    """删除整个 Collection。"""
    try:
        _chroma_client.delete_collection(name)
    except Exception:
        pass


def clear_collection(name: str | None = None) -> int:
    """清空 Collection 中所有向量数据（保留 Collection 本身）。返回删除数量。"""
    collection = get_collection(name)
    results = collection.get(include=[])
    count = len(results["ids"])
    if count > 0:
        collection.delete(ids=results["ids"])
    return count
