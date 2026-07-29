# 自定义技能库

## run-app

启动 RAG 知识库问答系统的开发模式。

### 启动流程

1. 先检查 `backend/venv` 和 `frontend/node_modules` 是否存在
2. 后端不存在则创建 venv 并 `pip install -r requirements.txt`
3. 前端不存在则 `npm install`
4. 两个终端分别启动后端和前端

### 启动命令

| 命令 | 说明 |
|------|------|
| `cd backend && source venv/Scripts/activate && uvicorn app.main:app --reload --port 8000` | 启动后端 |
| `cd frontend && npm run dev` | 启动前端 |

启动成功后：
- 后端地址：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`
- 前端地址：`http://localhost:5173`
- 管理员账号：`admin / 12345678`

---

## test

对项目代码进行单元测试——自动创建测试用例、执行测试、生成测试报告。

### 什么是单元测试？

> 就像工厂流水线上每颗螺丝出厂前都要过一遍卡尺，确保没有次品。
> 单元测试 = 用「测试代码」自动检查「业务代码」是否正确。

### 三种使用方式

| 命令 | 功能 |
|------|------|
| `/test` | 跑全部测试 + 分析哪些代码还没有测试覆盖 |
| `/test 给 xxx 写测试` | 为指定模块/API/组件创建测试文件 |
| `/test 跑一下` | 只执行已有测试，出报告 |

### 本项目的测试工具

| 层级 | 工具 | 作用 |
|------|------|------|
| 后端 | **pytest** + **pytest-asyncio** + **httpx** | FastAPI 异步 API 测试 |
| 前端 | **Vitest** + **@testing-library/react** + **jsdom** | React 组件测试 |

### 测试文件规范

- 后端：`backend/tests/test_*.py`（命名以 `test_` 开头）
- 前端：`frontend/src/__tests__/*.test.ts(x)`（命名以 `.test.` 结尾）

### 执行命令

| 命令 | 场景 |
|------|------|
| `cd backend && venv/Scripts/pytest tests/ -v --tb=short` | 后端全部测试 |
| `cd frontend && npx vitest run` | 前端全部测试 |

---

### 已有测试清单

| 测试文件 | 对应源码 | 用例数 | 测试类型 |
|----------|----------|:------:|:--------:|
| `test_auth.py` | `backend/app/api/auth.py` | 23 | 后端 API — 注册/登录/Token/权限/密码修改 |
| `test_chat.py` | `backend/app/api/chat.py` | 17 | 后端 API — 会话CRUD/隔离/消息历史/问答 |
| `test_knowledge.py` | `backend/app/api/knowledge.py` | 18 | 后端 API — 文档上传/列表/删除/状态/验证 |
| `test_rag_utils.py` | `backend/app/rag/* + utils/*` | 24 | 后端工具 — 分块/BM25/缓存/文件存储 |
| `AuthStore.test.ts` | `frontend/src/store/authStore.ts` | 8 | 前端 Store — 登录/注册/登出/初始化 |
| `Login.test.tsx` | `frontend/src/pages/Login.tsx` | 7 | 前端组件 — 表单渲染/提交/错误处理 |
| `Register.test.tsx` | `frontend/src/pages/Register.tsx` | 8 | 前端组件 — 表单/验证/注册流程 |
| `ChatStore.test.ts` | `frontend/src/store/chatStore.ts` | 9 | 前端 Store — 会话/消息/流式状态 |
| **合计** | | **114** | |

---

### 测试报告格式

```
══════════════════════════════════
  ✅ 通过：113 项
  ❌ 失败：0 项
  ⏱️  耗时：22.99s
  📁 测试文件：8 个
══════════════════════════════════

📁 逐文件明细
  ✅ test_auth.py         — 认证模块（注册/登录/Token/权限）        — 23 项通过
  ✅ test_chat.py         — 聊天会话（CRUD/隔离/消息历史）          — 17 项通过
  ✅ test_knowledge.py    — 知识库管理（上传/列表/删除/统计）        — 18 项通过
  ✅ test_rag_utils.py    — RAG工具（分块/BM25/缓存/文件）          — 24 项通过
  ✅ AuthStore.test.ts    — 前端认证状态管理                        — 8 项通过
  ✅ Login.test.tsx       — 登录页组件渲染与交互                    — 7 项通过
  ✅ Register.test.tsx    — 注册页组件渲染与交互                    — 8 项通过
  ✅ ChatStore.test.ts    — 聊天状态管理                            — 9 项通过

📊 结果判定
─────────────────────────────
  通过：113 项  失败：0 项
  ✅ 测试全部通过 — 允许继续提交流程
─────────────────────────────
```

### 四种测试类型速查

#### 1. 后端 API 测试（如 auth、chat、knowledge）

使用 `conftest.py` 中已有的 fixtures（`client`、`auth_headers`、`user_headers`）：

```python
class TestModuleName:
    async def test_normal_case(self, client, auth_headers):
        """正常情况应返回 200。"""
        resp = await client.get("/api/xxx", headers=auth_headers)
        assert resp.status_code == 200

    async def test_no_auth(self, client):
        """未登录应返回 401。"""
        resp = await client.get("/api/xxx")
        assert resp.status_code == 401
```

#### 2. 后端工具函数测试（如 BM25、splitter、cache）

直接 import 测试，无需 mock 数据库：

```python
def test_split_text():
    chunks = split_text("这是一个测试文档", chunk_size=500, overlap=50)
    assert len(chunks) > 0
    assert all(len(c) <= 500 for c in chunks)
```

#### 3. 前端 Store 测试（如 authStore、chatStore）

Mock API 模块，测状态变化：

```typescript
vi.mock('../api/auth', () => ({
  login: vi.fn().mockResolvedValue({ access_token: 'at', ... }),
  getMe: vi.fn().mockResolvedValue({ id: '1', username: 'admin', ... }),
}));

it('login 成功后应设置认证状态', async () => {
  await useAuthStore.getState().login('admin', '12345678');
  expect(useAuthStore.getState().isAuthenticated).toBe(true);
});
```

#### 4. 前端组件测试（如 Login、ChatMessage）

```typescript
it('应正常渲染', () => {
  render(<MemoryRouter><Login /></MemoryRouter>);
  expect(screen.getByText(/知识库问答系统/)).toBeInTheDocument();
});
```

### Mock 速查表

| 需要 Mock 的 | 写法 |
|-------------|------|
| 后端 API 请求 | 使用 conftest.py 的 `client` fixture（自动处理依赖注入） |
| 百炼 API（LLM/Embedding/VL） | `vi.mock` 或 `unittest.mock.patch` |
| 前端 API 模块 | `vi.mock('../api/auth', () => ({ login: vi.fn() }))` |
| 前端 Zustand Store | `vi.mock('../store/chatStore', () => ({ useChatStore: mockFn }))` |
| 子组件（避免级联渲染） | `vi.mock('../components/Child', () => ({ default: () => <div>Child</div> }))` |
| vi.hoisted（mock 数据变量提升） | `const { data } = vi.hoisted(() => ({ data: [...] }))` |

### 常见问题与解决

| 问题 | 原因 | 解决 |
|------|------|------|
| Ant Design 按钮文字有空格 | Antd 中文字符间插入空格（`登 录`） | 用正则 `/登.*录/` 匹配 |
| FastAPI 异步测试报错 | 同步写法在异步环境中 | 用 conftest.py 的 `client` fixture |
| `vi.mock` 变量 undefined | vi.mock 工厂自动提升 | 用 `vi.hoisted()` 包裹变量定义 |
| 数据库测试数据互相干扰 | 前一个测试的数据影响后面 | conftest.py 的 `setup_db` 自动清空表 |
| 弹窗按钮找不到 | Antd Modal 动画未完成 | `waitFor` + `timeout: 3000` |

### 测试设计原则

1. 🎯 每个 `it`/`def test_` 只测一件事
2. 🇨🇳 测试名用中文，描述"应该xxx"
3. ⚖️ 覆盖三类场景：正常 → 边界 → 异常
4. 🔌 依赖外部系统的用 mock 隔离
5. 🚫 不要让测试依赖执行顺序（每个测试独立）
6. 📐 组件测试优先测渲染和核心交互，不测样式细节

---

## comments-check

对项目源码进行三维度注释质量检查——覆盖率、准确性、小白友好度，并给出改进建议和最终评分。

### 使用方式

| 命令 | 功能 |
|------|------|
| `/comments-check` | 扫描全部源码，输出完整检查报告 |
| `/comments-check 文件路径` | 只检查指定文件 |
| `/comments-check 关键词` | 检查文件名包含关键词的文件 |
| `/comments-check 目录路径` | 检查指定目录下的所有源码 |

### 检查排除规则

检查时**跳过**：
- `backend/tests/` / `frontend/src/__tests__/` — 测试代码
- `*.d.ts` — 类型声明文件
- `node_modules/` / `__pycache__/` — 第三方依赖
- 纯类型定义文件（只含 interface/type/Pydantic model 字段定义）

### 三维度检查标准

#### 维度一：注释覆盖率（权重 40%）

**目标：10 行代码中，至少 3 行是注释（约 30% 注释率）**

| 注释率 | 评分 | 等级 |
|--------|:----:|:----:|
| ≥ 30% | ⭐⭐⭐ | 优秀 |
| 20% ~ 29% | ⭐⭐ | 良好 |
| 10% ~ 19% | ⭐ | 需改进 |
| < 10% | ❌ | 不合格 |

#### 维度二：注释内容准确性（权重 35%）

注释必须准确描述代码的实际行为，不能"说一套做一套"。

| 级别 | 说明 |
|------|------|
| 🔴 严重 | 注释和代码完全矛盾，会误导开发者 |
| 🟡 中等 | 注释有歧义或不完整 |
| 🟢 轻微 | 可以更精准但不会引起误解 |

#### 维度三：小白友好度（权重 25%）

- 技术术语必须有白话解释（不能堆砌"RAG""向量化""嵌入"）
- 复杂逻辑（>5行）必须有生活比喻
- 数字和阈值必须有来源说明（为什么 chunk_size=500？）

---

## security-audit

对项目进行全面的安全审计——检查硬编码密钥、SQL注入、XSS、API安全配置、依赖漏洞等九大类别，并给出修复方案和优先级排序。

### 使用方式

| 命令 | 功能 |
|------|------|
| `/security-audit` | 全面审计——源码 + 配置 + 依赖 |
| `/security-audit 快速` | 快速扫描——只查 🔴 严重级别 |
| `/security-audit backend/` | 按目录审计 |
| `/security-audit 依赖` | 只审计第三方依赖漏洞 |

### 九大检查类别一览

| # | 检查类别 | 严重度 | 核心检查内容 |
|:---:|----------|:------:|------------|
| 1 | 硬编码敏感信息 | 🔴 | 密码、API Key、Token 是否明文写在代码中 |
| 2 | SQL 注入风险 | 🔴 | 数据库操作是否使用参数化查询 |
| 3 | XSS 跨站脚本 | 🔴 | `dangerouslySetInnerHTML`、`innerHTML`、`eval()` |
| 4 | API 安全配置 | 🔴 | JWT 密钥来源、过期时间、CORS 配置、速率限制 |
| 5 | 配置文件泄露 | 🟡 | `.env` 是否有明文密钥、是否被 gitignore |
| 6 | 不安全数据存储 | 🟡 | Token 存储方式是否安全 |
| 7 | 第三方依赖漏洞 | 🟡 | pip/npm 包是否有已知漏洞 |
| 8 | 输入验证缺失 | 🟡 | 文件上传类型/大小、密码复杂度 |
| 9 | 其他安全隐患 | 🟢~🟡 | console.log 泄露、空异常处理、类型绕过 |

### 严重度定义

| 级别 | 图标 | 含义 | 处理时限 |
|------|:----:|------|:--------:|
| 严重 | 🔴 | 可直接导致数据泄露或系统被入侵 | **立即修复** |
| 中等 | 🟡 | 存在潜在风险，特定条件下可被利用 | **尽快修复**（本周内） |
| 轻微 | 🟢 | 不良实践，不会直接导致安全事件 | **逐步改进** |
| 通过 | ⚪ | 该项检查无问题 | — |

---

## Git 提交质量门禁

### 什么是质量门禁？

> 就像大楼的消防验收——入住前必须确保消防栓有水、逃生通道畅通、灭火器在有效期内。
> 质量门禁 = 代码提交前自动跑测试 + 安全检查，全部通过才能提交。

### 提交流程

```
用户说 "帮我提交"
     ↓
gitcommit-agent 启动
     ↓
并行运行：
  ├── tester agent（后端 pytest + 前端 vitest）
  └── quality-engineer agent（安全检查 + 注释检查 + 代码规范）
     ↓
读取结果文件
  ├── ✅ 全部通过 → 执行 git commit
  └── ❌ 任一失败 → 阻止提交，输出问题详情
```

### 为什么需要这个流程？

1. **防止"能跑就行"心态**：测试不通过不提交
2. **防止安全漏洞上线**：密钥泄露、注入漏洞在提交前被发现
3. **保证代码可读性**：注释率达标、规范合格才能入库
4. **保护用户隐私**：数据库中没有明文密码等安全隐患

### 相关文件

| 文件 | 作用 |
|------|------|
| `.claude/agents/tester.md` | 测试 agent 配置和规范 |
| `.claude/agents/quality-engineer.md` | 质量检查 agent 配置和规范 |
| `.claude/agents/gitcommit-agent.md` | 提交调度器 agent 配置 |
| `.claude/hooks/pre-commit-check.js` | Git commit 拦截 hook |
| `.claude/commands/test.md` | `/test` 命令入口 |
| `.claude/commands/security-audit.md` | `/security-audit` 命令入口 |
| `.claude/commands/comments-check.md` | `/comments-check` 命令入口 |
| `.claude/commands/git-save.md` | `/git-save` 命令入口 |
| `.claude/commands/run-app.md` | `/run-app` 命令入口 |
