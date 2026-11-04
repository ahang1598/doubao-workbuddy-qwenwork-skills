#!/usr/bin/env node
import telemetry, { EVENTS } from '../telemetry/main.mjs';
// 本文件负责独立的账号入口探测命令：
// 调用 runtime/account-entry.mjs 判断当前宿主是否存在可用账号态，并通过正式版 记录探测事件。
import { detectAccountEntry } from '../runtime/account-entry.mjs';
await telemetry.runCommand(
  { command: EVENTS.formal.DETECT_ACCOUNT_ENTRY, skip: process.argv.includes('--help') },
  async () => {
    const result = { ok: true, data: await detectAccountEntry() };
    console.log(JSON.stringify(result));
    return result;
  },
);
