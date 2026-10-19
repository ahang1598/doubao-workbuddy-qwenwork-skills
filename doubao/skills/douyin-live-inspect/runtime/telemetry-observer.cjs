"use strict";

// Optional local mirror. Online delivery never goes through this server.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {randomUUID} = require('node:crypto');
const {telemetryConfigDir} = require('../lite/scripts/telemetry-identity.cjs');
const {_comments, ...groups} = require('./telemetry-events.json');
const descriptions = Object.fromEntries(Object.entries(groups).flatMap(([group, keys]) =>
  Object.entries(keys).map(([name, key]) => [key, _comments[`${group}.${name}`]])));
const MAX_BODY = 16 * 1024;
const LIMIT = 1000;
let pending = 0;
const locatorPath = env => path.join(telemetryConfigDir(env), 'telemetry-observer.json');

function readLocator(env) {
  let fd;
  try {
    fd = fs.openSync(locatorPath(env), fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0) | (fs.constants.O_NONBLOCK || 0));
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > 1024) return;
    const value = JSON.parse(fs.readFileSync(fd, 'utf8'));
    if (Number.isInteger(value.port) && value.port > 0 && value.port <= 65535 &&
        Number.isSafeInteger(value.pid) && value.pid > 0 &&
        typeof value.session === 'string' && /^[0-9a-f-]{36}$/.test(value.session)) return value;
  } catch { /* No service means no local requests or output. */ }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}

function captureEvent(event, env = process.env) {
  if (['1', 'true'].includes(String(env.BYTEDLIVE_TELEMETRY_DISABLED || '').trim().toLowerCase())) return;
  try {
    // ponytail: drop observations beyond 32 concurrent requests; never queue business events.
    if (pending >= 32) return;
    const locator = readLocator(env);
    if (!locator || !Object.hasOwn(descriptions, event.command)) return;
    const body = JSON.stringify({session: locator.session, pid: process.pid, event});
    if (Buffer.byteLength(body) > MAX_BODY) return;
    // Use a separate loopback request, never replace global fetch or the SDK endpoint.
    const request = http.request({hostname: '127.0.0.1', port: locator.port, path: '/api/events',
      method: 'POST', agent: false, headers: {'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body)}},
    response => response.resume());
    pending++;
    request.on('socket', socket => socket.unref());
    const deadline = setTimeout(() => request.destroy(), 150);
    deadline.unref();
    request.on('error', () => {});
    request.on('close', () => { pending--; clearTimeout(deadline); });
    request.end(body);
  } catch { /* Observing must never change business or online delivery. */ }
}

async function startObserver({env = process.env, port = 0} = {}) {
  if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('端口必须是 0–65535 的整数');
  const filename = locatorPath(env);
  const existing = readLocator(env);
  if (existing) {
    let alive = true;
    try { process.kill(existing.pid, 0); } catch (error) { alive = error.code !== 'ESRCH'; }
    if (alive) throw new Error(`观察服务已在运行：http://127.0.0.1:${existing.port}`);
    fs.unlinkSync(filename);
  }
  const html = fs.readFileSync(path.join(__dirname, '../ui/telemetry-observer.html'));
  const script = fs.readFileSync(path.join(__dirname, '../ui/telemetry-observer.js'));
  const clients = new Set();
  const records = [];
  let received = 0;
  const session = randomUUID();
  let origin;
  const snapshot = () => ({records, received, limit: LIMIT, session});
  const sse = (type, data) => `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
  const server = http.createServer((request, response) => {
    response.setHeader('Cache-Control', 'no-store');
    response.setHeader('X-Content-Type-Options', 'nosniff');
    response.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");
    const reply = (status, data) => {
      response.writeHead(status, {'Content-Type': 'application/json; charset=utf-8'});
      response.end(JSON.stringify(data));
    };
    // Reject browser cross-origin access and DNS rebinding. No CORS opt-in.
    if (`http://${request.headers.host}` !== origin ||
        (request.headers.origin && request.headers.origin !== origin) ||
        request.headers['sec-fetch-site'] === 'cross-site') return reply(403, {error: '仅允许本机同源访问'});
    if (request.method === 'GET' && request.url === '/') {
      response.writeHead(200, {'Content-Type': 'text/html; charset=utf-8'});
      return response.end(html);
    }
    if (request.method === 'GET' && request.url === '/app.js') {
      response.writeHead(200, {'Content-Type': 'text/javascript; charset=utf-8'});
      return response.end(script);
    }
    if (request.method === 'GET' && request.url === '/api/events') return reply(200, snapshot());
    if (request.method === 'GET' && request.url === '/api/stream') {
      response.writeHead(200, {'Content-Type': 'text/event-stream; charset=utf-8'});
      response.write(sse('snapshot', snapshot()));
      clients.add(response);
      response.on('close', () => clients.delete(response));
      return;
    }
    if (request.method !== 'POST' || request.url !== '/api/events') return reply(404, {error: '未找到'});
    if (request.headers['content-type'] !== 'application/json') return reply(415, {error: '仅接受 JSON'});
    let size = 0;
    const chunks = [];
    request.on('error', () => {});
    request.on('data', chunk => {
      size += chunk.length;
      if (size > MAX_BODY) {
        if (!response.writableEnded) reply(413, {error: '事件过大'});
        chunks.length = 0;
      } else chunks.push(chunk);
    });
    request.on('end', () => {
      if (response.writableEnded) return;
      let payload;
      try { payload = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { return reply(400, {error: '无效 JSON'}); }
      const event = payload?.event;
      if (payload?.session !== session || !event || typeof event !== 'object' || Array.isArray(event) ||
          !Object.hasOwn(descriptions, event.command) || !Number.isSafeInteger(payload.pid) || payload.pid < 1) {
        return reply(400, {error: '无效事件或观察会话已变更'});
      }
      let extra = {};
      try {
        if (event.extra !== undefined) extra = JSON.parse(event.extra);
        if (!extra || typeof extra !== 'object' || Array.isArray(extra)) throw new Error();
      } catch { return reply(400, {error: '无效事件字段'}); }
      const record = {id: ++received, captured_at: new Date().toISOString(), pid: payload.pid,
        description: descriptions[event.command], event, extra};
      // ponytail: retain 1000 events in memory; add disk retention only for historical debugging.
      records.push(record);
      if (records.length > LIMIT) records.shift();
      for (const client of clients) {
        // A slow browser must not accumulate an unbounded SSE buffer.
        if (!client.write(sse('event', {record, received, limit: LIMIT}))) client.destroy();
      }
      reply(202, {captured: true});
    });
  });
  server.requestTimeout = 2000;
  server.headersTimeout = 2000;
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', resolve);
  });
  const actualPort = server.address().port;
  origin = `http://127.0.0.1:${actualPort}`;
  try {
    fs.mkdirSync(telemetryConfigDir(env), {recursive: true, mode: 0o700});
    fs.writeFileSync(filename, JSON.stringify({port: actualPort, pid: process.pid, session}), {flag: 'wx', mode: 0o600});
  } catch (error) {
    server.close();
    throw error;
  }
  const heartbeat = setInterval(() => {
    for (const client of clients) if (!client.write(': connected\n\n')) client.destroy();
  }, 15000);
  heartbeat.unref();
  let stopped;
  const stop = () => stopped ??= (async () => {
    clearInterval(heartbeat);
    try { if (readLocator(env)?.session === session) fs.unlinkSync(filename); } catch {}
    for (const client of clients) client.end();
    await new Promise(resolve => server.close(resolve));
  })();
  return {url: origin, stop};
}

async function stopObserver({env = process.env} = {}) {
  const locator = readLocator(env);
  if (!locator) {
    if (fs.existsSync(locatorPath(env))) throw new Error('观察标记无效，无法确认服务身份；请在原终端使用 Ctrl+C 关闭');
    return false;
  }
  try { process.kill(locator.pid, 0); } catch (error) {
    if (error.code !== 'ESRCH') throw error;
    if (readLocator(env)?.session === locator.session) fs.unlinkSync(locatorPath(env));
    return false;
  }
  // Older observers expose this snapshot too. Verify the session before signalling
  // a PID from disk, so stale markers cannot stop an unrelated process.
  const url = `http://127.0.0.1:${locator.port}/api/events`;
  const response = await fetch(url, {signal: AbortSignal.timeout(2000)});
  const snapshot = response.ok ? await response.json() : null;
  if (snapshot?.session !== locator.session || readLocator(env)?.session !== locator.session) {
    throw new Error('观察会话已变更，未关闭任何进程；请重新运行关闭命令');
  }
  process.kill(locator.pid, 'SIGTERM');
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 50));
    try {
      const probe = await fetch(url, {signal: AbortSignal.timeout(500)});
      await probe.body.cancel();
    } catch (error) {
      if (error.cause?.code !== 'ECONNREFUSED') continue;
      if (readLocator(env)?.session === locator.session) fs.unlinkSync(locatorPath(env));
      return true;
    }
  }
  throw new Error('已请求关闭，但服务仍未退出；请检查原启动终端');
}

module.exports = {captureEvent, startObserver, stopObserver};
