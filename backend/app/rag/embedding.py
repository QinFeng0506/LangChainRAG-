"""百炼 Embedding API 封装 —— 批量文本向量化。"""
import httpx
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

_embedding_client = AsyncOpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url=settings.DASHSCOPE_BASE_URL,
    http_client=httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
        timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
    ),
)


async def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    """批量将文本转换为向量。"""
    import asyncio

    # Mock 模式：返回固定维度随机向量
    if settings.STRESS_TEST_MOCK:
        await asyncio.sleep(0.02)  # 模拟网络延迟
        import random
        random.seed(hash(texts[0]) if texts else 0)
        return [[random.uniform(-1, 1) for _ in range(1024)] for _ in texts]

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
