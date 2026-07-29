"""阿里云百炼 DashScope LLM 客户端 —— 兼容 OpenAI 协议。"""
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

# 百炼 DashScope 兼容 OpenAI 协议，直接用 AsyncOpenAI 客户端
llm_client = AsyncOpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url=settings.DASHSCOPE_BASE_URL,
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
) -> str:
    """调用百炼 LLM 聊天接口，返回完整文本（非流式）。"""
    response = await llm_client.chat.completions.create(
        model=model or settings.LLM_MODEL,
        messages=messages,
        stream=False,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
