#!/usr/bin/env node
import { readStdin } from '../runtime/script-input.mjs';
import telemetry, { EVENTS } from '../telemetry/main.mjs';
import { fetchSingleTaskSnapshot } from '../runtime/audit-openapi.mjs';
import { buildChatUpdate } from '../runtime/chat-status.mjs';

async function readInput() {
  const bytes = await readStdin(
    64 * 1024,
    Object.assign(new Error('Input exceeds 64 KiB'), { code: 'INVALID_INPUT' }),
  );
  const value = JSON.parse(bytes.toString('utf8') || '{}');
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('invalid input');
  return value;
}

await telemetry.runCommand({ command: EVENTS.formal.CHAT_STATUS }, async () => {
  try {
    const input = await readInput();
    const snapshot = await fetchSingleTaskSnapshot({
      projectName: input.project_name,
      profile: input.profile,
      account_id: input.account_id,
      environment: input.environment,
      taskId: input.task_id,
      taskName: input.task_name,
      scenarioId: input.scenario_id,
      scenarioName: input.scenario,
      source: 'MACHINE',
      limit: 100,
    });
    const result = {
      ok: true,
      command: 'chat-status',
      data: buildChatUpdate(snapshot, input.cursor),
    };
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return result;
  } catch (error) {
    const result = {
      ok: false,
      command: 'chat-status',
      data: null,
      error: { code: error?.code || 'STATUS_UNAVAILABLE', message: '质检状态暂时无法获取' },
    };
    process.stdout.write(`${JSON.stringify(result)}\n`);
    process.exitCode = 1;
    return result;
  }
});
