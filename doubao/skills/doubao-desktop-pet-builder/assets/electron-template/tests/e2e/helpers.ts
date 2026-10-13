import { chromium, type Browser, type Page } from 'playwright';
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { createServer } from 'node:net';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

export interface AppSnapshot {
  tray: boolean;
  roles: Array<{ role: 'pet' | 'reminder' | 'dashboard'; visible: boolean; destroyed: boolean }>;
  quitting: boolean;
}

export interface PackagedApplication {
  browser: Browser;
  child: ChildProcessWithoutNullStreams;
  close: () => Promise<void>;
}

export async function packagedExecutable(): Promise<string> {
  const releaseDirectory = path.resolve('release');
  const manifest = JSON.parse(await readFile(path.join(releaseDirectory, 'manifest.json'), 'utf8')) as {
    artifacts: Array<{ file: string; kind: string }>;
  };
  const artifact = manifest.artifacts.find((item) => item.kind === 'ready-to-run');
  if (!artifact) throw new Error('release/manifest.json has no ready-to-run artifact');
  return path.join(releaseDirectory, artifact.file);
}

async function availablePort(): Promise<number> {
  const server = createServer();
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  const port = typeof address === 'object' && address ? address.port : 0;
  await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  if (!port) throw new Error('Could not reserve a local debugging port');
  return port;
}

export async function launchPackaged(userData: string): Promise<PackagedApplication> {
  const port = await availablePort();
  const child = spawn(await packagedExecutable(), [`--remote-debugging-port=${port}`], {
    env: {
      ...process.env,
      PET_E2E: '1',
      PET_PREVIEW_MODE: '1',
      PET_E2E_USER_DATA: userData,
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  child.stdin.end();
  let launchOutput = '';
  child.stdout.on('data', (chunk) => { launchOutput += String(chunk); });
  child.stderr.on('data', (chunk) => { launchOutput += String(chunk); });
  const deadline = Date.now() + 30_000;
  let browser: Browser | undefined;
  while (Date.now() < deadline && child.exitCode === null) {
    try {
      browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`, { timeout: 1_000 });
      break;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  if (!browser) {
    child.kill('SIGTERM');
    throw new Error(`Packaged app did not expose its debugging endpoint. ${launchOutput.slice(-2000)}`);
  }
  await new Promise((resolve) => setTimeout(resolve, 750));
  if (child.exitCode !== null) {
    await browser.close().catch(() => {});
    throw new Error(`Packaged app exited during startup with code ${child.exitCode}. ${launchOutput.slice(-2000)}`);
  }
  return {
    browser,
    child,
    close: async () => {
      await browser?.close().catch(() => {});
      if (child.exitCode === null) {
        child.kill('SIGTERM');
        await Promise.race([
          new Promise<void>((resolve) => child.once('exit', () => resolve())),
          new Promise<void>((resolve) => setTimeout(resolve, 5_000)),
        ]);
      }
    },
  };
}

function pages(application: PackagedApplication): Page[] {
  return application.browser.contexts().flatMap((context) => context.pages());
}

export async function waitForWindows(application: PackagedApplication): Promise<Record<'pet' | 'dashboard' | 'reminder', Page>> {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    const currentPages = pages(application);
    const pet = currentPages.find((page) => page.url().includes('/pet_window/'));
    const dashboard = currentPages.find((page) => page.url().includes('/dashboard_window/'));
    const reminder = currentPages.find((page) => page.url().includes('/reminder_window/'));
    if (pet && dashboard && reminder) {
      await Promise.all([pet.waitForLoadState(), dashboard.waitForLoadState(), reminder.waitForLoadState()]);
      return { pet, dashboard, reminder };
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('Packaged app did not create pet, dashboard and reminder windows');
}

export async function snapshot(application: PackagedApplication): Promise<AppSnapshot> {
  const { pet } = await waitForWindows(application);
  return pet.evaluate(() => {
    if (!window.__petE2E) throw new Error('E2E diagnostics are unavailable');
    return window.__petE2E.snapshot();
  });
}

export async function quitGracefully(application: PackagedApplication): Promise<void> {
  const { pet } = await waitForWindows(application);
  const exited = new Promise<void>((resolve) => application.child.once('exit', () => resolve()));
  await pet.evaluate(() => {
    if (!window.__petE2E) throw new Error('E2E diagnostics are unavailable');
    return window.__petE2E.quit();
  });
  await Promise.race([
    exited,
    new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Application did not quit normally')), 10_000)),
  ]);
}
