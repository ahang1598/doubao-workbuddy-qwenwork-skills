// 维护入口关联的整体流程文件，接入正式版任务、Lite 根漏斗、交付确认及流程问题。
// 持锁更新和去重，摘要变化才增加 revision，释放锁后发送快照；读取时兼容转换旧 Lite 状态。
import { summary, reason, liteProjection, migrateLite } from './summary.mjs';
import { createRequire } from 'node:module';
import * as io from '../utils/io.mjs';
import reporter from '../utils/reporter.mjs';
import identity from '../utils/identity.mjs';
import { formalContract } from '../commands/fields.mjs';
import { STAGES } from '../config/events.mjs';

const require = createRequire(import.meta.url);

const fs = require('node:fs');
const path = require('node:path');
const { createHash, randomUUID } = require('node:crypto');

function read(file) {
  return migrateLite(JSON.parse(io.readText(file, 256 * 1024)));
}
function workflowKind(env = process.env, { legacyDirectory } = {}) {
  try {
    if (env.INSPECT_USAGE_CONTEXT_DIR) {
      const root = fs.realpathSync(env.INSPECT_USAGE_CONTEXT_DIR);
      const context = require('../../runtime/lite-task-context.cjs').readContext(root);
      if (!context) return 'unknown';
      let state;
      try {
        state = read(path.join(root, '.workflow-telemetry.json'));
      } catch (error) {
        if (error.code === 'ENOENT' && env.INSPECT_USAGE_CONTEXT_DIR === legacyDirectory) {
          const legacy = env.BYTEDLIVE_INSPECT_WORKFLOW_KIND || env.INSPECT_TELEMETRY_WORKFLOW;
          return ['live', 'video_single', 'video_batch'].includes(legacy) ? legacy : 'unknown';
        }
        return 'unknown';
      }
      if (
        context &&
        state.id === context.task_id &&
        state.mode === 'formal' &&
        Number.isInteger(state.expected) &&
        state.expected >= 1 &&
        state.expected <= 100
      ) {
        if (state.kind === 'live') return 'live';
        if (state.kind === 'video')
          return state.batch === true || state.expected > 1 ? 'video_batch' : 'video_single';
      }
      // A supplied but invalid context must not inherit a stale global batch flag.
      return 'unknown';
    }
  } catch {
    return 'unknown';
  }
  // Compatibility for older standalone callers without an entrance directory.
  const legacy = env.BYTEDLIVE_INSPECT_WORKFLOW_KIND || env.INSPECT_TELEMETRY_WORKFLOW;
  return ['live', 'video_single', 'video_batch'].includes(legacy) ? legacy : 'unknown';
}

async function mutate(change, { env = process.env, emit, strict = false } = {}) {
  if (reporter.disabled(env)) return;
  if (!env.INSPECT_USAGE_CONTEXT_DIR) {
    if (strict) throw Error('original flow context required');
    return;
  }
  let lock, file, output;
  try {
    const root = fs.realpathSync(env.INSPECT_USAGE_CONTEXT_DIR),
      context = require('../../runtime/lite-task-context.cjs').readContext(root);
    if (!context) {
      if (strict) throw Error('original flow context required');
      return;
    }
    file = path.join(root, '.workflow-telemetry.json');
    const lockfile = file + '.lock';
    lock = await io.acquire(lockfile);
    let state;
    try {
      state = read(file);
    } catch (e) {
      if (e.code !== 'ENOENT') throw e;
    }
    if (state && state.id !== context.task_id) throw Error('flow binding mismatch');
    const previous = state ? summary(state) : null;
    state = await change(state, context, previous);
    if (!state) return;
    const next = summary(state);
    if (JSON.stringify(previous) !== JSON.stringify(next)) {
      state.revision = (state.revision || 0) + 1;
      output = { ...next, flow_revision: state.revision };
    }
    io.atomicWrite(file, JSON.stringify(state));
  } catch (e) {
    if (strict) throw e;
  } finally {
    if (lock) lock();
  }
  if (output) {
    try {
      await (
        emit ||
        ((extra) =>
          reporter.reportEvent('workflow.snapshot', extra, {
            toolName: 'douyin-live-inspect',
            env,
          }))
      )(output);
    } catch {
      /* no business replay */
    }
  }
  return output;
}
async function begin(
  { kind, mode, expected, batch = false, newTaskOnly = false } = {},
  options = {},
) {
  return mutate(async (s, c) => {
    // Direct Lite startup may initialize only a fresh request, never backfill a
    // historical task or reset the flow already owned by the business entrance.
    if (
      newTaskOnly &&
      (s ||
        c.started ||
        ['inspection.db', 'batch.json'].some((name) =>
          fs.existsSync(
            path.join(
              options.env?.INSPECT_USAGE_CONTEXT_DIR || process.env.INSPECT_USAGE_CONTEXT_DIR,
              name,
            ),
          ),
        ))
    )
      return s;
    if (!s) {
      const uid = (await identity.resolveIdentity(options.env || process.env)).doubao_user_id;
      s = {
        id: c.task_id,
        started: Math.floor(Date.now() / 1000),
        kind: 'unknown',
        mode: 'unselected',
        expected: 1,
        tasks: {},
        uid,
        account_link_schema: 1,
      };
    }
    if (['live', 'video'].includes(kind)) {
      if (s.kind !== 'unknown' && s.kind !== kind) throw Error('flow kind mismatch');
      s.kind = kind;
    }
    if (batch && s.kind === 'video') s.batch = true;
    if (['lite', 'formal'].includes(mode)) s.mode = mode;
    if (expected !== undefined) {
      if (
        !Number.isInteger(expected) ||
        expected < 1 ||
        expected > 100 ||
        (s.kind !== 'video' && expected !== 1)
      )
        throw Error('invalid task count');
      if ((s.lite_projection?.created || Object.keys(s.tasks || {}).length) && s.expected !== expected) throw Error('task count frozen');
      s.expected = expected;
    }
    // Before creation the selected kind/count may still change.
    if (s.lite_projection && !s.lite_projection.created) delete s.lite_projection;
    return migrateLite(s);
  }, options);
}
function key(identity) {
  if (
    !identity ||
    identity.environment !== 'online' ||
    !identity.profile ||
    !identity.account_id ||
    !identity.project_name ||
    !/^\d+$/.test(String(identity.task_id))
  )
    throw Error('original task identity required');
  return createHash('sha256')
    .update(
      JSON.stringify([
        'online',
        identity.profile,
        String(identity.account_id),
        identity.project_name,
        String(identity.task_id),
      ]),
    )
    .digest('hex');
}
function association(env = process.env) {
  if (reporter.disabled(env) || !env.INSPECT_USAGE_CONTEXT_DIR) return {};
  try {
    const root = fs.realpathSync(env.INSPECT_USAGE_CONTEXT_DIR);
    const context = require('../../runtime/lite-task-context.cjs').readContext(root);
    const state = read(path.join(root, '.workflow-telemetry.json'));
    if (!context || state.id !== context.task_id) return {};
    return { flow_id: state.id, flow_started_at: state.started };
  } catch { return {}; }
}
async function account(accountId, { used = false, flowId, ...options } = {}) {
  if (typeof accountId !== 'string' || !/^\d{1,128}$/.test(accountId) || ['123', '123456'].includes(accountId)) return;
  return mutate(s => {
    if (!s || s.mode !== 'formal' || (flowId && flowId !== s.id)) return s;
    // A workflow cannot silently change owners after selection or task creation.
    if (s.account_id && s.account_id !== accountId) s.account_conflict = true;
    if (!s.account_conflict) s.account_id = accountId;
    if (used) s.account_used = true;
    return s;
  }, options);
}
async function formal(identity, patch, options = {}) {
  return mutate((s) => {
    if (!s) return;
    const id = key(identity);
    let t = s.tasks?.[id];
    if (!t && !patch.created) return s; // Never attach an unrelated existing task by time or device.
    if (!t) {
      if ((s.lite_projection?.created || Object.keys(s.tasks || {}).length) >= s.expected) throw Error('unexpected extra task');
      s.tasks ||= {};
      delete s.lite_projection;
      t = s.tasks[id] = { created: true, inspection: 'unknown', quality: 'none', recap: 'none' };
    }
    s.mode = 'formal';
    const blocked = s.problem?.failure_stage;
    // Only recovery at the affected stage clears an observed blocker.
    if (
      (patch.created && ['entry', 'startup'].includes(blocked)) ||
      (['running', 'completed'].includes(patch.inspection) &&
        ['entry', 'startup', 'inspection'].includes(blocked)) ||
      (patch.quality === 'ready' && blocked === 'quality') ||
      (patch.recap === 'ready' && blocked === 'recap') ||
      (patch.report_saved === true && blocked === 'delivery' && !s.problem?.terminal)
    )
      delete s.problem;
    for (const k of ['inspection', 'quality', 'recap'])
      if (patch[k] !== undefined) {
        const allowed =
          k === 'inspection'
            ? ['unknown', 'running', 'completed', 'failed']
            : ['none', 'ready', 'delivered', 'insufficient', 'failed'];
        if (!allowed.includes(patch[k])) throw Error('invalid stage');
        // Re-reading a ready report must not revoke an acknowledged delivery.
        if (!(patch[k] === 'ready' && t[k] === 'delivered')) t[k] = patch[k];
        if (k !== 'inspection' && ['ready', 'delivered', 'insufficient', 'none'].includes(patch[k]))
          t[k + '_generated'] = ['ready', 'delivered'].includes(patch[k]);
      }
    if (patch.inspection === 'running') {
      t.quality = t.recap = 'none';
      t.quality_generated = t.recap_generated = false;
    }
    // Keep the cause of an unresolved stage when another report is read.
    if (patch.failure_reason || !['failed', 'insufficient'].includes(t[t.failure_stage])) {
      t.failure_stage = STAGES.has(patch.failure_stage) ? patch.failure_stage : 'none';
      t.failure_reason = patch.failure_reason ? reason(patch.failure_reason) : 'none';
    }
    return s;
  }, options);
}
async function ack(identity, kind, outcome, options = {}) {
  if (
    !['quality', 'recap'].includes(kind) ||
    !['delivered', 'insufficient', 'failed'].includes(outcome)
  )
    throw Error('invalid delivery acknowledgement');
  return mutate(
    (s) => {
      if (!s) throw Error('original flow context required');
      const t = s.tasks?.[key(identity)];
      if (!t || t.inspection !== 'completed' || (kind === 'recap' && s.kind !== 'live'))
        throw Error('task is not ready');
      if (outcome === 'delivered' && !['ready', 'delivered'].includes(t[kind]))
        throw Error('report not ready');
      t[kind] = outcome;
      if (outcome === 'insufficient') t[kind + '_generated'] = false;
      if (outcome !== 'delivered' || !['failed', 'insufficient'].includes(t[t.failure_stage])) {
        t.failure_stage = outcome === 'delivered' ? 'none' : kind;
        t.failure_reason =
          outcome === 'insufficient'
            ? 'CONTENT_INSUFFICIENT'
            : outcome === 'failed'
              ? 'HOST_DELIVERY_FAILED'
              : 'none';
      }
      return s;
    },
    { ...options, strict: true },
  );
}
async function problem(stage, code, terminal = false, options = {}) {
  return mutate((s, _context, previous) => {
    if (!s || previous.flow_result === 'success' || (s.problem?.terminal && !terminal)) return s;
    if (
      options.beforeCreation &&
      (previous.task_created ||
        ['inspection.db', 'batch.json'].some((name) =>
          fs.existsSync(
            path.join(
              options.env?.INSPECT_USAGE_CONTEXT_DIR || process.env.INSPECT_USAGE_CONTEXT_DIR,
              name,
            ),
          ),
        ))
    )
      return s;
    s.problem = {
      failure_stage: STAGES.has(stage) ? stage : 'entry',
      failure_reason: reason(code),
      terminal: !!terminal,
    };
    return s;
  }, options);
}
async function lite(event, options = {}) {
  const e = event.extra || {};
  if (
    !['funnel.snapshot', 'task.started', 'task.resumed'].includes(event.command) ||
    e.child_task_id ||
    e.task_type === 'live_recap'
  )
    return;
  return mutate((s) => {
    if (!s || s.id !== e.task_id) return s;
    const order = [e.run_index || 0, e.funnel_revision || 0],
      old = s.lite_order || [-1, -1];
    if (order[0] < old[0] || (order[0] === old[0] && order[1] <= old[1])) return s;
    s.lite_order = order;
    s.mode = 'lite';
    s.batch = e.task_type === 'video_batch';
    delete s.problem;
    // Batch snapshot is already an all-children projection; do not count each child again.
    s.expected = 1;
    s.kind = e.task_type === 'live_inspection' ? 'live' : 'video';
    s.lite_projection = liteProjection(s, e);
    delete s.tasks;
    if (e.flow_result === 'failed')
      s.problem = {
        terminal: true,
        failure_stage: STAGES.has(e.failure_stage) ? e.failure_stage : 'inspection',
        failure_reason: reason(e.failure_reason),
      };
    return s;
  }, options);
}
async function observeEvent(event, env = process.env, { emit } = {}) {
  if (event.command === 'workflow.snapshot') return;
  let extra;
  try { extra = JSON.parse(event.extra || '{}'); } catch { return; }
  if (extra.inspection_mode === 'formal' && extra.record_type === 'command' &&
      extra.feature !== 'setup' && /^[0-9a-f]{32}$/.test(extra.flow_id || ''))
    await account(event.account_id, { used: true, flowId: extra.flow_id, env, emit });
  // 项目发现不代表开始质检；失败也不能推进业务流程阶段。
  if (
    [
      'livesaas.quality.shortcut-project-list',
      'livesaas.content.shortcut-video-project-list',
    ].includes(event.command)
  )
    return;
  if (
    event.result === 'business_rejected' &&
    formalContract.isPermissionRejection({ code: extra.error_code })
  )
    return;
  if (['funnel.snapshot', 'task.started', 'task.resumed'].includes(event.command))
    return lite({ command: event.command, extra }, { env, emit });
  if (
    event.result === 'failure' ||
    event.result === 'business_rejected' ||
    event.result === 'cancelled'
  ) {
    const stage = extra.startup_stage
      ? 'startup'
      : extra.feature === 'live_recap'
        ? 'recap'
        : extra.feature === 'quality_report'
          ? 'quality'
          : 'inspection';
    return problem(
      stage,
      extra.error_code || 'OPERATION_FAILED',
      event.command === 'start' && extra.startup_outcome === 'failed',
      { env },
    );
  }
}
const workflow = { workflowKind, association, account, begin, formal, ack, problem, lite, observeEvent, summary, reason };
export default workflow;
