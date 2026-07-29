/** 认证相关 API 请求。 */
import client from './client';
import type { LoginRequest, RegisterRequest, TokenResponse, UserInfo } from '../types';

export async function login(req: LoginRequest): Promise<TokenResponse> {
  const { data } = await client.post('/auth/login', req);
  return data;
}

export async function register(req: RegisterRequest): Promise<TokenResponse> {
  const { data } = await client.post('/auth/register', req);
  return data;
}

export async function refreshToken(refreshToken: string): Promise<TokenResponse> {
  const { data } = await client.post('/auth/refresh', { refresh_token: refreshToken });
  return data;
}

export async function getMe(): Promise<UserInfo> {
  const { data } = await client.get('/auth/me');
  return data;
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await client.put('/user/password', { old_password: oldPassword, new_password: newPassword });
}
