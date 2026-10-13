// Original task identity is input, never inferred from a mutable login profile.
export function taskBindingError(code = 'TASK_BINDING_MISMATCH') {
  const message = code === 'ORIGINAL_TASK_CONTEXT_REQUIRED'
    ? 'Original task context is required; preserve the task and recover its identity'
    : 'The selected account or task does not match the original task context';
  return Object.assign(new Error(message), { code, stage: 'task_binding', retryable: false, write_occurred: false });
}

export function requireOriginalTaskContext(input = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw Object.assign(new Error('Invalid task context'), { code: 'INVALID_INPUT', write_occurred: false });
  if (['environment', 'profile', 'account_id', 'project_name', 'task_id'].some(key => input[key] === undefined || input[key] === null || input[key] === ''))
    throw taskBindingError('ORIGINAL_TASK_CONTEXT_REQUIRED');
  if (input.environment !== 'online' || typeof input.profile !== 'string' || !input.profile.trim()
    || typeof input.account_id !== 'string' || !/^[0-9]{1,128}$/.test(input.account_id)
    || typeof input.project_name !== 'string' || !input.project_name.trim()
    || !['string', 'number'].includes(typeof input.task_id) || !String(input.task_id).trim()
    || (typeof input.task_id === 'number' && (!Number.isSafeInteger(input.task_id) || input.task_id <= 0)))
    throw Object.assign(new Error('Invalid original task context'), { code: 'INVALID_INPUT', stage: 'task_binding', retryable: false, write_occurred: false });
}

export function assertTaskAccount(input, actual) {
  if (actual?.profile !== input.profile || actual?.account_id !== input.account_id) throw taskBindingError();
}

export async function resolveTaskBinding(input, readConfiguration) {
  requireOriginalTaskContext(input);
  const selected = await readConfiguration(['--format', 'json', 'configure', 'get', '--profile', input.profile]);
  const profile = selected?.data?.profile;
  if (!selected?.ok || !profile?.account_id)
    throw Object.assign(new Error('Restore the original account login'), { code: 'AUTH_REQUIRED', stage: 'authentication', retryable: false });
  assertTaskAccount(input, { profile: profile.name, account_id: profile.account_id });
  const bindings = [profile.openapi_env, profile.openapiEnv].filter(value => value !== undefined);
  const baseUrl = String(profile.baseUrl ?? profile.base_url ?? '').trim().replace(/\/+$/, '');
  if (bindings.some(value => !['online', 'prod', 'production'].includes(String(value).trim().toLowerCase()))
    || (baseUrl && baseUrl !== 'https://livesaas.volcengineapi.com')
    || (!bindings.length && !baseUrl)) throw taskBindingError();
  return ['--profile', input.profile, '--env', 'online', '--account-id', input.account_id];
}

const SETUP_MESSAGE = '当前质检服务配置暂不可用，请检查已选账号的服务配置后继续。本次未创建任务。';
function pending() { return Object.assign(new Error(SETUP_MESSAGE), { code: 'SETUP_PENDING', retryable: false }); }
function environment(value) {
  if (typeof value !== 'string') return null;
  const text = value.trim().toLowerCase();
  if (['online', 'prod', 'production'].includes(text)) return 'online';
  return null;
}

// Resolve an explicitly selected independent profile before any business request.
export async function resolveCreationBinding(input, readConfiguration) {
  if (input.profile !== undefined && (typeof input.profile !== 'string' || !input.profile.trim())) throw pending();
  const expected = input.environment === undefined || input.environment === 'online' ? 'online' : null;
  if (input.environment !== undefined && !expected) throw pending();
  const args = ['--format', 'json', 'configure', 'get'];
  if (input.profile !== undefined) args.push('--profile', input.profile);
  let selected;
  try { selected = await readConfiguration(args); } catch { throw pending(); }
  const profile = selected?.data?.profile;
  if (!selected?.ok || !profile || typeof profile !== 'object' || !profile.name) throw pending();
  if (input.profile !== undefined && profile.name !== input.profile) throw pending();
  const bound = profile.openapi_env ?? profile.openapiEnv;
  const bindings = [profile.openapi_env, profile.openapiEnv].filter(value => value !== undefined);
  if (bindings.some(value => environment(value) !== 'online')) throw pending();
  const baseUrl = String(profile.baseUrl ?? profile.base_url ?? '').trim().replace(/\/+$/, '');
  if (baseUrl && baseUrl !== 'https://livesaas.volcengineapi.com') throw pending();
  const actual = environment(bound) || (!bindings.length && baseUrl ? 'online' : null);
  if (!actual || (expected && actual !== expected)) throw pending();
  if (input.account_id && profile.account_id !== input.account_id) throw pending();
  return ['--profile', profile.name, '--env', actual, ...(profile.account_id ? ['--account-id', profile.account_id] : [])];
}
