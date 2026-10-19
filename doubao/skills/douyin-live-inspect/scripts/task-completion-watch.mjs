#!/usr/bin/env node
import flow from '../runtime/workflow-telemetry.cjs';
import { EVENTS, runCommand, observeResult } from '../runtime/telemetry.mjs';
import { writeFile, mkdir, rename, rm } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { prepareEcommerceReview } from '../runtime/ecommerce-review-prepare.mjs';
import { watchTaskCompletion } from '../runtime/task-completion-watch.mjs';

function parseArgs(argv) {
  const args = { output: null };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--output' && argv[i + 1]) {
      args.output = resolve(argv[i + 1]);
      i += 1;
    }
  }
  return args;
}

async function persistResult(outputPath, payload) {
  if (!outputPath) return;
  await mkdir(dirname(outputPath), { recursive: true });
  const temporary = `${outputPath}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporary, `${JSON.stringify(payload)}\n`, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
    await rename(temporary, outputPath);
  } finally {
    await rm(temporary, { force: true });
  }
}

const controller = new AbortController();
// Abort stdin too: a partial line must not keep a cancelled command alive.
const cancel = () => { controller.abort(); process.stdin.destroy(); };
process.on('SIGINT', cancel);
process.on('SIGTERM', cancel);

const { output: outputPath } = parseArgs(process.argv.slice(2));
let data = null;
await runCommand(EVENTS.formal.TASK_COMPLETION_WATCH, async () => {
try {
  let text = '';
  for await (const chunk of process.stdin) {
    text += chunk.toString('utf8');
    if (Buffer.byteLength(text) > 64 * 1024) throw Object.assign(new Error(), { code: 'INVALID_INPUT' });
    if (text.includes('\n')) break;
  }
  let input;
  try { input = JSON.parse(text.split(/\r?\n/, 1)[0]); }
  catch { throw Object.assign(new Error(), { code: 'INVALID_INPUT' }); }
  data = await watchTaskCompletion(input, { signal: controller.signal });
  if(['timed_out','cancelled'].includes(data.status))await flow.problem('inspection',data.status==='timed_out'?'WATCH_TIMEOUT':'HOST_INTERRUPTED');
  if (data.status === 'completed') {
    // Task completion starts preparation; only the Agent can perform analysis.
    data.review_phase = 'preparing';
    data.review_preparation = await prepareEcommerceReview({
      ...data.context, scenario_name: data.context.scenario,
    }, { signal: controller.signal });
    data.review_phase = 'analyzing';
    data.next_action = 'generate_review';
  }
  const payload = { ok: true, command: 'task-completion-watch', data, error: null };
  await persistResult(outputPath, payload);
  process.stdout.write(`${JSON.stringify(payload)}\n`);
} catch (error) {
  const errorCode = controller.signal.aborted ? 'CANCELLED' : error?.recoveryCode || error?.code;
  const codes = new Set(['ORIGINAL_TASK_CONTEXT_REQUIRED', 'INVALID_INPUT', 'SETUP_PENDING', 'AUTH_REQUIRED', 'PERMISSION_DENIED', 'TASK_BINDING_MISMATCH', 'TASK_QUERY_FAILED', 'CLI_UNAVAILABLE', 'INVALID_RESPONSE', 'REPORT_NOT_READY', 'TASK_FAILED', 'ASR_NOT_FOUND', 'CANCELLED', 'OUTPUT_TOO_LARGE', 'CLI_ERROR', 'GET_REPORT_FAILED']);
  if (data && errorCode === 'REPORT_NOT_READY') data.review_phase = 'waiting';
  const payload = { ok: false, command: 'task-completion-watch', data,
    error: { code: codes.has(errorCode) ? errorCode : (data ? 'PREPARATION_FAILED' : 'WATCH_FAILED'), message: data ? '复盘输入准备未能完成，请保留原任务上下文续办' : '任务监听未能继续，请保留原任务上下文续办', stage: data ? 'report_preparation' : 'task_watch', retryable: errorCode === 'REPORT_NOT_READY' },
  };
  observeResult(payload);
  try { await persistResult(outputPath, payload); } catch { /* best-effort persist */ }
  process.stdout.write(`${JSON.stringify(payload)}\n`);
  process.exitCode = 1;
} finally {
  process.removeListener('SIGINT', cancel);
  process.removeListener('SIGTERM', cancel);
}
});
