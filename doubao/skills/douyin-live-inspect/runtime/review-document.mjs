import { constants } from 'node:fs';
import { open } from 'node:fs/promises';
import { extname } from 'node:path';
import { createHash } from 'node:crypto';

export const MAX_REPORT_BYTES = 20 * 1024 * 1024;
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const nonempty = value => typeof value === 'string' && Boolean(value.trim());
const optionalText = (value, keys) => keys.every(key => value[key] === undefined || typeof value[key] === 'string');
function invalid(message, code = 'INVALID_INPUT') {
  throw Object.assign(new Error(message), { code, stage: 'report_document', retryable: false });
}
export function validateTaskId(value) {
  const id = typeof value === 'number' && Number.isSafeInteger(value) ? String(value) : value;
  if (typeof id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$/.test(id)) invalid('task_id must match the report service task ID format');
  return id;
}
export function validateProjectName(value) {
  if (!nonempty(value) || value.length > 256 || /[\x00-\x1f\x7f/\\]/.test(value) || ['.', '..'].includes(value)) invalid('project_name is required and must identify one project');
  return value;
}
function safeTree(value, depth = 0) {
  if (depth > 20) invalid('Report is nested too deeply');
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    if (['__proto__', 'constructor', 'prototype', 'raw_report', 'render_context_id', 'accessToken', 'secretAccessKey', 'sessionToken'].includes(key)) invalid('Report contains a private or unsupported field');
    safeTree(child, depth + 1);
  }
}
function validRows(rows, labels = [1, 2, 3]) {
  return Array.isArray(rows) && rows.every(row => object(row)
    && Number.isSafeInteger(row.start_time) && row.start_time >= 0
    && Number.isSafeInteger(row.end_time) && row.end_time >= row.start_time
    && nonempty(row.content) && Array.isArray(row.labels) && row.labels.every(label => labels.includes(label))
    && Array.isArray(row.tags) && row.tags.every(nonempty)
    && optionalText(row, ['title', 'time_text'])
    && (row.frame_images === undefined || (Array.isArray(row.frame_images) && row.frame_images.every(url => typeof url === 'string')))
    && (row.moment_detail === undefined || (object(row.moment_detail) && optionalText(row.moment_detail, ['title', 'reason', 'suggestion']))));
}
export function validateReviewDocument(report, target = {}) {
  if (!object(report)) invalid('Report must be a JSON object');
  if (report.module_code === 'content_analysis') invalid('Analysis JSON is not an upload document; assemble a complete report with the original task context first');
  if (report.schema_version !== 1) invalid('Unsupported report schema_version; expected 1', 'UNSUPPORTED_REPORT_VERSION');
  const keys = ['schema_version', 'live', 'playbackInfo', 'metrics', 'content', 'modules', 'display_flags', 'report_meta'];
  if (Object.keys(report).some(key => !keys.includes(key))) invalid('Unknown report document field');
  safeTree(report);
  if (!object(report.report_meta)) invalid('Report identity is required');
  const taskId = validateTaskId(report.report_meta.task_id);
  const project = validateProjectName(report.report_meta.project_name);
  if ((target.task_id !== undefined && validateTaskId(target.task_id) !== taskId)
    || (target.project_name !== undefined && validateProjectName(target.project_name) !== project)) invalid('Report does not belong to the requested task/project', 'TASK_BINDING_MISMATCH');
  const analysis = report.modules?.content_analysis;
  if (!object(report.live) || !nonempty(report.live.title) || report.live.review_type !== 'live'
    || !optionalText(report.live, ['duration_text', 'account_name', 'scenario_name', 'vid'])
    || !Array.isArray(report.metrics) || !report.metrics.every(row => object(row) && nonempty(row.label)
      && (typeof row.value === 'string' || (typeof row.value === 'number' && Number.isFinite(row.value))) && optionalText(row, ['sub_label']))
    || !object(report.content) || !Array.isArray(report.content.tabs)
    || !validRows(report.content.segments, [1, 2, 3, 4]) || !report.content.segments.length
    || !object(report.display_flags) || !object(analysis) || analysis.module_code !== 'content_analysis'
    || !['success', 'degraded'].includes(analysis.status) || !validRows(analysis.semantic_segments)) invalid('Incomplete report document');
  for (const key of ['conclusion', 'summary', 'data_scope_note']) if (!nonempty(analysis[key])) invalid(`Report analysis.${key} is required`);
  for (const key of ['recommended_structure', 'recommendations']) {
    if (!Array.isArray(analysis[key]) || !analysis[key].length || !analysis[key].every(nonempty)) invalid(`Report analysis.${key} must contain text`);
  }
  for (const key of ['highlights', 'problems']) {
    if (!Array.isArray(analysis[key]) || !analysis[key].every(row => object(row) && nonempty(row.title) && nonempty(row.reason))) invalid(`Invalid report analysis.${key}`);
  }
  if (report.playbackInfo !== undefined && (!object(report.playbackInfo) || typeof report.playbackInfo.PlayUrl !== 'string')) invalid('Invalid playback information');
  return report;
}
export function parseReviewDocument(bytes, target) {
  if (!bytes.length || bytes.length > MAX_REPORT_BYTES) invalid('Report must be non-empty and at most 20 MiB');
  let report;
  try { report = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
  catch { invalid('Report must contain valid UTF-8 JSON'); }
  return validateReviewDocument(report, target);
}
export async function readReviewFile(file, target) {
  if (typeof file !== 'string' || extname(file).toLowerCase() !== '.json') invalid('file_path must name a JSON file');
  let handle;
  try {
    handle = await open(file, constants.O_RDONLY | constants.O_NOFOLLOW);
    const info = await handle.stat();
    if (!info.isFile() || info.size <= 0 || info.size > MAX_REPORT_BYTES) invalid('Report must be a non-empty regular JSON file of at most 20 MiB');
    const bytes = await handle.readFile();
    return { bytes, report: parseReviewDocument(bytes, target) };
  } catch (error) {
    if (error.stage) throw error;
    invalid('Report must be a readable regular JSON file (no symlinks)');
  } finally { await handle?.close(); }
}

// This digest identifies the exact saved document when a transport failure makes a write ambiguous.
export function reportDigest(report) {
  const canonical = value => Array.isArray(value) ? value.map(canonical) : object(value)
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
  return createHash('sha256').update(JSON.stringify(canonical(report))).digest('hex');
}

export async function readReviewDocument(file, target) {
  return (await readReviewFile(file, target)).report;
}
