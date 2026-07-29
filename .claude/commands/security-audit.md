对项目进行全面的安全审计——检查硬编码密钥、SQL注入、XSS、API安全配置、依赖漏洞等九大类别，并给出修复方案和优先级排序。

## 意图识别

收到 `/security-audit` 后，先解析用户输入，判断审计范围：

| 用户说法示例 | 审计模式 |
|-------------|:------:|
| `/security-audit`（无参数） | **全面审计** — 源码 + 配置 + 依赖，全量扫描 |
| `/security-audit 快速` | **快速扫描** — 只查 🔴 严重级别 |
| `/security-audit backend/` | **目录审计** — 只审计后端目录 |
| `/security-audit backend/app/api/auth.py` | **单文件审计** |
| `/security-audit 依赖` | **依赖审计** — 只审计第三方依赖 |

---

## 审计范围

| 范围 | 文件类型 | 搜索方式 |
|------|----------|----------|
| 后端源码 | `backend/app/**/*.py` | Glob 扫描，排除 `backend/tests/` |
| 前端源码 | `frontend/src/**/*.ts` `frontend/src/**/*.tsx` | Glob 扫描，排除 `__tests__/`、`*.d.ts` |
| 配置文件 | `backend/.env` `backend/.env.example` `package.json` `vite.config.ts` `.gitignore` | 直接读取 |

---

## 九大审计检查类别

---

### 检查项 1：硬编码敏感信息 🔴 严重 ⚡ 快速通道

用 Grep 搜索以下模式（`-i: true`）：

| # | 搜索模式 | 说明 |
|---|----------|------|
| 1 | `password\s*[:=]\s*['"]\S+['"]` | 硬编码密码 |
| 2 | `secret\s*[:=]\s*['"]\S+['"]` | 硬编码密钥 |
| 3 | `api[_-]?key\s*[:=]\s*['"][\w-]{10,}['"]` | API Key |
| 4 | `dashscope.*api.*key` | 百炼 API Key |
| 5 | `access[_-]?token\s*[:=]\s*['"][^'"]+['"]` | 硬编码 Token |
| 6 | `sqlite.*://.*\.db` | 数据库路径（检查是否含敏感路径） |

**确认方法**：搜到匹配后必须 Read 上下文判断是真实密钥还是变量声明/测试数据。

**严重度**：
- 出现真实密钥 → 🔴 严重
- 出现真实密码 → 🔴 严重
- 只有变量声明无赋值 → ⚪ 通过

---

### 检查项 2：SQL 注入风险 🔴 严重 ⚡ 快速通道

搜索 SQL 拼接模式：

| # | 搜索模式（Python） | 说明 |
|---|-------------------|------|
| 1 | `f"SELECT\|f'SELECT\|f"INSERT\|f'INSERT` | f-string 拼接 SQL |
| 2 | `\+ "SELECT\|\+ 'SELECT\|\+ "INSERT` | 字符串拼接 SQL |
| 3 | `execute\(\s*f["']` | execute 中用了 f-string |
| 4 | `\.format\(.*SELECT` | format 方法拼接 SQL |

**安全 vs 不安全**：
```python
# ✅ 安全（参数化查询）
await db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})

# ❌ 危险（字符串拼接）
await db.execute(text(f"SELECT * FROM users WHERE id = {user_id}"))
```

---

### 检查项 3：XSS 跨站脚本 🔴 严重 ⚡ 快速通道

搜索前端代码：

| # | 搜索模式 | 说明 |
|---|----------|------|
| 1 | `dangerouslySetInnerHTML` | React 危险属性 |
| 2 | `\.innerHTML\s*=` | 原生 DOM 操作 |
| 3 | `eval\(` | eval 执行 |
| 4 | `new Function\(` | 动态函数创建 |

---

### 检查项 4：API 安全配置 🔴 严重

| # | 检查项 | 搜索/检查方法 |
|---|--------|--------------|
| 1 | JWT `SECRET_KEY` 是否硬编码 | 读取 `backend/.env` 和 `backend/app/config.py` |
| 2 | `access_token` 过期时间 | 检查 `expire_minutes` 是否 ≤ 30 |
| 3 | CORS `allow_origins` | 搜索 `CORSMiddleware` 的 `allow_origins` 参数 |
| 4 | 密码最小长度 | 检查注册接口的密码验证 |
| 5 | 密码哈希 | 确认使用 `bcrypt` 而非明文存储 |
| 6 | 速率限制 | 检查是否有 `RateLimiter` 或 token bucket |

---

### 检查项 5：配置文件泄露 🟡 中等

| # | 检查内容 | 方法 |
|---|----------|------|
| 1 | `.env` 文件是否包含明文密钥 | 读取 `backend/.env` |
| 2 | `.env` 是否在 `.gitignore` 中 | 读取 `.gitignore` |
| 3 | `vite.config.ts` 中是否硬编码环境变量 | 搜索 `define:` 块 |
| 4 | `.claude/settings.json` 敏感路径 | 检查 `additionalDirectories` |

---

### 检查项 6：不安全存储 🟡 中等

| # | 搜索模式 | 说明 |
|---|----------|------|
| 1 | `sessionStorage\.setItem\(` | Token 存储方式 |
| 2 | `JSON\.stringify\(.*password` | 密码序列化存储 |

> 本项目使用 sessionStorage 存储 JWT token（关闭浏览器即清除），属于可接受的安全实践。

---

### 检查项 7：依赖漏洞 🟡 中等

1. Python 后端：`cd backend && venv/Scripts/pip list --outdated 2>&1 | head -20`
2. 前端：检查 `package.json` 中关键依赖版本（React、Vite、Axios）

---

### 检查项 8：输入验证 🟡 中等

| # | 检查项 | 方法 |
|---|--------|------|
| 1 | 文件上传类型白名单 | 检查 `file_storage.py` 的 `ALLOWED_EXTENSIONS` |
| 2 | 文件大小限制 | 检查上传接口是否有大小限制 |
| 3 | 密码复杂度 | 检查注册接口的最小密码长度 |
| 4 | 用户名长度限制 | 检查注册接口的用户名验证 |

---

### 检查项 9：其他隐患 🟢~🟡

| # | 搜索模式 | 说明 |
|---|----------|------|
| 1 | `console\.log\(.*(password\|token\|secret)` | 日志泄露敏感信息 |
| 2 | `print\(.*(password\|secret\|key)` | Python print 泄露 |
| 3 | `@ts-ignore` / `@ts-nocheck` | TypeScript 类型绕过 |
| 4 | `# type: ignore` | Python 类型绕过 |
| 5 | `eslint-disable` | ESLint 规则禁用 |
| 6 | `except:\|except Exception:` 后直接 `pass` | 空异常处理 |

---

## 审计报告格式

```
╔══════════════════════════════════════╗
║     🔒 安全审计报告                  ║
║     📅 检查时间：YYYY-MM-DD HH:MM   ║
║     📁 扫描文件：N 个               ║
║     🎯 审计模式：全面 / 快速 / 目录 ║
╚══════════════════════════════════════╝

📊 总体评分：XX/100 分（🟢安全 / 🟡需改进 / 🟠有风险 / 🔴高危）

🔴 严重：N 项  |  🟡 中等：N 项  |  🟢 轻微：N 项  |  ⚪ 通过：N 项

──────────────────────────────────────
检查项 1：硬编码敏感信息
──────────────────────────────────────
  ⚪ [通过] 未发现硬编码的密码或密钥
  ...

══════════════════════════════════════
  📋 修复优先级
══════════════════════════════════════

🔴 立即修复：
  1. [检查项4] config.py:15 — SECRET_KEY 硬编码为 "my-secret"

🟡 尽快修复：
  1. [检查项8] 文件上传缺少大小限制

🟢 逐步改进：
  1. [检查项9] 3 处 console.log 需要移除
```

## 评分公式

```
总分 = Σ(各项得分) / 检查项数

单项得分：
- 无问题：100 分
- 只有轻微问题：85 分
- 有中等问题：60 分
- 有严重问题：30 分

安全等级：
  90-100 分 → 🟢 安全
  70-89 分  → 🟡 需改进
  50-69 分  → 🟠 有风险
  < 50 分   → 🔴 高危
```

---

## ⚠️ 审计避坑指南

1. **把声明语句当硬编码**：`password: str = ""` 是类型声明，不是硬编码
2. **把测试 mock 数据当漏洞**：`backend/tests/` 和 `frontend/src/__tests__/` 下的文件跳过
3. **把 import 路径当 URL**：`from app.rag import graph` 是本地模块，不是硬编码 URL
4. **把环境变量读取当硬编码**：`os.getenv("API_KEY")` 是安全的读取方式
