"""文档分块 —— 父子文档模式。"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import get_settings

settings = get_settings()


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """获取分块器：chunk_size=500, overlap=50，按中文标点和段落分块。"""
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", ".", "!", "?", ";", ",", " ", ""],
        length_function=len,
    )


def split_documents(documents: list) -> list:
    """将文档列表切分为文本块，保留原始 metadata。"""
    splitter = get_text_splitter()
    return splitter.split_documents(documents)
