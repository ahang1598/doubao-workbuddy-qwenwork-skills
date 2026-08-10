#!/usr/bin/env node
// 长稿合章：极薄封装，调 core/merge-chapters.mjs 的 runMergeChapters，
// 把 manuscript/*.md 合并为单一交付稿（默认 deliverables/final.md）。
//
// 本封装对 runMergeChapters 的返回码做统一的三态映射，并保留一层 try/catch 兜底，
// 确保合章过程中的非致命异常不会让整个交付流程崩溃；不修改合章器本身。
//
// 参数 --workspace --output [--title <t>] [--glob <pattern>] [--dry-run]。
// exit code：0 通过 / 1 未找到章节或合并失败 / 2 参数或路径错误。

import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { runMergeChapters } from '../core/merge-chapters.mjs';

const DEFAULT_OUTPUT = 'deliverables/final.md';

function emit(payload, exitCode = 0) {
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(exitCode);
}

/**
 * 合并章节。
 * @param {{ workspace?: string, output?: string, title?: string|null, glob?: string|null, dryRun?: boolean }} options
 * @returns {{ status: 'pass'|'fail'|'error', code: number, ... }}
 */
export function mergeChapters({ workspace = process.cwd(), output = DEFAULT_OUTPUT, title = null, glob = null, dryRun = false } = {}) {
  const root = path.resolve(workspace);
  let result;
  try {
    result = runMergeChapters({ workspace: root, output, title, glob, dryRun });
  } catch (error) {
    // 兜底：snippet index 或其它非致命步骤抛错时，不让整个合章崩溃。
    return { status: 'error', stage: 'deliver', code: 2, failures: [error instanceof Error ? error.message : String(error)] };
  }

  const status = result.code === 0 ? 'pass' : result.code === 1 ? 'fail' : 'error';
  const payload = {
    status,
    stage: 'deliver',
    code: result.code,
    workspace: root,
    output: result.output || path.resolve(root, output),
    dryRun: Boolean(result.dryRun),
    sourceFileCount: Array.isArray(result.files) ? result.files.length : 0,
    files: Array.isArray(result.files)
      ? result.files.map(file => path.relative(root, file).split(path.sep).join('/'))
      : [],
    nonWhitespaceChars: result.nonWhitespaceChars ?? null,
  };
  if (result.message) payload.message = result.message;
  if (result.backup) payload.backup = result.backup;
  if (status !== 'pass') payload.failures = [result.message || `合章失败（code=${result.code}）`];
  return payload;
}

function parseArgs(argv) {
  const options = { workspace: process.cwd(), output: DEFAULT_OUTPUT, title: null, glob: null, dryRun: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = argv[++index];
    else if (token === '--output' || token === '-o') options.output = argv[++index];
    else if (token === '--title') options.title = argv[++index];
    else if (token === '--glob' || token === '-g') options.glob = argv[++index];
    else if (token === '--dry-run') options.dryRun = true;
    else if (token === '--help' || token === '-h') options.help = true;
  }
  return options;
}

function main() {
  const options = parseArgs(process.argv);
  if (options.help) {
    process.stdout.write('用法: node scripts/pipeline/merge_chapters.mjs --workspace <path> [--output deliverables/final.md] [--title <t>] [--glob <pattern>] [--dry-run]\n');
    return;
  }
  const result = mergeChapters(options);
  emit(result, result.code ?? (result.status === 'pass' ? 0 : 1));
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();
