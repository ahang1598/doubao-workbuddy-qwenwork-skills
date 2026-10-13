import { access, chmod, mkdir, readFile, realpath, rename, rm, writeFile } from 'node:fs/promises';
import { createHash, randomUUID, timingSafeEqual } from 'node:crypto';
import { createServer } from 'node:http';
import { join, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { validateReviewDocument, validateTaskId, MAX_REPORT_BYTES } from './review-document.mjs';

export const REVIEW_REPORT_ROOT = join(tmpdir(), 'byted-live-inspect', 'ecommerce-review-reports');

const TEMPLATE_PLACEHOLDER = '__REVIEW_REPORT_JSON__';
const FORBIDDEN_KEYS = new Set(['asr', 'utterances', 'fd', 'tx', 'raw_report', 'quality_report']);
const DEFAULT_IDLE_TIMEOUT_MS = 24 * 60 * 60 * 1_000;

function text(value) {
  return value === undefined || value === null ? '' : String(value).trim();
}

function integer(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? Math.round(parsed) : null;
}

function textArray(value) {
  return Array.isArray(value) ? value.map(text).filter(Boolean) : [];
}

function timeText(milliseconds) {
  const total = Math.max(0, Math.floor(Number(milliseconds || 0) / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  return [hours, minutes, seconds].map((part) => String(part).padStart(2, '0')).join(':');
}

function inspectionPeriod(playback) {
  const valid = value => typeof value === 'number' && Number.isFinite(value) && value > 0
    && Number.isFinite(new Date(value * 1000).getTime());
  const start = playback.inspection_start_time;
  const end = playback.inspection_end_time;
  const format = value => {
    const parts = Object.fromEntries(new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
    }).formatToParts(new Date(value * 1000)).map(part => [part.type, part.value]));
    return `${parts.year}年${parts.month}月${parts.day}日 ${parts.hour}:${parts.minute}:${parts.second}`;
  };
  // An absent or inverted end time cannot be reconstructed from content duration.
  const hasEnd = valid(end) && (!valid(start) || end >= start);
  return `${valid(start) ? format(start) : '开始时间暂无'} ~ ${hasEnd ? format(end) : '结束时间暂无'}`;
}

function durationText(milliseconds) {
  const total = Math.max(0, Math.floor(Number(milliseconds || 0) / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (hours) return `${hours}小时${minutes}分`;
  if (minutes) return `${minutes}分${seconds ? `${seconds}秒` : ''}`;
  return `${seconds}秒`;
}

function reviewTitle(value) {
  const name = text(value);
  if (!name) return '电商直播复盘';
  return name.replace(/\s*[·・]\s*复盘\s*$/, '').trim() || '电商直播复盘';
}

function assertNoRawReportData(node, depth = 0, seen = new Set()) {
  if (!node || typeof node !== 'object' || seen.has(node)) return;
  if (depth > 20) throw Object.assign(new Error('review result is nested too deeply'), { code: 'INVALID_REVIEW_RESULT' });
  seen.add(node);
  for (const [key, value] of Object.entries(node)) {
    if (FORBIDDEN_KEYS.has(key.toLowerCase())) {
      throw Object.assign(new Error(`review result contains forbidden raw-data field: ${key}`), { code: 'RAW_DATA_REJECTED' });
    }
    assertNoRawReportData(value, depth + 1, seen);
  }
}

function normalizeSegments(review) {
  const rows = Array.isArray(review?.segments) ? review.segments : [];
  if (review?.status !== 'degraded' && rows.length === 0) {
    throw Object.assign(new Error('successful content analysis must contain at least one segment'), { code: 'INVALID_REVIEW_RESULT' });
  }
  let totalContentLength = 0;
  let previousEnd = null;
  return rows.map((segment, index) => {
    const startTime = integer(segment?.start_time);
    const endTime = integer(segment?.end_time);
    const content = text(segment?.content);
    if (startTime === null || endTime === null || endTime < startTime || !content) {
      throw Object.assign(new Error(`segment ${index + 1} has invalid time or content`), { code: 'INVALID_REVIEW_RESULT' });
    }
    if (previousEnd !== null && startTime < previousEnd) {
      throw Object.assign(new Error(`segment ${index + 1} overlaps or is out of order`), { code: 'INVALID_REVIEW_RESULT' });
    }
    const labels = Array.isArray(segment?.labels) ? segment.labels : [];
    if (labels.some((label) => ![1, 2, 3].includes(label)) || new Set(labels).size !== labels.length) {
      throw Object.assign(new Error(`segment ${index + 1} contains a V1-unsupported label`), { code: 'INVALID_REVIEW_RESULT' });
    }
    if (labels.includes(2) && labels.includes(3)) {
      throw Object.assign(new Error(`segment ${index + 1} cannot be both highlight and problem`), { code: 'INVALID_REVIEW_RESULT' });
    }
    const tags = Array.isArray(segment?.tags) ? segment.tags : [];
    if (tags.length > 2 || tags.some((tag) => !text(tag))) {
      throw Object.assign(new Error(`segment ${index + 1} contains invalid tags`), { code: 'INVALID_REVIEW_RESULT' });
    }
    if (segment?.scores !== undefined) {
      if (!segment.scores || typeof segment.scores !== 'object' || Array.isArray(segment.scores)
        || Object.values(segment.scores).some((score) => typeof score !== 'number' || !Number.isFinite(score) || score < 0 || score > 100)) {
        throw Object.assign(new Error(`segment ${index + 1} contains invalid scores`), { code: 'INVALID_REVIEW_RESULT' });
      }
    }
    const duration = endTime - startTime;
    if (duration > 180_000) {
      throw Object.assign(new Error(`segment ${index + 1} exceeds the V1 duration limit`), { code: 'INVALID_REVIEW_RESULT' });
    }
    previousEnd = endTime;
    if (content.length > 1200) {
      throw Object.assign(new Error(`segment ${index + 1} content is too long for a review report`), { code: 'RAW_DATA_REJECTED' });
    }
    totalContentLength += content.length;
    if (totalContentLength > 40_000) {
      throw Object.assign(new Error('review content exceeds the safe display limit'), { code: 'RAW_DATA_REJECTED' });
    }
    return {
      ...segment,
      segment_id: segment.segment_id ?? index + 1,
      index: segment.index ?? index + 1,
      start_time: startTime,
      end_time: endTime,
      time_text: `${timeText(startTime)} ~ ${timeText(endTime)}`,
      title: text(segment.title) || `内容片段 ${index + 1}`,
      content,
      labels,
      tags: tags.map(text),
    };
  });
}

function normalizeFindingRows(rows, field) {
  return rows.map((item, index) => {
    if (!text(item?.title) || !text(item?.reason)) {
      throw Object.assign(new Error(`${field}[${index}] has invalid content`), { code: 'INVALID_REVIEW_RESULT' });
    }
    const startTime = integer(item?.start_time);
    const endTime = integer(item?.end_time);
    if (startTime === null && endTime === null) return null;
    if (startTime === null || endTime === null || endTime <= startTime) {
      throw Object.assign(new Error(`${field}[${index}] has invalid time or content`), { code: 'INVALID_REVIEW_RESULT' });
    }
    return { startTime, endTime };
  }).filter(Boolean);
}

function assertFindingRangesDoNotConflict(highlights, problems) {
  const highlightRanges = normalizeFindingRows(highlights, 'highlights');
  const problemRanges = normalizeFindingRows(problems, 'problems');
  for (const highlight of highlightRanges) {
    if (problemRanges.some((problem) => highlight.startTime < problem.endTime && highlight.endTime > problem.startTime)) {
      throw Object.assign(new Error('highlight and problem time ranges cannot overlap; split by ASR evidence or keep the problem range'), { code: 'INVALID_REVIEW_RESULT' });
    }
  }
}

function asrTimelineSegments(rows, semanticSegments, review) {
  if (!Array.isArray(rows)) return [];
  return rows.map((row, index) => {
    const startTime = integer(row?.start_time);
    const endTime = integer(row?.end_time);
    const content = text(row?.text);
    if (startTime === null || endTime === null || endTime < startTime || !content) {
      throw Object.assign(new Error(`ASR timeline segment ${index + 1} is invalid`), { code: 'INVALID_RENDER_CONTEXT' });
    }
    const matched = semanticSegments.find((segment) => startTime < segment.end_time && endTime > segment.start_time)
      ?? semanticSegments.find((segment) => startTime >= segment.start_time && startTime <= segment.end_time)
      ?? {};
    const labels = Array.isArray(matched.labels) ? matched.labels : [];
    const findingRows = labels.includes(2) ? review?.highlights : labels.includes(3) ? review?.problems : [];
    const finding = (Array.isArray(findingRows) ? findingRows : []).find((item) => {
      const findingStart = integer(item?.start_time);
      const findingEnd = integer(item?.end_time);
      return findingStart !== null && findingEnd !== null && startTime < findingEnd && endTime > findingStart;
    });
    const sourceDetail = matched.moment_detail ?? matched.momentData ?? matched.moment_data ?? {};
    const hasSourceDetail = sourceDetail && typeof sourceDetail === 'object' && Object.keys(sourceDetail).length > 0;
    const momentDetail = finding || hasSourceDetail ? {
      title: text(finding?.title ?? sourceDetail.title),
      reason: text(finding?.reason ?? sourceDetail.reason ?? sourceDetail.body),
      suggestion: text(finding?.suggestion ?? sourceDetail.suggestion),
    } : undefined;
    const frameImages = Array.isArray(review?.timed_images) ? [...new Set(review.timed_images
      .filter((item) => item.time >= startTime && item.time <= endTime)
      .map((item) => item.url))] : [];
    return {
      segment_id: `asr-${index + 1}`,
      index: index + 1,
      start_time: startTime,
      end_time: endTime,
      time_text: `${timeText(startTime)} ~ ${timeText(endTime)}`,
      title: text(matched.title) || '主播语音',
      content,
      labels: labels.map((label) => label === 3 ? 4 : label),
      tags: Array.isArray(matched.tags) ? matched.tags : [],
      ...(momentDetail ? { moment_detail: momentDetail } : {}),
      ...(frameImages.length ? { frame_images: frameImages } : {}),
    };
  });
}

function reviewMetrics(segments, durationMs) {
  const highlightCount = segments.filter((segment) => Array.isArray(segment?.labels) && segment.labels.includes(2)).length;
  const problemCount = segments.filter((segment) => Array.isArray(segment?.labels) && segment.labels.includes(3)).length;
  return [
    { label: '有效内容时长', value: timeText(durationMs), unit: '', sub_label: '可用于内容复盘的主播语音' },
    { label: '内容片段', value: segments.length, unit: '段', sub_label: '按直播内容主题划分' },
    { label: '高光时刻', value: highlightCount, unit: '段', sub_label: '值得复用的优质讲解片段' },
    { label: '问题时刻', value: problemCount, unit: '段', sub_label: '建议重点优化的内容片段' },
  ];
}

export function buildReviewReportViewModel(review, metadata = {}) {
  if (!review || typeof review !== 'object' || Array.isArray(review)) {
    throw Object.assign(new Error('review must be a JSON object'), { code: 'INVALID_REVIEW_RESULT' });
  }
  assertNoRawReportData(review);
  if (text(review.module_code) !== 'content_analysis') {
    throw Object.assign(new Error('review.module_code must be content_analysis'), { code: 'INVALID_REVIEW_RESULT' });
  }
  for (const field of ['conclusion', 'summary', 'data_scope_note']) {
    if (!text(review[field])) throw Object.assign(new Error(`review.${field} is required`), { code: 'INVALID_REVIEW_RESULT' });
  }
  for (const field of ['highlights', 'problems', 'recommended_structure', 'recommendations']) {
    if (!Array.isArray(review[field])) throw Object.assign(new Error(`review.${field} must be an array`), { code: 'INVALID_REVIEW_RESULT' });
  }
  if (!review.recommended_structure.length || !review.recommendations.length) {
    throw Object.assign(new Error('review recommendations are required'), { code: 'INVALID_REVIEW_RESULT' });
  }
  assertFindingRangesDoNotConflict(review.highlights, review.problems);
  const segments = normalizeSegments(review);
  const startTime = segments.length ? segments[0].start_time : 0;
  const endTime = segments.length ? segments.at(-1).end_time : 0;
  const durationMs = Math.max(0, endTime - startTime);
  const qualitySummary = metadata.quality_summary && typeof metadata.quality_summary === 'object'
    ? metadata.quality_summary
    : {};
  const taskId = metadata.task_id ?? null;
  // Keep service IDs as supplied; converting a large string ID to Number can bind the wrong task.
  if (taskId !== null) validateTaskId(taskId);
  const playback = metadata.playback && typeof metadata.playback === 'object' ? metadata.playback : {};
  const playbackUrl = text(playback.play_url);
  const playbackVid = text(playback.vid);
  const timedImages = Array.isArray(playback.timed_images) ? playback.timed_images
    .map((item) => ({ time: integer(item?.time), url: text(item?.url) }))
    .filter((item) => item.time !== null && /^https?:\/\//i.test(item.url))
    : [];
  const transcriptSegments = asrTimelineSegments(playback.asr_timeline, segments, { ...review, timed_images: timedImages });
  return {
    schema_version: 1,
    live: {
      title: reviewTitle(metadata.title || playback.display_name),
      duration_text: durationText(durationMs),
      time_range: inspectionPeriod(playback),
      review_type: 'live',
      vid: playbackVid,
      cover_label: text(playback.source_label) || '直播',
      account_name: text(metadata.account_name || playback.account_name),
      scenario_id: integer(metadata.scenario_id ?? playback.scenario_id),
      scenario_name: text(metadata.scenario_name || playback.scenario_name),
    },
    playbackInfo: playbackUrl || playbackVid ? {
      PlayUrl: playbackUrl,
      Format: text(playback.format) || 'hls',
    } : undefined,
    metrics: reviewMetrics(segments, durationMs),
    content: {
      tabs: ['全部', '高光时刻', '问题时刻'],
      segments: transcriptSegments.length ? transcriptSegments : segments,
    },
    modules: {
      content_analysis: {
        module_code: 'content_analysis',
        status: text(review.status) || 'success',
        conclusion: text(review.conclusion),
        summary: text(review.summary),
        highlights: Array.isArray(review.highlights) ? review.highlights : [],
        problems: Array.isArray(review.problems) ? review.problems : [],
        recommended_structure: textArray(review.recommended_structure),
        recommendations: textArray(review.recommendations),
        data_scope_note: text(review.data_scope_note),
        semantic_segments: segments,
      },
    },
    display_flags: {
      live_score: false,
      full_curve: false,
      highlight_moment: true,
      content_analysis: true,
    },
    report_meta: {
      source: 'byted-live-inspect/get-report',
      project_name: text(metadata.project_name),
      task_id: taskId,
      scope: text(metadata.scope) || 'asr_and_quality_report_only',
      quality_conclusion_code: integer(qualitySummary.overall_conclusion_code),
    },
  };
}

export function injectReviewReportData(template, viewModel) {
  const occurrences = template.split(TEMPLATE_PLACEHOLDER).length - 1;
  if (occurrences !== 1) throw Object.assign(new Error('review report template must contain exactly one data placeholder'), { code: 'INVALID_TEMPLATE' });
  const embedded = JSON.stringify(viewModel)
    .replace(/</g, '\\u003c')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
  return template.replace(TEMPLATE_PLACEHOLDER, embedded);
}

export async function renderReviewReport({ review, metadata, templatePath, outputRoot = REVIEW_REPORT_ROOT, format = 'html' }) {
  const viewModel = buildReviewReportViewModel(review, metadata);
  if (!['html', 'json'].includes(format)) throw Object.assign(new Error('Unsupported report format'), { code: 'INVALID_INPUT' });
  // The complete document is assembled in the runtime, without sending ASR back through model output.
  if (format === 'json') {
    if (!Array.isArray(metadata?.playback?.asr_timeline) || !metadata.playback.asr_timeline.length) {
      throw Object.assign(new Error('Complete JSON requires the prepared ASR timeline'), { code: 'ASR_NOT_FOUND' });
    }
    if (!metadata.playback.asr_timeline.every(row => Number.isSafeInteger(row?.start_time) && row.start_time >= 0
      && Number.isSafeInteger(row.end_time) && row.end_time >= row.start_time && typeof row.text === 'string' && row.text.trim())) {
      throw Object.assign(new Error('Prepared ASR timeline contains invalid rows; refresh the original task context'), { code: 'INVALID_RENDER_CONTEXT' });
    }
    validateReviewDocument(viewModel);
  }
  const content = format === 'json' ? `${JSON.stringify(viewModel)}\n` : injectReviewReportData(await readFile(templatePath, 'utf8'), viewModel);
  if (Buffer.byteLength(content) > MAX_REPORT_BYTES) throw Object.assign(new Error('Report exceeds 20 MiB'), { code: 'INVALID_INPUT' });
  await mkdir(outputRoot, { recursive: true, mode: 0o700 });
  await chmod(outputRoot, 0o700);
  const taskPart = viewModel.report_meta.task_id === null ? 'unknown' : String(viewModel.report_meta.task_id);
  const outputPath = join(outputRoot, `review_report-${taskPart}-${randomUUID()}.${format}`);
  await writeFile(outputPath, content, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
  return { path: outputPath, segmentCount: viewModel.content.segments.length, scope: viewModel.report_meta.scope };
}

function reportPath(path, root = REVIEW_REPORT_ROOT) {
  const absoluteRoot = resolve(root);
  const absolutePath = resolve(path);
  if (!absolutePath.startsWith(`${absoluteRoot}${sep}`) || !absolutePath.endsWith('.html')) {
    throw Object.assign(new Error('review report path is outside the managed runtime directory'), { code: 'INVALID_PATH' });
  }
  return absolutePath;
}

function reportPointerPath(taskId) {
  const normalized = integer(taskId);
  if (normalized === null) throw Object.assign(new Error('task id is required for report registration'), { code: 'INVALID_INPUT' });
  return join(REVIEW_REPORT_ROOT, `task-${normalized}.json`);
}

function reportOwnerPath(taskId, { pid, url }) {
  const owner = createHash('sha256').update(JSON.stringify([pid, url])).digest('hex');
  return `${reportPointerPath(taskId)}.${owner}.active`;
}

export async function registerReviewReport(taskId, url, pid = process.pid) {
  const parsed = new URL(String(url || ''));
  if (parsed.protocol !== 'http:' || parsed.hostname !== '127.0.0.1' || !parsed.searchParams.get('token')) {
    throw Object.assign(new Error('review report URL must be a token-protected loopback URL'), { code: 'INVALID_INPUT' });
  }
  await mkdir(REVIEW_REPORT_ROOT, { recursive: true, mode: 0o700 });
  const value = { url: parsed.href, pid, owner_marker: true };
  const pointer = reportPointerPath(taskId);
  const staged = `${pointer}.${randomUUID()}.tmp`;
  try {
    await writeFile(reportOwnerPath(taskId, value), '', { mode: 0o600 });
    await writeFile(staged, `${JSON.stringify(value)}\n`, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
    // Readers must see either complete registration, never truncated JSON.
    await rename(staged, pointer);
  } finally { await rm(staged, { force: true }); }
  return parsed.href;
}

export async function readRegisteredReviewReport(taskId) {
  try {
    const value = JSON.parse(await readFile(reportPointerPath(taskId), 'utf8'));
    const parsed = new URL(String(value?.url || ''));
    if (!Number.isSafeInteger(value?.pid) || value.pid <= 0) return null;
    if (value.owner_marker === true) await access(reportOwnerPath(taskId, value));
    try { process.kill(value.pid, 0); } catch { await unregisterReviewReport(taskId, value); return null; }
    return parsed.protocol === 'http:' && parsed.hostname === '127.0.0.1' && parsed.searchParams.get('token') ? parsed.href : null;
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    return null;
  }
}

export async function unregisterReviewReport(taskId, expected = null) {
  if (integer(taskId) === null) return;
  let owner = expected;
  if (!owner) {
    try { owner = JSON.parse(await readFile(reportPointerPath(taskId), 'utf8')); }
    catch (error) {
      if (error.code === 'ENOENT' || error instanceof SyntaxError) return;
      throw error;
    }
  }
  // Never check then unlink the shared pointer: a replacement can be published
  // between those operations, including from another process. Retire only this
  // owner's marker; the last locator is harmless without its live marker.
  await rm(reportOwnerPath(taskId, owner), { force: true });
}

function tokenMatches(actual, expected) {
  const left = Buffer.from(String(actual || ''));
  const right = Buffer.from(String(expected || ''));
  return left.length === right.length && left.length > 0 && timingSafeEqual(left, right);
}

function downloadPage({ token, filename }) {
  const href = `/download/file.html?token=${encodeURIComponent(token)}`;
  return Buffer.from(`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>下载复盘报告</title><style>body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;background:#f5f7fb;color:#1f2937}.card{max-width:560px;margin:12vh auto;padding:32px;border-radius:16px;background:#fff;box-shadow:0 12px 36px rgba(15,23,42,.1)}h1{font-size:22px;margin:0 0 12px}p{line-height:1.6;color:#64748b}.button{display:inline-block;margin-top:12px;padding:12px 20px;border-radius:10px;background:#1664ff;color:#fff;text-decoration:none;font-weight:600}</style></head><body><main class="card"><h1>复盘报告已准备好</h1><p>文件：${filename}</p><a class="button" href="${href}" download="${filename}">下载 HTML 报告</a></main></body></html>`);
}

export async function startReviewReportServer({ path, token, taskId = null, port = 0, idleTimeoutMs = DEFAULT_IDLE_TIMEOUT_MS }) {
  if (!token) throw Object.assign(new Error('report token is required'), { code: 'INVALID_INPUT' });
  const candidate = reportPath(path);
  // Resolve both sides because OS temporary-directory paths may be symlinked.
  const [resolvedPath, resolvedRoot] = await Promise.all([realpath(candidate), realpath(REVIEW_REPORT_ROOT)]);
  const managedPath = reportPath(resolvedPath, resolvedRoot);
  // Read before announcing readiness; subsequent requests do not depend on the file staying present.
  const reportBody = await readFile(managedPath);
  let lastAuthorizedAt = Date.now();
  const server = createServer((request, response) => {
    const url = new URL(request.url || '/', 'http://127.0.0.1');
    if (request.method !== 'GET' || !['/', '/download.html', '/download/file.html', '/api/health'].includes(url.pathname) || !tokenMatches(url.searchParams.get('token'), token)) {
      const body = Buffer.from('Not found');
      response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8', 'content-length': body.length, 'cache-control': 'no-store' });
      response.end(body);
      return;
    }
    lastAuthorizedAt = Date.now();
    if (url.pathname === '/api/health') {
      response.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      response.end('{"ok":true}');
      return;
    }
    const filename = `review-report-${integer(taskId) ?? 'task'}.html`;
    const isDownloadFile = url.pathname === '/download/file.html';
    const body = url.pathname === '/download.html' ? downloadPage({ token, filename }) : reportBody;
    response.writeHead(200, {
      'content-type': isDownloadFile ? 'application/octet-stream' : 'text/html; charset=utf-8',
      'content-length': body.length,
      'cache-control': 'no-store',
      ...(isDownloadFile ? { 'content-disposition': `attachment; filename="${filename}"` } : {}),
      'referrer-policy': 'no-referrer',
      'x-content-type-options': 'nosniff',
      'x-frame-options': 'DENY',
    });
    response.end(body);
  });
  await new Promise((resolveListen, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', resolveListen);
  });
  const reportUrl = `http://127.0.0.1:${server.address().port}/?token=${encodeURIComponent(token)}`;
  const downloadUrl = `http://127.0.0.1:${server.address().port}/download.html?token=${encodeURIComponent(token)}`;
  if (integer(taskId) !== null) {
    try { await registerReviewReport(taskId, reportUrl); }
    catch (error) { server.close(); throw error; }
  }
  const idleTimer = setInterval(() => {
    if (Date.now() - lastAuthorizedAt >= idleTimeoutMs) server.close();
  }, Math.min(30_000, Math.max(100, Math.floor(idleTimeoutMs / 4))));
  idleTimer.unref();
  server.on('close', () => {
    clearInterval(idleTimer);
    // The returned HTML artifact remains available for file delivery and --open recovery.
    // Cleanup is best-effort during shutdown; dead PIDs are also rejected on read.
    void unregisterReviewReport(taskId, { pid: process.pid, url: reportUrl }).catch(() => {});
  });
  return { server, port: server.address().port, url: reportUrl, downloadUrl, stop: () => server.close() };
}
