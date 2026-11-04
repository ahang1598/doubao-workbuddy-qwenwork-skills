// 提供受限文件读取、原子写入、进程锁和有界管道消息读取等底层能力。
// 只负责存储与通信，不判断哪些事件应触发、失败如何归因或业务是否完成。
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

function removeOwner(directory, owner) {
  // Never recursively delete the shared path: another process may already own it.
  try {
    fs.unlinkSync(path.join(directory, owner));
  } catch {}
  try {
    fs.rmdirSync(directory);
  } catch {} // A replacement lock is nonempty.
}

function recover(directory) {
  let fd;
  try {
    if (!fs.lstatSync(directory).isDirectory()) return; // Legacy files have no provable owner.
    const names = fs.readdirSync(directory);
    if (!names.length) {
      try {
        fs.rmdirSync(directory);
      } catch {}
      return;
    }
    if (names.length !== 1) return;
    const match = /^owner-([1-9][0-9]*)-([0-9a-f-]{36})\.json$/.exec(names[0]);
    if (!match) return;
    fd = fs.openSync(
      path.join(directory, names[0]),
      fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0) | (fs.constants.O_NONBLOCK || 0),
    );
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > 1024) return;
    const owner = JSON.parse(fs.readFileSync(fd, 'utf8'));
    if (
      !Number.isSafeInteger(owner.pid) ||
      owner.pid <= 0 ||
      String(owner.pid) !== match[1] ||
      owner.token !== match[2]
    )
      return;
    try {
      process.kill(owner.pid, 0);
      return;
    } catch (error) {
      if (error.code !== 'ESRCH') return;
    } // EPERM / PID reuse remain locked.
    removeOwner(directory, names[0]);
  } catch {
    /* Missing, malformed or unverifiable ownership is never guessed. */
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
  }
}

function tryAcquire(directory) {
  const token = randomUUID(),
    owner = `owner-${process.pid}-${token}.json`;
  const pending = `${directory}.${token}.pending`;
  fs.mkdirSync(pending, { mode: 0o700 });
  let published = false;
  try {
    fs.writeFileSync(path.join(pending, owner), JSON.stringify({ pid: process.pid, token }), {
      flag: 'wx',
      mode: 0o600,
    });
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        // Publish a populated directory atomically. Live locks are never empty,
        // so an old reclaimer's rmdir cannot remove a newly acquired lock.
        fs.renameSync(pending, directory);
        published = true;
        return () => removeOwner(directory, owner);
      } catch (error) {
        if (!['EEXIST', 'ENOTEMPTY', 'ENOTDIR', 'EISDIR', 'EPERM', 'EACCES'].includes(error.code))
          throw error;
        // A conflicting owner may release between rename and inspection.
        // Retry contention; genuine permission errors still fail immediately.
        if (!fs.existsSync(directory)) {
          if (['EEXIST', 'ENOTEMPTY', 'ENOTDIR', 'EISDIR'].includes(error.code)) continue;
          throw error;
        }
        recover(directory);
      }
    }
  } finally {
    if (!published) removeOwner(pending, owner);
  }
}

async function acquire(directory, timeout = 500) {
  const deadline = Date.now() + timeout;
  do {
    const release = tryAcquire(directory);
    if (release) return release;
    if (Date.now() >= deadline) break;
    await new Promise((resolve) => setTimeout(resolve, 10));
  } while (true);
  throw Object.assign(new Error('Telemetry state is locked'), { code: 'ELOCKED' });
}
function acquireSync(directory, timeout = 500) {
  const deadline = Date.now() + timeout,
    sleeper = new Int32Array(new SharedArrayBuffer(4));
  do {
    const release = tryAcquire(directory);
    if (release) return release;
    if (Date.now() >= deadline) break;
    Atomics.wait(sleeper, 0, 0, 10);
  } while (true);
  throw Object.assign(new Error('Telemetry state is locked'), { code: 'ELOCKED' });
}
export { acquire, acquireSync };

// Bound each local frame before parsing; never buffer an unbounded child stream.
export async function* readMessages(stream, limit) {
  let pending = Buffer.alloc(0);
  for await (const chunk of stream) {
    pending = Buffer.concat([pending, Buffer.from(chunk)]);
    let newline;
    while ((newline = pending.indexOf(10)) >= 0) {
      if (newline > limit) throw Error('frame too large');
      const line = pending.subarray(0, newline);
      pending = pending.subarray(newline + 1);
      if (line.length) yield JSON.parse(line.toString('utf8'));
    }
    if (pending.length > limit) throw Error('frame too large');
  }
  if (pending.length) throw Error('incomplete frame');
}

const os = require('node:os');
export function telemetryConfigDir(env = process.env, platform = process.platform) {
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

export function privateDirectory(directory, { python, platform = process.platform } = {}) {
  try {
    const info = fs.lstatSync(directory);
    if (info.isSymbolicLink() || !info.isDirectory()) throw Error('Private directory required');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  if (platform === 'win32') {
    if (!python) throw Error('Python runtime required for private directory');
    const helper = new URL('../../lite/scripts/telemetry_cache.py', import.meta.url);
    const result = require('node:child_process').spawnSync(
      python,
      [require('node:url').fileURLToPath(helper), directory],
      {
        env: { ...process.env, BYTEDLIVE_TELEMETRY_DISABLED: '1' },
        stdio: 'ignore',
        timeout: 2000,
        windowsHide: true,
      },
    );
    if (result.error || result.status !== 0) throw Error('Private directory unavailable');
  } else if (fs.statSync(directory).mode & 0o077) throw Error('Private directory required');
}

// File primitives only. Callers own event validity, retention and retry decisions.
export function directoryFiles(directory, options = {}) {
  const root = path.resolve(directory);
  const filePath = (file) => {
    const resolved = path.resolve(root, file);
    if (path.dirname(resolved) !== root) throw Error('File outside directory');
    return resolved;
  };
  const remove = (file) => {
    try {
      fs.unlinkSync(filePath(file));
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  };
  return {
    path: (name) => filePath(name),
    names() {
      try {
        return fs.readdirSync(root);
      } catch (error) {
        if (error.code === 'ENOENT') return [];
        throw error;
      }
    },
    exists: (file) => fs.existsSync(filePath(file)),
    read(file, maxBytes) {
      const name = filePath(file);
      if (fs.lstatSync(name).isSymbolicLink()) throw Error('File link rejected');
      const fd = fs.openSync(
        name,
        fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0) | (fs.constants.O_NONBLOCK || 0),
      );
      try {
        const info = fs.fstatSync(fd);
        if (!info.isFile() || info.size > maxBytes) throw Error('Invalid file');
        return JSON.parse(fs.readFileSync(fd, 'utf8'));
      } finally {
        fs.closeSync(fd);
      }
    },
    write(file, value) {
      atomicWrite(filePath(file), JSON.stringify(value));
    },
    remove,
    locked(name, operation) {
      privateDirectory(root, options);
      let release;
      try {
        release = acquireSync(filePath(name), 0);
      } catch (error) {
        if (error.code === 'ELOCKED') return false;
        throw error;
      }
      try {
        return operation();
      } finally {
        release();
      }
    },
  };
}

export function readText(file, maxBytes) {
  if (!fs.lstatSync(file).isFile()) throw Error('Invalid file');
  const fd = fs.openSync(
    file,
    fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0) | (fs.constants.O_NONBLOCK || 0),
  );
  try {
    const stat = fs.fstatSync(fd);
    if (!stat.isFile()) throw Error('Invalid file');
    if (stat.size > maxBytes) throw Object.assign(Error('Invalid file'), { code: 'EFILESIZE' });
    return fs.readFileSync(fd, 'utf8');
  } finally {
    fs.closeSync(fd);
  }
}
export function atomicWrite(file, text, { exclusive = false } = {}) {
  const temporary = file + '.' + randomUUID() + '.tmp';
  try {
    fs.writeFileSync(temporary, text, { flag: 'wx', mode: 0o600 });
    if (exclusive) {
      try {
        fs.linkSync(temporary, file);
      } catch (error) {
        if (error.code !== 'EEXIST') throw error;
      }
    } else fs.renameSync(temporary, file);
  } finally {
    try {
      fs.unlinkSync(temporary);
    } catch {}
  }
}
