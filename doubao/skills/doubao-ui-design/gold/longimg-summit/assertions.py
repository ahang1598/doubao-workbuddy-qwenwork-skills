#!/usr/bin/env python3
"""活动长图的验收断言。

这一份要证明的是**长图不是把网页拉长**：
750 宽单栏纵向，首段能单独当封面被转发，
段与段之间换气方式要交替 —— 否则一路滚下去只有一个节奏。
"""
from playwright.sync_api import sync_playwright
import sys

URL = "http://localhost:8911/index.html"
W = 750
checks, fails = [], []


def ck(name, ok, detail=""):
    checks.append((name, ok, detail))
    if not ok:
        fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": W, "height": 1200})
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(700)

    # ── 1 单栏纵向，宽度就是 750，不横滚 ────────────────────
    box = pg.evaluate("""() => ({
      sw: document.documentElement.scrollWidth,
      sh: document.documentElement.scrollHeight, vw: innerWidth })""")
    ck("宽度 750 且不横滚", box["sw"] - box["vw"] <= 1, f"{box['sw']} vs {box['vw']}")
    ck("是长图（高 >= 3 个屏高）", box["sh"] >= 1200 * 3, f"{box['sh']}px")

    # ── 2 首段能单独当封面：一屏内讲得完，且有主标题 ────────
    seg = pg.evaluate("""() => [...document.querySelectorAll('.seg')].map(e => {
      const r = e.getBoundingClientRect();
      return Math.round(r.height);
    })""")
    ck("分段 >=4（长图靠分段给节奏）", len(seg) >= 4, f"{len(seg)} 段")
    if seg:
        ck("首段接近一屏（能单独当封面转发）",
           700 <= seg[0] <= 1400, f"首段 {seg[0]}px")

    head = pg.evaluate("""() => {
      const s = document.querySelector('.seg');
      if (!s) return 0;
      return [...s.querySelectorAll('*')].filter(e =>
        parseFloat(getComputedStyle(e).fontSize) >= 40
        && (e.textContent || '').trim().length >= 2).length;
    }""")
    ck("首段有 >=40px 的主标题", head >= 1, f"{head} 个")

    # ── 3 段与段之间要换气：相邻段不能是同一个模子 ──────────
    # 指纹只取"结构形状"，不取文案 —— 换了字不算换了版式。
    fp = pg.evaluate("""() => [...document.querySelectorAll('.seg')].map(s => {
      const kids = [...s.children].map(c => {
        const r = c.getBoundingClientRect();
        return c.tagName + ':' + Math.round(r.width / 50) + 'x' + Math.round(r.height / 50);
      });
      const bg = getComputedStyle(s).backgroundColor;
      return kids.join('|') + '##' + bg;
    })""")
    same = sum(1 for a, b2 in zip(fp, fp[1:]) if a == b2)
    ck("相邻段结构不全同（有换气）", same == 0, f"{same} 处相邻同构")

    # ── 4 长图是手机上看的：正文不能小 ──────────────────────
    tiny = pg.evaluate("""() => [...document.querySelectorAll('p,li,.txt,.s,.who,.org')]
      .filter(e => e.textContent.trim().length > 6
        && parseFloat(getComputedStyle(e).fontSize) < 20).length""")
    ck("正文 >=20px（750 宽长图在手机上是缩着看的）", tiny == 0, f"{tiny} 处")

    # ── 5 有真实视觉资产，不是纯文字排版 ────────────────────
    art = pg.evaluate("""() => document.querySelectorAll(
      'img,svg,canvas,[style*=background-image]').length""")
    ck("有视觉资产（>=6）", art >= 6, f"{art} 个")

    ck("无 JS 报错", not errs, str(errs[:3]))
    b.close()

for n, ok, d in checks:
    print(("  PASS  " if ok else "  FAIL  ") + n + (f"   → {d}" if d and not ok else ""))
print(f"\n{len(checks) - len(fails)}/{len(checks)} 通过")
sys.exit(1 if fails else 0)
