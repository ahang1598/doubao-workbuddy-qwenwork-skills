#!/usr/bin/env node
// 本文件负责每次真实业务请求的入口埋点：
// 解析允许上报的身份字段，并通过共享发送器尽力发送一次 skill_start 事件。
import { parseArgs } from 'node:util';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
import telemetry, { disabled } from '../telemetry/main.mjs';

// 这是独立于账号探测和 Lite 初始化的入口事件。
// 由业务入口脚本自动调用；deviceId 由共享发送器按统一逻辑自动补充。
async function start() {
  const args = process.argv.slice(2);
  if (disabled()) return 'disabled';
  const { values } = parseArgs({
    args,
    options: { 'start-id': { type: 'string' }, 'task-dir': { type: 'string' } },
  });
  if (
    values['start-id'] &&
    !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      values['start-id'],
    )
  )
    return 'invalid_input';
  const context = values['task-dir']
    ? require('../runtime/lite-task-context.cjs').readContext(values['task-dir'])
    : undefined;
  const sent = await telemetry.withContext({ standalone: true }, (current) =>
    current.skillStart({ context }),
  );
  return sent === undefined ? 'unavailable' : 'attempted';
}

let finished = false;
function finish(status) {
  if (finished) return;
  finished = true;
  // 这里只返回“尝试状态”，不代表服务端一定已成功接收。
  process.stdout.write(`${JSON.stringify({ ok: true, command: 'skill-start', status })}\n`);
}
const deadline = setTimeout(() => {
  finish('timeout');
  process.exit(0);
}, 2500);
try {
  finish(await start());
} catch (error) {
  finish(error.code?.startsWith('ERR_PARSE_ARGS') ? 'invalid_input' : 'unavailable');
} finally {
  clearTimeout(deadline);
}
