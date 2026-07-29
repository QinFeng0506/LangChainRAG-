# RAG 知识库问答系统 — 项目开发指南

## 产品概述

基于 LangChain 框架开发的 **RAG（检索增强生成）企业级知识库问答系统**，面向电商平台商品知识库场景。

- **定位**：浏览器端知识库管理与智能问答
- **目标用户**：企业客服、运营人员（管理员）+ 普通用户
- **核心价值**：引用知识库内容提供可溯源的智能回答
- **多模态**：支持商品图片描述检索

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | **React 18 + TypeScript** | 组件化开发 |
| UI 组件库 | **Ant Design 5** | 中文友好的企业级 UI |
| 状态管理 | **Zustand** | 轻量级状态管理 |
| 前端构建 | **Vite 5** | 快速冷启动 + HMR |
| 后端框架 | **FastAPI** (Python 3.11+) | 异步高性能，自动 OpenAPI 文档 |
| LLM 框架 | **LangChain + LangGraph** | RAG 流程编排 |
| LLM 模型 | **阿里云百炼 DeepSeek-V3** | 中文能力强，按量付费 |
| Embedding | **阿里云百炼 text-embedding-v3** | 中文语义向量化 |
| 多模态 VL | **阿里云百炼 Qwen-VL** | 商品图片描述生成 |
| 重排序 | **阿里云百炼 gte-rerank** | Cross-Encoder 精排 |
| 向量数据库 | **ChromaDB**（嵌入式模式） | pip install 即用 |
| 关系数据库 | **SQLite**（aiosqlite 异步驱动） | 零安装，文件即数据库 |
| 缓存 | **diskcache** | 基于 SQLite，pip install 即用 |
| 文件存储 | 本地文件系统 | `/data/uploads/` |
| 认证 | **JWT** (python-jose + bcrypt) | 无状态认证 |

---

## 项目结构

```
langchain-rag-system/
├── CLAUDE.md                         # 项目开发指南（本文件）
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                   # FastAPI 入口 + 生命周期
│   │   ├── config.py                 # 配置管理 (pydantic-settings)
│   │   ├── database.py               # SQLite 异步引擎 + 建表
│   │   ├── dependencies.py           # 依赖注入 (get_db, get_current_user)
│   │   ├── api/                      # 路由
│   │   │   ├── auth.py               # 认证 API
│   │   │   ├── chat.py               # 聊天/问答 API（SSE 流式）
│   │   │   ├── knowledge.py          # 知识库管理 API（仅管理员）
│   │   │   └── user.py               # 用户信息 API
│   │   ├── services/                 # 业务逻辑
│   │   │   ├── auth_service.py       # 认证服务
│   │   │   ├── knowledge_service.py  # 知识库管理服务
│   │   │   └── chat_service.py       # 聊天服务
│   │   ├── rag/                      # RAG 引擎核心
│   │   │   ├── graph.py              # LangGraph RAG 流程编排
│   │   │   ├── retriever.py          # 混合检索（语义+BM25）
│   │   │   ├── vector_store.py       # ChromaDB 封装
│   │   │   ├── splitter.py           # 文档分块
│   │   │   ├── embedding.py          # 百炼 Embedding API
│   │   │   ├── multimodal.py         # 百炼 Qwen-VL 图片描述
│   │   │   └── llm_client.py         # 百炼 LLM API 客户端
│   │   └── utils/
│   │       ├── cache.py              # diskcache 封装
│   │       └── file_storage.py       # 本地文件存储
│   └── tests/                        # 后端测试（pytest）
├── frontend/
│   ├── src/
│   │   ├── App.tsx                   # 路由 + 初始化
│   │   ├── api/                      # API 请求封装
│   │   │   ├── client.ts             # Axios 实例 + JWT 拦截器
│   │   │   ├── auth.ts               # 认证 API
│   │   │   ├── chat.ts               # 聊天 API（SSE 流式）
│   │   │   └── knowledge.ts          # 知识库 API
│   │   ├── pages/
│   │   │   ├── Login.tsx             # 登录页
│   │   │   ├── Register.tsx          # 注册页
│   │   │   ├── Chat.tsx              # 问答主页面（核心）
│   │   │   ├── KnowledgeManage.tsx   # 知识库管理（仅管理员）
│   │   │   └── Profile.tsx           # 个人中心
│   │   ├── components/
│   │   │   ├── ChatMessage.tsx       # 消息气泡（Markdown + 引用溯源）
│   │   │   ├── SourceCitation.tsx    # 引用片段展开组件
│   │   │   └── Layout.tsx            # 页面布局（侧边栏 + 顶栏）
│   │   ├── store/
│   │   │   ├── authStore.ts          # 认证状态（Zustand）
│   │   │   ├── chatStore.ts          # 聊天状态（Zustand）
│   │   │   └── themeStore.ts         # 主题状态（暗色模式）
│   │   └── __tests__/                # 前端测试（Vitest）
│   └── vite.config.ts
└── data/                             # 运行时数据（gitignore）
    ├── chroma/                       # ChromaDB 持久化
    ├── uploads/                      # 上传文件
    ├── cache/                        # diskcache
    └── app.db                        # SQLite 数据库
```

---

## RAG 流程

```
用户问题
    │
    ▼
┌─────────────────┐
│ 1. 问题改写      │ ← LLM 将口语化问题改写为检索友好形式
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. 混合检索      │ ← 语义检索(ChromaDB) + 关键词检索(BM25)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. 重排序        │ ← 百炼 gte-rerank Cross-Encoder 精排
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. 上下文压缩    │ ← 对过长文档片段做压缩
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. LLM 生成      │ ← 带引用模板的 Prompt，标注 [1][2]...
└────────┬────────┘
    返回: { answer, sources }
```

---

## 启动方式

### 首次启动

```bash
# 1. 后端
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入百炼 API Key
uvicorn app.main:app --reload --port 8000

# 2. 前端（新终端）
cd frontend
npm install
npm run dev             # http://localhost:5173
```

### 后续启动

```bash
# 终端 1 — 后端
cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000

# 终端 2 — 前端
cd frontend && npm run dev
```

---

## API 文档

启动后端后访问 `http://localhost:8000/docs` 查看 Swagger UI。

### 核心接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/refresh` | 刷新 Token |
| GET  | `/api/auth/me` | 获取当前用户信息 |
| POST | `/api/chat/query` | 发送问题（SSE 流式） |
| GET  | `/api/chat/sessions` | 会话列表 |
| POST | `/api/chat/sessions` | 创建会话 |
| DELETE | `/api/chat/sessions/{id}` | 删除会话 |
| POST | `/api/knowledge/upload` | 上传文档（admin） |
| GET  | `/api/knowledge/documents` | 文档列表（admin） |
| DELETE | `/api/knowledge/documents/{id}` | 删除文档（admin） |

---

## 预设账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `12345678` |
| 普通用户 | 自行注册 | — |

---

## 代码规范

- 🇨🇳 所有注释、文档、UI 文案使用中文
- Python：函数用 docstring，类型注解用 Pydantic
- TypeScript：strict 模式，公共函数必须有返回类型
- 金额统一用"元"，保留两位小数
- 日期格式：ISO 8601
- 数据库操作集中在 `backend/app/database.py`
- RAG 组件各自独立在 `backend/app/rag/` 目录
- 前端状态管理用 Zustand，不散落在组件中
- 暗色模式颜色全部用 Ant Design `theme.useToken()`

---

## 开发协作规则

1. **🎯 先展示再执行**：修改或创建文件前，先向用户说明打算做什么
2. **💬 解释要通俗**：用生活比喻解释技术概念
3. **📝 逐步推进**：大型功能拆分为小步骤，每步确认无误再继续
4. **🇨🇳 中文优先**：所有产出（注释、文档、报告）均使用中文
5. **🔒 提交走质量门禁**：`git commit` 必须通过 gitcommit-agent，不要用 `--no-verify` 绕过

---

## 版本记录

| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-29 | 完整项目搭建、所有功能实现、113 项测试通过 | Claude |
