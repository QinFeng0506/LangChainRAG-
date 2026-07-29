/** 主题状态管理 (Zustand) — 暗色模式切换。 */
import { create } from 'zustand';
import { useEffect } from 'react';

interface ThemeState {
  isDark: boolean;
  toggleTheme: () => void;
}

const useThemeStore = create<ThemeState>((set) => ({
  isDark: localStorage.getItem('theme') === 'dark',
  toggleTheme: () => set((s) => {
    const next = !s.isDark;
    localStorage.setItem('theme', next ? 'dark' : 'light');
    return { isDark: next };
  }),
}));

// 导出 Provider 用于 React 树
function ThemeProvider({ children }: { children: React.ReactNode }) {
  return children;
}

export { useThemeStore, ThemeProvider };
