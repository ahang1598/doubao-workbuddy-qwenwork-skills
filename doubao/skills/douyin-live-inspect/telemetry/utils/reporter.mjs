// 适配原 SDK，统一命令开始/结束、一次性事件发送、载荷预算与 HTTP 发送确认。
// 限时等待发送，将安全副本交给本机监控，并用未裁剪的有效事实观察流程；SDK 不执行业务回调。
import { createRequire } from 'node:module';
import { EVENTS } from '../config/events.mjs';
import workflow from '../workflow/state.mjs';
import { liteContract } from '../commands/fields.mjs';
import { settleWithin } from './common.mjs';
import identity from './identity.mjs';

const require = createRequire(import.meta.url);

const ALLOWED = new Set(Object.values(EVENTS).flatMap(Object.values));
const OBSERVATIONS = new Set([
  EVENTS.service.NOT_ENABLED,
  EVENTS.startup.ATTEMPT,
  EVENTS.stop.OBSERVED,
]);
const disabled = (env = process.env) =>
  ['1', 'true'].includes(
    String(env.BYTEDLIVE_TELEMETRY_DISABLED || '')
      .trim()
      .toLowerCase(),
  ) ||
  Boolean(
    (env.NODE_TEST_CONTEXT || env.NODE_ENV === 'test') &&
    env.BYTEDLIVE_TELEMETRY_TEST_CAPTURE !== '1',
  );
function createTelemetry({
  toolName,
  env = process.env,
  isolated = false,
  observeWorkflow = true,
}) {
  const version = require('../../scripts/skill-version.cjs').readSkillVersion();
  // 兼容旧 byted 名称；线上 cli_name 保留主 Skill / Lite 两个既有统计标识。
  toolName = toolName.endsWith('-lite') ? 'douyin-live-inspect-lite' : 'douyin-live-inspect';
  process.env.VE_SKILL_ID = `douyin-live-inspect/${version}`;
  const config = {
    toolName,
    toolVersion: version,
    disabled: disabled(env),
    region:
      String(env.BYTEDLIVE_TELEMETRY_REGION || '')
        .trim()
        .toLowerCase() === 'sg'
        ? 'sg'
        : 'cn',
  };
  const filename = require.resolve('../vendor/tooling-telemetry.cjs');
  let telemetry;
  if (!isolated) telemetry = require(filename).createToolTelemetry(config);
  else {
    // Each in-process OpenAPI operation needs its own SDK invocation context.
    const cached = require.cache[filename];
    delete require.cache[filename];
    try {
      telemetry = require(filename).createToolTelemetry(config);
    } finally {
      if (cached) require.cache[filename] = cached;
      else delete require.cache[filename];
    }
  }
  telemetry.pending = new Set();
  try {
    const reporter = telemetry.getReporter();
    telemetry.reporter = {
      report(event) {
        // Observation results do not inherit an unrelated CLI failure exit code.
        if (OBSERVATIONS.has(event.command))
          event = { ...event, result: 'success', error_message: undefined };
        // The SDK uses cli_* for script toolName/toolVersion as well.
        let deviceId;
        try {
          deviceId = JSON.parse(event.extra || '{}').deviceId;
        } catch {}
        event = {
          ...event,
          cli_name: toolName,
          skill_name: 'douyin-live-inspect',
          skill_version: version,
          ...(typeof deviceId === 'string' &&
          /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(deviceId)
            ? { device_id: deviceId }
            : {}),
        };
        // Command contracts retain the pre-budget facts for local state progression.
        const localEvent = telemetry.commandExtra
          ? { ...event, extra: JSON.stringify(telemetry.commandExtra) }
          : event;
        const observation = observeWorkflow
          ? workflow.observeEvent(localEvent, env).catch(() => {})
          : Promise.resolve();
        if (telemetry.commandExtraRejected) return observation;
        const delivery = (telemetry.delivery = reporter.report(event));
        // observer 只做本机观察，不参与真实上报结果，也不能阻塞主链路。
        try {
          require('../telemetry-observer.cjs').captureEvent(event, env);
        } catch {
          /* Local observation is optional. */
        }
        const pending = Promise.all([delivery, observation]);
        telemetry.pending.add(pending);
        pending.finally(() => telemetry.pending.delete(pending)).catch(() => {});
        return pending;
      },
    };
  } catch {
    /* An unavailable observer cannot affect the real reporter. */
  }
  return telemetry;
}
// Command and one-shot sends share the SDK's completion and HTTP acknowledgement.
async function finishTelemetry(telemetry, failure, pending = [], timeout = telemetry?.deliveryTimeout ?? 3000) {
  if (!telemetry) {
    await settleWithin(pending, timeout);
    return false;
  }
  let confirmed = false;
  await settleWithin([Promise.resolve().then(() => {
    if (telemetry.commandExtra) {
      telemetry.commandExtraRejected = true;
      try {
        const fitted = liteContract.fitExtra(telemetry.commandExtra);
        if (fitted) {
          telemetry.addExtra(fitted);
          telemetry.commandExtraRejected = false;
        }
      } catch { /* Finish the SDK scope even if optional metadata fails. */ }
    }
    if (!failure && process.exitCode != null && Number(process.exitCode) !== 0)
      failure = new Error(`Script completed with exit code ${process.exitCode}`);
    return failure ? telemetry.finishCommandFailure(failure) : telemetry.finishCommandSuccess();
  }).catch(() => {}).then(async () => {
    const [delivered] = await Promise.allSettled([telemetry.delivery, ...(telemetry.pending || []), ...pending]);
    confirmed = delivered.status === 'fulfilled' && delivered.value === true;
  })], timeout);
  return confirmed;
}
// 只启动 SDK 事件，不接收或执行业务回调。
function beginTelemetry(telemetry, key) {
  try {
    if (telemetry && ALLOWED.has(key)) {
      telemetry.beginCommand({ command: key, outputFormat: 'json' });
      return telemetry;
    }
  } catch {}
}
async function reportEvent(key, extra, { toolName, env = process.env, timeout = 3000 }) {
  if (disabled(env) || !ALLOWED.has(key)) return;
  const { account_id, ...eventExtra } = extra;
  extra = eventExtra;
  const deadline = Date.now() + timeout;
  const remaining = () => Math.max(0, deadline - Date.now());
  // These facts have passed the lifecycle whitelist after the business transaction.
  // Advance local workflow even when identity enrichment or wire fitting later fails.
  const lifecycle = [EVENTS.task.STARTED, EVENTS.task.RESUMED, EVENTS.funnel.SNAPSHOT].includes(
    key,
  );
  let workflowDelivery;
  if (lifecycle)
    await workflow
      .observeEvent({ command: key, result: 'success', extra: JSON.stringify(extra) }, env, {
        // Persist local state first, but do not serialize two network requests.
        emit: (snapshot) => {
          workflowDelivery = reportEvent(EVENTS.workflow.SNAPSHOT, snapshot, {
            toolName: 'douyin-live-inspect',
            env,
            timeout: remaining(),
          }).catch(() => {});
        },
      })
      .catch(() => {});
  const { fitExtra } = liteContract;
  const { resolveDeviceId } = identity;
  // 一次性事件也统一补充 deviceId，并按合同裁剪 extra，避免超长或字段越界。
  // 设备 ID 写入失败事件不可再次解析 ID，且需隔离正在执行的命令上下文。
  const identityFailure = key === EVENTS.identity.DEVICE_ID_WRITE_FAILED;
  const fitted = fitExtra({
    ...extra,
    deviceId: identityFailure ? undefined : resolveDeviceId(env),
  });
  if (!fitted || !remaining()) {
    await settleWithin([workflowDelivery], remaining());
    return false;
  }
  let telemetry;
  try {
    telemetry = createTelemetry({ toolName, env, isolated: true, observeWorkflow: !lifecycle });
    telemetry.beginCommand({ command: key, outputFormat: 'json' });
    if (typeof account_id === 'string' && /^\d{1,128}$/.test(account_id) && !['123', '123456'].includes(account_id))
      telemetry.setAccountId(account_id);
    telemetry.addExtra(fitted);
  } catch {
    await settleWithin([workflowDelivery], remaining());
    // SDK 不可用时尚未开始发送，入口仍应返回 unavailable，而不是 attempted。
    return;
  }
  return finishTelemetry(telemetry, undefined, [workflowDelivery], remaining());
}

const reporter = { EVENTS, disabled, createTelemetry, beginTelemetry, finishTelemetry, reportEvent };
export default reporter;

export { disabled, createTelemetry, beginTelemetry, finishTelemetry, reportEvent };
