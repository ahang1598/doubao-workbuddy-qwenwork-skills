import { createHash } from 'node:crypto';
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { gunzipSync } from 'node:zlib';

export function readEngineArtifact(lockUrl) {
  const lock = JSON.parse(readFileSync(lockUrl, 'utf8'));
  if (
    lock.formatVersion !== 1 ||
    lock.package?.name !== '@shan-he/map-create-engine' ||
    !/^[a-f0-9]{64}$/.test(lock.sha256) ||
    lock.artifact !== 'engine.json.gz'
  )
    throw new Error('ENGINE_ARTIFACT_INVALID: 不支持的引擎锁');
  const bytes = readFileSync(new URL(lock.artifact, lockUrl));
  if (
    bytes.length !== lock.bytes ||
    createHash('sha256').update(bytes).digest('hex') !== lock.sha256
  )
    throw new Error('ENGINE_ARTIFACT_INVALID: 引擎产物与锁不一致');
  const artifact = JSON.parse(
    gunzipSync(bytes, { maxOutputLength: 16 * 1024 * 1024 }),
  );
  if (
    artifact.formatVersion !== 1 ||
    artifact.package?.name !== lock.package.name ||
    artifact.package?.version !== lock.package.version ||
    !artifact.files ||
    Array.isArray(artifact.files)
  )
    throw new Error('ENGINE_ARTIFACT_INVALID: 引擎元数据不一致');
  for (const [filename, contents] of Object.entries(artifact.files)) {
    if (
      !/^[a-zA-Z0-9_.-]+(?:\/[a-zA-Z0-9_.-]+)*$/.test(filename) ||
      filename
        .split('/')
        .some(segment => segment === '.' || segment === '..') ||
      typeof contents !== 'string' ||
      Buffer.from(contents, 'base64').toString('base64') !== contents
    )
      throw new Error('ENGINE_ARTIFACT_INVALID: 非法产物文件');
  }
  for (const required of [
    'compiler/index.mjs',
    'validation.mjs',
    'runtime.mjs',
  ])
    if (!artifact.files[required])
      throw new Error(`ENGINE_ARTIFACT_INVALID: 缺失 ${required}`);
  return { lock, artifact };
}

export function unpackEngineArtifact(lockUrl) {
  const { lock, artifact } = readEngineArtifact(lockUrl);
  const root = mkdtempSync(path.join(tmpdir(), 'map-engine-'));
  try {
    for (const [filename, contents] of Object.entries(artifact.files)) {
      const target = path.join(root, filename);
      mkdirSync(path.dirname(target), { recursive: true });
      writeFileSync(target, Buffer.from(contents, 'base64'));
    }
  } catch (error) {
    rmSync(root, { recursive: true, force: true });
    throw error;
  }
  process.once('exit', () => rmSync(root, { recursive: true, force: true }));
  return {
    root,
    lock,
    moduleUrl: filename => pathToFileURL(path.join(root, filename)).href,
  };
}
