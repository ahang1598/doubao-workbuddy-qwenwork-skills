#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

function completedChapters(markdown) {
  const completed = new Set();
  for (const line of String(markdown).split(/\r?\n/u)) {
    if (!line.trim().startsWith('|')) continue;
    const cells = line.trim().slice(1, -1).split('|').map(cell => cell.trim());
    const chapter = cells[0]?.toLowerCase();
    if (/^ch\d+$/iu.test(chapter || '') && /已完成|✅|完成/u.test(cells[2] || '')) completed.add(chapter);
  }
  return completed;
}

function dependencyRow(configuration, chapter) {
  if (Array.isArray(configuration?.chapters)) {
    return configuration.chapters.find(item => String(item?.id || '').toLowerCase() === chapter) || null;
  }
  if (configuration?.chapters && typeof configuration.chapters === 'object') return configuration.chapters[chapter] || null;
  return configuration?.[chapter] || null;
}

export function runChapterDependencyGate({ workspace, chapter } = {}) {
  if (!workspace || !chapter) return { code: 2, message: 'missing --workspace or --chapter', missing: [] };
  const root = path.resolve(workspace);
  const dependencyPath = path.join(root, '.doubao-book-writer', 'chapter-dependencies.json');
  const statusPath = path.join(root, 'chapter-ledger.md');
  if (!fs.existsSync(dependencyPath) || !fs.existsSync(statusPath)) {
    return { code: 0, message: '缺少依赖文件，跳过', missing: [] };
  }
  let configuration;
  try {
    configuration = JSON.parse(fs.readFileSync(dependencyPath, 'utf8').replace(/^\uFEFF/, ''));
  } catch {
    return { code: 2, message: 'chapter-dependencies.json 无法解析', missing: [] };
  }
  const chapterKey = String(chapter).trim().toLowerCase();
  const row = dependencyRow(configuration, chapterKey);
  const required = Array.isArray(row?.dependsOn) ? row.dependsOn.map(value => String(value).toLowerCase()) : [];
  const completed = completedChapters(fs.readFileSync(statusPath, 'utf8'));
  const missing = required.filter(requiredChapter => !completed.has(requiredChapter));
  return { code: missing.length > 0 ? 1 : 0, message: missing.length > 0 ? '依赖未满足' : '依赖已满足', missing };
}

function main() {
  const options = { workspace: null, chapter: null };
  for (let index = 2; index < process.argv.length; index += 1) {
    if (process.argv[index] === '--workspace') options.workspace = process.argv[++index];
    else if (process.argv[index] === '--chapter') options.chapter = process.argv[++index];
  }
  if (!options.workspace || !options.chapter) {
    process.stderr.write('用法: node scripts/gates/chapter-dependency-gate.mjs --workspace <工作目录> --chapter <章节id>\n');
    process.exitCode = 2;
    return;
  }
  const result = runChapterDependencyGate(options);
  if (result.code === 0) process.stdout.write(`chapter-dependency-gate: ${result.message === '依赖已满足' ? '✅ ' : ''}${result.message}\n`);
  else process.stderr.write(`chapter-dependency-gate: ✖ ${result.message}: ${JSON.stringify(result.missing)}\n`);
  process.exitCode = result.code;
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();
