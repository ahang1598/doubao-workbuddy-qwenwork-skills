#!/usr/bin/env python3
"""「班次」产品界面原型的真机验收。

这一份 gold 的职责和另外三份不同：它要证明**产品界面不是幻灯片**。
所以断言的重心全在"点了会不会变"上——那是 trace 64 那份 5 屏 deck
唯一做不到的事（它也有按钮，点了只是换一屏"关于产品的说明"）。
"""
from playwright.sync_api import sync_playwright
import sys

URL = "http://localhost:8911/index.html"
checks, fails = [], []


def ck(name, ok, detail=""):
    checks.append((name, ok, detail))
    if not ok:
        fails.append(name)


SIG = """() => {
  const parts = [];
  document.querySelectorAll('*').forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.top > innerHeight || r.bottom < 0) return;
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.opacity === '0') return;
    parts.push([r.top|0, r.left|0, r.width|0, r.height|0, cs.backgroundColor].join(','));
  });
  return parts.join('|') + '##' + (document.body.innerText || '').slice(0, 4000);
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(900)

    # ── 1 首屏就是产品本身，不是封面页 ──────────────────────
    first = pg.evaluate("""() => [...document.querySelectorAll(
      'button,a[href],input,[role=button],[role=tab]')].filter(e=>{
        const r=e.getBoundingClientRect();
        return r.width>=20&&r.height>=20&&r.top<innerHeight&&r.bottom>0;}).length""")
    ck("首屏 >=3 个可操作元素（是产品不是封面）", first >= 3, f"{first} 个")

    meta = pg.evaluate("""() => {
      const M=/设计方案|改版后|全貌|关键屏|视觉语言|设计主张|封面页|结束页|设计总结/;
      return [...document.querySelectorAll('h1,h2,h3,h4,.eyebrow,.brand')]
        .filter(e=>{const r=e.getBoundingClientRect();
          return r.top<innerHeight&&r.bottom>0;})
        .map(e=>e.textContent.trim()).filter(t=>M.test(t));}""")
    ck("首屏 0 处元叙述词", not meta, str(meta))

    # 首屏第一眼要能回答"下一班几分钟后到" —— 产品的那句话
    ck("首屏就给出倒计时", pg.inner_text("#cMin").strip().isdigit(),
       pg.inner_text("#cMin"))

    # ── 2 三个真实状态切换，点了界面真的变 ──────────────────
    before = pg.evaluate(SIG)
    pg.click('.seg button[data-dir="home"]')
    pg.wait_for_timeout(420)
    after_dir = pg.evaluate(SIG)
    ck("切通勤方向：界面真的变了", after_dir != before)
    ck("切方向后线路跟着换", pg.inner_text("#rLine").strip() == "2 号线",
       pg.inner_text("#rLine"))
    ck("切方向有一句解释（toast）",
       pg.eval_on_selector("#toast", "e=>e.classList.contains('on')"))
    pg.click('.seg button[data-dir="work"]')
    pg.wait_for_timeout(420)

    before = pg.evaluate(SIG)
    pg.click(".plan .hd")
    pg.wait_for_timeout(460)
    ck("展开换乘方案：界面真的变了", pg.evaluate(SIG) != before)
    ck("展开后控件文案跟着状态走",
       pg.inner_text(".plan.open [data-toggle]").strip() == "收起",
       pg.inner_text(".plan.open [data-toggle]"))

    before = pg.evaluate(SIG)
    pg.click('.tabbar button[data-go="lines"]')
    pg.wait_for_timeout(420)
    ck("切底部 tab：界面真的变了", pg.evaluate(SIG) != before)
    ck("tab 选中态在变（这就是产品的位置表达）",
       pg.eval_on_selector('.tabbar button[data-go="lines"]',
                           "e=>e.classList.contains('on')"))
    ck("切 tab 后面板真的换了",
       pg.eval_on_selector('[data-panel="live"]', "e=>e.hidden") is True)
    pg.click('.tabbar button[data-go="live"]')
    pg.wait_for_timeout(420)

    # ── 3 不是年报的机箱 ────────────────────────────────────
    ck("没有分屏（产品首页是一条连续的流）",
       pg.eval_on_selector_all(".screen,[data-screen]", "e=>e.length") == 0)
    ck("没有『继续 / 上一页』三键条",
       pg.evaluate("""() => !/继续\\s*↓|上一页/.test(document.body.innerText)"""))
    ck("没有 N / M 页码",
       pg.evaluate("""() => ![...document.querySelectorAll('*')].some(e =>
         e.children.length<=2 && /^\\s*\\d{1,2}\\s*\\/\\s*\\d{1,2}\\s*$/
           .test(e.textContent||''))"""))

    # ── 4 副作用都有一句解释 ────────────────────────────────
    for sel, name in [("#btnRemind", "设提醒"), ("#btnFav", "收藏")]:
        pg.click(sel)
        pg.wait_for_timeout(320)
        ck(f"{name}有 toast 解释",
           pg.eval_on_selector("#toast", "e=>e.classList.contains('on')"))
        ck(f"{name}按钮文案响应状态",
           pg.inner_text(sel).strip() not in ("", "收藏" if name == "收藏" else ""),
           pg.inner_text(sel))
        pg.wait_for_timeout(1800)

    # ── 5 几何 ──────────────────────────────────────────────
    ck("底栏贴底", pg.eval_on_selector(
        ".tabbar", "e=>Math.abs(innerHeight-e.getBoundingClientRect().bottom)<=2"))
    ck("滚动容器给底栏留了位置", pg.evaluate(
        """() => parseFloat(getComputedStyle(document.getElementById('flow'))
             .paddingBottom) >= document.querySelector('.tabbar')
             .getBoundingClientRect().height - 6"""))
    ovf = pg.evaluate("()=>document.documentElement.scrollWidth-innerWidth")
    ck("无横向溢出", ovf <= 1, f"{ovf}px")

    ck("无 JS 报错", not errs, str(errs[:3]))
    b.close()

for n, ok, d in checks:
    print(("  PASS  " if ok else "  FAIL  ") + n + (f"   → {d}" if d and not ok else ""))
print(f"\n{len(checks)-len(fails)}/{len(checks)} 通过")
sys.exit(1 if fails else 0)
