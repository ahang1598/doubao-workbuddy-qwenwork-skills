import { requireOriginalTaskContext, assertTaskAccount } from './task-binding.mjs';
import { requestOpenAPI } from './openapi-client.mjs';
import { resolveProfileBinding } from './auth.mjs';
const AUDIT_SOURCES = new Set(['ALL', 'MACHINE', 'HUMAN']);
const SCREENSHOT_CACHE_MS = 30_000;
const screenshotCache = new Map();
const screenshotRefreshes = new Map();

// ListLiveAudit 的记录状态域；不要与 GetReport.FinalMachineStatus 的状态域混用。
// 集中维护既有适配映射。新增/未知状态只保留代码，不自动扩大机审命中集合。
const LIVE_AUDIT_STATUS = Object.freeze({
  MACHINE_APPROVED: 1,
  MACHINE_REJECTED: 2,
  HUMAN_APPROVED: 3,
  HUMAN_REJECTED: 4,
  WARNING: 5,
});
const LIVE_AUDIT_STATUS_LABELS = new Map([
  [LIVE_AUDIT_STATUS.MACHINE_APPROVED, '机审通过'],
  [LIVE_AUDIT_STATUS.MACHINE_REJECTED, '机审不通过'],
  [LIVE_AUDIT_STATUS.HUMAN_APPROVED, '人审通过'],
  [LIVE_AUDIT_STATUS.HUMAN_REJECTED, '人审不通过'],
  [LIVE_AUDIT_STATUS.WARNING, '警告'],
]);
const LIVE_AUDIT_SOURCE_CATEGORY = new Map([
  [1, 'machine'], [2, 'machine'],
  [3, 'human'], [4, 'human'], [5, 'human'], [6, 'human'],
]);

function enumCode(value) {
  if (!['number', 'string'].includes(typeof value) || String(value).trim() === '') return null;
  return integer(value);
}

function positiveInteger(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0) throw Object.assign(new Error(`${name} must be a positive integer`), { code: 'INVALID_INPUT' });
  return parsed;
}

function safeText(value, maxLength = 4_000) {
  if (value === undefined || value === null) return null;
  const text = `${value}`.trim().replace(/\b(?:https?|rtmps?|wss?):\/\/[^\s,}\]]+/gi, '[redacted-url]');
  return text ? text.slice(0, maxLength) : null;
}

function integer(value) {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

function taskMetadata(value) {
  if (!value) return {};
  try {
    const parsed = typeof value === 'string' ? JSON.parse(value) : value;
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function auditSource(value) {
  return LIVE_AUDIT_SOURCE_CATEGORY.get(enumCode(value)) || 'unknown';
}

function auditStatus(value) {
  return LIVE_AUDIT_STATUS_LABELS.get(enumCode(value)) || '待判定';
}

function machineResult(source, status) {
  if (source === 'human') return 'not_applicable';
  if (source !== 'machine') return 'unknown';
  if (status === LIVE_AUDIT_STATUS.MACHINE_REJECTED) return 'hit';
  if (status === LIVE_AUDIT_STATUS.MACHINE_APPROVED) return 'clear';
  return 'unknown';
}

function reviewLabel(status) {
  if (status === null || status === 0 || status === LIVE_AUDIT_STATUS.WARNING) return null;
  if (status === LIVE_AUDIT_STATUS.HUMAN_APPROVED || status === LIVE_AUDIT_STATUS.HUMAN_REJECTED) return auditStatus(status);
  return `未知复核状态（${status}）`;
}

function timeText(value) {
  if (typeof value === 'string' && /^\d{1,3}:\d{2}:\d{2}$/.test(value)) return value;
  const milliseconds = integer(value);
  if (milliseconds === null || milliseconds < 0) return null;
  const seconds = Math.floor(milliseconds / 1_000);
  return [Math.floor(seconds / 3_600), Math.floor((seconds % 3_600) / 60), seconds % 60]
    .map((part) => `${part}`.padStart(2, '0')).join(':');
}

function imageUrl(value) {
  if (!value || typeof value !== 'object') return null;
  const seen = new Set();
  const visit = (node, depth = 0, imageContext = false) => {
    if (!node || typeof node !== 'object' || depth > 8 || seen.has(node)) return null;
    seen.add(node);
    for (const [key, child] of Object.entries(node)) {
      const contextual = imageContext || /image|picture|screenshot|snapshot|frame|cover/i.test(key);
      if (contextual && typeof child === 'string') {
        try {
          const parsed = new URL(child);
          if (parsed.protocol === 'https:') return parsed.toString();
        } catch {}
      }
      const found = visit(child, depth + 1, contextual);
      if (found) return found;
    }
    return null;
  };
  return visit(value);
}

function collectSamples(value) {
  const samples = [];
  const seen = new Set();
  const visit = (node, depth = 0) => {
    if (!node || typeof node !== 'object' || depth > 10 || seen.has(node) || samples.length >= 20) return;
    seen.add(node);
    if (!Array.isArray(node) && (node.Text !== undefined || node.Reason !== undefined)
      && (node.StartTime !== undefined || node.AbsoluteStartTime !== undefined || node.AuditID !== undefined)) {
      samples.push({
        time: timeText(node.StartTime),
        text: safeText(node.Text, 2_000),
        reason: safeText(node.Reason, 500),
        status: auditStatus(node.AuditStatus),
        image_url: imageUrl(node),
      });
    }
    for (const child of Object.values(node)) visit(child, depth + 1);
  };
  visit(value);
  return samples;
}

export function normalizeAuditRecord(record) {
  const detail = record?.Detail ?? {};
  const status = enumCode(record?.AuditStatus);
  const reviewStatus = enumCode(record?.ReviewAuditStatus);
  const source = auditSource(record?.AuditSource);
  return {
    id: integer(record?.ID),
    rule_id: integer(record?.RuleID ?? detail?.Id),
    rule_name: safeText(record?.RuleName ?? detail?.Name, 200) || '质检规则',
    source,
    source_code: enumCode(record?.AuditSource),
    status: auditStatus(status),
    status_code: status,
    // 原始机审结论、后续复核、处置三者独立；复核不会改写机审命中事实。
    machine_result: machineResult(source, status),
    review_status_code: reviewStatus,
    review_label: reviewLabel(reviewStatus),
    disposition_label: status === LIVE_AUDIT_STATUS.WARNING || reviewStatus === LIVE_AUDIT_STATUS.WARNING ? '警告' : null,
    audit_comment: safeText(record?.AuditComment, 500),
    auditor: safeText(record?.Auditor, 100),
    mark_time_ms: integer(record?.MarkTime),
    created_at: safeText(record?.CreatedTime, 100),
    updated_at: safeText(record?.UpdatedTime, 100),
    samples: collectSamples(detail),
  };
}

export function normalizeAuditResponse(payload) {
  const result = payload?.Result ?? {};
  const records = (Array.isArray(result.Data) ? result.Data : [])
    .map(normalizeAuditRecord).filter((item) => item.id !== null)
    .sort((left, right) => right.id - left.id);
  return {
    counts: {
      all: integer(result.Total) ?? records.length,
      machine: integer(result.MachineTotal) ?? records.filter((item) => item.source === 'machine').length,
      human: integer(result.HumanTotal) ?? records.filter((item) => item.source === 'human').length,
    },
    records,
  };
}

function attachScreenshotEvidence(audits, payload) {
  const shots = (Array.isArray(payload?.Result?.Data) ? payload.Result.Data : [])
    .map((item) => ({ second: integer(item.ScreenshotTime), url: imageUrl({ ScreenshotUrl: item.Url }) }))
    .filter((item) => item.second !== null && item.url);
  if (!shots.length) return audits;
  for (const record of audits.records) {
    for (const sample of record.samples || []) {
      if (sample.image_url || !sample.time) continue;
      const parts = sample.time.split(':').map(Number);
      const second = parts[0] * 3600 + parts[1] * 60 + parts[2];
      const nearest = shots.reduce((best, shot) => !best || Math.abs(shot.second - second) < Math.abs(best.second - second) ? shot : best, null);
      if (nearest && Math.abs(nearest.second - second) <= 3) sample.image_url = nearest.url;
    }
  }
  return audits;
}

export function normalizeTaskResponse(payload, fallback = {}) {
  const result = payload?.Result ?? {};
  const status = integer(result.Status ?? fallback.status);
  const scenarioId = integer(result.ScenarioId ?? fallback.scenarioId);
  const metadata = taskMetadata(result.Extra);
  return {
    id: integer(result.TaskId ?? fallback.taskId),
    name: safeText(result.TaskName ?? fallback.taskName, 200) || '直播质检任务',
    project_name: safeText(result.ProjectName ?? fallback.projectName, 100),
    scenario_id: scenarioId,
    scenario_name: safeText(result.ScenarioName ?? fallback.scenarioName ?? metadata.scenario_name, 100),
    account_name: safeText(metadata.account_name ?? fallback.accountName, 100),
    status,
    status_text: ({ 1: '等待检测', 2: '检测中', 3: '检测已完成', 4: '检测已完成', 5: '检测失败' })[status] || '状态同步中',
    created_at: integer(result.CreatedTime),
    updated_at: integer(result.UpdatedTime),
  };
}


async function clientFor(input) {
  requireOriginalTaskContext({ ...input, project_name: input.projectName, task_id: input.taskId });
  const binding = await input.resolveBinding({ profile: input.profile, environment: input.environment, account_id: input.account_id }, { env: input.env });
  assertTaskAccount(input, binding);
  return { binding, request: (request) => input.request({ ...request, ...binding, readOnly: true }, { env: input.env, signal: input.signal }) };
}

export async function fetchSingleTaskSnapshot({
  projectName, taskId, taskName = null, scenarioId = null, scenarioName = null,
  source = 'MACHINE', limit = 20, includeAudits = true, profile, account_id,
  environment, env = process.env, signal,
  request = requestOpenAPI, resolveBinding = resolveProfileBinding,
}) {
  requireOriginalTaskContext({ environment, profile, account_id, project_name: projectName, task_id: taskId });
  const input = { projectName: String(projectName || '').trim(), taskId: positiveInteger(taskId, 'taskId'),
    taskName, scenarioId, scenarioName, source: String(source).toUpperCase(), limit: positiveInteger(limit, 'limit') };
  if (!input.projectName || !AUDIT_SOURCES.has(input.source) || input.limit > 100 || environment !== 'online') {
    throw Object.assign(new Error('Invalid snapshot target'), { code: 'INVALID_INPUT' });
  }
  const client = await clientFor({ profile, account_id, environment, projectName, taskId, env, signal, request, resolveBinding });
  const task = await client.request({ method: 'GET', action: 'GetTask', version: '2024-08-01', query: { ProjectName: input.projectName, TaskId: input.taskId } });
  if (String(task?.Result?.TaskId) !== String(input.taskId) || task?.Result?.ProjectName !== input.projectName) {
    throw Object.assign(new Error('Task does not match the requested context'), { code: 'TASK_BINDING_MISMATCH' });
  }
  const audits = includeAudits ? await client.request({ method: 'GET', action: 'ListLiveAudit', version: '2023-01-01',
    query: { ProjectName: input.projectName, TaskID: input.taskId, Limit: input.limit, AuditSourceCategory: input.source, IncludeStats: true } }) : { Result: { Data: [] } };
  const key = JSON.stringify([client.binding.profile, client.binding.account_id, environment, input.projectName, input.taskId]);
  const cached = screenshotCache.get(key);
  if (includeAudits && (!cached || Date.now() - cached.updatedAt >= SCREENSHOT_CACHE_MS) && !screenshotRefreshes.has(key)) {
    const refresh = client.request({ method: 'GET', action: 'ListLiveScreenshot', version: '2024-08-01',
      query: { ProjectName: input.projectName, TaskId: input.taskId, PageNumber: 1, PageSize: 1000 } })
      .then(data => screenshotCache.set(key, { data, updatedAt: Date.now() }))
      .catch(() => {}).finally(() => screenshotRefreshes.delete(key));
    screenshotRefreshes.set(key, refresh);
  }
  return { task: normalizeTaskResponse(task, input),
    ...attachScreenshotEvidence(normalizeAuditResponse(audits), includeAudits ? cached?.data : null), refreshed_at: new Date().toISOString() };
}

export async function fetchSingleTaskReport({ projectName, taskId, profile, account_id, environment,
  env = process.env, signal, request = requestOpenAPI, resolveBinding = resolveProfileBinding }) {
  requireOriginalTaskContext({ environment, profile, account_id, project_name: projectName, task_id: taskId });
  if (!String(projectName || '').trim() || environment !== 'online') throw Object.assign(new Error('Invalid report target'), { code: 'INVALID_INPUT' });
  const client = await clientFor({ profile, account_id, environment, projectName, taskId, env, signal, request, resolveBinding });
  const report = await client.request({ method: 'GET', action: 'GetReport', version: '2024-08-01',
    query: { ProjectName: projectName, TaskId: positiveInteger(taskId, 'taskId') } });
  if (!report?.Result?.TaskResult) throw Object.assign(new Error('直播质检报告仍在生成中'), { code: 'REPORT_NOT_READY' });
  return report;
}

export async function openSingleTaskReport({ projectName, taskId, profile, account_id, environment, env = process.env, fetchReport = fetchSingleTaskReport }) {
  const { remoteReport } = await import('./remote-dashboard.mjs');
  const target = remoteReport({ kind: 'live', environment, projectName, taskId });
  await fetchReport({ projectName, taskId, profile, account_id, environment, env });
  return { url: target.report_url };
}
