#!/usr/bin/env node
import { EVENTS, runCommand, observeResult } from '../runtime/telemetry.mjs';
import { cleanupReviewInput, REVIEW_INPUT_ROOT } from '../runtime/ecommerce-review-input.mjs';
import { join } from 'node:path';

await runCommand(EVENTS.formal.ECOMMERCE_REVIEW_CLEANUP, async () => {
const id = String(process.argv[2] || '').trim();
if (!/^[0-9a-f-]{36}$/i.test(id)) {
  process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'INVALID_INPUT', message: 'cleanup id is required' } })}\n`);
  observeResult({ok:false,error:{code:'INVALID_INPUT'}});
  process.exitCode = 2;
} else {
  await cleanupReviewInput(join(REVIEW_INPUT_ROOT, `${id}.json`));
  process.stdout.write(`${JSON.stringify({ ok: true, command: 'ecommerce-review-cleanup', data: { removed: true } })}\n`);
}
});
