#!/usr/bin/env node
import { readJsonLine } from '../runtime/script-input.mjs';
import telemetry, { EVENTS } from '../telemetry/main.mjs';
import { prepareEcommerceReview } from '../runtime/ecommerce-review-prepare.mjs';

const MAX_INPUT_BYTES = 64 * 1024;
const controller = new AbortController();
// Abort stdin too: a partial line must not keep a cancelled command alive.
const cancel = () => {
  controller.abort();
  process.stdin.destroy();
};
process.on('SIGINT', cancel);
process.on('SIGTERM', cancel);

function emit(data, error = null) {
  const result = {
    ok: !error,
    command: 'ecommerce-review-prepare',
    data: error ? null : data,
    error,
  };
  process.stdout.write(`${JSON.stringify(result)}\n`);
  return result;
}

await telemetry.runCommand({ command: EVENTS.formal.ECOMMERCE_REVIEW_PREPARE }, async () => {
  try {
    return emit(
      await prepareEcommerceReview(await readJsonLine(MAX_INPUT_BYTES), {
        signal: controller.signal,
      }),
    );
  } catch (error) {
    process.exitCode = 1;
    return emit(null, {
      code: controller.signal.aborted ? 'CANCELLED' : error?.code || 'UNEXPECTED_ERROR',
      message: '复盘输入准备未能完成，请保留原任务上下文续办',
      retryable: error?.code === 'REPORT_NOT_READY',
    });
  } finally {
    process.removeListener('SIGINT', cancel);
    process.removeListener('SIGTERM', cancel);
  }
});
