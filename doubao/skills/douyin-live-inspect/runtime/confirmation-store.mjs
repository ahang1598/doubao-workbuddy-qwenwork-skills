import { randomBytes, createHash } from 'node:crypto';
import { mkdirSync, chmodSync, writeFileSync, readFileSync, renameSync, unlinkSync } from 'node:fs';
import { join } from 'node:path';
import { configDir } from './auth-store.mjs';
const digest = value => createHash('sha256').update(value).digest('hex');
const invalid = () => Object.assign(new Error('Invalid confirmation'), { code: 'INVALID_CONFIRMATION' });
export function createConfirmationStore({ directory, env = process.env, now = Date.now } = {}) {
  directory ??= join(configDir(env), 'confirmations');
  return {
    issue(scope) {
      mkdirSync(directory, { recursive: true, mode: 0o700 });
      chmodSync(directory, 0o700);
      const token = randomBytes(32).toString('hex');
      const expires_at = new Date(now() + 5 * 60 * 1000).toISOString();
      writeFileSync(join(directory, digest(token)), JSON.stringify({ scope, expires_at }), { mode: 0o600, flag: 'wx' });
      return { token, expires_at, target: scope };
    },
    consume(token, scope) {
      if (!/^[a-f0-9]{64}$/.test(String(token))) throw invalid();
      const path = join(directory, digest(token));
      const claimed = path + '.' + randomBytes(8).toString('hex');
      // Claim once across processes, before the write. Unknown write outcomes
      // must never resurrect authorization for a second attempt.
      try { renameSync(path, claimed); } catch { throw invalid(); }
      try {
        const record = JSON.parse(readFileSync(claimed, 'utf8'));
        if (!Number.isFinite(Date.parse(record.expires_at)) || Date.parse(record.expires_at) <= now() || JSON.stringify(record.scope) !== JSON.stringify(scope)) throw invalid();
      } finally { unlinkSync(claimed); }
    }
  };
}
