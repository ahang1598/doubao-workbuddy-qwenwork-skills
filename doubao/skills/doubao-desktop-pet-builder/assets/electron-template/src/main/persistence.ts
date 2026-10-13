import { readFile, writeFile, rename, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

export async function atomicWriteJson(file: string, value: unknown): Promise<void> {
  const dir = path.dirname(file);
  await mkdir(dir, { recursive: true });
  const tmpFile = `${file}.${randomUUID()}.tmp`;
  await writeFile(tmpFile, JSON.stringify(value, null, 2) + '\n', 'utf8');
  await rename(tmpFile, file);
}

export async function readJson<T>(file: string, defaultValue: T): Promise<T> {
  try {
    const content = await readFile(file, 'utf8');
    return JSON.parse(content) as T;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return defaultValue;
    }
    throw error;
  }
}

export async function readValidatedJson<T>(file: string, defaultValue: T, parse: (value: unknown) => T): Promise<T> {
  try {
    return parse(JSON.parse(await readFile(file, 'utf8')));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return defaultValue;
    const corruptFile = `${file}.${new Date().toISOString().replaceAll(':', '-')}.corrupt`;
    try {
      await rename(file, corruptFile);
    } catch (renameError) {
      if ((renameError as NodeJS.ErrnoException).code !== 'ENOENT') throw renameError;
    }
    return defaultValue;
  }
}

export async function uniqueDestination(directory: string, filename: string): Promise<string> {
  const ext = path.extname(filename);
  const base = path.basename(filename, ext);
  let candidate = path.join(directory, filename);
  let counter = 1;

  while (true) {
    try {
      await readFile(candidate);
      counter += 1;
      candidate = path.join(directory, `${base}-${counter}${ext}`);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        return candidate;
      }
      throw error;
    }
  }
}
