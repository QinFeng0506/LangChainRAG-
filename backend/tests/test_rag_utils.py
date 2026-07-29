"""RAG 工具模块单元测试 —— 文档加载、分块、缓存、文件存储。"""
import os
import tempfile
import pytest


class TestDocumentSplitter:
    """文档分块器测试。"""

    def test_chunk_size_and_overlap(self):
        """分块大小和重叠应符合配置。"""
        from app.rag.splitter import get_text_splitter, split_documents
        from langchain_core.documents import Document

        # 构造 1500 字符的测试文档
        long_text = "这是一个测试文档。" * 150

        chunks = split_documents([Document(page_content=long_text)])
        assert len(chunks) > 1, "长文档应被切分为多个块"

        # 验证 chunk_size 约束
        for chunk in chunks:
            assert len(chunk.page_content) <= 550, f"分块大小应不超过 550（500+overlap 容忍）"

    def test_short_document_single_chunk(self):
        """短文档应保持为单一块。"""
        from app.rag.splitter import split_documents
        from langchain_core.documents import Document

        short_text = "简短文档。只有一句话。"
        chunks = split_documents([Document(page_content=short_text)])
        assert len(chunks) == 1
        assert chunks[0].page_content == short_text

    def test_preserves_metadata(self):
        """分块后应保留原始 metadata。"""
        from app.rag.splitter import split_documents
        from langchain_core.documents import Document

        doc = Document(page_content="测试内容。" * 100, metadata={"source": "test.md", "page": 1})
        chunks = split_documents([doc])

        for chunk in chunks:
            assert chunk.metadata.get("source") == "test.md"
            assert chunk.metadata.get("page") == 1

    def test_empty_document_list(self):
        """空文档列表应返回空列表。"""
        from app.rag.splitter import split_documents

        chunks = split_documents([])
        assert chunks == []

    def test_chinese_separators(self):
        """中文标点应作为分割点 —— 验证分块器包含中文分隔符。"""
        from app.rag.splitter import get_text_splitter

        splitter = get_text_splitter()
        # 验证中文标点在分隔符列表中
        assert "。" in splitter._separators
        assert "！" in splitter._separators
        assert "？" in splitter._separators

    def test_splitter_config(self):
        """分块器配置应正确加载。"""
        from app.rag.splitter import get_text_splitter

        splitter = get_text_splitter()
        assert splitter._chunk_size == 500
        assert splitter._chunk_overlap == 50


class TestBM25Scorer:
    """BM25 关键词评分器测试。"""

    def test_basic_scoring(self):
        """基本评分 —— 包含关键词的文档得分更高。"""
        from app.rag.retriever import BM25Scorer

        scorer = BM25Scorer()
        docs = [
            "苹果是一种水果，含有丰富的维生素",
            "香蕉也是水果，口感软糯",
            "汽车是一种交通工具，使用汽油驱动",
        ]
        scorer.fit(docs)

        score_apple = scorer.score("苹果", 0)
        score_banana = scorer.score("苹果", 1)
        score_car = scorer.score("苹果", 2)

        # 包含"苹果"的文档 0 得分最高
        assert score_apple > score_banana
        assert score_apple > score_car

    def test_empty_query(self):
        """空查询应返回 0 分。"""
        from app.rag.retriever import BM25Scorer

        scorer = BM25Scorer()
        scorer.fit(["测试文档内容"])

        score = scorer.score("", 0)
        assert score == 0.0

    def test_english_mixed_text(self):
        """中英混合文本应正确处理。"""
        from app.rag.retriever import BM25Scorer

        scorer = BM25Scorer()
        docs = ["iPhone 15 Pro 拥有 A17 Pro 芯片"]
        scorer.fit(docs)

        # 英文关键词应能匹配
        score = scorer.score("iPhone", 0)
        assert score > 0

    def test_idf_computation(self):
        """IDF 计算 —— 出现在所有文档的词权重低。"""
        from app.rag.retriever import BM25Scorer

        scorer = BM25Scorer()
        docs = [
            "商品A 红色 大码",
            "商品B 红色 中码",
            "商品C 蓝色 小码",
        ]
        scorer.fit(docs)

        # "红色"出现在 2/3 文档中，权重应低于"蓝色"（仅 1/3）
        assert "红色" in scorer.idf
        assert "蓝色" in scorer.idf
        # IDF 值：蓝色 > 红色（越稀有越高）
        assert scorer.idf["蓝色"] > scorer.idf["红色"]


class TestCacheUtils:
    """缓存工具测试。"""

    def test_cache_key_consistent(self):
        """相同问题应生成相同缓存 key。"""
        from app.utils.cache import cache_key

        k1 = cache_key("这件商品有什么特点？")
        k2 = cache_key("这件商品有什么特点？")
        assert k1 == k2

    def test_cache_key_normalized(self):
        """空白字符差异应被标准化。"""
        from app.utils.cache import cache_key

        k1 = cache_key("how much is this")
        k2 = cache_key("how  much is  this")
        assert k1 == k2

    def test_cache_set_and_get(self):
        """缓存写入和读取应正确。"""
        from app.utils.cache import set_cached_answer, get_cached_answer

        question = "测试问题" + os.urandom(4).hex()
        result = {"answer": "测试回答", "sources": []}

        set_cached_answer(question, result)
        cached = get_cached_answer(question)
        assert cached is not None
        assert cached["answer"] == "测试回答"

    def test_cache_miss(self):
        """未缓存的查询应返回 None。"""
        from app.utils.cache import get_cached_answer

        result = get_cached_answer("完全不存在的问题" + os.urandom(8).hex())
        assert result is None

    def test_rate_limit_allows(self):
        """限流器在配额内应允许请求。"""
        from app.utils.cache import get_rate_limit

        key = f"test_user_{os.urandom(4).hex()}"
        # 前几次应允许
        for i in range(5):
            assert get_rate_limit(key, max_requests=10, window_seconds=60)

    def test_rate_limit_blocks(self):
        """限流器超出配额应拒绝。"""
        from app.utils.cache import get_rate_limit

        key = f"test_blocked_{os.urandom(4).hex()}"
        max_req = 3

        # 消耗所有配额
        for _ in range(max_req):
            assert get_rate_limit(key, max_requests=max_req, window_seconds=60)

        # 超出配额
        assert not get_rate_limit(key, max_requests=max_req, window_seconds=60)

    def test_get_question_suggestions(self):
        """问题建议应返回预设列表。"""
        from app.utils.cache import get_question_suggestions

        suggestions = get_question_suggestions(3)
        assert len(suggestions) == 3
        for s in suggestions:
            assert isinstance(s, str)
            assert len(s) > 0


class TestFileStorage:
    """文件存储工具测试。"""

    def test_validate_file_type_allowed(self):
        """允许的文件类型应通过校验。"""
        from app.utils.file_storage import validate_file_type

        for name in ["doc.pdf", "data.txt", "sheet.csv", "readme.md", "photo.png", "img.jpg", "商品.webp"]:
            assert validate_file_type(name), f"{name} 应被允许"

    def test_validate_file_type_rejected(self):
        """不被允许的文件类型应被拒绝。"""
        from app.utils.file_storage import validate_file_type

        for name in ["virus.exe", "script.bat", "malware.dll", "noextension"]:
            assert not validate_file_type(name), f"{name} 应被拒绝"

    def test_get_file_type_mapping(self):
        """文件类型映射应正确。"""
        from app.utils.file_storage import get_file_type

        assert get_file_type("pdf") == "pdf"
        assert get_file_type("txt") == "txt"
        assert get_file_type("png") == "image"
        assert get_file_type("jpg") == "image"
        assert get_file_type("webp") == "image"
        assert get_file_type("md") == "md"
        assert get_file_type("docx") == "docx"

    def test_save_and_delete_upload(self):
        """上传保存和删除应正常运作。"""
        import aiofiles
        from io import BytesIO
        from fastapi import UploadFile
        from app.utils.file_storage import save_upload, delete_document_files

        # 创建模拟上传文件
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("test content")

        # 保存
        info = {
            "doc_id": "test_doc_id",
            "filename": "test.txt",
            "file_type": "txt",
            "file_size": os.path.getsize(file_path),
            "file_path": file_path,
            "doc_dir": temp_dir,
        }

        # 验证文件存在
        assert os.path.exists(file_path)

        # 删除
        delete_document_files(temp_dir)
        assert not os.path.exists(temp_dir), "删除后目录不应存在"

    def test_allowed_extensions_set(self):
        """允许扩展名集合应包含常见格式。"""
        from app.utils.file_storage import ALLOWED_EXTENSIONS

        expected = {"pdf", "txt", "csv", "md", "markdown", "docx", "xlsx", "png", "jpg", "jpeg", "webp", "gif"}
        for ext in expected:
            assert ext in ALLOWED_EXTENSIONS, f"{ext} 应在允许列表中"


class TestEmbeddingIntegration:
    """Embedding API 测试（需真实 API Key）。"""

    @pytest.mark.slow
    async def test_embed_single_text(self):
        """单文本向量化应返回正确维度向量。"""
        from app.rag.embedding import embed_single
        from app.config import get_settings

        settings = get_settings()
        if not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY.startswith("your-"):
            pytest.skip("未配置百炼 API Key")

        vector = await embed_single("测试文本")
        assert len(vector) > 100  # 向量维度应大于 100

    @pytest.mark.slow
    async def test_embed_batch(self):
        """批量向量化应返回相同数量向量。"""
        from app.rag.embedding import embed_texts
        from app.config import get_settings

        settings = get_settings()
        if not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY.startswith("your-"):
            pytest.skip("未配置百炼 API Key")

        texts = ["第一段测试文本", "第二段测试文本", "第三段测试文本"]
        vectors = await embed_texts(texts)
        assert len(vectors) == 3
        assert all(len(v) > 100 for v in vectors)
