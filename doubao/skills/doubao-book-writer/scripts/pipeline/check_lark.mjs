#!/usr/bin/env node
// 飞书读回校验：比对本地交付 Markdown 与从飞书读回的文档内容（xml 或 md）。
//
// 只做内容一致性校验，不含任何交付操作证明（operation-proof 状态机仪式）：
//   - 占位符检测：本地与读回都不得残留 TODO/TBD/{{...}}/[待补...] 等。
//   - 标题一致性：本地每个 Markdown 标题都应在读回文本中出现。
//   - 覆盖率：本地正文的 4-gram 有多少比例出现在读回文本中，低于阈值即阻断。
//
// textCoverage/visibleText/comparableText/ngrams/decodeEntities/markdownHeadings/
// placeholderHits 与 PLACEHOLDERS 逐字搬自 delivery/check-lark-doc.mjs 的对应导出/内部函数，
// 保持判定口径一致；此处不引入 check-lark-doc.mjs 本体，以免连带其 operation-proof 依赖。
//
// 参数 --markdown --fetched [--min-coverage 0.85] [--workspace <path>] [--write-report]。
// 产物 .doubao-book-writer/reports/lark_check.json。
// exit code：0 通过 / 1 阻断 / 2 环境或参数错误。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPORT_RELATIVE = ['.doubao-book-writer', 'reports', 'lark_check.json'];

// —— 以下为从 check-lark-doc.mjs 搬入的内容校验纯函数（保持逻辑一致）——
const PLACEHOLDERS = [
  /\bTODO\b/gi,
  /\bTBD\b/gi,
  /\{\{[^}\r\n]+\}\}/g,
  /\[(?:待补|待完善|待核实)[^\]\r\n]*\]/g,
  /待核实-MAT-[A-Za-z0-9-]+/gi,
  /MAT-[A-Za-z0-9-]+（待补充）/gi,
  /\[DISCARDED-[^\]\r\n]+\]/gi,
];

function decodeEntities(text) {
  return text
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&#(\d+);/g, (_, value) => String.fromCodePoint(Number(value)));
}

/** 去除 HTML 标签、Markdown 标记与代码围栏，抽取可读正文文本。 */
export function visibleText(content) {
  return decodeEntities(String(content || ''))
    .replace(/<script\b[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/```[A-Za-z0-9_-]*|```/g, ' ')
    .replace(/[*_~`>|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function comparableText(content) {
  return visibleText(content).toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
}

function ngrams(text, size = 4) {
  if (text.length <= size) return text ? new Set([text]) : new Set();
  const values = new Set();
  for (let index = 0; index <= text.length - size; index++) values.add(text.slice(index, index + size));
  return values;
}

/** 本地正文 4-gram 有多少比例出现在读回文本中；本地为空返回 0。 */
export function textCoverage(markdown, fetched) {
  const source = ngrams(comparableText(markdown));
  const target = ngrams(comparableText(fetched));
  if (source.size === 0) return 0;
  let matched = 0;
  for (const value of source) if (target.has(value)) matched++;
  return matched / source.size;
}

function markdownHeadings(content) {
  return String(content)
    .split(/\r?\n/)
    .map(line => line.match(/^#{1,6}\s+(.+?)\s*#*\s*$/)?.[1])
    .filter(Boolean)
    .map(value => comparableText(value));
}

function placeholderHits(content) {
  const hits = [];
  for (const pattern of PLACEHOLDERS) {
    const matches = String(content).match(pattern);
    if (matches) hits.push(...matches.slice(0, 5));
  }
  return [...new Set(hits)];
}
// —— 搬入结束 ——

function readNonEmpty(filePath) {
  if (!filePath || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) return null;
  const content = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
  return content.trim() ? content : null;
}

/** 从 markdown 路径向上查找含 .doubao-book-writer 的目录，作为默认 workspace。 */
function inferWorkspace(markdownPath) {
  let current = path.dirname(path.resolve(markdownPath));
  for (;;) {
    if (fs.existsSync(path.join(current, '.doubao-book-writer'))) return current;
    const parent = path.dirname(current);
    if (parent === current) return path.dirname(path.resolve(markdownPath));
    current = parent;
  }
}

function emit(payload, exitCode = 0) {
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(exitCode);
}

/**
 * 执行飞书读回内容校验。
 * @param {{ markdownPath: string, fetchedPath: string, minCoverage?: number, workspace?: string|null, writeReport?: boolean }} options
 */
export function checkLark({ markdownPath, fetchedPath, minCoverage = 0.85, workspace = null, writeReport = false } = {}) {
  const failures = [];
  if (!markdownPath) return { status: 'error', stage: 'deliver', code: 2, failures: ['缺少 --markdown'] };
  if (!fetchedPath) return { status: 'error', stage: 'deliver', code: 2, failures: ['缺少 --fetched'] };

  const markdown = readNonEmpty(markdownPath);
  if (!markdown) failures.push(`本地 Markdown 缺失或为空：${markdownPath}`);
  const fetched = readNonEmpty(fetchedPath);
  if (!fetched) failures.push(`读回文档缺失或为空：${fetchedPath}`);

  const markdownPlaceholders = markdown ? placeholderHits(markdown) : [];
  if (markdownPlaceholders.length) failures.push(`本地 Markdown 含占位符：${markdownPlaceholders.join(', ')}`);
  const fetchedPlaceholders = fetched ? placeholderHits(fetched) : [];
  if (fetchedPlaceholders.length) failures.push(`读回文档含占位符：${fetchedPlaceholders.join(', ')}`);

  let coverage = 0;
  let missingHeadings = [];
  if (markdown && fetched) {
    const fetchedComparable = comparableText(fetched);
    missingHeadings = markdownHeadings(markdown).filter(heading => heading && !fetchedComparable.includes(heading));
    if (missingHeadings.length) failures.push(`读回文档缺少 ${missingHeadings.length} 个本地 Markdown 标题`);
    coverage = textCoverage(markdown, fetched);
    if (coverage < minCoverage) failures.push(`内容覆盖率 ${coverage.toFixed(4)} 低于阈值 ${minCoverage}`);
  }

  const status = failures.length === 0 ? 'pass' : 'fail';
  const payload = {
    status,
    stage: 'deliver',
    code: status === 'pass' ? 0 : 1,
    markdownPath: path.resolve(markdownPath),
    fetchedPath: path.resolve(fetchedPath),
    minCoverage,
    coverage: Number(coverage.toFixed(4)),
    missingHeadingCount: missingHeadings.length,
    markdownPlaceholders,
    fetchedPlaceholders,
    failures,
  };
  if (failures.length > 0) payload.fix = '按 failures 修复飞书文档内容后重跑 make deliver。';

  if (writeReport) {
    const root = workspace ? path.resolve(workspace) : inferWorkspace(markdownPath);
    const reportPath = path.join(root, ...REPORT_RELATIVE);
    fs.mkdirSync(path.dirname(reportPath), { recursive: true });
    fs.writeFileSync(reportPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
    payload.reportPath = reportPath;
  }

  return payload;
}

function parseArgs(argv) {
  const options = { minCoverage: 0.85, writeReport: false, workspace: null };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--markdown') options.markdownPath = argv[++index];
    else if (token === '--fetched') options.fetchedPath = argv[++index];
    else if (token === '--min-coverage') options.minCoverage = Number(argv[++index]);
    else if (token === '--workspace') options.workspace = argv[++index];
    else if (token === '--write-report') options.writeReport = true;
    else if (token === '--help' || token === '-h') options.help = true;
  }
  return options;
}

function main() {
  const options = parseArgs(process.argv);
  if (options.help) {
    process.stdout.write('用法: node scripts/pipeline/check_lark.mjs --markdown <local.md> --fetched <fetched.xml|md> [--min-coverage 0.85] [--workspace <path>] [--write-report]\n');
    return;
  }
  try {
    const result = checkLark(options);
    emit(result, result.code ?? (result.status === 'pass' ? 0 : 1));
  } catch (error) {
    emit({ status: 'error', stage: 'deliver', code: 2, failures: [error instanceof Error ? error.message : String(error)] }, 2);
  }
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();
