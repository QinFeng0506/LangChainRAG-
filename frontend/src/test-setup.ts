/** Vitest + jsdom 环境初始化 —— 补丁 Ant Design 所需的浏览器 API。 */
import '@testing-library/jest-dom/vitest';

// jsdom 补丁：window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// jsdom 补丁：ResizeObserver
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverMock as any;

// 抑制 jsdom 无害的 getComputedStyle 伪元素警告
const originalError = console.error;
console.error = (...args: any[]) => {
  if (
    typeof args[0] === 'string' &&
    (args[0].includes("Not implemented: Window's getComputedStyle") ||
     args[0].includes('Not implemented: window.computedStyle'))
  ) {
    return;
  }
  originalError.call(console, ...args);
};
