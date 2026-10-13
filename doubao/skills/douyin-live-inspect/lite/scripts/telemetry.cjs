"use strict";

// 本文件负责 Lite 命令的 Node -> Python 遥测桥接：
// 在启动 Python 业务进程的同时，给白名单命令补充命令级遥测，并隔离 metadata 文件与身份上下文。

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync, spawn } = require("node:child_process");

function readMetadata(filename, contract) {
  if (!filename || !contract) return {};
  let fd;
  try {
    // 只读取本次临时 metadata 文件，限制大小并拒绝跟随符号链接。
    if (!fs.lstatSync(filename).isFile()) return {};
    fd = fs.openSync(filename, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0) | (fs.constants.O_NONBLOCK || 0));
    const info = fs.fstatSync(fd);
    if (!info.isFile() || info.size > 4096) return {};
    const buffer = Buffer.alloc(4097);
    const size = fs.readSync(fd, buffer, 0, buffer.length, 0);
    if (size > 4096) return {};
    return contract.safeFields(JSON.parse(buffer.subarray(0, size).toString('utf8')));
  } catch { return {}; }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}

function record_command_finished(telemetry, contract, command, metadata, identity, outcome, interrupted) {
  if (!telemetry || !contract) return;
  try {
    const deviceId = telemetry.config.disabled ? undefined : require('./telemetry-identity.cjs').resolveDeviceId();
    if (deviceId) telemetry.addExtra({ deviceId });
    const extra = contract.commandMetadata(command, metadata);
    if (!extra) return;
    if (interrupted || outcome.signal) { extra.error_code = 'ABORTED'; delete extra.error_detail; }
    else if (outcome.code !== 0) extra.error_code ||= 'OPERATION_FAILED';
    else { delete extra.error_code; delete extra.error_detail; }
    const fitted = contract.fitExtra({...extra, ...identity, ...(deviceId ? { deviceId } : {})});
    if (fitted) telemetry.addExtra(fitted);
  } catch { /* Optional metadata never changes the command result. */ }
}

async function run(python, entry, args) {
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

  let metadataDir, metadataPath;
  if (telemetry && contract) {
    try {
      metadataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'inspect-meta-'));
      if (process.platform === 'win32') {
        const secured = spawnSync(python, [path.join(__dirname, 'telemetry_cache.py'), metadataDir], {stdio: 'ignore', timeout: 2000});
        if (secured.status !== 0) throw new Error('private metadata unavailable');
      } else fs.chmodSync(metadataDir, 0o700);
      metadataPath = path.join(metadataDir, 'metadata.json');
      fs.writeFileSync(metadataPath, '{}', {mode: 0o600, flag: 'wx'});
    } catch { metadataPath = undefined; }
  }
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
    business ??= new Promise(resolve => {
      child = spawn(python, [entry, ...args], {
        stdio: "inherit", env: {
          ...process.env,
          BYTEDLIVE_LITE_TELEMETRY_CHILD: "1",
          // Python 侧只通过受控文件和环境变量回传允许的遥测元信息。
          INSPECT_TELEMETRY_METADATA_FILE: metadataPath || "",
          BYTEDLIVE_LITE_TELEMETRY_IDENTITY: JSON.stringify(identity),
          BYTEDLIVE_LITE_TELEMETRY_NODE: process.execPath,
        },
      });
      child.once("error", () => resolve({ code: 127 }));
      child.once("close", (code, signal) => resolve({ code: code ?? 1, signal }));
      if (pendingSignal) child.kill(pendingSignal);
    });
    return business;
  };
  const handler = async () => {
    outcome = await execute();
    record_command_finished(telemetry, contract, args[0], readMetadata(metadataPath, contract), identity, outcome, pendingSignal);
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
    try { if (metadataDir) fs.rmSync(metadataDir, {recursive: true, force: true}); } catch {}
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
