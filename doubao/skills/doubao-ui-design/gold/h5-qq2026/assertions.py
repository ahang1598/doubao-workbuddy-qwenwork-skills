#!/usr/bin/env python3
"""QQ 2026 H5 真机验收。案例 3 的投诉是「元素都是乱的，看不出什么东西」，
所以这里全部量运行时几何与可读性，不看源码、不看措辞。"""
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
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(3000)          # 等开机动画走完

    # 1. 恰好 10 屏，且每屏 = 一个视口高
    n = pg.eval_on_selector_all(".screen", "e=>e.length")
    ck("恰好 10 屏", n == 10, f"实际 {n}")
    hs = pg.eval_on_selector_all(".screen", "e=>e.map(x=>Math.round(x.getBoundingClientRect().height))")
    ck("每屏高度 = 视口高 844", all(abs(h - 844) <= 2 for h in hs), str(hs))

    # 2. 分屏滚动真的生效（snap 后 scrollTop 落在整数屏上）
    deck = "#deck"
    pg.eval_on_selector(deck, "d=>d.scrollTop=0")
    pg.click("#btnNext"); pg.wait_for_timeout(1100)
    st = pg.eval_on_selector(deck, "d=>d.scrollTop")
    ck("点『继续』翻到第 2 屏", abs(st - 844) <= 4, f"scrollTop={st}")
    ck("页码同步到 02", pg.inner_text("#pgNow") == "02", pg.inner_text("#pgNow"))

    # 3. 逐屏检查：无横向溢出 / 无元素超出屏底 / 文字不重叠 dock
    bad_overflow, bad_bottom = [], []
    for i in range(10):
        pg.evaluate(f"document.querySelectorAll('.screen')[{i}].scrollIntoView()")
        pg.wait_for_timeout(650)
        r = pg.evaluate("""() => {
          const sc=[...document.querySelectorAll('.screen')].find(s=>{
            const b=s.getBoundingClientRect(); return b.top>-40 && b.top<40;});
          if(!sc) return {miss:true};
          let ox=0, below=0;
          sc.querySelectorAll('*').forEach(e=>{
            const b=e.getBoundingClientRect();
            if(b.width===0||b.height===0) return;
            if(b.right>391.5||b.left<-1.5) ox++;
            // 正文不得被底部操作条（76px）盖住
            if(e.matches('h1,h2,p,.lead,.tagline,.num,.rank,.pill,.bub,.win') && b.bottom>844-70) below++;
          });
          return {ox,below};}""")
        if r.get("miss"):
            bad_overflow.append(f"p{i+1}:未定位")
        else:
            if r["ox"]:
                bad_overflow.append(f"p{i+1}:{r['ox']}个")
            if r["below"]:
                bad_bottom.append(f"p{i+1}:{r['below']}个")
    ck("10 屏均无横向溢出", not bad_overflow, ",".join(bad_overflow))
    ck("正文不被底部操作条压住", not bad_bottom, ",".join(bad_bottom))

    # 4. 每屏都有内容：文字量与元素数下限（防"空屏/错乱"）
    thin = pg.evaluate("""() => [...document.querySelectorAll('.screen')].map((s,i)=>({
        i:i+1, chars:s.innerText.replace(/\\s/g,'').length,
        els:s.querySelectorAll('div,p,h1,h2,span,svg').length}))
        .filter(o=>o.chars<28||o.els<6)""")
    ck("没有空屏（每屏正文 >= 28 字）", not thin, str(thin))

    # 5. 巨数字真的巨：每个数据屏至少一个 >= 48px 的数字
    # 视觉锚点：巨数字 *或* 大号展示元素（关键词屏、称号屏本来就没有数字，
    # 用「必须有数字」当硬门会判死这两种正当版式 —— 所以判据是"有没有主角"
    anchor = pg.evaluate("""() => [...document.querySelectorAll('.screen')].slice(1,9).map((s,i)=>{
        const es=[...s.querySelectorAll('.num,.stats2 b,.cloud b.s1,h2.big')]
          .map(n=>parseFloat(getComputedStyle(n).fontSize));
        return {p:i+2, max:es.length?Math.max(...es):0};}).filter(o=>o.max<30)""")
    ck("8 个数据屏都有 >= 30px 的视觉主角", not anchor, str(anchor))
    bignum = pg.evaluate("""() => [...document.querySelectorAll('.screen')].slice(1,9).filter(s=>
        [...s.querySelectorAll('.num,.stats2 b')].some(n=>parseFloat(getComputedStyle(n).fontSize)>=48)
      ).length""")
    ck("至少 5 个数据屏有 >= 48px 的巨数字", bignum >= 5, f"实际 {bignum}")

    # 6. 单位标签不是 4px（这是本轮真实修掉的 bug，留作回归）
    us = pg.evaluate("()=>[...document.querySelectorAll('.unit')].map(u=>parseFloat(getComputedStyle(u).fontSize))")
    ck("单位标签字号 >= 14px", us and min(us) >= 14, str(us))

    # 7. 最小字号：不得出现 <10px 的可见文字
    # .win-bar i 是 Win98 标题栏的 _ □ × 装饰字形，本来就该是 9px，豁免并写明理由
    tiny = pg.evaluate("""() => {const o=[];document.querySelectorAll('*').forEach(e=>{
        if(e.matches('.win-bar i')) return;
        if(!e.childNodes.length) return;
        const hasText=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
        if(!hasText) return; const s=getComputedStyle(e);
        if(s.visibility==='hidden'||s.opacity==='0') return;
        const f=parseFloat(s.fontSize); if(f<10) o.push(e.className+':'+f);});return o;}""")
    ck("无 <10px 的正文", not tiny, str(tiny[:4]))

    # 8. 结束页真的有分享入口
    pg.evaluate("document.querySelectorAll('.screen')[9].scrollIntoView()")
    pg.wait_for_timeout(800)
    share = pg.eval_on_selector_all("[data-share]", "e=>e.map(x=>x.innerText)")
    ck("结束页有 2 个分享动作", len(share) == 2, str(share))
    ck("结束页有二维码", pg.eval_on_selector("#qr svg rect", "e=>!!e") is True)
    pg.click('[data-share="friend"]')
    pg.wait_for_timeout(500)
    ck("点分享有反馈 toast", pg.eval_on_selector("#toast", "e=>e.classList.contains('on')"))

    # 9. 首屏开机动画真的结束了（不能把用户卡在黑屏）
    pg.evaluate("document.querySelectorAll('.screen')[0].scrollIntoView()")
    pg.wait_for_timeout(400)
    ck("开机遮罩已退场", pg.eval_on_selector("#boot", "e=>e.classList.contains('off')"))

    ck("无 JS 报错", not errs, str(errs[:3]))
    b.close()

for n, ok, d in checks:
    print(("  PASS  " if ok else "  FAIL  ") + n + (f"   → {d}" if d and not ok else ""))
print(f"\n{len(checks)-len(fails)}/{len(checks)} 通过")
sys.exit(1 if fails else 0)
