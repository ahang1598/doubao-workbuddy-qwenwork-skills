import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const root = process.cwd();
const spec = JSON.parse(await readFile(path.join(root, 'pet-spec.json'), 'utf8'));
const assetDirectory = path.join(root, 'src', 'assets', 'pet');
const qaDirectory = path.join(root, 'qa');
await mkdir(qaDirectory, { recursive: true });
const issues = [];
const usedFiles = new Set();
usedFiles.add(spec.character.coreAsset.replaceAll('\\', '/'));
const triggerOwners = new Map();
const stateById = new Map(spec.states.map((state) => [state.id, state]));

for (const state of spec.states) {
  for (const frame of state.frames) usedFiles.add(frame.replaceAll('\\', '/'));
  if (!state.triggers.length) issues.push({ gate: 'reachability', state: state.id, message: 'state has no runtime trigger' });
  for (const trigger of state.triggers) {
    if (triggerOwners.has(trigger)) issues.push({ gate: 'reachability', state: state.id, message: `trigger ${trigger} is already owned by ${triggerOwners.get(trigger)}` });
    triggerOwners.set(trigger, state.id);
  }
}
for (const interaction of spec.experience.interactions) {
  const state = stateById.get(interaction.stateId);
  if (!state) issues.push({ gate: 'interaction', interaction: interaction.id, message: `missing state ${interaction.stateId}` });
  else if (state.frames.length < 2) issues.push({ gate: 'motion', interaction: interaction.id, message: 'interaction state needs at least two distinct frames' });
  if (triggerOwners.get(`interaction:${interaction.id}`) !== interaction.stateId) issues.push({ gate: 'interaction', interaction: interaction.id, message: 'menu action, trigger and stateId are not connected' });
}
const multiFrameStates = spec.states.filter((state) => state.frames.length >= 2).map((state) => state.id);
if (multiFrameStates.length < 4) issues.push({ gate: 'motion', message: 'fewer than four multi-frame states' });
if (!spec.motion.breathing.enabled && !spec.motion.squashStretch.enabled) issues.push({ gate: 'motion', message: 'both procedural breathing and squash/stretch are disabled' });
const files = (await readdir(assetDirectory, { recursive: true, withFileTypes: true }))
  .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith('.png'))
  .map((entry) => path.relative(assetDirectory, path.join(entry.parentPath, entry.name)).replaceAll('\\', '/'));
const unusedAssets = files.filter((file) => !usedFiles.has(file));
const missingAssets = [...usedFiles].filter((file) => !files.includes(file));
for (const file of unusedAssets) issues.push({ gate: 'asset-coverage', file, message: 'PNG exists but neither a runtime state nor coreAsset references it' });
for (const file of missingAssets) issues.push({ gate: 'asset-coverage', file, message: 'pet-spec references a missing PNG' });

const report = {
  generatedAt: new Date().toISOString(),
  passed: issues.length === 0,
  summary: { states: spec.states.length, triggers: triggerOwners.size, interactions: spec.experience.interactions.length, multiFrameStates, unusedAssets, missingAssets },
  issues,
};
await writeFile(path.join(qaDirectory, 'experience-report.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
console.log(`Experience QA: ${report.passed ? 'PASS' : 'FAIL'} (${spec.states.length} states, ${triggerOwners.size} triggers, ${multiFrameStates.length} multi-frame)`);
if (!report.passed) {
  for (const issue of issues) console.error(`- [${issue.gate}] ${issue.message}${issue.file ? `: ${issue.file}` : ''}`);
  process.exit(1);
}
