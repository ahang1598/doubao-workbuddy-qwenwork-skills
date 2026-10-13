#!/usr/bin/env node
import { EVENTS, runCommand, observeResult, addScenarioContext } from '../runtime/telemetry.mjs';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { onlineEnvironment } from '../runtime/online-environment.mjs';
import { resolveCreationBinding } from '../runtime/task-binding.mjs';
import { resolveTaskSource } from '../runtime/browser-stream.mjs';
import { launchSingleTaskDashboard } from './audit-dashboard.mjs';
import { resolveLiveScope } from '../runtime/product-scope.mjs';
import { remoteDashboard, resolveInspectionEnvironment } from '../runtime/remote-dashboard.mjs';
import { detectRuntimeMode } from '../runtime/runtime-mode.mjs';
import { runService } from '../runtime/service-call.mjs';

const MAX_INPUT_BYTES = 64 * 1024;
const MAX_OUTPUT_BYTES = 2 * 1024 * 1024;

function emit(data, error = null, ok = !error) {
  observeResult({ok,error});
  process.stdout.write(`${JSON.stringify({ ok, command: 'douyin-task-create', data: ok ? data : null, error })}\n`);
}

function safeMessage(value) {
  return `${value || 'Command failed'}`.replace(/https?:\/\/\S+/gi, '[redacted]').slice(0, 500);
}

function defaultTaskName(now = new Date()) {
  const part = (value) => `${value}`.padStart(2, '0');
  return `直播质检-${now.getFullYear()}${part(now.getMonth() + 1)}${part(now.getDate())}-${part(now.getHours())}${part(now.getMinutes())}${part(now.getSeconds())}`;
}

async function readInput() {
  const chunks = [];
  let size = 0;
  const rawMode = Boolean(process.stdin.isTTY && process.stdin.setRawMode);
  if (rawMode) process.stdin.setRawMode(true);
  try {
    for await (const chunk of process.stdin) {
      size += chunk.length;
      if (size > MAX_INPUT_BYTES) throw Object.assign(new Error('stdin input is too large'), { code: 'INVALID_INPUT' });
      chunks.push(chunk);
      if (chunk.includes(10)) break;
    }
  } finally {
    if (rawMode) process.stdin.setRawMode(false);
  }
  const text = Buffer.concat(chunks).toString('utf8');
  const line = text.split(/\r?\n/, 1)[0];
  let value;
  try { value = JSON.parse(line); } catch {
    throw Object.assign(new Error('stdin must contain one JSON object'), { code: 'INVALID_INPUT' });
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw Object.assign(new Error('stdin must contain one JSON object'), { code: 'INVALID_INPUT' });
  }
  return value;
}

function runInspection(args, env = process.env) { return runService(args, { env }); }

function parseCliResult(result) {
  if (result.overflow) return { ok: false, error: { type: 'internal', message: 'Service output exceeded limit' } };
  try { return JSON.parse(result.code === 0 ? result.stdout : result.stderr?.trim() || result.stdout); } catch {
    return { ok: false, error: { type: 'internal', message: result.stderr || 'Service returned an unreadable response' } };
  }
}

export async function createInspection(input, { resolveSource = resolveTaskSource, run = runInspection, output = emit, detectMode = detectRuntimeMode, launchDashboard = launchSingleTaskDashboard } = {}) {

  const dashboardMode = input.dashboard_mode ?? 'auto';
  if (!['auto', 'remote'].includes(dashboardMode)) {
    throw Object.assign(new Error('Invalid dashboard mode'), { code: 'INVALID_INPUT' });
  }

  // Validate business input before configuration or source access.
  const { projectName, scenarioId, scenarioName } = resolveLiveScope({ ...input, environment: input.environment ?? 'online' });
  addScenarioContext(scenarioName);
  const binding = await resolveCreationBinding(input, async (args) => {
    const response = await run(args);
    return response.code === 0 ? parseCliResult(response) : null;
  });
  // Use the selected profile binding for both API routing and the dashboard.
  const environment = binding.length ? binding[binding.indexOf('--env') + 1] : input.environment;
  const routing = dashboardMode === 'remote' || environment ? resolveInspectionEnvironment({ environment }) : null;
  const source = await resolveSource(input);
  if (source.status === 'not_live') {
    output({ status: 'not_live', source_type: 'douyin' });
    return;
  }
  const taskName = `${input.task_name ?? ''}`.trim() || source.roomName || defaultTaskName();
  const extra = `${input.extra ?? ''}`.trim() || JSON.stringify({
    source_type: source.sourceMethod === 'direct_flv' ? 'flv' : 'douyin',
    room_title: source.roomName || '',
    account_name: source.accountName || '',
    scenario_name: scenarioName,
  });

  const args = [
    ...binding, 'quality', '+task-create', '--project-name', projectName, '--scenario-id', scenarioId,
    '--task-name', taskName, '--live-pull-url', source.streamUrl, '--extra', extra,
  ];
  // Pin the same API environment for dry-run and the single create, even if the default profile changes.
  const childEnv = routing ? onlineEnvironment() : process.env;
  const dryRunRaw = await run([...args, '--dry-run'], childEnv);
  const dryRun = parseCliResult(dryRunRaw);
  if (dryRunRaw.code !== 0 || !dryRun.ok) {
    output(null, { code: 'DRY_RUN_FAILED', message: safeMessage(dryRun.error?.message) }, false);
    return;
  }

  const createRaw = await run(args, childEnv);
  const created = parseCliResult(createRaw);
  if (createRaw.code !== 0 || !created.ok) {
    const writeOccurred = created.error?.write_occurred;
    output(null, {
      code: writeOccurred === false ? 'CREATE_FAILED' : 'CREATE_UNCERTAIN',
      message: safeMessage(created.error?.message), retryable: false,
    }, false);
    return;
  }
  const taskId = created.data?.response?.data?.Result?.TaskId ?? created.data?.response?.Result?.TaskId;
  if (taskId === undefined || taskId === null) {
    output(null, { code: 'CREATE_UNCERTAIN', message: 'Create response did not include TaskId', retryable: false }, false);
    return;
  }
  const runtime = detectMode();
  // Doubao Work opens the deployed console page even on a local desktop.
  let dashboard = dashboardMode === 'remote' && routing ? remoteDashboard({ ...routing, projectName, taskId }) : { status: 'not_applicable' };
  if (dashboardMode !== 'remote' && runtime.mode === 'local') {
    try {
      dashboard = { status: 'ready', ...(await launchDashboard({
        projectName, taskId, taskName, scenarioId, profile: binding[binding.indexOf('--profile') + 1],
        account_id: binding.includes('--account-id') ? binding[binding.indexOf('--account-id') + 1] : undefined, environment,
      })) };
    } catch (error) {
      dashboard = { status: 'unavailable', message: safeMessage(error?.message) };
    }
  }
  output({
    status: 'created', source_type: source.sourceMethod === 'direct_flv' ? 'flv' : 'douyin', task_id: taskId,
    project_name: projectName, scenario_id: scenarioId,
    scenario: scenarioName, task_name: taskName, runtime_mode: runtime.mode,
    profile: binding[binding.indexOf('--profile') + 1],
    account_id: binding.includes('--account-id') ? binding[binding.indexOf('--account-id') + 1] : undefined,
    ...(routing ? { environment: routing.environment } : {}), dashboard,
  });
}

if (process.argv[1] && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1])) await runCommand(EVENTS.formal.DOUYIN_TASK_CREATE, () => readInput().then(input => createInspection(input))).catch((cause) => {
  emit(null, {
    code: cause?.code || 'UNEXPECTED_ERROR', message: safeMessage(cause?.message),
    retryable: Boolean(cause?.retryable),
  }, false);
});
