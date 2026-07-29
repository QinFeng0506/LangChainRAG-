/**
 * Git Commit 预检查 Hook
 *
 * 在每次 Bash 工具调用前触发，检查是否为 git commit 命令。
 * 如果是，则验证 .claude/test-result.json 和 .claude/quality-result.json
 * 两个标记文件都存在且 passed=true，否则阻止提交。
 *
 * 退出码：0 = 允许, 2 = 阻止并反馈给 agent
 *
 * 设计原则：
 *   - 非 git commit 命令立即放行（减少性能影响）
 *   - 脚本自身异常默认阻止（安全优先）
 *   - 纯 Node.js，不依赖 jq/bash，保证 Windows 兼容
 */

const fs = require('fs');
const path = require('path');

// 从当前脚本位置推断项目根目录（.claude/hooks/ → 上两级）
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const TEST_RESULT = path.join(PROJECT_ROOT, '.claude', 'test-result.json');
const QUALITY_RESULT = path.join(PROJECT_ROOT, '.claude', 'quality-result.json');

// ============================================================
// 读取 stdin — Hook 通过 stdin 传入 JSON 事件数据
// ============================================================
function readStdin() {
  return new Promise((resolve) => {
    const chunks = [];
    let settled = false;

    const done = () => {
      if (settled) return;
      settled = true;
      resolve(chunks.join(''));
    };

    // 如果 stdin 已经被关闭（无数据传入），直接返回空
    if (process.stdin.isTTY) {
      resolve('');
      return;
    }

    process.stdin.setEncoding('utf8');

    // 逐块收集数据
    process.stdin.on('data', (chunk) => {
      chunks.push(chunk);
    });

    // stdin 关闭时完成
    process.stdin.on('end', () => {
      done();
    });

    // 2 秒兜底
    setTimeout(() => {
      done();
    }, 2000);
  });
}

// ============================================================
// 判断命令行是否为 git commit（排除 commit-tree/graph 等）
// ============================================================
function isGitCommit(command) {
  if (!command || typeof command !== 'string') return false;
  return /\bgit\b.*?\bcommit\b/.test(command) &&
         !/\bcommit-tree\b/.test(command) &&
         !/\bcommit-graph\b/.test(command);
}

// ============================================================
// 读取并验证 JSON 标记文件
// ============================================================
function checkMarkerFile(filePath, label) {
  if (!fs.existsSync(filePath)) {
    return {
      exists: false,
      passed: false,
      error: `❌ 未找到${label}标记文件 (${path.relative(PROJECT_ROOT, filePath)})`,
    };
  }

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const data = JSON.parse(content);

    if (typeof data.passed !== 'boolean') {
      return {
        exists: true,
        passed: false,
        data,
        error: `❌ ${label}标记文件格式错误：缺少 passed 字段`,
      };
    }

    return {
      exists: true,
      passed: data.passed,
      data,
      error: data.passed ? null : getFailureDetail(data, label),
    };
  } catch (e) {
    return {
      exists: true,
      passed: false,
      error: `❌ ${label}标记文件解析失败：${e.message}`,
    };
  }
}

// ============================================================
// 生成具体的失败原因描述
// ============================================================
function getFailureDetail(data, label) {
  if (label.includes('测试')) {
    return `❌ 测试未通过：${data.failedCount || '?'}/${data.total || '?'} 个用例失败`;
  }
  if (label.includes('质量')) {
    return `❌ 质量检查未通过：总分 ${data.totalScore || '?'}/100（需 ≥ ${data.threshold || 75}）`;
  }
  return `❌ ${label}未通过`;
}

// ============================================================
// 主流程
// ============================================================
async function main() {
  const stdinInput = await readStdin();

  // 空输入 → 非 hook 调用场景，直接放行
  if (!stdinInput) {
    process.exit(0);
  }

  // 解析 hook 传入的 JSON
  let toolCall;
  try {
    toolCall = JSON.parse(stdinInput);
  } catch {
    // JSON 解析失败 → 非标准输入，放行
    process.exit(0);
  }

  const command = toolCall.tool_input?.command || '';

  // 非 git commit 命令 → 立即放行（减少对正常工作的性能影响）
  if (!isGitCommit(command)) {
    process.exit(0);
  }

  // ========== 这是 git commit 命令，执行门禁检查 ==========

  const testCheck = checkMarkerFile(TEST_RESULT, '测试结果');
  const qualityCheck = checkMarkerFile(QUALITY_RESULT, '质量检查');

  const errors = [];

  // 检查测试标记文件
  if (!testCheck.exists) {
    errors.push(testCheck.error);
    errors.push('   请先运行 /test 或使用 gitcommit-agent 自动完成检查');
  } else if (!testCheck.passed) {
    errors.push(testCheck.error);
  }

  // 检查质量标记文件
  if (!qualityCheck.exists) {
    errors.push(qualityCheck.error);
    errors.push('   请先运行 /security-audit 或使用 gitcommit-agent 自动完成检查');
  } else if (!qualityCheck.passed) {
    errors.push(qualityCheck.error);
  }

  // 输出结果
  if (errors.length > 0) {
    console.error('');
    console.error('═══════════════════════════════════════════');
    console.error('  🚫  Git Commit 被阻止 — 质量门禁未通过');
    console.error('═══════════════════════════════════════════');
    console.error('');
    errors.forEach((e) => console.error(e));
    console.error('');
    console.error('💡 正确做法：使用 gitcommit-agent 完成检查 + 提交');
    console.error('   （这是项目安全机制，不是 bug，请勿尝试 --no-verify 或创建假标记文件绕过）');
    console.error('');
    process.exit(2); // exit 2 = 阻止工具执行
  }

  // 全部通过
  console.error('✅ 质量门禁检查通过，允许提交');
  process.exit(0); // exit 0 = 放行
}

main().catch((err) => {
  // 脚本自身异常 → 默认阻止（安全优先原则）
  console.error(`⚠️ Hook 脚本执行异常：${err.message}`);
  console.error('   默认阻止提交以确保安全，请检查 hook 配置');
  process.exit(2);
});
