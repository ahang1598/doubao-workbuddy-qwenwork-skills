import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import process from 'node:process';
import { isPortAvailable, parsePort } from './dev-ports.mjs';

const root = process.cwd();
const buildDirectory = path.join(root, '.build');
const checks = [];

function record(name, ok, details) {
  checks.push({ name, ok, details });
}

const nodeMajor = Number(process.versions.node.split('.')[0]);
record('node-version', nodeMajor < 25 || Boolean(process.env.PET_BUILD_NODE), {
  current: process.versions.node,
  compatibleForgeNode: nodeMajor < 25 ? process.execPath : process.env.PET_BUILD_NODE,
  repair: nodeMajor < 25 || process.env.PET_BUILD_NODE
    ? undefined
    : 'Set PET_BUILD_NODE to a Node 24-or-earlier executable.',
});

let provenance;
try {
  provenance = JSON.parse(await readFile(path.join(root, '.doubao-pet-builder.json'), 'utf8'));
  record('builder-provenance', provenance.templateContractVersion === 5, {
    templateContractVersion: provenance.templateContractVersion,
    repair: provenance.templateContractVersion === 5
      ? undefined
      : 'Create an isolated v2 scaffold; the semantic cutout contract is not a hash-only migration.',
  });
} catch (error) {
  record('builder-provenance', false, { error: error instanceof Error ? error.message : String(error) });
}

if (provenance?.criticalFileHashes) {
  const drift = [];
  for (const [relative, expected] of Object.entries(provenance.criticalFileHashes)) {
    try {
      const actual = createHash('sha256').update(await readFile(path.join(root, relative))).digest('hex');
      if (actual !== expected) drift.push({ relative, expected, actual });
    } catch (error) {
      drift.push({ relative, expected, error: error instanceof Error ? error.message : String(error) });
    }
  }
  record('template-hashes', drift.length === 0, { drift });
}

try {
  const electronPackage = JSON.parse(await readFile(path.join(root, 'node_modules', 'electron', 'package.json'), 'utf8'));
  const executable = process.platform === 'darwin'
    ? path.join('Electron.app', 'Contents', 'MacOS', 'Electron')
    : process.platform === 'win32' ? 'electron.exe' : 'electron';
  const runtime = path.join(root, 'node_modules', 'electron', 'dist', executable);
  await access(runtime);
  const installedVersion = (await readFile(path.join(root, 'node_modules', 'electron', 'dist', 'version'), 'utf8')).trim().replace(/^v/, '');
  record('electron-runtime', installedVersion === electronPackage.version, {
    packageVersion: electronPackage.version,
    installedVersion,
    executable: runtime,
  });
} catch (error) {
  record('electron-runtime', false, {
    error: error instanceof Error ? error.message : String(error),
    repair: 'Run npm ci exactly once, then npm run preflight.',
  });
}

for (const [name, value, fallback] of [
  ['PET_DEV_PORT', process.env.PET_DEV_PORT, 3000],
  ['PET_LOGGER_PORT', process.env.PET_LOGGER_PORT, 9000],
  ['PET_SMOKE_PORT', process.env.PET_SMOKE_PORT, 9223],
]) {
  try {
    const port = parsePort(value || fallback, name);
    const available = await isPortAvailable(port);
    const explicit = Boolean(value);
    record(`port-${name.toLowerCase()}`, available || !explicit, {
      port,
      explicit,
      available,
      willAutoSelect: !explicit && !available,
      repair: explicit && !available ? `Choose another ${name} value or unset it for automatic selection.` : undefined,
    });
  } catch (error) {
    record(`port-${name.toLowerCase()}`, false, { error: error instanceof Error ? error.message : String(error) });
  }
}

try {
  const report = JSON.parse(await readFile(path.join(root, 'qa', 'assets-report.json'), 'utf8'));
  const complete = (report.scope ?? 'all') === 'all';
  record('asset-qa-report', report.passed === true && complete, {
    passed: report.passed,
    scope: report.scope ?? 'all',
    repair: report.passed && complete
      ? undefined
      : complete
        ? 'Run npm run inspect:assets and follow the per-frame diagnostic codes.'
        : 'State-level QA passed, but run npm run qa:assets for complete-project evidence.',
  });
} catch {
  record('asset-qa-report', false, { repair: 'Run npm run inspect:assets before development preview.' });
}

const report = {
  generatedAt: new Date().toISOString(),
  platform: process.platform,
  arch: process.arch,
  passed: checks.every((check) => check.ok),
  checks,
};
await mkdir(buildDirectory, { recursive: true });
await writeFile(path.join(buildDirectory, 'doctor-report.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
console.log(`Desktop pet doctor: ${report.passed ? 'PASS' : 'ATTENTION'} (${checks.filter((check) => !check.ok).length} issue(s))`);
for (const check of checks.filter((item) => !item.ok)) console.error(`- ${check.name}: ${JSON.stringify(check.details)}`);
if (!report.passed) process.exit(1);
