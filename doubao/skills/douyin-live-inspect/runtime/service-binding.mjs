const SETUP_MESSAGE = '当前质检服务配置暂不可用，请检查已选账号的服务配置后继续。本次未创建任务。';
function pending() { return Object.assign(new Error(SETUP_MESSAGE), { code: 'SETUP_PENDING', retryable: false }); }
function environment(value) {
  if (typeof value !== 'string') return null;
  const text = value.trim().toLowerCase();
  if (['online', 'prod', 'production'].includes(text)) return 'online';
  return null;
}

// configure-get describes a profile's binding. Its command metadata can reflect
// default service flags rather than that binding, so explicit profile fields win.
export async function resolveServiceBinding(input, readConfiguration) {
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
  return ['--profile', profile.name, '--env', actual];
}
