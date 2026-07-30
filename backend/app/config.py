"""应用配置管理 —— 通过 .env 文件和 pydantic-settings 加载。"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # ===== 应用基础 =====
    APP_NAME: str = "LangChain RAG 知识库问答系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ===== JWT 认证 =====
    # ⚠️ 生产环境必须通过 .env 设置强随机密钥，默认空值启动时会随机生成
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ===== 数据库 SQLite =====
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # ===== ChromaDB 向量库 =====
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"

    # ===== 阿里云百炼 DashScope =====
    DASHSCOPE_API_KEY: str = ""
    # LLM 模型：qwen-plus, qwen-max, deepseek-v3 等
    LLM_MODEL: str = "qwen-plus"
    # Embedding 模型
    EMBEDDING_MODEL: str = "text-embedding-v3"
    # 多模态 VL 模型
    VL_MODEL: str = "qwen-vl-plus"
    # 重排序模型
    RERANK_MODEL: str = "gte-rerank"

    # 百炼 DashScope 兼容 OpenAI 协议
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ===== 文件存储 =====
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ===== RAG 参数 =====
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 20        # 粗排返回数量
    RERANK_TOP_K: int = 5            # 精排后返回数量
    MAX_HISTORY_ROUNDS: int = 10     # 多轮对话上下文轮数
    SIMILARITY_THRESHOLD: float = 0.5

    # ===== 缓存 =====
    CACHE_DIR: str = "./data/cache"
    CACHE_TTL_SECONDS: int = 3600    # 缓存过期时间，默认1小时

    # ===== 限流 =====
    RATE_LIMIT_PER_MINUTE: int = 20  # 单用户每分钟最多请求数

    # ===== 压力测试 Mock 模式 =====
    STRESS_TEST_MOCK: bool = False  # True 时跳过所有百炼 API 调用，使用模拟返回

    # ===== 管理员预设 =====
    ADMIN_USERNAME: str = "admin"
    # ⚠️ 生产环境必须通过 .env 设置强密码，默认空值启动时会随机生成
    ADMIN_PASSWORD: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
