/** Axios 实例 —— 封装 JWT 拦截器、Token 刷新、统一错误处理。 */
import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  timeout: 60000,
});

// ===== 请求拦截器：自动附加 access_token =====
client.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ===== 响应拦截器：Token 过期自动刷新 =====
let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 如果是 401 且不是刷新请求本身，尝试刷新 token
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = sessionStorage.getItem('refresh_token');

      if (!refreshToken) {
        // 没有 refresh token（比如登录页输入错误密码）：不跳转，让调用方自己处理错误提示
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // 正在刷新中，加入队列等待
        return new Promise((resolve) => {
          refreshQueue.push((newToken: string) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            resolve(client(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post('/api/auth/refresh', {
          refresh_token: refreshToken,
        });

        sessionStorage.setItem('access_token', data.access_token);
        sessionStorage.setItem('refresh_token', data.refresh_token);

        // 唤醒等待队列
        refreshQueue.forEach((cb) => cb(data.access_token));
        refreshQueue = [];

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return client(originalRequest);
      } catch (refreshError) {
        // 刷新失败，清除登录状态（React Router 会处理跳转）
        sessionStorage.clear();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default client;
