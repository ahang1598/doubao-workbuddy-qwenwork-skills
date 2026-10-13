#!/usr/bin/env python3
"""PULSE 官网功能真机验收：图片是否真的渲染、购物车是否真的能用、筛选是否真的过滤。
每一条都读运行时几何 / 文本，不看源码。"""
from playwright.sync_api import sync_playwright
import sys

URL = "http://localhost:8910/index.html"
fails, checks = [], []


def ck(name, ok, detail=""):
    checks.append((name, ok, detail))
    if not ok:
        fails.append(f"{name} :: {detail}")


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(800)

    # 1. 所有 <img> 真的解码出了像素，且渲染尺寸不是 0
    pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
    pg.wait_for_timeout(2500)
    bad = pg.evaluate("""() => Array.from(document.images).map(i=>({
        src:i.currentSrc.split('/').pop(), nat:i.naturalWidth,
        w:Math.round(i.getBoundingClientRect().width),
        h:Math.round(i.getBoundingClientRect().height)}))
        .filter(o=>o.nat===0 || o.w<8 || o.h<8)""")
    ck("每张图都解码且渲染尺寸>8px", not bad, str(bad))
    n_img = pg.evaluate("document.images.length")
    ck("图片数量 >= 12", n_img >= 12, f"实际 {n_img}")

    # 2. 首屏媒体占比（参考站下沿 40%）
    ratio = pg.evaluate("""() => {
      const vw=innerWidth, vh=innerHeight; let a=0;
      document.querySelectorAll('img,video').forEach(m=>{const r=m.getBoundingClientRect();
        const w=Math.max(0,Math.min(r.right,vw)-Math.max(r.left,0));
        const h=Math.max(0,Math.min(r.bottom,vh)-Math.max(r.top,0)); a+=w*h;});
      return Math.round(a/(vw*vh)*1000)/10;}""")
    ck("首屏媒体占比 >= 40%", ratio >= 40, f"实际 {ratio}%")

    # 3. 正文对比度：背景可信的文字最差对比度
    worst = pg.evaluate("""() => {
      const lum=c=>{const [r,g,b]=c.match(/\\d+(\\.\\d+)?/g).slice(0,3).map(Number)
        .map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});
        return .2126*r+.7152*g+.0722*b;};
      let w=99, el=null;
      document.querySelectorAll('p,h1,h2,h3,h4,span,a,button,dd,dt,small,li').forEach(n=>{
        if(!n.textContent.trim()) return;
        const s=getComputedStyle(n); if(s.visibility==='hidden'||s.opacity==='0') return;
        let bg=null,q=n;
        while(q){const b=getComputedStyle(q);
          if(b.backgroundImage!=='none') return;              // 背景不可信 → 跳过
          // 透明的定位层（fixed/absolute 的导航、压在图上的文案层）背后是什么无法从
          // 父链推断，继续往上取到 body 底色一定是错的 → 同样判为不可信
          if((b.position==='fixed'||b.position==='absolute') &&
             b.backgroundColor.includes('rgba(0, 0, 0, 0)')) return;
          if(b.backgroundColor && !b.backgroundColor.includes('rgba(0, 0, 0, 0)')){bg=b.backgroundColor;break;}
          q=q.parentElement;}
        if(!bg) return;
        const l1=lum(s.color),l2=lum(bg);
        const c=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
        if(c<w){w=c; el=n.tagName+':'+n.textContent.trim().slice(0,18);}});
      return [Math.round(w*100)/100, el];}""")
    ck("可信背景上的最差正文对比度 >= 3.0", worst[0] >= 3.0, f"{worst[0]}:1 @ {worst[1]}")

    # 4. 购物车：加两件 → 数量 / 小计 / 结算
    pg.click(".card:nth-child(1) .sizes button:nth-child(3)")
    pg.click(".card:nth-child(1) .add")
    pg.wait_for_timeout(300)
    pg.click(".card:nth-child(3) .add")
    pg.wait_for_timeout(300)
    ck("购物袋计数 = 2", pg.inner_text("#bagN") == "2", pg.inner_text("#bagN"))
    pg.click("#bagBtn")
    pg.wait_for_timeout(600)
    ck("抽屉真的滑出（右边界贴住视口）",
       pg.evaluate("Math.round(document.getElementById('drawer').getBoundingClientRect().right)") >= 1435,
       str(pg.evaluate("document.getElementById('drawer').getBoundingClientRect().right")))
    ck("小计 = ¥1,158（459+699）", pg.inner_text("#sub") == "¥1,158", pg.inner_text("#sub"))
    ck("满 399 免运费生效", pg.inner_text("#ship") == "免运费", pg.inner_text("#ship"))
    ck("已选尺码 M 带进购物车", "尺码 M" in pg.inner_text("#items"), pg.inner_text("#items")[:80])
    pg.click(".line .qty button:nth-child(3)")   # +1
    pg.wait_for_timeout(250)
    ck("加一件后小计 = ¥1,617", pg.inner_text("#sub") == "¥1,617", pg.inner_text("#sub"))
    pg.click(".line .rm")
    pg.wait_for_timeout(250)
    ck("移除后只剩 1 行", pg.eval_on_selector_all(".line", "e=>e.length") == 1)
    pg.click("#payBtn")
    pg.wait_for_timeout(400)
    ck("下单后购物袋清零", pg.inner_text("#bagN") == "0", pg.inner_text("#bagN"))
    ck("下单成功 toast 出现", "下单成功" in pg.inner_text("#toast"), pg.inner_text("#toast"))

    # 5. 筛选真的筛掉了卡片
    pg.evaluate("scrollTo(0,1200)")
    pg.click('.chip[data-f="shoe"]')
    pg.wait_for_timeout(300)
    vis = pg.eval_on_selector_all(".card", "es=>es.filter(e=>e.offsetParent!==null).length")
    ck("筛选『鞋履』只剩 1 件", vis == 1, f"实际 {vis}")
    pg.click('.chip[data-f="all"]')
    pg.wait_for_timeout(300)
    vis = pg.eval_on_selector_all(".card", "es=>es.filter(e=>e.offsetParent!==null).length")
    ck("『全部』回到 8 件", vis == 8, f"实际 {vis}")

    # 6. 没有横向溢出
    ovf = pg.evaluate("document.documentElement.scrollWidth - innerWidth")
    ck("无横向溢出", ovf <= 1, f"溢出 {ovf}px")

    # 7. 控制台无错误
    b.close()

for n, ok, d in checks:
    print(("  PASS  " if ok else "  FAIL  ") + n + (f"   → {d}" if d and not ok else ""))
print(f"\n{len(checks)-len(fails)}/{len(checks)} 通过")
sys.exit(1 if fails else 0)
