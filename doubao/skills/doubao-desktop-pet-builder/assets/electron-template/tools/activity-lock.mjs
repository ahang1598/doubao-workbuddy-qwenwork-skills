import { randomUUID } from 'node:crypto';
import { appendFile, mkdir, open, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

function isPidAlive(pid) {
  if (!Number.isInteger(pid) || pid < 1) return false;
  try { process.kill(pid, 0); return true; }
  catch (error) { return error?.code === 'EPERM'; }
}

export async function acquireActivityLock(buildDirectory, mode) {
  await mkdir(buildDirectory, { recursive: true });
  const lockFile = path.join(buildDirectory, 'activity.lock');
  const staleLog = path.join(buildDirectory, 'stale-locks.jsonl');
  for (let attempt = 0; attempt < 2; attempt += 1) {
    let handle;
    try { handle = await open(lockFile, 'wx'); }
    catch (error) {
      if (error?.code !== 'EEXIST') throw error;
      let owner = {};
      try { owner = JSON.parse(await readFile(lockFile, 'utf8')); }
      catch { /* invalid lock is stale */ }
      if (isPidAlive(owner.pid)) throw new Error(`Development or another build is active (pid ${owner.pid}, mode ${owner.mode ?? 'unknown'}).`);
      await appendFile(staleLog, `${JSON.stringify({ recoveredAt: new Date().toISOString(), owner })}\n`, 'utf8');
      await rm(lockFile, { force: true });
      continue;
    }
    const token = randomUUID();
    const owner = { pid: process.pid, mode, token, startedAt: new Date().toISOString() };
    await handle.writeFile(`${JSON.stringify(owner)}\n`, 'utf8');
    return {
      file: lockFile,
      owner,
      async release() {
        await handle.close();
        let current;
        try { current = JSON.parse(await readFile(lockFile, 'utf8')); }
        catch { return; }
        if (current.token === token) await rm(lockFile, { force: true });
      },
    };
  }
  throw new Error(`Could not acquire activity lock: ${lockFile}`);
}
