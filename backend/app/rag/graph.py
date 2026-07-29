"""LangGraph RAG 流程编排 —— 改写 → 检索 → 精排 → 生成 → 溯源。"""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from app.rag.llm_client import chat_completion, chat_completion_sync
from app.rag.retriever import hybrid_search
from app.rag.reranker import rerank_documents
from app.config import get_settings

settings = get_settings()


# ===== State 定义 =====
class RAGState(TypedDict):
    question: str            # 用户原始问题
    rewritten_question: str  # 改写后的问题（检索友好）
    candidates: list[dict]   # 混合检索结果
    final_docs: list[dict]   # 重排序后的最终文档
    answer: str              # LLM 生成的回答
    sources: list[dict]      # 引用溯源列表


# ===== 节点函数 =====

async def rewrite_question(state: RAGState) -> RAGState:
    """节点1：用 LLM 改写用户问题为检索友好形式。"""
    question = state["question"]

    prompt = f"""你是一个电商客服问答系统的查询改写助手。请将用户的原始问题改写为更适合知识库检索的形式。

规则：
1. 保留原始语义，不要添加或删除关键信息
2. 将口语化表达转换为书面表达
3. 补充隐含的上下文信息（如商品名、品牌等）
4. 去除无关的语气词和客套话
5. 如果原始问题已经非常清晰，直接返回原问题

原始问题：{question}

改写后的问题（只返回改写后的问题，不要添加任何解释）："""

    try:
        rewritten = await chat_completion_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        state["rewritten_question"] = rewritten.strip()
    except Exception:
        state["rewritten_question"] = question

    return state


async def retrieve(state: RAGState) -> RAGState:
    """节点2：混合检索（语义 + BM25）。"""
    query = state.get("rewritten_question") or state["question"]
    candidates = await hybrid_search(query, top_k=settings.RETRIEVAL_TOP_K)

    # 过滤低分结果
    filtered = [c for c in candidates if c.get("score", 0) > settings.SIMILARITY_THRESHOLD]
    if not filtered:
        # 如果没有高于阈值的，保留前5个
        filtered = candidates[:settings.RERANK_TOP_K]

    state["candidates"] = filtered
    return state


async def rerank(state: RAGState) -> RAGState:
    """节点3：Cross-Encoder 精排。"""
    query = state.get("rewritten_question") or state["question"]
    candidates = state["candidates"]

    if not candidates:
        state["final_docs"] = []
        return state

    reranked = await rerank_documents(query, candidates, top_k=settings.RERANK_TOP_K)
    state["final_docs"] = reranked
    return state


async def generate(state: RAGState) -> RAGState:
    """节点4：基于检索结果 + 对话历史，LLM 流式生成回答。"""
    docs = state["final_docs"]
    question = state["question"]

    # 构建带引用标记的上下文
    context_parts = []
    for i, doc in enumerate(docs):
        meta = doc.get("metadata", {})
        source_name = meta.get("doc_name", f"文档{i+1}")
        context_parts.append(f"[来源{i+1}] 文档《{source_name}》：\n{doc['text']}")

    context = "\n\n---\n\n".join(context_parts) if context_parts else "（知识库中暂无相关内容）"

    # 根据是否有匹配文档构建不同的 system prompt
    if docs:
        system_prompt = f"""你是一个专业的电商客服助手，专门回答用户关于商品的问题。请严格根据以下知识库内容作答。

## 回答规则
1. **仅基于知识库内容回答**，不要编造任何不在知识库中的信息
2. 回答时**必须引用具体来源**，使用 [1] [2] 等编号标注引用的知识库片段
3. 如果知识库中的信息不足以回答问题，请明确说明"根据现有信息无法确定"，并建议用户联系人工客服
4. 涉及到价格、库存等时效性信息时，提醒用户以页面实际显示为准
5. 如果用户询问的是商品对比，用表格形式呈现对比信息
6. 回答要友好、专业、准确，中式电商客服风格

## 知识库内容
{context}

请开始回答用户的问题。"""
    else:
        system_prompt = f"""你是一个基于 LangChain 框架开发的 RAG（检索增强生成）企业级知识库问答系统的 AI 助手。

## 关于你自己
- 你运行在阿里云百炼平台上，底层使用 DeepSeek-V3 大语言模型
- 你通过 ChromaDB 向量数据库检索知识库内容来回答问题
- 当前知识库尚未上传相关文档，所以暂时无法引用具体资料

## 你能做什么
- 回答电商平台商品相关的各种问题（需要管理员先上传知识库文档）
- 帮助用户了解退换货政策、支付方式、配送信息等
- 提供商品对比、选购建议等

## 当前知识库状态
{context}

## 回答规则
1. 如果用户问"你是谁"、"你能做什么"之类的问题，根据自己的身份设定友好回答
2. 如果用户问商品相关问题但知识库为空，礼貌告知"知识库中暂无相关内容，请联系管理员上传文档"
3. 回答风格：友好、专业，中式电商客服风格
4. 如果知识库中有内容，必须引用来源

用户问题：{question}

请回答："""

    # 无文档时也保留来源（可能是空列表）

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    try:
        answer = await chat_completion_sync(
            messages=messages,
            temperature=0.5,
            max_tokens=2048,
        )
        state["answer"] = answer
    except Exception as e:
        state["answer"] = f"回答生成失败: {str(e)}"

    # 构建引用溯源
    sources = []
    seen_docs = set()
    for i, doc in enumerate(docs):
        meta = doc.get("metadata", {})
        doc_name = meta.get("doc_name", f"文档{i+1}")
        if doc_name not in seen_docs:
            sources.append({
                "doc_name": doc_name,
                "chunk_text": doc["text"][:300] + ("..." if len(doc["text"]) > 300 else ""),
                "score": round(doc.get("score", 0), 4),
                "image_path": meta.get("image_path"),
            })
            seen_docs.add(doc_name)

    state["sources"] = sources
    return state


# ===== 构建 LangGraph =====
def build_rag_graph() -> StateGraph:
    """构建 RAG 流程 Graph。"""
    workflow = StateGraph(RAGState)

    # 添加节点
    workflow.add_node("rewrite", rewrite_question)  # type: ignore
    workflow.add_node("retrieve", retrieve)  # type: ignore
    workflow.add_node("rerank", rerank)  # type: ignore
    workflow.add_node("generate", generate)  # type: ignore

    # 设置流程：全流程
    workflow.set_entry_point("rewrite")
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# 全局编译好的 Graph
rag_graph = build_rag_graph()
