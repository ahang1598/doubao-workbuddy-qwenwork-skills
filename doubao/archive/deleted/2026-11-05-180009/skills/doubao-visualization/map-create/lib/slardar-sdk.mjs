import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';

export function readSlardarSdk() {
  const root = new URL('../assets/slardar/', import.meta.url);
  const lock = JSON.parse(readFileSync(new URL('sdk.lock.json', root), 'utf8'));
  const bytes = readFileSync(new URL('sdk.json.gz', root));
  const hash = value => createHash('sha256').update(value).digest('hex');
  if (hash(bytes) !== lock.sha256) throw new Error('SLARDAR_SDK_HASH_MISMATCH');
  const { files } = JSON.parse(gunzipSync(bytes));
  for (const [name, digest] of Object.entries(lock.files))
    if (hash(files[name]) !== digest)
      throw new Error('SLARDAR_SDK_FILE_MISMATCH');
  return { files, lock };
}
