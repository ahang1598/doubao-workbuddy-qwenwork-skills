"use strict";

// 本文件负责 Lite 任务生命周期遥测：
// 校验生命周期与 funnel.snapshot 载荷，只允许白名单字段通过，并以 best effort 方式发送。


const contract = require("./telemetry-contract.cjs");
const {EVENTS, disabled, reportEvent} = require("../../runtime/telemetry-reporter.cjs");
const TASK_COMMANDS = new Set(Object.values(EVENTS.task));

const MAX_INPUT_BYTES = 16 * 1024;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TASK_TYPES = new Set(["live_inspection", "video_inspection", "video_batch", "live_recap"]);
const TASK_RESULTS = new Set(["completed", "partial", "stopped", "failed"]);

const COUNTS = ['asr_skipped_segments', 'asr_skipped_ms'];

function validIso(value) {
  return typeof value === "string" && value.length <= 64 &&
    /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value) &&
    Number.isFinite(Date.parse(value));
}

function validIdentity(id) {
  return typeof id === "string" && /^\d{1,64}$/.test(id);
}

function validIdentityEmail(email) {
  return typeof email === "string" && email.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validIdentityUsername(name) {
  return typeof name === "string" && name.length >= 1 && name.length <= 64 && !/\s/.test(name) && !name.includes("@");
}

function validatePayload(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const funnel = value.command === EVENTS.funnel.SNAPSHOT;
  if (!funnel && !TASK_COMMANDS.has(value.command)) return undefined;
  const input = value.extra;
  // 生命周期事件要求严格的结构化载荷，避免把任意业务对象直接发到遥测侧。
  if (!input || typeof input !== "object" || Array.isArray(input)) return undefined;
  if (!TASK_TYPES.has(input.task_type) || !UUID.test(input.telemetry_task_id || "") ||
      !UUID.test(input.lifecycle_event_id || "") ||
      (input.parent_task_id !== undefined && !UUID.test(input.parent_task_id || "")) ||
      !Number.isSafeInteger(input.run_index) || input.run_index < 1 ||
      !validIso(input.task_started_at)) return undefined;
  if (input.task_finished_at !== undefined && !validIso(input.task_finished_at)) return undefined;
  if (input.task_elapsed_ms !== undefined &&
      (!Number.isSafeInteger(input.task_elapsed_ms) || input.task_elapsed_ms < 0)) return undefined;
  if (input.task_result !== undefined && !TASK_RESULTS.has(input.task_result)) return undefined;
  if (value.command === EVENTS.task.FINISHED &&
      (input.task_finished_at === undefined || input.task_elapsed_ms === undefined || input.task_result === undefined)) return undefined;
  if (input.doubao_user_id !== undefined && !validIdentity(input.doubao_user_id)) return undefined;
  if (input.doubao_email !== undefined && !validIdentityEmail(input.doubao_email)) return undefined;
  if (input.doubao_username !== undefined && !validIdentityUsername(input.doubao_username)) return undefined;

  for (const key of COUNTS) {
    if (input[key] !== undefined && (!Number.isSafeInteger(input[key]) || input[key] < 0)) return undefined;
  }
  if (funnel && (input.funnel_schema_version !== 1 || !Number.isSafeInteger(input.funnel_revision) || input.funnel_revision < 1 ||
      !/^[0-9a-f]{32}$/i.test(input.task_id || '') || input.task_type === 'live_recap' ||
      !['effective_result','quality_ready','workflow_success','quality_blocked'].every(k => [0,1].includes(input[k])) ||
      !['quality_delivery','recap_delivery'].every(k => ['none','ready','failed'].includes(input[k])) ||
      !['none','host'].includes(input.delivery_error) || !Number.isSafeInteger(input.funnel_run) || input.funnel_run < 1)) return undefined;
  if (funnel && (input.funnel_run !== input.run_index ||
      (input.quality_ready === 1 && input.effective_result !== 1) ||
      (input.quality_delivery === 'ready' && input.quality_ready !== 1) ||
      (input.workflow_success === 1 && (input.quality_delivery !== 'ready' ||
        (input.task_type === 'live_inspection' && input.recap_delivery !== 'ready'))))) return undefined;
  const extra = {
    inspection_mode: "lite",
    record_type: funnel ? "task_funnel" : "task_lifecycle",
    task_type: input.task_type,
    telemetry_task_id: input.telemetry_task_id,
    run_index: input.run_index,
    lifecycle_event_id: input.lifecycle_event_id,
    task_started_at: input.task_started_at,
  };
  for (const key of ["parent_task_id", "task_finished_at", "task_elapsed_ms", "task_result",
    "doubao_user_id", "doubao_email", "doubao_username"]) {
    if (input[key] !== undefined) extra[key] = input[key];
  }
  const fields = value.command === EVENTS.task.FINISHED ? COUNTS : [];
  for (const key of fields) {
    if (input[key] !== undefined) extra[key] = input[key];
  }
  Object.assign(extra, contract.lifecycleMetadata(input.task_type, input));
  if (input.funnel_schema_version === 1) extra.funnel_schema_version = 1;
  if (funnel) {
    const flow = require('../../runtime/workflow-telemetry.cjs');
    if (['success','failed','insufficient','unknown'].includes(input.flow_result)) extra.flow_result=input.flow_result;
    if (['none','entry','startup','inspection','quality','recap','delivery'].includes(input.failure_stage)) extra.failure_stage=input.failure_stage;
    if(input.failure_reason!==undefined)extra.failure_reason=flow.reason(input.failure_reason);
    if(['ready','insufficient','failed','blocked','missing','generating','stale','not_required'].includes(input.recap_status))extra.recap_status=input.recap_status;
    for (const key of ['funnel_revision','funnel_run','effective_result','quality_ready','quality_delivery',
      'recap_delivery','workflow_success','quality_blocked','delivery_error']) extra[key] = input[key];
    for (const key of ['expected_children','observed_children']) {
      if (input[key] !== undefined) {
        if (!Number.isSafeInteger(input[key]) || input[key] < 0) return undefined;
        extra[key] = input[key];
      }
    }
  }
  // Workflow attribution needs the immutable user ID, not optional display identity.
  // Preserve normal legacy payloads; shed display fields only if a funnel would be lost.
  if(funnel && !contract.fitExtra(extra)){delete extra.doubao_email;delete extra.doubao_username;}
  const fitted = contract.fitExtra(extra);
  return fitted ? { command: value.command, extra: fitted } : undefined;
}

function readInput(stream = process.stdin) {
  return new Promise(resolve => {
    const chunks = [];
    let size = 0;
    let rejected = false;
    stream.on("data", chunk => {
      size += chunk.length;
      if (size > MAX_INPUT_BYTES) rejected = true;
      else chunks.push(chunk);
    });
    stream.on("error", () => resolve(undefined));
    stream.on("end", () => {
      if (rejected) return resolve(undefined);
      try { resolve(validatePayload(JSON.parse(Buffer.concat(chunks).toString("utf8")))); }
      catch { resolve(undefined); }
    });
  });
}

async function report(env = process.env, stream = process.stdin) {
  if (disabled(env)) return;
  const payload = await readInput(stream);
  if (!payload) return;
  try {
    // 生命周期事件是事务提交后的旁路发送；失败时绝不影响业务收尾。
    await reportEvent(payload.command, payload.extra, {toolName: 'byted-live-inspect-lite', env});
  } catch { /* Lifecycle telemetry is always best effort. */ }
}

if (require.main === module) {
  // This reporter is intentionally detached from the business process. Bound
  // its total lifetime even if an SDK or network implementation never settles.
  setTimeout(() => process.exit(0), 3000).unref();
  report().catch(() => {});
}
module.exports = { readInput, report, validatePayload };
