"use strict";

// 本文件负责正式版遥测字段合同：
// 把脚本名或 operation 名映射成允许上报的 feature / workflow_kind / scenario_category 等白名单字段。

// A closed vocabulary: never serialize business input as telemetry metadata.
const ENUMS = {
  workflow_kind: ['live', 'video_single', 'video_batch', 'unknown'],
  scenario_category: ['ecommerce', 'finance', 'automotive', 'other', 'unknown'],
  delivery_mode: ['chat', 'local_dashboard', 'remote'],
  asr_policy: ['local_first', 'local_only'],
  asr_backend: ['local', 'mediakit', 'mixed', 'unknown'],
};
const ERRORS = new Set(['INVALID_INPUT', 'AUTH_REQUIRED', 'PERMISSION_DENIED', 'NETWORK_ERROR', 'WRITE_RESULT_UNKNOWN', 'UPLOAD_RESULT_UNKNOWN', 'TASK_BINDING_MISMATCH', 'ORIGINAL_TASK_CONTEXT_REQUIRED', 'TASK_FAILED', 'REPORT_NOT_READY', 'ASR_NOT_FOUND', 'RUNTIME_UNAVAILABLE', 'SETUP_PENDING', 'CANCELLED', 'ABORTED', 'OPERATION_FAILED', 'CREATE_FAILED', 'CREATE_UNCERTAIN', 'LOCAL_VIDEO_PATH_REQUIRED', 'VIDEO_SOURCE_UNAVAILABLE', 'VIDEO_SOURCE_CHANGED', 'VIDEO_INVALID', 'EVIDENCE_CHANGED', 'EVIDENCE_NOT_READY', 'SCENE_REQUIRED', 'RULES_INCOMPLETE', 'FRAMES_NOT_REVIEWED', 'ALREADY_REVIEWED', 'VIDEO_RECAP_NOT_SUPPORTED', 'RECAP_EVIDENCE_CHANGED', 'RECAP_ALREADY_SAVED']);

function safeFields(value = {}) {
  const result = {};
  for (const [key, values] of Object.entries(ENUMS)) if (values.includes(value[key])) result[key] = value[key];
  if (typeof value.doubao_user_id === 'string' && /^\d{1,64}$/.test(value.doubao_user_id)) result.doubao_user_id = value.doubao_user_id;
  if (ERRORS.has(value.error_code)) result.error_code = value.error_code;
  return result;
}

function scenarioCategory(value) {
  return ({'电商':'ecommerce', '金融':'finance', '汽车':'automotive', ecommerce:'ecommerce', finance:'finance', automotive:'automotive'})[value] || (value ? 'other' : 'unknown');
}

function commandMetadata(name, mode, context = {}) {
  const safe = safeFields(context);
  let workflow = 'unknown', feature = 'setup';
  // 这里只根据命令名和白名单上下文推导统计维度，不读取业务正文或媒体内容。
  if (name.startsWith('quality/') || ['chat-status','task-completion-watch','audit-dashboard'].includes(name)) workflow = 'live';
  if (name.startsWith('content/')) workflow = 'video_single';
  if (/project|scenario/.test(name) && name !== 'scene-confirm') feature = 'task_management';
  else if (/recap-|ecommerce-review-/.test(name)) { feature = 'live_recap'; workflow = 'live'; }
  else if (name.startsWith('batch-')) { feature = 'video_batch'; workflow = 'video_batch'; }
  else if (/report|screenshot/.test(name)) feature = 'quality_report';
  else if (['start', 'douyin-task-create'].includes(name) || name === 'quality/+task-create') { feature = 'live_inspection'; workflow = 'live'; }
  else if (name === 'start-video' || name === 'content/+video-task-create') { feature = 'video_inspection'; workflow = 'video_single'; }
  else if (['review-next','review-submit','review-defer','report-delivery-ack','scene-confirm'].includes(name)) feature = safe.workflow_kind === 'video_single' || safe.workflow_kind === 'video_batch' ? 'video_inspection' : 'live_inspection';
  else if (/task-|status|stop|resume|audit|screenshot|delivery-ack/.test(name) && name !== 'auth-status') feature = 'task_management';
  if (feature === 'video_inspection' && safe.workflow_kind === 'video_batch') feature = 'video_batch';
  return {product:'douyin-live-inspect', schema_version:2, inspection_mode:mode, record_type:'command', feature,
    command_name:name, workflow_kind:workflow, ...safe};
}

// Use parsed command names and closed enums only; never inspect request payloads.
function inspectionMetadata(command, env = process.env) {
  if (String(env.VE_SKILL_ID || "").split("/")[0] !== "byted-live-inspect") return undefined;
  const parts = command.split(".");
  const quality = parts[1] === "quality";
  const video = parts[1] === "content" && /^(?:shortcut-video-|video-)/.test(parts[2] || "");
  const batch = video && env.BYTEDLIVE_INSPECT_WORKFLOW_KIND === "video_batch";
  // operation 侧只使用环境变量里的闭集上下文，不反查原始请求参数。
  const workflow = quality ? "live" : video ? (batch ? "video_batch" : "video_single") : "unknown";
  const action = parts.slice(2).join(".");
  let feature = "setup";
  if (quality || video) {
    feature = /(?:report|screenshot)/.test(action) ? "quality_report"
      : /task(?:[.-])create$/.test(action) ? (quality ? "live_inspection" : batch ? "video_batch" : "video_inspection")
        : "task_management";
    if (quality && env.BYTEDLIVE_INSPECT_FEATURE === "live_recap") feature = "live_recap";
  }
  const category = env.BYTEDLIVE_INSPECT_SCENARIO_CATEGORY;
  return {
    product: "douyin-live-inspect", schema_version: 2, inspection_mode: "formal",
    record_type: "command", feature, workflow_kind: workflow,
    scenario_category: ["ecommerce", "finance", "automotive", "other", "unknown"].includes(category) ? category : "unknown",
  };
}


module.exports = { safeFields, scenarioCategory, commandMetadata, inspectionMetadata };
