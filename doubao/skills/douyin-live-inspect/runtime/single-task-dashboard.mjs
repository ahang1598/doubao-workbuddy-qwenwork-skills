import { timingSafeEqual } from 'node:crypto';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { fetchSingleTaskSnapshot, openSingleTaskReport } from './audit-openapi.mjs';
import { readRegisteredReviewReport } from './ecommerce-review-report.mjs';
import { createTaskEndController } from './task-end.mjs';

const RUNTIME_DIR = dirname(fileURLToPath(import.meta.url));
const UI_ROOT = new URL('../ui/', import.meta.url);
const DEFAULT_IDLE_TIMEOUT_MS = 10 * 60 * 1_000;
const DEFAULT_REPORT_RETRY_DELAY_MS = 15_000;
const DEFAULT_REPORT_REUSE_MS = 9 * 60 * 1_000;

function supportsReviewReport(task) {
  return [9056, 9057, 9058].includes(Number(task?.scenario_id))
    || ['金融', '汽车', '电商'].includes(`${task?.scenario_name || ''}`.trim());
}

function tokenMatches(actual, expected) {
  const left = Buffer.from(`${actual || ''}`);
  const right = Buffer.from(`${expected || ''}`);
  return left.length === right.length && left.length > 0 && timingSafeEqual(left, right);
}

function safeError(error) {
  const messages = {
    TASK_FAILED: '质检任务执行失败，无法生成报告',
    TASK_NOT_FINISHED: '质检任务尚未结束',
    REPORT_LAUNCH_FAILED: '报告页面暂不可用',
  };
  return messages[error?.code] || '质检服务暂不可用，请稍后重试';
}

function reportPending(error) {
  const code = `${error?.code || ''}`.toUpperCase();
  const message = `${error?.message || ''}`;
  return code.includes('REPORTNOTFOUND')
    || code.includes('REPORT_NOT_FOUND')
    || code === 'REPORT_NOT_READY'
    || /报告.*(?:生成|不存在|未找到)|report.*(?:not\s*found|generat)/i.test(message);
}

function headers(contentType, length) {
  return {
    'content-type': contentType,
    'content-length': length,
    'cache-control': 'no-store',
    'referrer-policy': 'no-referrer',
    'x-content-type-options': 'nosniff',
    'x-frame-options': 'DENY',
    'content-security-policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'",
  };
}

function jsonResponse(response, status, value) {
  const body = Buffer.from(JSON.stringify(value));
  response.writeHead(status, headers('application/json; charset=utf-8', body.length));
  response.end(body);
}

async function assetResponse(response, filename, contentType) {
  const body = await readFile(new URL(filename, UI_ROOT));
  response.writeHead(200, headers(contentType, body.length));
  response.end(body);
}

export async function startSingleTaskDashboard({
  token, projectName, taskId, profile, account_id, environment, taskName = null, scenarioId = null, port = 0,
  idleTimeoutMs = DEFAULT_IDLE_TIMEOUT_MS, fetchSnapshot = fetchSingleTaskSnapshot,
  openReport = openSingleTaskReport, reportRetryDelayMs = DEFAULT_REPORT_RETRY_DELAY_MS,
  reportReuseMs = DEFAULT_REPORT_REUSE_MS, now = () => Date.now(), runEndCli,
}) {
  if (!token) throw new Error('dashboard token is required');
  let stopping = false;
  let requestCount = 0;
  let lastPresenceAt = Date.now();
  let snapshotInFlight = null;
  let lastSnapshot = null;
  let endRequestAccepted = false;
  const endOperation = createTaskEndController({
    projectName, taskId, profile, account_id, environment, runCli: runEndCli, now,
    onAccepted: () => { endRequestAccepted = true; },
  });
  let reportOpenInFlight = null;
  let reportLink = null;
  let reportRetryAt = 0;
  const evidenceUrls = new Map();

  const checkReport = async (url) => {
    try {
      const health = new URL(url);
      if (health.protocol !== 'http:' || health.hostname !== '127.0.0.1' || !health.searchParams.get('token')) return false;
      health.pathname = '/api/health';
      const response = await fetch(health, { signal: AbortSignal.timeout(3000), redirect: 'error' });
      return response.ok && (await response.json()).ok === true;
    } catch { return false; }
  };

  const snapshot = () => {
    snapshotInFlight ||= fetchSnapshot({ projectName, taskId, profile, account_id, environment, taskName, scenarioId, source: 'MACHINE', limit: 20,
      includeAudits: !endRequestAccepted && ![3, 4, 5].includes(Number(lastSnapshot?.task?.status)),
    })
      .then(async (value) => {
        endOperation.observe(value.task?.status);
        // Also discard an audit response that was already in flight at acceptance.
        if (endRequestAccepted || [3, 4, 5].includes(Number(lastSnapshot?.task?.status))) {
          value = { ...value, records: lastSnapshot?.records || [], counts: lastSnapshot?.counts || value.counts };
        }
        value.records = (value.records || []).map((record) => ({
          ...record,
          samples: (record.samples || []).map((sample, index) => {
            if (!sample.image_url) return sample;
            const evidenceId = `${record.id}-${index}`;
            evidenceUrls.set(evidenceId, sample.image_url);
            return { ...sample, image_url: undefined, evidence_id: evidenceId };
          }),
        }));
        while (evidenceUrls.size > 400) evidenceUrls.delete(evidenceUrls.keys().next().value);
        const reviewSupported = supportsReviewReport(value.task);
        let enriched = {
          ...value,
          end_request_accepted: endRequestAccepted,
          end_accepted_at: endOperation.view().end_accepted_at,
          review_report_supported: reviewSupported,
          review_report_url: reviewSupported
            ? value.review_report_url || ([3, 4].includes(value?.task?.status) ? await readRegisteredReviewReport(taskId) : null)
            : null,
        };
        lastSnapshot = enriched;
        if ([3, 4].includes(Number(value?.task?.status))) {
          enriched = {
            ...enriched,
            quality_report_url: reportLink?.url || null,
            quality_report_status: reportLink ? 'ready' : 'generating',
            review_report_supported: reviewSupported,
            review_report_status: enriched.review_report_url ? 'ready' : reviewSupported ? 'not_started' : 'not_supported',
          };
          lastSnapshot = enriched;
          // Task state must reach the browser immediately. Report generation is
          // independent and can take minutes, so probe it without blocking this
          // snapshot; the next refresh will publish the resulting report link.
          void openReportPage(enriched).catch(() => {});
        }
        return enriched;
      })
      .finally(() => { snapshotInFlight = null; });
    return snapshotInFlight;
  };

  const openReportPage = async (providedSnapshot = null) => {
    const current = providedSnapshot || lastSnapshot || await snapshot();
    const status = Number(current?.task?.status);
    if (status === 5) throw Object.assign(new Error('质检任务执行失败，无法生成报告'), { code: 'TASK_FAILED' });
    if (![3, 4].includes(status)) throw Object.assign(new Error('质检任务尚未结束'), { code: 'TASK_NOT_FINISHED' });
    const currentTime = now();
    if (reportLink && currentTime - reportLink.checked_at < reportReuseMs) {
      return { status: 'ready', report_url: reportLink.url };
    }
    if (currentTime < reportRetryAt) {
      return {
        status: 'generating', retry_at: new Date(reportRetryAt).toISOString(),
        retry_after_seconds: Math.max(1, Math.ceil((reportRetryAt - currentTime) / 1_000)),
      };
    }
    // Health checks and launches share one promise so concurrent refreshes cannot
    // create duplicate long-lived report processes after the reuse window.
    reportOpenInFlight ||= (async () => {
      if (reportLink && await checkReport(reportLink.url)) {
        reportLink.checked_at = now();
        return { url: reportLink.url };
      }
      reportLink = null;
      return openReport({ projectName, taskId, profile, account_id, environment });
    })()
      .then((launched) => {
        const url = launched?.url ?? launched?.report_url;
        if (!url) throw Object.assign(new Error('本地报告服务未返回访问地址'), { code: 'REPORT_LAUNCH_FAILED' });
        reportLink = { url, checked_at: now() };
        reportRetryAt = 0;
        return { status: 'ready', report_url: url };
      })
      .catch((error) => {
        if (!reportPending(error)) throw error;
        reportRetryAt = now() + reportRetryDelayMs;
        return {
          status: 'generating', retry_at: new Date(reportRetryAt).toISOString(),
          retry_after_seconds: Math.max(1, Math.ceil(reportRetryDelayMs / 1_000)),
        };
      })
      .finally(() => { reportOpenInFlight = null; });
    return reportOpenInFlight;
  };

  const server = createServer(async (request, response) => {
    requestCount += 1;
    const url = new URL(request.url || '/', 'http://127.0.0.1');
    try {
      if (request.method === 'GET' && url.pathname === '/') return await assetResponse(response, 'index.html', 'text/html; charset=utf-8');
      if (request.method === 'GET' && url.pathname === '/app.js') return await assetResponse(response, 'app.js', 'text/javascript; charset=utf-8');
      if (request.method === 'GET' && url.pathname === '/app.css') return await assetResponse(response, 'app.css', 'text/css; charset=utf-8');
      if (!tokenMatches(request.headers['x-dashboard-token'] || url.searchParams.get('token'), token)) {
        return jsonResponse(response, 401, { ok: false, error: 'Invalid dashboard token' });
      }
      lastPresenceAt = Date.now();
      if (request.method === 'GET' && url.pathname === '/api/health') {
        return jsonResponse(response, 200, {
          ok: true, service: 'byted-live-inspect-single-task', pid: process.pid,
          task_id: Number(taskId), end_request_accepted: endRequestAccepted,
          end_operation: endOperation.view(),
        });
      }
      if (request.method === 'POST' && ['/api/task/end/prepare', '/api/task/end'].includes(url.pathname)) {
        const origin = `http://127.0.0.1:${server.address().port}`;
        if (request.headers.origin !== origin || request.headers.host !== new URL(origin).host
          || !tokenMatches(request.headers['x-dashboard-token'], token)) {
          return jsonResponse(response, 403, { ok: false, error: '结束操作必须来自当前工作台' });
        }
        if (request.headers['content-type']?.split(';')[0].trim().toLowerCase() !== 'application/json') {
          return jsonResponse(response, 415, { ok: false, error: '需要 JSON 请求' });
        }
        let body = '';
        for await (const chunk of request) {
          body += chunk.toString('utf8');
          if (Buffer.byteLength(body) > 4096) return jsonResponse(response, 413, { ok: false, error: '请求过大' });
        }
        let input;
        try { input = JSON.parse(body); }
        catch { return jsonResponse(response, 400, { ok: false, error: '无效 JSON' }); }
        const isPrepare = url.pathname.endsWith('/prepare');
        const keys = isPrepare ? [] : ['operation_id'];
        if (!input || Array.isArray(input) || typeof input !== 'object' || Object.keys(input).some((key) => !keys.includes(key))
          || (!isPrepare && (typeof input.operation_id !== 'string' || !input.operation_id))) {
          return jsonResponse(response, 400, { ok: false, error: '请求只能操作当前任务' });
        }
        if (!isPrepare && input.operation_id !== endOperation.view().operation_id) {
          return jsonResponse(response, 409, { ok: false, error: '确认计划已变化，请刷新操作状态' });
        }
        const operation = await (isPrepare ? endOperation.prepare() : endOperation.submit(input.operation_id));
        return jsonResponse(response, 200, { ok: true, end_operation: operation });
      }
      if (request.method === 'POST' && url.pathname === '/api/end-accepted') {
        let body = '';
        for await (const chunk of request) {
          body += chunk.toString('utf8');
          if (Buffer.byteLength(body) > 4_096) return jsonResponse(response, 413, { ok: false, error: 'Notification too large' });
        }
        let input;
        try { input = JSON.parse(body); }
        catch { return jsonResponse(response, 400, { ok: false, error: 'Invalid notification JSON' }); }
        if (input?.project_name !== projectName || input?.task_id !== Number(taskId)) {
          return jsonResponse(response, 409, { ok: false, error: 'Notification target does not match this dashboard' });
        }
        endOperation.acknowledge();
        return jsonResponse(response, 200, { ok: true, task_id: Number(taskId), end_request_accepted: true });
      }
      if (request.method === 'GET' && url.pathname === '/api/snapshot') {
        const current = await snapshot();
        const { project_name, scenario_id, ...task } = current.task || {};
        task.scenario_name = ({ 9056: '金融', 9057: '汽车', 9058: '电商' })[scenario_id]
          || (['金融', '汽车', '电商'].includes(task.scenario_name) ? task.scenario_name : null);
        return jsonResponse(response, 200, { ok: true, ...current, task });
      }
      if (request.method === 'GET' && url.pathname === '/api/evidence') {
        const evidenceUrl = evidenceUrls.get(url.searchParams.get('id'));
        if (!evidenceUrl) return jsonResponse(response, 404, { ok: false, error: 'Evidence not found' });
        const upstream = await fetch(evidenceUrl, { signal: AbortSignal.timeout(10_000) });
        const contentType = upstream.headers.get('content-type') || '';
        if (!upstream.ok || !contentType.startsWith('image/')) return jsonResponse(response, 502, { ok: false, error: 'Evidence unavailable' });
        const body = Buffer.from(await upstream.arrayBuffer());
        if (body.length > 5 * 1024 * 1024) return jsonResponse(response, 413, { ok: false, error: 'Evidence too large' });
        response.writeHead(200, headers(contentType, body.length));
        response.end(body);
        return;
      }
      if (request.method === 'POST' && url.pathname === '/api/report/open') {
        const result = await openReportPage();
        if (result.status === 'generating') {
          return jsonResponse(response, 202, {
            ok: false,
            code: 'REPORT_GENERATING',
            message: '质检报告仍在生成中，请在 10 分钟后再次获取。当前未生成不代表审核通过。',
            ...result,
          });
        }
        return jsonResponse(response, 200, { ok: true, ...result });
      }
      return jsonResponse(response, 404, { ok: false, error: 'Not found' });
    } catch (error) {
      const status = error?.code === 'AUTH_REQUIRED' ? 401
        : ['TASK_FAILED', 'TASK_NOT_FINISHED'].includes(error?.code) ? 409
          : 502;
      return jsonResponse(response, status, {
        ok: false, code: error?.code || 'DASHBOARD_ERROR', error: safeError(error),
      });
    } finally {
      requestCount = Math.max(0, requestCount - 1);
    }
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', resolve);
  });
  const idleTimer = setInterval(() => {
    if (!stopping && requestCount === 0 && !snapshotInFlight && !reportOpenInFlight
      && !['preparing', 'submitting'].includes(endOperation.view().status)
      && Date.now() - lastPresenceAt >= idleTimeoutMs) server.close();
  }, Math.min(30_000, Math.max(1_000, Math.floor(idleTimeoutMs / 4))));
  idleTimer.unref();
  server.on('close', () => { stopping = true; clearInterval(idleTimer); });
  return {
    server,
    port: server.address().port,
    stop: () => server.close(),
    state: () => ({
      stopping,
      request_count: requestCount,
      snapshot_in_flight: Boolean(snapshotInFlight),
      report_open_in_flight: Boolean(reportOpenInFlight),
      report_retry_at: reportRetryAt || null,
    }),
  };
}
