// 把流程事实转换为 workflow.snapshot 的统计字段：正式版汇总真实任务，Lite 直接使用根投影。
// 统一生成与交付、有效质检、阶段和失败原因的映射，并提供旧 Lite 文件转换；不读写文件或发送。
import { REASONS, STAGES } from '../config/events.mjs';
import { ENUMS } from '../config/lite.mjs';

const reason = (value) => (REASONS.has(value) ? value : 'OPERATION_FAILED');
function aggregate(s) {
  const tasks = Object.values(s.tasks || {}), complete = tasks.length === s.expected;
  const all = (key, value) => complete && tasks.every(t => t[key] === value);
  const generated = key => complete && tasks.every(t => t[key + '_generated'] === true || ['ready', 'delivered'].includes(t[key]));
  const failed = tasks.find(t => t.inspection === 'failed' || t.quality === 'failed' || t.recap === 'failed');
  const insufficient = tasks.find(t => t.quality === 'insufficient' || t.recap === 'insufficient');
  const evidence = failed || insufficient || tasks.find(t => t.failure_reason && t.failure_reason !== 'none') || {};
  return {
    complete, pending: tasks.length < s.expected, created: tasks.some(t => t.created),
    inspected: tasks.every(t => t.inspection === 'completed'),
    qualityGenerated: generated('quality'), recapGenerated: generated('recap'),
    qualityDelivered: all('quality', 'delivered'), recapDelivered: all('recap', 'delivered'),
    failed: failed && (failed.inspection === 'failed' ? 'inspection' : failed.quality === 'failed' ? 'quality' : 'recap'),
    insufficient: insufficient && (insufficient.quality === 'insufficient' ? 'quality' : 'recap'),
    failure_stage: evidence.failure_stage, failure_reason: evidence.failure_reason,
  };
}
// A root funnel already aggregates business results, including every batch child.
function liteProjection(s, e) {
  const inspected = !!e.quality_ready && (s.kind === 'live' || e.effective_result === 1);
  const qualityDelivered = !!e.quality_ready && e.quality_delivery === 'ready';
  const recapInsufficient = e.recap_status === 'insufficient' ||
    (e.recap_status === 'blocked' && e.flow_result === 'insufficient' && e.failure_stage === 'recap');
  const recapDelivered = !recapInsufficient && e.recap_delivery === 'ready';
  return {
    complete: true, pending: false, created: true, inspected,
    qualityGenerated: e.quality_ready === 1 || qualityDelivered,
    recapGenerated: e.recap_status === 'ready' || recapDelivered,
    qualityDelivered, recapDelivered, workflowSuccess: e.workflow_success === 1,
    failed: !inspected && e.flow_result === 'failed' ? 'inspection'
      : e.quality_ready && e.quality_delivery === 'failed' ? 'quality'
      : !recapInsufficient && e.recap_delivery === 'failed' ? 'recap' : undefined,
    insufficient: !e.quality_ready && e.flow_result === 'insufficient' ? 'quality'
      : recapInsufficient ? 'recap' : undefined,
    failure_stage: STAGES.has(e.failure_stage) ? e.failure_stage : 'none',
    failure_reason: reason(e.failure_reason || 'none'),
    ...Object.fromEntries(['source_end_reason', 'live_source_status'].map(key =>
      [key, ENUMS[key].includes(e[key]) ? e[key] : 'unknown'])),
  };
}
function migrateLite(s) {
  // Reading alone never writes, increments revision, or emits historical snapshots.
  if (s.mode === 'lite' && !s.lite_projection) {
    s.lite_projection = {
      ...aggregate(s), workflowSuccess: s.lite_success === true,
      source_end_reason: s.tasks?.root?.source_end_reason || 'unknown',
      live_source_status: s.tasks?.root?.live_source_status || 'unknown',
    };
    delete s.tasks;
    delete s.lite_success;
  }
  return s;
}
function summary(s) {
  const p = s.lite_projection || aggregate(s);
  const live = s.kind === 'live', selected = ['lite', 'formal'].includes(s.mode);
  const success = (s.mode !== 'lite' || p.workflowSuccess) && p.complete &&
    (s.mode === 'lite' && s.kind === 'video' || p.inspected) && p.qualityDelivered &&
    (s.kind === 'video' || live && p.recapDelivered);
  // Report outcomes retain priority over later command failures; success stays terminal.
  const evidence = {...(p.failed || p.insufficient ? p : s.problem || p)};
  if ((p.failed || p.insufficient) && (!evidence.failure_reason || evidence.failure_reason === 'none')) {
    evidence.failure_stage = p.failed || p.insufficient;
    evidence.failure_reason = p.failed
      ? p.failed === 'inspection' ? 'TASK_FAILED' : 'HOST_DELIVERY_FAILED'
      : 'CONTENT_INSUFFICIENT';
  }
  return {
    product: 'douyin-live-inspect', record_type: 'workflow', flow_schema: 2,
    flow_id: s.id, flow_started_at: s.started, inspection_mode: s.mode,
    workflow_kind: live ? 'live' : s.kind === 'video'
      ? s.batch || s.expected > 1 ? 'video_batch' : 'video_single' : 'unknown',
    flow_result: success ? 'success' : p.failed || s.problem?.terminal ? 'failed'
      : p.insufficient ? 'insufficient' : 'unknown',
    version_selected: Number(selected), expected_tasks: s.expected,
    task_created: Number(p.created), inspection_completed: Number(p.complete && p.inspected),
    quality_generated: Number(p.qualityGenerated), recap_generated: Number(live && p.recapGenerated),
    quality_delivered: Number(p.qualityDelivered), recap_delivered: Number(live && p.recapDelivered),
    current_stage: success ? 'complete' : evidence.failure_reason === 'HOST_DELIVERY_FAILED' ? 'delivery'
      : evidence.failure_stage && evidence.failure_stage !== 'none' ? evidence.failure_stage
      : !selected ? 'version_selection' : p.pending ? 'startup'
      : !p.qualityGenerated ? p.inspected ? 'quality' : 'inspection'
      : live && !p.recapGenerated ? 'recap'
      : !p.qualityDelivered || (live && !p.recapDelivered) ? 'delivery' : 'finalizing',
    failure_stage: success ? 'none' : evidence.failure_stage || 'none',
    failure_reason: success ? 'none' : evidence.failure_reason || 'none',
    ...(s.mode === 'lite' && live ? {
      source_end_reason: p.source_end_reason || 'unknown', live_source_status: p.live_source_status || 'unknown',
    } : {}),
    ...(s.uid ? {doubao_user_id: s.uid} : {}),
    ...(s.account_link_schema === 1 ? {
      account_link_schema: 1, account_used: Number(!!s.account_used),
      account_conflict: Number(!!s.account_conflict),
      ...(s.account_id && !s.account_conflict ? { account_id: s.account_id } : {}),
    } : {}),
  };
}
export { summary, reason, liteProjection, migrateLite };
