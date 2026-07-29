/** 聊天相关 API 请求。 */
import client from './client';
import type { SessionInfo, MessageInfo } from '../types';

export async function getSessions(): Promise<SessionInfo[]> {
  const { data } = await client.get('/chat/sessions');
  return data;
}

export async function createSession(title?: string): Promise<SessionInfo> {
  const { data } = await client.post('/chat/sessions', title ? { title } : {});
  return data;
}

export async function renameSession(sessionId: string, title: string): Promise<void> {
  await client.patch(`/chat/sessions/${sessionId}`, { title });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await client.delete(`/chat/sessions/${sessionId}`);
}

export async function getSessionMessages(sessionId: string): Promise<MessageInfo[]> {
  const { data } = await client.get(`/chat/sessions/${sessionId}/messages`);
  return data;
}

export function createChatStream(
  sessionId: string,
  question: string,
  onChunk: (text: string) => void,
  onSources: (sources: any[]) => void,
  onDone: () => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();

  fetch('/api/chat/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${sessionStorage.getItem('access_token')}`,
    },
    body: JSON.stringify({ session_id: sessionId, question }),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: '请求失败' }));
      onError(err.detail || '请求失败');
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError('不支持流式读取');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'chunk') {
              onChunk(data.content);
            } else if (data.type === 'sources') {
              onSources(data.sources);
            } else if (data.type === 'done') {
              onDone();
            } else if (data.type === 'error') {
              onError(data.content);
            }
          } catch {
            // parse error, skip
          }
        }
      }
    }
    onDone();
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError(err.message || '网络错误');
    }
  });

  return controller;
}
