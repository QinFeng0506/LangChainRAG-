/** 聊天状态管理 (Zustand) */
import { create } from 'zustand';
import type { SessionInfo, MessageInfo, SourceInfo } from '../types';

interface ChatState {
  sessions: SessionInfo[];
  currentSessionId: string | null;
  messages: MessageInfo[];
  loading: boolean;
  streaming: boolean;
  streamingContent: string;
  streamingSources: SourceInfo[];

  setSessions: (sessions: SessionInfo[]) => void;
  setCurrentSession: (id: string | null) => void;
  setMessages: (messages: MessageInfo[]) => void;
  addMessage: (msg: MessageInfo) => void;
  setStreaming: (v: boolean) => void;
  appendStreamChunk: (chunk: string) => void;
  setStreamSources: (sources: SourceInfo[]) => void;
  finishStreaming: (content: string, sources: SourceInfo[]) => void;
  clearStreaming: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  loading: false,
  streaming: false,
  streamingContent: '',
  streamingSources: [],

  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (id) => set({ currentSessionId: id }),
  setMessages: (messages) => set({ messages }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  setStreaming: (v) => set({ streaming: v, streamingContent: '', streamingSources: [] }),
  appendStreamChunk: (chunk) => set((s) => ({ streamingContent: s.streamingContent + chunk })),
  setStreamSources: (sources) => set({ streamingSources: sources }),
  finishStreaming: (content, sources) => set((s) => ({
    messages: [...s.messages, {
      id: `temp_${Date.now()}`,
      role: 'assistant',
      content,
      sources,
      created_at: new Date().toISOString(),
    }],
    streaming: false,
    streamingContent: '',
  })),
  clearStreaming: () => set({ streaming: false, streamingContent: '', streamingSources: [] }),
}));
