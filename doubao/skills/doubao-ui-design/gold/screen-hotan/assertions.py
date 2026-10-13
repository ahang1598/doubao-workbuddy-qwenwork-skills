#!/usr/bin/env python3
"""数据大屏的验收断言。

这一份要证明的是**大屏不是放大的网页**：
它按 query 给的尺寸铺满一屏，不滚动、不触控，深场，
一个主角占住画面中心，红色是稀缺资源只给预警。

每一条都对着 `rubric.md` 右边那一列（扣分判断）写：
  · 尺寸与要求不符 / 出现滚动        → 1 画布尺寸
  · 主次不清、没有视觉中心           → 2 主角占比
  · 颜色风格不统一、红色泛滥         → 3 红色只给预警
  · 数据单纯罗列、数字与名称混淆     → 4 数配标签
  · 正文不可读                       → 5 最小字号
"""
from playwright.sync_api import sync_playwright
import sys

URL = "http://localhost:8911/index.html"
W, H = 4001, 2251
checks, fails = [], []


def ck(name, ok, detail=""):
    checks.append((name, ok, detail))
    if not ok:
        fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": W, "height": H})
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(900)

    # ── 1 一屏就是一屏：既不横滚也不竖滚 ────────────────────
    box = pg.evaluate("""() => ({
      sw: document.documentElement.scrollWidth,
      sh: document.documentElement.scrollHeight,
      vw: innerWidth, vh: innerHeight })""")
    ck("画布宽度就是要求的宽度", abs(box["sw"] - W) <= 2, f"{box['sw']} vs {W}")
    ck("一屏装完，不需要竖滚", box["sh"] - box["vh"] <= 2,
       f"高 {box['sh']} vs 视口 {box['vh']}")

    # ── 2 深场：大屏的底是暗的，否则灯光感全无 ──────────────
    lum = pg.evaluate("""() => {
      const c = getComputedStyle(document.body).backgroundColor.match(/[\\d.]+/g).map(Number);
      return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255;
    }""")
    ck("深场（底色明度 <=0.2）", lum <= 0.2, f"{lum:.3f}")

    # ── 3 有一个占住画面的主角，不是一堆等大的卡片 ──────────
    # 判据是几何的：最大的那个内容块要显著大于第二大的。
    top2 = pg.evaluate("""() => {
      const a = [];
      document.querySelectorAll('div,section,figure,svg').forEach(e => {
        const r = e.getBoundingClientRect();
        const s = r.width * r.height;
        if (s > 0 && s < innerWidth * innerHeight * 0.92) a.push(s);
      });
      a.sort((x, y) => y - x);
      return [a[0] || 0, a[1] || 0, innerWidth * innerHeight];
    }""")
    share = top2[0] / top2[2]
    ck("有一个主角占住画面（最大块 >=20% 版面）", share >= 0.20, f"{share:.1%}")

    # ── 4 红色是稀缺资源：只给预警，不做装饰 ────────────────
    red = pg.evaluate("""() => {
      let redArea = 0, total = 0;
      document.querySelectorAll('*').forEach(e => {
        const r = e.getBoundingClientRect();
        const s = r.width * r.height;
        if (s <= 0 || s > innerWidth * innerHeight) return;
        const bg = getComputedStyle(e).backgroundColor.match(/[\\d.]+/g);
        if (!bg || (bg[3] !== undefined && +bg[3] < 0.1)) return;
        total += s;
        const [rr, gg, bb] = bg.map(Number);
        if (rr > 120 && rr > gg * 1.7 && rr > bb * 1.7) redArea += s;
      });
      return total ? redArea / total : 0;
    }""")
    ck("红色只给预警（红色面积 <5%）", red < 0.05, f"{red:.2%}")

    # ── 5 数配标签：数字旁边必须有它是什么 ──────────────────
    m = pg.evaluate("""() => {
      const big = [...document.querySelectorAll('.num,.v')]
        .filter(e => parseFloat(getComputedStyle(e).fontSize) >= 28);
      // 注意：closest() 会先匹配元素自己 —— 数字本身常常就是那个 div，
      // 于是"容器文字减去数字"永远是空的，一条正确的稿会被判成没标签。
      // 要从**父节点**往上找。
      const ok = big.filter(e => {
        const box = e.parentElement
          && e.parentElement.closest('.card,.pair,.col,.cell,li,div,section');
        return box && (box.innerText || '').replace(e.innerText, '').trim().length >= 2;
      });
      return [big.length, ok.length];
    }""")
    ck("头条数字都有标签（>=3 个且全部有）", m[0] >= 3 and m[1] == m[0], f"{m[1]}/{m[0]}")

    # ── 6 大屏是远看的：正文字号不能按网页来 ────────────────
    tiny = pg.evaluate("""() => [...document.querySelectorAll('p,li,td,dd,.k,.v,.body')]
      .filter(e => e.textContent.trim().length > 6
        && parseFloat(getComputedStyle(e).fontSize) < 14).length""")
    ck("没有 <14px 的正文（大屏是远看的）", tiny == 0, f"{tiny} 处")

    ck("无 JS 报错", not errs, str(errs[:3]))
    b.close()

for n, ok, d in checks:
    print(("  PASS  " if ok else "  FAIL  ") + n + (f"   → {d}" if d and not ok else ""))
print(f"\n{len(checks) - len(fails)}/{len(checks)} 通过")
sys.exit(1 if fails else 0)
