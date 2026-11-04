#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { createRequire } from 'node:module';
import telemetry, { disabled } from '../telemetry/main.mjs';
const require = createRequire(import.meta.url);

async function selected() {
  if (disabled()) return 'disabled';
  const args = process.argv.slice(2);
  if (args.filter((a) => a === '--mode' || a.startsWith('--mode=')).length !== 1)
    return 'invalid_input';
  const { values } = parseArgs({
    args,
    options: { mode: { type: 'string' }, 'task-dir': { type: 'string' } },
  });
  if (!['lite', 'formal'].includes(values.mode)) return 'invalid_input';
  const context = values['task-dir']
    ? require('../runtime/lite-task-context.cjs').readContext(values['task-dir'])
    : undefined;
  const sent = await telemetry.withContext({ standalone: true }, (current) =>
    current.versionSelected({ mode: values.mode, context }),
  );
  return sent === undefined ? 'unavailable' : 'attempted';
}

let finished = false;
function finish(status) {
  if (finished) return;
  finished = true;
  // attempted 仅表示尝试发送，不保证服务端收到。
  process.stdout.write(`${JSON.stringify({ ok: true, command: 'version-selected', status })}\n`);
}
const deadline = setTimeout(() => {
  finish('timeout');
  process.exit(0);
}, 2500);
try {
  finish(await selected());
} catch (error) {
  finish(error.code?.startsWith('ERR_PARSE_ARGS') ? 'invalid_input' : 'unavailable');
} finally {
  clearTimeout(deadline);
}
