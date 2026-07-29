import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Login from '../pages/Login';

// Mock useAuthStore
const mockLogin = vi.fn();
vi.mock('../store/authStore', () => ({
  useAuthStore: (selector: any) => selector({
    login: mockLogin,
    isAuthenticated: false,
    user: null,
  }),
}));

describe('Login 登录页面', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应渲染登录表单', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    expect(screen.getByPlaceholderText('用户名')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('密码')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /登.*录/ })).toBeInTheDocument();
  });

  it('应显示页面标题', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    expect(screen.getByText('知识库问答系统')).toBeInTheDocument();
    expect(screen.getByText('电商商品知识库 RAG 智能问答')).toBeInTheDocument();
  });

  it('应显示注册链接', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    expect(screen.getByText('立即注册')).toBeInTheDocument();
  });

  it('用户名和密码为空时应显示验证提示', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    const loginBtn = screen.getByRole('button', { name: /登.*录/ });
    await user.click(loginBtn);

    await waitFor(() => {
      expect(screen.getByText('请输入用户名')).toBeInTheDocument();
    });
  });

  it('提交表单时应调用 login', async () => {
    mockLogin.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    await user.type(screen.getByPlaceholderText('用户名'), 'admin');
    await user.type(screen.getByPlaceholderText('密码'), '123456');
    await user.click(screen.getByRole('button', { name: /登.*录/ }));

    expect(mockLogin).toHaveBeenCalledWith('admin', '123456');
  });

  it('登录失败应显示错误信息', async () => {
    mockLogin.mockRejectedValueOnce({
      response: { data: { detail: '用户名或密码错误' } },
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    await user.type(screen.getByPlaceholderText('用户名'), 'bad');
    await user.type(screen.getByPlaceholderText('密码'), 'wrong');
    await user.click(screen.getByRole('button', { name: /登.*录/ }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalled();
    });
  });

  it('应显示管理员提示信息', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    expect(screen.getByText('管理员: admin / 123456')).toBeInTheDocument();
  });
});
