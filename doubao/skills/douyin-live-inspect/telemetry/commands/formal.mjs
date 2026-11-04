// 包装正式版命令和嵌套操作，隔离调用上下文、账号、UA 与取消信号。
// 将操作结果映射为命令事件和流程观察，处理预演排除、外层计数抑制及服务未开通观察。
import { formalContract } from "./fields.mjs";
import workflow from "../workflow/state.mjs";
import { settleWithin } from "../utils/common.mjs";
import { AsyncLocalStorage } from "node:async_hooks";
import { EVENTS } from "../config/events.mjs";
import reporter, {
  disabled,
  beginTelemetry,
  finishTelemetry,
  reportEvent,
} from "../utils/reporter.mjs";
import { reportRequest } from "./entry.mjs";
import identity from "../utils/identity.mjs";

const contract = formalContract,
  flow = workflow;
const legacyDirectories = new WeakMap();
function workflowKind(env = process.env) {
  const state = storage.getStore();
  return state?.env === env
    ? state.workflow
    : flow.workflowKind(env, { legacyDirectory: legacyDirectories.get(env) });
}
const storage = new AsyncLocalStorage();
const operations = EVENTS.operations;
const scripts = new Set(Object.values(EVENTS.formal));
const publicSetup = new Set([
  EVENTS.formal.DETECT_ACCOUNT_ENTRY,
  EVENTS.formal.DETECT_RUNTIME_MODE,
  EVENTS.formal.CHECK_LOGIN_CAPABILITY,
  EVENTS.formal.AUTH_STATUS,
]);
function addCommandContext(value) {
  const state = storage.getStore();
  if (state) Object.assign(state.extra, contract.safeFields(value));
}
function addScenarioContext(value) {
  addCommandContext({ scenario_category: contract.scenarioCategory(value) });
}
function observeAccount(account) {
  const state = storage.getStore();
  if (!state) return;
  // ponytail: 只拦截已知样例账号；其他人工测试用 BYTEDLIVE_TELEMETRY_DISABLED=1。
  if (account === "123" || account === "123456") state.testAccount = true;
  if (
    typeof account !== "string" ||
    !/^\d{1,128}$/.test(account) ||
    (state.account && state.account !== account)
  )
    state.accountConflict = true;
  else state.account = account;
}
function commandSignal() {
  return storage.getStore()?.controller?.signal;
}
function commandUserAgent() {
  try {
    return storage.getStore()?.telemetry?.getUserAgent();
  } catch {
    return undefined;
  }
}
function observeError(error) {
  const state = storage.getStore();
  if (!state) return;
  const metadata = contract.errorMetadata(error);
  state.failed = true;
  state.cancelled ||= metadata.outcome === "cancelled";
  // A later business guard must not hide a previously observed runtime fault.
  if (state.outcome !== "failure") {
    state.outcome = metadata.outcome;
    addCommandContext({ error_code: metadata.error_code });
  }
}
function observeResult(value) {
  if (value?.ok === false) observeError(value.error || value.data?.error || {});
  return value;
}
function isPreview(input, confirmationRequired = false) {
  // 统一兼容 dry_run / dry-run / dryRun 这类控制字段写法。
  const controls = Object.fromEntries(
    Object.entries(input || {}).map(([key, value]) => [
      key.replace(/[_-]/g, "").toLowerCase(),
      value,
    ]),
  );
  return (
    controls.dryrun === true ||
    controls.plan === true ||
    (confirmationRequired && !controls.confirmtoken)
  );
}
async function executeFormalCommand(
  name,
  handler,
  { skip = false, env = process.env } = {},
) {
  const parent = storage.getStore();
  const state = {
    env,
    extra: {},
    controller: new AbortController(),
    pending: new Set(),
  };
  const untracked = async () => {
    const inherited = parent || state;
    try {
      return await handler(inherited);
    } finally {
      // 嵌套的未计数调用沿用父作用域，由父级收尾，避免在业务中途等待网络。
      if (!parent) {
        state.closed = true;
        await settleWithin(state.pending, 3000);
      }
    }
  };
  // 能力探测和排除的命令只执行一次业务，不创建 SDK 命令。
  if (env.INSPECT_ENTRY_PROBE === "1") return untracked();
  // 内层调用直接复用外层上下文，避免同一条调用链被重复记成多次入口事件。
  if (
    (parent && (parent.name === name || !operations[name])) ||
    skip ||
    process.argv.includes("--help") ||
    process.argv.includes("-h") ||
    disabled(env) ||
    (!operations[name] && !scripts.has(name))
  )
    return untracked();
  // Resolve before the legacy request fallback reserves a directory without flow state.
  const workflow = workflowKind(env);
  if (!parent) {
    const select = [
      EVENTS.formal.DOUYIN_TASK_CREATE,
      "quality/+task-create",
      "content/+video-task-create",
    ].includes(name);
    const hadDirectory = Boolean(env.INSPECT_USAGE_CONTEXT_DIR);
    await reportRequest({ mode: "formal", select, env });
    if (!hadDirectory && env.INSPECT_USAGE_CONTEXT_DIR)
      legacyDirectories.set(env, env.INSPECT_USAGE_CONTEXT_DIR);
  }
  // workflow 包装器本身不抢占上报权，真正的 operation 才是最终事件所有者。
  if (parent && operations[name]) parent.serviceEvents = true;
  let telemetry;
  try {
    telemetry = reporter.createTelemetry({
      toolName: "douyin-live-inspect",
      env,
      isolated: Boolean(operations[name]),
    });
    // telemetry 初始化失败时直接退化为纯业务执行，不影响命令本身。
  } catch {
    return untracked();
  }
  const canonicalCommand = operations[name] || name;
  // 正式版脚本命令与底层 operation 共用同一套 extra 合同，但来源不同。
  const extra = operations[name]
    ? contract.inspectionMetadata(canonicalCommand, {
        ...env,
        BYTEDLIVE_INSPECT_WORKFLOW_KIND: workflow,
        VE_SKILL_ID: process.env.VE_SKILL_ID,
        BYTEDLIVE_INSPECT_FEATURE:
          env.BYTEDLIVE_INSPECT_FEATURE ||
          (parent?.extra.feature === "live_recap" ? "live_recap" : undefined),
      })
    : contract.commandMetadata(
        name,
        publicSetup.has(name) ? "unselected" : "formal",
        {
          workflow_kind: workflow === "unknown" ? undefined : workflow,
          scenario_category:
            env.BYTEDLIVE_INSPECT_SCENARIO_CATEGORY || "unknown",
        },
      );
  try {
    Object.assign(extra, await identity.resolveIdentity(env), {
      deviceId: identity.resolveDeviceId(env),
    });
  } catch {
    /* optional attribution */
  }
  Object.assign(extra, contract.safeFields(parent?.extra || {}));
  // state 是整次命令期间的共享态：既给业务读，也给 telemetry 收口时用。
  Object.assign(state, {
    name,
    telemetry,
    extra,
    workflow,
    env,
    account: parent?.account,
    accountConflict: parent?.accountConflict,
  });
  // workflow 包装层让出 reporter；底层 service 已上报时，这里不再重复发送。
  // 即便 SDK reporter 不可用，也不能因此重放业务逻辑。
  try {
    const reporter = telemetry.getReporter();
    telemetry.reporter = {
      report: (event) => {
        if (state.serviceEvents || state.testAccount) return;
        // Classify the emitted event, never clear process.exitCode or change the
        // handler result. SDK exit-code checks must not turn a business guard
        // back into a runtime failure.
        if (state.outcome === "failure") {
          event = {
            ...event,
            result: "failure",
            error_message: "Inspection command failed",
          };
        } else if (!state.cancelled && state.outcome === "business_rejected") {
          event = {
            ...event,
            result: "business_rejected",
            error_message: undefined,
          };
        }
        return reporter.report(event);
      },
    };
  } catch {
    /* Older SDK fixture without a reporter. */
  }
  let signalReceived;
  const signals =
    process.platform === "win32"
      ? ["SIGINT", "SIGTERM"]
      : ["SIGINT", "SIGTERM", "SIGHUP"];
  const listeners = new Map(
    signals.map((signal) => [
      signal,
      () => {
        signalReceived = signal;
        state.cancelled = true;
        // 把进程级中断翻译成可传递给业务代码的 AbortSignal。
        state.controller.abort(
          Object.assign(new Error("Command cancelled"), {
            name: "AbortError",
            code: "CANCELLED",
          }),
        );
      },
    ]),
  );
  for (const [signal, listener] of listeners) process.on(signal, listener);
  let business, originalError;
  // 收到取消后先给业务一小段时间自我收敛，避免已经被服务端接受的写操作被过早打断。
  // 若业务不响应 AbortSignal，再由本地兜底超时结束等待。
  let cancelTimer;
  const cancelled = new Promise((_, reject) =>
    state.controller.signal.addEventListener(
      "abort",
      () => {
        cancelTimer = setTimeout(
          () => reject(state.controller.signal.reason),
          250,
        );
      },
      { once: true },
    ),
  );
  // 将共享状态挂到异步上下文后执行，确保 handler 内部任意层级都能读到统一 telemetry 状态。
  await storage.run(state, async () => {
    const active = beginTelemetry(telemetry, canonicalCommand);
    let failure;
    try {
      try {
        business = Promise.resolve()
          .then(() => handler(state))
          .then(observeResult);
        await Promise.race([business, cancelled]);
      } catch (error) {
        originalError = error;
        observeError(error);
      }
      if (!state.failed && Number(process.exitCode) > 0) observeError({});
      try {
        telemetry.commandExtra = { ...state.extra, ...flow.association(env) };
        // 仅在账号来源单一且可信时写入 accountId，避免多账号冲突导致错误归因。
        if (state.account && !state.accountConflict)
          telemetry.setAccountId(state.account);
      } catch {
        /* metadata must not alter execution */
      }
      if (state.failed || state.cancelled) {
        const safe = new Error("Inspection command failed");
        if (state.cancelled && state.outcome !== "failure")
          safe.name = "AbortError";
        failure = safe;
      }
    } finally {
      state.closed = true;
      await finishTelemetry(active, failure, state.pending);
    }
  });
  clearTimeout(cancelTimer);
  for (const [signal, listener] of listeners)
    process.removeListener(signal, listener);
  if (signalReceived) {
    // telemetry 尽力收尾后，恢复进程收到信号时原本应有的退出语义。
    if (process.platform === "win32")
      process.exit(signalReceived === "SIGINT" ? 130 : 143);
    else {
      process.removeAllListeners(signalReceived);
      process.kill(process.pid, signalReceived);
      await new Promise(() => {});
    }
  }
  if (originalError) throw originalError;
  return business;
}
async function observeServiceAvailability(
  operation,
  result,
  env = process.env,
) {
  if (
    !operations[operation] ||
    result?.ok !== false ||
    result.error?.code !== "AccessDenyError" ||
    contract.errorMetadata(result.error).outcome !== "business_rejected"
  )
    return;
  try {
    await reportEvent(
      EVENTS.service.NOT_ENABLED,
      {
        product: "douyin-live-inspect",
        record_type: "service_availability",
        feature: "setup",
        inspection_mode: "formal",
        workflow_kind: operation.startsWith("quality/")
          ? "live"
          : workflowKind(env) === "video_batch"
          ? "video_batch"
          : "video_single",
        reason: "formal_service_not_enabled",
        operation: operations[operation],
        ...(await identity.resolveIdentity(env)),
      },
      { toolName: "douyin-live-inspect", env },
    );
  } catch {
    /* 可用性观察不能改变接口结果或触发重试。 */
  }
}
async function observeOperation(operation, input, response, options = {}) {
  try {
    // 仅记录任务创建、状态查询和报告查询三类生命周期节点。
    if (!/^(quality|content)\//.test(operation)) return;
    const result = response?.data?.response?.data?.Result;
    const create = /\+.*task-create$/.test(operation),
      get = /\+.*task-get$/.test(operation),
      report = /\+.*report-get$/.test(operation);
    if (!create && !get && !report) return;
    if (!response?.ok) {
      if (formalContract.isPermissionRejection(response.error)) return;
      const code = response?.error?.code;
      await flow.problem(
        create ? "startup" : report ? "quality" : "inspection",
        code || "OPERATION_FAILED",
        create &&
          response?.error?.write_occurred === false &&
          ![
            "AUTH_REQUIRED",
            "SETUP_PENDING",
            "REQUEST_TIMEOUT",
            "NETWORK_ERROR",
            "REPORT_NOT_READY",
          ].includes(code),
        options,
      );
      return;
    }
    const identity = {
      environment: "online",
      profile: response.meta?.profile || input.profile,
      account_id: response.meta?.account_id || input.account_id,
      project_name: input.project_name,
      task_id: create ? result?.TaskId ?? result?.TaskID : input.task_id,
    };
    if (create) {
      if (!identity.task_id)
        return flow.problem("startup", "CREATE_UNCERTAIN", false, options);
      await flow.formal(identity, { created: true }, options);
    } else if (get) {
      const status = Number(result?.Status);
      if ([3, 4].includes(status))
        await flow.formal(identity, { inspection: "completed" }, options);
      else if (status === 5)
        await flow.formal(
          identity,
          {
            inspection: "failed",
            failure_stage: "inspection",
            failure_reason: "TASK_FAILED",
          },
          options,
        );
      else if ([1, 2].includes(status))
        await flow.formal(identity, { inspection: "running" }, options);
    } else if (report) {
      if (
        result &&
        Object.hasOwn(result, "TaskResult") &&
        result.TaskResult !== null &&
        result.TaskResult !== ""
      )
        await flow.formal(identity, { quality: "ready" }, options);
      else await flow.problem("quality", "REPORT_NOT_READY", false, options);
    }
  } catch {
    /* telemetry cannot alter API results */
  }
}

export {
  legacyDirectories,
  workflowKind,
  storage,
  operations,
  scripts,
  publicSetup,
  addCommandContext,
  addScenarioContext,
  observeAccount,
  commandSignal,
  commandUserAgent,
  observeError,
  observeResult,
  isPreview,
  executeFormalCommand,
  observeServiceAvailability,
  observeOperation,
};
