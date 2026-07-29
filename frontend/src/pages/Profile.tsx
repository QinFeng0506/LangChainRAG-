import { useState } from 'react';
import { Card, Form, Input, Button, Typography, Divider, message } from 'antd';
import { UserOutlined, LockOutlined, KeyOutlined } from '@ant-design/icons';
import { useAuthStore } from '../store/authStore';
import { changePassword } from '../api/auth';

const { Title } = Typography;

export default function Profile() {
  const [loading, setLoading] = useState(false);
  const user = useAuthStore((s) => s.user);

  const onChangePassword = async (values: { oldPassword: string; newPassword: string }) => {
    setLoading(true);
    try {
      await changePassword(values.oldPassword, values.newPassword);
      message.success('密码修改成功');
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      const detail = err?.response?.data?.detail || '密码修改失败';
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 40, maxWidth: 600, margin: '0 auto' }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <UserOutlined style={{ marginRight: 8 }} />
        个人中心
      </Title>

      <Card style={{ marginBottom: 24 }}>
        <p><strong>用户名：</strong>{user?.username}</p>
        <p><strong>角色：</strong>{user?.role === 'admin' ? '管理员' : '普通用户'}</p>
      </Card>

      <Card title={<span><KeyOutlined /> 修改密码</span>}>
        <Form layout="vertical" onFinish={onChangePassword}>
          <Form.Item
            name="oldPassword"
            label="旧密码"
            rules={[{ required: true, message: '请输入旧密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="输入旧密码" />
          </Form.Item>

          <Form.Item
            name="newPassword"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少 6 个字符' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="输入新密码" />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label="确认新密码"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="确认新密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
