import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, message, Space } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuthStore } from '../store/authStore';
import { useChatStore } from '../store/chatStore';

const { Title, Text } = Typography;

export default function Login() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const loginAction = useAuthStore((s) => s.login);

  // 进入登录页时清空旧聊天数据
  useEffect(() => {
    useChatStore.getState().setSessions([]);
    useChatStore.getState().setCurrentSession(null);
    useChatStore.getState().setMessages([]);
  }, []);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await loginAction(values.username, values.password);
      message.success('登录成功');
      navigate('/chat');
    } catch (err: any) {
      console.error('Login error:', err);
      const detail = err?.response?.data?.detail || err?.message || '登录失败，请确认后端服务已启动';
      message.error(typeof detail === 'string' ? detail : '登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <Card style={{ width: 400, boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={3} style={{ marginBottom: 4 }}>知识库问答系统</Title>
          <Text type="secondary">电商商品知识库 RAG 智能问答</Text>
        </div>

        <Form name="login" onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>

          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center' }}>
          <Space>
            <Text type="secondary">还没有账号？</Text>
            <Link to="/register">立即注册</Link>
          </Space>
        </div>

        <div style={{ textAlign: 'center', marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            管理员: admin / 123456
          </Text>
        </div>
      </Card>
    </div>
  );
}
