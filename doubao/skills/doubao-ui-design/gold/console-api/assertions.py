#!/usr/bin/env python3
"""API 监控台的验收断言。

这一份要证明的是**B 端工作台的正确形态**，它和影像驱动的稿正好相反：
满屏是图反而是错的，密度与状态齐全才是对的。

每一条都对着 `rubric.md` 右边那一列（扣分判断）写：
  · 做成普通列表页 / 看不出主体是调用情况   → 1 数据主体
  · 数据单纯罗列没有图表 / 数字与名称混淆   → 2 一个数配一个说明 + 图表
  · 没有异常与告警                          → 3 告警板块
  · 关键状态缺失                            → 4 四种状态
  · 横向滚动 / 按钮太小 / 正文不可读        → 5 界面细节
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
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(700)

    # ── 1 主体是"调用情况"，不是一张普通列表 ────────────────
    # 词表按**这一类页面真的会用的词**取，不要凭印象列同义词：
    # 同一个意思有很多说法（延迟/耗时、成功率/错误率），
    # 列窄了会把正确的稿判成"跑题"。
    txt = pg.inner_text("body")
    hit = [w for w in ("调用", "API", "接口", "请求", "耗时", "错误",
                       "告警", "异常", "流量", "成功率", "延迟") if w in txt]
    ck("主体是 API 调用数据（术语命中 >=5）", len(hit) >= 5, f"{len(hit)} 个：{hit}")

    # ── 2 一个数配一个说明；且有图表，不是纯数字罗列 ────────
    # 只量**头条数字**（>=20px）。表格里、坐标轴上的小数字本来就靠列头说明，
    # 拿"每个 .num 都要有相邻文字"去要求它们，是把一份正确的稿判成缺陷。
    m = pg.evaluate("""() => ({
      big: [...document.querySelectorAll('.num')]
        .filter(e => parseFloat(getComputedStyle(e).fontSize) >= 20).length,
      labelled: [...document.querySelectorAll('.num')]
        .filter(e => parseFloat(getComputedStyle(e).fontSize) >= 20)
        .filter(e => {
          const box = e.closest('.card,.panel,.cell,li,td,div');
          return box && (box.innerText || '').replace(e.innerText, '').trim().length >= 2;
        }).length,
      charts: document.querySelectorAll('svg,canvas,.bar,.track,.spark').length,
    })""")
    ck("头条数字都有文字说明（数字不与名称混淆）",
       m["big"] >= 3 and m["labelled"] == m["big"],
       f"{m['labelled']}/{m['big']}")
    ck("有图表，不是纯数字罗列（>=6 个图形元素）", m["charts"] >= 6, str(m["charts"]))

    # ── 3 告警/异常必须有，且不是一句话带过 ─────────────────
    alarm = pg.evaluate("""() => [...document.querySelectorAll('*')].filter(e =>
      /告警|异常|预警/.test(e.textContent || '') &&
      e.getBoundingClientRect().height > 60).length""")
    ck("有成块的告警/异常区（不是一句话带过）", alarm >= 1, f"{alarm} 块")

    # ── 4 四种关键状态齐全：这是 B 端与展示页最大的区别 ──────
    states = pg.evaluate("() => (window.__UI_CAPTURE__ && window.__UI_CAPTURE__.states || [])"
                         ".map(s => s.id)")
    for want in ("empty", "loading", "error"):
        ck(f"声明了 {want} 状态", want in states, str(states))
    ck("状态数 >=4（有数据 / 空 / 加载 / 异常…）", len(states) >= 4, str(len(states)))

    # 声明了还要真的能切过去，且切过去画面确实变了
    sig = "() => (document.body.innerText || '').slice(0, 3000)"
    base = pg.evaluate(sig)
    changed = 0
    for i in range(len(states)):
        pg.evaluate(f"async () => {{ const m = window.__UI_CAPTURE__;"
                    f" if (m.reset) await m.reset();"
                    f" const s = m.states[{i}]; if (s.go) await s.go(); }}")
        pg.wait_for_timeout(260)
        if pg.evaluate(sig) != base:
            changed += 1
    ck("声明的状态点过去画面真的变了（>=3 个）", changed >= 3, f"{changed} 个")

    # ── 5 界面细节：亮场、不溢出、按钮够大、正文可读 ─────────
    pg.evaluate("async () => { const m = window.__UI_CAPTURE__;"
                " if (m.reset) await m.reset(); }")
    pg.wait_for_timeout(200)
    lum = pg.evaluate("""() => {
      const c = getComputedStyle(document.body).backgroundColor.match(/[\\d.]+/g).map(Number);
      return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255;
    }""")
    ck("亮场工作台（底色明度 >=0.6）", lum >= 0.6, f"{lum:.2f}")

    ovf = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
    ck("1440 下无横向溢出", ovf <= 1, f"{ovf}px")

    small = pg.evaluate("""() => [...document.querySelectorAll(
      'button,a[href],[role=button],[role=tab]')].filter(e => {
        const r = e.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && (r.width < 24 || r.height < 24);
      }).length""")
    ck("可点元素都 >=24px", small == 0, f"{small} 个偏小")

    tiny = pg.evaluate("""() => [...document.querySelectorAll('p,li,td,dd,.v,.body')]
      .filter(e => e.textContent.trim().length > 8
        && parseFloat(getComputedStyle(e).fontSize) < 12).length""")
    ck("正文没有 <12px 的", tiny == 0, f"{tiny} 处")

    ck("无 JS 报错", not errs, str(errs[:3]))
    b.close()

for n, ok, d in checks:
    print(("  PASS  " if ok else "  FAIL  ") + n + (f"   → {d}" if d and not ok else ""))
print(f"\n{len(checks) - len(fails)}/{len(checks)} 通过")
sys.exit(1 if fails else 0)
