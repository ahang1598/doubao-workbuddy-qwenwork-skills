#!/usr/bin/env node
import telemetry, { EVENTS } from '../telemetry/main.mjs';
// 按上下文 ID 清理复盘临时输入。
import { cleanupReviewInput, REVIEW_INPUT_ROOT } from '../runtime/ecommerce-review-input.mjs';
import { join } from 'node:path';

await telemetry.runCommand({ command: EVENTS.formal.ECOMMERCE_REVIEW_CLEANUP }, async () => {
  const id = String(process.argv[2] || '').trim();
  if (!/^[0-9a-f-]{36}$/i.test(id)) {
    const result = {
      ok: false,
      error: { code: 'INVALID_INPUT', message: 'cleanup id is required' },
    };
    process.stderr.write(`${JSON.stringify(result)}\n`);
    process.exitCode = 2;
    return result;
  }
  await cleanupReviewInput(join(REVIEW_INPUT_ROOT, `${id}.json`));
  const result = { ok: true, command: 'ecommerce-review-cleanup', data: { removed: true } };
  process.stdout.write(`${JSON.stringify(result)}\n`);
  return result;
});
