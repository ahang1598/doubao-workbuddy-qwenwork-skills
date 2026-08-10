#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { globSync } from '../lib/simple-glob.mjs';
import { resolveSafePath } from '../lib/path-safety.mjs';

const DEFAULT_PATTERN = 'manuscript/**/*.md';
const SOURCE_IGNORES = ['**/node_modules/**', '**/.git/**', '**/.doubao-book-writer/**', '**/qc-output/**'];

function cliOptions(argv) {
  const options = { workspace: process.cwd(), output: null, glob: null, title: null, dryRun: false, noBackup: false, recordArtifacts: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = path.resolve(argv[++index] || '');
    else if (token === '--output' || token === '-o') options.output = argv[++index];
    else if (token === '--glob' || token === '-g') options.glob = argv[++index];
    else if (token === '--title') options.title = argv[++index];
    else if (token === '--dry-run') options.dryRun = true;
    else if (token === '--no-backup') options.noBackup = true;
    else if (token === '--record-artifacts') options.recordArtifacts = true;
  }
  return options;
}

function projectRelative(root, filePath) {
  return path.relative(root, filePath).replace(/\\/g, '/');
}

function sourceFiles(root, pattern, output) {
  const matched = globSync(pattern, { cwd: root, absolute: true, nodir: true, ignore: SOURCE_IGNORES })
    .filter(file => file.toLowerCase().endsWith('.md'));
  const safe = matched.map(file => resolveSafePath(root, file, { mustExist: true, forbidden: ['.doubao-book-writer'] }));
  const unique = [...new Set(safe.map(file => path.resolve(file)))].filter(file => file !== path.resolve(output));
  return unique.sort((left, right) => path.basename(left).localeCompare(path.basename(right), 'zh-Hans-CN', { numeric: true }));
}

function renderMerged(root, files, title, generatedAt) {
  const sections = [`<!-- title: ${title} -->`, `<!-- generated-at: ${generatedAt} -->`, '', '---', ''];
  for (const file of files) {
    sections.push(`<!-- source: ${projectRelative(root, file)} -->`, '');
    sections.push(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '').replace(/\r\n/gu, '\n').trimEnd(), '', '');
  }
  return sections.join('\n');
}

function backupOutput(output, disabled) {
  if (!fs.existsSync(output)) return null;
  if (disabled) throw new Error('refusing to overwrite an existing output without backup');
  const backup = `${output}.merge-backup-${new Date().toISOString().replace(/[:.]/gu, '-')}.md`;
  fs.copyFileSync(output, backup, fs.constants.COPYFILE_EXCL);
  return backup;
}

function writeAtomic(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(temporary, content, 'utf8');
  fs.renameSync(temporary, filePath);
}

export function runMergeChapters(options = {}) {
  const root = path.resolve(options.workspace || process.cwd());
  if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) return { code: 2, message: 'invalid book root' };
  if (!options.output) return { code: 2, message: 'missing --output <file.md>' };
  let output;
  try {
    output = resolveSafePath(root, options.output, { forbidden: ['.doubao-book-writer'] });
  } catch (error) {
    return { code: 2, message: `${error.message}; output must stay inside workspace and outside .doubao-book-writer` };
  }
  const pattern = options.glob || DEFAULT_PATTERN;
  let files;
  try {
    files = sourceFiles(root, pattern, output);
  } catch (error) {
    return { code: 2, message: error instanceof Error ? error.message : String(error) };
  }
  if (files.length === 0) return { code: 1, message: `no markdown matched by glob: ${pattern}`, pattern, files: [] };

  const generatedAt = new Date().toISOString();
  const body = renderMerged(root, files, options.title || path.basename(output, '.md'), generatedAt);
  const nonWhitespaceChars = body.replace(/\s+/gu, '').length;
  if (options.dryRun) return { code: 0, dryRun: true, output, files, nonWhitespaceChars, pattern };

  let backup = null;
  try {
    backup = backupOutput(output, Boolean(options.noBackup));
  } catch (error) {
    return { code: 2, message: error.message, output, files };
  }
  writeAtomic(output, body);
  let artifactPath = null;
  if (options.recordArtifacts) {
    artifactPath = path.join(root, '.doubao-book-writer', 'merge-chapters.last.json');
    writeAtomic(artifactPath, `${JSON.stringify({
      schemaVersion: '1.0.0',
      mergedAt: generatedAt,
      workspace: root,
      outputPath: output,
      outputRelative: projectRelative(root, output),
      sourceFileCount: files.length,
      mergedNonWhitespaceChars: nonWhitespaceChars,
      globPattern: pattern,
      sourcesSample: files.slice(0, 8).map(file => projectRelative(root, file)),
      hint: '合章终稿即交付源，由 make deliver 生成飞书文档；章节字数可由 refresh-chapter-ledger 刷新。',
    }, null, 2)}\n`);
  }
  return { code: 0, dryRun: false, output, files, nonWhitespaceChars, pattern, backup, artifactPath };
}

export function main() {
  const result = runMergeChapters(cliOptions(process.argv));
  if (result.code !== 0) {
    process.stderr.write(`merge-chapters: ${result.message}\n`);
    process.exitCode = result.code;
    return;
  }
  if (result.dryRun) {
    process.stdout.write(`[dry-run] merge-chapters: sources=${result.files.length}, output=${result.output}, charsWithoutSpace≈${result.nonWhitespaceChars}；该数字按合章结果统计，不等同于逐章台账或扩写检查口径。\n`);
    return;
  }
  if (result.backup) process.stdout.write(`merge-chapters: 已备份既有输出 → ${result.backup}\n`);
  process.stdout.write(`merge-chapters: done sources=${result.files.length}, output=${result.output}, charsWithoutSpace≈${result.nonWhitespaceChars}；合章统计覆盖最终文件全文，可能不同于章节台账的单行记录。\n`);
  if (result.artifactPath) process.stdout.write('merge-chapters: metadata written → .doubao-book-writer/merge-chapters.last.json\n');
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();
