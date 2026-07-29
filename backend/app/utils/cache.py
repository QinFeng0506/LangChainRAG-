"""diskcache 缓存封装 —— 热门问答缓存、相似问题复用。"""
import hashlib
import diskcache
from app.config import get_settings

settings = get_settings()

# 持久化缓存（基于 SQLite）
_cache = diskcache.Cache(settings.CACHE_DIR)


def cache_key(question: str) -> str:
    """对问题做标准化生成缓存 key。"""
    # 去除多余空格和标点，取 hash
    normalized = "".join(question.lower().split())
    return hashlib.md5(normalized.encode()).hexdigest()


def get_cached_answer(question: str) -> dict | None:
    """查询缓存的问答结果。"""
    key = cache_key(question)
    return _cache.get(key)


def set_cached_answer(question: str, result: dict):
    """缓存问答结果（TTL 1小时）。"""
    key = cache_key(question)
    _cache.set(key, result, expire=settings.CACHE_TTL_SECONDS)


def get_question_suggestions(n: int = 4) -> list[str]:
    """从缓存中获取热门问题作为推荐。"""
    # diskcache 没有直接获取所有 key 的方法，返回预设建议
    suggestions = [
        "这件商品有什么特点？",
        "如何退换货？",
        "商品支持什么支付方式？",
        "这款产品的材质是什么？",
        "有没有优惠活动？",
        "商品的保修期是多久？",
    ]
    return suggestions[:n]


def get_rate_limit(key: str, max_requests: int, window_seconds: int = 60) -> bool:
    """简易令牌桶限流 —— 返回 True 表示允许请求。"""
    cache_key_rl = f"rate_limit:{key}"
    current = _cache.get(cache_key_rl, 0)
    if current >= max_requests:
        return False
    _cache.set(cache_key_rl, current + 1, expire=window_seconds)
    return True
