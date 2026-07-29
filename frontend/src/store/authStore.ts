/** 认证状态管理 (Zustand) —— 使用 sessionStorage，关闭浏览器即清除登录。 */
import { create } from 'zustand';
import type { UserInfo } from '../types';
import { login as loginApi, register as registerApi, getMe } from '../api/auth';
import { useChatStore } from './chatStore';

// 统一使用 sessionStorage：页面刷新保持登录，关闭浏览器后需要重新登录
const storage = sessionStorage;

interface AuthState {
  user: UserInfo | null;
  isAuthenticated: boolean;
  loading: boolean;
  initialized: boolean;

  initialize: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  loading: false,
  initialized: false,

  // App 启动时调用：验证 storage 中的 token 是否有效
  initialize: async () => {
    const token = storage.getItem('access_token');
    if (!token) {
      set({ initialized: true, isAuthenticated: false, user: null });
      return;
    }
    try {
      const user = await getMe();
      set({ user, isAuthenticated: true, initialized: true });
    } catch {
      // Token 过期或无效，清除
      storage.removeItem('access_token');
      storage.removeItem('refresh_token');
      set({ user: null, isAuthenticated: false, initialized: true });
    }
  },

  login: async (username, password) => {
    set({ loading: true });
    try {
      const res = await loginApi({ username, password });
      storage.setItem('access_token', res.access_token);
      storage.setItem('refresh_token', res.refresh_token);
      const user = await getMe();
      set({ user, isAuthenticated: true });
    } finally {
      set({ loading: false });
    }
  },

  register: async (username, password) => {
    set({ loading: true });
    try {
      const res = await registerApi({ username, password });
      storage.setItem('access_token', res.access_token);
      storage.setItem('refresh_token', res.refresh_token);
      const user = await getMe();
      set({ user, isAuthenticated: true });
    } finally {
      set({ loading: false });
    }
  },

  logout: () => {
    storage.removeItem('access_token');
    storage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false });
    // 清空聊天状态，防止新用户看到旧用户的会话和消息
    const chatState = useChatStore.getState();
    chatState.setSessions([]);
    chatState.setCurrentSession(null);
    chatState.setMessages([]);
    chatState.clearStreaming();
  },
}));
