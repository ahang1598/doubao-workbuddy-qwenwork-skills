import { requireOriginalTaskContext } from './task-binding.mjs';
import { commandUserAgent, commandSignal } from './telemetry.mjs';
import { open, rm } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { basename, extname, resolve } from 'node:path';
import { signVolcRequest } from './upload-signer.mjs';
import { MAX_REPORT_BYTES, parseReviewDocument, readReviewFile, reportDigest, validateProjectName, validateTaskId } from './review-document.mjs';

function fail(code, message, details = {}) {
  return Object.assign(new Error(message), { code, stage: 'report_service', retryable: false, ...details });
}
function identity(input) {
  return { task_id: validateTaskId(input.task_id), project_name: validateProjectName(input.project_name) };
}
function reportUrl(value) {
  try {
    const url = new URL(value);
    if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) {
      // Reuse the quality-report path recognized by the deployed console shell.
      // Other service-provided viewers retain their original URL and environment.
      if (url.hostname === 'console.volcengine.com'
        && /^\/livesaas\/liveinspect\/projectManagement\/[^/]+\/taskManagement\/review\/view\/[^/]+\/?$/.test(url.pathname)) {
        url.pathname = url.pathname.replace('/taskManagement/review/view/', '/taskManagement/report/view/');
        url.searchParams.set('reportType', 'review');
        return url.href;
      }
      return value;
    }
  } catch {}
  return null;
}
function safeCode(value) { return typeof value === 'string' && /^[A-Za-z0-9_.-]{1,160}$/.test(value) ? value : undefined; }

// Persist only diagnostic identifiers, never upstream messages, bodies or credentials.
export function reportErrorDetails(error = {}) {
  const details = {};
  for (const key of ['api_code', 'request_id', 'verification_result']) {
    if (safeCode(error[key])) details[key] = error[key];
  }
  if (Number.isInteger(error.http_status) && error.http_status >= 100 && error.http_status <= 599) details.http_status = error.http_status;
  if (error.write_occurred === false || error.write_occurred === null) details.write_occurred = error.write_occurred;
  if (['not_started', 'unknown'].includes(error.mutation_state)) details.mutation_state = error.mutation_state;
  if (['check_report_access', 'verify_report'].includes(error.next_action)) details.next_action = error.next_action;
  if (error.verification_error) {
    // Do not recurse into arbitrary nested error objects.
    const { http_status, api_code, request_id } = error.verification_error;
    details.verification_error = reportErrorDetails({ http_status, api_code, request_id });
  }
  return details;
}

async function requestReport(input, runtime, dependencies, { action, body, contentType, environment }) {
  requireOriginalTaskContext(input);
  const cred = await runtime.resolveUploadCredentials({ ...input, environment }, dependencies);
  const url = new URL(runtime.reportUploadEndpoint(environment));
  url.searchParams.set('Action', action);
  const isUpload = action === runtime.REPORT_UPLOAD_CONFIG.action;
  if (!isUpload) {
    body = Buffer.from(JSON.stringify({ TaskId: input.task_id }));
    contentType = 'application/json';
  }
  const headers = signVolcRequest({
    method: 'POST', url: url.href, headers: body ? { 'Content-Type': contentType } : {}, body: body || '',
    accessKeyId: cred.accessKeyId, secretAccessKey: cred.secretAccessKey, sessionToken: cred.sessionToken,
    region: runtime.REPORT_UPLOAD_CONFIG.region, service: runtime.REPORT_UPLOAD_CONFIG.services[environment],
  });
  const ua = commandUserAgent();
  if (ua) headers['User-Agent'] = ua;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), isUpload ? 90000 : 30000);
  try {
    const response = await (dependencies.fetchImpl || globalThis.fetch)(url.href, {
      method: 'POST', headers, ...(body ? { body } : {}), signal: AbortSignal.any([controller.signal, commandSignal()].filter(Boolean)), redirect: 'error',
    });
    const chunks = []; let size = 0;
    for await (const chunk of response.body || []) {
      size += chunk.length;
      if (size > MAX_REPORT_BYTES + 65536) { controller.abort(); throw fail(isUpload ? 'UPLOAD_RESULT_UNKNOWN' : 'REPORT_FETCH_FAILED', 'Report service response exceeds the size limit'); }
      chunks.push(Buffer.from(chunk));
    }
    let payload;
    try { payload = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch {}
    const details = { http_status: response.status, request_id: safeCode(payload?.ResponseMetadata?.RequestId), api_code: safeCode(payload?.ResponseMetadata?.Error?.Code) };
    // A gateway timeout or server error may arrive after the database commit.
    if (isUpload && (response.status >= 500 || response.status === 408)) {
      throw fail('UPLOAD_RESULT_UNKNOWN', 'Server could not confirm the write; verify server state before retrying', details);
    }
    if (!response.ok || payload?.ResponseMetadata?.Error) {
      const accessDenied = [401, 403].includes(response.status)
        || ['AccessDenied', 'Forbidden', 'Unauthorized'].includes(details.api_code);
      const code = isUpload ? 'REPORT_UPLOAD_REJECTED'
        : details.api_code === 'ReportNotFound' ? 'REPORT_NOT_FOUND'
          : accessDenied ? 'REPORT_ACCESS_DENIED' : 'REPORT_FETCH_FAILED';
      throw fail(code, 'Report service rejected the request; the source JSON is preserved', {
        ...details,
        ...(accessDenied ? { next_action: 'check_report_access' } : {}),
        // Only an explicit upload authentication/authorization rejection proves
        // this write was blocked. A failed readback says nothing about a write.
        ...(isUpload && accessDenied ? { write_occurred: false, mutation_state: 'not_started' } : {}),
      });
    }
    if (!/^application\/json(?:\s*;|$)/i.test(response.headers.get('content-type') || '') || !payload) {
      throw fail(isUpload ? 'UPLOAD_RESULT_UNKNOWN' : 'REPORT_FETCH_FAILED', 'Report service did not return JSON; verify server state before retrying', details);
    }
    return { result: payload.Result, ...details };
  } catch (error) {
    if (error.stage) throw error;
    throw fail(isUpload ? 'UPLOAD_RESULT_UNKNOWN' : 'REPORT_FETCH_FAILED', 'Report request failed or timed out; verify server state before retrying');
  } finally { clearTimeout(timer); }
}

export async function uploadReviewJson(rawInput, runtime, dependencies = {}) {
  if (!rawInput || typeof rawInput !== 'object' || Array.isArray(rawInput)
    || Object.keys(rawInput).some(key => !runtime.REPORT_UPLOAD_FIELDS.includes(key))) throw fail('INVALID_INPUT', 'Unknown upload input field');
  if (rawInput.dry_run !== undefined && typeof rawInput.dry_run !== 'boolean') throw fail('INVALID_INPUT', 'dry_run must be boolean');
  for (const key of ['room_name', 'profile']) if (rawInput[key] !== undefined && (typeof rawInput[key] !== 'string' || !rawInput[key].trim())) throw fail('INVALID_INPUT', `${key} must be a non-empty string`);
  const environment = runtime.resolveReportEnvironment(rawInput);
  const { report, bytes } = await readReviewFile(rawInput.file_path, rawInput);
  const input = { ...rawInput, ...identity(report.report_meta) };
  // Identifiers come from the complete document and are checked against any explicit upload target.
  // Send the exact bytes validated above, without rereading or reserializing the file.
  const boundary = `douyin-inspect-${randomUUID()}`;
  const filename = basename(rawInput.file_path).replace(/["\r\n\\]/g, '_');
  const fields = { taskId: input.task_id, projectName: input.project_name, task_name: input.room_name || report.live.title };
  const contentType = `multipart/form-data; boundary=${boundary}`;
  const body = Buffer.concat([
    ...Object.entries(fields).map(([name, value]) => Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`)),
    Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${filename}"\r\nContent-Type: application/json\r\n\r\n`),
    bytes, Buffer.from(`\r\n--${boundary}--\r\n`),
  ]);
  if (body.length > MAX_REPORT_BYTES) throw fail('INVALID_INPUT', 'Upload request exceeds 20 MiB');
  const summary = { task_id: input.task_id, project_name: input.project_name, environment, schema_version: 1, report_hash: reportDigest(report) };
  if (input.dry_run) return { status: 'dry_run', ...summary, overwrites_task_report: true, action: 'UploadReport', version: runtime.REPORT_UPLOAD_CONFIG.version, file_name: filename, file_bytes: bytes.length, bytes: body.length };
  // Pin the resolved account for this upload and its readback, even if the
  // host changes its default profile while the request is in flight.
  const resolveCredentials = runtime.resolveUploadCredentials;
  let credentials;
  runtime = { ...runtime, resolveUploadCredentials: (...args) => (credentials ??= Promise.resolve(resolveCredentials(...args))) };
  try {
    const { result, request_id } = await requestReport(input, runtime, dependencies, { action: 'UploadReport', body, contentType, environment });
    const report_url = reportUrl(result?.URL);
    if (result?.Status !== true || String(result.TaskID) !== input.task_id || result.ProjectName !== input.project_name || !report_url) {
      throw fail('UPLOAD_RESULT_UNKNOWN', 'UploadReport did not confirm persistence of this task', { request_id });
    }
    return { status: 'saved', ...summary, verification: 'response', report_url, next_action: 'deliver_report', updated_at: result.UpdatedAt ?? null, request_id };
  } catch (error) {
    if (error.code !== 'UPLOAD_RESULT_UNKNOWN') throw error;
    return verifyReviewJson(input, summary.report_hash, runtime, dependencies, error);
  }
}

// A readback is never permission to replay a write. Keep the original failure
// and only expose a small, safe verification result when persistence is unknown.
export async function verifyReviewJson(input, expectedHash, runtime, dependencies = {}, originalError) {
  const error = originalError || fail('UPLOAD_RESULT_UNKNOWN', 'Saved report has not been verified');
  Object.assign(error, { report_hash: expectedHash, write_occurred: null, mutation_state: 'unknown', next_action: 'verify_report' });
  try {
    const { report, ...saved } = await fetchReviewJson({
      task_id: input.task_id, project_name: input.project_name, environment: runtime.resolveReportEnvironment(input),
      ...(input.profile ? { profile: input.profile } : {}),
      ...(input.account_id ? { account_id: input.account_id } : {}),
    }, runtime, dependencies);
    if (saved.report_hash === expectedHash) return {
      ...saved, status: 'saved', schema_version: 1, verification: 'readback',
      next_action: saved.report_url ? 'deliver_report' : 'fetch_report_link',
    };
    error.verification_result = 'hash_mismatch';
  } catch (cause) {
    error.verification_result = safeCode(cause.code) || 'REPORT_FETCH_FAILED';
    error.verification_error = reportErrorDetails(cause);
  }
  throw error;
}

export async function fetchReviewJson(rawInput, runtime, dependencies = {}) {
  const environment = runtime.resolveReportEnvironment(rawInput);
  const input = { ...rawInput, ...identity(rawInput) };
  if (input.dry_run) return { status: 'dry_run', ...identity(input), environment, action: runtime.REPORT_UPLOAD_CONFIG.fetchAction, version: runtime.REPORT_UPLOAD_CONFIG.version };
  const { result, request_id } = await requestReport(input, runtime, dependencies, { action: runtime.REPORT_UPLOAD_CONFIG.fetchAction, environment });
  if (!result?.ReportData) throw fail('REPORT_FETCH_FAILED', 'GetReportDataForCLI did not return a saved report', { request_id });
  const report = parseReviewDocument(Buffer.from(JSON.stringify(result.ReportData)), input);
  return { ...identity(input), environment, report, report_hash: reportDigest(report), report_url: reportUrl(result.URL), request_id };
}

export async function saveReviewJson(input, runtime, dependencies = {}) {
  const environment = runtime.resolveReportEnvironment(input);
  const target = identity(input);
  if (typeof input.output !== 'string' || extname(input.output).toLowerCase() !== '.json') throw fail('INVALID_INPUT', 'output must be a new JSON path');
  const path = resolve(input.output);
  if (input.dry_run) return { status: 'dry_run', ...target, environment, action: runtime.REPORT_UPLOAD_CONFIG.fetchAction, report_file: path };
  requireOriginalTaskContext(input);
  let handle;
  try { handle = await open(path, 'wx', 0o600); } catch { throw fail('INVALID_INPUT', 'Cannot create output file; choose a new writable JSON path'); }
  let success = false;
  try {
    const result = await fetchReviewJson(input, runtime, dependencies);
    await handle.writeFile(`${JSON.stringify(result.report)}\n`); success = true;
    return { status: 'downloaded', ...target, environment, report_file: path, report_hash: result.report_hash, report_url: result.report_url };
  } finally {
    await handle.close();
    if (!success) await rm(path, { force: true });
  }
}
