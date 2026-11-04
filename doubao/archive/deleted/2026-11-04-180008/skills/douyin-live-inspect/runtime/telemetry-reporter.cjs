"use strict";

// 本文件负责统一的遥测发送入口：
// 管理 SDK 初始化、白名单事件校验、一次性事件发送，以及本地 observer 的旁路镜像。

// Shared event keys and the only application-owned SDK invocation boundary.
// 中文说明仅供维护者阅读，不参与事件白名单或上报。
const {_comments, ...EVENTS} = require('./telemetry-events.json');
for (const group of Object.values(EVENTS)) Object.freeze(group);
Object.freeze(EVENTS);
const ALLOWED = new Set(Object.values(EVENTS).flatMap(Object.values));
const disabled = (env = process.env) => ['1', 'true'].includes(String(env.BYTEDLIVE_TELEMETRY_DISABLED || '').trim().toLowerCase()) ||
  Boolean((env.NODE_TEST_CONTEXT || env.NODE_ENV === 'test') && env.BYTEDLIVE_TELEMETRY_TEST_CAPTURE !== '1');

function createTelemetry({toolName, env = process.env, isolated = false}) {
  const version = require('../scripts/skill-version.cjs').readSkillVersion();
  // 统一把 Skill 标识写入环境，供上游 SDK 生成一致的调用上下文。
  toolName = toolName.endsWith('-lite') ? 'douyin-live-inspect-lite' : 'douyin-live-inspect';
  process.env.VE_SKILL_ID = `douyin-live-inspect/${version}`;
  const config = {toolName, toolVersion: version, disabled: disabled(env),
    region: String(env.BYTEDLIVE_TELEMETRY_REGION || '').trim().toLowerCase() === 'sg' ? 'sg' : 'cn'};
  const filename = require.resolve('../lite/scripts/vendor/tooling-telemetry.cjs');
  let telemetry;
  if (!isolated) telemetry = require(filename).createToolTelemetry(config);
  else {
    // Each in-process OpenAPI operation needs its own SDK invocation context.
    const cached = require.cache[filename];
    delete require.cache[filename];
    try { telemetry = require(filename).createToolTelemetry(config); }
    finally {
      if (cached) require.cache[filename] = cached;
      else delete require.cache[filename];
    }
  }
  try {
    const reporter = telemetry.getReporter();
    telemetry.reporter = {report(event) {
      // The SDK uses cli_* for script toolName/toolVersion as well.
      let deviceId;
      try { deviceId = JSON.parse(event.extra || '{}').deviceId; } catch {}
      event = {...event, cli_name:toolName, skill_name:'douyin-live-inspect', skill_version:version,
        ...(typeof deviceId === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(deviceId) ? {device_id:deviceId} : {})};
      const delivery = reporter.report(event);
      // observer 只做本机观察，不参与真实上报结果，也不能阻塞主链路。
      try { require('./telemetry-observer.cjs').captureEvent(event, env); } catch { /* Local observation is optional. */ }
      return Promise.all([delivery, require('./workflow-telemetry.cjs').observeEvent(event, env).catch(() => {})]);
    }};
  } catch { /* An unavailable observer cannot affect the real reporter. */ }
  return telemetry;
}

function runEvent(telemetry, key, handler) {
  // Reject unregistered keys before the SDK can emit even a base event.
  if (!telemetry || !ALLOWED.has(key)) return handler();
  return telemetry.runScript(handler, {command: key, argv: ['node', 'inspect', '--json']});
}

async function reportEvent(key, extra, {toolName, env = process.env}) {
  if (disabled(env) || !ALLOWED.has(key)) return;
  const {fitExtra} = require('../lite/scripts/telemetry-contract.cjs');
  const {resolveDeviceId} = require('../lite/scripts/telemetry-identity.cjs');
  // 一次性事件也统一补充 deviceId，并按合同裁剪 extra，避免超长或字段越界。
  // 设备 ID 写入失败事件不可再次解析 ID，且需隔离正在执行的命令上下文。
  const identityFailure = key === EVENTS.identity.DEVICE_ID_WRITE_FAILED;
  const fitted = fitExtra({...extra, deviceId: identityFailure ? undefined : resolveDeviceId(env)});
  if (!fitted) return;
  const telemetry = createTelemetry({toolName, env, isolated: identityFailure});
  // Await delivery for one-shot reporters; their callers impose the deadline.
  const reporter = telemetry.getReporter();
  let delivery;
  telemetry.reporter = {report(event) { delivery = reporter.report(event); return delivery; }};
  await runEvent(telemetry, key, async () => telemetry.addExtra(fitted));
  await delivery;
}

module.exports = {EVENTS, disabled, createTelemetry, runEvent, reportEvent};
