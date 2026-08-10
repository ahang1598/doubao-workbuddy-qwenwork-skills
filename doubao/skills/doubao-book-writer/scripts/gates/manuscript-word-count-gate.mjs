#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { globSync } from '../lib/simple-glob.mjs';

const CN_NUMERAL_CLASS = '\\u96f6\\u3007\\u4e00\\u4e8c\\u4e09\\u56db\\u4e94\\u516d\\u4e03\\u516b\\u4e5d\\u5341\\u767e\\u5343\\u4e07\\u4e24';
const WORD_COUNT_REQUIREMENT_RE = new RegExp(`(?:约|至少|不少于|不低于|不超过|最多|控制在|目标(?:为|是)?|篇幅(?:为|是)?|字数(?:为|是|约|不少于|不低于|不超过|控制在)?)[^。；;\\n]{0,24}(?:\\d+(?:\\.\\d+)?(?:\\s*[-–—~～至到]\\s*\\d+(?:\\.\\d+)?)?\\s*(?:万|千|百)?|[${CN_NUMERAL_CLASS}]+)\\s*字|(?:\\d+(?:\\.\\d+)?|[${CN_NUMERAL_CLASS}]+)\\s*(?:万|千|百)?\\s*字`, 'u');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
}

function resolveInside(root, relativePath) {
  if (typeof relativePath !== 'string' || !relativePath.trim() || path.isAbsolute(relativePath)) return null;
  const absolute = path.resolve(root, relativePath);
  const relation = path.relative(root, absolute);
  return relation === '' || (!relation.startsWith('..') && !path.isAbsolute(relation)) ? absolute : null;
}

function countText(filePath) {
  return fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '').replace(/\s+/g, '').length;
}

function inventoryCount(filePath, root, fileInventory) {
  if (!Array.isArray(fileInventory)) return null;
  const relative = path.relative(root, filePath).replace(/\\/g, '/');
  const entry = fileInventory.find(item => item?.file === relative || item?.path === relative);
  const value = Number(entry?.chars ?? entry?.nonWhitespaceChars);
  return Number.isFinite(value) ? value : null;
}

function defaultManuscriptFiles(root) {
  const short = path.join(root, 'manuscript.md');
  if (fs.existsSync(short) && fs.statSync(short).isFile() && fs.readFileSync(short, 'utf8').trim()) return [short];
  return globSync('manuscript/**/*.md', { cwd: root, absolute: true, nodir: true })
    .sort((left, right) => left.localeCompare(right, 'zh-Hans-CN', { numeric: true }));
}

export function ruleBounds(rule) {
  const target = Number(rule.target);
  const requestedTolerance = Number.isFinite(Number(rule.tolerancePercent)) ? Number(rule.tolerancePercent) : 20;
  const toleranceValid = requestedTolerance >= 0 && requestedTolerance <= 20;
  const tolerance = toleranceValid ? requestedTolerance : 20;
  const targetMinimum = Number.isFinite(target) ? Math.ceil(target * (1 - tolerance / 100)) : null;
  const targetMaximum = Number.isFinite(target) ? Math.floor(target * (1 + tolerance / 100)) : null;
  const explicitMinimum = Number.isFinite(Number(rule.minimum)) ? Number(rule.minimum) : null;
  const explicitMaximum = Number.isFinite(Number(rule.maximum)) ? Number(rule.maximum) : null;
  const minimum = targetMinimum == null ? explicitMinimum : Math.max(targetMinimum, explicitMinimum ?? targetMinimum);
  const maximum = targetMaximum == null ? explicitMaximum : Math.min(targetMaximum, explicitMaximum ?? targetMaximum);
  return {
    target: Number.isFinite(target) ? target : null,
    tolerancePercent: tolerance,
    toleranceValid,
    minimum,
    maximum,
  };
}

function baselineCount(rule, artifactBaseline, files, root) {
  if (!artifactBaseline) return null;
  if (rule.path) return Number(artifactBaseline[String(rule.path).replace(/\\/g, '/')]?.nonWhitespaceChars);
  let total = 0;
  let found = false;
  for (const file of files) {
    const relative = path.relative(root, file).replace(/\\/g, '/');
    const value = Number(artifactBaseline[relative]?.nonWhitespaceChars);
    if (Number.isFinite(value)) { total += value; found = true; }
  }
  return found ? total : null;
}

function evaluateManuscriptWordCount({
  workspace,
  route = null,
  artifactBaseline = null,
  checklist: suppliedChecklist = null,
  fileInventory = null,
  progressOnly = false,
} = {}) {
  if (!workspace) return { status: 'fail', code: 2, failures: [{ code: 'INVALID_ARGUMENTS', message: 'workspace is required' }], results: [] };
  const root = path.resolve(workspace);
  const checklistPath = path.join(root, '.doubao-book-writer', 'requirement-checklist.json');
  if (suppliedChecklist == null && !fs.existsSync(checklistPath)) {
    if (progressOnly) return { status: 'pass', code: 0, skipped: true, phase: 'progress', route, failures: [], results: [] };
    return { status: 'fail', code: 1, failures: [{ code: 'WORD_COUNT_CHECKLIST_MISSING', message: 'requirement checklist is missing' }], results: [] };
  }
  let checklist = suppliedChecklist;
  try { checklist ??= readJson(checklistPath); } catch (error) {
    return { status: 'fail', code: 1, failures: [{ code: 'WORD_COUNT_CHECKLIST_INVALID', message: error.message }], results: [] };
  }
  const rules = Array.isArray(checklist.wordCountRules) ? checklist.wordCountRules : [];
  if (rules.length === 0) {
    const requirementText = [
      checklist.topic,
      ...(Array.isArray(checklist.requirements) ? checklist.requirements.map(item => item?.requirement) : []),
    ].filter(value => typeof value === 'string').join('\n');
    if (WORD_COUNT_REQUIREMENT_RE.test(requirementText)) {
      return {
        status: 'fail',
        code: 1,
        skipped: false,
        phase: progressOnly ? 'progress' : 'final',
        route,
        failures: [{
          code: 'WORD_COUNT_RULES_REQUIRED',
          message: 'topic or requirements specify a word count, but wordCountRules is empty or missing',
        }],
        results: [],
      };
    }
    return { status: 'pass', code: 0, skipped: true, phase: progressOnly ? 'progress' : 'final', route, failures: [], results: [] };
  }

  const failures = [];
  const results = [];
  for (const [index, rule] of rules.entries()) {
    const id = typeof rule?.id === 'string' && rule.id.trim() ? rule.id : `word-count-${index + 1}`;
    let files;
    if (rule?.path) {
      const absolute = resolveInside(root, rule.path);
      if (!absolute) {
        failures.push({ code: 'INVALID_WORD_COUNT_PATH', id, path: rule.path, message: 'word-count path is outside workspace' });
        continue;
      }
      files = [absolute];
    } else files = defaultManuscriptFiles(root);
    if (files.length === 0 || files.some((file) => !fs.existsSync(file) || !fs.statSync(file).isFile())) {
      if (progressOnly) {
        results.push({ id, route, phase: 'progress', files: [], pending: true });
        continue;
      }
      failures.push({ code: 'WORD_COUNT_TARGET_MISSING', id, path: rule?.path || null, message: 'word-count target file is missing' });
      continue;
    }
    const actual = files.reduce((total, file) => total + (inventoryCount(file, root, fileInventory) ?? countText(file)), 0);
    const bounds = ruleBounds(rule || {});
    const before = baselineCount(rule || {}, artifactBaseline, files, root);
    const added = Number.isFinite(before) ? actual - before : null;
    const minimumAdded = Number.isFinite(Number(rule?.minimumAdded)) ? Number(rule.minimumAdded) : null;
    const maximumAdded = minimumAdded == null ? null : Math.floor(minimumAdded * 1.2);
    const result = { id, route, phase: progressOnly ? 'progress' : 'final', files: files.map((file) => path.relative(root, file).replace(/\\/g, '/')), actual, before, added, ...bounds, minimumAdded, maximumAdded };
    results.push(result);
    if (!bounds.toleranceValid) failures.push({ code: 'WORD_COUNT_TOLERANCE_EXCEEDS_LIMIT', id, tolerancePercent: Number(rule?.tolerancePercent), maximumTolerancePercent: 20, message: `${id} tolerancePercent must be between 0 and 20` });
    if (!progressOnly && bounds.minimum != null && actual < bounds.minimum) failures.push({ code: 'WORD_COUNT_BELOW_MINIMUM', id, actual, minimum: bounds.minimum, message: `${id} actual ${actual} is below ${bounds.minimum}` });
    if (bounds.maximum != null && actual > bounds.maximum) failures.push({ code: 'WORD_COUNT_ABOVE_MAXIMUM', id, actual, maximum: bounds.maximum, message: `${id} actual ${actual} is above ${bounds.maximum}` });
    if (result.minimumAdded != null) {
      if (!Number.isFinite(before)) failures.push({ code: 'WORD_COUNT_BASELINE_MISSING', id, message: `${id} 使用 minimumAdded 增量规则，但缺少字数基线；三阶段模型请改用 minimum 全量下限` });
      else if (!progressOnly && added < result.minimumAdded) failures.push({ code: 'WORD_COUNT_ADDITION_BELOW_MINIMUM', id, added, minimumAdded: result.minimumAdded, message: `${id} added ${added}, below ${result.minimumAdded}` });
      else if (added > result.maximumAdded) failures.push({ code: 'WORD_COUNT_ADDITION_ABOVE_MAXIMUM', id, added, maximumAdded: result.maximumAdded, message: `${id} added ${added}, above ${result.maximumAdded}` });
    }
  }
  return { status: failures.length === 0 ? 'pass' : 'fail', code: failures.length === 0 ? 0 : 1, skipped: false, phase: progressOnly ? 'progress' : 'final', route, failures, results };
}

export function runManuscriptWordCountGate(options = {}) {
  return evaluateManuscriptWordCount({ ...options, progressOnly: false });
}

export function runManuscriptWordCountProgressGate(options = {}) {
  return evaluateManuscriptWordCount({ ...options, progressOnly: true });
}

function main() {
  const args = { workspace: null, route: null, json: false };
  for (let index = 2; index < process.argv.length; index += 1) {
    const token = process.argv[index];
    if (token === '--workspace') args.workspace = process.argv[++index] || null;
    else if (token === '--route') args.route = process.argv[++index] || null;
    else if (token === '--json') args.json = true;
  }
  const result = runManuscriptWordCountGate(args);
  console.log(args.json ? JSON.stringify(result, null, 2) : `[manuscript-word-count-gate] ${result.status}`);
  process.exit(result.code);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
