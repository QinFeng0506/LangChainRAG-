"""阿里云百炼 DashScope LLM 客户端 —— 兼容 OpenAI 协议。"""
import httpx
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

# 百炼 DashScope 兼容 OpenAI 协议，配置连接池和超时
llm_client = AsyncOpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url=settings.DASHSCOPE_BASE_URL,
    http_client=httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
        timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
    ),
)


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
    stream: bool = True,
    temperature: float = 0.7,
    max_tokens: int = 2048,
):
    """调用百炼 LLM 聊天接口，返回流式响应。"""
    return await llm_client.chat.completions.create(
        model=model or settings.LLM_MODEL,
        messages=messages,
        stream=stream,
        temperature=temperature,
        max_tokens=max_tokens,
    )


async def chat_completion_sync(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    max_retries: int = 2,
) -> str:
    """调用百炼 LLM 聊天接口，返回完整文本（非流式）。支持指数退避重试。"""
    import asyncio

    # Mock 模式：跳过真实 API 调用
    if settings.STRESS_TEST_MOCK:
        await asyncio.sleep(0.05)  # 模拟网络延迟
        user_content = messages[-1]["content"] if messages else ""
        return (
            f"根据知识库内容，关于「{user_content[:30]}」的详细信息如下：\n\n"
            "该商品具备以下核心特性：高性能处理器、大容量电池、高清显示屏。"
            "售后服务涵盖7天无理由退换、1年质保。如需了解更多信息，欢迎继续咨询。[1][2]"
        )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = await llm_client.chat.completions.create(
                model=model or settings.LLM_MODEL,
                messages=messages,
                stream=False,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # 指数退避: 1s, 2s
    raise last_error  # type: ignore
