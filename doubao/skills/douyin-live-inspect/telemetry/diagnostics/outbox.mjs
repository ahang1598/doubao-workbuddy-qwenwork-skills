// 管理诊断持久化、领取、重试和确认删除，并按补报策略分派普通事件与诊断事件。
// 保留容量、有效期、尝试次数和锁边界；普通事件不新增重放，未确认发送的诊断不删除。
import { persistent } from '../config/events.mjs';
import { createRequire } from 'node:module';
import * as io from '../utils/io.mjs';
import { safeDiagnostic, asr } from './events.mjs';
import { deliver } from '../utils/payload.mjs';

const pending = new Set();
function background(promise) {
  const p = Promise.resolve(promise).catch(() => {});
  pending.add(p);
  p.finally(() => pending.delete(p));
  return p;
}
export { pending };

const require = createRequire(import.meta.url);

const spools = new Map();
function spool(root, limit = 128, context = {}) {
  const files = io.directoryFiles(root, { python: context.python });
  const write = (file, value) => files.write(file, value);
  function entries(now) {
    const result = [];
    for (const name of files.names().filter((x) => x.endsWith('.json'))) {
      const file = files.path(name);
      try {
        const v = files.read(file, 8192),
          e = safeDiagnostic(v.event);
        if (
          !e ||
          name !== e.extra.diagnostic_event_id + '.json' ||
          !Number.isFinite(v.created) ||
          now - v.created < 0 ||
          now - v.created >= 86400 ||
          !Number.isInteger(v.attempts) ||
          v.attempts < 0 ||
          v.attempts > 5 ||
          !Number.isFinite(v.next_at)
        )
          throw Error('Invalid entry');
        v.event = e;
        result.push([file, v]);
      } catch (error) {
        // 临时读盘失败不是坏记录：保留待报文件，下一轮再读取。
        if (error.code) continue;
        try {
          files.remove(file);
        } catch {}
      }
    }
    return result.sort((a, b) => a[1].created - b[1].created);
  }
  const locked = (fn) => files.locked('delivery.node-lock', fn);
  return {
    put(event, now = Date.now() / 1000) {
      event = safeDiagnostic(event);
      if (!event) return null;
      return locked(() => {
        const file = files.path(event.extra.diagnostic_event_id + '.json');
        if (files.exists(file)) return true;
        const old = entries(now);
        for (const [p] of old.slice(0, Math.max(0, old.length - limit + 1))) files.remove(p);
        write(file, { event, created: now, attempts: 0, next_at: now });
        return true;
      });
    },
    claim(now = Date.now() / 1000) {
      return (
        locked(() => {
          const eligible = entries(now)
            .filter(([, v]) => v.attempts < 5 && v.next_at <= now)
            .slice(0, 8);
          for (const [file, v] of eligible) {
            v.attempts++;
            v.next_at = now + Math.min(300, 30 * 2 ** v.attempts);
            write(file, v);
          }
          return eligible.map(([file, v]) => ({ file, event: v.event }));
        }) || []
      );
    },
    acknowledge(file) {
      return locked(() => {
        try {
          files.remove(file);
        } catch {}
      });
    },
    entries,
  };
}
function startSpool(context) {
  if (!context.cacheRoot) return null;
  const root = require('node:path').join(context.cacheRoot, 'diagnostics');
  if (spools.has(root)) return spools.get(root);
  const box = spool(root, 128, context);
  let flushing = false;
  const flush = () => {
    if (flushing) return Promise.resolve();
    flushing = true;
    // 补报也纳入桥接 EOF 的有界收口，落盘成功不代表 HTTP 已确认。
    return background((async () => {
      try {
        for (const entry of box.claim()) {
          try {
            if (await deliver(entry.event, context)) box.acknowledge(entry.file);
          } catch {
            // 单条失败仍保留补报；继续发送本轮已经领取的其他记录。
          }
        }
      } finally {
        flushing = false;
      }
    })());
  };
  const timer = setInterval(() => {
    flush().catch(() => {});
  }, 1000);
  timer.unref();
  const state = { box, flush };
  spools.set(root, state);
  flush().catch(() => {});
  return state;
}
async function submit(event, context) {
  const state = startSpool(context);
  if (!state) return false;
  const deadline = Date.now() + 1000;
  while (true) {
    try {
      const result = state.box.put(event);
      if (result !== false) {
        state.flush().catch(() => {});
        return result;
      }
    } catch {
      /* Preserve the original bounded persistence grace. */
    }
    if (Date.now() >= deadline) return false;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
}

export { spools, spool, startSpool, submit };

async function send(events, context, wait = false) {
  const deliveries = [];
  for (const value of events || []) {
    if (!value) continue;
    // ASR 与任务事件共用发送入口，业务仅提供 Key、结果和任务归属。
    const constructed = value.command === 'asr.diagnostic' && value.task !== undefined;
    const e = constructed ? asr(value.task, value.extra) : value;
    if (!e) continue;
    if (persistent(e, constructed)) await submit(e, context);
    else if (!constructed || pending.size < 32) deliveries.push(background(deliver(e, context)));
  }
  if (wait) await Promise.allSettled(deliveries);
  return true;
}

export { send };
