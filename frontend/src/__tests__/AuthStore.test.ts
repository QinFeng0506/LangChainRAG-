import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  getMe: vi.fn(),
  changePassword: vi.fn(),
}));

describe('AuthStore 认证状态管理', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    vi.resetModules();
  });

  it('初始状态应未认证', async () => {
    const { useAuthStore } = await import('../store/authStore');
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });

  it('login 成功后应设置认证状态', async () => {
    const mockLogin = (await import('../api/auth')).login as any;
    const mockGetMe = (await import('../api/auth')).getMe as any;
    mockLogin.mockResolvedValueOnce({
      access_token: 'at', refresh_token: 'rt', username: 'admin', role: 'admin',
    });
    mockGetMe.mockResolvedValueOnce({
      id: '1', username: 'admin', role: 'admin', is_active: true,
    });

    const { useAuthStore } = await import('../store/authStore');
    await useAuthStore.getState().login('admin', '12345678');

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.username).toBe('admin');
    expect(state.user?.role).toBe('admin');
    expect(sessionStorage.getItem('access_token')).toBe('at');
    expect(sessionStorage.getItem('refresh_token')).toBe('rt');
  });

  it('register 成功后应设置认证状态', async () => {
    const mockRegister = (await import('../api/auth')).register as any;
    const mockGetMe = (await import('../api/auth')).getMe as any;
    mockRegister.mockResolvedValueOnce({
      access_token: 'at2', refresh_token: 'rt2', username: 'new', role: 'user',
    });
    mockGetMe.mockResolvedValueOnce({
      id: '2', username: 'new', role: 'user', is_active: true,
    });

    const { useAuthStore } = await import('../store/authStore');
    await useAuthStore.getState().register('new', 'pass123');

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.username).toBe('new');
  });

  it('logout 应清除所有状态', async () => {
    const mockLogin = (await import('../api/auth')).login as any;
    const mockGetMe = (await import('../api/auth')).getMe as any;
    mockLogin.mockResolvedValueOnce({
      access_token: 'tok', refresh_token: 'ref', username: 'test', role: 'user',
    });
    mockGetMe.mockResolvedValueOnce({
      id: '1', username: 'test', role: 'user', is_active: true,
    });

    const { useAuthStore } = await import('../store/authStore');
    await useAuthStore.getState().login('test', 'pass');

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
    expect(sessionStorage.getItem('access_token')).toBeNull();
  });

  it('initialize 有效 token 应恢复登录状态', async () => {
    const mockGetMe = (await import('../api/auth')).getMe as any;
    mockGetMe.mockResolvedValueOnce({
      id: '99', username: 'cached', role: 'user', is_active: true,
    });

    // 模拟有旧 token
    sessionStorage.setItem('access_token', 'valid_token');
    sessionStorage.setItem('refresh_token', 'valid_refresh');

    const { useAuthStore } = await import('../store/authStore');
    await useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.initialized).toBe(true);
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.username).toBe('cached');
  });

  it('initialize 过期 token 应清除并跳转登录', async () => {
    const mockGetMe = (await import('../api/auth')).getMe as any;
    mockGetMe.mockRejectedValueOnce(new Error('Token expired'));

    sessionStorage.setItem('access_token', 'expired');
    sessionStorage.setItem('refresh_token', 'expired');

    const { useAuthStore } = await import('../store/authStore');
    await useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.initialized).toBe(true);
    expect(state.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem('access_token')).toBeNull();
  });

  it('initialize 无 token 应保持未认证', async () => {
    const { useAuthStore } = await import('../store/authStore');
    await useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.initialized).toBe(true);
    expect(state.isAuthenticated).toBe(false);
  });

  it('login 失败应抛出错误', async () => {
    const mockLogin = (await import('../api/auth')).login as any;
    mockLogin.mockRejectedValueOnce({ response: { data: { detail: '密码错误' } } });

    const { useAuthStore } = await import('../store/authStore');

    await expect(
      useAuthStore.getState().login('admin', 'wrong')
    ).rejects.toEqual({ response: { data: { detail: '密码错误' } } });

    // 登录失败不应设置认证状态
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
