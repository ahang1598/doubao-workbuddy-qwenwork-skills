#!/usr/bin/env node
import { readStdin } from '../runtime/script-input.mjs';
import telemetry, { EVENTS } from '../telemetry/main.mjs';
// 完成复盘报告校验、保存及显式交付确认。
import { parseArgs } from 'node:util';
import { finalizeReview } from '../runtime/review-finalize.mjs';
import { parseAnalysisJson, analysisErrorDetails } from '../runtime/review-analysis.mjs';

await telemetry.runCommand({ command: EVENTS.formal.ECOMMERCE_REVIEW_FINALIZE }, async () => {
  try {
    const { values } = parseArgs({ options: { 'ack-delivered': { type: 'boolean' } } });
    const input = parseAnalysisJson(
      await readStdin(
        2 * 1024 * 1024,
        Object.assign(new Error('Input exceeds 2 MiB'), {
          code: 'INVALID_INPUT',
          reason: 'invalid_file_size',
        }),
      ),
    );
    const data = await finalizeReview({
      ...input,
      ack_delivered: values['ack-delivered'] === true,
    });
    const result = { ok: !data.error, command: 'ecommerce-review-finalize', data };
    process.stdout.write(`${JSON.stringify(result)}\n`);
    if (data.error) process.exitCode = 1;
    return result;
  } catch (error) {
    const result = {
      ok: false,
      command: 'ecommerce-review-finalize',
      error: {
        code: error.code || 'FINALIZATION_FAILED',
        message: 'Review finalization could not complete; preserve the original task context',
        ...analysisErrorDetails(error),
      },
    };
    process.stdout.write(`${JSON.stringify(result)}\n`);
    process.exitCode = error.code === 'INVALID_INPUT' ? 2 : 1;
    return result;
  }
});
