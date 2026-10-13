import process from 'node:process';

const options = Object.fromEntries(process.argv.slice(2).map((entry) => entry.replace(/^--/, '').split('=')));
const port = Number(options.port || 9223);
const endpoint = `http://127.0.0.1:${port}`;

async function waitForTargets(timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const targets = await (await fetch(`${endpoint}/json/list`)).json();
      const roles = new Set(targets.map((target) => {
        if (target.url.includes('/pet_window/')) return 'pet';
        if (target.url.includes('/dashboard_window/')) return 'dashboard';
        if (target.url.includes('/reminder_window/')) return 'reminder';
        return undefined;
      }).filter(Boolean));
      if (roles.size === 3) return targets;
    } catch {
      // The local debugging endpoint may need a moment after Electron starts.
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error('Dev smoke could not find pet, dashboard and reminder debugging targets.');
}

function targetForRole(targets, role) {
  const token = `/${role}_window/`;
  const target = targets.find((item) => item.url.includes(token));
  if (!target) throw new Error(`Missing ${role} renderer target.`);
  return target;
}

async function evaluate(target, expression) {
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.onopen = resolve;
    socket.onerror = reject;
  });
  const value = await new Promise((resolve, reject) => {
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.id !== 1) return;
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else if (message.result?.exceptionDetails) reject(new Error(JSON.stringify(message.result.exceptionDetails)));
      else resolve(message.result?.result?.value);
    };
    socket.send(JSON.stringify({
      id: 1,
      method: 'Runtime.evaluate',
      params: { expression, awaitPromise: true, returnByValue: true },
    }));
  });
  socket.close();
  return value;
}

const targets = await waitForTargets();
const pet = targetForRole(targets, 'pet');
const dashboard = targetForRole(targets, 'dashboard');
const reminder = targetForRole(targets, 'reminder');

for (const [role, target] of Object.entries({ pet, dashboard, reminder })) {
  const bootstrap = await evaluate(target, '({apiReady:Boolean(window.petAPI),documentReady:document.readyState==="complete"})');
  if (!bootstrap?.apiReady || !bootstrap?.documentReady) throw new Error(`${role} renderer did not finish bootstrap.`);
}

const interactions = await evaluate(pet, 'window.petAPI.interactions.list()');
if (!Array.isArray(interactions) || interactions.length < 1) throw new Error('No interactions are available.');
const interaction = await evaluate(pet, `window.petAPI.interactions.trigger(${JSON.stringify(interactions[0].id)})`);
if (!interaction?.stats || interaction.stats.todayInteractions < 1) throw new Error('Interaction did not update stats.');
await new Promise((resolve) => setTimeout(resolve, interactions[0].durationMs + 350));
const recoveredState = await evaluate(pet, 'document.getElementById("pet-container")?.dataset.state');
if (recoveredState !== 'idle') throw new Error(`Interaction did not recover to idle (current: ${recoveredState}).`);

const settingsBefore = await evaluate(dashboard, 'window.petAPI.settings.get()');
const invalidSettingsRejected = await evaluate(
  dashboard,
  'window.petAPI.settings.update({petScale:0.81,unknown:true}).then(()=>false,()=>true)',
);
if (!invalidSettingsRejected) throw new Error('Invalid settings patch was accepted.');
const toggled = await evaluate(
  dashboard,
  `window.petAPI.settings.update({edgeSnap:${JSON.stringify(!settingsBefore.edgeSnap)}})`,
);
if (toggled?.edgeSnap === settingsBefore.edgeSnap) throw new Error('Settings update did not apply.');
await evaluate(dashboard, `window.petAPI.settings.update({edgeSnap:${JSON.stringify(settingsBefore.edgeSnap)}})`);

const testReminder = await evaluate(
  reminder,
  'window.petAPI.reminders.save({text:"Doubao dev smoke",dueAt:new Date(Date.now()+300000).toISOString()})',
);
const reminders = await evaluate(dashboard, 'window.petAPI.reminders.list()');
if (!reminders.some((item) => item.id === testReminder.id)) throw new Error('Reminder was not persisted.');
const removed = await evaluate(dashboard, `window.petAPI.reminders.remove(${JSON.stringify(testReminder.id)})`);
if (!removed) throw new Error('Reminder cleanup failed.');

await evaluate(pet, 'window.petAPI.window.showDashboard()');
await evaluate(dashboard, 'window.petAPI.window.hideDashboard()');
await evaluate(pet, 'window.petAPI.window.showReminder()');
await evaluate(reminder, 'window.petAPI.window.hideReminder()');
await evaluate(pet, 'window.petAPI.window.beginDrag().then(()=>window.petAPI.window.updateDrag()).then(()=>window.petAPI.window.endDrag())');

console.log('Dev smoke: PASS (three renderers, interaction recovery, strict settings, reminder, windows, drag IPC).');
