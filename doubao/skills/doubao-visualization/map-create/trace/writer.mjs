import { createHash, randomUUID } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const hash = value =>
  createHash('sha256')
    .update(typeof value === 'string' ? value : JSON.stringify(value))
    .digest('hex');

export async function writeTrace(directory, artifacts, metadata = {}) {
  if (Object.hasOwn(artifacts, 'map.html'))
    throw new Error(
      'Trace 不保存可能含运行时凭据的 map.html；请保存 map-html.json 摘要',
    );
  const root = resolve(directory);
  await mkdir(root, { recursive: true });
  const files = {};
  for (const [name, value] of Object.entries(artifacts)) {
    const content =
      typeof value === 'string' ? value : `${JSON.stringify(value, null, 2)}\n`;
    await writeFile(resolve(root, name), content);
    files[name] = { sha256: hash(content), bytes: Buffer.byteLength(content) };
  }
  const manifest = {
    ...metadata,
    traceId: metadata.traceId || randomUUID(),
    parentTraceId: metadata.parentTraceId || null,
    createdAt: new Date().toISOString(),
    skillVersion: '2.0.0-m1',
    files,
  };
  await writeFile(
    resolve(root, 'manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
  );
  return manifest;
}
