#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { resolveSafePath } from '../lib/path-safety.mjs';

// 扩写计量：核对扩写后的正文是否达到计划目标字符（按最低比例）。
// 既可单文件校验，也可从扩写计划表批量校验。仅服务扩写场景，不在 write 强制门内。

// 这些是流程台账/元文件，不是可计量的正文，批量校验时应排除。
const META_DOCUMENTS = new Set([
  'book-context-brief.md',
  'chapter-ledger.md',
  'esm-state.md',
  'material-inventory.md',
  'material-library.md',
  'next-action.md',
  'retro-action-items.md',
]);

// 把比例夹到 [0.1, 1]；非法值退回默认 0.9。
function clampRatio(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0.9;
  return Math.min(1, Math.max(0.1, numeric));
}

/** 判断某文件是否是可计量的章节正文（排除流程台账/元文件）。 */
export function isCountableChapterFile(filePath) {
  return !META_DOCUMENTS.has(path.basename(String(filePath)).toLowerCase());
}

function splitRow(line) {
  const trimmed = line.trim();
  if (trimmed[0] !== '|' || trimmed.at(-1) !== '|') return null;
  return trimmed.slice(1, -1).split('|').map(cell => cell.trim());
}

function isSeparator(cells) {
  return Array.isArray(cells) && cells.length > 0 && cells.every(cell => /^:?-{3,}:?$/u.test(cell));
}

function looksLikePlanHeader(cells) {
  return Array.isArray(cells) && cells.some(cell => /(?:目标.{0,4}(?:字符|字数)|targetChars)/iu.test(cell));
}

function safePlanFile(workspace, rawValue) {
  const relative = String(rawValue || '').replace(/^`+|`+$/gu, '');
  if (!relative) return null;
  try {
    return resolveSafePath(workspace, relative, { mustExist: false });
  } catch {
    return null;
  }
}

/**
 * 从扩写计划 Markdown 抽取 {chapterId, file, targetChars} 行。
 * 表头需含"目标字符/字数"列，前三列依次为章节、文件、目标字符。
 */
export function readPlanRows(planPath, workspace, options = {}) {
  const lines = fs.readFileSync(planPath, 'utf8').replace(/^\uFEFF/u, '').split(/\r?\n/u);
  const headerIndex = lines.findIndex(line => looksLikePlanHeader(splitRow(line)));
  if (headerIndex === -1) return [];

  const rows = [];
  for (let cursor = headerIndex + 1; cursor < lines.length; cursor += 1) {
    const cells = splitRow(lines[cursor]);
    if (!cells) {
      if (rows.length > 0) break;
      continue;
    }
    if (isSeparator(cells)) continue;
    const chapterId = cells[0] || '';
    const file = safePlanFile(workspace, cells[1] || '');
    const targetChars = Number(String(cells[2] || '').replace(/,/gu, ''));
    if (!file || !Number.isFinite(targetChars) || targetChars <= 0) continue;
    if (options.filterMeta !== false && !isCountableChapterFile(file)) continue;
    rows.push({ chapterId, file, targetChars });
  }
  return rows;
}

/** 计量单个文件是否达标：实际字符 ≥ 目标 × 比例。 */
export function measureFile(fileAbs, targetChars, minRatio) {
  const minRequired = Math.floor(targetChars * clampRatio(minRatio));
  if (!fs.existsSync(fileAbs) || !fs.statSync(fileAbs).isFile()) {
    return { ok: false, actual: 0, minRequired: 0, targetChars, file: fileAbs, error: 'file_missing' };
  }
  const actual = fs.readFileSync(fileAbs, 'utf8').length;
  return { ok: actual >= minRequired, actual, minRequired, targetChars, file: fileAbs, error: null };
}

function requestedFile(workspace, requested, mustExist) {
  try {
    return { file: resolveSafePath(workspace, requested, { mustExist }), error: null };
  } catch {
    return { file: null, error: requested };
  }
}

function measureFromPlan(options, ratio) {
  const resolved = requestedFile(options.workspace, options.fromPlan, true);
  if (!resolved.file) {
    return { code: 2, results: [], message: `无法读取扩写计划：${path.resolve(options.workspace, options.fromPlan || '')}` };
  }
  const rows = readPlanRows(resolved.file, options.workspace, { filterMeta: true });
  if (rows.length > 0) {
    return { code: 0, results: rows.map(row => measureFile(row.file, row.targetChars, ratio)), message: null };
  }
  const hasHeaderOnly = fs.readFileSync(resolved.file, 'utf8')
    .split(/\r?\n/u)
    .some(line => looksLikePlanHeader(splitRow(line)));
  if (hasHeaderOnly) {
    return { code: 0, results: [], message: '扩写计划表存在，但没有可计量的正文文件；请把文件列改为 manuscript 下的章节 Markdown。' };
  }
  return { code: 2, results: [], message: '扩写计划缺少可识别的目标表；表格前三列应为章节、文件和目标字符。' };
}

/** 执行扩写计量。支持单文件（file+targetChars）或计划批量（fromPlan）两种模式。 */
export function runExpansionWordVerify(options = {}) {
  if (!options.workspace) return { code: 2, results: [], message: '缺少工作目录参数' };
  const ratio = clampRatio(options.minRatio);

  let outcome;
  if (options.fromPlan) {
    outcome = measureFromPlan(options, ratio);
  } else if (options.file && Number.isFinite(options.targetChars)) {
    const resolved = requestedFile(options.workspace, options.file, false);
    if (!resolved.file) return { code: 2, results: [], message: `正文文件不在工作目录内：${options.file}` };
    outcome = { code: 0, results: [measureFile(resolved.file, options.targetChars, ratio)], message: null };
  } else {
    return { code: 2, results: [], message: '请提供单文件及目标字符，或提供扩写计划路径' };
  }

  if (outcome.code === 0 && outcome.results.some(item => !item.ok)) return { ...outcome, code: 1 };
  return outcome;
}

function parseCli(argv) {
  const options = { workspace: null, file: null, targetChars: null, fromPlan: null, minRatio: 0.9, json: false };
  const valueFlags = {
    '--workspace': 'workspace',
    '--file': 'file',
    '--target-chars': 'targetChars',
    '--from-plan': 'fromPlan',
    '--min-ratio': 'minRatio',
  };
  for (let cursor = 2; cursor < argv.length; cursor += 1) {
    const token = argv[cursor];
    if (token === '--json') { options.json = true; continue; }
    const key = valueFlags[token];
    if (key) options[key] = argv[++cursor];
  }
  if (options.workspace) options.workspace = path.resolve(options.workspace);
  if (options.targetChars !== null) options.targetChars = Number(options.targetChars);
  options.minRatio = clampRatio(options.minRatio);
  return options;
}

function report(outcome, ratio) {
  if (outcome.message) {
    (outcome.code === 2 ? process.stderr : process.stdout).write(`[扩写计量] ${outcome.message}\n`);
  }
  for (const item of outcome.results) {
    const status = item.error ? `ERROR ${item.error}` : item.ok ? 'PASS' : 'FAIL';
    process.stdout.write(`[扩写计量] ${status} ${item.file} actual=${item.actual} minimum=${item.minRequired} target=${item.targetChars} ratio=${ratio}\n`);
  }
}

export function main() {
  const options = parseCli(process.argv);
  if (!options.workspace) {
    process.stderr.write('用法：node scripts/gates/chapter-length-verify.mjs --workspace <workspace> (--file <Markdown> --target-chars <N> | --from-plan <plan.md>) [--min-ratio 0.9] [--json]\n');
    process.exitCode = 2;
    return;
  }
  const outcome = runExpansionWordVerify(options);
  if (options.json) process.stdout.write(`${JSON.stringify(outcome, null, 2)}\n`);
  else report(outcome, options.minRatio);
  process.exitCode = outcome.code;
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();
