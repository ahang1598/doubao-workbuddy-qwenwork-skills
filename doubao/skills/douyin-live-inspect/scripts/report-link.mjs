#!/usr/bin/env node
import { readStdin } from '../runtime/script-input.mjs';
import telemetry, { EVENTS, addCommandContext, workflowKind } from '../telemetry/main.mjs';
import { remoteReport } from '../runtime/remote-dashboard.mjs';

await telemetry.runCommand({ command: EVENTS.formal.REPORT_LINK }, async () => {
  try {
    const { kind, environment, project_name, task_id } = JSON.parse(
      await readStdin(4096, new Error('Invalid input')),
    );
    const data = remoteReport({ kind, environment, projectName: project_name, taskId: task_id });
    addCommandContext({
      workflow_kind:
        workflowKind() === 'video_batch' && kind === 'video'
          ? 'video_batch'
          : kind === 'video'
            ? 'video_single'
            : 'live',
      delivery_mode: 'remote',
    });
    const result = { ok: true, data, error: null };
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return result;
  } catch {
    const result = {
      ok: false,
      data: null,
      error: { code: 'INVALID_REMOTE_TARGET', message: '报告类型、原任务环境或任务定位不可用' },
    };
    process.stdout.write(`${JSON.stringify(result)}\n`);
    process.exitCode = 1;
    return result;
  }
});
