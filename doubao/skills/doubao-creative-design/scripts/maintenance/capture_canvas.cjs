#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const Module = require("module");
const { pathToFileURL } = require("url");

const argv = process.argv.slice(2);
const checkRuntime = argv[0] === "--check-runtime";
const [htmlPath, outputPath, widthRaw, heightRaw, scaleRaw, nodeModules, browserExecutable] = checkRuntime ? [] : argv;

function load(name) {
  const roots = [
    nodeModules,
    process.env.CREATIVE_DESIGN_NODE_MODULES,
    ...Module.globalPaths,
    "/opt/node_modules",
    "/workspace/node_modules",
    "/usr/local/lib/node_modules",
    "/usr/lib/node_modules",
    "/opt/homebrew/lib/node_modules",
  ].filter(Boolean);
  try {
    return require(name);
  } catch (error) {
    for (const root of roots) {
      try {
        return require(require.resolve(name, { paths: [root] }));
      } catch (_) {
        // Continue through the image-owned runtime locations.
      }
    }
    throw new Error(
      `RENDER_RUNTIME_MISSING: ${name} must be preinstalled in the execution image; ` +
      "do not run npm install or npx playwright install during a design task. " +
      "Set CREATIVE_DESIGN_NODE_MODULES only when the image exposes a non-standard module root."
    );
  }
}

const { chromium } = load("playwright");
const sharp = load("sharp");
const tileHeight = 8000;

function browserCandidates() {
  const system = process.platform === "darwin"
    ? [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
      ]
    : ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"];
  const bundled = typeof chromium.executablePath === "function" ? chromium.executablePath() : "";
  return [browserExecutable, process.env.CREATIVE_DESIGN_BROWSER, bundled, ...system].filter(Boolean);
}

function resolveBrowser() {
  return browserCandidates().find((candidate) => fs.existsSync(candidate)) || "";
}

if (checkRuntime) {
  const executable = resolveBrowser();
  if (!executable) {
    throw new Error(
      "RENDER_RUNTIME_MISSING: a Playwright-compatible Chromium must be preinstalled in the execution image; " +
      "do not download Chromium during a design task."
    );
  }
  process.stdout.write(JSON.stringify({ status: "ready", playwright: true, sharp: true, browser: executable }) + "\n");
  process.exit(0);
}

if (!htmlPath || !outputPath || !widthRaw || !heightRaw || !scaleRaw) {
  throw new Error("usage: capture_canvas.cjs HTML OUTPUT WIDTH HEIGHT SCALE [NODE_MODULES] [BROWSER]");
}

const requestedWidth = widthRaw === "auto" ? null : Number(widthRaw);
const requestedHeight = heightRaw === "auto" ? null : Number(heightRaw);
const scale = Number(scaleRaw);
if ([requestedWidth, requestedHeight].some(v => v !== null && (!Number.isSafeInteger(v) || v <= 0)) || !Number.isFinite(scale) || scale <= 0) {
  throw new Error("RENDER_DIMENSIONS: dimensions must be positive integers and scale positive finite");
}
if (path.resolve(htmlPath) === path.resolve(outputPath)) throw new Error("Output must not overwrite HTML source");

async function main() {
  const launch = { headless: true };
  const executable = resolveBrowser();
  if (!executable) {
    throw new Error(
      "RENDER_RUNTIME_MISSING: a Playwright-compatible Chromium must be preinstalled in the execution image; " +
      "do not download Chromium during a design task."
    );
  }
  launch.executablePath = executable;
  const browser = await chromium.launch(launch);
  let tempDir;
  try {
    const context = await browser.newContext({
      viewport: { width: requestedWidth || 1440, height: Math.min(requestedHeight || 900, tileHeight) },
      deviceScaleFactor: scale,
    });
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    await page.goto(pathToFileURL(path.resolve(htmlPath)).href, { waitUntil: "load", timeout: 30000 });
    const dimensions = await page.evaluate(async () => {
      const wait = Promise.all([
        document.fonts.ready,
        ...[...document.images].map(async image => {
          await image.decode();
          if (!image.naturalWidth) throw new Error("RENDER_IMAGE: empty image");
        }),
      ]);
      let timer;
      try {
        await Promise.race([wait, new Promise((_, reject) => {
          timer = setTimeout(() => reject(new Error("RENDER_ASSETS: loading timed out")), 30000);
        })]);
      } finally { clearTimeout(timer); }
      const html = document.documentElement;
      const w = html.getAttribute("data-canvas-width"), h = html.getAttribute("data-canvas-height");
      if (!/^[1-9]\d*$/.test(w || "") || !/^[1-9]\d*$/.test(h || "")) throw new Error("RENDER_DIMENSIONS: missing positive canvas attributes");
      const width = Number(w), height = Number(h), roots = document.querySelectorAll("body > main");
      if (!Number.isSafeInteger(width) || !Number.isSafeInteger(height) || roots.length !== 1) throw new Error("RENDER_ROOT: exactly one body > main required");
      for (const node of [html, document.body, roots[0]]) {
        const box = node.getBoundingClientRect(), css = getComputedStyle(node);
        if (node.style.width !== `${width}px` || node.style.height !== `${height}px` ||
            Math.abs(box.width - width) > 0.01 || Math.abs(box.height - height) > 0.01 ||
            css.transform !== "none" || !["1", "normal"].includes(css.zoom)) {
          throw new Error("RENDER_DIMENSIONS: html/body/main must have matching fixed px sizes without transforms");
        }
      }
      return { width, height };
    });
    const { width, height } = dimensions;
    if ((requestedWidth !== null && requestedWidth !== width) || (requestedHeight !== null && requestedHeight !== height)) {
      throw new Error("RENDER_DIMENSIONS: requested size differs from source canvas attributes");
    }
    await page.setViewportSize({ width, height: Math.min(height, tileHeight) });
    // Wait for CSS/SVG images too; they are not included in document.images.
    await page.evaluate(async () => {
      const urls = new Set();
      for (const e of document.querySelectorAll("*")) {
        const css = getComputedStyle(e);
        for (const value of [css.backgroundImage, css.maskImage, css.borderImageSource]) {
          for (const match of value.matchAll(/url\(["']?(.*?)["']?\)/g)) if (match[1] && !match[1].startsWith("#")) urls.add(match[1]);
        }
        if (e instanceof SVGImageElement && e.href.baseVal && !e.href.baseVal.startsWith("#")) urls.add(new URL(e.href.baseVal, document.baseURI).href);
      }
      await Promise.all([...urls].map(url => new Promise((resolve, reject) => {
        const image = new Image();
        const timer = setTimeout(() => reject(new Error("RENDER_IMAGE: timed out " + url)), 30000);
        image.onload = () => { clearTimeout(timer); resolve(); };
        image.onerror = () => { clearTimeout(timer); reject(new Error("RENDER_IMAGE: failed " + url)); };
        image.src = url;
      })));
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    const root = await page.locator("body > main").boundingBox();
    if (!root || Math.abs(root.width - width) > 0.01 || Math.abs(root.height - height) > 0.01) throw new Error("RENDER_DIMENSIONS: root size changed");
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "canvas-html-tiles-"));
    const tiles = [];
    const session = await context.newCDPSession(page);
    try {
      for (let y = 0, index = 0; y < height; y += tileHeight, index += 1) {
        const cssHeight = Math.min(tileHeight, height - y);
        const tile = path.join(tempDir, `tile-${String(index).padStart(4, "0")}.png`);
        // Playwright's screenshot wrapper clips to the viewport before calling CDP.
        const screenshot = await session.send("Page.captureScreenshot", {
          format: "png",
          fromSurface: true,
          clip: { x: root.x, y: root.y + y, width, height: cssHeight, scale: 1 },
          captureBeyondViewport: true,
        });
        fs.writeFileSync(tile, Buffer.from(screenshot.data, "base64"));
        tiles.push({ input: tile, top: Math.round(y * scale), left: 0 });
      }
    } finally { await session.detach(); }
    const pixelWidth = Math.round(width * scale);
    const pixelHeight = Math.round(height * scale);
    await sharp({
      create: { width: pixelWidth, height: pixelHeight, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } },
    }).composite(tiles).png().toFile(path.resolve(outputPath));
  } finally {
    try { await browser.close(); }
    finally { if (tempDir) fs.rmSync(tempDir, { recursive: true, force: true }); }
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
