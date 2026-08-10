#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { countChars } from '../lib/quality-runtime.mjs';
import { listChapterMarkdown } from '../lib/chapter-md-resolve.mjs';

const CHAPTER_HEADERS = new Set(['章节', '章节ID']);
const COUNT_HEADERS = ['当前字数', '字数', '字符数'];
const FILE_HEADERS = new Set(['文件', '路径', '章节文件']);

function cellsOf(line) {
  const trimmed = line.trim();
  if (!(trimmed.startsWith('|') && trimmed.endsWith('|'))) return null;
  return trimmed.slice(1, -1).split('|').map(cell => cell.trim());
}

function locateColumns(lines) {
  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const headers = cellsOf(lines[lineIndex]);
    if (!headers) continue;
    const chapter = headers.findIndex(value => CHAPTER_HEADERS.has(value));
    const count = COUNT_HEADERS.map(value => headers.indexOf(value)).find(index => index >= 0) ?? -1;
    if (chapter < 0 || count < 0) continue;
    return {
      lineIndex,
      chapter,
      count,
      file: headers.findIndex(value => FILE_HEADERS.has(value)),
    };
  }
  throw new Error('章节台账缺少「章节」和「当前字数 / 字数 / 字符数」表头');
}

function linkedPath(value) {
  const cell = String(value || '').trim();
  const markdownLink = cell.match(/^\[[^\]]*\]\(([^)]+)\)$/u);
  return (markdownLink?.[1] || cell.replace(/`/gu, '')).trim();
}

function inside(root, relativePath) {
  if (!relativePath || path.isAbsolute(relativePath)) return null;
  const candidate = path.resolve(root, relativePath);
  const relation = path.relative(root, candidate);
  if (relation.startsWith('..') || path.isAbsolute(relation)) return null;
  return fs.existsSync(candidate) && fs.statSync(candidate).isFile() ? candidate : null;
}

function chapterById(root, value) {
  const match = String(value || '').trim().match(/^ch0*(\d+)$/iu);
  if (!match) return null;
  const number = Number(match[1]);
  return listChapterMarkdown(path.join(root, 'manuscript'), { recursive: true })
    .find(file => {
      const candidate = path.basename(file).match(/^ch0*(\d+)(?:\D|$)/iu);
      return candidate && Number(candidate[1]) === number;
    }) || null;
}

export function refreshChapterCharCounts(workspace, { dryRun = false } = {}) {
  const root = path.resolve(workspace);
  const statusPath = path.join(root, 'chapter-ledger.md');
  if (!fs.existsSync(statusPath)) throw new Error(`未找到章节台账：${statusPath}`);
  const original = fs.readFileSync(statusPath, 'utf8');
  const lines = original.split(/\r?\n/u);
  const columns = locateColumns(lines);
  let updated = 0;

  for (let index = columns.lineIndex + 2; index < lines.length; index += 1) {
    const cells = cellsOf(lines[index]);
    if (!cells) break;
    if (cells.length <= Math.max(columns.chapter, columns.count)) continue;
    const chapterFile = columns.file >= 0 ? inside(root, linkedPath(cells[columns.file])) : null;
    const source = chapterFile || chapterById(root, cells[columns.chapter]);
    if (!source) continue;
    const measured = String(countChars(fs.readFileSync(source, 'utf8')));
    if (cells[columns.count] === measured) continue;
    cells[columns.count] = measured;
    lines[index] = `| ${cells.join(' | ')} |`;
    updated += 1;
  }

  if (!dryRun && updated > 0) fs.writeFileSync(statusPath, lines.join('\n'), 'utf8');
  return { updated, statusPath, dryRun };
}

function argumentsOf(argv) {
  const options = { dryRun: false };
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--workspace') options.workspace = argv[++index];
    else if (argv[index] === '--dry-run') options.dryRun = true;
  }
  return options;
}

function main() {
  const options = argumentsOf(process.argv);
  if (!options.workspace) {
    process.stderr.write('refresh-chapter-ledger: 缺少 --workspace\n');
    process.exitCode = 2;
    return;
  }
  try {
    const result = refreshChapterCharCounts(options.workspace, options);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();
