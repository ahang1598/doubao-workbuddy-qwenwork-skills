#!/usr/bin/env node
// Called only after the host actually delivers a verified report (or failure explanation).
import { readStdin } from '../runtime/script-input.mjs';
import telemetry from '../telemetry/main.mjs';
try {
  const input = JSON.parse(await readStdin(4096, new Error('input too large')));
  const accepted = await telemetry.withContext(
    {},
    (current) =>
      current.disabled ||
      current.deliveryConfirmed({
        identity: input,
        kind: input.report_kind,
        outcome: input.outcome,
      }),
  );
  if (accepted !== true) throw Error('delivery not confirmed');
  process.stdout.write(JSON.stringify({ ok: true, command: 'workflow-delivery' }) + '\n');
} catch {
  process.stdout.write(
    JSON.stringify({
      ok: false,
      error: {
        code: 'DELIVERY_NOT_CONFIRMED',
        message: '原流程、任务状态或报告就绪证据不匹配；保留原任务续办。',
      },
    }) + '\n',
  );
  process.exitCode = 2;
}
