import fs from 'node:fs';
import path from 'node:path';

// 章节 Markdown 枚举：按目录深度限制递归收集书稿里的 .md，跳过状态与依赖目录。
// 供台账真值校验等按章定位文件；只做文件发现，不解析章节依赖。

const MAX_RECURSION_DEPTH = 8;
const IGNORED_DIRS = new Set(['.git', '.doubao-book-writer', 'node_modules']);

function listDirSafe(directory) {
  try {
    return fs.readdirSync(directory, { withFileTypes: true });
  } catch {
    return [];
  }
}

/**
 * 收集 root 下的章节 Markdown 绝对路径（按中文自然序排序）。
 * options.recursive=false 只看首层；options.maxDepth 覆盖默认深度上限。
 */
export function listChapterMarkdown(root, options = {}) {
  const base = path.resolve(root);
  if (!fs.existsSync(base)) return [];
  const recursive = options.recursive !== false;
  const depthCap = Number.isInteger(options.maxDepth) ? options.maxDepth : MAX_RECURSION_DEPTH;

  const found = [];
  const frontier = [{ dir: base, depth: 0 }];
  for (let cursor = 0; cursor < frontier.length; cursor += 1) {
    const { dir, depth } = frontier[cursor];
    for (const entry of listDirSafe(dir)) {
      const full = path.join(dir, entry.name);
      if (entry.isFile()) {
        if (path.extname(entry.name).toLowerCase() === '.md') found.push(full);
      } else if (recursive && entry.isDirectory() && depth < depthCap && !IGNORED_DIRS.has(entry.name)) {
        frontier.push({ dir: full, depth: depth + 1 });
      }
    }
    if (!recursive) break;
  }
  return found.sort((left, right) => left.localeCompare(right, 'zh-Hans-CN', { numeric: true }));
}
