"""聊天 API 路由 —— 会话管理 + SSE 流式问答。"""
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import (
    CreateSessionRequest, SessionResponse, MessageResponse,
    ChatQueryRequest, RenameSessionRequest, FeedbackRequest, SourceInfo,
)
from app.services.chat_service import (
    get_user_sessions, get_session, create_session, rename_session, delete_session,
    get_session_messages, save_message, rag_query, auto_generate_title,
)
from app.utils.cache import get_cached_answer, set_cached_answer, get_rate_limit
from app.config import get_settings

_settings = get_settings()

router = APIRouter(prefix="/api/chat", tags=["聊天"])


# ===== 会话管理 =====

@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的会话列表。"""
    sessions = await get_user_sessions(db, current_user.id)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_new_session(
    req: CreateSessionRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新会话。"""
    title = req.title if req and req.title else "新会话"
    session = await create_session(db, current_user.id, title)
    return SessionResponse.model_validate(session)


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    req: RenameSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """重命名会话。"""
    session = await rename_session(db, session_id, current_user.id, req.title)
    if not session:
        raise HTTPException(404, "会话不存在")
    return {"message": "已重命名"}


@router.delete("/sessions/{session_id}")
async def remove_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除会话。"""
    success = await delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(404, "会话不存在")
    return {"message": "已删除"}


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话历史消息。"""
    session = await get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(404, "会话不存在")

    messages = await get_session_messages(db, session_id, current_user.id)

    result = []
    for msg in messages:
        sources = None
        if msg.sources:
            try:
                sources = [SourceInfo(**s) for s in json.loads(msg.sources)]
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            sources=sources,
            created_at=msg.created_at,
        ))
    return result


# ===== 问答 (SSE 流式) =====

@router.post("/query")
async def chat_query(
    req: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送问题 —— SSE 流式返回 RAG 回答 + 引用来源。"""
    # 验证会话归属
    session = await get_session(db, req.session_id, current_user.id)
    if not session:
        raise HTTPException(404, "会话不存在")

    # 限流检查
    if not get_rate_limit(current_user.id, _settings.RATE_LIMIT_PER_MINUTE):
        raise HTTPException(429, f"请求过于频繁，每分钟最多 {_settings.RATE_LIMIT_PER_MINUTE} 次")

    # 缓存检查（相同问题直接返回缓存）
    cached = get_cached_answer(req.question)
    if cached:
        async def cached_stream():
            answer = cached["answer"]
            for i in range(0, len(answer), 3):
                yield f"data: {json.dumps({'type': 'chunk', 'content': answer[i:i+3]}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'type': 'sources', 'sources': cached['sources']}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(cached_stream(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})

    # 保存用户问题
    user_msg = await save_message(db, req.session_id, "user", req.question)

    # 首次提问自动生成标题
    messages = await get_session_messages(db, req.session_id, current_user.id)
    if len(messages) <= 1:
        await auto_generate_title(db, req.session_id, req.question)

    async def event_stream():
        """SSE 事件流 —— 先用非流式 RAG 生成，再逐字发送。"""
        try:
            # 执行 RAG 流程
            result = await rag_query(req.question)
            answer = result["answer"]
            sources = result["sources"]

            # 逐字发送答案（模拟流式效果）
            chunk_size = 3  # 每次发送3个字符
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)

            # 发送引用来源
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"

            # 保存助手回复 + 缓存
            from app.database import async_session as as_db
            async with as_db() as _db:
                await save_message(_db, req.session_id, "assistant", answer, sources)
            set_cached_answer(req.question, {"answer": answer, "sources": sources})

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

        # 结束信号
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    current_user: User = Depends(get_current_user),
):
    """保存用户反馈（点赞/点踩）。暂存至日志，后续可扩展。"""
    import logging
    logger = logging.getLogger("chat_feedback")
    logger.info(f"Feedback: user={current_user.username}, message={req.message_id}, rating={req.rating}, comment={req.comment}")
    return {"message": "反馈已记录，感谢您的参与"}
