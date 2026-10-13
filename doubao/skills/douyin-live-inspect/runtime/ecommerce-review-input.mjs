import { chmod, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { basename, join, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { getRuleFindingCount } = require('./rule-findings.cjs');

export const REVIEW_INPUT_ROOT = join(tmpdir(), 'byted-live-inspect', 'ecommerce-review-inputs');

function artifactId(value) {
  const id = String(value ?? '').trim();
  if (!/^[0-9a-f-]{36}$/i.test(id)) throw Object.assign(new Error('review artifact id is invalid'), { code: 'INVALID_PATH' });
  return id;
}

function integer(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? Math.round(parsed) : null;
}

function timeMilliseconds(value) {
  const numeric = integer(value);
  if (numeric !== null) return numeric;
  const match = String(value ?? '').trim().match(/^(\d{1,3}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?$/);
  if (!match) return null;
  return ((Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3])) * 1000)
    + Number(String(match[4] || '').padEnd(3, '0'));
}

function text(value) {
  return value === undefined || value === null ? '' : String(value).trim();
}

function httpUrl(value) {
  const candidate = text(value);
  if (!candidate) return '';
  try {
    const parsed = new URL(candidate);
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : '';
  } catch {
    return '';
  }
}

function imageUrls(node, depth = 0, output = []) {
  if (!node || typeof node !== 'object' || depth > 3) return output;
  for (const [key, value] of Object.entries(node)) {
    if (!/image|frame|screenshot/i.test(key)) continue;
    if (typeof value === 'string') {
      const url = httpUrl(value);
      if (url) output.push(url);
    } else if (Array.isArray(value)) {
      for (const item of value) {
        if (typeof item === 'string') {
          const url = httpUrl(item);
          if (url) output.push(url);
        } else imageUrls(item, depth + 1, output);
      }
    } else imageUrls(value, depth + 1, output);
  }
  return output;
}

function timedImageTime(node) {
  const milliseconds = utteranceTime(node, ['TimestampMs', 'timestamp_ms', 'ScreenshotTimeMs', 'screenshot_time_ms', 'StartTimeMs', 'start_time_ms']);
  if (milliseconds !== null) return milliseconds;
  const screenshotSeconds = node?.ScreenshotTime ?? node?.screenshot_time;
  if (screenshotSeconds !== undefined && Number.isFinite(Number(screenshotSeconds))) return Math.round(Number(screenshotSeconds) * 1000);
  return utteranceTime(node, ['Timestamp', 'timestamp', 'StartTime', 'start_time', 'BeginTime', 'begin_time']);
}

export function collectTimedImages(reportPayload) {
  const result = unwrapCliPayload(reportPayload) ?? reportPayload;
  const output = [];
  const seenNodes = new Set();
  const visit = (node, depth = 0) => {
    if (!node || typeof node !== 'object' || depth > 10 || seenNodes.has(node) || output.length >= 100) return;
    seenNodes.add(node);
    if (!Array.isArray(node)) {
      const time = timedImageTime(node);
      const urls = time === null ? [] : [...new Set(imageUrls(node))];
      for (const url of urls) output.push({ time, url });
    }
    for (const value of Object.values(node)) visit(value, depth + 1);
  };
  visit(result);
  const unique = new Map();
  for (const item of output) unique.set(`${item.time}:${item.url}`, item);
  return [...unique.values()].sort((left, right) => left.time - right.time).slice(0, 100);
}

function unwrapCliPayload(payload) {
  return payload?.data?.response?.data?.Result
    ?? payload?.data?.response?.Result
    ?? payload?.data?.Result
    ?? payload?.Result
    ?? null;
}

function findAsrCandidates(node, depth = 0, output = [], seen = new Set()) {
  if (!node || typeof node !== 'object' || depth > 10 || seen.has(node)) return output;
  seen.add(node);
  for (const [key, value] of Object.entries(node)) {
    if (/^(asr|asrresult)$/i.test(key) && (Array.isArray(value) || typeof value === 'string' || (value && typeof value === 'object'))) output.push(value);
  }
  for (const value of Object.values(node)) {
    findAsrCandidates(value, depth + 1, output, seen);
  }
  return output;
}

function parseAsr(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === 'object') {
    const utterances = value.Utterances ?? value.utterances ?? value.Segments ?? value.segments;
    return Array.isArray(utterances) ? utterances : [];
  }
  if (typeof value !== 'string' || !value.trim()) return [];
  try {
    const parsed = JSON.parse(value);
    return parseAsr(parsed);
  } catch {
    return [];
  }
}

function utteranceTime(item, names) {
  for (const name of names) {
    const value = timeMilliseconds(item?.[name]);
    if (value !== null) return value;
  }
  return null;
}

function asrUtteranceTime(item, millisecondNames, secondNames) {
  const milliseconds = utteranceTime(item, millisecondNames);
  if (milliseconds !== null) return milliseconds;
  for (const name of secondNames) {
    const raw = item?.[name];
    if (typeof raw === 'number' || /^\d+(?:\.\d+)?$/.test(String(raw ?? '').trim())) {
      const seconds = Number(raw);
      if (Number.isFinite(seconds) && seconds >= 0) return Math.round(seconds * 1000);
    }
    const parsed = timeMilliseconds(raw);
    if (parsed !== null) return parsed;
  }
  return null;
}

export function normalizeAsrUtterances(reportPayload) {
  const result = unwrapCliPayload(reportPayload) ?? reportPayload;
  return findAsrCandidates(result).map((candidate) => parseAsr(candidate).map((item, index) => {
      const tx = text(item?.Text ?? item?.text ?? item?.Content ?? item?.content);
      const st = asrUtteranceTime(item, ['StartTimeMs', 'start_time_ms', 'startTimeMs'], ['StartTime', 'start_time', 'startTime', 'BeginTime', 'begin_time']);
      const et = asrUtteranceTime(item, ['EndTimeMs', 'end_time_ms', 'endTimeMs'], ['EndTime', 'end_time', 'endTime', 'StopTime', 'stop_time']);
      return tx && st !== null ? { index, st, et: et !== null && et >= st ? et : st, tx } : null;
    }).filter(Boolean).sort((left, right) => left.st - right.st || left.index - right.index))
    .sort((left, right) => right.length - left.length)[0] ?? [];
}

export function buildSegments(utterances, targetDurationMs = 120_000, {
  minDurationMs = 60_000, maxDurationMs = 180_000, pauseThresholdMs = 2500,
} = {}) {
  if (![targetDurationMs, minDurationMs, maxDurationMs, pauseThresholdMs].every(Number.isSafeInteger)
    || targetDurationMs <= 0 || minDurationMs <= 0 || pauseThresholdMs < 0
    || maxDurationMs < Math.max(targetDurationMs, minDurationMs)) {
    throw new Error('Invalid segment duration settings');
  }
  if (!utterances.length) return [];
  const segments = [];
  let current = [];
  let segmentStart = utterances[0].st;
  let lastEnd = segmentStart;
  const flush = () => {
    if (!current.length) return;
    segments.push({
      i: segments.length + 1,
      sid: segments.length + 1,
      st: segmentStart,
      et: lastEnd,
      tx: current.map((item) => item.tx).join('\n'),
      tc: 0,
      cm: [],
      dc: [],
      rp: [],
      ia: [],
      wm: {},
    });
    current = [];
  };
  for (const utterance of utterances) {
    const end = Math.max(utterance.et ?? utterance.st, utterance.st);
    const elapsed = utterance.st - segmentStart;
    const pause = utterance.st - lastEnd;
    const naturalBoundary = elapsed >= Math.max(targetDurationMs, minDurationMs) && pause >= pauseThresholdMs;
    const sizeBoundary = end - segmentStart > maxDurationMs || elapsed >= maxDurationMs;
    // Keep ASR utterances intact; overlapping or individually long utterances may exceed the cap.
    if (current.length && pause >= 0 && (naturalBoundary || sizeBoundary)) {
      flush();
      segmentStart = utterance.st;
      lastEnd = utterance.st;
    }
    current.push(utterance);
    lastEnd = Math.max(lastEnd, end);
  }
  flush();
  return segments;
}

function collectRuleEvidence(node, depth = 0, output = [], seen = new Set()) {
  if (!node || typeof node !== 'object' || depth > 9 || seen.has(node) || output.length >= 100) return output;
  seen.add(node);
  if (!Array.isArray(node)) {
    const name = text(node.RuleName ?? node.Name ?? node.rule_name);
    const conclusion = text(node.Conclusion ?? node.AnalysisConclusion ?? node.Result ?? node.conclusion ?? node.FinalMachineStatus ?? node.FinalManualStatus);
    const rawCount = node.FindingCount ?? node.HitCount ?? node.ViolationCount ?? node.count ?? node.RulePointResults?.Total;
    const explicitCount = (typeof rawCount === 'number' || typeof rawCount === 'string') && String(rawCount).trim() !== ''
      && Number.isSafeInteger(Number(rawCount)) && Number(rawCount) >= 0 ? Number(rawCount) : null;
    const count = explicitCount ?? getRuleFindingCount(node);
    if (name && (node.RuleName !== undefined || node.rule_name !== undefined || conclusion || explicitCount !== null || node.FinalMachineStatus !== undefined || node.FinalManualStatus !== undefined)) {
      const startTime = utteranceTime(node, ['StartTime', 'start_time', 'StartTimeMs', 'startTime', 'BeginTime', 'begin_time']);
      const endTime = utteranceTime(node, ['EndTime', 'end_time', 'EndTimeMs', 'endTime', 'StopTime', 'stop_time']);
      output.push({
        rule_id: integer(node.RuleId ?? node.RuleID ?? node.rule_id),
        rule_name: name,
        conclusion,
        finding_count: count,
        machine_status_code: integer(node.FinalMachineStatus ?? node.MachineStatus),
        manual_status_code: integer(node.FinalManualStatus ?? node.ManualStatus),
        ...(startTime === null ? {} : { start_time: startTime }),
        ...(endTime === null ? {} : { end_time: endTime }),
      });
    }
  }
  for (const value of Object.values(node)) collectRuleEvidence(value, depth + 1, output, seen);
  return output;
}

function plainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export function validateEcommerceReviewInput(input) {
  const fail = (message) => { throw Object.assign(new TypeError(`invalid ecommerce review input: ${message}`), { code: 'INVALID_REVIEW_INPUT' }); };
  if (!plainObject(input) || input.input_contract !== 'ecommerce_review_skill/v1') fail('input_contract must be ecommerce_review_skill/v1');
  if (!Array.isArray(input.review_dimensions) || input.review_dimensions.length !== 1 || input.review_dimensions[0] !== 'content_analysis') fail('review_dimensions must equal ["content_analysis"]');
  const fd = input.fd;
  if (!plainObject(fd) || !Array.isArray(fd.sg) || !fd.sg.length) fail('fd.sg must be a non-empty array');
  fd.sg.forEach((segment, index) => {
    if (!Number.isSafeInteger(segment?.i) || segment.i < 1 || !Number.isSafeInteger(segment?.sid) || segment.sid < 1) fail(`fd.sg[${index}] identifiers must be positive integers`);
    if (!Number.isSafeInteger(segment.st) || segment.st < 0 || !Number.isSafeInteger(segment.et) || segment.et < segment.st) fail(`fd.sg[${index}] st/et must be ordered millisecond integers`);
    if (!text(segment.tx)) fail(`fd.sg[${index}].tx must be a non-empty string`);
    if (!Number.isSafeInteger(segment.tc) || segment.tc < 0) fail(`fd.sg[${index}].tc must be a non-negative integer`);
    for (const key of ['cm', 'dc', 'rp', 'ia']) if (!Array.isArray(segment[key])) fail(`fd.sg[${index}].${key} must be an array`);
    if (!plainObject(segment.wm)) fail(`fd.sg[${index}].wm must be an object`);
  });
  if (!plainObject(fd.pd) || !Array.isArray(fd.pd.ps) || !plainObject(fd.pd.cf)) fail('fd.pd must contain ps[] and cf{}');
  if (!plainObject(fd.wd) || !Array.isArray(fd.wd.ws)) fail('fd.wd.ws must be an array');
  if (!plainObject(fd.scs) || !plainObject(fd.bm) || !Array.isArray(fd.iad)) fail('fd.scs, fd.bm and fd.iad have invalid types');
  const ev = fd.ev;
  if (!plainObject(ev) || ev.scope !== 'asr_and_quality_report_only' || !Array.isArray(ev.limitations) || ev.limitations.some((item) => typeof item !== 'string')) fail('fd.ev scope or limitations are invalid');
  const quality = ev.quality_report;
  if (!plainObject(quality) || typeof quality.source !== 'string' || typeof quality.project_name !== 'string') fail('quality_report metadata is invalid');
  for (const key of ['task_id', 'task_status', 'overall_conclusion_code']) if (quality[key] !== null && !Number.isSafeInteger(quality[key])) fail(`quality_report.${key} must be an integer or null`);
  if (quality.scenario_id !== undefined && quality.scenario_id !== null && !Number.isSafeInteger(quality.scenario_id)) fail('quality_report.scenario_id must be an integer or null');
  if (!Array.isArray(quality.rules)) fail('quality_report.rules must be an array');
  quality.rules.forEach((rule, index) => {
    if (rule.rule_id !== null && !Number.isSafeInteger(rule.rule_id)) fail(`rules[${index}].rule_id must be an integer or null`);
    if (typeof rule.rule_name !== 'string' || typeof rule.conclusion !== 'string') fail(`rules[${index}] text fields are invalid`);
    if (rule.finding_count !== null && (!Number.isSafeInteger(rule.finding_count) || rule.finding_count < 0)) fail(`rules[${index}].finding_count must be a non-negative integer or null`);
    for (const key of ['machine_status_code', 'manual_status_code']) if (rule[key] !== null && !Number.isSafeInteger(rule[key])) fail(`rules[${index}].${key} must be an integer or null`);
    for (const key of ['start_time', 'end_time']) if (rule[key] !== undefined && (!Number.isSafeInteger(rule[key]) || rule[key] < 0)) fail(`rules[${index}].${key} must be a non-negative millisecond integer`);
  });
  return input;
}

export function buildEcommerceReviewInput(reportPayload, { projectName, taskId, scenarioName, segmentDurationMs = 120_000 } = {}) {
  const result = unwrapCliPayload(reportPayload) ?? reportPayload;
  const utterances = normalizeAsrUtterances(reportPayload);
  if (!utterances.length) throw Object.assign(new Error('GetReport did not contain readable timestamped ASR'), { code: 'ASR_NOT_FOUND' });
  const sg = buildSegments(utterances, segmentDurationMs);
  const rules = collectRuleEvidence(result);
  const reportBasicInfo = result?.ReportBasicInfo ?? {};
  const reportTask = result?.TaskDetail ?? reportBasicInfo?.Task ?? result?.Task ?? {};
  const taskResult = result?.TaskResult ?? {};
  return validateEcommerceReviewInput({
    input_contract: 'ecommerce_review_skill/v1',
    review_dimensions: ['content_analysis'],
    fd: {
      sg,
      pd: { ps: [], cf: {} },
      wd: { ws: [] },
      scs: {},
      bm: {},
      iad: [],
      ev: {
        scope: 'asr_and_quality_report_only',
        limitations: [
          'comments_unavailable',
          'products_unavailable',
          'interactions_unavailable',
          'window_metrics_unavailable',
          'conversion_metrics_unavailable',
        ],
        quality_report: {
          source: 'livesaas_quality_get_report',
          project_name: text(projectName ?? result?.ProjectName),
          task_id: integer(taskId ?? result?.TaskId ?? reportTask?.ID ?? reportTask?.TaskId ?? reportBasicInfo?.Task?.ID ?? reportBasicInfo?.Task?.TaskId),
          task_status: integer(result?.Status ?? reportTask?.Status ?? reportBasicInfo?.Task?.Status ?? reportBasicInfo?.TaskStatus),
          scenario_id: integer(reportTask?.ScenarioId ?? reportTask?.ScenarioID ?? result?.ScenarioId ?? result?.ScenarioID),
          scenario_name: text(reportTask?.ScenarioName ?? result?.ScenarioName ?? scenarioName),
          overall_conclusion_code: integer(result?.FinalStatus ?? reportBasicInfo?.FinalStatus ?? reportTask?.FinalStatus ?? taskResult?.FinalManualStatus),
          rules,
        },
      },
    },
  });
}

export function buildReviewRenderContext(reportPayload, { segments, scenarioName, projectName, taskId } = {}) {
  const result = unwrapCliPayload(reportPayload) ?? reportPayload;
  const taskResult = result?.TaskResult ?? {};
  const taskDetail = result?.TaskDetail ?? {};
  let sourceMetadata = {};
  try {
    const parsed = JSON.parse(text(taskDetail.Extra));
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) sourceMetadata = parsed;
  } catch {}
  const playUrl = text(taskResult.RecordURL ?? taskResult.RecordUrl ?? taskResult.record_url);
  const vid = text(taskResult.Vid ?? taskResult.VID ?? taskResult.vid);
  const timelineSegments = Array.isArray(segments) ? segments : buildSegments(normalizeAsrUtterances(reportPayload));
  const asrTimeline = timelineSegments.map((segment) => ({
    start_time: segment.st,
    end_time: segment.et,
    text: segment.tx,
  }));
  if (!playUrl && !vid && !asrTimeline.length) return null;
  if (playUrl) {
    let parsed;
    try { parsed = new URL(playUrl); } catch { throw Object.assign(new Error('GetReport RecordURL is not a valid URL'), { code: 'INVALID_PLAYBACK_URL' }); }
    if (!['http:', 'https:'].includes(parsed.protocol)) throw Object.assign(new Error('GetReport RecordURL uses an unsupported protocol'), { code: 'INVALID_PLAYBACK_URL' });
  }
  const pathname = playUrl ? new URL(playUrl).pathname.toLowerCase() : '';
  const format = pathname.endsWith('.mp4') ? 'mp4' : pathname.endsWith('.flv') ? 'flv' : 'hls';
  let sourceLabel = '直播';
  try {
    const hostname = new URL(text(taskDetail.LivePullURL)).hostname.toLowerCase();
    if (/(^|\.)(douyin|douyincdn|amemv)\.com$/.test(hostname)) sourceLabel = '抖音直播';
  } catch {}
  return {
    project_name: text(projectName ?? taskDetail.ProjectName),
    task_id: taskId ?? taskDetail.TaskId ?? taskDetail.ID,
    play_url: playUrl,
    vid,
    format,
    source_label: sourceLabel,
    display_name: text(taskDetail.ActivityName) || text(sourceMetadata.room_title) || text(taskDetail.TaskName),
    account_name: text(sourceMetadata.account_name),
    scenario_id: integer(taskDetail.ScenarioId ?? taskDetail.ScenarioID ?? result?.ScenarioId ?? result?.ScenarioID),
    scenario_name: text(taskDetail.ScenarioName ?? result?.ScenarioName ?? scenarioName ?? sourceMetadata.scenario_name),
    // Preserve machine execution timestamps (Unix seconds), never task updates or ASR offsets.
    inspection_start_time: typeof taskResult.MachineStartTime === 'number' ? taskResult.MachineStartTime : null,
    inspection_end_time: typeof taskResult.MachineEndTime === 'number' ? taskResult.MachineEndTime : null,
    asr_timeline: asrTimeline,
    timed_images: collectTimedImages(reportPayload),
  };
}

export async function writeReviewInput(input, root = REVIEW_INPUT_ROOT, renderContext = null) {
  await mkdir(root, { recursive: true, mode: 0o700 });
  await chmod(root, 0o700);
  const id = randomUUID();
  const path = join(root, `${id}.json`);
  const renderContextPath = join(root, `${id}.render.json`);
  try {
    await writeFile(path, `${JSON.stringify(validateEcommerceReviewInput(input))}\n`, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
    if (renderContext) await writeFile(renderContextPath, `${JSON.stringify(renderContext)}\n`, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
  } catch (error) {
    await Promise.all([rm(path, { force: true }), rm(renderContextPath, { force: true })]);
    throw error;
  }
  return { id, path, renderContextId: renderContext ? id : null };
}

function checkedPath(path, root = REVIEW_INPUT_ROOT) {
  const absoluteRoot = resolve(root);
  const absolutePath = resolve(path);
  if (!absolutePath.startsWith(`${absoluteRoot}${sep}`) || !absolutePath.endsWith('.json')) {
    throw Object.assign(new Error('review input path is outside the managed runtime directory'), { code: 'INVALID_PATH' });
  }
  return absolutePath;
}

export async function readReviewInput(path, root = REVIEW_INPUT_ROOT) {
  return JSON.parse(await readFile(checkedPath(path, root), 'utf8'));
}

export async function readReviewRenderContext(id, root = REVIEW_INPUT_ROOT) {
  const path = checkedPath(join(root, `${artifactId(id)}.render.json`), root);
  const context = JSON.parse(await readFile(path, 'utf8'));
  if (!context || typeof context !== 'object' || Array.isArray(context)) throw Object.assign(new Error('review render context is invalid'), { code: 'INVALID_RENDER_CONTEXT' });
  return context;
}

export async function cleanupReviewInput(path, root = REVIEW_INPUT_ROOT) {
  const inputPath = checkedPath(path, root);
  const id = artifactId(basename(inputPath, '.json'));
  await Promise.all([
    rm(inputPath, { force: true }),
    rm(checkedPath(join(root, `${id}.render.json`), root), { force: true }),
  ]);
  return true;
}
