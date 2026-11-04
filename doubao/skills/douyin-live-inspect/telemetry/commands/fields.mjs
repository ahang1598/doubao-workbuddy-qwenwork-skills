// 集中维护正式版与 Lite 的埋点字段、结果分类和载荷裁剪；不执行业务或网络发送。
// 共用场景分类，保留两版不同的白名单、结果口径及 Lite 1024 字符裁剪顺序。
import { EVENTS } from "../config/events.mjs";
import { enumFields } from "../utils/common.mjs";
import {
  ENUMS as FORMAL_ENUMS,
  ERRORS as FORMAL_ERRORS,
  BUSINESS_REJECTIONS,
  COMMAND_METADATA,
} from "../config/formal.mjs";
import {
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
} from "../config/lite.mjs";

function errorMetadata(error = {}) {
  error = error || {};
  const raw = error.code || error.subtype;
  const code = ["ENOMEM", "ERR_WORKER_OUT_OF_MEMORY"].includes(raw)
    ? "OUT_OF_MEMORY"
    : raw;
  const error_code = FORMAL_ERRORS.has(code) ? code : "OPERATION_FAILED";
  const status = error.http_status ?? error.httpStatus;
  const cancellationCode = ["CANCELLED", "ABORTED", "ABORT_ERR"].includes(code);
  const fault =
    status >= 500 ||
    error.write_occurred === null ||
    error.write_occurred === true ||
    (FORMAL_ERRORS.has(code) &&
      !BUSINESS_REJECTIONS.has(code) &&
      !cancellationCode);
  const cancelled = !fault && (error.name === "AbortError" || cancellationCode);
  const business = !fault && BUSINESS_REJECTIONS.has(code);
  return {
    error_code,
    outcome: cancelled
      ? "cancelled"
      : business
      ? "business_rejected"
      : "failure",
  };
}
function isPermissionRejection(error) {
  return (
    [
      "AccessDenyError",
      "AccessDenied",
      "Forbidden",
      "PERMISSION_DENIED",
    ].includes(error?.code) &&
    errorMetadata(error).outcome === "business_rejected"
  );
}
function formalSafeFields(value = {}) {
  const result = {};
  Object.assign(result, enumFields(value, FORMAL_ENUMS));
  if (
    typeof value.doubao_user_id === "string" &&
    /^\d{1,64}$/.test(value.doubao_user_id)
  )
    result.doubao_user_id = value.doubao_user_id;
  if (FORMAL_ERRORS.has(value.error_code)) result.error_code = value.error_code;
  return result;
}
function scenarioCategory(value) {
  return (
    {
      电商: "ecommerce",
      金融: "finance",
      汽车: "automotive",
      ecommerce: "ecommerce",
      finance: "finance",
      automotive: "automotive",
    }[value] || (value ? "other" : "unknown")
  );
}
// 命令名和操作事件名共用固定映射，动态上下文只调整允许的维度。
function formalCommandMetadata(name, mode, context = {}) {
  const safe = formalSafeFields(context);
  const [feature, workflow_kind] = COMMAND_METADATA[name] || [
    "setup",
    "unknown",
  ];
  return {
    product: "douyin-live-inspect",
    schema_version: 2,
    inspection_mode: mode,
    record_type: "command",
    feature:
      feature === "video_inspection" && safe.workflow_kind === "video_batch"
        ? "video_batch"
        : feature,
    command_name: name,
    workflow_kind,
    ...safe,
  };
}
const operationMetadata = Object.fromEntries(
  Object.entries(EVENTS.operations).map(([operation, event]) => [
    event,
    COMMAND_METADATA[operation],
  ]),
);
function inspectionMetadata(command, env = process.env) {
  if (
    !["douyin-live-inspect", "byted-live-inspect"].includes(
      String(env.VE_SKILL_ID || "").split("/")[0],
    )
  )
    return;
  let [feature, workflow_kind] = operationMetadata[command] || [
    "setup",
    "unknown",
  ];
  if (
    workflow_kind === "video_single" &&
    env.BYTEDLIVE_INSPECT_WORKFLOW_KIND === "video_batch"
  ) {
    workflow_kind = "video_batch";
    if (feature === "video_inspection") feature = "video_batch";
  }
  if (
    workflow_kind === "live" &&
    env.BYTEDLIVE_INSPECT_FEATURE === "live_recap"
  )
    feature = "live_recap";
  return {
    product: "douyin-live-inspect",
    schema_version: 2,
    inspection_mode: "formal",
    record_type: "command",
    feature,
    workflow_kind,
    scenario_category: FORMAL_ENUMS.scenario_category.includes(
      env.BYTEDLIVE_INSPECT_SCENARIO_CATEGORY,
    )
      ? env.BYTEDLIVE_INSPECT_SCENARIO_CATEGORY
      : "unknown",
  };
}
const formalContract = {
  isPermissionRejection,
  errorMetadata,
  safeFields: formalSafeFields,
  scenarioCategory,
  commandMetadata: formalCommandMetadata,
  inspectionMetadata,
};

// 诊断事件字段，根据诊断事件类型和上下文推导统计维度。
// 不包含业务正文或媒体内容，仅用于统计分析。
function diagnosticFields(value = {}) {
  const safe = {};
  if (!value || typeof value !== "object" || Array.isArray(value)) return safe;
  Object.assign(safe, enumFields(value, DIAGNOSTIC_ENUMS));
  for (const key of DIAGNOSTIC_NUMBERS)
    if (Number.isSafeInteger(value[key]) && (!['json_line', 'json_column'].includes(key) || value[key] >= 0)) safe[key] = value[key];
  if (
    Number.isInteger(value.http_status) &&
    value.http_status >= 400 &&
    value.http_status <= 599
  )
    safe.http_status = value.http_status;
  for (const key of ["python_version", "node_version"]) {
    if (
      typeof value[key] === "string" &&
      /^\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(value[key])
    )
      safe[key] = value[key];
  }
  if (
    [
      "x64",
      "arm64",
      "ia32",
      "arm",
      "ppc64",
      "s390x",
      "riscv64",
      "loong64",
    ].includes(value.runtime_arch)
  )
    safe.runtime_arch = value.runtime_arch;
  if (
    typeof value.diagnostic_event_id === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(
      value.diagnostic_event_id,
    )
  )
    safe.diagnostic_event_id = value.diagnostic_event_id;
  if (value.diagnostic_schema_version === 1) safe.diagnostic_schema_version = 1;
  return safe;
}
function safeFields(value = {}) {
  const safe = {};
  if (!value || typeof value !== "object" || Array.isArray(value)) return safe;
  Object.assign(safe, enumFields(value, ENUMS));
  for (const key of ["task_id", "child_task_id"])
    if (typeof value[key] === "string" && /^[0-9a-f]{32}$/i.test(value[key]))
      safe[key] = value[key];
  if (ERRORS.includes(value.error_code)) safe.error_code = value.error_code;
  if (ERROR_DETAILS.includes(value.error_detail))
    safe.error_detail = value.error_detail;
  return { ...safe, ...diagnosticFields(value) };
}
function commandMetadata(command, context = {}) {
  if (!Object.hasOwn(COMMAND_FEATURES, command)) return undefined;
  const safe = safeFields(context);
  if (command !== COMMAND.START) {
    delete safe.startup_stage;
    delete safe.startup_outcome;
  }
  const feature = COMMAND_FEATURES[command];
  const workflow =
    safe.workflow_kind ??
    (["live_inspection", "live_recap"].includes(feature) ? "live" : "unknown");
  return {
    product: "douyin-live-inspect",
    schema_version: 2,
    inspection_mode: "lite",
    record_type: "command",
    feature,
    ...safe,
    workflow_kind: workflow,
  };
}
function lifecycleMetadata(kind, context = {}) {
  const safe = safeFields(context);
  for (const key of DIAGNOSTIC_FIELDS) delete safe[key];
  delete safe.error_code;
  delete safe.error_detail;
  return {
    product: "douyin-live-inspect",
    schema_version: 2,
    feature: kind,
    workflow_kind:
      kind === "video_batch"
        ? "video_batch"
        : kind === "video_inspection"
        ? "video_single"
        : "live",
    ...safe,
  };
}
function fitExtra(input) {
  const result = { ...input };
  const fits = () => Array.from(JSON.stringify(result)).length <= 1024;
  for (const key of [
    "doubao_email",
    "doubao_username",
    "capture_error_category",
    "capture_http_status",
    "capture_exit_code",
  ]) {
    if (fits()) break;
    delete result[key];
  }
  // 字段预算不足时，将房间查询信息保留在 URL 字段本身。
  if (!fits() && typeof result.source_page_ref === "string") {
    result.source_page_url = result.source_page_ref;
    delete result.source_page_ref;
  }
  // 优先保留终态解析失败原因，再处理可选配置和页面上下文。
  // 即使核心字段超长，也应先删除状态，再删除失败原因。
  for (const key of [
    ...DIAGNOSTIC_FIELDS.filter((key) => !CORE_DIAGNOSTICS.has(key)),
    ...DROP_ORDER,
    "skipped_segments",
    "reviewed_segments",
    "review_ready_segments",
    "media_pending_segments",
    "asr_pending_segments",
    "review_pending_segments",
    "diagnostic_child_index",
    "pending_child_index",
    "report_status",
    "error_detail",
    "entry_task_id",
    "startup_attempt_id",
    "source_page_url",
    "source_http_status",
    "source_failure_kind",
    "startup_stage",
    "startup_outcome",
  ]) {
    // 按固定优先级逐步删除低优先级字段，绝不截断 ID 或任意字符串。
    if (fits()) return result;
    delete result[key];
  }
  return fits() ? result : undefined;
}
const liteContract = {
  DIAGNOSTIC_ENUMS,
  DIAGNOSTIC_FIELDS,
  diagnosticFields,
  scenarioCategory,
  ENUMS,
  ERRORS,
  ERROR_DETAILS,
  COMMAND_FEATURES,
  safeFields,
  commandMetadata,
  lifecycleMetadata,
  fitExtra,
};
export { formalContract, liteContract };
