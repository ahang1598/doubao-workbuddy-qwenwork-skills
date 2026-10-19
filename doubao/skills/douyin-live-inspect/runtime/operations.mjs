import { observeOperation } from './formal-workflow.mjs';
import { runCommand, isPreview } from './telemetry.mjs';
import { requireOriginalTaskContext, assertTaskAccount, taskBindingError } from './task-binding.mjs';
import { readFileSync } from 'node:fs';
import { requestOpenAPI, OPENAPI_ENDPOINT } from './openapi-client.mjs';
import { createConfirmationStore } from './confirmation-store.mjs';
import { getAuthStatus, resolveProfileBinding } from './auth.mjs';
const contracts = JSON.parse(readFileSync(new URL('./operation-contracts.json', import.meta.url), 'utf8'));
const key = value => value.replace(/[-_]/g, '').toLowerCase();
const executionSchema = { profile: 'string', account_id: 'string', environment: { const: 'online' }, dry_run: 'boolean', plan: 'boolean', confirm_token: 'string', mutuallyExclusive: ['dry_run', 'plan', 'confirm_token'] };
const controls = new Set(['profile', 'accountid', 'environment', 'env', 'dryrun', 'plan', 'confirmtoken', 'format']);
export function getOperationSchema(operation) {
  if (operation) return contracts[operation] ? { ...structuredClone(contracts[operation]), execution: { ...structuredClone(executionSchema), ...(contracts[operation].fields.some(f => /^TaskId$/i.test(f.field) && f.required) ? { requiredForExecution: ['environment', 'profile', 'account_id', 'project_name', 'task_id'] } : {}) } } : null;
  return { operations: structuredClone(contracts), execution: structuredClone(executionSchema), environment: 'online' };
}
function invalid(message) { throw Object.assign(new Error(message), { code: 'INVALID_INPUT', exitCode: 2 }); }
function normalizeValues(input, allowed) {
  const values = {};
  for (const [name, value] of Object.entries(input)) {
    const normalized = key(name);
    if (!allowed.has(normalized)) invalid('Unknown input parameter');
    if (Object.hasOwn(values, normalized)) invalid('Duplicate input parameter aliases');
    values[normalized] = value;
  }
  for (const field of ['plan', 'dryrun']) if (values[field] !== undefined && typeof values[field] !== 'boolean') invalid(`${field} must be boolean`);
  if ((values.environment ?? 'online') !== 'online' || (values.env ?? 'online') !== 'online') invalid('Only online is supported');
  if (values.profile !== undefined && (typeof values.profile !== 'string' || !values.profile.trim())) invalid('profile must be a nonempty string');
  if (values.accountid !== undefined && (typeof values.accountid !== 'string' || !values.accountid.trim())) invalid('account_id must be a nonempty string');
  if (values.confirmtoken !== undefined && typeof values.confirmtoken !== 'string') invalid('confirm_token must be a string');
  if ([values.plan === true, values.dryrun === true, values.confirmtoken !== undefined].filter(Boolean).length > 1) invalid('Conflicting execution controls');
  if (values.format !== undefined && values.format !== 'json') invalid('Only JSON format is supported');
  return values;
}
function numeric(value, field, integer = false) {
  if (!['number', 'string'].includes(typeof value) || (typeof value === 'string' && !value.trim())) invalid(`${field} must be numeric`);
  const result = Number(value);
  if (!Number.isFinite(result) || (integer && !Number.isSafeInteger(result))) invalid(`${field} must be numeric`);
  return result;
}
function normalize(contract, input) {
  const allowed = new Set(controls);
  for (const f of contract.fields) { allowed.add(key(f.field)); allowed.add(key(f.flag)); }
  for (const alias of Object.values(contract.aliases || {})) allowed.add(key(alias));
  const values = normalizeValues(input, allowed);
  for (const [name, value] of Object.entries(contract.fixedInput || {})) {
    if (values[key(name)] !== undefined && String(values[key(name)]) !== String(value)) invalid(`${name} is fixed for this operation`);
    values[key(name)] = value;
  }
  if (/^Create/.test(contract.action) && !values.taskname) values.taskname = `质检-${new Date().toISOString()}`;
  const query = {}, body = {};
  for (const f of contract.fields) {
    const alias = contract.aliases?.[f.flag.replace(/-([a-z])/g, (_, c) => c.toUpperCase())];
    const canonical = values[key(f.field)] ?? values[key(f.flag)];
    if (alias && canonical !== undefined && values[key(alias)] !== undefined) invalid('Duplicate input parameter aliases');
    let value = canonical ?? (alias ? values[key(alias)] : undefined);
    if (value === undefined || value === null || value === '') { if (f.required) invalid(`${f.field} is required`); continue; }
    const timeMode = Object.entries(contract.timeTransforms || {}).find(([name]) => key(name) === key(f.field))?.[1];
    if (timeMode) {
      let seconds;
      if (typeof value === 'number' || (typeof value === 'string' && /^-?\d+$/.test(value))) seconds = numeric(value, f.field, true);
      else if (typeof value === 'string') seconds = Math.floor(new Date(value).getTime() / 1000);
      if (!Number.isSafeInteger(seconds)) invalid(`${f.field} must be Unix seconds or ISO time`);
      const date = new Date(seconds * 1000);
      if (timeMode === 'day-start') date.setHours(0, 0, 0, 0);
      if (timeMode === 'day-end') date.setHours(23, 59, 59, 0);
      value = Math.floor(date.getTime() / 1000);
    }
    if (f.type === 'array') {
      if (typeof value === 'string') { try { value = JSON.parse(value); } catch { value = value.split(','); } }
      if (!Array.isArray(value)) value = [value];
      if (['number', 'integer'].includes(f.items?.type)) value = value.map(item => numeric(item, f.field, true));
      else if (f.items?.type && value.some(item => typeof item !== f.items.type)) invalid(`${f.field} has invalid items`);
      if (f.enum && value.some(item => !f.enum.some(choice => String(choice) === String(item)))) invalid(`${f.field} is outside the allowed values`);
    }
    if (f.type === 'boolean') { if (![true, false, 'true', 'false'].includes(value)) invalid(`${f.field} must be boolean`); value = value === true || value === 'true'; }
    if (['number', 'integer'].includes(f.type)) value = numeric(value, f.field, f.type === 'integer');
    if (f.type === 'string' && typeof value !== 'string') invalid(`${f.field} must be a string`);
    if (/^(TaskId|TaskID|ScenarioId|ActivityId|PageNumber|PageSize|Limit)$/.test(f.field) && (!Number.isSafeInteger(value) || value <= 0)) invalid(`${f.field} must be a positive safe integer`);
    if (f.enum && f.type !== 'array' && !f.enum.some(choice => String(choice) === String(value))) invalid(`${f.field} is outside the allowed values`);
    (f.location === 'query' ? query : body)[f.field] = value;
  }
  const combined = { ...query, ...body };
  if (combined.StartTime !== undefined && combined.EndTime !== undefined && combined.StartTime > combined.EndTime) invalid('StartTime must precede EndTime');
  if (combined.PageNumber > 1000) invalid('PageNumber exceeds the maximum');
  if (contract.pageSizeMax && combined.PageSize > contract.pageSizeMax) invalid('PageSize exceeds the maximum');
  if (combined.Limit > 100) invalid('Limit exceeds the maximum');
  for (const name of ['TaskIds', 'TagIds']) {
    if (combined[name]?.some(value => !Number.isSafeInteger(value) || value <= 0)) invalid(`${name} requires positive safe integers`);
    if (combined[name]?.length > (name === 'TaskIds' ? 100 : 10)) invalid(`${name} exceeds the maximum`);
  }
  for (const name of ['MachineStatus', 'ManualStatus']) if (combined[name]?.some(value => ![1, 2].includes(value))) invalid(`${name} is outside the allowed values`);
  if (contract.action === 'CreateVideoTask') {
    if (body.SourceType !== 4 || body.TaskItems.length !== 1) invalid('Video inspection requires SourceType 4 and exactly one TaskItems entry');
    const item = body.TaskItems[0];
    if (!item || typeof item !== 'object' || Array.isArray(item) || Object.keys(item).some(name => name !== 'Url')) invalid('TaskItems must contain an object');
    let url; try { url = new URL(item.Url); } catch { invalid('TaskItems requires an HTTP(S) URL'); }
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) invalid('TaskItems requires an HTTP(S) URL');
  }
  if (contract.action === 'CreateTask' && (!body.LivePullURL || body.ActivityId !== undefined)) invalid('Live inspection requires LivePullURL and does not accept ActivityId');
  return { query, body, values };
}
function safeFailure(error) {
  const messages = { REQUEST_TIMEOUT: 'OpenAPI request timed out', SETUP_PENDING: 'Authentication required', AUTH_EXCHANGE_FAILED: 'Authentication refresh failed', ORIGINAL_TASK_CONTEXT_REQUIRED: 'Original task identity is required', TASK_BINDING_MISMATCH: 'Original task identity does not match', AUTH_REQUIRED: 'Authentication required', INVALID_CONFIRMATION: 'Confirmation is expired, consumed, or does not match this request', WRITE_RESULT_UNKNOWN: 'Write result is unknown; inspect task state before retrying', NETWORK_ERROR: 'OpenAPI request failed', OPENAPI_ERROR: 'OpenAPI request rejected', INVALID_RESPONSE: 'Invalid OpenAPI response', INVALID_ENVIRONMENT: 'Only online is supported' };
  const remoteCodes = new Set(['ReportNotFoundError', 'ReportNotFound', 'Throttling', 'ThrottlingException', 'TooManyRequests', 'AccessDenied', 'AccessDenyError', 'Forbidden', 'Unauthorized', 'InvalidParameter', 'InvalidParameterValue', 'ResourceNotFound', 'TaskNotFound', 'ExpiredToken', 'ExpiredTokenException', 'InvalidSecurityToken', 'InvalidToken', 'TokenExpired', 'STSExpired', 'ABORTED', 'ABORT_ERR', 'RESPONSE_TOO_LARGE']);
  const code = ['ENOMEM', 'ERR_WORKER_OUT_OF_MEMORY', 'OUT_OF_MEMORY'].includes(error.code) ? 'OUT_OF_MEMORY' : remoteCodes.has(error.code) ? error.code : error.code === 'INVALID_INPUT' ? 'INVALID_INPUT' : Object.hasOwn(messages, error.code) ? error.code : 'OPERATION_FAILED';
  return { ok: false, code: code === 'INVALID_INPUT' ? 2 : 1, error: { code, message: code === 'INVALID_INPUT' ? error.message : messages[code] || 'Operation failed', subtype: code, ...(typeof error.request_id === 'string' && /^[a-zA-Z0-9_-]{1,128}$/.test(error.request_id) ? {request_id:error.request_id} : {}), write_occurred: error.write_occurred === null || code === 'WRITE_RESULT_UNKNOWN' ? null : false, ...(Number.isInteger(error.http_status ?? error.httpStatus) ? { http_status: error.http_status ?? error.httpStatus } : {}) } };
}
function redactPreview(value) {
  if (Array.isArray(value)) return value.map(redactPreview);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([name, child]) => [name, redactPreview(child)]));
  if (typeof value === 'string') return value.replace(/\b(?:https?|rtmps?|wss?):\/\/[^\s"'<>]+/gi, '[redacted-url]');
  return value;
}
export async function executeOperation(operation, input = {}, deps = {}) {
  return runCommand(operation, async () => {
    const result = await performOperation(operation, input, deps);
    if(!isPreview(input, contracts[operation]?.requiresConfirmation)) {
      const normalized=Object.fromEntries(Object.entries(input).map(([k,v])=>[key(k),v]));
      await observeOperation(operation,{profile:normalized.profile,account_id:normalized.accountid,project_name:normalized.projectname,task_id:normalized.taskid},result,{env:deps.env||process.env});
    }
    return result;
  }, {
    skip:isPreview(input, contracts[operation]?.requiresConfirmation), env:deps.env,
  });
}
async function performOperation(operation, input = {}, deps = {}) {
  try {
    if (!input || typeof input !== 'object' || Array.isArray(input)) invalid('Input must be an object');
    const contract = contracts[operation]; if (!contract) invalid('Unknown operation');
    const { query, body, values } = normalize(contract, input);
    const taskSpecific = contract.fields.some(f => /^TaskId$/i.test(f.field) && f.required);
    const authInput = { profile: values.profile?.trim(), account_id: values.accountid, environment: values.environment ?? values.env };
    const target = { action: contract.action, version: contract.version, method: contract.method, query, body, profile: values.profile, account_id: values.accountid ?? null, environment: 'online' };
    if (!contract.requiresConfirmation && (values.plan || values.confirmtoken)) invalid('Confirmation controls apply only to task-end operations');
    if (values.dryrun) return { ok: true, code: 0, data: { network_request: false, dry_run: true, risk: { requires_confirmation: !!contract.requiresConfirmation }, target: redactPreview(target) } };
    if (taskSpecific) requireOriginalTaskContext({ ...authInput, project_name: values.projectname, task_id: values.taskid });
    const binding = await (deps.resolveProfileBinding || resolveProfileBinding)(authInput, deps);
    if (taskSpecific) assertTaskAccount(authInput, binding);
    else if (authInput.account_id && binding.account_id !== authInput.account_id) throw taskBindingError();
    Object.assign(target, { profile: binding.profile, account_id: binding.account_id ?? null });
    if (contract.requiresConfirmation) {
      const confirmations = deps.confirmations || createConfirmationStore({ env: deps.env, ...deps.confirmationOptions });
      if (!values.confirmtoken || values.plan) { const confirmation = confirmations.issue(target); return { ok: false, code: 10, error: { subtype: 'confirmation_required', exitCode: 10, details: { confirmation } } }; }
      confirmations.consume(values.confirmtoken, target);
    } else if (values.plan || values.confirmtoken) invalid('Confirmation controls apply only to task-end operations');
    const raw = await (deps.requestOpenAPI || requestOpenAPI)({ ...target, readOnly: contract.readOnly }, deps);
    // Some read endpoints include identity; never consume evidence for another task.
    if (taskSpecific && contract.readOnly) {
      const result = raw?.Result;
      const id = result?.TaskId ?? result?.TaskID;
      if ((id !== undefined && String(id) !== String(query.TaskId ?? query.TaskID ?? body.TaskId))
        || (result?.ProjectName !== undefined && result.ProjectName !== values.projectname)) throw taskBindingError();
    }
    return { ok: true, code: 0, data: { response: { data: raw } }, meta: { environment: 'online', profile: binding.profile, account_id: binding.account_id } };
  } catch (error) { return safeFailure(error); }
}
export async function runOperationArgs(args, deps = {}) {
  try {
    const input = {}, path = [];
    for (let i = 0; i < args.length; i++) {
      const arg = args[i]; if (!arg.startsWith('--')) { path.push(arg); continue; }
      const name = arg.slice(2), boolean = ['plan', 'dry-run'].includes(name);
      const value = boolean ? true : args[++i]; if (value === undefined || (typeof value === 'string' && value.startsWith('--'))) invalid('Missing option value');
      const normalized = name.replace(/-/g, '_'); input[normalized] = Object.hasOwn(input, normalized) ? [].concat(input[normalized], value) : value;
    }
    if (['configure/get', 'auth/status'].includes(path.join('/'))) {
      const values = normalizeValues(input, controls);
      const authInput = { profile: values.profile, account_id: values.accountid, environment: 'online' };
      await (deps.resolveProfileBinding || resolveProfileBinding)(authInput, deps);
      const status = await (deps.getAuthStatus || getAuthStatus)(authInput, deps);
      if (authInput.account_id && status.account_id !== authInput.account_id) throw Object.assign(new Error(), { code: 'AUTH_REQUIRED' });
      const profile = { name: status.profile, mode: 'console-login', region: 'cn-north-1', service: 'livesaas', base_url: OPENAPI_ENDPOINT.replace(/\/$/, ''), baseUrl: OPENAPI_ENDPOINT.replace(/\/$/, ''), openapi_env: 'online', account_id: status.account_id };
      return { ok: true, code: 0, data: { status: status.status, refresh_available: status.refresh_available === true, account_id: status.account_id, profile, credentials: { source: 'standalone-profile' } }, meta: { environment: 'online' } };
    }
    const operation = path.length === 3 ? `${path[0]}/+${path[1]}-${path[2]}` : path.join('/');
    return executeOperation(operation, input, deps);
  } catch (error) { return safeFailure(error); }
}
