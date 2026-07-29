启动 RAG 知识库问答系统的开发模式。

## 项目启动说明

本系统由两部分组成：
- **后端**：FastAPI 服务（端口 8000），提供 REST API 和 SSE 流式响应
- **前端**：Vite + React 开发服务器（端口 5173），提供浏览器界面

## 启动流程

### 第 1 步：环境检查

检查以下目录是否存在：
- `backend/venv/` — Python 虚拟环境
- `backend/.env` — 环境变量配置（含百炼 API Key）
- `frontend/node_modules/` — 前端依赖

如果虚拟环境不存在：
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

如果前端依赖不存在：
```bash
cd frontend
npm install
```

### 第 2 步：启动后端

打开一个新终端（Git Bash）：
```bash
cd backend
source venv/Scripts/activate
uvicorn app.main:app --reload --port 8000
```

验证：访问 `http://localhost:8000/docs` 应显示 Swagger API 文档页面。
验证：访问 `http://localhost:8000/api/health` 应返回 `{"status": "ok"}`。

### 第 3 步：启动前端

打开另一个终端：
```bash
cd frontend
npm run dev
```

验证：访问 `http://localhost:5173` 应显示登录页面。

### 第 4 步：启动完成

向用户报告：
- 后端地址：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`
- 前端地址：`http://localhost:5173`
- 管理员账号：`admin / 12345678`

## 常见问题

### 端口被占用
```bash
# Windows — 查找并关闭占用端口的进程
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Python 版本过旧
项目需要 Python ≥ 3.10。检查版本：`python --version`

### 百炼 API Key 未配置
检查 `backend/.env` 文件中的 `DASHSCOPE_API_KEY` 是否已设置。

### 前端请求后端报 CORS 错误
确认后端已启动在 8000 端口，前端 Vite 代理配置正确。
