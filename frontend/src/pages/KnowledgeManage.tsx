import { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Button, Upload, Tag, Space, Popconfirm, message,
  Typography, Row, Col, Statistic, Tabs,
} from 'antd';
import {
  UploadOutlined, DeleteOutlined, FileTextOutlined,
  FilePdfOutlined, FileExcelOutlined, FileImageOutlined,
  ReloadOutlined, InboxOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { getDocuments, uploadDocument, deleteDocument, getDocumentStatus, getKnowledgeStats } from '../api/knowledge';
import type { DocumentInfo, KnowledgeStats } from '../types';

const { Title } = Typography;
const { Dragger } = Upload;

const statusColors: Record<string, string> = {
  pending: 'default',
  parsing: 'processing',
  chunking: 'processing',
  embedding: 'processing',
  completed: 'success',
  failed: 'error',
};

const statusLabels: Record<string, string> = {
  pending: '等待处理',
  parsing: '解析中',
  chunking: '分块中',
  embedding: '向量化中',
  completed: '已完成',
  failed: '失败',
};

const fileTypeIcons: Record<string, React.ReactNode> = {
  pdf: <FilePdfOutlined style={{ color: '#f5222d' }} />,
  txt: <FileTextOutlined style={{ color: '#1677ff' }} />,
  docx: <FileTextOutlined style={{ color: '#1677ff' }} />,
  xlsx: <FileExcelOutlined style={{ color: '#52c41a' }} />,
  csv: <FileExcelOutlined style={{ color: '#52c41a' }} />,
  md: <FileTextOutlined style={{ color: '#722ed1' }} />,
  image: <FileImageOutlined style={{ color: '#fa8c16' }} />,
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function KnowledgeManage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getDocuments(page, 20);
      setDocuments(res.items);
      setTotal(res.total);

      // 自动轮询处理中的文档
      const ids = new Set(
        res.items.filter((d: DocumentInfo) =>
          ['pending', 'parsing', 'chunking', 'embedding'].includes(d.status)
        ).map((d: DocumentInfo) => d.id)
      );
      setProcessingIds(ids);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [page]);

  const fetchStats = async () => {
    try {
      const s = await getKnowledgeStats();
      setStats(s);
    } catch {
      // ignore
    }
  };

  useEffect(() => { fetchDocuments(); fetchStats(); }, [fetchDocuments]);

  // 自动轮询处理中的文档
  useEffect(() => {
    if (processingIds.size === 0) return;
    const timer = setInterval(async () => {
      const updatedIds = new Set(processingIds);
      for (const id of processingIds) {
        try {
          const status = await getDocumentStatus(id);
          if (['completed', 'failed'].includes(status.status)) {
            updatedIds.delete(id);
          }
        } catch { updatedIds.delete(id); }
      }
      if (updatedIds.size !== processingIds.size) {
        setProcessingIds(updatedIds);
        fetchDocuments();
        fetchStats();
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [processingIds, fetchDocuments]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await uploadDocument(file);
      message.success(`${file.name} 上传成功，后台处理中...`);
      fetchDocuments();
      fetchStats();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || '上传失败';
      message.error(detail);
    } finally {
      setUploading(false);
    }
    return false; // 阻止默认上传行为
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      message.success('文档已删除');
      fetchDocuments();
      fetchStats();
    } catch {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<DocumentInfo> = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (text: string, record: DocumentInfo) => (
        <Space>
          {fileTypeIcons[record.file_type] || <FileTextOutlined />}
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      key: 'file_type',
      width: 80,
      render: (t: string) => <Tag>{t.toUpperCase()}</Tag>,
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (s: number) => formatSize(s),
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (s: string) => (
        <Tag color={statusColors[s] || 'default'}>
          {statusLabels[s] || s}
        </Tag>
      ),
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (t: string) => new Date(t).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: DocumentInfo) => (
        <Popconfirm
          title="确认删除"
          description="删除后将同时清除向量数据，不可恢复"
          onConfirm={() => handleDelete(record.id)}
          okText="确认"
          cancelText="取消"
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div style={{ padding: 24, height: '100%', overflow: 'auto' }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <FileTextOutlined style={{ marginRight: 8 }} />
        知识库管理
      </Title>

      <Tabs defaultActiveKey="documents" items={[
        {
          key: 'documents',
          label: '文档管理',
          children: (
            <>
              {/* 上传区域 */}
              <Card style={{ marginBottom: 16 }}>
                <Dragger
                  accept=".pdf,.txt,.csv,.md,.docx,.xlsx,.png,.jpg,.jpeg,.webp"
                  showUploadList={false}
                  beforeUpload={handleUpload}
                  disabled={uploading}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined />
                  </p>
                  <p className="ant-upload-text">
                    {uploading ? '上传中...' : '点击或拖拽文件上传'}
                  </p>
                  <p className="ant-upload-hint">
                    支持 PDF、Word、Excel、TXT、Markdown 及图片（PNG/JPG/WebP）
                  </p>
                </Dragger>
              </Card>

              {/* 文档列表 */}
              <Card
                title="文档列表"
                extra={
                  <Button icon={<ReloadOutlined />} onClick={fetchDocuments}>
                    刷新
                  </Button>
                }
              >
                <Table
                  rowKey="id"
                  columns={columns}
                  dataSource={documents}
                  loading={loading}
                  pagination={{
                    current: page,
                    total,
                    pageSize: 20,
                    showSizeChanger: false,
                    showTotal: (t) => `共 ${t} 个文档`,
                    onChange: (p) => setPage(p),
                  }}
                  locale={{ emptyText: '暂无文档，请上传' }}
                  scroll={{ x: 900 }}
                />
              </Card>
            </>
          ),
        },
        {
          key: 'stats',
          label: '统计信息',
          children: (
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Card><Statistic title="文档总数" value={stats?.total_documents || 0} /></Card>
              </Col>
              <Col span={6}>
                <Card><Statistic title="向量分块总数" value={stats?.total_chunks || 0} /></Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="存储大小"
                    value={stats ? stats.total_size_bytes : 0}
                    formatter={(v) => formatSize(v as number)}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card><Statistic title="处理中" value={processingIds.size} /></Card>
              </Col>

              {stats && (
                <>
                  <Col span={12}>
                    <Card title="按文件类型">
                      {Object.entries(stats.documents_by_type).map(([k, v]) => (
                        <p key={k}>{k}: <strong>{v}</strong></p>
                      ))}
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="按处理状态">
                      {Object.entries(stats.documents_by_status).map(([k, v]) => (
                        <p key={k}><Tag color={statusColors[k] || 'default'}>{statusLabels[k] || k}</Tag>: <strong>{v}</strong></p>
                      ))}
                    </Card>
                  </Col>
                </>
              )}
            </Row>
          ),
        },
      ]} />
    </div>
  );
}
