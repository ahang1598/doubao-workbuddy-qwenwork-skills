import { copyFile, cp, lstat, mkdir, readFile, readlink, readdir, rm, stat, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';

const execFileAsync = promisify(execFile);
const root = process.cwd();
const options = Object.fromEntries(process.argv.slice(2).map((entry) => entry.replace(/^--/, '').split('=')));
const mode = options.mode;
const platform = options.platform;
const arch = options.arch;
if (!['package', 'make'].includes(mode) || !platform || !arch) throw new Error('Usage: collect-release.mjs --mode=package|make --platform=... --arch=... --out=...');
const sourceOut = options.out ? path.resolve(options.out) : path.join(root, 'out');
const release = path.resolve(root, 'release');
if (path.dirname(release) !== path.resolve(root)) throw new Error('Refusing unsafe release path');
await rm(release, { recursive: true, force: true });
await mkdir(release, { recursive: true });
const packageJson = JSON.parse(await readFile(path.join(root, 'package.json'), 'utf8'));
const spec = JSON.parse(await readFile(path.join(root, 'pet-spec.json'), 'utf8'));
const artifacts = [];

async function hashedRecord(file, relativeFile, kind) {
  const bytes = await readFile(file);
  return { file: relativeFile.replaceAll('\\', '/'), kind, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
}

async function assertPortableSymlinks(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    const info = await lstat(full);
    if (info.isSymbolicLink()) {
      const target = await readlink(full);
      if (path.isAbsolute(target)) throw new Error(`Release bundle contains an absolute symlink: ${path.relative(directory, full)} -> ${target}`);
    } else if (info.isDirectory()) {
      await assertPortableSymlinks(full);
    }
  }
}

if (mode === 'package') {
  const entries = await readdir(sourceOut, { withFileTypes: true });
  const suffix = `-${platform}-${arch}`;
  const packageDirectory = entries.find((entry) => entry.isDirectory() && entry.name.endsWith(suffix));
  if (!packageDirectory) throw new Error(`No packaged app ending in ${suffix} found under out.`);
  const destinationName = `${spec.app.name}-${platform}-${arch}-ready-to-run`;
  const destination = path.join(release, destinationName);
  await cp(path.join(sourceOut, packageDirectory.name), destination, { recursive: true, verbatimSymlinks: true });
  if (platform === 'darwin') {
    const appBundle = path.join(destination, `${spec.app.name}.app`);
    await assertPortableSymlinks(appBundle);
    await execFileAsync('codesign', ['--force', '--deep', '--sign', '-', appBundle]);
    await execFileAsync('codesign', ['--verify', '--deep', '--strict', appBundle]);
  }
  const executable = platform === 'win32'
    ? path.join(destination, `${spec.app.name}.exe`)
    : path.join(destination, `${spec.app.name}.app`, 'Contents', 'MacOS', spec.app.name);
  await stat(executable);
  artifacts.push(await hashedRecord(executable, path.relative(release, executable), 'ready-to-run'));
} else {
  const accepted = new Set(['.exe', '.dmg', '.zip']);
  const found = [];
  async function walk(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const full = path.join(directory, entry.name);
      if (entry.isDirectory()) await walk(full);
      else if (accepted.has(path.extname(entry.name).toLowerCase())) found.push(full);
    }
  }
  await walk(path.join(sourceOut, 'make'));
  if (!found.length) throw new Error('No installer or portable package found under out/make. Manual ZIP fallback is forbidden.');
  for (const source of found) {
    let destination = path.join(release, path.basename(source));
    for (let index = 1; await stat(destination).then(() => true, () => false); index += 1) {
      const parsed = path.parse(source);
      destination = path.join(release, `${parsed.name}-${index}${parsed.ext}`);
    }
    await copyFile(source, destination);
    artifacts.push(await hashedRecord(destination, path.basename(destination), path.extname(destination).slice(1)));
  }
}

const manifest = { app: spec.app.name || packageJson.productName || packageJson.name, version: spec.app.version || packageJson.version, platform, arch, mode, unsigned: true, artifacts };
await writeFile(path.join(release, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
console.log(`Collected ${artifacts.length} verified artifact(s) in ${release}`);
