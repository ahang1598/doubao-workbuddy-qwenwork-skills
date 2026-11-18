import { fork } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { profileName, readStore, writeStore, withProfileLock } from './auth-store.mjs';
import { requireOnline } from './auth.mjs';
import { runLogin } from './auth-login.mjs';

const errors = new Set(['AUTH_DENIED', 'AUTH_TIMEOUT', 'AUTH_CALLBACK_UNAVAILABLE',
  'AUTH_EXCHANGE_FAILED', 'AUTH_SESSION_INVALID', 'AUTH_STORE_FAILED',
  'AUTH_RESPONSE_INVALID', 'AUTH_INTERRUPTED', 'AUTH_START_FAILED']);
export function publicLoginError(error) {
  const code = errors.has(error?.code) ? error.code : 'AUTH_FAILED';
  return { code, message: `Login failed (${code}). Authorization input is never echoed.` };
}

export async function localLoginStatus(profile, env = process.env) {
  const state = await readStore(profile, 'login', env);
  if (!state) return undefined;
  if (state.status === 'pending') {
    let alive = false;
    if (Number.isSafeInteger(state.pid) && state.pid > 0) {
      try { process.kill(state.pid, 0); alive = true; }
      catch (error) { alive = error.code === 'EPERM'; }
    }
    // The worker owns the callback timeout; token exchange can outlive that deadline.
    if (!alive) return {
      status: 'failed', error: publicLoginError({ code: 'AUTH_INTERRUPTED' }),
    };
  }
  return { status: state.status, ...(state.error ? { error: publicLoginError(state.error) } : {}) };
}

export async function startLocalLogin(input, { env = process.env, forkImpl = fork } = {}) {
  requireOnline(input);
  const profile = profileName(input);
  // Serialize launchers separately; the worker holds the credential lock while waiting.
  return withProfileLock(`${profile}:login-launch`, env, async () => {
    const existing = await localLoginStatus(profile, env);
    if (existing?.status === 'pending') return { profile, environment: 'online', status: 'pending' };
    return new Promise((resolve, reject) => {
      const child = forkImpl(fileURLToPath(import.meta.url), ['--worker'], {
        env, detached: true, windowsHide: true, execArgv: [],
        stdio: ['ignore', 'ignore', 'ignore', 'ipc'],
      });
      let finished = false;
      const timer = setTimeout(() => finish({ code: 'AUTH_START_FAILED' }), 15000);
      const finish = (error, data) => {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        child.removeAllListeners('exit');
        if (error) child.kill();
        if (child.connected) child.disconnect();
        child.unref();
        if (error) reject(Object.assign(new Error('Login worker unavailable'), publicLoginError(error)));
        else resolve(data);
      };
      child.once('error', () => finish({ code: 'AUTH_START_FAILED' }));
      child.once('exit', () => finish({ code: 'AUTH_START_FAILED' }));
      child.once('message', (message) => {
        if (message.error) finish(message.error);
        else finish(null, { profile, environment: 'online', status: 'pending', authorization_url: message.url });
      });
      child.send({ profile }, (error) => { if (error) finish({ code: 'AUTH_START_FAILED' }); });
    });
  });
}

export async function serveLocalLogin(input, deps = {}) {
  const env = deps.env || process.env;
  const profile = profileName(input);
  const send = (message) => { if (process.connected) process.send(message, () => {}); };
  try {
    await runLogin(input, {
      ...deps, env, output: { write() {} },
      onReady: async (url) => {
        await writeStore(profile, 'login', {
          status: 'pending', pid: process.pid,
        }, env);
        send({ url });
      },
      onResult: (result) => writeStore(profile, 'login', result.error
        ? { status: 'failed', error: publicLoginError(result.error) }
        : { status: 'authenticated' }, env),
    });
  } catch (error) {
    const safe = publicLoginError(error);
    send({ error: safe });
  }
}

if (process.argv[2] === '--worker' && process.send) {
  process.once('message', async (input) => {
    await serveLocalLogin(input);
    if (process.connected) process.disconnect();
  });
}
