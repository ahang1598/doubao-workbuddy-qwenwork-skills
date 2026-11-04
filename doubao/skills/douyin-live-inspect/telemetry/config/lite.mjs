// 读取两端共用的 contracts.json，补充 Lite 命令功能映射、诊断字段集合和裁剪优先级。
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { ENUMS, DIAGNOSTIC_ENUMS, ERRORS, ERROR_DETAILS } = require('./contracts.json');

const { lite: COMMAND } = require('../telemetry-events.json');
const SOURCE_ERRORS = [
  'XHS_FETCH_FAILED',
  'XHS_PAGE_UNAVAILABLE',
  'XHS_AUTH_REQUIRED',
  'XHS_STREAM_UNAVAILABLE',
  'XHS_LIVE_STATE_UNKNOWN',
  'BROWSER_SOURCE_TIMEOUT','BROWSER_SOURCE_TASK_CLOSED','INVALID_BROWSER_SOURCE',
  'DOUYIN_FETCH_FAILED', // 从抖音获取视频失败
  'DOUYIN_PAGE_UNAVAILABLE',
  'DOUYIN_FLV_UNAVAILABLE',
  'DOUYIN_RESOLVER_UNAVAILABLE',
];
const CAPTURE_ERRORS = [
  'http_error',
  'process_exit',
  'encoder_unavailable',
  'permission_denied',
  'tls_error',
  'network_timeout',
  'connection_error',
  'invalid_media',
  'stream_missing',
];

const DIAGNOSTIC_NUMBERS = [
  'json_line',
  'json_column',
  'reviewed_segments',
  'unresolved_segments',
  'recovery_attempts',
  'bytes_received',
  'bytes_total',
  'prepare_attempts',
  'recovery_elapsed_ms',
  'errno',
  'winerror',
  'sqlite_errorcode',
  'child_exit_code',
];
const DIAGNOSTIC_FIELDS = [
  'recap_input_code',
  'download_source',
  'network_failure_kind',
  'watchdog_stage',
  'blocking_reason',
  'recovery_action',
  'http_status',
  'diagnostic_event_id',
  'prepare_stage',
  'recovery_outcome',
  'recovery_code',
  'failure_component',
  'failure_reason',
  'python_version',
  'node_version',
  'runtime_arch',
  ...DIAGNOSTIC_NUMBERS,
  'process_error_code',
  'error_category',
  'child_signal',
  'startup_outcome',
  'metadata_transport',
  'startup_stage',
  'error_origin',
  'metadata_read_status',
  'metadata_init_status',
  'diagnostic_schema_version',
];

const COMMAND_FEATURES = {
  [COMMAND.START]: 'live_inspection',
  [COMMAND.STOP]: 'task_management',
  [COMMAND.REPORT]: 'quality_report',
  [COMMAND.RECAP_REPORT]: 'live_recap',
};
const DROP_ORDER = ['delivery_mode', 'asr_policy', 'scenario_category'];
const CORE_DIAGNOSTICS = new Set([
  'failure_component',
  'failure_reason',
  'startup_outcome',
  'startup_stage',
  'diagnostic_event_id',
  'recovery_code',
  'recovery_outcome',
  'prepare_stage',
]);

export {
  SOURCE_ERRORS,
  CAPTURE_ERRORS,
  COMMAND,
  ENUMS,
  DIAGNOSTIC_ENUMS,
  DIAGNOSTIC_NUMBERS,
  DIAGNOSTIC_FIELDS,
  ERRORS,
  ERROR_DETAILS,
  COMMAND_FEATURES,
  DROP_ORDER,
  CORE_DIAGNOSTICS,
};
