#!/usr/bin/env node
import {parseArgs} from 'node:util';
import {createRequire} from 'node:module';
import {EVENTS, disabled, reportEvent} from '../runtime/telemetry-reporter.cjs';
const require = createRequire(import.meta.url);

async function selected() {
  if (disabled()) return 'disabled';
  const args = process.argv.slice(2);
  if (args.filter(a=>a==='--mode' || a.startsWith('--mode=')).length !== 1) return 'invalid_input';
  const {values} = parseArgs({args, options:{mode:{type:'string'}, 'task-dir':{type:'string'}}});
  if (!['lite','formal'].includes(values.mode)) return 'invalid_input';
  const context = values['task-dir'] ? require('../runtime/lite-task-context.cjs').readContext(values['task-dir']) : undefined;
  const {resolveIdentity} = require('../lite/scripts/telemetry-identity.cjs');
  const identity = await resolveIdentity(process.env);
  // 只传递解析后的允许字段，不把认证令牌带入发送链路。
  delete process.env.DOUBAO_OFFICE_BYTEDANCE_USER_ACCESS_TOKEN;
  for (const key of Object.keys(process.env)) {
    if (key.startsWith('BYTECLOUD_CLI_API_JWT_TOKEN')) delete process.env[key];
  }
  // 报告版本选择事件
  await reportEvent(EVENTS.skill.VERSION_SELECTED, {
    product: 'douyin-live-inspect', record_type: 'skill_lifecycle',
    feature: 'version_selection', inspection_mode: values.mode,
    ...(values.mode === 'lite' && context?.funnel_schema_version === 1 ? {funnel_schema_version:1} : {}), ...(context ? {task_id:context.task_id} : {}), ...identity,
  }, {toolName: 'byted-live-inspect'});
  return 'attempted';
}

let finished = false;
function finish(status) {
  if (finished) return;
  finished = true;
  // attempted 仅表示尝试发送，不保证服务端收到。
  process.stdout.write(`${JSON.stringify({ok:true, command:'version-selected', status})}\n`);
}
const deadline = setTimeout(() => { finish('timeout'); process.exit(0); }, 2500);
try { finish(await selected()); }
catch (error) { finish(error.code?.startsWith('ERR_PARSE_ARGS') ? 'invalid_input' : 'unavailable'); }
finally { clearTimeout(deadline); }
