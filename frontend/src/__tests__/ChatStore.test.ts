import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../api/chat', () => ({
  getSessions: vi.fn().mockResolvedValue([]),
  createSession: vi.fn().mockResolvedValue({ id: 's1', title: 'test', created_at: '', updated_at: '' }),
  deleteSession: vi.fn().mockResolvedValue(undefined),
  getSessionMessages: vi.fn().mockResolvedValue([]),
  createChatStream: vi.fn(),
}));

describe('ChatStore 聊天状态管理', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  it('初始状态应为空', async () => {
    const { useChatStore } = await import('../store/chatStore');
    const state = useChatStore.getState();

    expect(state.sessions).toEqual([]);
    expect(state.currentSessionId).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.streaming).toBe(false);
  });

  it('setSessions 应更新会话列表', async () => {
    const { useChatStore } = await import('../store/chatStore');

    useChatStore.getState().setSessions([
      { id: '1', title: '会话1', created_at: '', updated_at: '' },
      { id: '2', title: '会话2', created_at: '', updated_at: '' },
    ]);

    expect(useChatStore.getState().sessions).toHaveLength(2);
  });

  it('setCurrentSession 应切换当前会话', async () => {
    const { useChatStore } = await import('../store/chatStore');

    useChatStore.getState().setCurrentSession('session-123');
    expect(useChatStore.getState().currentSessionId).toBe('session-123');

    useChatStore.getState().setCurrentSession(null);
    expect(useChatStore.getState().currentSessionId).toBeNull();
  });

  it('setMessages 应更新消息列表', async () => {
    const { useChatStore } = await import('../store/chatStore');

    const msgs = [
      { id: '1', role: 'user' as const, content: '你好', created_at: '' },
      { id: '2', role: 'assistant' as const, content: '你好！请问有什么可以帮助你的？', sources: [], created_at: '' },
    ];

    useChatStore.getState().setMessages(msgs);
    expect(useChatStore.getState().messages).toHaveLength(2);
  });

  it('addMessage 应追加单条消息', async () => {
    const { useChatStore } = await import('../store/chatStore');

    useChatStore.getState().addMessage({
      id: 'msg1', role: 'user', content: '问题', created_at: '',
    });
    expect(useChatStore.getState().messages).toHaveLength(1);

    useChatStore.getState().addMessage({
      id: 'msg2', role: 'assistant', content: '回答', sources: [], created_at: '',
    });
    expect(useChatStore.getState().messages).toHaveLength(2);
  });

  it('appendStreamChunk 应累积流式文本', async () => {
    const { useChatStore } = await import('../store/chatStore');

    useChatStore.getState().setStreaming(true);
    useChatStore.getState().appendStreamChunk('你好');
    useChatStore.getState().appendStreamChunk('，世界');

    expect(useChatStore.getState().streamingContent).toBe('你好，世界');
  });

  it('finishStreaming 应将流式内容转为正式消息', async () => {
    const { useChatStore } = await import('../store/chatStore');

    // 模拟流式过程
    useChatStore.getState().setStreaming(true);
    useChatStore.getState().appendStreamChunk('这是回答内容');

    const sources = [{ doc_name: 'test.pdf', chunk_text: '来源片段', score: 0.95 }];
    useChatStore.getState().setStreamSources(sources);
    useChatStore.getState().finishStreaming('这是回答内容', sources);

    const state = useChatStore.getState();
    expect(state.streaming).toBe(false);
    expect(state.streamingContent).toBe('');
    // 消息中应有助手回复
    expect(state.messages).toHaveLength(1);
    expect(state.messages[0].role).toBe('assistant');
    expect(state.messages[0].content).toBe('这是回答内容');
    expect(state.messages[0].sources).toEqual(sources);
  });

  it('clearStreaming 应清除流式状态', async () => {
    const { useChatStore } = await import('../store/chatStore');

    useChatStore.getState().setStreaming(true);
    useChatStore.getState().appendStreamChunk('正在生成...');
    useChatStore.getState().clearStreaming();

    const state = useChatStore.getState();
    expect(state.streaming).toBe(false);
    expect(state.streamingContent).toBe('');
    expect(state.streamingSources).toEqual([]);
  });

  it('setStreamSources 应更新流式引用来源', async () => {
    const { useChatStore } = await import('../store/chatStore');

    const sources = [
      { doc_name: '商品介绍.pdf', chunk_text: '描述文本', score: 0.88 },
    ];
    useChatStore.getState().setStreamSources(sources);

    expect(useChatStore.getState().streamingSources).toEqual(sources);
  });
});
