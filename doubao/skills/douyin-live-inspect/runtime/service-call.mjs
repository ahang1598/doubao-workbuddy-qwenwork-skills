// 核心实现模块：负责本模块声明的检测、状态处理或交付边界；敏感输入和原始响应不进入日志。
import { runOperationArgs } from './operations.mjs';

// Preserve business workflow result envelopes without starting an external process.
export async function runService(args, options = {}) {
  const payload = await runOperationArgs(args, options);
  const code = payload.code ?? payload.exitCode ?? (payload.ok ? 0 : payload.error?.exit_code ?? 1);
  const text = JSON.stringify(payload);
  return { code, payload, stdout: code === 0 ? text : '', stderr: code === 0 ? '' : text, overflow: false };
}
