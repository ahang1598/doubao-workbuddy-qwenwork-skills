import { spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';

const root = process.cwd();
const forwarded = process.argv.slice(2);

async function run(script) {
  const child = spawn(process.execPath, [path.join(root, 'tools', script), ...forwarded], {
    cwd: root,
    stdio: 'inherit',
    shell: false,
  });
  const code = await new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', (value) => resolve(value ?? 1));
  });
  if (code !== 0) process.exit(code);
}

await run('process-assets.mjs');
await run('qa-assets.mjs');
