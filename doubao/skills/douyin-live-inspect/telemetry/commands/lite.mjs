// 启动并观察 Lite Python 命令，从专用管道收集命令元数据并生成命令结束事实。
// 处理进程启动、退出、取消信号和管道故障，保留业务退出码，避免遥测故障重跑业务。
import { settleWithin } from "../utils/common.mjs";
import { createRequire } from "node:module";
import identityProvider from "../utils/identity.mjs";
import sdkReporter from "../utils/reporter.mjs";
import { reportRequest } from "./entry.mjs";
import workflow from "../workflow/state.mjs";
import { liteContract } from "./fields.mjs";

const require = createRequire(import.meta.url);

const { spawn } = require("node:child_process");
function readMetadata(buffer, contract, diagnostic = {}) {
  if (
    diagnostic.metadata_read_status === "io_error" ||
    diagnostic.metadata_read_status === "invalid"
  )
    return {};
  diagnostic.metadata_read_status =
    buffer === undefined ? "unavailable" : "empty";
  if (!buffer?.length || !contract) return {};
  diagnostic.metadata_read_status = "invalid";
  if (buffer.length > 4096) return {};
  try {
    const value = JSON.parse(buffer.toString("utf8"));
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    const metadata = contract.safeFields(value);
    diagnostic.metadata_read_status = Object.keys(metadata).length
      ? "valid"
      : "empty";
    return metadata;
  } catch {
    return {};
  }
}
function recordCommandFinished(
  telemetry,
  contract,
  command,
  metadata,
  identity,
  outcome,
  interrupted,
  context,
  diagnostic = {},
  startupAttemptId,
) {
  if (!telemetry || !contract) return;
  try {
    const deviceId = telemetry.config.disabled
      ? undefined
      : identityProvider.resolveDeviceId();
    const extra = contract.commandMetadata(command, metadata);
    if (!extra) return;
    const childExitCode = outcome.processError
      ? undefined
      : Object.hasOwn(outcome, "childExitCode")
      ? outcome.childExitCode
      : outcome.code;
    Object.assign(
      extra,
      contract.diagnosticFields({
        ...diagnostic,
        diagnostic_schema_version: 1,
        node_version: process.versions.node,
        runtime_arch: process.arch,
        child_exit_code: childExitCode,
      }),
    );
    if (command === "start") {
      if (/^[a-f0-9]{32}$/.test(startupAttemptId || ""))
        extra.startup_attempt_id = startupAttemptId;
      if (/^[a-f0-9]{32}$/.test(context?.task_id || ""))
        extra.entry_task_id = context.task_id;
      extra.startup_stage ||= "unknown";
      extra.startup_outcome ||= outcome.code !== 0 ? "failed" : "unknown";
    }
    if (interrupted || outcome.signal) {
      extra.error_code = "ABORTED";
      delete extra.error_detail;
      extra.error_origin = "signal";
      Object.assign(
        extra,
        contract.diagnosticFields({
          child_signal: outcome.signal || interrupted,
        }),
      );
    } else if (outcome.code !== 0) {
      extra.error_code ||= "OPERATION_FAILED";
      extra.error_origin = outcome.processError
        ? "process_launch"
        : extra.error_origin || "wrapper_fallback";
      if (outcome.processError) {
        const code = outcome.processError;
        if (code === "ENOMEM") extra.error_code = "OUT_OF_MEMORY";
        extra.process_error_code =
          contract.DIAGNOSTIC_ENUMS.process_error_code.includes(code)
            ? code
            : "UNKNOWN";
        extra.error_category =
          code === "ENOENT"
            ? "not_found"
            : ["EACCES", "EPERM"].includes(code)
            ? "permission"
            : "io";
      }
    } else {
      for (const key of [
        "error_code",
        "error_detail",
        "error_origin",
        "error_category",
        "errno",
        "winerror",
        "sqlite_errorcode",
      ])
        delete extra[key];
    }
    telemetry.commandExtra = {
      ...extra,
      ...(context && !extra.task_id ? { task_id: context.task_id } : {}),
      ...identity,
      ...(deviceId ? { deviceId } : {}),
    };
  } catch {
    /* Optional metadata never changes the command result. */
  }
}
async function runLiteCommand(python, entry, args) {
  let context;
  let initialFlow;
  const requests = [];
  const queueRequest = (options) => {
    try {
      const env = { ...process.env };
      const pending = reportRequest({ ...options, env });
      if (env.INSPECT_USAGE_CONTEXT_DIR)
        process.env.INSPECT_USAGE_CONTEXT_DIR = env.INSPECT_USAGE_CONTEXT_DIR;
      requests.push(Promise.resolve(pending).catch(() => {}));
    } catch {
      /* Optional reporting cannot block business startup. */
    }
  };
  if (!args.includes("--help") && !args.includes("-h")) {
    const option = args[0]?.startsWith("batch-") ? "--batch-dir" : "--task-dir";
    const at = args.indexOf(option);
    const inline = args.find((a) => a.startsWith(option + "="));
    const directory = at >= 0 ? args[at + 1] : inline?.slice(option.length + 1);
    if (["start", "start-video", "batch-create"].includes(args[0])) {
      try {
        const tasks = require("../../runtime/lite-task-context.cjs");
        if (process.env.INSPECT_USAGE_CONTEXT_DIR) {
          const value = tasks.readContext(
            process.env.INSPECT_USAGE_CONTEXT_DIR,
          );
          if (value)
            context = {
              task_dir: process.env.INSPECT_USAGE_CONTEXT_DIR,
              task_id: value.task_id,
            };
        } else context = tasks.reserveTask(directory);
      } catch {
        /* Python returns the business validation error; no telemetry may block it. */
      }
      if (context && !directory && args[0] !== "batch-create")
        args = [...args, option, context.task_dir];
      try {
        if (context?.task_id)
          initialFlow = await workflow.begin(
            {
              kind: args[0] === "start" ? "live" : "video",
              batch: args[0] === "batch-create",
              mode: "lite",
              newTaskOnly: true,
            },
            {
              env: {
                ...process.env,
                INSPECT_USAGE_CONTEXT_DIR: context.task_dir,
              },
              emit: () => {},
            },
          );
      } catch {
        /* Optional local flow state cannot block or replay business startup. */
      }
      try {
        queueRequest({ mode: "lite", context });
      } catch {
        /* Optional reporting cannot block business execution. */
      }
    } else if (directory) {
      try {
        const value =
          require("../../runtime/lite-task-context.cjs").readContext(directory);
        context = {
          task_dir: directory,
          ...(value ? { task_id: value.task_id } : {}),
        };
        // Continuations observe the explicit task even if the shell retains an older entry.
        queueRequest({
          mode: "lite",
          select: false,
          context,
          newRequest: !process.env.INSPECT_USAGE_CONTEXT_DIR,
        });
      } catch {
        /* Business validation handles invalid task directories. */
      }
    }
  }
  let telemetry;
  let contract;
  let reporter;
  let identity = {};
  try {
    const { resolveIdentity } = identityProvider;
    identity = await resolveIdentity(process.env);
  } catch {
    /* Identity failures cannot affect command execution. */
  }
  // Identity credentials are input-only. Neither the telemetry SDK nor the
  // business child should inherit raw Doubao or ByteCloud identity tokens.
  delete process.env.DOUBAO_OFFICE_BYTEDANCE_USER_ACCESS_TOKEN;
  for (const key of Object.keys(process.env)) {
    if (key.startsWith("BYTECLOUD_CLI_API_JWT_TOKEN")) delete process.env[key];
  }
  try {
    contract = liteContract;
    reporter = sdkReporter;
    // 只有 Lite 白名单命令才创建命令级遥测；其余命令只跑业务，不额外记命令事件。
    if (Object.hasOwn(contract.COMMAND_FEATURES, args[0])) {
      telemetry = reporter.createTelemetry({
        toolName: "douyin-live-inspect-lite",
      });
    }
  } catch {
    /* Missing or broken optional SDK must not block Python. */
  }

  const reportFlow = (extra) => {
    try {
      if (extra && reporter) {
        requests.push(
          settleWithin(
            [
              reporter.reportEvent("workflow.snapshot", extra, {
                toolName: "douyin-live-inspect",
              }),
            ],
            1500,
          ),
        );
      }
    } catch {
      /* A broken optional sender must not prevent the business spawn. */
    }
  };
  // Persist before Python can emit task events; send concurrently with business.
  reportFlow(initialFlow);

  let channel = false;
  let metadata;
  let issue;
  const diagnostic = {};
  try {
    channel = Boolean(reporter && contract && !reporter.disabled());
  } catch {
    /* Optional SDK configuration must not block business startup. */
  }
  let child;
  let pendingSignal;
  let outcome;
  let startupAttemptId;
  const forward = (signal) => {
    pendingSignal = signal;
    if (child) child.kill(signal);
  };
  const interrupt = () => forward("SIGINT");
  const terminate = () => forward("SIGTERM");
  const hangup = () => forward("SIGHUP");
  process.on("SIGINT", interrupt);
  process.on("SIGTERM", terminate);
  // A supervisor may hang up only the entry PID; reap Python before exiting.
  if (process.platform !== "win32") process.on("SIGHUP", hangup);
  if (process.platform === "win32") process.on("SIGBREAK", interrupt);
  const execute = () =>
    new Promise((resolve, reject) => {
      if (
        args[0] === "start" &&
        !args.includes("--help") &&
        !args.includes("-h")
      ) {
        try {
          startupAttemptId = require("node:crypto")
            .randomBytes(16)
            .toString("hex");
          const pending = reporter.reportEvent(
            "startup.attempt",
            {
              product: "douyin-live-inspect",
              schema_version: 2,
              inspection_mode: "lite",
              record_type: "startup_attempt",
              startup_attempt_id: startupAttemptId,
              ...identity,
              ...(context?.task_id ? { task_id: context.task_id } : {}),
            },
            { toolName: "douyin-live-inspect-lite" },
          );
          // Observe invocation before spawn, without awaiting telemetry delivery.
          requests.push(settleWithin([pending], 1500));
        } catch {
          /* Optional observation must never prevent or replay startup. */
        }
      }
      const launch = (useChannel) => {
        let launched;
        try {
          launched = child = spawn(python, [entry, ...args], {
            stdio: useChannel
              ? ["inherit", "inherit", "inherit", "pipe"]
              : "inherit",
            env: {
              ...process.env,
              BYTEDLIVE_LITE_TELEMETRY_CHILD: "1",
              // fd 3 is a dedicated diagnostic channel; business streams remain inherited.
              INSPECT_TELEMETRY_FD: useChannel ? "3" : "",
              INSPECT_TELEMETRY_METADATA_FILE: "",
              BYTEDLIVE_LITE_TELEMETRY_IDENTITY: JSON.stringify(identity),
              BYTEDLIVE_LITE_TELEMETRY_NODE: process.execPath,
            },
          });
        } catch (error) {
          if (
            useChannel &&
            [
              "EMFILE",
              "ENFILE",
              "ENOMEM",
              "EINVAL",
              "ENOSYS",
              "ENOTSUP",
            ].includes(error.code)
          ) {
            diagnostic.metadata_init_status = "io_error";
            return launch(false);
          }
          reject(error);
          return;
        }
        let drainTimer;
        if (useChannel) {
          try {
            const pipe = child.stdio[3];
            metadata = Buffer.alloc(0);
            diagnostic.metadata_init_status = "ready";
            diagnostic.metadata_transport = "pipe";
            pipe.on("error", () => {
              diagnostic.metadata_read_status = "io_error";
            });
            pipe.on("data", (chunk) => {
              if (diagnostic.metadata_read_status === "invalid") return;
              if (metadata.length + chunk.length > 4096) {
                diagnostic.metadata_read_status = "invalid";
                metadata = Buffer.alloc(0);
                pipe.destroy();
                return;
              }
              metadata = Buffer.concat([metadata, chunk]);
            });
            // A leaked descendant handle must not hold the command open after Python exits.
            child.once("exit", () => {
              drainTimer = setTimeout(() => {
                if (!pipe.readableEnded)
                  diagnostic.metadata_read_status = "io_error";
                pipe.destroy();
              }, 100);
              drainTimer.unref();
            });
          } catch {
            diagnostic.metadata_init_status = "io_error";
            try {
              child.stdio?.[3]?.destroy();
            } catch {}
          }
        }
        launched.once("error", (error) => {
          // Only retry pipe allocation failure before a business PID exists, never a running command.
          if (
            useChannel &&
            !launched.pid &&
            [
              "EMFILE",
              "ENFILE",
              "ENOMEM",
              "EINVAL",
              "ENOSYS",
              "ENOTSUP",
            ].includes(error.code)
          ) {
            diagnostic.metadata_init_status = "io_error";
            metadata = undefined;
            try {
              launched.stdio?.[3]?.destroy();
            } catch {}
            return launch(false);
          }
          resolve({ code: 127, processError: error.code || "UNKNOWN" });
        });
        launched.once("close", (code, signal) => {
          clearTimeout(drainTimer);
          if (launched !== child) return;
          resolve({ code: code ?? 1, childExitCode: code, signal });
        });
        if (pendingSignal) child.kill(pendingSignal);
      };
      launch(channel);
    });
  const handler = async () => {
    outcome = await execute();
    issue = readMetadata(metadata, contract, diagnostic);
    recordCommandFinished(
      telemetry,
      contract,
      args[0],
      issue,
      identity,
      outcome,
      pendingSignal,
      context,
      diagnostic,
      startupAttemptId,
    );
    process.exitCode = outcome.code;
    if (pendingSignal || outcome.signal) {
      const error = new Error("Command interrupted");
      error.name = "AbortError";
      throw error;
    }
  };
  const active = sdkReporter.beginTelemetry(telemetry, args[0]);
  let failure;
  try {
    await handler();
  } catch (error) {
    failure = error || new Error("Command failed");
    if (!outcome) throw error;
  } finally {
    await sdkReporter.finishTelemetry(active, failure);
    issue ||= readMetadata(metadata, contract, diagnostic);
    // Video creation has no command event. Record explicit pre-creation failure
    // on the original flow without turning signals or existing-task misuse into failure.
    if (
      ["start-video", "batch-create"].includes(args[0]) &&
      context?.task_id &&
      outcome &&
      outcome.code !== 0 &&
      !pendingSignal &&
      !outcome.signal
    ) {
      try {
        const code =
          issue.error_code ||
          {
            ENOMEM: "OUT_OF_MEMORY",
            EACCES: "PERMISSION_DENIED",
            EPERM: "PERMISSION_DENIED",
          }[outcome.processError] ||
          "OPERATION_FAILED";
        await workflow.problem("startup", code, true, {
          beforeCreation: true,
          env: { ...process.env, INSPECT_USAGE_CONTEXT_DIR: context.task_dir },
          emit: reportFlow,
        });
      } catch {
        /* Observation never changes the business result. */
      }
    }
    // Failure-only diagnostics also cover commands with no normal command event.
    // No task directory writes and no raw errors/paths/arguments are transported.
    // Python 只在诊断确认落盘后返回 ID；此时补报通道独占发送，父进程不再双发。
    if (
      reporter &&
      issue.failure_component &&
      issue.failure_reason &&
      !issue.diagnostic_event_id
    ) {
      try {
        await settleWithin(
          [
            reporter.reportEvent(
              "runtime.failure",
              {
                product: "douyin-live-inspect",
                schema_version: 2,
                inspection_mode: "lite",
                record_type: "runtime_failure",
                ...identity,
                ...(context?.task_id ? { task_id: context.task_id } : {}),
                ...contract.diagnosticFields(issue),
              },
              { toolName: "douyin-live-inspect-lite" },
            ),
          ],
          1500,
        );
      } catch {}
    }
    // Existing request reporters retain their deadlines, but overlap the business run.
    await Promise.allSettled(requests);
    process.removeListener("SIGINT", interrupt);
    process.removeListener("SIGTERM", terminate);
    if (process.platform !== "win32") process.removeListener("SIGHUP", hangup);
    if (process.platform === "win32")
      process.removeListener("SIGBREAK", interrupt);
  }
  process.exitCode = outcome.code;
  const signal = pendingSignal || outcome.signal;
  if (signal) {
    if (process.platform === "win32")
      process.exitCode = signal === "SIGINT" ? 130 : 143;
    else process.kill(process.pid, signal);
  }
}
export { runLiteCommand, readMetadata, recordCommandFinished };
