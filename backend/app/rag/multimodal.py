"""多模态图片处理 —— 百炼 Qwen-VL 图片描述生成。"""
import os
import httpx
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

_vl_client = AsyncOpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url=settings.DASHSCOPE_BASE_URL,
    http_client=httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        timeout=httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=10.0),
    ),
)


async def describe_image(image_path: str) -> str:
    """调用百炼 Qwen-VL 模型生成商品图片的文字描述。

    将图片转为 base64，通过 OpenAI 兼容接口发送给 Qwen-VL。
    """
    import base64

    # 读取图片并转 base64
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
    mime_type = mime_map.get(ext, "image/jpeg")

    prompt = """请详细描述这张商品图片的内容，包括但不限于：
1. 商品的类别和名称
2. 商品的颜色、材质、外观特征
3. 包装、规格等可见信息
4. 图中任何文字标签、价格、品牌标志
5. 图片的整体风格和用途（如商品主图、详情图、包装图等）

请直接描述，不要加"这张图片显示"等引导语。描述语言为中文。"""

    try:
        response = await _vl_client.chat.completions.create(
            model=settings.VL_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}},
                ],
            }],
            max_tokens=1000,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        # 如果 VL 模型不可用，回退到基于文件名的简单描述
        filename = os.path.basename(image_path)
        return f"[图片] {filename} —— 商品图片（多模态描述生成失败: {str(e)[:100]}）"


async def process_image_document(doc_id: str, image_path: str, filename: str) -> tuple[str, str]:
    """处理图片文档：生成描述 + 保存图片路径元信息。

    Returns:
        (description_text, relative_image_url)
    """
    # 1. VL 模型生成描述
    description = await describe_image(image_path)

    # 2. 拼接完整描述文本
    full_text = f"[商品图片] {filename}\n图片内容描述：{description}"

    # 3. 构建图片访问 URL（通过 FastAPI 静态文件服务）
    # image_path 格式: ./data/uploads/{doc_id}/{safe_filename}
    # URL 格式: /uploads/{doc_id}/{safe_filename}
    parts = image_path.replace("\\", "/").split("/")
    try:
        idx = parts.index("uploads")
        relative_url = "/" + "/".join(parts[idx:])
    except ValueError:
        relative_url = f"/uploads/{doc_id}/{os.path.basename(image_path)}"

    return full_text, relative_url
