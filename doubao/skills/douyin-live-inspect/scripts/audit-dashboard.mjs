#!/usr/bin/env node
import telemetry, { EVENTS } from '../telemetry/main.mjs';
import { requireOriginalTaskContext, taskBindingError } from '../runtime/task-binding.mjs';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';

import { remoteDashboard, resolveInspectionEnvironment } from '../runtime/remote-dashboard.mjs';
import { executeOperation } from '../runtime/operations.mjs';

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
  if (!Number.isSafeInteger(parsed) || parsed <= 0)
    throw new Error(`${name} must be a positive integer`);
  return parsed;
}

function safeError(error) {
  return `${error?.message || error || 'Unknown error'}`
    .replace(/\b(?:https?|rtmps?|wss?):\/\/[^\s,}\]]+/gi, '[redacted-url]')
    .slice(0, 500);
}

export async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (argv.some(arg => ['--serve', '--notify-end'].includes(arg.split('=')[0])))
    throw Object.assign(new Error('正式版本地工作台已退役，请使用原任务身份获取远端控制台链接。'), {code: 'LOCAL_DASHBOARD_RETIRED'});
  // Existing tasks must carry their original environment; never guess from a changed default profile.
  requireOriginalTaskContext({
    environment: args.environment,
    profile: args.profile,
    account_id: args['account-id'],
    project_name: args['project-name'],
    task_id: args['task-id'],
  });
  const routing = resolveInspectionEnvironment({ environment: args.environment });
  const dashboard = remoteDashboard({
    ...routing,
    projectName: args['project-name'],
    taskId: args['task-id'],
  });
  let task;
  try {
    if (!args.profile) throw new Error('Original profile is required');
    const response = await executeOperation('quality/+task-get', {
      environment: args.environment,
      profile: args.profile,
      account_id: args['account-id'],
      project_name: args['project-name'],
      task_id: positiveInteger(args['task-id'], 'taskId'),
    });
    const result = response.data?.response?.data?.Result ?? response.data?.response?.Result;
    if (!response.ok || !result)
      throw Object.assign(new Error('unavailable'), { code: response.error?.code });
    task = result;
  } catch (error) {
    if (['ORIGINAL_TASK_CONTEXT_REQUIRED', 'TASK_BINDING_MISMATCH'].includes(error.code))
      throw taskBindingError(error.code);
    throw new Error('当前环境中无法核验此直播任务');
  }
  if (
    String(task.ProjectName) !== args['project-name'] ||
    Number(task.TaskId) !== Number(args['task-id']) ||
    task.TaskType !== 2
  ) {
    throw taskBindingError();
  }
  const payload = { ok: true, command: 'audit-dashboard', data: dashboard, error: null };
  process.stdout.write(`${JSON.stringify(payload)}\n`);
  return payload;
}

if (
  process.argv[1] &&
  realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1])
) {
  await telemetry
    .runCommand(
      {
        command: EVENTS.formal.AUDIT_DASHBOARD,
        skip: process.argv.some(arg => ['--serve', '--notify-end'].includes(arg.split('=')[0])) || process.argv.includes('--help'),
      },
      () => main(),
    )
    .catch((error) => {
      process.stdout.write(
        `${JSON.stringify({ ok: false, command: 'audit-dashboard', data: null, error: { code: error?.code || 'DASHBOARD_ERROR', message: safeError(error) } })}\n`,
      );
      process.exitCode = 1;
    });
}
