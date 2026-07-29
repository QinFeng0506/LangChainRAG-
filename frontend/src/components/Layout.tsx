import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout as AntLayout, Menu, Button, Dropdown, theme, Space } from 'antd';
import {
  MessageOutlined, DatabaseOutlined, UserOutlined,
  LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
  MoonOutlined, SunOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';

const { Header, Sider, Content } = AntLayout;

export default function Layout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { isDark, toggleTheme } = useThemeStore();
  const { token: themeToken } = theme.useToken();

  const isAdmin = user?.role === 'admin';

  const menuItems = [
    { key: '/chat', icon: <MessageOutlined />, label: '知识库问答' },
    ...(isAdmin ? [{ key: '/knowledge', icon: <DatabaseOutlined />, label: '知识库管理' }] : []),
  ];

  const selectedKey = menuItems.find((item) =>
    location.pathname.startsWith(item.key)
  )?.key || '/chat';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: '个人中心', onClick: () => navigate('/profile') },
      { type: 'divider' as const },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
    ],
  };

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        breakpoint="lg"
        onBreakpoint={(broken) => setCollapsed(broken)}
        style={{ background: themeToken.colorBgContainer }}
      >
        <div style={{
          height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center',
          borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
        }}>
          <span style={{ fontSize: collapsed ? 16 : 18, fontWeight: 700, color: themeToken.colorPrimary }}>
            {collapsed ? 'RAG' : 'RAG 知识库问答'}
          </span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>

      <AntLayout>
        <Header style={{
          background: themeToken.colorBgContainer,
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Dropdown menu={userMenu} placement="bottomRight">
            <Button type="text" icon={<UserOutlined />}>
              {user?.username}
              {isAdmin && <span style={{ color: themeToken.colorPrimary, marginLeft: 4, fontSize: 12 }}>(管理员)</span>}
            </Button>
          </Dropdown>
          <Button
            type="text"
            icon={isDark ? <SunOutlined /> : <MoonOutlined />}
            onClick={toggleTheme}
            title={isDark ? '切换明亮模式' : '切换暗色模式'}
          />
        </Header>

        <Content style={{ margin: 0, overflow: 'auto', height: 'calc(100vh - 64px)' }}>
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
