// 构造 ASR、运行时诊断及停止/云电脑观察的安全字段，生成诊断事件和可持久化副本。
// 保留各入口的校验约定与稳定事件标识；网络发送交给 reporter，持久化和重试交给 outbox。
import { EVENTS, persistent, UUID, ASR_ENUMS, STOP_ENUMS, STOP_OPTIONAL_ENUMS } from '../config/events.mjs';
import reporter, { disabled } from '../utils/reporter.mjs';
import { liteContract as contract } from '../commands/fields.mjs';
import identity from '../utils/identity.mjs';
import { uuid5, validIdentity, enumFields, validIso, owner } from '../utils/common.mjs';

// 运行时与 ASR 诊断构造，以及补报记录的安全副本。
async function reportRuntimeFailure(facts, env = process.env) {
  if (disabled(env)) return;
  const value = contract.diagnosticFields(facts);
  if (!value.failure_component || !value.failure_reason) return;
  return reporter.reportEvent(
    EVENTS.runtime.FAILURE,
    {
      product: 'douyin-live-inspect',
      schema_version: 2,
      inspection_mode: 'lite',
      record_type: 'runtime_failure',
      ...(await identity.resolveIdentity(env)),
      ...value,
    },
    { toolName: 'douyin-live-inspect-lite', env },
  );
}
function asr(task, fields) {
  const extra = asrFields({...fields, task_id:task.task_id || task.id,
    doubao_user_id:task._telemetry?.owner?.doubao_user_id}, false);
  if (!extra) return null;
  extra.diagnostic_event_id = uuid5(extra.task_id,
    ['segment_id','attempt','route_generation','phase'].map(k => extra[k] ?? '').join(':'));
  return {command:EVENTS.asr.DIAGNOSTIC, extra};
}
function safeDiagnostic(event) {
  if (!event?.extra || !persistent(event, true)) return null;
  if (event.command === EVENTS.asr.DIAGNOSTIC)
    return asr({task_id:event.extra.task_id,_telemetry:{owner:event.extra}}, event.extra);
  const extra = event.command === EVENTS.stop.OBSERVED
    ? stopFields(event.extra) : runtimeFields(event.extra, true);
  return extra ? {command:event.command, extra} : null;
}
export { reportRuntimeFailure, asr, safeDiagnostic };

// ASR 与运行时诊断字段：构造可丢弃非法可选项，严格输入必须拒绝。
export function asrFields(input, strict = true) {
  if (!input || typeof input !== 'object' || Array.isArray(input) ||
      !/^[0-9a-f]{32}$/i.test(input.task_id || '') ||
      !strict && typeof input.task_id !== 'string') return;
  if (strict && (!UUID.test(input.diagnostic_event_id || '') ||
      !({attempt:['started'],result:['success','failed'],route:['selected'],recovery:['success','failed']}[input.phase] || []).includes(input.outcome))) return;
  const extra = strict
    ? {task_id:input.task_id,diagnostic_event_id:input.diagnostic_event_id,segment_id:input.segment_id}
    : {task_id:input.task_id};
  for (const [key, allowed] of Object.entries(ASR_ENUMS)) {
    if (allowed.includes(input[key])) extra[key] = input[key];
    else if (strict && input[key] !== undefined) return;
  }
  for (const key of ['segment_id','attempt','route_generation','recovery_elapsed_ms','http_status']) {
    const value = input[key];
    if (Number.isInteger(value) && value >= 0 && value <= 2 ** 31 &&
        (key !== 'http_status' || value >= 400 && value <= 599)) extra[key] = value;
    else if (key === 'segment_id' || strict && value !== undefined) return;
  }
  if (!extra.phase) return;
  if (validIdentity(input.doubao_user_id)) extra.doubao_user_id = input.doubao_user_id;
  return extra;
}

export function runtimeFields(input, stored = false) {
  if (!input) return;
  // 保留历史补报文件的标识格式与非负计数约定。
  const uuid = stored ? /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/ : UUID;
  if ((stored && typeof input.diagnostic_event_id !== 'string') ||
      !uuid.test(input.diagnostic_event_id || '')) return;
  const extra = stored ? enumFields(input, contract.DIAGNOSTIC_ENUMS) : contract.safeFields(input);
  if (!['failure_component','failure_reason','recovery_outcome'].every(k => extra[k])) return;
  if (stored) {
    for (const key of ['json_line','json_column','reviewed_segments','unresolved_segments','recovery_attempts','bytes_received','bytes_total','prepare_attempts','recovery_elapsed_ms'])
      if (Number.isSafeInteger(input[key]) && input[key] >= 0) extra[key] = input[key];
    if (Number.isInteger(input.http_status) && input.http_status >= 400 && input.http_status <= 599) extra.http_status = input.http_status;
    if (typeof input.task_id === 'string' && /^[0-9a-f]{32}$/.test(input.task_id)) extra.task_id = input.task_id;
  }
  extra.diagnostic_event_id = input.diagnostic_event_id;
  return extra;
}

// 停止来源仅描述事实，不代表任务已经完成。
function stopFields(input) {
  if (
    !input ||
    !/^[0-9a-f]{32}$/i.test(input.task_id || '') ||
    !UUID.test(input.diagnostic_event_id || '') ||
    !validIso(input.observed_at) ||
    !Number.isSafeInteger(input.run_index) ||
    input.run_index < 1 ||
    !Number.isSafeInteger(input.stop_revision) ||
    input.stop_revision < 1
  )
    return;
  const extra = {
    task_id: input.task_id,
    diagnostic_event_id: input.diagnostic_event_id,
    observed_at: input.observed_at,
    run_index: input.run_index,
    stop_revision: input.stop_revision,
  };
  for (const [key, allowed] of Object.entries(STOP_ENUMS)) {
    if (!allowed.includes(input[key])) return;
    extra[key] = input[key];
  }
  Object.assign(
    extra,
    enumFields(input, STOP_OPTIONAL_ENUMS),
    enumFields(input, contract.DIAGNOSTIC_ENUMS, [
      'blocking_reason',
      'failure_component',
      'failure_reason',
    ]),
    enumFields(input, contract.ENUMS, ['capture_status', 'source_end_reason', 'source_error_code']),
  );
  return extra;
}
export { stopFields };
