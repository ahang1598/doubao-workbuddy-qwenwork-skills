"use strict";

// 本文件负责 Lite 遥测字段合同：
// 限定 Lite 命令、生命周期事件允许携带的字段，并在发送前做超长裁剪。

const {lite: COMMAND} = require("../../runtime/telemetry-events.json");

// Closed vocabulary only. Business input and exception text are never metadata.
const ENUMS = {
  live_source_status: ['live', 'not_live', 'unknown'],
  capture_status: ['pending', 'running', 'ended', 'stopped', 'failed'],
  source_end_reason: ['offline', 'stream_retry_exhausted', 'source_resolution_failed', 'capture_failed', 'user_stop', 'duration_limit', 'unknown'],
  source_error_code: ['none', 'STREAM_RETRY_EXHAUSTED', 'DOUYIN_FETCH_FAILED', 'DOUYIN_PAGE_UNAVAILABLE', 'DOUYIN_FLV_UNAVAILABLE', 'DOUYIN_RESOLVER_UNAVAILABLE', 'INVALID_INPUT'],
  workflow_kind: ['live', 'video_single', 'video_batch', 'unknown'],
  scenario_category: ['ecommerce', 'finance', 'automotive', 'other', 'unknown'],
  delivery_mode: ['chat', 'local_dashboard', 'html_snapshot'],
  asr_policy: ['remote_first', 'local_first', 'local_only'],
};
const DIAGNOSTIC_ENUMS = {
  startup_stage: ['input_validation', 'dependency_prepare', 'task_create', 'credential_prepare', 'dashboard_prepare', 'worker_launch', 'watcher_launch', 'completed', 'unknown'],
  startup_outcome: ['setup_pending', 'started', 'failed', 'unknown'],
  error_origin: ['business', 'process_launch', 'signal', 'wrapper_fallback'],
  error_category: ['invalid_input', 'permission', 'not_found', 'file_conflict', 'io', 'sqlite', 'timeout', 'import', 'runtime', 'other'],
  metadata_transport: ['pipe'],
  metadata_init_status: ['ready', 'timeout', 'helper_failed', 'io_error'],
  metadata_read_status: ['valid', 'empty', 'unavailable', 'invalid', 'io_error'],
  child_signal: ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGBREAK', 'SIGKILL', 'SIGABRT', 'SIGSEGV'],
  process_error_code: ['ENOENT', 'EACCES', 'EPERM', 'ENOEXEC', 'EINVAL', 'ENOMEM', 'EAGAIN', 'UNKNOWN'],
};
const DIAGNOSTIC_NUMBERS = ['errno', 'winerror', 'sqlite_errorcode', 'child_exit_code'];
const DIAGNOSTIC_FIELDS = ['python_version', 'node_version', 'runtime_arch', ...DIAGNOSTIC_NUMBERS,
  'process_error_code', 'error_category', 'child_signal', 'startup_outcome',
  'metadata_transport', 'startup_stage', 'error_origin', 'metadata_read_status', 'metadata_init_status', 'diagnostic_schema_version'];
function diagnosticFields(value = {}) {
  const safe = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) return safe;
  for (const [key, allowed] of Object.entries(DIAGNOSTIC_ENUMS)) if (allowed.includes(value[key])) safe[key] = value[key];
  for (const key of DIAGNOSTIC_NUMBERS) if (Number.isSafeInteger(value[key])) safe[key] = value[key];
  for (const key of ['python_version', 'node_version']) {
    if (typeof value[key] === 'string' && /^\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(value[key])) safe[key] = value[key];
  }
  if (['x64', 'arm64', 'ia32', 'arm', 'ppc64', 's390x', 'riscv64', 'loong64'].includes(value.runtime_arch)) safe.runtime_arch = value.runtime_arch;
  if (value.diagnostic_schema_version === 1) safe.diagnostic_schema_version = 1;
  return safe;
}
const ERRORS = ['INVALID_INPUT', 'OUT_OF_MEMORY', 'OPERATION_FAILED', 'ABORTED', 'RUNTIME_UNAVAILABLE',
  'LOCAL_VIDEO_PATH_REQUIRED', 'VIDEO_SOURCE_UNAVAILABLE', 'VIDEO_SOURCE_CHANGED', 'VIDEO_INVALID',
  'SEGMENT_SKIPPED', 'ASR_EVIDENCE_MISSING', 'VIDEO_RECAP_NOT_SUPPORTED', 'RECAP_EVIDENCE_CHANGED',
  'RECAP_ALREADY_SAVED', 'EVIDENCE_CHANGED', 'FRAMES_NOT_REVIEWED', 'RULES_INCOMPLETE',
  'ALREADY_REVIEWED', 'EVIDENCE_NOT_READY', 'SCENE_REQUIRED'];
const ERROR_DETAILS = ['ARGUMENT_PARSE_ERROR', 'STOP_USER_INSTRUCTION_REQUIRED',
  'STOP_TASK_NOT_FOUND', 'STOP_CONFIRM_DISCARD_REQUIRED',
  'STOP_ORDINARY_REQUIRES_DRAIN', 'STOP_LIVE_TASK_REQUIRED', 'STOP_STATE_PENDING'];
const COMMAND_FEATURES = {
  [COMMAND.START]: 'live_inspection', [COMMAND.STOP]: 'task_management',
  [COMMAND.REPORT]: 'quality_report', [COMMAND.RECAP_REPORT]: 'live_recap',
};
function safeFields(value = {}) {
  const safe = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) return safe;
  for (const [key, allowed] of Object.entries(ENUMS)) if (allowed.includes(value[key])) safe[key] = value[key];
  for (const key of ['task_id','child_task_id']) if (typeof value[key] === 'string' && /^[0-9a-f]{32}$/i.test(value[key])) safe[key] = value[key];
  if (ERRORS.includes(value.error_code)) safe.error_code = value.error_code;
  if (ERROR_DETAILS.includes(value.error_detail)) safe.error_detail = value.error_detail;
  return {...safe, ...diagnosticFields(value)};
}
function commandMetadata(command, context = {}, legacyContext = {}) {
  if (typeof context === 'string') {
    // 兼容旧调用方式：非 lite 上下文仍交回正式版合同处理。
    if (context !== 'lite') return require('../../runtime/formal-telemetry-contract.cjs').commandMetadata(command, context, legacyContext);
    context = legacyContext;
  }
  if (!Object.hasOwn(COMMAND_FEATURES, command)) return undefined;
  const safe = safeFields(context);
  if (command !== COMMAND.START) { delete safe.startup_stage; delete safe.startup_outcome; }
  const feature = COMMAND_FEATURES[command];
  const workflow = safe.workflow_kind ?? (['live_inspection', 'live_recap'].includes(feature) ? 'live' : 'unknown');
  return {product: 'douyin-live-inspect', schema_version: 2, inspection_mode: 'lite',
    record_type: 'command', feature, ...safe, workflow_kind: workflow};
}
function lifecycleMetadata(kind, context = {}) {
  const safe = safeFields(context);
  for (const key of DIAGNOSTIC_FIELDS) delete safe[key];
  delete safe.error_code;
  delete safe.error_detail;
  return {product: 'douyin-live-inspect', schema_version: 2, feature: kind,
    workflow_kind: kind === 'video_batch' ? 'video_batch' : kind === 'video_inspection' ? 'video_single' : 'live', ...safe};
}
const DROP_ORDER = ['feature', 'product', 'delivery_mode', 'asr_policy', 'scenario_category', 'workflow_kind', 'schema_version'];
function fitExtra(input) {
  const result = {...input};
  const fits = () => Array.from(JSON.stringify(result)).length <= 1024;
  for (const key of [...DIAGNOSTIC_FIELDS, ...DROP_ORDER]) {
    // 按固定优先级逐步删除低优先级字段，绝不截断 ID 或任意字符串。
    if (fits()) return result;
    delete result[key];
  }
  return fits() ? result : undefined;
}
const {scenarioCategory} = require('../../runtime/formal-telemetry-contract.cjs');
module.exports = {DIAGNOSTIC_ENUMS, DIAGNOSTIC_FIELDS, diagnosticFields, scenarioCategory, ENUMS, ERRORS, ERROR_DETAILS, COMMAND_FEATURES, safeFields, commandMetadata, lifecycleMetadata, fitExtra};
