## 执行流程

收到 `/test` 后，判断模式并**通过 Agent 工具派发 tester subagent 执行**，利用并行加速。

---

## 意图识别

| 用户说法 | 模式 | 派发方式 |
|----------|:----:|----------|
| `/test` 无参数 / "所有" / "全部" | **模式 C** | 并行派发 2 个 tester agent（后端 + 前端） |
| "/test 后端" / "/test 前端" / 指定模块名 | **模式 A** | 先分析源码，再派发 tester agent 写测试 |
| "/test 跑一下" / "执行" | **模式 B** | 并行派发 2 个 tester agent 跑已有测试 |

---

## 模式 C：全部测试 + 覆盖（最常用）

**必须并行派发 2 个 tester subagent**：

```javascript
// Agent 1: 后端测试
Agent({ subagent_type: "tester", description: "Run backend tests",
  prompt: "执行后端全部测试：cd backend && venv/Scripts/pytest tests/ -v --tb=short。输出每个测试文件的结果和最终统计。" })

// Agent 2: 前端测试（与上面同时派发）
Agent({ subagent_type: "tester", description: "Run frontend tests",  
  prompt: "执行前端全部测试：cd frontend && npx vitest run。输出每个测试文件的结果和最终统计。" })
```

两个 agent 完成后，主 Agent 负责：
1. 合并结果输出统一报告（按 tester 规定的三部分报告格式）
2. 列出源文件 vs 测试文件覆盖概览
3. 写入 `.claude/test-result.json`
4. 主动询问用户优先补充哪个模块的测试

---

## 模式 B：只跑已有测试

同上，并行派发 2 个 tester agent 分别执行后端和前端测试，合并报告并写入 `.claude/test-result.json`。

---

## 模式 A：为指定模块创建测试

主 Agent 先用 Read 分析源码 → 派发 tester agent 写测试 → tester agent 写完自动执行验证。

---

## 覆盖分析格式

```
📋 测试覆盖概览

✅ 已有测试（N/M）
  backend/tests/test_auth.py → backend/app/api/auth.py
  frontend/src/__tests__/AuthStore.test.ts → frontend/src/store/authStore.ts

❌ 缺少测试（N/M）
  🔴 backend/app/rag/graph.py — RAG 核心流程，建议优先
  🟡 frontend/src/pages/KnowledgeManage.tsx — 知识库管理页面
  ⚪ backend/app/main.py — 入口文件，不需要测试
```

---

## 测试环境（供 tester agent 使用）

| 层级 | 工具 | 执行命令 |
|------|------|----------|
| 后端 | pytest + pytest-asyncio + httpx | `cd backend && venv/Scripts/pytest tests/ -v --tb=short` |
| 前端 | Vitest + @testing-library/react + jsdom | `cd frontend && npx vitest run` |

测试文件位置：`backend/tests/` / `frontend/src/__tests__/`

---

## 完成后必须写入

```json
// .claude/test-result.json
{ "passed": true, "total": 113, "passedCount": 113, "failedCount": 0, "duration": 22.99, "timestamp": "..." }
```
