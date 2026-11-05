import { args } from '../lib/cli-utils.mjs';
import {
  startTelemetryTask,
  finishTelemetryTask,
  flushTaskTelemetry,
} from '../lib/task-telemetry.mjs';

const options = args();
try {
  if (!options.task) throw new Error('需要 --task <任务上下文文件>');
  if (options.start)
    await startTelemetryTask(options.task, {
      env: options.env || 'production',
    });
  else if (options.finish)
    await finishTelemetryTask(options.task, {
      status: options.finish,
      stage: options.stage,
      errorCode: options.code,
    });
  else if (!options.flush)
    throw new Error('需要 --start、--finish failed|cancelled 或 --flush');
  await flushTaskTelemetry(options.task);
  process.stdout.write(
    JSON.stringify({ status: 'recorded', task: options.task }) + '\n',
  );
} catch (error) {
  process.stderr.write(
    JSON.stringify({
      status: 'failed',
      code: error.code || 'TELEMETRY_CONTEXT_ERROR',
    }) + '\n',
  );
  process.exitCode = 1;
}
