#!/usr/bin/env node
import telemetry, { EVENTS } from '../telemetry/main.mjs';
// 探测当前宿主支持的登录方式。
import { probeLoginCapability } from '../runtime/login-capability.mjs';
await telemetry.runCommand(
  { command: EVENTS.formal.CHECK_LOGIN_CAPABILITY, skip: process.argv.includes('--help') },
  async () => {
    const result = { ok: true, data: probeLoginCapability() };
    console.log(JSON.stringify(result));
    return result;
  },
);
