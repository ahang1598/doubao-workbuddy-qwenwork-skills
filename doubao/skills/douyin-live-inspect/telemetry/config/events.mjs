// 统一提供事件名、任务载荷约束、流程失败枚举和诊断补报资格判断。
// 事件名来自注册表，字段合同与补报策略读取两端共用 JSON；本文件不发送事件或修改状态。
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

// 注册表仅在读取时冻结，事件名和中文说明仍由原 JSON 维护。
const { _comments, ...EVENTS } = require('../telemetry-events.json');
for (const group of Object.values(EVENTS)) Object.freeze(group);
Object.freeze(EVENTS);

// 生命周期与观察事件的字段约束。
const { ASR_ENUMS, STOP_ENUMS, STOP_OPTIONAL_ENUMS } = require('./contracts.json');
const TASK_COMMANDS = new Set(Object.values(EVENTS.task));
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TASK_TYPES = new Set(['live_inspection', 'video_inspection', 'video_batch', 'live_recap']);
const TASK_RESULTS = new Set(['completed', 'partial', 'stopped', 'failed']);
const COUNTS = ['asr_skipped_segments', 'asr_skipped_ms'];

// 整体质检流程允许上报的失败阶段与原因。
const STAGES = new Set(['none', 'entry', 'startup', 'inspection', 'quality', 'recap', 'delivery']);
const REASONS = new Set([
  'none',
  'OUT_OF_MEMORY',
  'OPERATION_FAILED',
  'TASK_FAILED',
  'CONTENT_INSUFFICIENT',
  'NO_CAPTURED_CONTENT',
  'NO_REVIEWED_CONTENT',
  'NO_SPEECH',
  'NO_USABLE_TRANSCRIPT',
  'ASR_RETRY_EXHAUSTED',
  'REVIEW_FAILED',
  'RECAP_FAILED',
  'RECAP_TIMEOUT',
  'HOST_DELIVERY_FAILED',
  'REPORT_NOT_READY',
  'RUNTIME_UNAVAILABLE',
  'SETUP_PENDING',
  'INVALID_INPUT',
  'AUTH_REQUIRED',
  'PERMISSION_DENIED',
  'NETWORK_ERROR',
  'REQUEST_TIMEOUT',
  'WRITE_RESULT_UNKNOWN',
  'CREATE_FAILED',
  'CREATE_UNCERTAIN',
  'STREAM_RETRY_EXHAUSTED',
  'XHS_FETCH_FAILED',
  'XHS_PAGE_UNAVAILABLE',
  'XHS_AUTH_REQUIRED',
  'XHS_STREAM_UNAVAILABLE',
  'XHS_LIVE_STATE_UNKNOWN',
  'BROWSER_SOURCE_TIMEOUT','BROWSER_SOURCE_TASK_CLOSED','INVALID_BROWSER_SOURCE',
  'DOUYIN_FETCH_FAILED',
  'DOUYIN_PAGE_UNAVAILABLE',
  'DOUYIN_FLV_UNAVAILABLE',
  'DOUYIN_RESOLVER_UNAVAILABLE',
  'USER_STOP',
  'WATCH_TIMEOUT',
  'HOST_INTERRUPTED',
  'TASK_BINDING_MISMATCH',
  'LOCAL_VIDEO_PATH_REQUIRED',
  'VIDEO_SOURCE_UNAVAILABLE',
  'VIDEO_SOURCE_CHANGED',
  'VIDEO_INVALID',
  'VIDEO_START_FAILED',
]);


// 区分自动持久化和显式提交；容量、重试与确认删除由 outbox 负责。
const policies = require('./delivery.json');
export function persistent(event, explicit = false) {
  const rule = policies[explicit ? 'explicit' : 'automatic'][event?.command];
  const value = event?.extra?.[event.command === 'asr.diagnostic' ? 'phase' : 'failure_component'];
  return rule === true || (Array.isArray(rule) && rule.includes(value));
}

export { EVENTS, TASK_COMMANDS, UUID, TASK_TYPES, TASK_RESULTS, COUNTS,
  ASR_ENUMS, STOP_ENUMS, STOP_OPTIONAL_ENUMS, STAGES, REASONS };
