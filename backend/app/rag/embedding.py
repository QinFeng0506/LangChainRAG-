"""百炼 Embedding API 封装 —— 批量文本向量化。"""
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

_embedding_client = AsyncOpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url=settings.DASHSCOPE_BASE_URL,
)


async def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    """批量将文本转换为向量。"""
    model_name = model or settings.EMBEDDING_MODEL
    response = await _embedding_client.embeddings.create(
        model=model_name,
        input=texts,
    )
    # 按输入顺序返回向量
    embeddings = sorted(response.data, key=lambda x: x.index)
    return [e.embedding for e in embeddings]


async def embed_single(text: str) -> list[float]:
    """单条文本向量化。"""
    results = await embed_texts([text])
    return results[0]
