#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { listChapterMarkdown } from '../lib/chapter-md-resolve.mjs';

function cliOptions(argv) {
  const options = { workspace: null, strict: false, minBytes: 300, minWordRatio: 0.8, maxWordRatio: 1.2, failOnOver: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = argv[++index];
    else if (token === '--strict') options.strict = true;
    else if (token === '--min-bytes') options.minBytes = Math.max(80, Number(argv[++index]) || 300);
    else if (token === '--min-word-ratio') options.minWordRatio = Math.max(0.1, Number(argv[++index]) || 0.8);
    else if (token === '--max-word-ratio') options.maxWordRatio = Math.max(options.minWordRatio, Number(argv[++index]) || 1.2);
    else if (token === '--fail-on-over') options.failOnOver = true;
  }
  return options;
}

function statusRows(markdown) {
  const rows = [];
  for (const line of String(markdown).split(/\r?\n/u)) {
    const trimmed = line.trim();
    if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) continue;
    const cells = trimmed.slice(1, -1).split('|').map(cell => cell.trim());
    if (cells.length < 3 || /^(章节ID|-+)$/iu.test(cells[0])) continue;
    rows.push({ chapterId: cells[0], fileCell: cells[1], status: cells[2] });
  }
  return rows;
}

function completed(status) {
  return /已完成|^✅|完成|成文|质检|終稿|终稿|归档/u.test(String(status || ''));
}

function linkedFileName(cell) {
  const link = String(cell || '').match(/^\[[^\]]+\]\(([^)]+)\)$/u)?.[1];
  return path.basename((link || String(cell || '')).replace(/`/gu, '').trim());
}

function chapterNumber(chapterId) {
  const value = String(chapterId || '').match(/^ch(\d+)$/iu)?.[1];
  return value ? Number(value) : null;
}

function chapterById(files, chapterId) {
  const number = chapterNumber(chapterId);
  if (!Number.isInteger(number)) return null;
  const padded = String(number).padStart(2, '0');
  return files.find(file => {
    const name = path.basename(file);
    return name.includes(`[S3-Ch${padded}]`) || new RegExp(`^ch0*${number}(?:\\D|$)`, 'iu').test(name);
  }) || null;
}

function substantiveBody(markdown) {
  return String(markdown).split(/\r?\n/u)
    .map(line => line.trim())
    .filter(line => line
      && !/^(?:#|[-*]\s+|\||>|```)/u.test(line))
    .filter(line => line.length >= 20)
    .length >= 5;
}

function briefOnly(markdown) {
  const briefPattern = new RegExp('Chapter\\s*Brief|\\u7ae0\\u8282\\u4efb\\u52a1\\u5361|Brief', 'u');
  return briefPattern.test(markdown) && !substantiveBody(markdown);
}

function expectedCharacters(workspace, number) {
  if (!Number.isInteger(number)) return null;
  const padded = String(number).padStart(2, '0');
  const candidates = [
    path.join(workspace, '.doubao-book-writer', 'briefs', `brief-ch${number}.md`),
    path.join(workspace, '.doubao-book-writer', 'writing-notes', `ch${padded}.brief.md`),
    path.join(workspace, '.doubao-book-writer', 'writing-notes', `brief-ch${padded}.md`),
  ];
  for (const candidate of candidates) {
    if (!fs.existsSync(candidate)) continue;
    const text = fs.readFileSync(candidate, 'utf8');
    const wordTargetPattern = new RegExp('(?:\\u9884\\u8ba1\\u5b57\\u6570|\\u76ee\\u6807\\u5b57\\u6570)\\s*[:：]\\s*([\\d,]+)', 'u');
    const raw = text.match(wordTargetPattern)?.[1];
    const value = Number(String(raw || '').replace(/,/gu, ''));
    if (value > 0) return value;
  }
  return null;
}

function visibleCharacterCount(markdown) {
  return String(markdown || '')
    .replace(/```[\s\S]*?```/gu, '')
    .replace(/`[^`]*`/gu, '')
    .replace(/!\[[^\]]*\]\([^)]*\)/gu, '')
    .replace(/\[[^\]]*\]\([^)]*\)/gu, '')
    .replace(/^\s*#{1,6}\s+/gmu, '')
    .replace(/^\s*[-*]\s+/gmu, '')
    .replace(/^\s*\|.*\|\s*$/gmu, '')
    .replace(/\s+/gu, '')
    .length;
}

export function verifyChapterLedgerTruth(options = {}) {
  if (!options.workspace) return { code: 2, failures: ['missing --workspace'], warnings: [], files: [] };
  const workspace = path.resolve(options.workspace);
  const statusPath = path.join(workspace, 'chapter-ledger.md');
  if (!fs.existsSync(statusPath)) return { code: 2, failures: [`缺少台账文件：${statusPath}`], warnings: [], files: [] };
  const files = listChapterMarkdown(workspace, { recursive: true });
  const filesByName = new Map(files.map(file => [path.basename(file), file]));
  const failures = [];
  const warnings = [];
  for (const row of statusRows(fs.readFileSync(statusPath, 'utf8'))) {
    if (!completed(row.status)) continue;
    const file = filesByName.get(linkedFileName(row.fileCell)) || chapterById(files, row.chapterId);
    if (!file || !fs.existsSync(file)) {
      failures.push(`${row.chapterId}: 状态写为完成，磁盘上没有对应正文（fileCell=${row.fileCell || '-'}）`);
      continue;
    }
    const size = fs.statSync(file).size;
    const text = fs.readFileSync(file, 'utf8');
    if (size < (options.minBytes ?? 300)) {
      failures.push(`${row.chapterId}: 状态写为完成，正文文件体积不足(${size}B < ${options.minBytes ?? 300}B) -> ${path.basename(file)}`);
      continue;
    }
    if (briefOnly(text)) {
      failures.push(`${row.chapterId}: 状态写为完成，内容仍像任务卡而非正文 -> ${path.basename(file)}`);
      continue;
    }
    const expected = expectedCharacters(workspace, chapterNumber(row.chapterId));
    if (!expected) continue;
    const actual = visibleCharacterCount(text);
    const minimum = Math.floor(expected * (options.minWordRatio ?? 0.8));
    const maximum = Math.floor(expected * (options.maxWordRatio ?? 1.2));
    if (actual < minimum) failures.push(`${row.chapterId}: 正文字数低于下限（实际≈${actual}，目标=${expected}，下限=${minimum}）`);
    else if (actual > maximum) {
      const message = `${row.chapterId}: 正文字数高于建议区间（实际≈${actual}，目标=${expected}，上限=${maximum}）`;
      (options.failOnOver ? failures : warnings).push(message);
    }
  }
  return { code: failures.length > 0 && options.strict ? 1 : 0, failures, warnings, files };
}

function main() {
  const options = cliOptions(process.argv);
  if (!options.workspace) {
    process.stderr.write('用法: node scripts/gates/verify-chapter-ledger-truth.mjs --workspace <工作目录> [--strict]\n');
    process.exitCode = 2;
    return;
  }
  const result = verifyChapterLedgerTruth(options);
  process.stdout.write(`verify-chapter-ledger-truth: ${path.resolve(options.workspace)}\n`);
  for (const warning of result.warnings) process.stdout.write(`  ⚠ ${warning}\n`);
  if (result.failures.length === 0) process.stdout.write('  ✅ 章节台账、正文文件和字数下限已对齐\n');
  else {
    process.stderr.write('  ✖ 台账与磁盘正文存在偏差:\n');
    for (const failure of result.failures) process.stderr.write(`    - ${failure}\n`);
  }
  process.exitCode = result.code;
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();
