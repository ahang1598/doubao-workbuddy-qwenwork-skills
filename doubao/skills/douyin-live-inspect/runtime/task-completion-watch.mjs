import { setTimeout as sleep } from 'node:timers/promises';
import { runOperationArgs } from './operations.mjs';
import { resolveTaskBinding, requireOriginalTaskContext } from './task-binding.mjs';
import { resolveInspectionEnvironment } from './remote-dashboard.mjs';

export const POLL_INTERVAL_MS = 60_000;
export const MAX_WATCH_MS = 4 * 60 * 60_000;
export const REQUEST_TIMEOUT_MS = 30_000;

function failure(code, message, retryable = false) {
  return Object.assign(new Error(message), { code, retryable });
}

// Error bodies may contain credentials or media URLs. Classify in memory and
// return only fixed codes/messages to the Agent, never raw response bodies.
export async function runWatchCli(args, { env = process.env, signal, execute = runOperationArgs } = {}) {
  const payload = await execute(args, { env, signal });
  if (payload?.ok === true) return payload;
  const error = payload?.error || {};
  if (['ORIGINAL_TASK_CONTEXT_REQUIRED', 'TASK_BINDING_MISMATCH'].includes(error.code)) throw failure(error.code, '原任务身份缺失或不匹配');
  if (/^(?:INVALID_RESPONSE|RESPONSE_TOO_LARGE)$/.test(error.code || '')) throw failure('INVALID_RESPONSE', '质检响应无效，请稍后继续');
  const response = error.details?.response;
  const status = Number(error.http_status ?? error.httpStatus ?? error.statusCode ?? error.details?.http_status ?? response?.status);
  const remoteCode = response?.data?.ResponseMetadata?.Error?.Code ?? response?.ResponseMetadata?.Error?.Code;
  const detail = `${error.code || ''} ${remoteCode || ''} ${error.subtype || ''} ${error.type || ''} ${error.message || ''}`;
  if (status === 403 || error.type === 'authorization' || /forbidden|permission|access.?denied|权限/i.test(detail)) {
    throw failure('PERMISSION_DENIED', '当前账号无法访问本次质检任务');
  }
  if (status === 401 || /authentication|unauthorized|credential|token|session|expired|登录|认证/i.test(detail)) {
    throw failure('AUTH_REQUIRED', '本次质检需要恢复原账号授权');
  }
  if (status === 429 || status >= 500 || /timeout|timed.?out|throttl|rate.?limit|too.?many|service.?unavailable|internal.?error|network|ECONN|ETIMEDOUT|EAI_AGAIN/i.test(detail)) {
    throw failure('STATUS_UNAVAILABLE', '质检状态暂时无法获取', true);
  }
  throw failure('TASK_QUERY_FAILED', '无法查询本次质检任务，请核对原任务配置');
}

export function validateWatchInput(input) {
  requireOriginalTaskContext(input);
  if (!input || typeof input !== 'object' || Array.isArray(input)
    || !['online'].includes(input.environment)
    || typeof input.profile !== 'string' || !input.profile.trim()
    || typeof input.project_name !== 'string' || !input.project_name.trim()
    || /[\x00-\x1f\x7f/\\]/.test(input.project_name)
    || !/^\d+$/.test(String(input.task_id)) || !Number.isSafeInteger(Number(input.task_id)) || Number(input.task_id) <= 0) {
    throw failure('INVALID_INPUT', '监听需要原任务的环境、账号配置、项目与任务编号');
  }
  return {
    environment: input.environment, profile: input.profile.trim(),
    ...(input.account_id ? { account_id: input.account_id } : {}),
    project_name: input.project_name, task_id: Number(input.task_id),
    ...(typeof input.scenario === 'string' ? { scenario: input.scenario } : {}),
  };
}

export async function watchTaskCompletion(input, {
  signal, env = process.env, runCli = runWatchCli,
  now = () => Date.now(), wait = (ms, abortSignal) => sleep(ms, undefined, { signal: abortSignal }),
  setTimer = setTimeout, clearTimer = clearTimeout,
  resolveRouting = resolveInspectionEnvironment,
} = {}) {
  const context = validateWatchInput(input);
  const startedAt = now();
  const deadline = startedAt + MAX_WATCH_MS;
  const timeout = new AbortController();
  const combined = signal ? AbortSignal.any([signal, timeout.signal]) : timeout.signal;
  const timer = setTimer(() => timeout.abort(), MAX_WATCH_MS);
  let lastStatus = null;
  let checks = 0;
  let authRetried = false;
  const result = (status) => ({
    status, context, task_status: lastStatus, checks,
    elapsed_ms: Math.max(0, now() - startedAt),
  });
  const interrupted = () => signal?.aborted ? 'cancelled' : 'timed_out';
  try {
    if (combined.aborted) return result(interrupted());
    const routing = resolveRouting({ environment: context.environment, env });
    const childEnv = { ...env, DOUYIN_INSPECT_ENV: context.environment, DOUYIN_INSPECT_BASE_URL: routing.baseUrl, DOUYIN_INSPECT_AUTO_LOGIN: '0' };
    const options = { env: childEnv, signal: combined };
    const binding = await resolveTaskBinding(context, (args) => runCli(args, options));
    if (binding.includes('--account-id')) context.account_id = binding[binding.indexOf('--account-id') + 1];
    while (!combined.aborted && now() < deadline) {
      const checkStartedAt = now();
      try {
        checks += 1;
        const payload = await runCli([
          ...binding, 'quality', '+task-get', '--project-name', context.project_name, '--task-id', String(context.task_id),
        ], options);
        if (combined.aborted || now() >= deadline) return result(interrupted());
        const task = payload?.data?.response?.data?.Result ?? payload?.data?.response?.Result;
        if (!task || task.ProjectName !== context.project_name || String(task.TaskId) !== String(context.task_id) || Number(task.TaskType) !== 2) {
          throw failure('TASK_BINDING_MISMATCH', '查询结果与原直播质检任务不一致');
        }
        lastStatus = ['number', 'string'].includes(typeof task.Status) && String(task.Status).trim() !== ''
          && Number.isInteger(Number(task.Status)) ? Number(task.Status) : null;
        if ([3, 4].includes(lastStatus)) return result('completed');
        if (lastStatus === 5) return result('task_failed');
      } catch (error) {
        if (combined.aborted) return result(interrupted());
        // A single transient auth failure (e.g. an STS refresh hiccup) must not
        // kill the watcher: retry once after a short backoff. A genuine login
        // problem fails again and still exits with AUTH_REQUIRED for recovery.
        if (error.code === 'AUTH_REQUIRED' && !authRetried) {
          authRetried = true;
          await wait(Math.min(REQUEST_TIMEOUT_MS, Math.max(0, deadline - now())), combined);
          if (combined.aborted) return result(interrupted());
          continue;
        }
        if (!error.retryable) throw error;
      }
      await wait(Math.min(Math.max(0, POLL_INTERVAL_MS - (now() - checkStartedAt)), Math.max(0, deadline - now())), combined);
    }
    return result(interrupted());
  } catch (error) {
    if (combined.aborted) return result(interrupted());
    throw error;
  } finally {
    clearTimer(timer);
    timeout.abort();
  }
}
