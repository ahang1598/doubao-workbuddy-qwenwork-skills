#!/usr/bin/env node
// 执行指定账号的登录流程，授权输入不回显。
import { parseArgs } from 'node:util';
import { startLocalLogin, publicLoginError } from '../runtime/auth-local-login.mjs';
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
        data: await (values.remote || values['authorization-response-stdin'] ? runLogin : startLocalLogin)({
          ...values,
          authorizationResponseStdin: values['authorization-response-stdin'],
        }),
      }),
    );
  }
} catch (error) {
  console.log(
    JSON.stringify({
      ok: false,
      command: 'login',
      error: publicLoginError(error),
    }),
  );
  process.exitCode = 1;
}
