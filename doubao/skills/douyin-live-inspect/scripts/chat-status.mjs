#!/usr/bin/env node
import { EVENTS, runCommand, observeResult } from '../runtime/telemetry.mjs';
import { fetchSingleTaskSnapshot } from '../runtime/audit-openapi.mjs';
import { buildChatUpdate } from '../runtime/chat-status.mjs';

async function readInput() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const value = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('invalid input');
  return value;
}

await runCommand(EVENTS.formal.CHAT_STATUS, async () => {
try {
  const input = await readInput();
  const snapshot = await fetchSingleTaskSnapshot({
    projectName: input.project_name,
    profile: input.profile, account_id: input.account_id, environment: input.environment,
    taskId: input.task_id,
    taskName: input.task_name,
    scenarioId: input.scenario_id,
    scenarioName: input.scenario,
    source: 'MACHINE',
    limit: 100,
  });
  process.stdout.write(`${JSON.stringify({ ok: true, command: 'chat-status', data: buildChatUpdate(snapshot, input.cursor) })}\n`);
} catch (error) {
  const result = { ok: false, command: 'chat-status', data: null, error: { code: error?.code || 'STATUS_UNAVAILABLE', message: '质检状态暂时无法获取' } };
  observeResult(result);
  process.stdout.write(`${JSON.stringify(result)}\n`);
  process.exitCode = 1;
}
});
