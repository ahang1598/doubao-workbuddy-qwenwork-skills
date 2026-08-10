import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// 质检工作面运行时。仅服务 doubao-book-writer 的深度质检（make quality）：
// 定位本包根目录、统计正文字符、必要时为裸书稿目录铺一个最小质检工作面。
// 命名与实现均独立于任何既有实现，只对齐本仓 pipeline 的调用契约。

// 扫描时跳过的目录名。集中在此，改一处即可全局生效。
const SKIP_DIRECTORY_NAMES = Object.freeze([
  '.doubao-book-writer',
  '.git',
  'node_modules',
  'dist',
  'qc-output',
  'releases',
]);

// 供外部扫描器复用的忽略 glob（如 machine 引擎的文件枚举）。
export const scanSkipGlobs = Object.freeze(
  SKIP_DIRECTORY_NAMES.map(name => `**/${name}/**`),
);

const SKIP_DIRECTORY_SET = new Set(SKIP_DIRECTORY_NAMES);

/** 目录名是否应在质检扫描中跳过。 */
export function isSkippedScanDir(name) {
  return SKIP_DIRECTORY_SET.has(name);
}

/** 把绝对路径转成相对 root 的正斜杠路径，便于跨平台稳定比较与展示。 */
export function normalizeRel(filePath, root) {
  const relative = path.relative(path.resolve(root), path.resolve(filePath));
  return relative.split(path.sep).join('/');
}

/** 统计非空白字符数（中文书稿字数口径，忽略所有空白）。 */
export function countChars(content) {
  const text = content == null ? '' : String(content);
  let count = 0;
  for (const ch of text) {
    if (!/\s/u.test(ch)) count += 1;
  }
  return count;
}

/** 从某个 import.meta.url 反推本包根目录（scripts/xxx/*.mjs -> 上两级）。 */
export function bundleRootFromUrl(importMetaUrl) {
  const here = path.dirname(fileURLToPath(importMetaUrl));
  return path.resolve(here, '..', '..');
}

// —— 以下为「裸书稿目录」自举所需的内部工具，均不导出 ——

function safeReadDir(directory) {
  try {
    return fs.readdirSync(directory, { withFileTypes: true });
  } catch {
    return [];
  }
}

function readUtf8(filePath) {
  return fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
}

// 广度优先枚举 root 下全部 .md，跳过 SKIP_DIRECTORY_NAMES 与调用方追加的目录。
function enumerateMarkdown(root, extraSkips = []) {
  const skip = new Set([...SKIP_DIRECTORY_NAMES, ...extraSkips]);
  const queue = [path.resolve(root)];
  const found = [];
  while (queue.length > 0) {
    const dir = queue.shift();
    for (const entry of safeReadDir(dir)) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (!skip.has(entry.name)) queue.push(full);
      } else if (entry.isFile() && path.extname(entry.name).toLowerCase() === '.md') {
        found.push(full);
      }
    }
  }
  found.sort((a, b) => normalizeRel(a, root).localeCompare(normalizeRel(b, root), 'zh-Hans-CN', { numeric: true }));
  return found;
}

function headingOrBasename(content, relPath) {
  for (const raw of String(content).split(/\r?\n/)) {
    const line = raw.trim();
    if (line.startsWith('# ')) return line.slice(2).trim();
  }
  return path.basename(relPath, path.extname(relPath));
}

// 把一批 .md 描述成质检清单条目。区域取顶层目录名，根下文件归入 root。
function describeFiles(files, root) {
  return files.map((filePath, order) => {
    const relPath = normalizeRel(filePath, root);
    const content = readUtf8(filePath);
    const topSegment = relPath.includes('/') ? relPath.split('/')[0] : 'root';
    return {
      id: `ch${String(order + 1).padStart(3, '0')}`,
      filePath,
      relPath,
      chars: countChars(content),
      group: topSegment,
      title: headingOrBasename(content, relPath),
      mtimeMs: fs.statSync(filePath).mtimeMs,
    };
  });
}

function tallyByArea(entries) {
  const areas = new Map();
  for (const entry of entries) {
    const key = entry.group || 'root';
    if (!areas.has(key)) areas.set(key, { count: 0, chars: 0, first: entry.relPath });
    const bucket = areas.get(key);
    bucket.count += 1;
    bucket.chars += entry.chars;
  }
  return areas;
}

function composeContextBrief(root, entries) {
  const areas = tallyByArea(entries);
  const totalChars = entries.reduce((sum, item) => sum + item.chars, 0);
  const lines = [];
  for (const [area, bucket] of areas) {
    lines.push(`| ${area} | ${bucket.count} | ${bucket.chars} | ${bucket.first || '—'} |`);
  }
  return [
    '# 存量书稿质检工作面',
    '',
    '> 由质检扫描器生成，只反映当前磁盘上的 Markdown，不代表已完成需求冻结。',
    '',
    `- root: \`${path.resolve(root).split(path.sep).join('/')}\``,
    `- markdownFiles: ${entries.length}`,
    `- charsWithoutSpace: ${totalChars}`,
    `- generatedAt: ${new Date().toISOString()}`,
    '',
    '## Area Inventory',
    '',
    '| area | files | chars | sample |',
    '|---|---:|---:|---|',
    lines.join('\n') || '| root | 0 | 0 | — |',
    '',
    '仅用于质量检查；正式创作请从 project-intake 起步。',
    '',
  ].join('\n');
}

function composeStatusLedger(entries) {
  const rows = entries.map(item =>
    `| ${item.id} | ${item.relPath} | ${item.group} | 待质检 | ${item.chars} | 扫描导入 |`);
  return [
    '# 存量书稿检查台账',
    '',
    '> 反映扫描结果，不替代正式写作阶段的状态台账。',
    '',
    `更新时间：${new Date().toISOString()}`,
    '',
    '| 编号 | 文件 | 区域 | 检查状态 | 字符数 | 来源 |',
    '|---|---|---|---|---:|---|',
    rows.join('\n') || '| ch001 | — | root | 待质检 | 0 | 无文件 |',
    '',
  ].join('\n');
}

function writeFileAtomic(filePath, content) {
  const staging = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(staging, content, 'utf8');
  fs.renameSync(staging, filePath);
}

/**
 * 为裸书稿目录铺最小质检工作面：建 .doubao-book-writer/ 与 qc-output/，
 * 缺失时生成上下文简报与检查台账。已存在则不覆盖（除非 force）。
 * 仅供深度质检在无 prepare 产物时兜底，不参与正式写作流程。
 */
export function prepareQualityScanSurface(workspace, options = {}) {
  const root = path.resolve(workspace);
  const stateDir = path.join(root, '.doubao-book-writer');
  const qcOutputDir = path.join(root, 'qc-output');
  fs.mkdirSync(stateDir, { recursive: true });
  fs.mkdirSync(qcOutputDir, { recursive: true });

  const files = options.files || enumerateMarkdown(root, options.ignoreDirs || []);
  const inventory = options.inventory || describeFiles(files, root);

  const contextPath = path.join(stateDir, 'book-context-brief.md');
  const statusPath = path.join(root, 'chapter-ledger.md');
  if (options.force || !fs.existsSync(contextPath)) {
    writeFileAtomic(contextPath, composeContextBrief(root, inventory));
  }
  if (options.force || !fs.existsSync(statusPath)) {
    writeFileAtomic(statusPath, composeStatusLedger(inventory));
  }
  return { workspace: root, stateDir, qcOutputDir, contextPath, statusPath, inventory };
}

/**
 * 定位质检词表/参考文件：优先本包根目录下的 sub-skills/revision-quality/references，
 * 回退到当前工作目录同名路径；两者都无则返回首选路径（由调用方处理缺失）。
 */
export function locateQualityReference(bundleRoot, fileName) {
  const base = path.resolve(bundleRoot || process.cwd());
  const preferred = path.join(base, 'sub-skills', 'revision-quality', 'references', fileName);
  if (fs.existsSync(preferred)) return preferred;
  const fallback = path.join(process.cwd(), 'sub-skills', 'revision-quality', 'references', fileName);
  return fs.existsSync(fallback) ? fallback : preferred;
}
