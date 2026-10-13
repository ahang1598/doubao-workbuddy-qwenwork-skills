import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { launchPackaged, packagedExecutable, quitGracefully, snapshot, waitForWindows } from './helpers';

async function main(): Promise<void> {
const userData = await mkdtemp(path.join(os.tmpdir(), 'desktop-pet-e2e-'));
let application = await launchPackaged(userData);

try {
  let windows = await waitForWindows(application);
  const initial = await snapshot(application);
  assert.equal(initial.tray, true, 'tray should be created');
  assert.deepEqual(initial.roles.map((item) => item.role).sort(), ['dashboard', 'pet', 'reminder']);
  assert.equal(initial.roles.every((item) => !item.destroyed), true);

  await windows.pet.evaluate(() => {
    const container = document.getElementById('pet-container');
    if (!container) throw new Error('pet container is missing');
    const eventLog: string[] = [];
    for (const eventName of ['click', 'pointerdown', 'pointermove', 'pointerup']) {
      container.addEventListener(eventName, () => eventLog.push(eventName));
    }
    container.addEventListener('contextmenu', (event) => {
      eventLog.push(event.type);
      event.preventDefault();
      event.stopImmediatePropagation();
    }, { capture: true });
    (window as typeof window & { __petMouseEvents?: string[] }).__petMouseEvents = eventLog;
  });
  const petBounds = await windows.pet.locator('#pet-container').boundingBox();
  assert.ok(petBounds, 'pet container should have clickable bounds');
  const center = { x: petBounds.x + petBounds.width / 2, y: petBounds.y + petBounds.height / 2 };
  await windows.pet.mouse.click(center.x, center.y);
  await windows.pet.waitForFunction(
    () => (window as typeof window & { __petMouseEvents?: string[] }).__petMouseEvents?.includes('click') === true,
  );
  assert.notEqual(
    await windows.pet.evaluate(() => document.getElementById('pet-container')?.dataset.state),
    'idle',
    'a real left click should trigger the tap state',
  );
  await windows.pet.mouse.click(center.x, center.y, { button: 'right' });
  await windows.pet.mouse.move(center.x, center.y);
  await windows.pet.mouse.down();
  await windows.pet.mouse.move(center.x + 24, center.y + 16, { steps: 4 });
  await windows.pet.mouse.up();
  const mouseEvents = await windows.pet.evaluate(
    () => (window as typeof window & { __petMouseEvents?: string[] }).__petMouseEvents ?? [],
  );
  for (const eventName of ['contextmenu', 'pointerdown', 'pointermove', 'pointerup']) {
    assert.ok(mouseEvents.includes(eventName), `real mouse test did not receive ${eventName}`);
  }
  await windows.pet.waitForFunction(
    () => document.getElementById('pet-container')?.dataset.state === 'idle',
    undefined,
    { timeout: 5_000 },
  );

  const interactions = await windows.pet.evaluate(() => window.petAPI!.interactions.list());
  assert.ok(interactions.length > 0);
  for (const interaction of interactions) {
    await windows.pet.evaluate((id) => window.petAPI!.interactions.trigger(id), interaction.id);
    await windows.pet.waitForFunction(
      (stateId) => document.getElementById('pet-container')?.dataset.state === stateId,
      interaction.stateId,
    );
    await windows.pet.waitForFunction(
      () => document.getElementById('pet-container')?.dataset.state === 'idle',
      undefined,
      { timeout: interaction.durationMs + 2_000 },
    );
  }

  const originalSettings = await windows.dashboard.evaluate(() => window.petAPI!.settings.get());
  const expectedAlwaysOnTop = !originalSettings.alwaysOnTop;
  await windows.dashboard.evaluate(
    (alwaysOnTop) => window.petAPI!.settings.update({ alwaysOnTop }),
    expectedAlwaysOnTop,
  );
  const savedReminder = await windows.reminder.evaluate(() => window.petAPI!.reminders.save({
    text: 'E2E reminder',
    dueAt: new Date(Date.now() + 300_000).toISOString(),
  }));
  assert.equal(
    (await windows.reminder.evaluate(() => window.petAPI!.reminders.list())).some((item) => item.id === savedReminder.id),
    true,
    'saved reminder should be visible immediately',
  );

  await windows.pet.evaluate(async () => {
    await window.petAPI!.window.showDashboard();
    await window.petAPI!.window.hidePet();
  });
  await windows.dashboard.evaluate(() => window.petAPI!.window.hideDashboard());
  await windows.reminder.evaluate(() => window.petAPI!.window.hideReminder());
  const hidden = await snapshot(application);
  assert.equal(hidden.roles.every((item) => !item.visible), true, 'all windows should be hideable while tray keeps app alive');

  const second = spawn(await packagedExecutable(), [], {
    env: { ...process.env, PET_E2E_USER_DATA: userData },
    stdio: 'ignore',
  });
  const secondExit = await Promise.race([
    new Promise<number | null>((resolve, reject) => {
      second.once('error', reject);
      second.once('exit', resolve);
    }),
    new Promise<never>((_, reject) => setTimeout(() => reject(new Error('second instance did not exit')), 10_000)),
  ]);
  assert.equal(secondExit, 0);
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal((await snapshot(application)).roles.find((item) => item.role === 'pet')?.visible, true);

  await quitGracefully(application);
  const settingsFile = JSON.parse(await readFile(path.join(userData, 'settings.json'), 'utf8'));
  assert.equal(settingsFile.alwaysOnTop, expectedAlwaysOnTop);
  await readFile(path.join(userData, 'pet-stats.json'), 'utf8');
  assert.equal(
    JSON.parse(await readFile(path.join(userData, 'reminders.json'), 'utf8')).some((item: { id: string }) => item.id === savedReminder.id),
    true,
    'reminder should be persisted during normal exit',
  );
  assert.equal((await readdir(userData)).some((name) => name.includes('runtime-failed') || name.endsWith('.tmp')), false);

  application = await launchPackaged(userData);
  windows = await waitForWindows(application);
  assert.equal(
    (await windows.dashboard.evaluate(() => window.petAPI!.settings.get())).alwaysOnTop,
    expectedAlwaysOnTop,
    'settings should persist across a normal restart',
  );
  assert.equal(
    (await windows.reminder.evaluate(() => window.petAPI!.reminders.list())).some((item) => item.id === savedReminder.id),
    true,
    'reminder should survive a normal restart',
  );
  assert.equal(
    await windows.dashboard.evaluate((id) => window.petAPI!.reminders.remove(id), savedReminder.id),
    true,
    'saved reminder should be removable',
  );
  await quitGracefully(application);
  console.log('E2E: PASS (startup, real mouse events, three windows, tray, interactions, settings/reminder persistence, hide/show, exit, single instance).');
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
