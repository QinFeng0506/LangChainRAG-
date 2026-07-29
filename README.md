<p align="center">
  <h1 align="center">🧠 LangChain RAG 知识库问答系统</h1>
  <p align="center">基于 LangChain + LangGraph 的企业级电商知识库智能问答平台</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react" alt="React">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain" alt="LangChain">
  <img src="https://img.shields.io/badge/Ant_Design-5-0170FE?logo=antdesign" alt="Ant Design">
  <img src="https://img.shields.io/badge/测试-114/114_通过-success" alt="Tests">
</p>

---

## 📖 项目简介

本项目是**毕业设计作品**，面向电商商品知识库场景，实现了一个完整的 **RAG（检索增强生成）** 企业级问答系统。

用户通过浏览器界面上传商品文档（文本/图片），系统自动解析、向量化入库，AI 回答问题时引用知识库内容，提供**可溯源的答案**。

> 💡 **通俗理解**：把公司所有产品资料"喂"给 AI，然后问它"哪个手机续航最久？"——AI 不仅回答你，还告诉你答案来自哪份文档。

---

## ✨ 核心功能

| 模块 | 功能 |
|------|------|
| 🔐 **用户认证** | 注册、登录、JWT 双 Token（access 30min + refresh 7天）、角色权限控制 |
| 📚 **知识库管理** | 文档上传（PDF/Word/TXT/CSV/Markdown/Excel）、图片上传自动描述、异步处理、状态追踪 |
| 💬 **智能问答** | RAG 全流程（问题改写→混合检索→精排→上下文压缩→LLM生成→引用溯源）、SSE 流式输出 |
| 🖼️ **多模态支持** | 商品图片经 Qwen-VL 生成文字描述后入库，图片内容可被文本问题检索 |
| 👥 **多用户多会话** | 多用户隔离、会话历史持久化、多轮对话上下文 |
| 🌙 **暗色模式** | 明亮/暗色主题切换 |
| 🛡️ **质量门禁** | 每次提交前自动跑 114 项单元测试 + 安全审计，通过后才允许提交 |

---

## 🏗️ 技术架构

```
┌──────────────────────────────────────────────┐
│              浏览器 (React 18 + Ant Design 5) │
│   登录注册 │ 知识库问答 │ 会话管理 │ 知识库管理 │
└──────────────────┬───────────────────────────┘
                   │ HTTP/SSE (JWT)
┌──────────────────▼───────────────────────────┐
│               FastAPI 后端                    │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ Auth    │  │ Chat API │  │ Knowledge API│ │
│  │ JWT     │  │ SSE 流式 │  │ 文档/图片处理│ │
│  └─────────┘  └──────────┘  └─────────────┘ │
│  ┌──────────────────────────────────────────┐│
│  │     RAG Engine (LangChain + LangGraph)   ││
│  │  改写→混合检索→重排序→上下文压缩→LLM生成  ││
│  └──────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────┐│
│  │  阿里云百炼 DashScope                    ││
│  │  LLM: DeepSeek-V3/Qwen3                  ││
│  │  Embedding: text-embedding-v3            ││
│  │  VL: Qwen-VL | Rerank: gte-rerank        ││
│  └──────────────────────────────────────────┘│
└──────┬──────────────┬──────────────┬─────────┘
       │              │              │
┌──────▼──┐  ┌────────▼──┐  ┌───────▼──┐
│ SQLite  │  │ ChromaDB  │  │ 本地文件  │
│用户/会话│  │ 向量存储   │  │uploads/   │
└─────────┘  └───────────┘  └──────────┘
```

### 技术栈一览

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + TypeScript + Vite 5 | SPA 单页应用 |
| **UI** | Ant Design 5 + Tailwind CSS 3 | 企业级 UI，暗色模式 |
| **状态管理** | Zustand | 轻量级状态管理 |
| **后端** | FastAPI (Python 3.11+) | 异步高性能，自动 API 文档 |
| **LLM 框架** | LangChain 0.3 + LangGraph 0.2 | RAG 流程编排 |
| **LLM 模型** | 阿里云百炼 DeepSeek-V3 / Qwen3 | 中文能力强 |
| **Embedding** | 阿里云百炼 text-embedding-v3 | 中文语义向量化 |
| **多模态** | 阿里云百炼 Qwen-VL | 商品图片描述生成 |
| **重排序** | 阿里云百炼 gte-rerank | Cross-Encoder 精排 |
| **向量库** | ChromaDB（嵌入式模式） | 零配置，持久化 |
| **数据库** | SQLite (aiosqlite) | 零配置，WAL 模式 |
| **缓存** | diskcache | 热门问题缓存 |
| **认证** | JWT (python-jose + bcrypt) | 双 Token 机制 |
| **测试** | pytest + Vitest | 114 项测试全覆盖 |

---

## 🚀 快速开始

### 环境要求

- **Python** ≥ 3.10（推荐 3.11）
- **Node.js** ≥ 18
- **阿里云百炼 API Key** → [免费注册](https://dashscope.aliyun.com)

### 1. 克隆项目

```bash
git clone git@gitee.com:qin-qyf/vibecoding_langchain.git
cd vibecoding_langchain
```

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入你的百炼 API Key：
# DASHSCOPE_API_KEY=sk-your-key-here
```

### 3. 安装依赖

```bash
# 后端
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 前端（新终端）
cd frontend
npm install
```

### 4. 启动

```bash
# 方式一：分别启动
# 终端 1 — 后端
cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000

# 终端 2 — 前端
cd frontend && npm run dev

# 方式二：Windows 一键启动
start.bat
```

### 5. 访问

| 地址 | 说明 |
|------|------|
| [http://localhost:5173](http://localhost:5173) | 前端页面 |
| [http://localhost:8000/docs](http://localhost:8000/docs) | API 文档（Swagger） |
| [http://localhost:8000/api/health](http://localhost:8000/api/health) | 健康检查 |

### 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | 通过 .env 的 `ADMIN_PASSWORD` 设置 |

> ⚠️ 首次启动时如果未配置密码，系统会自动生成并打印在控制台。

---

## 📁 项目结构

```
├── backend/                        # FastAPI 后端
│   ├── app/
│   │   ├── main.py                 # 入口 + 生命周期
│   │   ├── config.py               # 配置（pydantic-settings）
│   │   ├── database.py             # SQLite 异步引擎
│   │   ├── dependencies.py         # JWT 依赖注入
│   │   ├── api/                    # 路由层
│   │   │   ├── auth.py             # 认证 API
│   │   │   ├── chat.py             # 问答 API（SSE 流式）
│   │   │   ├── knowledge.py        # 知识库 API（管理员）
│   │   │   └── user.py             # 用户 API
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── auth_service.py     # 密码哈希 / JWT
│   │   │   ├── chat_service.py     # RAG 问答
│   │   │   └── knowledge_service.py# 文档处理
│   │   ├── rag/                    # RAG 引擎核心
│   │   │   ├── graph.py            # LangGraph 流程编排
│   │   │   ├── retriever.py        # 混合检索（语义+BM25）
│   │   │   ├── vector_store.py     # ChromaDB 封装
│   │   │   ├── splitter.py         # 文档分块
│   │   │   ├── embedding.py        # Embedding API
│   │   │   ├── reranker.py         # gte-rerank 精排
│   │   │   ├── multimodal.py       # Qwen-VL 图片理解
│   │   │   └── llm_client.py       # LLM 客户端
│   │   └── utils/
│   │       ├── cache.py            # diskcache 缓存
│   │       └── file_storage.py     # 文件存储
│   └── tests/                      # 后端测试（pytest）
│       ├── test_auth.py            # 认证测试（23 项）
│       ├── test_chat.py            # 聊天测试（18 项）
│       ├── test_knowledge.py       # 知识库测试（17 项）
│       └── test_rag_utils.py       # RAG 工具测试（24 项）
│
├── frontend/                       # React 前端
│   └── src/
│       ├── pages/
│       │   ├── Chat.tsx            # 问答页面（核心）
│       │   ├── KnowledgeManage.tsx # 知识库管理
│       │   ├── Login.tsx           # 登录
│       │   └── Register.tsx        # 注册
│       ├── components/
│       │   ├── ChatMessage.tsx     # 消息气泡（Markdown + 引用）
│       │   ├── SourceCitation.tsx  # 引用溯源展开
│       │   └── Layout.tsx          # 页面布局
│       ├── store/                  # 状态管理（Zustand）
│       ├── api/                    # API 请求层
│       └── __tests__/              # 前端测试（Vitest）
│
├── knowledge-base/                 # 示例知识库（8 文档 + 6 图片）
└── .claude/                        # Claude Code 配置
    ├── agents/                     # 3 个 Agent
    │   ├── tester.md               # 测试专家
    │   ├── quality-engineer.md     # 质量工程师
    │   └── gitcommit-agent.md      # 提交调度器
    ├── commands/                   # 5 个命令
    └── hooks/                      # pre-commit 钩子
```

---

## 🧪 测试

```bash
# 后端测试（82 项）
cd backend && venv\Scripts\pytest tests/ -v

# 前端测试（32 项）
cd frontend && npx vitest run

# 或使用技能命令
/test          # 运行全部测试 + 覆盖分析
/test 快速     # 只执行已有测试
```

---

## 🔒 每次提交自动检查

本项目配置了质量门禁——`git commit` 前必须通过：

| 检查项 | 通过标准 |
|--------|:--:|
| 后端 pytest | 82/82 通过 |
| 前端 vitest | 32/32 通过 |
| 安全审计 | ≥ 75/100 分 |

正确提交方式：直接说 **"帮我提交"**，系统自动跑完检查后存档。

---

## 📄 License

MIT — 毕业设计作品，仅供学习交流。

---

<p align="center">
  <sub>Built with ❤️ by QinFeng0506 | 2026</sub>
</p>
