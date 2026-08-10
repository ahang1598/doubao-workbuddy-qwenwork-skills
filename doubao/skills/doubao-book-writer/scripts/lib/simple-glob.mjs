import fs from 'node:fs';
import path from 'node:path';

// 零依赖 glob（替代原先对第三方 `glob` 包的依赖）。
// 只需支持本仓库实际用到的形态：
//   'manuscript/**/*.md'、'deliverables/**/*.md'、'**/*.md'、'sources/**/*'
// 选项：{ cwd, absolute, nodir, ignore }（ignore 为形如 '**/dir/**' 的字符串数组）。
// 语义：** 跨层，* 单层通配，扩展名精确匹配；返回按中文数字感知排序。

function segmentToRegex(segment) {
  // 把单个路径段的 glob 通配转成正则片段。* → [^/]*，? → [^/]
  let out = '';
  for (const ch of segment) {
    if (ch === '*') out += '[^/]*';
    else if (ch === '?') out += '[^/]';
    else out += ch.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return out;
}

function globToRegex(pattern) {
  // 先按 / 切段，处理 ** 跨层。
  const parts = String(pattern).split('/');
  let regex = '^';
  for (let i = 0; i < parts.length; i += 1) {
    const part = parts[i];
    const last = i === parts.length - 1;
    if (part === '**') {
      // ** 匹配零或多层目录（含其后的 /）。
      regex += '(?:.*/)?';
    } else {
      regex += segmentToRegex(part);
      if (!last) regex += '/';
    }
  }
  regex += '$';
  return new RegExp(regex);
}

function listAll(root) {
  // 返回 [{ full, rel, isDir }]，遍历整棵树。
  const result = [];
  const queue = [root];
  while (queue.length > 0) {
    const dir = queue.shift();
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      const rel = path.relative(root, full).split(path.sep).join('/');
      const isDir = entry.isDirectory();
      result.push({ full, rel, isDir });
      if (isDir) queue.push(full);
    }
  }
  return result;
}

export function globSync(pattern, options = {}) {
  const cwd = path.resolve(options.cwd || '.');
  const absolute = options.absolute === true;
  const nodir = options.nodir === true;
  const ignore = Array.isArray(options.ignore) ? options.ignore : options.ignore ? [options.ignore] : [];
  const patternRe = globToRegex(pattern);
  const ignoreRes = ignore.map(globToRegex);

  const matches = [];
  for (const item of listAll(cwd)) {
    if (nodir && item.isDir) continue;
    if (!patternRe.test(item.rel)) continue;
    if (ignoreRes.some((re) => re.test(item.rel))) continue;
    matches.push(absolute ? item.full : item.rel);
  }
  return matches.sort((left, right) => left.localeCompare(right, 'zh-Hans-CN', { numeric: true }));
}
