import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const root = process.cwd();
const qaDirectory = path.join(root, 'qa');
const spec = JSON.parse(await readFile(path.join(root, 'pet-spec.json'), 'utf8'));
const files = {
  main: await readFile(path.join(root, 'src', 'main.ts'), 'utf8'),
  dashboard: await readFile(path.join(root, 'src', 'renderer', 'dashboard', 'index.css'), 'utf8'),
  reminder: await readFile(path.join(root, 'src', 'renderer', 'reminder', 'index.css'), 'utf8'),
  pet: await readFile(path.join(root, 'src', 'renderer', 'pet', 'index.css'), 'utf8'),
};
const checks = [];
const add = (id, passed, detail) => checks.push({ id, passed, detail });

for (const view of ['dashboard', 'reminder', 'pet']) {
  add(`${view}-transparent-root`, /html, body\s*\{[^}]*overflow:\s*hidden[^}]*background:\s*transparent\s*!important/s.test(files[view]), `${view} html/body must be transparent and page-level overflow hidden`);
}
add('dashboard-hidden-scrollbar', /scrollbar-width:\s*none/.test(files.dashboard) && /::-webkit-scrollbar\s*\{[^}]*width:\s*0[^}]*height:\s*0/s.test(files.dashboard), 'dashboard internal scrolling must not expose a system scrollbar');
add('reminder-hidden-scrollbar', /scrollbar-width:\s*none/.test(files.reminder) && /::-webkit-scrollbar\s*\{[^}]*width:\s*0[^}]*height:\s*0/s.test(files.reminder), 'reminder internal scrolling must not expose a system scrollbar');
add('native-control-reset', /appearance:\s*none/.test(files.dashboard) && /appearance:\s*none/.test(files.reminder), 'native form controls must reset OS appearance');
add('png-tray-runtime', /path\.resolve\(__dirname,\s*trayIconPath\)/.test(files.main) && /nativeImage\.createFromPath/.test(files.main) && /\.isEmpty\(\)/.test(files.main) && !/createFromDataURL/.test(files.main), 'tray must resolve the bundled PNG beside the webpack main entry and reject an empty native image');
add('menu-emoji', ['⏰', '🏠', '🖱️', '🙈', '🐾', '🚪'].every((emoji) => files.main.includes(emoji)) && spec.experience.interactions.every((interaction) => typeof interaction.emoji === 'string' && interaction.emoji.length > 0), 'system and interaction menus need semantic emoji');

const baseWindow = Number(spec.experience?.petSizing?.baseWindowPx);
const defaultScale = Number(spec.experience?.petSizing?.defaultScale);
const occupancy = Number(spec.assetPipeline?.targetOccupancy);
const estimatedDefaultSubject = baseWindow * defaultScale * occupancy;
const estimatedMinimumSubject = baseWindow * 0.65 * occupancy;
add('default-pet-size', estimatedDefaultSubject >= 120 && estimatedDefaultSubject <= 175, `estimated visible subject ${estimatedDefaultSubject.toFixed(1)}px must be 120-175px`);
add('minimum-pet-size', estimatedMinimumSubject <= 150, `estimated minimum visible subject ${estimatedMinimumSubject.toFixed(1)}px must be <=150px`);

const trayPath = path.join(root, 'src', 'assets', 'tray', 'tray-icon.png');
try {
  const { data, info } = await sharp(trayPath).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  let visible = 0;
  for (let index = 3; index < data.length; index += 4) if (data[index] >= 16) visible += 1;
  const visibleRatio = visible / (info.width * info.height);
  add('tray-icon-file', info.width === 32 && info.height === 32 && visibleRatio >= 0.08, `tray icon ${info.width}×${info.height}, visible ${(visibleRatio * 100).toFixed(1)}%`);
} catch (error) {
  add('tray-icon-file', false, error instanceof Error ? error.message : String(error));
}

await mkdir(qaDirectory, { recursive: true });
const report = { generatedAt: new Date().toISOString(), passed: checks.every((check) => check.passed), checks };
await writeFile(path.join(qaDirectory, 'ui-report.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
console.log(`UI QA: ${report.passed ? 'PASS' : 'FAIL'} (${checks.filter((check) => check.passed).length}/${checks.length})`);
if (!report.passed) {
  for (const check of checks.filter((item) => !item.passed)) console.error(`${check.id}: ${check.detail}`);
  process.exit(1);
}
