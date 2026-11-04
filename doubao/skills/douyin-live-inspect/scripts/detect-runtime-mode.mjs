#!/usr/bin/env node
import telemetry, { EVENTS } from '../telemetry/main.mjs';
// 识别当前运行环境，输出本地或云端模式。
import { detectRuntimeMode } from '../runtime/runtime-mode.mjs';
await telemetry.runCommand(
  { command: EVENTS.formal.DETECT_RUNTIME_MODE, skip: process.argv.includes('--help') },
  async () => {
    const result = { ok: true, command: 'detect-runtime-mode', data: detectRuntimeMode() };
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return result;
  },
);
