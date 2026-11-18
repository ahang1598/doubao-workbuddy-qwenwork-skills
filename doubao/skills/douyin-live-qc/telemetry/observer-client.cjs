// 同机开发观察器的有界传输，供独立分发的 Skill 共用。
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
function telemetryConfigDir(env = process.env, platform = process.platform) {
  if (env.DOUYIN_LIVE_INSPECT_CONFIG_DIR) return env.DOUYIN_LIVE_INSPECT_CONFIG_DIR;
  const home = env.HOME || env.USERPROFILE || os.homedir();
  const base =
    platform === 'darwin'
      ? path.join(home, 'Library', 'Application Support')
      : platform === 'win32'
        ? env.LOCALAPPDATA || path.join(home, 'AppData', 'Local')
        : env.XDG_CONFIG_HOME || path.join(home, '.config');
  return path.join(base, 'douyin-live-inspect');
}
const MAX_BODY = 16 * 1024;
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
    if (!locator) return;
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

module.exports = {captureEvent, locatorPath, readLocator, telemetryConfigDir};
