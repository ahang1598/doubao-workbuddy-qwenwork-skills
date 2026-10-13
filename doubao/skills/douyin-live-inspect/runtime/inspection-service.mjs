// 本文件负责正式版能力探测与版本回退决策：
// 在已知是“新建请求”的前提下，检查认证状态、CLI 能力、项目列表，并决定走 formal / lite / clarify / blocked。
import { createProbeSession } from './probe-session.mjs';
import { runOperationArgs, getOperationSchema } from './operations.mjs';
import { runService } from './service-call.mjs';
import { resolveServiceBinding } from './service-binding.mjs';


const AUTH_CODES = new Set(['ExpiredToken', 'InvalidAccessKeyId', 'InvalidAccessKey', 'InvalidSecretToken', 'MissingAuthenticationToken', 'AUTH_REQUIRED', 'SETUP_PENDING', 'AUTH_EXCHANGE_FAILED', 'ExpiredTokenException', 'InvalidSecurityToken', 'InvalidToken', 'TokenExpired', 'STSExpired']);
const PROJECT_FIELDS = ['ProjectName', 'DisplayName', 'ProjectType', 'CreatedTime', 'ScenarioCount'];

// Capability checks are local; account and business reads use only this Skill.
function serviceReader(env, session) {
  return async args => {
    session.check();
    if (args.includes('--version')) return {ok:true};
    if (args.includes('schema')) {
      const id=args.at(-1);
      return {ok:id==='quality'||Boolean(getOperationSchema(id)),data:{id}};
    }
    const result=await runService(args,{env,signal:session.signal});
    session.check();
    return result.payload;
  };
}

function decision(route, reason, extra = {}) {
  return {
    ok: route !== 'blocked', command: 'check-inspection-service',
    data: {
      route, reason,
      next_action: { lite: 'start_lite', formal: 'select_project', clarify: 'choose_lite_or_login', blocked: 'resolve_blocker' }[route],
      activation_guidance_required: reason === 'formal_service_not_enabled',
      ...extra,
    },
  };
}

const safeId = value => typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,128}$/.test(value) ? value : undefined;
const NETWORK_CODES = new Set(['NETWORK_ERROR', 'ETIMEDOUT', 'ECONNRESET', 'ECONNREFUSED', 'ENOTFOUND', 'EAI_AGAIN', 'UND_ERR_CONNECT_TIMEOUT']);

function failureInfo(payload, thrown) {
  const error = payload?.error;
  let response = payload?.data?.response;
  // Old CLI versions embedded the transport JSON in this exact message prefix.
  // Never forward that message or interpret free text as a business error code.
  if (!error?.code && !error?.details?.remote_code && !error?.details?.remoteCode) {
    const match = /^OpenAPI call failed for action [A-Za-z0-9_]+: (\{[\s\S]*\})$/.exec(error?.message || '');
    if (match) { try { response = JSON.parse(match[1]); } catch { /* Unknown legacy failure. */ } }
  }
  const metadata = response?.data?.ResponseMetadata ?? response?.ResponseMetadata;
  const code = safeId(error?.code ?? error?.details?.remote_code ?? error?.details?.remoteCode ?? metadata?.Error?.Code);
  const status = error?.http_status ?? error?.details?.status ?? response?.status;
  const http_status = Number.isInteger(status) && status >= 100 && status <= 599 ? status : undefined;
  const request_id = safeId(error?.request_id ?? error?.details?.request_id ?? metadata?.RequestId);
  const network = error?.type === 'network' || NETWORK_CODES.has(thrown?.code)
    || NETWORK_CODES.has(code) || (error?.type === 'internal' && error?.message === 'fetch failed');
  const category = ['ENOENT', 'MODULE_NOT_FOUND', 'ERR_MODULE_NOT_FOUND'].includes(thrown?.code) ? 'script_missing'
    : thrown instanceof SyntaxError ? 'response_invalid'
    : AUTH_CODES.has(code) || ['auth', 'authentication'].includes(error?.type) ? 'authentication'
    : code === 'Forbidden' || error?.type === 'authorization' ? 'permission'
    : network ? 'network'
    : error?.type === 'validation' ? 'cli_arguments'
    : http_status >= 500 ? 'server'
    : error?.type === 'api' || code ? 'api' : 'unknown';
  return { category, ...(code ? { code } : {}), ...(http_status ? { http_status } : {}),
    ...(request_id ? { request_id } : {}) };
}

async function checkService(input, { read, sleep }) {
  // Explicit precondition prevents a caller from replacing an existing/unknown task.
  if (!['live', 'video'].includes(input.kind) || input.environment !== 'online'
      || (input.profile !== undefined && (typeof input.profile !== 'string' || !input.profile.trim()))
      || input.task_state !== 'not_created'
      || (input.allow_lite !== undefined && typeof input.allow_lite !== 'boolean')) {
    return decision('blocked', 'invalid_new_request_context');
  }
  const fallback = (reason, extra) => decision(input.allow_lite === false ? 'blocked' : 'lite', reason, extra);
  let context = {};
  const clarify = (reason, diagnostics) => decision(input.allow_lite === false ? 'blocked' : 'clarify', reason, {
    ...context, ...(diagnostics ? { diagnostics } : {}),
    next_action: input.allow_lite === false ? 'resolve_blocker' : 'choose_formal_or_lite',
  });
  const authChoice = diagnostics => input.allow_lite === false
    ? decision('blocked', 'authentication_required', { ...context, diagnostics, next_action: 'login_required' })
    : decision('clarify', 'authentication_required', { ...context, diagnostics });
  const domain = input.kind === 'live' ? 'quality' : 'content';
  const shortcut = input.kind === 'live' ? '+project-list' : '+video-project-list';
  const exactSchema = `${domain}/${shortcut}`;
  let binding;
  let bindingFailure;
  try {
    binding = await resolveServiceBinding(input, async args => {
      try {
        const payload = await read(args);
        // 绑定阶段如果失败，先把失败信息标准化，供后续 route 决策复用。
        if (payload?.ok !== true) bindingFailure = failureInfo(payload);
        return payload;
      } catch (error) {
        bindingFailure = failureInfo(undefined, error);
        throw error;
      }
    });
    context = { profile: binding[1], environment: 'online' };
  } catch {
    if (bindingFailure?.category === 'authentication') return authChoice({stage:'binding', ...bindingFailure, attempts:0});
    return decision('blocked', 'binding_unverified', { diagnostics: { stage: 'binding', ...(bindingFailure || { category: 'binding' }), attempts: 0 } });
  }
  // One extra read per check, shared across authentication and all project pages.
  let retried = false;
  let attempts = 0;
  async function query(args, stage) {
    for (;;) {
      let payload; let thrown;
      if (stage === 'projects') attempts += 1;
      try { payload = await read(args); } catch (error) { thrown = error; }
      const info = failureInfo(payload, thrown);
      const failed = thrown || payload?.ok !== true || info.code || info.http_status >= 400
        || payload?.data?.response?.ok === false;
      if (failed && !retried && info.code !== 'AccessDenyError'
          && ['network', 'server'].includes(info.category)) {
        retried = true;
        // 网络或服务端瞬时失败只允许一次重试，避免入口探测时间被无限拉长。
        try { await sleep(1000); }
        catch { return { payload, failed: true, diagnostics: { stage, ...info, attempts } }; }
        continue;
      }
      return { payload, failed, diagnostics: { stage, ...info, attempts } };
    }
  }
  const auth = await query(['--format', 'json', ...binding, 'auth', 'status'], 'authentication');
  const authState = auth.payload?.data;
  if (['unauthenticated', 'login_required'].includes(authState?.status)
      || (authState?.status === 'expired' && authState.refresh_available !== true)
      || auth.diagnostics.category === 'authentication') return authChoice(auth.diagnostics);
  const usable = authState?.status === 'authenticated'
    || (authState?.status === 'expired' && authState.refresh_available === true);
  if (auth.failed || !usable) return clarify('authentication_check_failed', auth.diagnostics);

  try {
    const gates = await Promise.all([
      read(['--version']), read(['--format', 'json', 'schema', 'quality']), read(['--format', 'json', 'schema', exactSchema]),
    ]);
    const failedGate = gates.find(p => p?.ok !== true);
    if (gates.some(p => p?.ok !== true) || gates[2].data?.id !== exactSchema) {
      return clarify('cli_capability_unavailable', { stage: 'capability', ...(failedGate ? failureInfo(failedGate) : { category: 'capability' }), attempts: 0 });
    }
  } catch (error) {
    return clarify('cli_capability_unavailable', { stage: 'capability', ...failureInfo(undefined, error), attempts: 0 });
  }
  const projects = new Map();
  const seen = new Set();
  for (let number = 1; number <= 1000; number += 1) {
    const { payload, failed, diagnostics } = await query(
      ['--format', 'json', ...binding, domain, shortcut, '--page-number', String(number), '--page-size', '100'], 'projects');
    const code = diagnostics.code;
    // 服务明确未开通时，才允许把新请求回退到 Lite；不能把其他错误混同成未开通。
    if (code === 'AccessDenyError') return fallback('formal_service_not_enabled', { ...context, diagnostics, formal_error: { code } });
    if (diagnostics.category === 'authentication') return authChoice(diagnostics);
    if (failed) return clarify({ script_missing: 'cli_script_missing', cli_arguments: 'cli_arguments_invalid',
      response_invalid: 'project_response_invalid', network: 'project_network_failed', server: 'project_server_failed' }[diagnostics.category] || 'project_query_failed', diagnostics);
    const invalidResponse = () => clarify('project_response_invalid', { ...diagnostics, category: 'response_invalid' });
    const result = payload.data?.response?.data?.Result ?? payload.data?.response?.Result;
    const rows = Array.isArray(result) ? result : result?.Projects ?? result?.Data;
    if (!Array.isArray(rows) || rows.length > 100) return invalidResponse();
    const total = Array.isArray(result) ? undefined : result?.TotalCount;
    if (total !== undefined && (!Number.isSafeInteger(total) || total < 0)) return invalidResponse();
    if (result?.PageNumber !== undefined && Number(result.PageNumber) !== number) return invalidResponse();
    const previousSize = seen.size;
    for (const row of rows) {
      if (!row || typeof row.ProjectName !== 'string' || !row.ProjectName || ![1, 2].includes(Number(row.ProjectType))) {
        return invalidResponse();
      }
      seen.add(row.ProjectName);
      if (Number(row.ProjectType) === (input.kind === 'live' ? 2 : 1) && !projects.has(row.ProjectName)) {
        projects.set(row.ProjectName, Object.fromEntries(PROJECT_FIELDS.filter(k => row[k] !== undefined).map(k => [k, row[k]])));
      }
    }
    if (number > 1 && rows.length > 0 && seen.size === previousSize) return invalidResponse();
    const complete = total === undefined ? rows.length < 100 : (number - 1) * 100 + rows.length >= total;
    if (complete) {
      return projects.size
        ? decision('formal', 'projects_available', { projects: [...projects.values()], ...context })
        : fallback('projects_unconfigured', context);
    }
    if (rows.length < 100) return invalidResponse();
  }
  return clarify('project_pagination_limit', { stage: 'projects', category: 'response_invalid', attempts });
}

export function entryTimeout(input, stage, context = {}) {
  return decision(input.allow_lite === false ? 'blocked' : 'clarify', 'entry_timeout', {
    ...context, next_action: input.allow_lite === false ? 'resolve_blocker' : 'choose_formal_or_lite',
    diagnostics: { stage, category: 'timeout', attempts: 0 },
  });
}

export async function checkInspectionService(input = {}, options = {}) {
  const session = options.session || createProbeSession();
  const read = options.read || serviceReader(options.env || process.env, session);
  let result;
  try {
    result = await checkService(input, {
      read: args => session.measure(args.includes('configure') ? 'binding' : args.includes('auth') ? 'authentication'
        : args.includes('schema') || args.includes('--version') ? 'capability' : 'projects', () => read(args)),
      sleep: options.sleep || (ms => session.sleep(ms)),
    });
    if (session.expired) result = entryTimeout(input, session.stage, result.data.profile ? { profile: result.data.profile, environment: 'online' } : {});
  } catch {
    result = session.expired ? entryTimeout(input, session.stage)
      : decision('blocked', 'execution_failed', { diagnostics: { stage: session.stage, category: 'unknown', attempts: 0 } });
  } finally { if (!options.session) await session.close(); }
  result.data.timings = session.timings();
  return result;
}
