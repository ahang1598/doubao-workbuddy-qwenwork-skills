import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

export function args(argv = process.argv.slice(2)) {
  const result = {};
  for (let index = 0; index < argv.length; index++) {
    const value = argv[index];
    if (!value.startsWith('--')) throw new Error(`未知参数 ${value}`);
    const key = value.slice(2);
    const next = argv[index + 1];
    result[key] = next && !next.startsWith('--') ? argv[++index] : true;
  }
  return result;
}

export async function readJson(file) {
  return JSON.parse(await readFile(resolve(file), 'utf8'));
}

export async function writeText(file, content) {
  const target = resolve(file);
  await mkdir(dirname(target), { recursive: true });
  const temporary = `${target}.tmp-${process.pid}`;
  await writeFile(temporary, content);
  await rename(temporary, target);
}

export async function writeJson(file, value) {
  await writeText(file, `${JSON.stringify(value, null, 2)}\n`);
}

export async function writeReport(file, value) {
  const previous = await readJson(file).catch(error => {
    if (error.code === 'ENOENT') return null;
    throw error;
  });
  if (previous)
    await writeJson(
      `${file}.history/${Date.now()}-${process.pid}.json`,
      previous,
    );
  await writeJson(file, value);
}

export const safeError = error => ({
  name: error?.name || 'Error',
  ...(error?.code ? { code: error.code } : {}),
  message: String(error?.message || error).replace(
    /\b[a-f0-9]{32}\b/gi,
    '[redacted]',
  ),
  diagnostics: error?.diagnostics || [],
});
