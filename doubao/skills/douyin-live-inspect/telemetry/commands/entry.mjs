// 记录 Skill 启动与版本选择，沿用入口上下文保存已观察标记，避免同一请求重复计数。
// 在释放上下文文件锁后限时发送入口事件；已登记的尝试不因发送失败而重放。
import { createRequire } from "node:module";
import * as io from "../utils/io.mjs";
import { EVENTS } from "../config/events.mjs";
import identity from "../utils/identity.mjs";
import reporter, { disabled } from "../utils/reporter.mjs";
import { settleWithin } from "../utils/common.mjs";
import workflow from "../workflow/state.mjs";

const require = createRequire(import.meta.url);

// 记录任务上下文，根据模式选择是否发送事件。
async function claimTask(
  context,
  mode,
  { newRequest = false, select = true } = {},
) {
  const path = require("node:path");
  const { readContext } = require("../../runtime/lite-task-context.cjs");
  const usageOnly = !context.task_id;
  const filename = path.join(
    context.task_dir,
    usageOnly ? ".usage-context.json" : ".task-context.json",
  );
  const release = await io.acquire(filename + ".lock");
  try {
    const state = readContext(context.task_dir, usageOnly) || {};
    if (!usageOnly && state.task_id !== context.task_id)
      throw Error("task binding mismatch");
    const events = [];
    if (!state.started || newRequest) {
      events.push(EVENTS.skill.START);
      state.started = true;
    }
    if (newRequest && !mode) delete state.mode;
    if (mode && select) {
      if (state.mode !== mode || newRequest)
        events.push(EVENTS.skill.VERSION_SELECTED);
      state.mode = mode;
    }
    io.atomicWrite(filename, JSON.stringify(state));
    return events;
  } finally {
    release();
  }
}
// 发送入口事件，根据模式选择是否包含 UID。
async function emitEntrance(
  command,
  {
    mode,
    context,
    env = process.env,
    timeout = 2500,
    scrubIdentity = false,
  } = {},
) {
  const selected = command === EVENTS.skill.VERSION_SELECTED;
  const attribution = await identity.resolveIdentity(env);
  if (scrubIdentity) {
    delete env.DOUBAO_OFFICE_BYTEDANCE_USER_ACCESS_TOKEN;
    for (const key of Object.keys(env))
      if (key.startsWith("BYTECLOUD_CLI_API_JWT_TOKEN")) delete env[key];
  }
  const extra = {
    product: "douyin-live-inspect",
    record_type: "skill_lifecycle",
    feature: selected ? "version_selection" : "skill_start",
    ...(selected ? { inspection_mode: mode } : {}),
    ...workflow.association(env),
    ...(context?.task_id ? { task_id: context.task_id } : {}),
    ...(selected && mode === "lite" && context?.funnel_schema_version === 1
      ? { funnel_schema_version: 1 }
      : {}),
    ...attribution,
  };
  return reporter.reportEvent(command, extra, {
    toolName: "douyin-live-inspect",
    env,
    timeout,
  });
}
// 发送请求事件
async function reportRequest({
  mode,
  context,
  newRequest = false,
  select = true,
  standalone = false,
  env = process.env,
} = {}) {
  if (disabled(env) || ![undefined, "lite", "formal"].includes(mode)) return;
  // 独立旧入口按显式调用计数，不补造任务或隐式启动事件。
  if (standalone)
    return emitEntrance(select ? EVENTS.skill.VERSION_SELECTED : EVENTS.skill.START, {
      mode, context, env, scrubIdentity: true,
    });
  const deadline = Date.now() + 2500;
  try {
    const fs = require("node:fs"),
      {
        readContext,
        reserveTask,
      } = require("../../runtime/lite-task-context.cjs");
    if (!context) {
      if (env.INSPECT_USAGE_CONTEXT_DIR) {
        const task_dir = fs.realpathSync(env.INSPECT_USAGE_CONTEXT_DIR),
          value = readContext(task_dir);
        context = { task_dir, ...(value ? { task_id: value.task_id } : {}) };
      } else context = reserveTask();
    }
    if (!context) return;
    env.INSPECT_USAGE_CONTEXT_DIR = context.task_dir;
    const events = await claimTask(context, mode, { newRequest, select });
    const value =
      context.task_id && mode !== "formal"
        ? readContext(context.task_dir)
        : undefined;
    for (const [index, command] of events.entries()) {
      if (Date.now() >= deadline) break;
      const budget = Math.floor(
        (deadline - Date.now()) / (events.length - index),
      );
      await settleWithin(
        [emitEntrance(command, { mode, context: value, env, timeout: budget })],
        budget,
      );
    }
  } catch {
    /* A claimed attempt is never replayed because telemetry failed. */
  }
}
export { claimTask, reportRequest };
