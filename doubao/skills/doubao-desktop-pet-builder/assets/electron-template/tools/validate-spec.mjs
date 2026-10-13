import { readFile } from 'node:fs/promises';

const specText = await readFile(new URL('../pet-spec.json', import.meta.url), 'utf8');
const packageText = await readFile(new URL('../package.json', import.meta.url), 'utf8');
const spec = JSON.parse(specText);
const packageJson = JSON.parse(packageText);
const errors = [];
const knownTriggers = new Set([
  'app:start', 'ambient:idle', 'ambient:blink', 'ambient:random', 'pointer:tap', 'window:drag', 'window:edge-snap',
  'reminder:due', 'typing:activity', 'file:drop', 'file:drop-success', 'file:drop-fail', 'movement:left', 'movement:right',
]);
if (spec.schemaVersion !== 5) errors.push('schemaVersion must equal 5');
const mojibakePattern = /\ufffd|锛|鈥|灏忛噾|妗屽疇|鍠傚皬|鎽告懜/u;
if (mojibakePattern.test(specText) || mojibakePattern.test(packageText)) errors.push('probable UTF-8/GBK mojibake; restore the UTF-8 source files');
if (!/^[A-Za-z][A-Za-z0-9]*(\.[A-Za-z0-9-]+)+$/.test(spec.app?.appId ?? '')) errors.push('app.appId must be a reverse-domain identifier');
if (packageJson.productName !== spec.app?.name) errors.push('package.productName must match app.name');
if (packageJson.version !== spec.app?.version) errors.push('package.version must match app.version');
if (spec.assetPipeline?.backgroundMode !== 'semantic-cutout') errors.push('assetPipeline.backgroundMode must be semantic-cutout');
if (!['auto', 'apple-vision', 'rembg'].includes(spec.assetPipeline?.segmentationBackend)) errors.push('assetPipeline.segmentationBackend must be auto, apple-vision or rembg');
if (!['auto', 'illustration', 'photo'].includes(spec.assetPipeline?.subjectKind)) errors.push('assetPipeline.subjectKind must be auto, illustration or photo');
if (!['transparent-grid', 'solid-chroma'].includes(spec.assetPipeline?.generationBackground)) errors.push('assetPipeline.generationBackground must be transparent-grid or solid-chroma');
if (!Number.isInteger(spec.assetPipeline?.backgroundTolerance) || spec.assetPipeline.backgroundTolerance < 12 || spec.assetPipeline.backgroundTolerance > 48) errors.push('assetPipeline.backgroundTolerance must be 12-48');
if (!Number.isInteger(spec.assetPipeline?.edgeFeather) || spec.assetPipeline.edgeFeather < 4 || spec.assetPipeline.edgeFeather > 24) errors.push('assetPipeline.edgeFeather must be 4-24');
if (!Number.isInteger(spec.assetPipeline?.safeMargin) || spec.assetPipeline.safeMargin < 16 || spec.assetPipeline.safeMargin > 64) errors.push('assetPipeline.safeMargin must be 16-64');
if (typeof spec.assetPipeline?.targetOccupancy !== 'number' || spec.assetPipeline.targetOccupancy < 0.65 || spec.assetPipeline.targetOccupancy > 0.82) errors.push('assetPipeline.targetOccupancy must be 0.65-0.82');
if (!Number.isInteger(spec.experience?.petSizing?.baseWindowPx) || spec.experience.petSizing.baseWindowPx < 180 || spec.experience.petSizing.baseWindowPx > 260) errors.push('experience.petSizing.baseWindowPx must be 180-260');
if (![0.65, 0.8, 1, 1.2].includes(spec.experience?.petSizing?.defaultScale)) errors.push('experience.petSizing.defaultScale must be one of 0.65, 0.8, 1, 1.2');
if (spec.features?.transparentWindow !== true) errors.push('transparentWindow must be true');
if (spec.build?.unsigned !== true) errors.push('build.unsigned must explicitly be true');
if (spec.build?.windows?.arch !== 'x64') errors.push('Windows architecture must be x64');
if (!Number.isInteger(spec.build?.timeoutMinutes) || spec.build.timeoutMinutes < 5 || spec.build.timeoutMinutes > 60) errors.push('build timeout must be 5-60 minutes');
if (spec.storage?.userData !== 'app-user-data' || spec.storage?.filePocket !== 'documents-app-name') errors.push('storage paths must use cross-platform policies');

const interactions = new Map((spec.experience?.interactions ?? []).map((interaction) => [interaction.id, interaction]));
const states = new Map();
const triggers = new Map();
const frameOwners = new Map();
for (const state of spec.states ?? []) {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(state.id ?? '')) errors.push(`invalid state id: ${state.id}`);
  if (states.has(state.id)) errors.push(`duplicate state id: ${state.id}`);
  states.set(state.id, state);
  if (!Array.isArray(state.frames) || state.frames.length < 1) errors.push(`state has no frames: ${state.id}`);
  for (const frame of state.frames ?? []) {
    if (typeof frame !== 'string' || /^[A-Za-z]:|^[/\\]|(?:^|[/\\])\.\.(?:[/\\]|$)/.test(frame)) errors.push(`unsafe frame path: ${frame}`);
    if (frameOwners.has(frame)) errors.push(`frame ${frame} belongs to both ${frameOwners.get(frame)} and ${state.id}`);
    else frameOwners.set(frame, state.id);
  }
  if (!Array.isArray(state.triggers) || !state.triggers.length) errors.push(`state has no runtime trigger: ${state.id}`);
  for (const trigger of state.triggers ?? []) {
    if (!knownTriggers.has(trigger) && !(trigger.startsWith('interaction:') && interactions.has(trigger.slice(12)))) errors.push(`unknown trigger ${trigger} on ${state.id}`);
    if (triggers.has(trigger)) errors.push(`trigger ${trigger} maps to both ${triggers.get(trigger)} and ${state.id}`);
    triggers.set(trigger, state.id);
  }
}
if (!states.has('idle')) errors.push('state machine requires an idle state');
for (const trigger of ['app:start', 'ambient:idle', 'ambient:blink', 'pointer:tap']) if (!triggers.has(trigger)) errors.push(`missing base trigger: ${trigger}`);
const conditional = {
  reminders: ['reminder:due'],
  edgeSnap: ['window:edge-snap'],
  typingReaction: ['typing:activity'],
  filePocket: ['file:drop', 'file:drop-success', 'file:drop-fail'],
  autonomousMovement: ['movement:left', 'movement:right'],
};
for (const [feature, required] of Object.entries(conditional)) {
  for (const trigger of required) {
    if (spec.features?.[feature] && !triggers.has(trigger)) errors.push(`${feature} is enabled but ${trigger} is not implemented`);
    if (!spec.features?.[feature] && triggers.has(trigger)) errors.push(`${trigger} exists although ${feature} is disabled`);
  }
}
if (spec.features?.interactions && interactions.size < 2) errors.push('enabled interactions require at least two character-specific actions');
for (const [id, interaction] of interactions) {
  if (typeof interaction.emoji !== 'string' || interaction.emoji.length < 1 || interaction.emoji.length > 8) errors.push(`interaction ${id} needs a short emoji`);
  const state = states.get(interaction.stateId);
  if (!state) errors.push(`interaction ${id} references missing state ${interaction.stateId}`);
  if (!triggers.has(`interaction:${id}`)) errors.push(`interaction ${id} has no runtime trigger`);
  if (state && (state.frames.length < 5 || state.frames.length > 6)) errors.push(`interaction state ${state.id} must have 5-6 frames`);
  if (state && interaction.durationMs < state.frames.length * state.frameDurationMs) errors.push(`interaction ${id} duration must cover one full animation cycle`);
}
const blink = states.get(triggers.get('ambient:blink'));
if (blink && blink.frames.length !== 5) errors.push('blink must have exactly five frames');
const idle = states.get('idle');
if (idle && (idle.frames.length < 4 || idle.frames.length > 6)) errors.push('idle must have 4-6 frames');
for (const trigger of ['pointer:tap', 'reminder:due', 'window:edge-snap', 'ambient:random']) {
  const state = states.get(triggers.get(trigger));
  if (state && (state.frames.length < 5 || state.frames.length > 6)) errors.push(`${trigger} state ${state.id} must have 5-6 frames`);
}
for (const trigger of ['movement:left', 'movement:right']) {
  const state = states.get(triggers.get(trigger));
  if (state && (state.frames.length < 6 || state.frames.length > 8)) errors.push(`${trigger} state ${state.id} must have 6-8 frames`);
}
if ([...states.values()].some((state) => state.frames.includes(spec.character?.coreAsset))) errors.push('character.coreAsset must be an independent identity master, not a runtime animation frame');

if (errors.length) {
  console.error(`Invalid pet-spec.json:\n${errors.map((error) => `- ${error}`).join('\n')}`);
  process.exit(1);
}
console.log(`Valid pet-spec.json v5: ${states.size} states, ${triggers.size} triggers, ${interactions.size} interactions.`);
