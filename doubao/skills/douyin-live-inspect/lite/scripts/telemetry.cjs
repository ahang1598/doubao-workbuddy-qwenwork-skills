"use strict";

// 本文件负责 Lite 命令的 Node -> Python 遥测桥接：
// 在启动 Python 业务进程的同时，给白名单命令补充命令级遥测，并隔离 metadata 文件与身份上下文。

const { spawn } = require("node:child_process");

function readMetadata(buffer, contract, diagnostic = {}) {
  if (diagnostic.metadata_read_status === 'io_error' || diagnostic.metadata_read_status === 'invalid') return {};
  diagnostic.metadata_read_status = buffer === undefined ? 'unavailable' : 'empty';
  if (!buffer?.length || !contract) return {};
  diagnostic.metadata_read_status = 'invalid';
  if (buffer.length > 4096) return {};
  try {
    const value = JSON.parse(buffer.toString('utf8'));
    if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
    const metadata = contract.safeFields(value);
    diagnostic.metadata_read_status = Object.keys(metadata).length ? 'valid' : 'empty';
    return metadata;
  } catch { return {}; }
}

function record_command_finished(telemetry, contract, command, metadata, identity, outcome, interrupted, context, diagnostic = {}) {
  if (!telemetry || !contract) return;
  try {
    const deviceId = telemetry.config.disabled ? undefined : require('./telemetry-identity.cjs').resolveDeviceId();
    if (deviceId) telemetry.addExtra({ deviceId });
    const extra = contract.commandMetadata(command, metadata);
    if (!extra) return;
    const childExitCode = outcome.processError ? undefined : Object.hasOwn(outcome, 'childExitCode') ? outcome.childExitCode : outcome.code;
    Object.assign(extra, contract.diagnosticFields({...diagnostic, diagnostic_schema_version: 1,
      node_version: process.versions.node, runtime_arch: process.arch, child_exit_code: childExitCode}));
    if (command === 'start') {
      extra.startup_stage ||= 'unknown';
      extra.startup_outcome ||= outcome.code !== 0 ? 'failed' : 'unknown';
    }
    if (interrupted || outcome.signal) {
      extra.error_code = 'ABORTED'; delete extra.error_detail;
      extra.error_origin = 'signal';
      Object.assign(extra, contract.diagnosticFields({child_signal: outcome.signal || interrupted}));
    } else if (outcome.code !== 0) {
      extra.error_code ||= 'OPERATION_FAILED';
      extra.error_origin = outcome.processError ? 'process_launch' : extra.error_origin || 'wrapper_fallback';
      if (outcome.processError) {
        const code = outcome.processError;
        if (code === 'ENOMEM') extra.error_code = 'OUT_OF_MEMORY';
        extra.process_error_code = contract.DIAGNOSTIC_ENUMS.process_error_code.includes(code) ? code : 'UNKNOWN';
        extra.error_category = code === 'ENOENT' ? 'not_found' : ['EACCES', 'EPERM'].includes(code) ? 'permission' : 'io';
      }
    } else {
      for (const key of ['error_code', 'error_detail', 'error_origin', 'error_category', 'errno', 'winerror', 'sqlite_errorcode']) delete extra[key];
    }
    const fitted = contract.fitExtra({...extra, ...(context && !extra.task_id ? {task_id:context.task_id} : {}), ...identity, ...(deviceId ? { deviceId } : {})});
    if (fitted) telemetry.addExtra(fitted);
  } catch { /* Optional metadata never changes the command result. */ }
}

async function run(python, entry, args) {
  let context;
  const requests = [];
  const reportRequest = options => {
    try {
      const env = {...process.env};
      const pending = require('../../runtime/request-telemetry.cjs').reportRequest({...options, env});
      if (env.INSPECT_USAGE_CONTEXT_DIR) process.env.INSPECT_USAGE_CONTEXT_DIR = env.INSPECT_USAGE_CONTEXT_DIR;
      requests.push(Promise.resolve(pending).catch(() => {}));
    }
    catch { /* Optional reporting cannot block business startup. */ }
  };
  if (!args.includes('--help') && !args.includes('-h')) {
    const option = args[0]?.startsWith('batch-') ? '--batch-dir' : '--task-dir';
    const at = args.indexOf(option);
    const inline = args.find(a => a.startsWith(option + '='));
    const directory = at >= 0 ? args[at + 1] : inline?.slice(option.length + 1);
    if (['start', 'start-video', 'batch-create'].includes(args[0])) {
      try { context = require('../../runtime/lite-task-context.cjs').reserveTask(directory || process.env.INSPECT_USAGE_CONTEXT_DIR); }
      catch { /* Python returns the business validation error; no telemetry may block it. */ }
      if (context && !directory && args[0] !== 'batch-create') args = [...args, option, context.task_dir];
      try { reportRequest({mode:'lite', context}); }
      catch { /* Optional reporting cannot block business execution. */ }
    } else if (directory) {
      try {
        const value = require('../../runtime/lite-task-context.cjs').readContext(directory);
        context = {task_dir:directory, ...(value ? {task_id:value.task_id} : {})};
        // A standalone command starts a request; a business-entry continuation carries its directory.
        reportRequest({mode:'lite', select:false,
          context:process.env.INSPECT_USAGE_CONTEXT_DIR ? undefined : context, newRequest:!process.env.INSPECT_USAGE_CONTEXT_DIR});
      } catch { /* Business validation handles invalid task directories. */ }
    }
  }
  let telemetry;
  let contract;
  let runEvent;
  let identity = {};
  try {
    const { resolveIdentity } = require("./telemetry-identity.cjs");
    identity = await resolveIdentity(process.env);
  } catch { /* Identity failures cannot affect command execution. */ }
  // Identity credentials are input-only. Neither the telemetry SDK nor the
  // business child should inherit raw Doubao or ByteCloud identity tokens.
  delete process.env.DOUBAO_OFFICE_BYTEDANCE_USER_ACCESS_TOKEN;
  for (const key of Object.keys(process.env)) {
    if (key.startsWith("BYTECLOUD_CLI_API_JWT_TOKEN")) delete process.env[key];
  }
  try {
    contract = require("./telemetry-contract.cjs");
    const reporter = require('../../runtime/telemetry-reporter.cjs');
    runEvent = reporter.runEvent;
    // 只有 Lite 白名单命令才创建命令级遥测；其余命令只跑业务，不额外记命令事件。
    if (Object.hasOwn(contract.COMMAND_FEATURES, args[0])) {
      telemetry = reporter.createTelemetry({toolName: 'byted-live-inspect-lite'});
    }
  } catch { /* Missing or broken optional SDK must not block Python. */ }

  let channel = false;
  let metadata;
  const diagnostic = {};
  try { channel = Boolean(telemetry && contract && !telemetry.config?.disabled); }
  catch { /* Optional SDK configuration must not block business startup. */ }
  let child;
  let pendingSignal;
  let outcome;
  let business;
  const forward = signal => {
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
  const execute = () => {
    // Memoize before SDK invocation: even an SDK failure after starting the
    // handler must never replay start/review-submit or consume stdin twice.
    business ??= new Promise((resolve, reject) => {
      const launch = useChannel => {
        let launched;
        try {
          launched = child = spawn(python, [entry, ...args], {
            stdio: useChannel ? ['inherit', 'inherit', 'inherit', 'pipe'] : "inherit", env: {
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
          if (useChannel && ['EMFILE', 'ENFILE', 'ENOMEM', 'EINVAL', 'ENOSYS', 'ENOTSUP'].includes(error.code)) {
            diagnostic.metadata_init_status = 'io_error';
            return launch(false);
          }
          reject(error); return;
        }
        let drainTimer;
        if (useChannel) {
          try {
            const pipe = child.stdio[3];
            metadata = Buffer.alloc(0);
            diagnostic.metadata_init_status = 'ready';
            diagnostic.metadata_transport = 'pipe';
            pipe.on('error', () => { diagnostic.metadata_read_status = 'io_error'; });
            pipe.on('data', chunk => {
              if (diagnostic.metadata_read_status === 'invalid') return;
              if (metadata.length + chunk.length > 4096) {
                diagnostic.metadata_read_status = 'invalid'; metadata = Buffer.alloc(0);
                pipe.destroy(); return;
              }
              metadata = Buffer.concat([metadata, chunk]);
            });
            // A leaked descendant handle must not hold the command open after Python exits.
            child.once('exit', () => {
              drainTimer = setTimeout(() => {
                if (!pipe.readableEnded) diagnostic.metadata_read_status = 'io_error';
                pipe.destroy();
              }, 100);
              drainTimer.unref();
            });
          } catch {
            diagnostic.metadata_init_status = 'io_error';
            try { child.stdio?.[3]?.destroy(); } catch {}
          }
        }
        launched.once("error", error => {
          // Only retry pipe allocation failure before a business PID exists, never a running command.
          if (useChannel && !launched.pid && ['EMFILE', 'ENFILE', 'ENOMEM', 'EINVAL', 'ENOSYS', 'ENOTSUP'].includes(error.code)) {
            diagnostic.metadata_init_status = 'io_error'; metadata = undefined;
            try { launched.stdio?.[3]?.destroy(); } catch {}
            return launch(false);
          }
          resolve({ code: 127, processError: error.code || 'UNKNOWN' });
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
    return business;
  };
  const handler = async () => {
    outcome = await execute();
    record_command_finished(telemetry, contract, args[0], readMetadata(metadata, contract, diagnostic), identity, outcome, pendingSignal, context, diagnostic);
    process.exitCode = outcome.code;
    if (pendingSignal || outcome.signal) {
      const error = new Error("Command interrupted");
      error.name = "AbortError";
      throw error;
    }
  };
  try {
    if (telemetry) {
      // Never give the SDK raw argv/stdin: only the allowlisted command and
      // fixed output format. All original arguments go exclusively to Python.
      await runEvent(telemetry, args[0], handler);
    } else {
      outcome = await execute();
    }
  } catch {
    outcome = await execute();
  } finally {
    // Existing request reporters retain their deadlines, but overlap the business run.
    await Promise.allSettled(requests);
    process.removeListener("SIGINT", interrupt);
    process.removeListener("SIGTERM", terminate);
    if (process.platform !== "win32") process.removeListener("SIGHUP", hangup);
    if (process.platform === "win32") process.removeListener("SIGBREAK", interrupt);
  }
  process.exitCode = outcome.code;
  const signal = pendingSignal || outcome.signal;
  if (signal) {
    if (process.platform === "win32") process.exitCode = signal === "SIGINT" ? 130 : 143;
    else process.kill(process.pid, signal);
  }
}

if (require.main === module) {
  const [python, entry, ...args] = process.argv.slice(2);
  run(python, entry, args).catch(() => { process.exitCode = 1; });
}
module.exports = { run, readMetadata, record_command_finished };
