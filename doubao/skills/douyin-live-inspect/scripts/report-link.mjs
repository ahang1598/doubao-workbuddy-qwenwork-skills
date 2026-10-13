#!/usr/bin/env node
import { remoteReport } from '../runtime/remote-dashboard.mjs';
import { EVENTS, runCommand, addCommandContext } from '../runtime/telemetry.mjs';

await runCommand(EVENTS.formal.REPORT_LINK, async () => {
try {
  let input = '';
  for await (const chunk of process.stdin) {
    input += chunk.toString('utf8');
    if (Buffer.byteLength(input) > 4096) throw new Error('Invalid input');
  }
  const { kind, environment, project_name, task_id } = JSON.parse(input);
  const data = remoteReport({ kind, environment, projectName: project_name, taskId: task_id });
  addCommandContext({workflow_kind: process.env.INSPECT_TELEMETRY_WORKFLOW === 'video_batch' && kind === 'video' ? 'video_batch' : kind === 'video' ? 'video_single' : 'live', delivery_mode:'remote'});
  process.stdout.write(`${JSON.stringify({ ok: true, data, error: null })}\n`);
} catch {
  process.stdout.write(`${JSON.stringify({ ok: false, data: null, error: { code: 'INVALID_REMOTE_TARGET', message: '报告类型、原任务环境或任务定位不可用' } })}\n`);
  process.exitCode = 1;
}
});
