import { Collapse, Tag, Image, Typography, theme } from 'antd';
import { LinkOutlined, FileImageOutlined } from '@ant-design/icons';
import type { SourceInfo } from '../types';

const { Text, Paragraph } = Typography;

export default function SourceCitation({ sources }: { sources: SourceInfo[] }) {
  if (!sources || sources.length === 0) return null;
  const { token: t } = theme.useToken();

  return (
    <div style={{ marginTop: 12 }}>
      <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
        <LinkOutlined /> 引用来源 ({sources.length})
      </Text>
      <Collapse
        size="small"
        ghost
        items={sources.map((source, idx) => ({
          key: String(idx),
          label: (
            <span style={{ color: t.colorText }}>
              <Tag color="blue" style={{ marginRight: 8 }}>[{idx + 1}]</Tag>
              {source.doc_name}
              <Tag style={{ marginLeft: 8 }}>
                相关度: {(source.score * 100).toFixed(0)}%
              </Tag>
            </span>
          ),
          children: (
            <div>
              {source.image_path && (
                <div style={{ marginBottom: 8 }}>
                  <FileImageOutlined /> 商品图片：
                  <Image
                    src={source.image_path}
                    alt={source.doc_name}
                    width={200}
                    style={{ maxHeight: 200, objectFit: 'contain' }}
                    fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
                  />
                </div>
              )}
              <Paragraph
                ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
                style={{ margin: 0, color: t.colorTextSecondary, fontSize: 13 }}
              >
                {source.chunk_text}
              </Paragraph>
            </div>
          ),
        }))}
      />
    </div>
  );
}
