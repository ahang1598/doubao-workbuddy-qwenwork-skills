#!/usr/bin/env node
import { EVENTS, runCommand, observeResult } from '../runtime/telemetry.mjs';
import { prepareEcommerceReview } from '../runtime/ecommerce-review-prepare.mjs';

const MAX_INPUT_BYTES = 64 * 1024;
const controller = new AbortController();
// Abort stdin too: a partial line must not keep a cancelled command alive.
const cancel = () => { controller.abort(); process.stdin.destroy(); };
process.on('SIGINT', cancel);
process.on('SIGTERM', cancel);

function emit(data, error = null) {
  observeResult({ok:!error,error});
  process.stdout.write(`${JSON.stringify({ ok: !error, command: 'ecommerce-review-prepare', data: error ? null : data, error })}\n`);
}

async function readInput() {
  const chunks = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    size += chunk.length;
    if (size > MAX_INPUT_BYTES) throw Object.assign(new Error('stdin input is too large'), { code: 'INVALID_INPUT' });
    chunks.push(chunk);
    if (chunk.includes(10)) break;
  }
  const line = Buffer.concat(chunks).toString('utf8').split(/\r?\n/, 1)[0];
  let input;
  try { input = JSON.parse(line); } catch {
    throw Object.assign(new Error('stdin must contain one JSON object'), { code: 'INVALID_INPUT' });
  }
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw Object.assign(new Error('stdin must contain one JSON object'), { code: 'INVALID_INPUT' });
  return input;
}

await runCommand(EVENTS.formal.ECOMMERCE_REVIEW_PREPARE, async () => {
try {
  emit(await prepareEcommerceReview(await readInput(), { signal: controller.signal }));
} catch (error) {
  emit(null, { code: controller.signal.aborted ? 'CANCELLED' : error?.code || 'UNEXPECTED_ERROR', message: '复盘输入准备未能完成，请保留原任务上下文续办', retryable: error?.code === 'REPORT_NOT_READY' });
  process.exitCode = 1;
} finally {
  process.removeListener('SIGINT', cancel);
  process.removeListener('SIGTERM', cancel);
}
});
