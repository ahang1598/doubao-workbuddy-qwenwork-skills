#!/usr/bin/env node
// 本文件负责每次真实业务请求的入口埋点：
// 解析允许上报的身份字段，并通过共享发送器尽力发送一次 skill_start 事件。
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
import {EVENTS, disabled, reportEvent} from '../runtime/telemetry-reporter.cjs';

// 这是独立于账号探测和 Lite 初始化的入口事件。
// 每次业务请求由 Skill 入口调用一次；deviceId 由共享发送器按统一逻辑自动补充。
async function start() {
  const args = process.argv.slice(2);
  if (disabled()) return 'disabled';
  // 兼容旧调用的 UUID；新入口无需参数，统一复用持久化 deviceId。
  if (args.length && (args.length !== 2 || args[0] !== '--start-id' ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(args[1]))) return 'invalid_input';
  const {resolveIdentity} = require('../lite/scripts/telemetry-identity.cjs');
  const identity = await resolveIdentity(process.env);
  // 身份令牌仅用于当前进程内解析允许字段，后续立即删除，避免误传给业务链路。
  delete process.env.DOUBAO_OFFICE_BYTEDANCE_USER_ACCESS_TOKEN; // 防止后续代码把Token带上去泄露
  for (const key of Object.keys(process.env)) {
    if (key.startsWith('BYTECLOUD_CLI_API_JWT_TOKEN')) delete process.env[key];
  }
  // 报告 Skill 启动事件
  await reportEvent(EVENTS.skill.START, {product:'douyin-live-inspect', record_type:'skill_lifecycle',
    feature:'skill_start', ...identity}, {toolName:'byted-live-inspect'});
  return 'attempted';
}

let finished = false;
function finish(status) {
  if (finished) return;
  finished = true;
  // 这里只返回“尝试状态”，不代表服务端一定已成功接收。
  process.stdout.write(`${JSON.stringify({ok:true, command:'skill-start', status})}\n`);
}
const deadline = setTimeout(() => { finish('timeout'); process.exit(0); }, 2500);
try { finish(await start()); }
catch { finish('unavailable'); }
finally { clearTimeout(deadline); }
