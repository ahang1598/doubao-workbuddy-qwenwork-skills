#!/usr/bin/env node
// capture_site.mjs — real mobile screenshots of a live site, run on the LOCAL machine.
// Mobile full-page capture + dedicated section stills, used as the source of the
// screenshot overlay cards. Requires Playwright + Chromium:
//   npm i -g playwright && npx playwright install chromium
//
// Usage:
//   node capture_site.mjs <url> --out output/site_full.png                 # full page
//   node capture_site.mjs <url> --sections "评价,价格" --outdir output       # section stills
//
// Prints one JSON line per capture: {"kind":"full"|"section","label":...,"path":...}
// and exits non-zero if NOTHING could be captured (exit 3 = Playwright missing).
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";

async function loadPlaywright() {
  // A local install (this skill's folder or the cwd) wins; a global install is the
  // documented setup; PLAYWRIGHT_BROWSERS_PATH stays honoured if the caller set it.
  try { return await import("playwright"); } catch {}
  const roots = [process.env.NODE_PATH, path.join(process.cwd(), "node_modules")];
  try { roots.push(execSync("npm root -g", { encoding: "utf8" }).trim()); } catch {}
  for (const root of roots) {
    if (!root) continue;
    try { return createRequire(path.join(root, "x.js"))("playwright"); } catch {}
  }
  console.error(
    "playwright not found — install it first:\n" +
      "  npm i -g playwright && npx playwright install chromium\n" +
      "Then re-run this script. Do not report the capture as successful without it.",
  );
  process.exit(3);
}

const args = process.argv.slice(2);
const url = args.find((a) => !a.startsWith("--"));
const flag = (name, dflt) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : dflt;
};
if (!url) { console.error("usage: node capture_site.mjs <url> [--out file.png] [--sections 'A,B'] [--outdir dir]"); process.exit(2); }
const out = flag("out", "output/site_full.png");
const outdir = flag("outdir", "output");
const sections = (flag("sections", "") || "").split(",").map((s) => s.trim()).filter(Boolean);
// Keep Unicode letters (labels are often non-Latin); fall back to the index so
// two sections can never collapse into the same filename.
const slug = (s, i) => s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "_").replace(/^_+|_+$/g, "") || `s${i + 1}`;

const { chromium, devices } = await loadPlaywright();

// Best-effort cookie/consent dismissal — never fails the capture.
async function dismissOverlays(page) {
  const texts = /^(accept( all)?|agree|allow( all)?|got it|ok(ay)?|i (understand|agree|accept)|continue|reject all|no thanks)$/i;
  for (let round = 0; round < 2; round++) {
    for (const el of await page.locator("button, [role=button], a").all()) {
      try {
        const t = ((await el.textContent()) || "").trim();
        if (t.length <= 24 && texts.test(t) && (await el.isVisible())) { await el.click({ timeout: 1000 }); await page.waitForTimeout(400); break; }
      } catch {}
    }
  }
  // Google One Tap renders in a cross-origin iframe, so the text sweep above can
  // never reach it — and it lands right over the hero, i.e. over the one card that
  // has to read as the site. Network-blocked at context level (see below); this is
  // the DOM belt-and-braces for anything that still mounted.
  await page.evaluate(() => {
    const junk = "#credential_picker_container, #credential_picker_iframe, [id*=credential], iframe[src*='accounts.google.com'], iframe[src*='gsi']";
    for (const node of document.querySelectorAll(junk)) node.remove();
  }).catch(() => {});
}

// Scroll through the page so lazy-loaded content renders, then return to top.
// Real landings need a longer dwell than one animation frame: sections wired to
// IntersectionObserver paint a beat after they enter the viewport, and a fast pass
// leaves whole bands blank in the full-page shot (layout height, no content).
async function forceLazyLoad(page) {
  await page.evaluate(async () => {
    const step = 500;
    for (let y = 0; y < document.body.scrollHeight; y += step) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 260)); }
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise((r) => setTimeout(r, 400));
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(600);
}

// Absolute, document-relative rect of the first element matching a label — the
// stable way to crop a band out of the full-page PNG. Page height varies by up to
// ~14% between captures of the same URL, so a y-FRACTION drifts by hundreds of px;
// these coordinates do not. Zero-height rects are dropped: they resolve as "found"
// and then crop to nothing.
async function anchorRects(page, labels) {
  const out = {};
  for (const label of labels) {
    const rect = await page.evaluate((text) => {
      const wanted = text.toLowerCase();
      for (const node of document.querySelectorAll("h1, h2, h3, h4, strong, [role=tab], summary, button")) {
        if (!(node.textContent || "").toLowerCase().includes(wanted)) continue;
        const r = node.getBoundingClientRect();
        if (r.height <= 0) continue;
        return { top: Math.round(r.top + window.scrollY), height: Math.round(r.height), dpr: window.devicePixelRatio || 1 };
      }
      return null;
    }, label).catch(() => null);
    if (rect) out[label] = rect;
  }
  return out;
}

let browser;
try {
  browser = await chromium.launch({ args: ["--no-sandbox", "--disable-dev-shm-usage"] });
} catch (err) {
  console.error(`chromium failed to launch (${err.message}) — run: npx playwright install chromium`);
  process.exit(3);
}
try {
  const ctx = await browser.newContext({ ...devices["iPhone 13"] });
  // Kill Google One Tap before it can mount. Do NOT extend this to analytics
  // (googletagmanager): blocking that has been observed to break hydration and
  // return a single blank viewport with every anchor missing.
  await ctx.route(/accounts\.google\.com|gsi\/client/, (r) => r.abort()).catch(() => {});
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
  await dismissOverlays(page);
  await forceLazyLoad(page);

  let captured = 0;
  if (sections.length === 0) {
    mkdirSync(path.dirname(out), { recursive: true });
    await page.screenshot({ path: out, fullPage: true });
    // Print only once the file is actually on disk — a caller chaining `&&` off
    // this line used to race the PNG write and see "no such file".
    for (let i = 0; i < 40 && !existsSync(out); i++) await page.waitForTimeout(50);
    console.log(JSON.stringify({ kind: "full", path: out, exists: existsSync(out) }));
    captured++;
  } else {
    mkdirSync(outdir, { recursive: true });
    // Clickable controls (tabs/accordions) first, then plain headings/text (scroll only — clicking
    // a heading that is a link would navigate away). Skip matches that can't be scrolled to
    // (e.g. links hidden in a collapsed mobile nav) and try the next one.
    const scrollToSection = async (label) => {
      for (const g of [
        { sel: "[role=tab], summary, button, [role=button]", click: true },
        { sel: "h1, h2, h3, h4, strong", click: false },
      ]) {
        const matches = page.locator(g.sel, { hasText: label });
        const n = Math.min(await matches.count(), 5);
        for (let i = 0; i < n; i++) {
          const el = matches.nth(i);
          try {
            await el.scrollIntoViewIfNeeded({ timeout: 2500 });
            if (g.click) { await el.click({ timeout: 1200 }).catch(() => {}); await page.waitForTimeout(700); }
            // Centre the section in the viewport so surrounding site chrome stays in frame.
            await el.evaluate((node) => node.scrollIntoView({ block: "center" })).catch(() => {});
            await page.waitForTimeout(400);
            return true;
          } catch {}
        }
      }
      return false;
    };
    // Lazy sections sometimes need more than one pass: re-probe the anchors and
    // repeat the scroll-through (up to 3 rounds) while any label is still missing.
    let rects = await anchorRects(page, sections);
    for (let round = 0; round < 2 && Object.keys(rects).length < sections.length; round++) {
      await forceLazyLoad(page);
      rects = { ...rects, ...(await anchorRects(page, sections)) };
    }

    for (const [i, label] of sections.entries()) {
      if (await scrollToSection(label)) {
        const p = path.join(outdir, `section_${slug(label, i)}.png`);
        await page.screenshot({ path: p });                        // viewport shot, not full page
        for (let k = 0; k < 40 && !existsSync(p); k++) await page.waitForTimeout(50);
        // `rect` is document-absolute (CSS px) plus the DPR — crop bands from the
        // full-page PNG with rect.top*dpr, never with a y-fraction.
        console.log(JSON.stringify({ kind: "section", label, path: p, exists: existsSync(p), rect: rects[label] ?? null }));
        captured++;
      } else {
        console.log(JSON.stringify({ kind: "section", label, error: "not reachable" }));
      }
    }
  }
  if (captured === 0) { console.error("no captures succeeded"); process.exit(1); }
} finally {
  await browser.close();
}
