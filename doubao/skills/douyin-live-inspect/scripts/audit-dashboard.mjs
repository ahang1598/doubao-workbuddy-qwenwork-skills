#!/usr/bin/env node
import { requireOriginalTaskContext, taskBindingError } from '../runtime/task-binding.mjs';
import { EVENTS, runCommand } from '../runtime/telemetry.mjs';
import { onlineEnvironment } from '../runtime/online-environment.mjs';
import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { startSingleTaskDashboard } from '../runtime/single-task-dashboard.mjs';

import { remoteDashboard, resolveInspectionEnvironment } from '../runtime/remote-dashboard.mjs';
import { executeOperation } from '../runtime/operations.mjs';

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const SKILL_ROOT = dirname(dirname(SCRIPT_PATH));

function parseArgs(argv) {
  const output = {};
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (!value.startsWith('--')) continue;
    const key = value.slice(2);
    if (key === 'serve' || key === 'notify-end' || key === 'remote') output[key] = true;
    else output[key] = argv[++index];
  }
  return output;
}

function positiveInteger(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0) throw new Error(`${name} must be a positive integer`);
  return parsed;
}

function safeError(error) {
  return `${error?.message || error || 'Unknown error'}`
    .replace(/\b(?:https?|rtmps?|wss?):\/\/[^\s,}\]]+/gi, '[redacted-url]').slice(0, 500);
}

export async function notifyEndAccepted({ dashboardUrl, projectName, taskId, fetchImpl = fetch }) {
  const url = new URL(dashboardUrl);
  const token = url.searchParams.get('token');
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port
    || url.username || url.password || url.pathname !== '/' || !token) {
    throw new Error('A token-protected local dashboard URL is required');
  }
  if (typeof projectName !== 'string' || !projectName.trim()) throw new Error('projectName is required');
  const id = positiveInteger(taskId, 'taskId');
  url.pathname = '/api/end-accepted';
  url.search = '';
  url.hash = '';
  // This only records a successful EndTask acknowledgement; it never ends a task.
  const response = await fetchImpl(url, {
    method: 'POST', redirect: 'error', signal: AbortSignal.timeout(3_000),
    headers: { 'content-type': 'application/json', 'x-dashboard-token': token },
    body: JSON.stringify({ project_name: projectName, task_id: id }),
  });
  if (!response.ok) throw new Error(`Dashboard notification failed with HTTP ${response.status}`);
  const result = await response.json();
  if (!result.ok || result.end_request_accepted !== true || result.task_id !== id) {
    throw new Error('Dashboard did not acknowledge the matching task');
  }
  return { status: 'notified', task_id: id };
}

async function readNotificationInput() {
  let input = '';
  for await (const chunk of process.stdin) {
    input += chunk.toString('utf8');
    if (Buffer.byteLength(input) > 4_096) throw new Error('Notification input is too large');
    if (input.includes('\n')) break;
  }
  try { return JSON.parse(input); }
  catch { throw new Error('stdin must contain one notification JSON object'); }
}

export async function launchSingleTaskDashboard({
  projectName, taskId, profile, account_id, environment = 'online', taskName = null, scenarioId = null, env = process.env, timeoutMs = 5_000,
}) {
  const token = randomUUID();
  const args = [
    SCRIPT_PATH, '--serve', '--token', token, '--project-name', `${projectName}`,
    '--task-id', `${positiveInteger(taskId, 'taskId')}`,
  ];
  if (!profile) throw new Error('Original profile is required');
  args.push('--profile', profile, '--environment', environment);
  if (account_id) args.push('--account-id', account_id);
  if (taskName) args.push('--task-name', `${taskName}`);
  if (scenarioId) args.push('--scenario-id', `${scenarioId}`);
  const child = spawn(process.execPath, args, {
    cwd: SKILL_ROOT, env, detached: true, shell: false, stdio: ['ignore', 'pipe', 'pipe'],
  });
  const result = await new Promise((resolve, reject) => {
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error('Dashboard did not become ready in time'));
    }, timeoutMs);
    const finish = (callback, value) => {
      clearTimeout(timer);
      child.stdout.removeAllListeners();
      child.stderr.removeAllListeners();
      callback(value);
    };
    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString('utf8');
      const newline = stdout.indexOf('\n');
      if (newline < 0) return;
      try { finish(resolve, JSON.parse(stdout.slice(0, newline))); }
      catch { finish(reject, new Error('Dashboard returned an invalid startup response')); }
    });
    child.stderr.on('data', (chunk) => { stderr = `${stderr}${chunk}`.slice(-4_000); });
    child.once('error', (error) => finish(reject, error));
    child.once('exit', (code) => {
      if (code !== null) finish(reject, new Error(safeError(stderr) || `Dashboard exited with code ${code}`));
    });
  });
  child.stdout.destroy();
  child.stderr.destroy();
  child.unref();
  return { dashboard_url: result.dashboard_url, dashboard_pid: child.pid };
}

async function serve(args) {
  const token = `${args.token || ''}`;
  const projectName = `${args['project-name'] || ''}`;
  const taskId = positiveInteger(args['task-id'], 'taskId');
  if (!token || !projectName) throw new Error('token and project-name are required');
  const running = await startSingleTaskDashboard({
    token, projectName, taskId, profile: args.profile, account_id: args['account-id'], environment: args.environment, taskName: args['task-name'] || null,
    scenarioId: args['scenario-id'] || null, port: Number(args.port || 0),
  });
  const dashboardUrl = `http://127.0.0.1:${running.port}/?token=${encodeURIComponent(token)}`;
  process.stdout.write(`${JSON.stringify({ ok: true, dashboard_url: dashboardUrl, pid: process.pid })}\n`);
  const close = () => {
    running.stop();
    running.server.closeAllConnections();
  };
  process.on('SIGINT', close);
  process.on('SIGTERM', close);
  await new Promise((resolve) => running.server.once('close', resolve));
}

export async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.remote) {
    if (args.serve || args['notify-end']) throw new Error('Remote mode cannot start or notify a local server');
    // Existing tasks must carry their original environment; never guess from a changed default profile.
    requireOriginalTaskContext({ environment: args.environment, profile: args.profile, account_id: args['account-id'], project_name: args['project-name'], task_id: args['task-id'] });
    const routing = resolveInspectionEnvironment({ environment: args.environment });
    const dashboard = remoteDashboard({ ...routing, projectName: args['project-name'], taskId: args['task-id'] });
    let task;
    try {
      if (!args.profile) throw new Error('Original profile is required');
      const response = await executeOperation('quality/+task-get', { environment: args.environment,
        profile: args.profile, account_id: args['account-id'], project_name: args['project-name'], task_id: positiveInteger(args['task-id'], 'taskId') });
      const result = response.data?.response?.data?.Result ?? response.data?.response?.Result;
      if (!response.ok || !result) throw Object.assign(new Error('unavailable'), { code: response.error?.code });
      task = result;
    } catch (error) {
      if (['ORIGINAL_TASK_CONTEXT_REQUIRED', 'TASK_BINDING_MISMATCH'].includes(error.code)) throw taskBindingError(error.code);
      throw new Error('当前环境中无法核验此直播任务');
    }
    if (String(task.ProjectName) !== args['project-name'] || Number(task.TaskId) !== Number(args['task-id']) || task.TaskType !== 2) {
      throw taskBindingError();
    }
    process.stdout.write(`${JSON.stringify({ ok: true, command: 'audit-dashboard', data: dashboard, error: null })}\n`);
    return;
  }
  if (args['notify-end']) {
    const input = await readNotificationInput();
    const result = await notifyEndAccepted({
      dashboardUrl: input?.dashboard_url, projectName: input?.project_name, taskId: input?.task_id,
    });
    process.stdout.write(`${JSON.stringify({ ok: true, command: 'audit-dashboard-notify-end', data: result, error: null })}\n`);
    return;
  }
  if (args.serve) return serve(args);
  const result = await launchSingleTaskDashboard({
    projectName: args['project-name'], taskId: args['task-id'], profile: args.profile, account_id: args['account-id'], environment: args.environment,
    taskName: args['task-name'], scenarioId: args['scenario-id'],
  });
  process.stdout.write(`${JSON.stringify({ ok: true, command: 'audit-dashboard', data: result, error: null })}\n`);
}

if (process.argv[1] && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1])) {
  await runCommand(EVENTS.formal.AUDIT_DASHBOARD, () => main(), {skip:process.argv.includes('--serve') || process.argv.includes('--help')}).catch((error) => {
    process.stdout.write(`${JSON.stringify({ ok: false, command: 'audit-dashboard', data: null, error: { code: error?.code || 'DASHBOARD_ERROR', message: safeError(error) } })}\n`);
    process.exitCode = 1;
  });
}
