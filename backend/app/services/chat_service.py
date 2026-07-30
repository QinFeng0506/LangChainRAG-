"""聊天服务 —— RAG 问答 + 流式输出 + 会话管理。"""
import json
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.session import Session
from app.models.message import Message
from app.rag.graph import rag_graph
from app.config import get_settings

settings = get_settings()


# ===== 会话管理 =====
async def get_user_sessions(db: AsyncSession, user_id: str) -> list[Session]:
    """获取用户的所有会话，按更新时间倒序。"""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_session(db: AsyncSession, session_id: str, user_id: str) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_session(db: AsyncSession, user_id: str, title: str = "新会话") -> Session:
    session = Session(user_id=user_id, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def rename_session(db: AsyncSession, session_id: str, user_id: str, title: str) -> Session | None:
    session = await get_session(db, session_id, user_id)
    if session:
        session.title = title
        await db.commit()
    return session


async def delete_session(db: AsyncSession, session_id: str, user_id: str) -> bool:
    session = await get_session(db, session_id, user_id)
    if session:
        await db.delete(session)
        await db.commit()
        return True
    return False


async def get_session_messages(
    db: AsyncSession, session_id: str, user_id: str, limit: int = 100
) -> list[Message]:
    """获取会话历史消息。"""
    session = await get_session(db, session_id, user_id)
    if not session:
        return []
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def save_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> Message:
    """保存消息到数据库。"""
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        sources=json.dumps(sources, ensure_ascii=False) if sources else None,
    )
    db.add(msg)

    # 更新会话时间
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(msg)
    return msg


async def auto_generate_title(db: AsyncSession, session_id: str, first_question: str):
    """根据首个问题自动生成会话标题。"""
    from app.rag.llm_client import chat_completion_sync

    # Mock 模式：直接用问题截断作为标题，跳过 LLM 调用
    if settings.STRESS_TEST_MOCK:
        title = first_question[:20]
    else:
        prompt = f"请将以下用户问题概括为10字以内的会话标题。直接返回标题，不要添加任何解释：\n\n{first_question}"

        try:
            title = await chat_completion_sync(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=20,
            )
            title = title.strip().strip('"').strip("《》").strip()
            if len(title) > 20:
                title = title[:20]
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("LLM 生成会话标题失败，使用问题截断作为标题: %s", str(e))
            title = first_question[:20]

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session and session.title == "新会话":
        session.title = title or "新会话"
        await db.commit()


# ===== RAG 问答 =====
async def rag_query(question: str) -> dict:
    """执行完整 RAG 流程并返回结果。"""
    initial_state = {
        "question": question,
        "rewritten_question": "",
        "candidates": [],
        "final_docs": [],
        "answer": "",
        "sources": [],
    }
    result = await rag_graph.ainvoke(initial_state)
    return {
        "answer": result["answer"],
        "sources": result["sources"],
    }


async def build_conversation_context(
    db: AsyncSession, session_id: str, max_rounds: int = None
) -> list[dict]:
    """从数据库加载多轮对话历史，构建 LLM 上下文。"""
    rounds = max_rounds or settings.MAX_HISTORY_ROUNDS

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(rounds * 2)  # 每轮2条消息(user+assistant)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # 时间正序

    history = []
    for msg in messages:
        history.append({
            "role": msg.role,
            "content": msg.content,
        })
    return history
