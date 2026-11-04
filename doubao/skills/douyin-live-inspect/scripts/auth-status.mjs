#!/usr/bin/env node
import telemetry, { EVENTS } from '../telemetry/main.mjs';
// 查询指定账号的认证状态，不输出凭证。
import { parseArgs } from 'node:util';
import { getAuthStatus } from '../runtime/auth.mjs';
await telemetry.runCommand(
  { command: EVENTS.formal.AUTH_STATUS, skip: process.argv.includes('--help') },
  async () => {
    try {
      const { values } = parseArgs({
        options: {
          profile: { type: 'string' },
          environment: { type: 'string', default: 'online' },
          help: { type: 'boolean' },
          json: { type: 'boolean' },
        },
      });
      if (values.help)
        console.log('Usage: node scripts/auth-status.mjs [--profile NAME] [--environment online]');
      else {
        const result = { ok: true, command: 'auth-status', data: await getAuthStatus(values) };
        console.log(JSON.stringify(result));
        return result;
      }
    } catch {
      const result = {
        ok: false,
        command: 'auth-status',
        error: {
          code: 'AUTH_FAILED',
          message:
            'Authentication operation failed; check login status and retry. Authorization input is never echoed.',
        },
      };
      console.log(JSON.stringify(result));
      process.exitCode = 1;
      return result;
    }
  },
);
