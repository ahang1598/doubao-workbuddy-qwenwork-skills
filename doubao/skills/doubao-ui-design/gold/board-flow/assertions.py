#!/usr/bin/env python3
"""设计展板的验收断言。

这一份要证明的是**展板是一张给人看的方案图**，不是一页网页：
横向多帧、每帧有编号和中文步骤标签、帧与帧之间有指向关系，
帧内亮、帧外暗 —— 眼睛先看到界面，再顺着编号读下去。

展板按**它自己的画布宽度**验收，不按视口验收：
它本来就宽过一屏，拿 1600 去量"横向溢出"是判错了对象。
"""
from playwright.sync_api import sync_playwright
import sys

URL = "http://localhost:8911/index.html"
checks, fails = [], []


def ck(name, ok, detail=""):
    checks.append((name, ok, detail))
    if not ok:
        fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch()
    # 先用一个大视口把整张展板装下，再量 —— 画布尺寸由内容决定。
    pg = b.new_page(viewport={"width": 3400, "height": 1200})
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(700)

    # ── 1 横向多帧，而且真的是"横排" ────────────────────────
    fr = pg.evaluate("""() => [...document.querySelectorAll('.frame')].map(e => {
      const r = e.getBoundingClientRect();
      return {t: Math.round(r.top), l: Math.round(r.left),
              w: Math.round(r.width), h: Math.round(r.height)};
    })""")
    ck("帧数 >=4（一张展板要讲得完一条流程）", len(fr) >= 4, f"{len(fr)} 帧")
    if fr:
        tops = [f["t"] for f in fr]
        ck("所有帧在同一条水平线上（是横排不是竖排）",
           max(tops) - min(tops) <= 8, f"top 跨度 {max(tops) - min(tops)}px")
        lefts = sorted(f["l"] for f in fr)
        ck("帧沿横轴依次排开（相邻帧左边缘递增）",
           all(b > a for a, b in zip(lefts, lefts[1:])), str(lefts))

    # ── 2 每帧都有编号 + 中文步骤标签 ───────────────────────
    sn = pg.evaluate("""() => [...document.querySelectorAll('.sn')]
      .map(e => e.textContent.trim()).filter(Boolean)""")
    ck("每帧一个编号（数量与帧数一致）", len(sn) >= len(fr) and len(fr) > 0,
       f"编号 {len(sn)} / 帧 {len(fr)}")
    ck("编号是有序的（01 02 03…）",
       sn == sorted(sn), str(sn[:6]))

    cn = pg.evaluate("""() => [...document.querySelectorAll('.cap,.why,.s,.l')]
      .filter(e => /[\\u4e00-\\u9fa5]{2,}/.test(e.textContent || '')).length""")
    ck("帧上有中文步骤说明（>=帧数）", cn >= len(fr), f"{cn} 处")

    # ── 3 帧与帧之间有指向关系，不是并列摆着 ────────────────
    link = pg.evaluate("""() => document.querySelectorAll(
      '.ar,.arrow,.lk,.link,[data-arrow]').length""")
    ck("帧之间有连接/箭头（>=帧数-1）", link >= max(0, len(fr) - 1), f"{link} 条")

    # ── 4 帧内亮、帧外暗：眼睛先落到界面上 ──────────────────
    # 帧本身常常是透明的（它只是个定位盒），真正发亮的是里面那块界面。
    # `querySelector('.frame .shot,.frame')` 会先命中祖先 .frame ——
    # 量到 rgba(0,0,0,0) 就成了"帧内亮度 0"。所以量**帧内painted 面积最大的那块底色**。
    con = pg.evaluate("""() => {
      const lum = s => { const c = (s.match(/[\\d.]+/g) || [0, 0, 0]).map(Number);
        if (c.length > 3 && c[3] < 0.5) return null;
        return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255; };
      const page = lum(getComputedStyle(document.body).backgroundColor) || 0;
      const f = document.querySelector('.frame');
      if (!f) return [page, page];
      let best = 0, area = 0;
      f.querySelectorAll('*').forEach(c => {
        const r = c.getBoundingClientRect();
        const s = r.width * r.height;
        const l = lum(getComputedStyle(c).backgroundColor);
        if (l === null || s <= area) return;
        area = s; best = l;
      });
      return [page, best];
    }""")
    ck("帧外是暗场（底色明度 <=0.25）", con[0] <= 0.25, f"{con[0]:.3f}")
    ck("帧内比帧外亮（界面是主角）", con[1] > con[0], f"帧内 {con[1]:.3f} / 帧外 {con[0]:.3f}")

    # ── 5 展板整体不该有竖向长滚：它是一张图 ────────────────
    sh = pg.evaluate("() => document.documentElement.scrollHeight")
    ck("竖向不超过一屏半（展板是一张图，不是长页）", sh <= 1200 * 1.5, f"{sh}px")

    ck("无 JS 报错", not errs, str(errs[:3]))
    b.close()

for n, ok, d in checks:
    print(("  PASS  " if ok else "  FAIL  ") + n + (f"   → {d}" if d and not ok else ""))
print(f"\n{len(checks) - len(fails)}/{len(checks)} 通过")
sys.exit(1 if fails else 0)
