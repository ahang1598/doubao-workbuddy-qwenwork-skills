#!/usr/bin/env node
// 本文件负责独立的账号入口探测命令：
// 调用 runtime/account-entry.mjs 判断当前宿主是否存在可用账号态，并通过正式版 runCommand 记录探测事件。
import { detectAccountEntry } from '../runtime/account-entry.mjs';
import { EVENTS, runCommand } from '../runtime/telemetry.mjs';
await runCommand(EVENTS.formal.DETECT_ACCOUNT_ENTRY, async () => {
console.log(JSON.stringify({ok:true,data:await detectAccountEntry()}));
}, {skip:process.argv.includes('--help')});
