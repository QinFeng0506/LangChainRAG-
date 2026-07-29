import { useState, useEffect, useRef, useCallback } from 'react';
import { Input, Button, Spin, Empty, Typography, message, Popconfirm, theme } from 'antd';
import { SendOutlined, PlusOutlined, DeleteOutlined, MessageOutlined } from '@ant-design/icons';
import { useChatStore } from '../store/chatStore';
import {
  getSessions, createSession, deleteSession,
  getSessionMessages, createChatStream,
} from '../api/chat';
import ChatMessage from '../components/ChatMessage';
import type { MessageInfo, SessionInfo, SourceInfo } from '../types';

const { TextArea } = Input;
const { Text } = Typography;

export default function Chat() {
  const { token: t } = theme.useToken();
  const {
    sessions, currentSessionId, messages,
    streaming, streamingContent, streamingSources,
    setSessions, setCurrentSession, setMessages,
    setStreaming, appendStreamChunk, setStreamSources, finishStreaming, clearStreaming,
  } = useChatStore();

  const [inputValue, setInputValue] = useState('');
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 加载会话列表
  const loadSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const list = await getSessions();
      setSessions(list);
    } catch {
      // ignore
    } finally {
      setLoadingSessions(false);
    }
  }, [setSessions]);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  // 切换会话时加载消息
  useEffect(() => {
    if (!currentSessionId) return;
    setLoadingMessages(true);
    getSessionMessages(currentSessionId)
      .then((msgs) => setMessages(msgs))
      .catch(() => {})
      .finally(() => setLoadingMessages(false));
  }, [currentSessionId, setMessages]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // 新建会话
  const handleNewSession = async () => {
    try {
      const session = await createSession();
      await loadSessions();
      setCurrentSession(session.id);
      setMessages([]);
    } catch {
      message.error('创建会话失败');
    }
  };

  // 删除会话
  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      await loadSessions();
      if (currentSessionId === id) {
        setCurrentSession(sessions.find((s) => s.id !== id)?.id || null);
        setMessages([]);
      }
    } catch {
      message.error('删除失败');
    }
  };

  // 发送问题
  const handleSend = async () => {
    const question = inputValue.trim();
    if (!question || streaming) return;

    let sessionId = currentSessionId;
    if (!sessionId) {
      const session = await createSession();
      setCurrentSession(session.id);
      sessionId = session.id;
      await loadSessions();
    }

    // 添加用户消息到界面
    setMessages([
      ...messages,
      { id: `temp_${Date.now()}`, role: 'user', content: question, created_at: new Date().toISOString() },
    ]);
    setInputValue('');
    setStreaming(true);

    const controller = createChatStream(
      sessionId,
      question,
      (chunk) => appendStreamChunk(chunk),
      (sources: SourceInfo[]) => setStreamSources(sources),
      () => {
        const content = useChatStore.getState().streamingContent;
        const sources = useChatStore.getState().streamingSources;
        if (content) {
          finishStreaming(content, sources);
        } else {
          clearStreaming();
        }
        loadSessions();
      },
      (error: string) => {
        message.error(error);
        clearStreaming();
      },
    );
    abortRef.current = controller;
  };

  // 键盘快捷键
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 当前选中的会话
  const currentSession = sessions.find((s) => s.id === currentSessionId);

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* 会话列表侧边栏 */}
      <div style={{
        width: 260, borderRight: `1px solid ${t.colorBorderSecondary}`,
        display: 'flex', flexDirection: 'column', background: t.colorFillAlter,
      }}>
        <div style={{ padding: '12px 16px', borderBottom: `1px solid ${t.colorBorderSecondary}` }}>
          <Button type="primary" icon={<PlusOutlined />} block onClick={handleNewSession}>
            新建会话
          </Button>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {loadingSessions ? (
            <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
          ) : sessions.length === 0 ? (
            <Empty description="暂无会话" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 32 }} />
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => setCurrentSession(session.id)}
                style={{
                  padding: '12px 16px', cursor: 'pointer',
                  background: session.id === currentSessionId ? t.colorPrimaryBg : 'transparent',
                  borderLeft: session.id === currentSessionId ? `3px solid ${t.colorPrimary}` : '3px solid transparent',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <div style={{ fontWeight: session.id === currentSessionId ? 600 : 400, fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: t.colorText }}>
                    <MessageOutlined style={{ marginRight: 8, fontSize: 12 }} />
                    {session.title}
                  </div>
                  <div style={{ fontSize: 11, color: t.colorTextTertiary, marginTop: 2 }}>
                    {new Date(session.updated_at).toLocaleDateString('zh-CN')}
                  </div>
                </div>
                <Popconfirm
                  title="确认删除此会话？"
                  onConfirm={(e) => { e?.stopPropagation(); handleDeleteSession(session.id); }}
                  onCancel={(e) => e?.stopPropagation()}
                  okText="确认"
                  cancelText="取消"
                >
                  <Button
                    type="text" size="small" danger
                    icon={<DeleteOutlined />}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Popconfirm>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 聊天主区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* 消息列表 */}
        <div style={{ flex: 1, overflow: 'auto', background: t.colorBgContainer }}>
          {loadingMessages ? (
            <div style={{ textAlign: 'center', padding: 48 }}><Spin tip="加载消息中..." /></div>
          ) : messages.length === 0 && !streaming ? (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', height: '100%', color: t.colorTextQuaternary,
            }}>
              <MessageOutlined style={{ fontSize: 48, marginBottom: 16 }} />
              <Text type="secondary" style={{ fontSize: 16 }}>开始提问，获取智能回答</Text>
              <Text type="secondary" style={{ fontSize: 13, marginTop: 8 }}>
                回答将引用知识库内容并展示来源片段
              </Text>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {/* 流式生成中的消息 */}
              {streaming && streamingContent && (
                <ChatMessage
                  message={{
                    id: 'streaming',
                    role: 'assistant',
                    content: streamingContent,
                    sources: streamingSources,
                    created_at: new Date().toISOString(),
                  }}
                />
              )}
              {streaming && !streamingContent && (
                <div style={{ padding: 24, textAlign: 'center' }}>
                  <Spin tip="AI 正在思考..." />
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入框 */}
        <div style={{
          borderTop: `1px solid ${t.colorBorderSecondary}`, padding: '16px 24px',
          background: t.colorBgContainer,
        }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的问题... (Enter 发送，Shift+Enter 换行)"
              autoSize={{ minRows: 1, maxRows: 5 }}
              disabled={streaming}
              style={{ flex: 1 }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={streaming}
              disabled={!inputValue.trim()}
              style={{ alignSelf: 'flex-end' }}
            >
              发送
            </Button>
          </div>
          <div style={{ marginTop: 4, fontSize: 11, color: t.colorTextQuaternary, textAlign: 'right' }}>
            Enter 发送 | Shift+Enter 换行
          </div>
        </div>
      </div>
    </div>
  );
}
