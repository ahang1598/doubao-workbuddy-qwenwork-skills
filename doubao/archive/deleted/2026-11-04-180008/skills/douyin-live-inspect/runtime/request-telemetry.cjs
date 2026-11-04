'use strict';
const path = require('node:path');
const {spawn} = require('node:child_process');
const {disabled} = require('./telemetry-reporter.cjs');
const fs = require('node:fs');
const {claimTask, readContext, reserveTask} = require('./lite-task-context.cjs');

async function reportRequest({mode, context, newRequest = false, select = true, env = process.env} = {}) {
  if (disabled(env) || ![undefined, 'lite', 'formal'].includes(mode)) return;
  const deadline = Date.now() + 2500;
  let events;
  try {
    if (!context) {
      if (env.INSPECT_USAGE_CONTEXT_DIR) {
        const task_dir = fs.realpathSync(env.INSPECT_USAGE_CONTEXT_DIR);
        const value = readContext(task_dir);
        context = {task_dir, ...(value ? {task_id:value.task_id} : {})};
      } else context = reserveTask();
    }
    if (!context) return;
    env.INSPECT_USAGE_CONTEXT_DIR = context.task_dir;
    events = await claimTask(context, mode, {newRequest, select});
  } catch { return; }
  // Claims are attempts: timeout/network failure never causes a replay on retry.
  for (const [index, [script, ...args]] of events.entries()) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    if (context.task_id && mode !== 'formal') args.push('--task-dir', context.task_dir);
    const budget = Math.floor(remaining / (events.length - index));
    await new Promise(resolve => {
      try {
        const child = spawn(process.execPath, [path.join(__dirname, '../scripts', script), ...args], {env, stdio:'ignore'});
        const timer = setTimeout(() => { child.kill(); resolve(); }, budget);
        const done = () => { clearTimeout(timer); resolve(); };
        child.once('error', done); child.once('close', done);
      } catch { resolve(); }
    });
  }
}
module.exports = {reportRequest};
