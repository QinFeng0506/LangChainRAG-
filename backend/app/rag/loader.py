"""文档加载器 —— 统一入口，按文件类型分派。"""
import os
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, CSVLoader, UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader, UnstructuredExcelLoader,
)


def load_document(file_path: str, file_type: str) -> list:
    """根据文件类型加载文档，返回 LangChain Document 列表。"""
    loaders = {
        "pdf": PyPDFLoader,
        "txt": TextLoader,
        "csv": CSVLoader,
        "docx": UnstructuredWordDocumentLoader,
        "md": UnstructuredMarkdownLoader,
        "markdown": UnstructuredMarkdownLoader,
        "xlsx": UnstructuredExcelLoader,
    }

    loader_cls = loaders.get(file_type)
    if loader_cls is None:
        raise ValueError(f"不支持的文件类型: {file_type}")

    loader = loader_cls(file_path, encoding="utf-8") if file_type == "txt" else loader_cls(file_path)
    return loader.load()
