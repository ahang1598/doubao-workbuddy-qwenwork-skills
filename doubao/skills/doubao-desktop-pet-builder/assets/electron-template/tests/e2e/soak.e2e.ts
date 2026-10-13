import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { launchPackaged, quitGracefully, snapshot, waitForWindows } from './helpers';

const execFileAsync = promisify(execFile);
const durationOption = process.argv.find((item) => item.startsWith('--duration-ms='));
const durationMs = Number(durationOption?.split('=')[1] || process.env.PET_SOAK_MS || 300_000);
if (!Number.isFinite(durationMs) || durationMs < 10_000) throw new Error('PET_SOAK_MS must be at least 10000');

async function main(): Promise<void> {
const userData = await mkdtemp(path.join(os.tmpdir(), 'desktop-pet-soak-'));
const application = await launchPackaged(userData);
const windows = await waitForWindows(application);
const interactions = await windows.pet.evaluate(() => window.petAPI!.interactions.list());
assert.ok(interactions.length > 0);
const rssSamples: number[] = [];
const startedAt = Date.now();
let iteration = 0;

async function rssKb(): Promise<number> {
  const { stdout } = await execFileAsync('ps', ['-o', 'rss=', '-p', String(application.child.pid)]);
  const value = Number(stdout.trim());
  if (!Number.isFinite(value)) throw new Error(`Invalid RSS sample: ${stdout}`);
  return value;
}

try {
  while (Date.now() - startedAt < durationMs) {
    const interaction = interactions[iteration % interactions.length]!;
    await windows.pet.evaluate((id) => window.petAPI!.interactions.trigger(id), interaction.id);
    await windows.pet.evaluate(async () => {
      await window.petAPI!.window.beginDrag();
      await window.petAPI!.window.updateDrag();
      await window.petAPI!.window.endDrag();
      await window.petAPI!.window.showDashboard();
    });
    const settings = await windows.dashboard.evaluate(() => window.petAPI!.settings.get());
    await windows.dashboard.evaluate(
      (edgeSnap) => window.petAPI!.settings.update({ edgeSnap }),
      !settings.edgeSnap,
    );
    await windows.dashboard.evaluate(() => window.petAPI!.window.hideDashboard());
    assert.equal((await snapshot(application)).tray, true);
    if (iteration % 10 === 0) rssSamples.push(await rssKb());
    iteration += 1;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  rssSamples.push(await rssKb());
  assert.ok(iteration > 0);
  assert.ok(rssSamples.length >= 2);
  const first = rssSamples.slice(0, Math.min(5, rssSamples.length));
  const last = rssSamples.slice(-Math.min(5, rssSamples.length));
  const average = (values: number[]) => values.reduce((sum, value) => sum + value, 0) / values.length;
  const growthKb = average(last) - average(first);
  assert.ok(growthKb < 128 * 1024, `sustained RSS growth is too high: ${Math.round(growthKb / 1024)} MiB`);
  await quitGracefully(application);
  const report = {
    passed: true,
    durationMs,
    iterations: iteration,
    rssSamplesKb: rssSamples,
    growthKb,
    completedAt: new Date().toISOString(),
  };
  await mkdir(path.resolve('qa'), { recursive: true });
  await writeFile(path.resolve('qa', 'soak-report.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(`Soak: PASS (${Math.round(durationMs / 1000)}s, ${iteration} cycles, RSS delta ${Math.round(growthKb / 1024)} MiB).`);
} finally {
  try {
    await application.close();
  } catch {
    // The normal path already closed the application.
  }
  await rm(userData, { recursive: true, force: true });
}
}

void main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
