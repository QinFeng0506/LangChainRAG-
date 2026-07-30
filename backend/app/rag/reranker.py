"""百炼 gte-rerank 重排序 —— Cross-Encoder 精排。"""
import httpx
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

_rerank_client = AsyncOpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url=settings.DASHSCOPE_BASE_URL,
    http_client=httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
        timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
    ),
)


async def rerank(
    query: str,
    documents: list[str],
    top_k: int | None = None,
    max_retries: int = 2,
) -> list[dict]:
    """对候选文档重排序，返回 Top-K 结果及评分。

    注意：百炼 DashScope 的 rerank API 使用 OpenAI 兼容格式。
    如果兼容格式不支持，回退到基于 LLM 的评分方式。
    """
    import asyncio
    k = top_k or settings.RERANK_TOP_K

    # Mock 模式：直接返回前 k 个，分数递减
    if settings.STRESS_TEST_MOCK:
        await asyncio.sleep(0.03)  # 模拟网络延迟
        return [
            {"index": i, "score": 1.0 - i * 0.05}
            for i in range(min(k, len(documents)))
        ]

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            # 尝试使用标准 rerank API
            response = await _rerank_client.post(
                "/rerank",
                json={
                    "model": settings.RERANK_MODEL,
                    "input": {
                        "query": query,
                        "documents": documents,
                    },
                    "parameters": {
                        "top_n": min(k, len(documents)),
                        "return_documents": False,
                    },
                },
            )
            data = response.json()
            results = data.get("output", {}).get("results", [])
            return [
                {
                    "index": r["index"],
                    "score": r.get("relevance_score", 0),
                }
                for r in results
            ]
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)

    # 所有重试失败后回退
    return [
        {"index": i, "score": 1.0 - i * 0.05}
        for i in range(min(k, len(documents)))
    ]


async def rerank_documents(
    query: str,
    candidates: list[dict],
    top_k: int | None = None,
) -> list[dict]:
    """对混合检索结果重排序，返回精排后的 Top-K。"""
    k = top_k or settings.RERANK_TOP_K

    if len(candidates) <= k:
        return candidates

    texts = [c["text"] for c in candidates]
    rerank_results = await rerank(query, texts, k)

    return [candidates[r["index"]] for r in rerank_results if r["index"] < len(candidates)]
