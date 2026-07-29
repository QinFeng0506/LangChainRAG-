import { Avatar, Typography, Tag, theme } from 'antd';
import { UserOutlined, RobotOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SourceCitation from './SourceCitation';
import type { MessageInfo, SourceInfo } from '../types';

const { Text } = Typography;

interface ChatMessageProps {
  message: MessageInfo;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const { token: t } = theme.useToken();

  return (
    <div
      style={{
        display: 'flex',
        gap: 12,
        padding: '16px 24px',
        background: isUser ? t.colorFillAlter : t.colorBgContainer,
        borderBottom: `1px solid ${t.colorBorderSecondary}`,
      }}
    >
      <Avatar
        icon={isUser ? <UserOutlined /> : <RobotOutlined />}
        style={{
          backgroundColor: isUser ? t.colorPrimary : t.colorSuccess,
          flexShrink: 0,
        }}
      />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ marginBottom: 4 }}>
          <Text strong style={{ color: t.colorText }}>{isUser ? '你' : 'AI 助手'}</Text>
          {!isUser && message.sources && message.sources.length > 0 && (
            <Tag color="green" style={{ marginLeft: 8, fontSize: 11 }}>
              基于 {message.sources.length} 条知识库内容
            </Tag>
          )}
        </div>

        <div className="message-content" style={{ color: t.colorText }}>
          {isUser ? (
            <Text style={{ color: t.colorText }}>{message.content}</Text>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {!isUser && message.sources && (
          <SourceCitation sources={message.sources as SourceInfo[]} />
        )}
      </div>
    </div>
  );
}
