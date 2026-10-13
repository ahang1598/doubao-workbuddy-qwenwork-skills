import { spawn } from 'node:child_process';
import { performance } from 'node:perf_hooks';
import { setTimeout as delay } from 'node:timers/promises';

const failure = code => Object.assign(new Error('PROBE_EXECUTION_FAILED'), { code });

// One owner for deadlines and children: a returned routing decision must not leave
// authentication, pagination or telemetry running behind the conversation.
export function createProbeSession({ budgetMs = 10_000 } = {}) {
  const started = performance.now();
  const controller = new AbortController();
  const children = new Set();
  const stages = {};
  let stage = 'account';
  let expired = false;
  const deadline = setTimeout(() => {
    expired = true;
    controller.abort();
  }, budgetMs);
  const remaining = () => Math.max(0, budgetMs - (performance.now() - started));
  const check = () => {
    if (remaining() === 0) expired = true;
    if (expired || controller.signal.aborted) throw failure('ENTRY_DEADLINE');
  };

  async function measure(name, operation, { timeout = remaining() } = {}) {
    check();
    stage = name;
    const span = stages[name] ||= { active: 0, elapsed: 0, begin: 0 };
    if (span.active++ === 0) span.begin = performance.now();
    const local = new AbortController();
    const signal = AbortSignal.any([controller.signal, local.signal]);
    let timer;
    let abort;
    try {
      const cancelled = new Promise((_, reject) => {
        abort = () => reject(failure(remaining() <= 0 || expired ? 'ENTRY_DEADLINE' : 'ETIMEDOUT'));
        signal.addEventListener('abort', abort, { once: true });
        const left = remaining();
        const globalDeadline = timeout >= left;
        timer = setTimeout(() => {
          if (globalDeadline) { expired = true; controller.abort(); }
          else local.abort();
        }, Math.min(timeout, left));
      });
      const value = await Promise.race([Promise.resolve().then(() => operation(signal)), cancelled]);
      check();
      return value;
    } finally {
      clearTimeout(timer);
      signal.removeEventListener('abort', abort);
      if (--span.active === 0) span.elapsed += performance.now() - span.begin;
    }
  }

  function run(command, args, { env = process.env, timeout = 30_000, maxBuffer = 4 * 1024 * 1024 } = {}) {
    check();
    return new Promise((resolve, reject) => {
      let stdout = ''; let stderr = ''; let bytes = 0; let code;
      let killTimer; let timer; let killer;
      const child = spawn(command, args, {
        env, shell: false, stdio: ['ignore', 'pipe', 'pipe'],
        detached: process.platform !== 'win32', windowsHide: true,
      });
      const signalTree = signal => {
        if (!child.pid) return;
        try {
          if (process.platform === 'win32') {
            // taskkill is the Windows process-tree equivalent of a POSIX group.
            if (!killer) {
              killer = spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
              killer.on('error', () => child.kill());
            }
          } else process.kill(-child.pid, signal);
        } catch { /* Already exited. */ }
      };
      const stop = reason => {
        if (code) return;
        code = reason;
        signalTree('SIGTERM');
        killTimer = setTimeout(() => signalTree('SIGKILL'), 100);
      };
      const abort = () => stop(expired ? 'ENTRY_DEADLINE' : 'PROBE_CANCELLED');
      let done;
      const completion = new Promise(resolveDone => { done = resolveDone; });
      const record = { stop, completion };
      children.add(record);
      controller.signal.addEventListener('abort', abort, { once: true });
      timer = setTimeout(() => stop(remaining() <= 0 ? 'ENTRY_DEADLINE' : 'ETIMEDOUT'), Math.min(timeout, remaining()));
      const collect = target => chunk => {
        bytes += Buffer.byteLength(chunk);
        if (bytes > maxBuffer) { stop('OUTPUT_LIMIT'); return; }
        if (target === 'out') stdout += chunk.toString(); else stderr += chunk.toString();
      };
      child.stdout.setEncoding('utf8');
      child.stderr.setEncoding('utf8');
      child.stdout.on('data', collect('out'));
      child.stderr.on('data', collect('err'));
      child.on('error', error => { code = error.code || 'EXECUTION_FAILED'; });
      child.on('close', (status, signal) => {
        clearTimeout(timer);
        // Kill surviving descendants even when their parent honored SIGTERM.
        if (code) signalTree('SIGKILL');
        clearTimeout(killTimer);
        controller.signal.removeEventListener('abort', abort);
        children.delete(record);
        done();
        if (code) reject(failure(code));
        else resolve({ status, signal, stdout, stderr });
      });
    });
  }

  return {
    run, measure, remaining, check, signal: controller.signal,
    get expired() { return expired || remaining() === 0; },
    get stage() { return stage; },
    async sleep(ms) { check(); await delay(Math.min(ms, remaining()), undefined, { signal: controller.signal }); check(); },
    timings() { return { total_ms: Math.round(performance.now() - started), stages: Object.fromEntries(Object.entries(stages).map(([k, v]) => [k, Math.round(v.elapsed + (v.active ? performance.now() - v.begin : 0))])) }; },
    async close() {
      clearTimeout(deadline);
      controller.abort();
      let cleanupTimer;
      try {
        await Promise.race([
          Promise.all([...children].map(child => child.completion)),
          new Promise(resolve => { cleanupTimer = setTimeout(resolve, 1000); }),
        ]);
      } finally { clearTimeout(cleanupTimer); }
    },
  };
}
