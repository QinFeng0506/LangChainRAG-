/** 知识库管理 API 请求。 */
import client from './client';
import type { DocumentInfo, KnowledgeStats } from '../types';

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await client.post('/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
  return data;
}

export async function getDocuments(page = 1, pageSize = 20, status?: string) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (status) params.status = status;
  const { data } = await client.get('/knowledge/documents', { params });
  return data;
}

export async function getDocumentStatus(docId: string): Promise<DocumentInfo> {
  const { data } = await client.get(`/knowledge/documents/${docId}/status`);
  return data;
}

export async function deleteDocument(docId: string): Promise<void> {
  await client.delete(`/knowledge/documents/${docId}`);
}

export async function getKnowledgeStats(): Promise<KnowledgeStats> {
  const { data } = await client.get('/knowledge/stats');
  return data;
}
