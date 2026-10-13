#!/usr/bin/env node
import { EVENTS, runCommand, observeResult } from '../runtime/telemetry.mjs';
import { parseArgs } from 'node:util';
import { finalizeReview } from '../runtime/review-finalize.mjs';
import { parseAnalysisJson, analysisErrorDetails } from '../runtime/review-analysis.mjs';

await runCommand(EVENTS.formal.ECOMMERCE_REVIEW_FINALIZE, async () => {
try {
  const { values } = parseArgs({ options: { 'ack-delivered': { type: 'boolean' } } });
  const chunks = []; let size = 0;
  for await (const chunk of process.stdin) {
    size += chunk.length;
    if (size > 2 * 1024 * 1024) throw Object.assign(new Error('Input exceeds 2 MiB'), { code: 'INVALID_INPUT', reason: 'invalid_file_size' });
    chunks.push(chunk);
  }
  const input = parseAnalysisJson(Buffer.concat(chunks));
  const data = await finalizeReview({ ...input, ack_delivered: values['ack-delivered'] === true });
  process.stdout.write(`${JSON.stringify(observeResult({ ok: !data.error, command: 'ecommerce-review-finalize', data }))}\n`);
  if (data.error) process.exitCode = 1;
} catch (error) {
  process.stdout.write(`${JSON.stringify(observeResult({ ok: false, command: 'ecommerce-review-finalize', error: { code: error.code || 'FINALIZATION_FAILED', message: 'Review finalization could not complete; preserve the original task context', ...analysisErrorDetails(error) } }))}\n`);
  process.exitCode = error.code === 'INVALID_INPUT' ? 2 : 1;
}
});
