import { args, safeError } from '../lib/cli-utils.mjs';
import { runMapWorkflow } from '../lib/map-workflow.mjs';
import {
  beginGenerationAttempt,
  finishGenerationAttempt,
  bestEffortTelemetry,
  flushTaskTelemetry,
  readTelemetryTask,
} from '../lib/task-telemetry.mjs';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const options = args();
const task = options['telemetry-task'];
try {
  if (task) {
    const current = await bestEffortTelemetry(() => readTelemetryTask(task));
    if (current && current.status !== 'running')
      throw new Error(
        'TELEMETRY_TASK_FINISHED: 新任务请使用独立上下文，不复用已结束任务的 ID',
      );
    await bestEffortTelemetry(() => beginGenerationAttempt(task));
  }
  const { output, state } = await runMapWorkflow(options);
  if (task)
    await bestEffortTelemetry(async () => {
      const build = JSON.parse(
        await readFile(
          resolve(dirname(options.out), 'build-report.json'),
          'utf8',
        ),
      );
      await finishGenerationAttempt(task, {
        status: state.status === 'passed' ? 'succeeded' : 'validated',
        stage: state.phase,
        artifactId: build.telemetry?.artifact_id || build.htmlSha256,
      });
    });
  process.stdout.write(output);
} catch (error) {
  if (task && error.workflow?.status !== 'pending')
    await bestEffortTelemetry(() =>
      finishGenerationAttempt(task, {
        status: 'failed',
        stage: error.workflow?.phase || 'input',
        errorCode: error.workflow?.diagnosis?.code || error.message,
        exception: error,
      }),
    );
  process.stderr.write(
    JSON.stringify(
      error.workflow || { status: 'failed', error: safeError(error) },
    ) + '\n',
  );
  process.exitCode = 1;
} finally {
  if (task) await bestEffortTelemetry(() => flushTaskTelemetry(task));
}
