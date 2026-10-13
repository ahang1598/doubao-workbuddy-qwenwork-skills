import { requireOriginalTaskContext, assertTaskAccount, taskBindingError } from './task-binding.mjs';
import { onlineEnvironment } from './online-environment.mjs';
import { randomUUID } from 'node:crypto';
import { runService } from './service-call.mjs';

export function runEndCli(args) { return runService(args, { env: onlineEnvironment() }); }

// Confirmation-required responses use stderr even with --format json. Keep both
// streams in memory and expose only the parsed payload to the controller.
export function parseCliPayload(stdout, stderr) {
  for (const output of [stdout, stderr]) {
    if (!output?.trim()) continue;
    try { return JSON.parse(output); } catch {}
  }
  return null;
}

function result(payload) {
  return payload?.data?.response?.data?.Result ?? payload?.data?.response?.Result;
}

function profileOf(payload) {
  const data = payload?.data;
  if (!payload?.ok || !(data?.status === 'authenticated' || (data?.status === 'expired' && data?.refresh_available === true))) return null;
  const p = data.profile || {};
  return { name: p.name, mode: p.mode, source: data.credentials?.source, region: p.region, service: p.service, account_id: data.account_id || p.account_id, base_url: p.base_url, openapi_env: p.openapi_env || payload.meta?.environment };
}

const locked = new Set(['submitting', 'accepted', 'unknown', 'terminal']);

export function createTaskEndController({ projectName, taskId, profile, account_id, environment, runCli = runEndCli, now = Date.now, onAccepted = () => {} }) {
  const context = { environment, profile, account_id, project_name: projectName, task_id: taskId };
  const pinned = [...(profile ? ['--profile', profile, '--env', environment] : []), ...(account_id ? ['--account-id', account_id] : [])];
  const targetArgs = ['--project-name', String(projectName), '--task-id', String(taskId)];
  let state = { status: 'idle', message: '', revision: 0 };
  let plan = null;
  let preparing = null;
  let acceptedAt = null;

  const view = () => ({
    ...state,
    end_accepted_at: acceptedAt,
    operation_id: plan?.id ?? null,
    expires_at: plan?.expires ?? null,
    can_end: state.status === 'ready' && Date.parse(plan?.expires) > now(),
  });
  const set = (status, message = '') => { state = { status, message, revision: state.revision + 1 }; return view(); };
  const observe = (status) => {
    if ([3, 4, 5].includes(Number(status)) && state.status !== 'terminal') set('terminal');
  };
  const acknowledge = () => {
    acceptedAt ??= now() / 1000;
    if (state.status !== 'terminal') set('accepted');
    onAccepted();
  };
  const taskStatus = async (prefix = []) => {
    const r = await runCli([...prefix, 'quality', '+task-get', ...targetArgs]);
    const task = result(r.payload);
    if (r.code !== 0 || !r.payload?.ok) throw Object.assign(new Error('TASK_CHECK_FAILED'), { code: r.payload?.error?.code });
    if (Number(task?.TaskId) !== Number(taskId) || task?.ProjectName !== projectName) throw taskBindingError();
    observe(task.Status);
    return Number(task.Status);
  };

  const prepare = () => {
    if (locked.has(state.status) || (state.status === 'ready' && Date.parse(plan?.expires) > now())) return Promise.resolve(view());
    if (preparing) return preparing;
    plan = null;
    set('preparing');
    preparing = (async () => {
      try {
        requireOriginalTaskContext(context);
        const auth = await runCli([...pinned, 'auth', 'status']);
        const profile = profileOf(auth.payload);
        if (auth.code !== 0 || !profile?.openapi_env) throw new Error('AUTH_REQUIRED');
        assertTaskAccount(context, { profile: profile.name, account_id: profile.account_id });
        if (profile.openapi_env !== context.environment) throw taskBindingError();
        const prefix = pinned;
        if (await taskStatus(prefix) !== 2) {
          if (!locked.has(state.status)) set('unavailable', '当前任务不可结束');
          return view();
        }
        if (locked.has(state.status)) return view();
        const args = [...prefix, 'quality', '+task-end', ...targetArgs];
        let preview = await runCli([...args, '--plan']);
        // Only an explicit unsupported-option response permits the legacy
        // preparation path; authentication/network failures must not fall back.
        if (preview.code === 2 && ['unknown_option', 'commander.unknownOption'].includes(preview.payload?.error?.subtype)) {
          const dry = await runCli([...args, '--dry-run']);
          if (dry.code !== 0 || !dry.payload?.ok || dry.payload?.data?.dry_run !== true
            || dry.payload.data.network_request !== false || dry.payload.data.risk?.requires_confirmation !== true) throw new Error('PREPARE_FAILED');
          preview = await runCli(args);
        }
        if (locked.has(state.status)) return view();
        const confirmation = preview.payload?.error?.details?.confirmation;
        if (preview.code !== 10 || preview.payload?.error?.subtype !== 'confirmation_required'
          || !confirmation?.token || confirmation?.target?.action !== 'EndTask'
          || confirmation.target.body?.ProjectName !== projectName || Number(confirmation.target.body?.TaskId) !== Number(taskId)
          || !(Date.parse(confirmation.expires_at) > now())) throw new Error('PREPARE_FAILED');
        if (locked.has(state.status)) return view();
        plan = { id: randomUUID(), token: confirmation.token, expires: confirmation.expires_at, args, prefix, profile };
        return set('ready');
      } catch (error) {
        if (!locked.has(state.status)) {
          set('failed', '暂时无法准备结束质检，请核对原任务上下文后继续');
          if (['ORIGINAL_TASK_CONTEXT_REQUIRED', 'TASK_BINDING_MISMATCH'].includes(error.code)) state.code = error.code;
        }
        return view();
      }
    })().finally(() => { preparing = null; });
    return preparing;
  };

  const submit = async (operationId) => {
    if (locked.has(state.status)) return view();
    if (!plan || operationId !== plan.id || state.status !== 'ready') return view();
    if (!(Date.parse(plan.expires) > now())) return set('failed', '确认计划已过期，请重新准备后再次点击');
    // Claim the operation before any await, including read-only preflight checks.
    set('submitting');
    let writeStarted = false;
    try {
      const auth = await runCli([...pinned, 'auth', 'status']);
      if (state.status !== 'submitting') return view();
      if (auth.code !== 0 || JSON.stringify(profileOf(auth.payload)) !== JSON.stringify(plan.profile)) {
        set('failed', '质检服务状态已变化，请核对原账号后继续');
        if (auth.payload?.error?.code === 'TASK_BINDING_MISMATCH' || (auth.code === 0 && profileOf(auth.payload))) state.code = 'TASK_BINDING_MISMATCH';
        return view();
      }
      if (await taskStatus(plan.prefix) !== 2) {
        if (state.status !== 'terminal') set('unavailable', '当前任务不可结束');
        return view();
      }
      if (state.status !== 'submitting') return view();
      writeStarted = true;
      const execution = await runCli([...plan.args, '--confirm-token', plan.token]);
      if (execution.code === 0 && execution.payload?.ok && result(execution.payload)?.Status === true) {
        acknowledge();
      } else if (state.status !== 'terminal') {
        // Only an explicit no-write result permits another user-initiated attempt.
        set(execution.payload?.error?.write_occurred === false ? 'failed' : 'unknown',
          execution.payload?.error?.write_occurred === false
            ? '结束未提交，请重新准备后再次点击' : '结束结果待确认，正在查询任务状态');
      }
    } catch (error) {
      if (state.status !== 'terminal') set(writeStarted ? 'unknown' : 'failed',
        writeStarted ? '结束结果待确认，正在查询任务状态' : '结束未提交，状态核对失败，请重试');
      if (!writeStarted && error.code === 'TASK_BINDING_MISMATCH') state.code = error.code;
    }
    return view();
  };
  return { view, prepare, submit, observe, acknowledge };
}
