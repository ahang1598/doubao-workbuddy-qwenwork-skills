#!/usr/bin/env node
import { probeLoginCapability } from '../runtime/login-capability.mjs';
import { EVENTS, runCommand } from '../runtime/telemetry.mjs';
await runCommand(EVENTS.formal.CHECK_LOGIN_CAPABILITY, async () => {
console.log(JSON.stringify({ok:true,data:probeLoginCapability()}));
}, {skip:process.argv.includes('--help')});
