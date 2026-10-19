import { taskBindingError } from './task-binding.mjs';
import { signVolcRequest } from './upload-signer.mjs';
import { resolveCredentials } from './auth.mjs';
import { commandUserAgent, commandSignal, observeAccount } from './telemetry.mjs';
export const OPENAPI_ENDPOINT = 'https://livesaas.volcengineapi.com/';
const AUTH_ERRORS = new Set(['ExpiredToken', 'ExpiredTokenException', 'InvalidSecurityToken', 'InvalidToken', 'TokenExpired', 'STSExpired']);
const SAFE_CODES = new Set(['ReportNotFoundError', 'ReportNotFound', 'Throttling', 'ThrottlingException', 'TooManyRequests', 'AccessDenied', 'AccessDenyError', 'Forbidden', 'Unauthorized', 'InvalidParameter', 'InvalidParameterValue', 'ResourceNotFound', 'TaskNotFound', ...AUTH_ERRORS]);
function failure(code, message, details = {}) { return Object.assign(new Error(message), { code, ...details }); }
async function payloadOf(response, limit, signal) {
  const declared = Number(response.headers?.get?.('content-length'));
  if (declared > limit) { await response.body?.cancel?.(); throw failure('RESPONSE_TOO_LARGE', 'OpenAPI response exceeded the size limit'); }
  if (response.body?.getReader) {
    const reader = response.body.getReader(), chunks = [];
    let bytes = 0;
    const abort = () => { reader.cancel().catch(() => {}); };
    signal.addEventListener('abort', abort, { once: true });
    try {
      while (true) {
        signal.throwIfAborted();
        const { done, value } = await reader.read();
        signal.throwIfAborted();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > limit) { await reader.cancel(); throw failure('RESPONSE_TOO_LARGE', 'OpenAPI response exceeded the size limit'); }
        chunks.push(Buffer.from(value));
      }
      return JSON.parse(Buffer.concat(chunks).toString('utf8'));
    } finally { signal.removeEventListener('abort', abort); reader.releaseLock(); }
  }
  // Small transport fixtures may expose json() only; production Fetch uses the
  // bounded stream reader above and never buffers an unbounded response.
  const payload = await response.json();
  if (Buffer.byteLength(JSON.stringify(payload)) > limit) throw failure('RESPONSE_TOO_LARGE', 'OpenAPI response exceeded the size limit');
  return payload;
}
export async function requestOpenAPI(input, deps = {}) {
  if (input.environment && input.environment !== 'online') throw failure('INVALID_ENVIRONMENT', 'Only online is supported', { write_occurred: false });
  const signal = AbortSignal.any([deps.signal, commandSignal(), AbortSignal.timeout(deps.timeoutMs || 15000)].filter(Boolean));
  const readOnly = input.readOnly === true;
  const abortCode = () => signal.reason?.name === 'TimeoutError' ? 'REQUEST_TIMEOUT' : 'ABORTED';
  for (let attempt = 0; attempt < 2; attempt++) {
    if (signal.aborted) throw failure(abortCode(), 'OpenAPI request interrupted', { write_occurred: false });
    let credentials;
    try { credentials = await (deps.resolveCredentials || resolveCredentials)({ ...input, forceRefresh: attempt > 0 }, { ...deps, forceRefresh: attempt > 0, signal }); }
    catch (error) {
      if (signal.aborted) throw failure(abortCode(), 'Credential request interrupted', {write_occurred:false});
      if (['TASK_BINDING_MISMATCH', 'NETWORK_ERROR', 'AUTH_EXCHANGE_FAILED', 'ABORT_ERR', 'ABORTED'].includes(error?.code)) throw error;
      const code = ['SETUP_PENDING', 'AUTH_REQUIRED'].includes(error?.code) ? 'AUTH_REQUIRED' : 'OPERATION_FAILED';
      throw failure(code, 'Credentials unavailable', { write_occurred: false });
    }
    if (input.account_id && credentials.account_id !== input.account_id) throw taskBindingError();
    if (input.profile && credentials.profile !== input.profile) throw taskBindingError();
    observeAccount(credentials.account_id);
    const url = new URL(OPENAPI_ENDPOINT);
    url.searchParams.set('Action', input.action); url.searchParams.set('Version', input.version);
    for (const [key, value] of Object.entries(input.query || {})) url.searchParams.set(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
    const body = input.method === 'GET' ? '' : JSON.stringify(input.body || {});
    const headers = signVolcRequest({ method: input.method, url: url.href, body, ...credentials, region: 'cn-north-1', service: 'livesaas' });
    const userAgent = commandUserAgent();
    if (userAgent) headers['User-Agent'] = userAgent;
    let response, data;
    try {
      signal.throwIfAborted();
      response = await (deps.fetch || deps.fetchImpl || globalThis.fetch)(url.href, { method: input.method, headers, body: body || undefined, redirect: 'error', signal });
      data = await payloadOf(response, deps.maxResponseBytes || 8 * 1024 * 1024, signal);
    } catch (error) {
      const code = readOnly ? signal.aborted ? abortCode() : error.code === 'RESPONSE_TOO_LARGE' ? 'RESPONSE_TOO_LARGE' : response ? 'INVALID_RESPONSE' : 'NETWORK_ERROR' : 'WRITE_RESULT_UNKNOWN';
      throw failure(code, readOnly ? 'OpenAPI response unavailable' : 'Write result is unknown; inspect task state before retrying', { write_occurred: readOnly ? false : null });
    }
    const remote = data?.ResponseMetadata?.Error;
    if (!response.ok || remote) {
      const remoteCode = SAFE_CODES.has(remote?.Code) ? remote.Code : 'OPENAPI_ERROR';
      if (readOnly && attempt === 0 && AUTH_ERRORS.has(remoteCode)) continue;
      throw failure(remoteCode, 'OpenAPI request rejected', { httpStatus: response.status, http_status: response.status, request_id: typeof data?.ResponseMetadata?.RequestId === 'string' && /^[a-zA-Z0-9_-]{1,128}$/.test(data.ResponseMetadata.RequestId) ? data.ResponseMetadata.RequestId : undefined, write_occurred: readOnly || response.status < 500 ? false : null });
    }
    return data;
  }
}
