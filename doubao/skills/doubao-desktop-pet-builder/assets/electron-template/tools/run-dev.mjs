import { spawn } from 'node:child_process';
import { access, appendFile, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { acquireActivityLock } from './activity-lock.mjs';
import { selectDevelopmentPorts } from './dev-ports.mjs';

const root = process.cwd();
const buildDirectory = path.join(root, '.build');
const readyFile = path.join(buildDirectory, 'runtime-ready.json');
const failureFile = path.join(buildDirectory, 'runtime-failed.json');
const statusFile = path.join(buildDirectory, 'dev-status.json');
const devLogFile = path.join(buildDirectory, 'dev.log');
const forgeCli = path.join(root, 'node_modules', '@electron-forge', 'cli', 'dist', 'electron-forge.js');
const preflight = path.join(root, 'tools', 'preflight.mjs');
const npmCli = process.env.npm_execpath || path.join(path.dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js');
const smokeMode = process.argv.includes('--smoke');
const smokeUserData = path.join(buildDirectory, 'dev-smoke-user-data');
const smokeClient = path.join(root, 'tools', 'dev-smoke-client.mjs');
const activityLock = await acquireActivityLock(buildDirectory, smokeMode ? 'dev-smoke' : 'dev-source-preview');
let child;
let shuttingDown = false;
let selectedPorts;

async function compatibleForgeNode() {
  if (Number(process.versions.node.split('.')[0]) < 25) return process.execPath;
  const candidates = [
    process.env.PET_BUILD_NODE,
    process.env.HOME ? path.join(process.env.HOME, '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'bin', 'node') : undefined,
    '/opt/homebrew/bin/node',
    '/usr/local/bin/node',
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // Continue looking for a Node release supported by Electron Forge.
    }
  }
  throw new Error('Electron development requires Node 24 or earlier. Set PET_BUILD_NODE to a compatible Node executable.');
}

async function status(stage, extra = {}) {
  await writeFile(statusFile, `${JSON.stringify({
    mode: smokeMode ? 'source-dev-smoke' : 'source-dev',
    stage,
    pid: process.pid,
    packaged: false,
    updatedAt: new Date().toISOString(),
    ...(selectedPorts ? { ports: selectedPorts } : {}),
    ...extra,
  }, null, 2)}\n`, 'utf8');
}

async function run(command, args) {
  const processChild = spawn(command, args, {
    cwd: root,
    stdio: 'inherit',
    shell: false,
    windowsHide: true,
  });
  const code = await new Promise((resolve, reject) => {
    processChild.once('error', reject);
    processChild.once('exit', (value) => resolve(value ?? 1));
  });
  if (code !== 0) throw new Error(`${path.basename(command)} ${args.join(' ')} exited with code ${code}`);
}

async function readJsonIfExists(file) {
  try {
    return JSON.parse(await readFile(file, 'utf8'));
  } catch (error) {
    if (error?.code === 'ENOENT') return undefined;
    throw error;
  }
}

function validReadyReport(report) {
  return report?.status === 'ready'
    && report.naturalWidth > 0
    && report.naturalHeight > 0
    && report.assetCount === report.expectedAssetCount
    && report.petVisible === true
    && report.ipcReady === true
    && report.renderers?.pet === true
    && report.renderers?.dashboard === true
    && report.renderers?.reminder === true;
}

async function waitForRuntimeReady(timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const failure = await readJsonIfExists(failureFile);
    if (failure) throw new Error(`Development preview failed at ${failure.event}: ${failure.message}`);
    const ready = await readJsonIfExists(readyFile);
    if (ready) {
      if (!validReadyReport(ready)) throw new Error(`Invalid runtime ready report: ${JSON.stringify(ready)}`);
      return ready;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Source development preview did not prove three ready renderers within ${Math.round(timeoutMs / 1000)} seconds.`);
}

async function terminateChild() {
  if (!child?.pid) return;
  if (process.platform === 'win32') {
    const killer = spawn('taskkill.exe', ['/pid', String(child.pid), '/t', '/f'], {
      windowsHide: true,
      stdio: 'ignore',
    });
    await new Promise((resolve) => killer.once('close', resolve));
  } else {
    try {
      process.kill(-child.pid, 'SIGTERM');
    } catch {
      child.kill('SIGTERM');
    }
  }
}

async function requestShutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  await status('stopping', { signal });
  await terminateChild();
}

process.once('SIGINT', () => { void requestShutdown('SIGINT'); });
process.once('SIGTERM', () => { void requestShutdown('SIGTERM'); });

try {
  await mkdir(buildDirectory, { recursive: true });
  await rm(readyFile, { force: true });
  await rm(failureFile, { force: true });
  await rm(devLogFile, { force: true });
  if (smokeMode) await rm(smokeUserData, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 });
  selectedPorts = await selectDevelopmentPorts(process.env, smokeMode);
  await status('ports-selected', { ports: selectedPorts });
  const forgeNode = await compatibleForgeNode();
  await status('preflight');
  await run(forgeNode, [preflight]);
  await status('check');
  await run(process.execPath, [npmCli, 'run', 'check']);
  await status('launch-source-dev');

  const forgeArgs = [forgeCli, 'start'];
  if (process.env.PET_VERBOSE_LOGGING === '1') forgeArgs.push('--enable-logging');
  if (smokeMode) forgeArgs.push('--', `--remote-debugging-port=${selectedPorts.smoke}`);
  child = spawn(forgeNode, forgeArgs, {
    cwd: root,
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
    windowsHide: false,
    detached: process.platform !== 'win32',
    env: {
      ...process.env,
      PET_DEV_MODE: '1',
      PET_DEV_PORT: String(selectedPorts.dev),
      PET_LOGGER_PORT: String(selectedPorts.logger),
      ...(smokeMode ? {
        PET_SMOKE_MODE: '1',
        PET_E2E_USER_DATA: smokeUserData,
        PET_SMOKE_PORT: String(selectedPorts.smoke),
      } : {}),
    },
  });
  const drainLog = (chunk) => {
    void appendFile(devLogFile, Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)))
      .catch(() => {});
  };
  child.stdout?.on('data', drainLog);
  child.stderr?.on('data', drainLog);
  const childExit = new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', (code, signal) => resolve({ code: code ?? 1, signal }));
  });
  const first = await Promise.race([
    waitForRuntimeReady().then((report) => ({ kind: 'ready', report })),
    childExit.then((exit) => ({ kind: 'exit', exit })),
  ]);
  if (first.kind === 'exit') {
    throw new Error(`Electron Forge exited before runtime became ready (code ${first.exit.code}, signal ${first.exit.signal ?? 'none'}).`);
  }

  await status('ready', first.report);
  if (smokeMode) {
    await status('smoke');
    await run(process.execPath, [smokeClient, `--port=${selectedPorts.smoke}`]);
    await status('smoke-passed', first.report);
    console.log('DEV_SMOKE_PASS isolatedUserData=true debugPortClosedOnExit=true');
    shuttingDown = true;
    await terminateChild();
    await childExit;
  } else {
    console.log(
      `DEV_PREVIEW_READY mode=source-dev renderers=pet,dashboard,reminder ipc=true `
      + `assets=${first.report.assetCount} image=${first.report.naturalWidth}x${first.report.naturalHeight} `
      + `state=${first.report.stateId} devPort=${selectedPorts.dev} loggerPort=${selectedPorts.logger}`,
    );
    const exit = await childExit;
    if (!shuttingDown && exit.code !== 0) {
      throw new Error(`Electron Forge development process exited with code ${exit.code}.`);
    }
    await status('stopped', { code: exit.code, signal: exit.signal });
  }
} catch (error) {
  await status('failed', { error: error instanceof Error ? error.message : String(error) });
  await terminateChild();
  throw error;
} finally {
  if (smokeMode) await rm(smokeUserData, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 });
  await activityLock.release();
}
