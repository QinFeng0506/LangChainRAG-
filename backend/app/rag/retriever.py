"""混合检索器 —— 语义向量 + BM25 关键词双路召回 + RRF 融合。"""
import re
from math import log
from collections import defaultdict
from app.rag.embedding import embed_single
from app.rag.vector_store import search_similar
from app.config import get_settings

settings = get_settings()


# ===== BM25 简易实现 =====
class BM25Scorer:
    """轻量级 BM25 关键词评分器。"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_term_freqs: list[dict[str, int]] = []
        self.doc_lengths: list[int] = []
        self.avg_doc_len: float = 0
        self.doc_count: int = 0
        self.idf: dict[str, float] = {}

    def fit(self, documents: list[str]):
        """对文档集合建立索引。"""
        tokenized = [self._tokenize(d) for d in documents]
        self.doc_term_freqs = [self._count_terms(tokens) for tokens in tokenized]
        self.doc_lengths = [len(tokens) for tokens in tokenized]
        self.doc_count = len(documents)
        self.avg_doc_len = sum(self.doc_lengths) / max(self.doc_count, 1)
        self._compute_idf()

    def _tokenize(self, text: str) -> list[str]:
        """简单中文分词（按2-gram + 英文分词）。"""
        # 中文字符用2-gram
        tokens = []
        text = text.lower()
        # 英文单词
        eng_tokens = re.findall(r'[a-zA-Z0-9]+', text)
        tokens.extend(eng_tokens)
        # 中文+混合字符用character 2-gram
        cn_chars = re.sub(r'[a-zA-Z0-9\s]', '', text)
        for i in range(len(cn_chars) - 1):
            tokens.append(cn_chars[i:i + 2])
        for char in cn_chars:
            tokens.append(char)
        return tokens

    def _count_terms(self, tokens: list[str]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for t in tokens:
            counts[t] += 1
        return dict(counts)

    def _compute_idf(self):
        self.idf = {}
        for tfs in self.doc_term_freqs:
            for term in tfs:
                self.idf[term] = self.idf.get(term, 0) + 1
        for term in self.idf:
            df = self.idf[term]
            self.idf[term] = log((self.doc_count - df + 0.5) / (df + 0.5) + 1)

    def score(self, query: str, doc_idx: int) -> float:
        """计算查询与文档的 BM25 分数。"""
        query_tokens = self._tokenize(query)
        doc_tfs = self.doc_term_freqs[doc_idx]
        doc_len = self.doc_lengths[doc_idx]
        score = 0.0
        for token in query_tokens:
            if token not in self.idf:
                continue
            tf = doc_tfs.get(token, 0)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / max(self.avg_doc_len, 1))
            score += self.idf[token] * numerator / max(denominator, 0.001)
        return score


# ===== 混合检索入口 =====
_bm25_scorer: BM25Scorer | None = None
_chunk_cache: list[dict] = []  # 缓存分块文本用于 BM25


def build_bm25_index(chunks: list[dict]):
    """构建/更新 BM25 索引。"""
    global _bm25_scorer, _chunk_cache
    if not chunks:
        return
    _chunk_cache = chunks
    texts = [c.get("text", "") for c in chunks]
    _bm25_scorer = BM25Scorer()
    _bm25_scorer.fit(texts)


def _semantic_search(query: str, top_k: int = None) -> list[dict]:
    """语义向量检索。"""
    query_embedding = _sync_embed(query)  # 同步调用（在 asyncio loop 中执行）
    k = top_k or settings.RETRIEVAL_TOP_K
    raw = search_similar(
        settings.CHROMA_COLLECTION_NAME,
        query_embedding,
        top_k=k,
    )
    results = []
    if raw.get("ids") and raw["ids"][0]:
        for i in range(len(raw["ids"][0])):
            results.append({
                "id": raw["ids"][0][i],
                "text": raw["documents"][0][i] if raw.get("documents") else "",
                "metadata": raw["metadatas"][0][i] if raw.get("metadatas") else {},
                "score": 1.0 - raw["distances"][0][i] if raw.get("distances") else 0,
            })
    return results


def _keyword_search(query: str, top_k: int = None) -> list[dict]:
    """BM25 关键词检索。"""
    global _bm25_scorer, _chunk_cache
    k = top_k or settings.RETRIEVAL_TOP_K
    if _bm25_scorer is None or not _chunk_cache:
        return []

    scores = []
    for idx in range(len(_chunk_cache)):
        s = _bm25_scorer.score(query, idx)
        scores.append((idx, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    results = []
    for idx, score in scores[:k]:
        if score > 0:
            results.append({
                "id": _chunk_cache[idx].get("id", f"bm25_{idx}"),
                "text": _chunk_cache[idx].get("text", ""),
                "metadata": _chunk_cache[idx].get("metadata", {}),
                "score": score,
            })
    return results


def _rrf_fusion(semantic_results: list[dict], keyword_results: list[dict], k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion —— 合并双路检索结果。"""
    scores: dict[str, dict] = {}
    for rank, item in enumerate(semantic_results):
        key = item["id"]
        scores[key] = item.copy()
        scores[key]["rrf"] = 1.0 / (k + rank + 1)

    for rank, item in enumerate(keyword_results):
        key = item["id"]
        if key in scores:
            scores[key]["rrf"] += 1.0 / (k + rank + 1)
        else:
            scores[key] = item.copy()
            scores[key]["rrf"] = 1.0 / (k + rank + 1)

    sorted_items = sorted(scores.values(), key=lambda x: x["rrf"], reverse=True)
    return sorted_items


async def hybrid_search(query: str, top_k: int = None) -> list[dict]:
    """混合检索入口：语义 + BM25 → RRF 融合。"""
    import asyncio
    k = top_k or settings.RETRIEVAL_TOP_K

    # 并行执行语义检索和关键词检索
    loop = asyncio.get_running_loop()
    semantic_results = await loop.run_in_executor(None, _semantic_search, query, k)
    keyword_results = await loop.run_in_executor(None, _keyword_search, query, k)

    # RRF 融合
    fused = _rrf_fusion(semantic_results, keyword_results)
    return fused


def _sync_embed(text: str) -> list[float]:
    """同步向量化（线程池中调用）。"""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 不在 asyncio 上下文中
        import asyncio as aio
        return aio.run(embed_single(text))

    import concurrent.futures
    future = asyncio.ensure_future(embed_single(text))
    return future.result()  # type: ignore
