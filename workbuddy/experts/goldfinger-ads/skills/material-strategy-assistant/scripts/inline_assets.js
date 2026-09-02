#!/usr/bin/env node
/**
 * inline_assets.js —— 把 HTML 里所有本地图片引用转成 base64 data URI 内联，保证换任何模型/机器/PDF引擎都不丢图。
 *
 * 解决的三类丢图根因：
 *   ① 相对路径断裂 / 忘记把 case_samples 图复制到输出目录 → 内联后不依赖任何外部文件
 *   ② PDF 引擎（wkhtmltopdf/低版本 weasyprint）不认 webp → 默认把 webp 转成 png 再内联（需 sips 或 sharp，任一可用即可）
 *   ③ 中文文件名未 URL 编码导致解析失败 → 内联后不再经过路径解析
 *
 * 用法：
 *   node inline_assets.js <input.html> [output.html]
 *   - 不传 output 时，默认写到 <input>.inlined.html（同目录）
 *   - PDF 应从 output(.inlined.html) 打印，而不是原 HTML
 *
 * 覆盖的引用形式：<img src="...">、CSS url(...)（含 style 属性与 <style> 块）。
 * 只处理本地相对/绝对文件路径；http(s)、data: 原样跳过。
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// skill 根目录（本脚本在 scripts/ 下）：案例图（case_samples）运行时由 fetch_case_samples.js 落地到输出目录；
// 若输出目录缺失，回退到 skill 内置的 assets/ 兜底，避免 [MISS] 丢图。
const SKILL_ROOT = path.resolve(__dirname, '..');

const MIME = { '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.gif':'image/gif', '.svg':'image/svg+xml', '.webp':'image/webp' };

function toPngIfWebp(absPath) {
  // 尝试把 webp 转 png（兼容 wkhtmltopdf 等不认 webp 的引擎）。转换失败则回退用原 webp。
  // 🚨 同时限制最大宽度 900px：这些图是版式示意图，原始分辨率转 PNG 会膨胀 3-5 倍，导致 PDF 数 MB 级臃肿；限制宽度后体积可控且打印清晰度足够。
  if (path.extname(absPath).toLowerCase() !== '.webp') return { file: absPath, mime: MIME[path.extname(absPath).toLowerCase()] || 'application/octet-stream' };
  const out = absPath.replace(/\.webp$/i, '.__inlined.png');
  // 优先 macOS 自带 sips（转 png 并缩到 ≤900px 宽）
  try { execSync(`sips -s format png --resampleWidth 900 ${JSON.stringify(absPath)} --out ${JSON.stringify(out)}`, { stdio: 'ignore' }); if (fs.existsSync(out)) return { file: out, mime: 'image/png', tmp: out }; } catch (_) {}
  // 其次尝试 sharp（若已装在 node workspace）
  try {
    const sharp = require('sharp');
    sharp(absPath).png().toFile(out); // 同步性对小图足够；若异步失败下方 existsSync 兜底
    if (fs.existsSync(out)) return { file: out, mime: 'image/png', tmp: out };
  } catch (_) {}
  // 都不可用 → 直接内联 webp（Chrome 认，wkhtmltopdf 不认，但至少不因路径丢图）
  return { file: absPath, mime: 'image/webp' };
}

function encode(absPath) {
  const { file, mime, tmp } = toPngIfWebp(absPath);
  const b64 = fs.readFileSync(file).toString('base64');
  if (tmp) { try { fs.unlinkSync(tmp); } catch (_) {} }
  return `data:${mime};base64,${b64}`;
}

function main() {
  const input = process.argv[2];
  if (!input) { console.error('[USAGE] node inline_assets.js <input.html> [output.html]'); process.exit(1); }
  const inputAbs = path.resolve(input);
  const baseDir = path.dirname(inputAbs);
  const output = process.argv[3] ? path.resolve(process.argv[3]) : inputAbs.replace(/\.html?$/i, '') + '.inlined.html';

  let html = fs.readFileSync(inputAbs, 'utf8');
  let done = 0, miss = 0;
  const cache = new Map();

  const resolveRef = (raw) => {
    let ref = raw.trim().replace(/^['"]|['"]$/g, '');
    if (/^(https?:|data:|#|mailto:)/i.test(ref)) return null; // 外链/内联/锚点跳过
    const decoded = decodeURIComponent(ref);
    let abs = path.isAbsolute(decoded) ? decoded : path.resolve(baseDir, decoded);
    if (!fs.existsSync(abs)) {
      // 输出目录没有 → 回退 skill 内置 assets（case_samples 本地兜底副本），仍找不到才算 MISS
      const fb = path.resolve(SKILL_ROOT, decoded);
      if (decoded.startsWith('assets/') && fs.existsSync(fb)) { abs = fb; console.error(`[FALLBACK] 输出目录未找到 ${ref}，已回退 skill 内置副本`); }
    }
    if (!fs.existsSync(abs)) { miss++; console.error(`[MISS] 找不到本地文件，未内联：${ref}`); return null; }
    if (!MIME[path.extname(abs).toLowerCase()]) return null; // 非图片跳过
    if (!cache.has(abs)) cache.set(abs, encode(abs));
    done++;
    return cache.get(abs);
  };

  // <img src="...">
  html = html.replace(/(<img\b[^>]*?\bsrc\s*=\s*)(["'])(.*?)\2/gi, (m, pre, q, ref) => {
    const uri = resolveRef(ref); return uri ? `${pre}${q}${uri}${q}` : m;
  });
  // CSS url(...)（style 属性 + <style> 块通用）
  html = html.replace(/url\(\s*(['"]?)([^)'"]+)\1\s*\)/gi, (m, q, ref) => {
    const uri = resolveRef(ref); return uri ? `url(${q}${uri}${q})` : m;
  });

  fs.writeFileSync(output, html, 'utf8');
  console.log(`[RESULT] 已内联 ${done} 张图片${miss ? `，${miss} 个引用未找到（见上方 [MISS]）` : '，全部命中'} → ${output}`);
  process.exit(0);
}

main();
