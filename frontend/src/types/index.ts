// ===== 认证相关 =====
export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  username: string;
  role: string;
}

export interface UserInfo {
  id: string;
  username: string;
  role: string; // "admin" | "user"
  is_active: boolean;
}

// ===== 聊天/会话相关 =====
export interface SessionInfo {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SourceInfo {
  doc_name: string;
  chunk_text: string;
  score: number;
  image_path?: string | null;
}

export interface MessageInfo {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceInfo[] | null;
  created_at: string;
}

export interface ChatQueryRequest {
  session_id: string;
  question: string;
}

// ===== 知识库相关 =====
export interface DocumentInfo {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'parsing' | 'chunking' | 'embedding' | 'completed' | 'failed';
  chunk_count: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeStats {
  total_documents: number;
  total_chunks: number;
  total_size_bytes: number;
  documents_by_type: Record<string, number>;
  documents_by_status: Record<string, number>;
}
