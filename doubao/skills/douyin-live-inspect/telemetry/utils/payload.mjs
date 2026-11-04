// 校验并整理任务生命周期、漏斗及观察事件的白名单载荷，再交给统一发送入口。
// 区分有效事实校验与网络预算裁剪，让本地流程先使用完整有效事实；仅本地事件保留原观察路径。
import { SOURCE_ERRORS, CAPTURE_ERRORS } from '../config/lite.mjs';
import reporter from './reporter.mjs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
import { asrFields, runtimeFields, stopFields } from '../diagnostics/events.mjs';
import { validIso, validIdentity, validIdentityEmail, validIdentityUsername } from './common.mjs';
import { liteContract } from '../commands/fields.mjs';
import workflow from '../workflow/state.mjs';
import {
  TASK_COMMANDS,
  UUID,
  TASK_TYPES,
  TASK_RESULTS,
  COUNTS,
  ASR_ENUMS,
  STOP_ENUMS,
  STOP_OPTIONAL_ENUMS,
} from '../config/events.mjs';

const contract = liteContract;
const { EVENTS } = reporter;

const observations = {
  [EVENTS.stop.OBSERVED]: ['stop_observation', stopFields],
  [EVENTS.asr.DIAGNOSTIC]: ['asr_diagnostic', asrFields],
  'runtime.failure': ['runtime_failure', runtimeFields],
};

function validatePayload(value, { fit = true } = {}) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
  if (observations[value.command]) {
    const [record_type, fields] = observations[value.command];
    const facts = fields(value.extra);
    if (!facts) return;
    const extra = {product:'douyin-live-inspect',schema_version:2,inspection_mode:'lite',record_type,
      ...(record_type === 'asr_diagnostic' ? {feature:'speech_recognition'} : {}), ...facts};
    const fitted = !fit || record_type === 'runtime_failure' ? extra : contract.fitExtra(extra);
    return fitted ? {command:value.command,extra:fitted} : undefined;
  }
  const local = value.local_only === true;
  const funnel = value.command === EVENTS.funnel.SNAPSHOT;
  if (!funnel && !TASK_COMMANDS.has(value.command)) return undefined;
  const input = value.extra;
  // 生命周期事件要求严格的结构化载荷，避免把任意业务对象直接发到遥测侧。
  if (!input || typeof input !== 'object' || Array.isArray(input)) return undefined;
  if (
    !TASK_TYPES.has(input.task_type) ||
    !UUID.test(input.telemetry_task_id || '') ||
    !UUID.test(input.lifecycle_event_id || '') ||
    (input.parent_task_id !== undefined && !UUID.test(input.parent_task_id || '')) ||
    !Number.isSafeInteger(input.run_index) ||
    input.run_index < 1 ||
    !validIso(input.task_started_at)
  )
    return undefined;
  if (input.task_finished_at !== undefined && !validIso(input.task_finished_at)) return undefined;
  if (
    input.task_elapsed_ms !== undefined &&
    (!Number.isSafeInteger(input.task_elapsed_ms) || input.task_elapsed_ms < 0)
  )
    return undefined;
  if (input.task_result !== undefined && !TASK_RESULTS.has(input.task_result)) return undefined;
  if (
    !local &&
    value.command === EVENTS.task.FINISHED &&
    (input.task_finished_at === undefined ||
      input.task_elapsed_ms === undefined ||
      input.task_result === undefined)
  )
    return undefined;
  if (input.doubao_user_id !== undefined && !validIdentity(input.doubao_user_id)) return undefined;
  if (input.doubao_email !== undefined && !validIdentityEmail(input.doubao_email)) return undefined;
  if (input.doubao_username !== undefined && !validIdentityUsername(input.doubao_username))
    return undefined;

  for (const key of COUNTS) {
    if (input[key] !== undefined && (!Number.isSafeInteger(input[key]) || input[key] < 0))
      return undefined;
  }
  if (
    funnel &&
    (input.funnel_schema_version !== 1 ||
      !Number.isSafeInteger(input.funnel_revision) ||
      input.funnel_revision < 1 ||
      !/^[0-9a-f]{32}$/i.test(input.task_id || '') ||
      input.task_type === 'live_recap' ||
      !['effective_result', 'quality_ready', 'workflow_success', 'quality_blocked'].every((k) =>
        [0, 1].includes(input[k]),
      ) ||
      !['quality_delivery', 'recap_delivery'].every((k) =>
        ['none', 'ready', 'failed'].includes(input[k]),
      ) ||
      !['none', 'host'].includes(input.delivery_error) ||
      !Number.isSafeInteger(input.funnel_run) ||
      input.funnel_run < 1)
  )
    return undefined;
  if (
    funnel &&
    (input.funnel_run !== input.run_index ||
      (input.task_type === 'live_inspection' &&
        input.quality_ready === 1 &&
        input.effective_result !== 1) ||
      (input.quality_delivery === 'ready' && input.quality_ready !== 1) ||
      (input.workflow_success === 1 &&
        (input.quality_delivery !== 'ready' ||
          (input.task_type === 'live_inspection' && input.recap_delivery !== 'ready'))))
  )
    return undefined;
  const recapFields = {};
  if (input.task_type === 'live_recap') {
    for (const key of ['recap_attempt', 'recap_retry_count']) {
      if (input[key] !== undefined) {
        if (!Number.isSafeInteger(input[key]) || input[key] < (key === 'recap_attempt' ? 1 : 0))
          return;
        recapFields[key] = input[key];
      }
    }
    if (input.recap_failure_reason !== undefined) {
      if (!['none', 'RECAP_TIMEOUT', 'RECAP_ATTEMPT_FAILED'].includes(input.recap_failure_reason))
        return;
      recapFields.recap_failure_reason = input.recap_failure_reason;
    }
    if (input.recap_final !== undefined) {
      if (typeof input.recap_final !== 'boolean') return;
      recapFields.recap_final = input.recap_final;
    }
  }
  if (
    !local &&
    input.task_type === 'live_recap' &&
    value.command === EVENTS.task.FINISHED &&
    input.recap_final === false
  )
    return;
  if (
    input.task_type === 'live_recap' &&
    input.recap_attempt !== undefined &&
    input.recap_retry_count !== input.recap_attempt - 1
  )
    return;
  if (local) {
    if (
      input.task_type !== 'live_recap' ||
      input.recap_final !== false ||
      !['task.finished', 'task.resumed'].includes(value.command) ||
      input.recap_attempt_state !== (value.command === 'task.finished' ? 'failed' : 'retrying') ||
      !Number.isSafeInteger(input.recap_attempt) ||
      input.recap_retry_count !== input.recap_attempt - 1 ||
      !recapFields.recap_failure_reason ||
      input.task_result !== undefined
    )
      return;
    recapFields.recap_attempt_state = input.recap_attempt_state;
  }
  const extra = {
    ...recapFields,
    inspection_mode: 'lite',
    record_type: funnel ? 'task_funnel' : 'task_lifecycle',
    task_type: input.task_type,
    telemetry_task_id: input.telemetry_task_id,
    run_index: input.run_index,
    lifecycle_event_id: input.lifecycle_event_id,
    task_started_at: input.task_started_at,
  };
  for (const key of [
    'parent_task_id',
    'task_finished_at',
    'task_elapsed_ms',
    'task_result',
    'doubao_user_id',
    'doubao_email',
    'doubao_username',
  ]) {
    if (input[key] !== undefined) extra[key] = input[key];
  }
  const fields = value.command === EVENTS.task.FINISHED ? COUNTS : [];
  for (const key of fields) {
    if (input[key] !== undefined) extra[key] = input[key];
  }
  Object.assign(extra, contract.lifecycleMetadata(input.task_type, input));
  if (input.funnel_schema_version === 1) extra.funnel_schema_version = 1;
  if (funnel) {
    // Resolver facts and the last FFmpeg failure have separate causes.
    if (input.task_type === 'live_inspection' && input.capture_status === 'failed') {
      if (SOURCE_ERRORS.includes(input.source_error_code)) {
        if (
          [
            'dns_error',
            'tls_error',
            'network_timeout',
            'connection_error',
            'http_error',
            'invalid_response',
            'permission_denied',
            'unknown',
          ].includes(input.source_failure_kind)
        ) {
          extra.source_failure_kind = input.source_failure_kind;
          if (
            input.source_failure_kind === 'http_error' &&
            Number.isSafeInteger(input.source_http_status) &&
            input.source_http_status >= 400 &&
            input.source_http_status <= 599
          )
            extra.source_http_status = input.source_http_status;
        }
        const reference = input.source_page_ref;
        if (
          typeof reference === 'string' &&
          reference.length <= 160 &&
          /^https:\/\/(?:live\.douyin\.com\/\?live_web_rid=[0-9]+|v\.douyin\.com\/[A-Za-z0-9_-]{4,128}\/)$/.test(
            reference,
          )
        )
          extra.source_page_ref = reference;
        const page = input.source_page_url;
        if (
          typeof page === 'string' &&
          Array.from(page).length <= 512 &&
          !/[\s\x00-\x1f\x7f\\]/u.test(page) &&
          /^https?:\/\/(?:live|www|v)\.douyin\.com(?:[/?#]|$)/.test(page)
        ) {
          try {
            const parsed = new URL(page);
            if (
              !parsed.username &&
              !parsed.password &&
              !parsed.port &&
              !/\.(?:flv|m3u8|mp4|ts)$/i.test(parsed.pathname)
            )
              extra.source_page_url = page;
          } catch {
            /* An invalid optional page must not discard the funnel. */
          }
        }
      } else if (input.source_error_code === 'STREAM_RETRY_EXHAUSTED') {
        if (CAPTURE_ERRORS.includes(input.capture_error_category))
          extra.capture_error_category = input.capture_error_category;
        if (
          Number.isSafeInteger(input.capture_http_status) &&
          input.capture_http_status >= 400 &&
          input.capture_http_status <= 599
        )
          extra.capture_http_status = input.capture_http_status;
        if (Number.isSafeInteger(input.capture_exit_code))
          extra.capture_exit_code = input.capture_exit_code;
      }
    }
    if (
      ['ready', 'blocked', 'pending_media', 'pending_review', 'unknown'].includes(
        input.report_status,
      )
    )
      extra.report_status = input.report_status;
    const flow = workflow;
    if (['success', 'failed', 'insufficient', 'unknown'].includes(input.flow_result))
      extra.flow_result = input.flow_result;
    if (
      ['none', 'entry', 'startup', 'inspection', 'quality', 'recap', 'delivery'].includes(
        input.failure_stage,
      )
    )
      extra.failure_stage = input.failure_stage;
    if (input.failure_reason !== undefined)
      extra.failure_reason = flow.reason(input.failure_reason);
    if (
      [
        'ready',
        'insufficient',
        'failed',
        'blocked',
        'missing',
        'generating',
        'stale',
        'not_required',
      ].includes(input.recap_status)
    )
      extra.recap_status = input.recap_status;
    for (const key of [
      'funnel_revision',
      'funnel_run',
      'effective_result',
      'quality_ready',
      'quality_delivery',
      'recap_delivery',
      'workflow_success',
      'quality_blocked',
      'delivery_error',
    ])
      extra[key] = input[key];
    for (const key of [
      'expected_children',
      'observed_children',
      'asr_pending_segments',
      'media_pending_segments',
      'review_pending_segments',
      'review_ready_segments',
      'reviewed_segments',
      'skipped_segments',
      'pending_child_index',
      'diagnostic_child_index',
    ]) {
      if (input[key] !== undefined) {
        if (!Number.isSafeInteger(input[key]) || input[key] < 0) return undefined;
        extra[key] = input[key];
      }
    }
  }
  // Validate business facts independently of the eventual wire budget.
  const fitted = fit ? contract.fitExtra(extra) : extra;
  return fitted
    ? { command: value.command, extra: fitted, ...(local ? { local_only: true } : {}) }
    : undefined;
}
const taskContract = {
  validatePayload,
  ASR_ENUMS,
  STOP_ENUMS,
  STOP_OPTIONAL_ENUMS,
};
export default taskContract;

export async function deliver(event, context = {}) {
  const payload = taskContract.validatePayload(event, { fit: false });
  if (!payload) return false;
  const env = context.env || process.env;
  if (payload.local_only) {
    try {
      require('../telemetry-observer.cjs').captureEvent(
        {
          command: payload.command,
          observation_only: true,
          skill_version: require('../../scripts/skill-version.cjs').readSkillVersion(),
          cli_name: 'douyin-live-inspect-lite',
          extra: JSON.stringify(payload.extra),
        },
        env,
      );
    } catch {}
    return true;
  }
  return !!(await reporter.reportEvent(payload.command, payload.extra, {
    toolName: 'douyin-live-inspect-lite',
    env,
  }));
}
