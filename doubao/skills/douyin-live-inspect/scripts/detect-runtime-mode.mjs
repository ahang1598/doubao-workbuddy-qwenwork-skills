#!/usr/bin/env node
import { detectRuntimeMode } from '../runtime/runtime-mode.mjs';
import { EVENTS, runCommand } from '../runtime/telemetry.mjs';
await runCommand(EVENTS.formal.DETECT_RUNTIME_MODE, async () => {

const result = detectRuntimeMode();
process.stdout.write(`${JSON.stringify({ ok: true, command: 'detect-runtime-mode', data: result })}\n`);
}, {skip:process.argv.includes('--help')});
