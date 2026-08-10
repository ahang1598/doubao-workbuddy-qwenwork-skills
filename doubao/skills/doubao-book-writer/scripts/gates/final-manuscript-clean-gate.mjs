#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { globSync } from '../lib/simple-glob.mjs';
import { resolveSafePath } from '../lib/path-safety.mjs';
import { checkWritingShape } from '../quality/check-writing-shape.mjs';

const PENDING_MARKERS = ['\\u5f85\\u5b8c\\u5584', '\\u5f85\\u7eed\\u5199', '\\u5f85\\u6838\\u5b9e', '\\u5f85\\u8865\\u5145'];

const PLACEHOLDER_RULES = Object.freeze([
  ['mat-todo-suffix', new RegExp('MAT-[A-Za-z0-9-]+（\\u5f85\\u8865\\u5145）', 'giu')],
  ['pending-mat-bracket', new RegExp('\\[\\u5f85\\u6838\\u5b9e-MAT-[^\\]\\r\\n]+\\]', 'giu')],
  ['discarded-tag', /\[DISCARDED-[^\]\r\n]{1,300}\]/giu],
  ['pending-mat-plain', new RegExp('\\u5f85\\u6838\\u5b9e-MAT-(?!XXX\\b)[A-Za-z0-9-]+', 'giu')],
  ['malformed-pending-line', new RegExp('^\\s*-\\s*`{0,2}\\s*`{0,2}\\s*[：:]\\s*\\u5f85\\u6838\\u5b9e[^\\r\\n]*$', 'gimu')],
  ['todo-tbd', /\bTODO\b|\bTBD\b/giu],
  ['template-braces', /\{\{[^}\r\n]+\}\}/gu],
  ['cn-placeholder-pending', new RegExp(`（${PENDING_MARKERS.join('|')}）`, 'gu')],
  ['cn-placeholder-expect', /敬请期待|稍后补充|此处省略/gu],
  ['cn-placeholder-omit', /（略）/gu],
]);

function markdownMatches(workspace, pattern) {
  return globSync(pattern, { cwd: workspace, absolute: true, nodir: true })
    .filter(file => file.toLowerCase().endsWith('.md'));
}

function receiptTarget(workspace) {
  try {
    const receipt = JSON.parse(fs.readFileSync(path.join(workspace, '.doubao-book-writer', 'delivery', 'document-delivery.json'), 'utf8').replace(/^\uFEFF/, ''));
    if (typeof receipt.markdown_path !== 'string' || !receipt.markdown_path.trim()) return null;
    const target = resolveSafePath(workspace, receipt.markdown_path, { mustExist: true, forbidden: ['.doubao-book-writer'] });
    return target.toLowerCase().endsWith('.md') && fs.statSync(target).isFile() ? target : null;
  } catch {
    return null;
  }
}

function finalTargets(workspace) {
  const targets = new Set();
  const short = path.join(workspace, 'manuscript.md');
  if (fs.existsSync(short) && fs.statSync(short).isFile()) targets.add(short);
  for (const file of markdownMatches(workspace, 'manuscript/**/*.md')) targets.add(file);
  for (const area of ['releases/**/*.md', 'deliverables/**/*.md']) {
    for (const file of markdownMatches(workspace, area)) if (/(全稿|终稿|终审)/u.test(path.basename(file))) targets.add(file);
  }
  const delivered = receiptTarget(workspace);
  if (delivered) targets.add(delivered);
  return [...targets].sort((left, right) => left.localeCompare(right, 'zh-Hans-CN', { numeric: true }));
}

function violationsIn(text) {
  const violations = [];
  for (const [rule, pattern] of PLACEHOLDER_RULES) {
    const matches = String(text).match(pattern);
    if (matches?.length) violations.push({ rule, count: matches.length, sample: matches[0].slice(0, 120) });
  }
  return violations;
}

function persistSnapshot(workspace, result) {
  try {
    const destination = path.join(workspace, '.doubao-book-writer', 'gates', 'final-manuscript-clean-gate.last.json');
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    const temporary = `${destination}.${process.pid}.${Date.now()}.tmp`;
    fs.writeFileSync(temporary, `${JSON.stringify({ generatedAt: new Date().toISOString(), ...result }, null, 2)}\n`, 'utf8');
    fs.renameSync(temporary, destination);
    return true;
  } catch {
    return false;
  }
}

function noTargetsResult(strictNoTargets) {
  return {
    code: strictNoTargets ? 1 : 0,
    status: strictNoTargets ? 'fail' : 'skipped',
    message: strictNoTargets ? 'no final manuscript targets' : 'skip: no final manuscript targets',
    targets: [],
    violations: [],
  };
}

export function runFinalCleanCheck({ workspace, strictNoTargets = true } = {}) {
  if (!workspace) return { code: 2, status: 'fail', message: 'missing --workspace', targets: [], violations: [] };
  const root = path.resolve(workspace);
  const targets = finalTargets(root);
  if (targets.length === 0) {
    const result = noTargetsResult(strictNoTargets);
    persistSnapshot(root, result);
    return result;
  }

  const violations = [];
  for (const file of targets) {
    try {
      const found = violationsIn(fs.readFileSync(file, 'utf8'));
      if (found.length > 0) violations.push({ file, violations: found });
    } catch (error) {
      violations.push({ file, violations: [{ rule: 'read-error', count: 1, sample: error instanceof Error ? error.message : String(error) }] });
    }
  }
  const shape = checkWritingShape({ workspace: root, writeReport: true });
  const failed = violations.length > 0 || shape.status !== 'pass';
  const result = {
    code: failed ? 1 : 0,
    status: failed ? 'fail' : 'pass',
    message: failed ? 'final manuscripts failed clean or writing-shape checks' : 'final manuscripts are clean',
    targets,
    violations,
    writingShape: {
      status: shape.status,
      failureCount: shape.failureCount,
      warningCount: shape.warningCount,
      reportPath: shape.reportPath,
    },
  };
  persistSnapshot(root, result);
  return result;
}

function cliOptions(argv) {
  const options = { workspace: null, strictNoTargets: true, json: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = path.resolve(argv[++index] || '');
    else if (token === '--strict-no-targets') options.strictNoTargets = true;
    else if (token === '--json') options.json = true;
  }
  return options;
}

export function main() {
  const options = cliOptions(process.argv);
  const result = runFinalCleanCheck(options);
  if (options.json) process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  else {
    process.stdout.write(`[final-manuscript-clean-gate] ${result.message}\n`);
    process.stdout.write(`[final-manuscript-clean-gate] targets=${result.targets.length} filesWithViolations=${result.violations.length}\n`);
  }
  process.exitCode = result.code;
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();
