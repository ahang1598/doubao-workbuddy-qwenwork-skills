#!/usr/bin/env node
// 执行指定账号的登录流程，授权输入不回显。
import { parseArgs } from 'node:util';
import { runLogin } from '../runtime/auth-login.mjs';
try {
  const { values } = parseArgs({
    options: {
      profile: { type: 'string' },
      environment: { type: 'string', default: 'online' },
      help: { type: 'boolean' },
      json: { type: 'boolean' },
      remote: { type: 'boolean' },
      'authorization-response-stdin': { type: 'boolean' },
      region: { type: 'string' },
    },
  });
  if (values.help)
    console.log(
      'Usage: node scripts/login.mjs [--profile NAME] [--environment online] [--remote [--authorization-response-stdin]]',
    );
  else {
    try {
      await (await import('../telemetry/main.mjs')).reportRequest({ mode: 'formal' });
    } catch {}
    console.log(
      JSON.stringify({
        ok: true,
        command: 'login',
        data: await runLogin({
          ...values,
          authorizationResponseStdin: values['authorization-response-stdin'],
        }),
      }),
    );
  }
} catch {
  console.log(
    JSON.stringify({
      ok: false,
      command: 'login',
      error: {
        code: 'AUTH_FAILED',
        message:
          'Authentication operation failed; check login status and retry. Authorization input is never echoed.',
      },
    }),
  );
  process.exitCode = 1;
}
