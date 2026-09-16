#!/usr/bin/env node
// Bake a short thumbnail headline into a generated image at the image's native size.
// The sandbox template provides global Playwright + Chromium.
//
// Usage:
//   node bake_text_overlay.mjs --image input.png --text-file headline.txt \
//     --style beast --position bottom --case upper --out output/thumbnail.png

import { execSync } from "node:child_process";
import { createRequire } from "node:module";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const USAGE = "usage: --image <path|https-url> (--text <2-6 words> | --text-file <path>) --out <png> [--style beast|fire|neon-lime|clean-glass|marker] [--position top|bottom|left|right|center] [--case upper|preserve]";

if (!process.env.PLAYWRIGHT_BROWSERS_PATH && existsSync("/ms-playwright")) {
  process.env.PLAYWRIGHT_BROWSERS_PATH = "/ms-playwright";
}

function loadPlaywright() {
  // 本地 IDE Agent 场景：优先脚本旁与当前工作目录的 node_modules，再回落到全局安装
  for (const base of [import.meta.url, path.join(process.cwd(), "x.js")]) {
    try { return createRequire(base)("playwright"); } catch {}
  }
  const roots = [process.env.NODE_PATH];
  try { roots.push(execSync("npm root -g", { encoding: "utf8" }).trim()); } catch {}
  for (const root of roots) {
    if (!root) continue;
    try { return createRequire(path.join(root, "x.js"))("playwright"); } catch {}
  }
  throw new Error("playwright 未安装。请执行 npm i -g playwright && npx playwright install chromium");
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "-h" || arg === "--help") {
      out.help = true;
      continue;
    }
    if (!arg.startsWith("--")) throw new Error(`unexpected argument: ${arg}`);
    const value = argv[++i];
    if (!value || value.startsWith("--")) throw new Error(`missing value for ${arg}`);
    out[arg.slice(2)] = value;
  }
  return out;
}

function mimeFor(filename, contentType = "") {
  if (contentType.startsWith("image/")) return contentType.split(";")[0];
  const ext = path.extname(filename).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  return "image/png";
}

async function imageDataUrl(source) {
  if (/^https:\/\//i.test(source)) {
    const response = await fetch(source, { redirect: "follow" });
    if (!response.ok) throw new Error(`image download failed: HTTP ${response.status}`);
    const body = Buffer.from(await response.arrayBuffer());
    return `data:${mimeFor(source, response.headers.get("content-type") || "")};base64,${body.toString("base64")}`;
  }
  if (!existsSync(source)) throw new Error(`image not found: ${source}`);
  return `data:${mimeFor(source)};base64,${readFileSync(source).toString("base64")}`;
}

const args = parseArgs(process.argv.slice(2));
if (args.help) {
  console.log(USAGE);
  process.exit(0);
}
const source = args.image;
if (args.text && args["text-file"]) throw new Error("use either --text or --text-file, not both");
const rawText = args["text-file"] ? readFileSync(args["text-file"], "utf8") : (args.text || "");
const text = rawText.trim().replace(/\s+/g, " ");
const output = args.out;
const style = args.style || "beast";
const position = args.position || "bottom";
const caseMode = args.case || "upper";
const styles = new Set(["beast", "fire", "neon-lime", "clean-glass", "marker"]);
const positions = new Set(["top", "bottom", "left", "right", "center"]);
const caseModes = new Set(["upper", "preserve"]);

if (!source || !text || !output) {
  throw new Error(USAGE);
}
// 中文标题没有空格，按字数校验；西文仍按词数
const isCjk = /[\u4e00-\u9fff\u3040-\u30ff]/u.test(text);
if (isCjk) {
  const charCount = [...text.replace(/\s+/gu, "")].length;
  if (charCount < 2 || charCount > 14) throw new Error(`中文标题需 2-14 字，当前 ${charCount} 字`);
} else {
  const wordCount = text.split(/\s+/u).length;
  if (wordCount < 2 || wordCount > 6) throw new Error(`headline must contain 2-6 words, got ${wordCount}`);
}
if (!styles.has(style)) throw new Error(`unknown style: ${style}`);
if (!positions.has(position)) throw new Error(`unknown position: ${position}`);
if (!caseModes.has(caseMode)) throw new Error(`unknown case mode: ${caseMode}`);

const dataUrl = await imageDataUrl(source);
const { chromium } = loadPlaywright();
const browser = await chromium.launch({ args: ["--no-sandbox", "--disable-dev-shm-usage"] });

try {
  const page = await browser.newPage();
  await page.setContent(`<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@800&family=Noto+Sans+SC:wght@900&display=swap"><canvas id="poster"></canvas>`);
  const result = await page.evaluate(async ({ dataUrl, headline, style, position, caseMode }) => {
    const timeout = new Promise((resolve) => setTimeout(resolve, 5000));
    await Promise.race([
      (async () => {
        await document.fonts.load(style === "clean-glass" ? '800 120px "Inter"' : '120px "Anton"');
        await document.fonts.load('900 120px "Noto Sans SC"');
        await document.fonts.ready;
      })(),
      timeout,
    ]);

    const image = new Image();
    image.src = dataUrl;
    await image.decode();

    const canvas = document.getElementById("poster");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;
    ctx.drawImage(image, 0, 0, W, H);

    const renderedHeadline = caseMode === "preserve" ? headline : headline.toLocaleUpperCase();
    const cjk = /[\u4e00-\u9fff\u3040-\u30ff]/u.test(renderedHeadline);
    const words = renderedHeadline.split(/\s+/u);
    let lines;
    if (cjk && words.length <= 2) {
      // 中文无空格：超过 6 字从中间断成两行
      const chars = [...renderedHeadline.replace(/\s+/gu, "")];
      lines = chars.length > 6
        ? [chars.slice(0, Math.ceil(chars.length / 2)).join(""), chars.slice(Math.ceil(chars.length / 2)).join("")]
        : [chars.join("")];
    } else if (words.length <= 3) {
      lines = [words.join(" ")];
    } else {
      let best = 1;
      let delta = Infinity;
      for (let i = 1; i < words.length; i++) {
        const next = Math.abs(words.slice(0, i).join(" ").length - words.slice(i).join(" ").length);
        if (next < delta) { best = i; delta = next; }
      }
      lines = [words.slice(0, best).join(" "), words.slice(best).join(" ")];
    }

    // 中文整条走同一个中文字族：Anton / Inter 无中文字形，混在栈里会按字逐个回退成不同字体
    const cjkStack = '"PingFang SC", "Noto Sans SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif';
    const fontFamily = cjk
      ? cjkStack
      : (style === "clean-glass" ? `"Inter", ${cjkStack}` : `"Anton", Impact, ${cjkStack}`);
    const maxWidth = position === "left" || position === "right" ? W * 0.46 : W * 0.88;
    let fontPx = Math.round(H * 0.17);
    const minFontPx = Math.round(H * 0.09);
    const fontWeight = cjk ? "900 " : (style === "clean-glass" ? "800 " : "");
    const setFont = () => { ctx.font = `${fontWeight}${fontPx}px ${fontFamily}`; };
    setFont();
    while (fontPx > minFontPx && Math.max(...lines.map((line) => ctx.measureText(line).width)) > maxWidth) {
      fontPx -= Math.max(1, Math.round(H * 0.005));
      setFont();
    }

    // 0.9 是为 Anton 大写字设计的紧行距；中文字形占满 em 框，需要更松
    const lineHeight = fontPx * (cjk ? 1.08 : 0.9);
    const blockHeight = lines.length * lineHeight;
    const marginX = W * 0.06;
    const marginY = H * 0.06;
    let x = W / 2;
    let firstBaseline = H - marginY - blockHeight + lineHeight;
    ctx.textAlign = "center";
    if (position === "top") firstBaseline = marginY + fontPx;
    if (position === "center") firstBaseline = H / 2 - blockHeight / 2 + lineHeight * 0.78;
    if (position === "left") {
      x = marginX + maxWidth / 2;
      firstBaseline = H / 2 - blockHeight / 2 + lineHeight * 0.78;
    }
    if (position === "right") {
      x = W - marginX - maxWidth / 2;
      firstBaseline = H / 2 - blockHeight / 2 + lineHeight * 0.78;
    }

    ctx.textBaseline = "alphabetic";
    ctx.lineJoin = "round";
    ctx.miterLimit = 2;

    for (const [index, line] of lines.entries()) {
      const y = firstBaseline + index * lineHeight;
      const metrics = ctx.measureText(line);
      const boxX = x - metrics.width / 2 - fontPx * 0.18;
      const boxY = y - fontPx * 0.86;
      const boxW = metrics.width + fontPx * 0.36;
      const boxH = fontPx * 1.02;

      if (style === "clean-glass" || style === "marker") {
        ctx.save();
        ctx.fillStyle = style === "marker" ? "#D4FF3F" : "rgba(20,20,25,.68)";
        ctx.shadowColor = "rgba(0,0,0,.5)";
        ctx.shadowBlur = style === "marker" ? 0 : Math.round(fontPx * 0.45);
        ctx.shadowOffsetY = Math.round(fontPx * 0.12);
        ctx.beginPath();
        ctx.roundRect(boxX, boxY, boxW, boxH, style === "marker" ? fontPx * 0.04 : fontPx * 0.2);
        ctx.fill();
        ctx.restore();
      }

      if (style !== "clean-glass" && style !== "marker") {
        ctx.save();
        ctx.shadowColor = style === "neon-lime" ? "rgba(180,255,40,.7)" : "rgba(0,0,0,.55)";
        ctx.shadowBlur = style === "neon-lime" ? Math.round(fontPx * 0.2) : Math.round(fontPx * 0.16);
        ctx.shadowOffsetY = Math.round(fontPx * 0.1);
        ctx.lineWidth = Math.round(fontPx * (style === "neon-lime" ? 0.1 : 0.11));
        ctx.strokeStyle = style === "fire" ? "#1a0a00" : style === "neon-lime" ? "#0a1400" : "#000";
        ctx.strokeText(line, x, y); // stroke FIRST: canvas equivalent of paint-order: stroke fill
        ctx.restore();
      }

      if (style === "fire") {
        const gradient = ctx.createLinearGradient(0, y - fontPx, 0, y);
        gradient.addColorStop(0, "#FFE24B");
        gradient.addColorStop(0.45, "#FF9A1F");
        gradient.addColorStop(1, "#FF2E2E");
        ctx.fillStyle = gradient;
      } else if (style === "neon-lime") {
        ctx.fillStyle = "#D4FF3F";
      } else if (style === "marker") {
        ctx.fillStyle = "#0a0a0a";
      } else {
        ctx.fillStyle = "#fff";
      }
      ctx.fillText(line, x, y); // fill AFTER stroke so the outline never eats the letters
    }

    return {
      png: canvas.toDataURL("image/png").split(",")[1],
      width: W,
      height: H,
      lines,
      fontReady: document.fonts.status === "loaded",
    };
  }, { dataUrl, headline: text, style, position, caseMode });

  mkdirSync(path.dirname(output), { recursive: true });
  writeFileSync(output, Buffer.from(result.png, "base64"));
  console.log(JSON.stringify({ output, style, position, text_case: caseMode, width: result.width, height: result.height, lines: result.lines, font_ready: result.fontReady }));
} finally {
  await browser.close();
}
