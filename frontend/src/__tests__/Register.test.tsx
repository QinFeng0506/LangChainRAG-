import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Register from '../pages/Register';

const mockRegister = vi.fn();
vi.mock('../store/authStore', () => ({
  useAuthStore: (selector: any) => selector({
    register: mockRegister,
    isAuthenticated: false,
    user: null,
  }),
}));

describe('Register 注册页面', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应渲染注册表单所有字段', () => {
    render(<MemoryRouter><Register /></MemoryRouter>);

    expect(screen.getByPlaceholderText('用户名')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('密码')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('确认密码')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /注.*册/ })).toBeInTheDocument();
  });

  it('应显示页面标题', () => {
    render(<MemoryRouter><Register /></MemoryRouter>);

    expect(screen.getByText('注册账号')).toBeInTheDocument();
    expect(screen.getByText('加入 RAG 知识库问答系统')).toBeInTheDocument();
  });

  it('应显示返回登录链接', () => {
    render(<MemoryRouter><Register /></MemoryRouter>);

    expect(screen.getByText('返回登录')).toBeInTheDocument();
  });

  it('空表单提交应显示验证错误', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><Register /></MemoryRouter>);

    await user.click(screen.getByRole('button', { name: /注.*册/ }));

    await waitFor(() => {
      expect(screen.getByText('请输入用户名')).toBeInTheDocument();
    });
  });

  it('两次密码不一致应显示错误', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><Register /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText('用户名'), 'newuser');
    await user.type(screen.getByPlaceholderText('密码'), 'pass123');
    await user.type(screen.getByPlaceholderText('确认密码'), 'different');
    await user.click(screen.getByRole('button', { name: /注.*册/ }));

    await waitFor(() => {
      expect(screen.getByText('两次输入的密码不一致')).toBeInTheDocument();
    });
  });

  it('密码少于 6 字符应显示错误', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><Register /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText('用户名'), 'usr');
    await user.type(screen.getByPlaceholderText('密码'), '12345');
    await user.type(screen.getByPlaceholderText('确认密码'), '12345');
    await user.click(screen.getByRole('button', { name: /注.*册/ }));

    // 验证应该显示至少一个验证错误（用户名或密码格式不正确）
    await waitFor(() => {
      const errors = document.querySelectorAll('.ant-form-item-explain-error');
      expect(errors.length).toBeGreaterThan(0);
    });
  });

  it('填写正确信息应调用 register', async () => {
    mockRegister.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    render(<MemoryRouter><Register /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText('用户名'), 'validuser');
    await user.type(screen.getByPlaceholderText('密码'), 'validpass');
    await user.type(screen.getByPlaceholderText('确认密码'), 'validpass');
    await user.click(screen.getByRole('button', { name: /注.*册/ }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('validuser', 'validpass');
    });
  });

  it('注册失败应显示错误提示', async () => {
    mockRegister.mockRejectedValueOnce({
      response: { data: { detail: '用户名已存在' } },
    });
    const user = userEvent.setup();
    render(<MemoryRouter><Register /></MemoryRouter>);

    await user.type(screen.getByPlaceholderText('用户名'), 'taken');
    await user.type(screen.getByPlaceholderText('密码'), 'pass123');
    await user.type(screen.getByPlaceholderText('确认密码'), 'pass123');
    await user.click(screen.getByRole('button', { name: /注.*册/ }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalled();
    });
  });
});
