#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const COVERAGE_TARGET = Object.freeze({ light: 0.15, medium: 0.25, strong: 0.35 });
const NOTICE_PATTERN = new RegExp('\\u503c\\u5f97\\u6ce8\\u610f\\u7684\\u662f|\\u9700\\u8981\\u6ce8\\u610f\\u7684\\u662f', 'g');
const PHRASE_RULES = Object.freeze([
  { name: '随着', pattern: /随着/g },
  { name: 'quality-growth', pattern: new RegExp('\\u9ad8\\u8d28\\u91cf\\u53d1\\u5c55', 'g') },
  { name: '助力', pattern: /助力/g },
  { name: '赋能', pattern: /赋能/g },
  { name: 'base-step', pattern: new RegExp('\\u5728\\u6b64\\u57fa\\u7840\\u4e0a', 'g') },
  { name: '不可忽视', pattern: /不可忽视/g },
  { name: '提示注意', pattern: NOTICE_PATTERN },
  { name: '总之', pattern: /总之|综上所述/g },
  { name: '最后', pattern: /最后/g },
  { name: '再次', pattern: /再次/g },
  { name: '其次', pattern: /其次/g },
  { name: '首先', pattern: /首先/g },
]);

function argumentsFrom(argv) {
  const parsed = { before: null, after: null, strength: 'medium', reportFile: null, json: false, help: false };
  const valueFlags = new Map([
    ['--before', 'before'],
    ['--after', 'after'],
    ['--strength', 'strength'],
    ['--report-file', 'reportFile'],
  ]);
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (valueFlags.has(token) && argv[index + 1]) parsed[valueFlags.get(token)] = argv[++index];
    else if (token === '--json') parsed.json = true;
    else if (token === '--help' || token === '-h') parsed.help = true;
  }
  return parsed;
}

function plainText(raw, extension) {
  const withoutMarkup = extension === '.html' || extension === '.htm'
    ? raw
        .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ')
        .replace(/<\/(?:h[1-6]|p|li|div|section|article)>|<br\s*\/?>/gi, '\n')
        .replace(/<[^>]*>/g, ' ')
    : raw;
  return withoutMarkup.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim();
}

function loadDocument(file) {
  const absolute = path.resolve(file);
  const text = plainText(fs.readFileSync(absolute, 'utf8'), path.extname(absolute).toLowerCase());
  return { path: absolute, text };
}

function paragraphs(text) {
  return text.split(/\n\s*\n/).map((block) => block.replace(/\s+/g, ' ').trim()).filter(Boolean);
}

function countPhrases(text) {
  return Object.fromEntries(PHRASE_RULES.map(({ name, pattern }) => [name, text.match(pattern)?.length ?? 0]));
}

function compareParagraphs(left, right) {
  const total = Math.max(left.length, right.length);
  const samples = [];
  let changed = 0;
  for (let index = 0; index < total; index += 1) {
    const before = left[index] ?? '';
    const after = right[index] ?? '';
    if (before === after) continue;
    changed += 1;
    if (samples.length < 6) samples.push({ index: index + 1, before: before.slice(0, 140), after: after.slice(0, 140) });
  }
  return { changed, ratio: total === 0 ? 0 : changed / total, samples };
}

function phraseChanges(before, after) {
  return PHRASE_RULES.map(({ name }) => ({
    label: name,
    before: before[name] ?? 0,
    after: after[name] ?? 0,
    delta: (after[name] ?? 0) - (before[name] ?? 0),
  })).filter((item) => item.before !== 0 || item.after !== 0);
}

function observations(ratio, strength, rows) {
  const notes = [];
  if (ratio < COVERAGE_TARGET[strength]) {
    notes.push(`${strength} 档要求下，段落变动不足（当前 ${(ratio * 100).toFixed(1)}%）。`);
  }
  const unchanged = rows.filter((row) => row.after > 0 && row.after >= row.before).map((row) => row.label);
  if (unchanged.length > 0) notes.push(`这些口吻标记仍未减少：${unchanged.join('、')}。`);
  return notes;
}

function tableFor(rows) {
  if (rows.length === 0) return '无明显高频口吻标记。';
  return ['| marker | before | after | delta |', '| --- | --- | --- | --- |',
    ...rows.map((row) => `| ${row.label} | ${row.before} | ${row.after} | ${row.delta} |`)].join('\n');
}

function render(result) {
  const sampleSections = result.samples.length === 0
    ? ['无段落级差异样本。']
    : result.samples.flatMap((sample) => [
        `### 段落 ${sample.index}`,
        '',
        `before：${sample.before || '(empty)'}`,
        '',
        `after：${sample.after || '(empty)'}`,
      ]);
  const conclusion = result.warnings.length > 0
    ? result.warnings.map((warning) => `- ${warning}`)
    : ['- 改写覆盖率与口吻词变化基本符合预期，仍需人工抽样复核。'];
  return [
    '# 表达改写对照', '',
    `- before：\`${result.beforePath}\``, `- after：\`${result.afterPath}\``,
    `- 档位：\`${result.strength}\``, `- 变动段落占比：${(result.changeRatio * 100).toFixed(1)}%`,
    '', '## 数量概览', '',
    `- before chars：${result.beforeChars}`, `- after chars：${result.afterChars}`,
    `- before paragraphs：${result.beforeParagraphCount}`, `- after paragraphs：${result.afterParagraphCount}`,
    '', '## 口吻标记', '', tableFor(result.markerRows),
    '', '## 抽样段落', '', ...sampleSections,
    '', '## 结论', '', ...conclusion, '',
  ].join('\n');
}

export function runDeAiComparison({ before, after, strength = 'medium', reportFile = null } = {}) {
  if (!before || !after) throw new Error('need both --before and --after');
  const level = Object.hasOwn(COVERAGE_TARGET, strength) ? strength : 'medium';
  const source = loadDocument(before);
  const revision = loadDocument(after);
  if (!source.text || !revision.text) throw new Error('one side is empty; diff report cannot be generated');

  const sourceParagraphs = paragraphs(source.text);
  const revisionParagraphs = paragraphs(revision.text);
  const comparison = compareParagraphs(sourceParagraphs, revisionParagraphs);
  const markerRows = phraseChanges(countPhrases(source.text), countPhrases(revision.text));
  const warnings = observations(comparison.ratio, level, markerRows);
  const result = {
    ok: true,
    beforePath: source.path,
    afterPath: revision.path,
    strength: level,
    beforeChars: source.text.length,
    afterChars: revision.text.length,
    beforeParagraphCount: sourceParagraphs.length,
    afterParagraphCount: revisionParagraphs.length,
    changeRatio: comparison.ratio,
    changedParagraphs: comparison.changed,
    markerRows,
    samples: comparison.samples,
    warnings,
  };
  const markdown = render(result);
  const extension = path.extname(revision.path);
  const reportPath = path.resolve(reportFile ?? path.join(path.dirname(revision.path), `${path.basename(revision.path, extension)}.de-ai-diff.md`));
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, markdown, 'utf8');
  return { ...result, reportFile: reportPath, markdown };
}

export function main(argv = process.argv) {
  const args = argumentsFrom(argv);
  if (args.help) {
    console.log('用法：node scripts/quality/de-ai-diff.mjs --before <原稿> --after <改写稿> [--strength light|medium|strong] [--json]');
    return 0;
  }
  try {
    const result = runDeAiComparison(args);
    const output = args.json
      ? JSON.stringify({ ok: true, reportFile: result.reportFile, strength: result.strength, changeRatio: Number(result.changeRatio.toFixed(4)), warnings: result.warnings }, null, 2)
      : `[de-ai-diff] ${result.reportFile}`;
    process.stdout.write(`${output}\n`);
    return 0;
  } catch (error) {
    const output = args.json ? JSON.stringify({ ok: false, error: error.message }, null, 2) : `[de-ai-diff] ${error.message}`;
    (args.json ? process.stdout : process.stderr).write(`${output}\n`);
    return 1;
  }
}

const invokedFile = process.argv[1] ? path.resolve(process.argv[1]) : null;
if (invokedFile === path.resolve(fileURLToPath(import.meta.url))) process.exit(main());
