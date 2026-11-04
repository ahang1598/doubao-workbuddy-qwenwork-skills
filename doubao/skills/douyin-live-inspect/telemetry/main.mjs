// 对业务提供统一埋点入口，管理一次命令或独立观察的调用作用域。
// 把入口、操作结果、报告交付和诊断事实交给对应模块；隔离账号、取消信号及待发送事件。
import {
  executeFormalCommand,
  storage,
  observeAccount,
  commandUserAgent,
  isPreview,
  observeServiceAvailability,
  observeOperation,
  observeResult,
  addCommandContext,
  addScenarioContext,
  commandSignal,
  workflowKind,
} from "./commands/formal.mjs";
import { settleWithin } from "./utils/common.mjs";
import reporter, {
  disabled,
  createTelemetry,
  beginTelemetry,
  finishTelemetry,
  reportEvent,
} from "./utils/reporter.mjs";
import { reportRequest, claimTask } from "./commands/entry.mjs";
import { EVENTS } from "./config/events.mjs";
import workflow from "./workflow/state.mjs";
import { liteContract } from "./commands/fields.mjs";
import identity from "./utils/identity.mjs";
import { formalContract } from "./commands/fields.mjs";
import taskContract from "./utils/payload.mjs";

// 命令状态由执行器持有；这里仅把业务事实接入同一次调用。
function runCommand(options, handler) {
  return executeFormalCommand(
    options.operation || options.command,
    (state) => usingCurrent(state, options, handler),
    options,
  );
}
async function withContext(context, handler) {
  const state = {
    env: context.env || process.env,
    extra: {},
    controller: new AbortController(),
    pending: new Set(),
  };
  try {
    return await storage.run(state, () =>
      usingCurrent(state, context, handler),
    );
  } finally {
    state.closed = true;
    await settleWithin(state.pending, 3000);
  }
}
async function usingCurrent(state, context, handler) {
  const env = context.env || process.env;
  let closed = false;
  const track = (promise) => {
    const pending = Promise.resolve(promise).catch(() => {});
    state.pending.add(pending);
    pending.finally(() => state.pending.delete(pending));
    return pending;
  };
  const observe =
    (fn) =>
    (facts = {}) =>
      closed || state.closed || disabled(env)
        ? Promise.resolve()
        : track(
            Promise.resolve().then(() => storage.run(state, () => fn(facts))),
          );
  const entrance = async (facts, selected) => {
    if (!context.standalone && facts.existing === false)
      await workflow.begin(
        {
          kind: facts.kind,
          mode: facts.mode,
          batch: facts.batch,
          expected: facts.expected,
        },
        { env },
      );
    return reportRequest({
      ...facts,
      standalone: context.standalone,
      select: selected || (!context.standalone && facts.existing === false && !!facts.mode),
      env,
    });
  };
  const current = Object.freeze({
    get disabled() {
      return closed || state.closed || disabled(env);
    },
    setAccountId: (id) => {
      if (!closed && !state.closed && !disabled(env))
        storage.run(state, () => observeAccount(id));
    },
    getUserAgent: () =>
      closed || state.closed
        ? undefined
        : storage.run(state, () => commandUserAgent()),
    skillStart: observe((facts) => entrance(facts, false)),
    versionSelected: observe((facts) => entrance(facts, true)),
    operationCompleted: observe(async (facts) => {
      if (facts.operation === "entry") {
        if (!facts.existing) {
          await workflow.begin(
            { kind: facts.kind, mode: facts.result?.data?.route },
            { env },
          );
          if (!facts.result?.ok || facts.result?.data?.route === "blocked")
            await workflow.problem("entry", "SETUP_PENDING", false, { env });
        }
        return;
      }
      if (isPreview(facts.input, facts.requiresConfirmation)) return;
      // 观察发送并行进行，不占用接口的业务预算；退出时统一等待。
      const availability = observeServiceAvailability(
        facts.operation,
        facts.result,
        env,
      );
      if (env.INSPECT_ENTRY_PROBE === "1") void availability.catch(() => {});
      else track(availability);
      return observeOperation(
        facts.operation,
        operationIdentity(facts.input),
        facts.result,
        { env },
      );
    }),
    reportGenerated: observe(
      (facts) =>
        facts.identity &&
        workflow.formal(
          facts.identity,
          {
            [facts.kind]: facts.quality || "none",
            ...(facts.saved ? { report_saved: true } : {}),
            ...(facts.quality === "insufficient"
              ? {
                  failure_stage: facts.kind,
                  failure_reason: "CONTENT_INSUFFICIENT",
                }
              : {}),
          },
          { env },
        ),
    ),
    deliveryConfirmed: observe(async (facts) => {
      if (!facts.identity) return;
      await workflow.ack(facts.identity, facts.kind, facts.outcome, { env });
      return true;
    }),
    diagnostic: observe((facts) => {
      if (facts.watchStatus)
        return ["timed_out", "cancelled"].includes(facts.watchStatus)
          ? workflow.problem(
              "inspection",
              facts.watchStatus === "timed_out"
                ? "WATCH_TIMEOUT"
                : "HOST_INTERRUPTED",
              false,
              { env },
            )
          : undefined;
      if (facts.reportError)
        return workflow.problem(
          facts.quality === "ready" ? "delivery" : "recap",
          facts.reportError,
          false,
          { env },
        );
    }),
  });
  try {
    return await handler(current);
  } finally {
    closed = true;
  }
}
const telemetry = { runCommand, withContext };
// 格式化操作输入，提取 profile、account_id、project_name、task_id。
function operationIdentity(input = {}) {
  const normalized = Object.fromEntries(
    Object.entries(input || {}).map(([k, v]) => [
      k.replace(/[_-]/g, "").toLowerCase(),
      v,
    ]),
  );
  return {
    profile: normalized.profile,
    account_id: normalized.accountid,
    project_name: normalized.projectname,
    task_id: normalized.taskid,
  };
}

export {
  EVENTS,
  disabled,
  reporter,
  liteContract,
  formalContract,
  identity,
  workflow,
  taskContract,
  createTelemetry,
  beginTelemetry,
  finishTelemetry,
  reportEvent,
  reportRequest,
  claimTask,
  runCommand,
  observeResult,
  observeAccount,
  addCommandContext,
  addScenarioContext,
  commandSignal,
  commandUserAgent,
  isPreview,
  workflowKind,
  observeServiceAvailability,
  observeOperation,
};
export default telemetry;

export { reportRuntimeFailure } from "./diagnostics/events.mjs";
