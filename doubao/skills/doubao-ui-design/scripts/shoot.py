#!/usr/bin/env python3
"""给自己的产物拍真机照片 —— 这个包里最重要的一个脚本。

为什么它最重要：执行者**看不见自己的产物**时
（性能合同明写「不再需要浏览器回传」），于是「两种橙打架」「装饰元素变噪音」
「底纹像二维码」这类构成缺陷 100% 会进最终交付，而所有数值门都显示绿灯。
在两份参照产物上统计：7 处修改里有 4 处只有看图才能发现。

为什么它必须只降级不崩溃：截图器一崩，链条就整段失效——

    shoot.py 崩 → 对工具失去信心 → 退回手工 open_url_in_browser ×7 + Wait ×4
             → 盘上只留下 1 张截图（5 个关键屏截了 1 个）
             → 没看到按钮压住卡片 → 交付 → 用户看到错位

崩的原因是 `wait_until="networkidle"`：它要求「500ms 内无网络连接」，
而有 base64 大图解码、外链字体、持续 CSS 动画或 setInterval 的页面
**永远等不到 idle**。所以这一版三条硬规矩：

  1. `load()` + 分段等待，每段单独 try/except —— 超时只降级，不抛异常
  2. 传本地文件路径就自己挑空闲端口托管，截完自动关 —— 不用你手工起服务器
  3. **失败也要出图**：任何异常都先 screenshot 再报错。一张有问题的图也比没有图强

四种模式：
  full    <url|文件>  <out.png> [w] [h]     整页长图（官网 / 文档画布）
  strips  <url|文件>  <outdir> [w] [h]      按视口切段，便于逐段看
  states  <url|文件>  <outdir> [n]          移动端逐个**真实界面状态**（390×844）
  sheet   <indir>     <out.png> [cols]      把多张图拼成联络表，一次看完

`screens` 是 `states` 的旧名，等价保留 —— 但行为已经换成声明式协议了，
不再是"滚不动就拍 N 张同图"（见下面 CAPTURE_MANIFEST 那一段注释）。

每次成功都往 run.json 的 receipts.shot 追加一条 {path, sha256, viewport}。
publish.py 的闭包 C1 就是从这里读的：**没截过图的东西不许发**。

没有 playwright 时打印宿主四调用链的替代方案（豆包实测约 15 秒）。
"""
from __future__ import annotations

import argparse
import http.server
import math
import os
import socket
import socketserver
import sys
import threading
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

FREEZE_CSS = """
*,*::before,*::after{
  animation-duration:.001s!important;animation-delay:0s!important;
  transition-duration:.001s!important;transition-delay:0s!important;
}
"""

# 把"入场动画的终态"直接落到 DOM 上。
# 不这样做的话截出来的是半透明中间态，你会以为是自己的设计有问题。
SETTLE_JS = """ () => {
  document.querySelectorAll('.rv,.rv-mask,.an,.wipe,.pop,[data-reveal]')
    .forEach(e => e.classList.add('in','live'));
  document.querySelectorAll('.screen,[data-screen]').forEach(e => e.classList.add('live'));
  // 数字滚动直接落终值
  document.querySelectorAll('[data-count],[data-n]').forEach(e => {
    const v = e.dataset.count || e.dataset.n;
    if (v) e.textContent = Number(v).toLocaleString('en-US');
  });
  // 懒加载图在长图拼接时来不及解码 —— 实测会拍出空白图，
  // 然后你会跑去"修"一个根本没坏的页面。
  document.querySelectorAll('img[loading="lazy"]').forEach(i => { i.loading = 'eager'; });
}"""

FONTS_READY = " () => document.fonts ? document.fonts.status === 'loaded' : true"
ALL_IMAGES_READY = (" () => Array.from(document.images)"
                    ".every(i => i.complete && i.naturalWidth > 0)")

# ── 关键屏：声明式协议，脚本不猜按钮（P0-6）─────────────────
# 只按 `.screen,[data-screen]` 找、找不到就 `scrollTo` 兜底是不够的。
# 在 app 骨架（用 `.panel[data-panel]`）上一个都不匹配，而 `body{overflow:hidden}`
# + 内层 `#flow{overflow-y:auto}` 让 window 根本不滚动 —— **N 张完全相同的图**。
# 本机在包自己的骨架上复现：5 个文件、1 个 sha256（770fe3cc…）。
# 连带损害：收据逐文件记 → 闭包看到"截了 6 屏" → 放行；
# 画布里 p01 出现两次而 p01/p02/p03 本来就是同一张。
#
# 收据数的是**文件个数**，不是**不同的图**。
# 「目标集合为空必须 FAIL」缺一条对偶：**目标集合全都一样也必须 FAIL。**
#
# 修法不是让脚本更会猜按钮 —— 脚本不知道任意页面的 selector、动作顺序和等待条件，
# 那样的 states 会变成下一道不可达门。改成**页面自己声明**，脚本只枚举：
#
# window.__UI_CAPTURE__ = { states: [
# {id:"home",   label:"首页动态流"},
# {id:"detail", label:"动态详情", go: async () =>
# document.querySelector('[data-post]').click()},
# ], reset: async () => {…} };
#
# 三级降级，**每一级都印出用的是哪条通路**；兜底路径产出重复 sha256 时，
# 报错必须是可执行的（S13 保底分岔）—— 直接给可粘贴的片段。
CAPTURE_MANIFEST = """ () => {
  const m = window.__UI_CAPTURE__;
  if (m && Array.isArray(m.states) && m.states.length)
    return {via: 'manifest', n: m.states.length,
            labels: m.states.map((s, i) => s.label || s.id || ('state' + i))};
  const marked = [...document.querySelectorAll('[data-capture]')];
  if (marked.length)
    return {via: 'data-capture', n: marked.length,
            labels: marked.map((e, i) => e.getAttribute('data-capture') || ('#' + i))};
  const scr = [...document.querySelectorAll('.screen,[data-screen]')];
  return {via: scr.length ? 'screen-scroll' : 'window-scroll',
          n: scr.length || 0, labels: []};
}"""

GOTO_STATE = """async (i) => {
  const m = window.__UI_CAPTURE__;
  if (m && Array.isArray(m.states) && m.states[i]) {
    if (m.reset) { try { await m.reset(); } catch (e) {} }
    const s = m.states[i];
    if (s.go) { try { await s.go(); } catch (e) { return 'go-failed'; } }
    return 'manifest';
  }
  const marked = [...document.querySelectorAll('[data-capture]')];
  if (marked[i]) {
    marked[i].scrollIntoView({behavior: 'instant', block: 'start'});
    if (marked[i].tagName === 'BUTTON' || marked[i].hasAttribute('data-capture-click'))
      marked[i].click();
    return 'data-capture';
  }
  const scr = [...document.querySelectorAll('.screen,[data-screen]')];
  if (scr[i]) { scr[i].scrollIntoView({behavior: 'instant', block: 'start'});
                return 'screen-scroll'; }
  scrollTo(0, i * innerHeight);
  return 'window-scroll';
}"""

FIX_SNIPPET = """  <script>window.__UI_CAPTURE__={states:[
    {id:"home",   label:"首页"},
    {id:"detail", label:"详情", go:async()=>document.querySelector('<你的卡片选择器>').click()},
    {id:"tab2",   label:"第二个 tab", go:async()=>document.querySelector('<你的 tab 选择器>').click()}
  ],reset:async()=>{ /* 回到初始态：把 tab 切回第一个、关掉弹层 */ }};</script>"""


def _no_playwright() -> None:
    print(
        "PLAYWRIGHT_MISSING —— 本机没有 playwright。宿主侧用这条四调用链代替（实测约 15 秒）：\n"
        "  1) cd <产物目录> && python3 -m http.server 8910 &\n"
        "  2) open_url_in_browser  http://localhost:8910/index.html\n"
        "     （file:// 打不开；URL 结尾不要带 &）\n"
        "  3) take_screenshot      —— 视口固定 1280×960\n"
        "  4) 把截图读进上下文，再写 observed\n"
        "移动端要看 390×844 时，用一个定宽 iframe 包装页把产物套进去再截。\n"
        "**不要因为这里失败就跳过看图。** 看图是发布的前置条件，不是可选项。",
        file=sys.stderr)


class _Serve:
    """传本地文件路径就自己起个服务器。端口冲突不该是你要解决的问题。"""

    def __init__(self, directory: Path):
        with closing(socket.socket()) as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        handler = type("H", (http.server.SimpleHTTPRequestHandler,),
                       {"__init__": lambda s, *a, **k:
                        http.server.SimpleHTTPRequestHandler.__init__(
                            s, *a, directory=str(directory), **k),
                        "log_message": lambda *a: None})
        self.httpd = socketserver.TCPServer(("127.0.0.1", self.port), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        try:
            self.httpd.shutdown()
        except Exception:
            pass


def resolve_target(target: str) -> tuple[str, _Serve | None]:
    """URL 原样返回；本地路径就地托管成 http URL（file:// 里很多东西不成立）。"""
    if target.startswith(("http://", "https://")):
        return target, None
    p = Path(target).resolve()
    if not p.exists():
        print(f"目标不存在：{p}", file=sys.stderr)
        sys.exit(1)
    if p.is_dir():
        srv = _Serve(p)
        return f"http://127.0.0.1:{srv.port}/index.html", srv
    srv = _Serve(p.parent)
    return f"http://127.0.0.1:{srv.port}/{p.name}", srv


def _try(fn, label: str, soft: list[str]) -> None:
    """每一段等待都只降级不抛异常。超时不是崩溃的理由——出图才是目的。"""
    try:
        fn()
    except Exception as e:
        soft.append(f"{label}: {type(e).__name__}")


def _open(pg, url: str, soft: list[str]) -> None:
    _try(lambda: pg.goto(url, wait_until="load", timeout=30000), "goto/load", soft)
    _try(lambda: pg.wait_for_function(FONTS_READY, timeout=8000), "fonts", soft)
    _try(lambda: pg.wait_for_function(ALL_IMAGES_READY, timeout=12000), "images", soft)
    _try(lambda: pg.wait_for_timeout(400), "settle", soft)


def _prep(pg, soft: list[str]) -> None:
    _try(lambda: pg.add_style_tag(content=FREEZE_CSS), "freeze", soft)
    _try(lambda: pg.evaluate(SETTLE_JS), "settle-js", soft)
    _try(lambda: pg.wait_for_function(ALL_IMAGES_READY, timeout=8000), "images2", soft)
    _try(lambda: pg.wait_for_timeout(350), "hold", soft)


def _receipt(run_path, out: Path, w: int, h: int, mode: str, source: str) -> None:
    if not out.is_file():
        return
    # source 必须记：闭包 C1 问的是"这份产物被看过没有"，
    # 只记截图文件名答不了这个问题。
    runstate.add_receipt(run_path, "shot", {
        "path": str(out), "source": source, "sha256": runstate.sha256_file(out),
        "viewport": f"{w}x{h}", "mode": mode,
        "bytes": out.stat().st_size})


def main() -> int:
    ap = argparse.ArgumentParser(add_help=False)
    runstate.add_run_arg(ap)
    a, rest = ap.parse_known_args()
    run_path = runstate.find(a.run)

    if len(rest) < 3:
        print(__doc__)
        return 1
    mode, target, out = rest[0], rest[1], rest[2]
    tail = rest[3:]

    if mode == "sheet":
        return _sheet(target, out, int(tail[0]) if tail else 5)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _no_playwright()
        return 2

    w = int(tail[0]) if len(tail) > 0 and tail[0].isdigit() else 1440
    h = int(tail[1]) if len(tail) > 1 and tail[1].isdigit() else 900
    n = 10
    if mode in ("states", "screens"):
        n = int(tail[0]) if tail and tail[0].isdigit() else 10
        w, h = 390, 844

    url, srv = resolve_target(target)
    soft: list[str] = []
    rc = 0
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            _open(pg, url, soft)
            _prep(pg, soft)

            if mode == "full":
                Path(out).parent.mkdir(parents=True, exist_ok=True)
                # full_page 在超长页上偶发失败；失败就退回视口截图，总之要出图
                try:
                    pg.screenshot(path=out, full_page=True)
                except Exception as e:
                    soft.append(f"full_page: {type(e).__name__}")
                    pg.screenshot(path=out)
                print(f"saved {out}")
                _receipt(run_path, Path(out), w, h, mode, target)
            elif mode == "strips":
                os.makedirs(out, exist_ok=True)
                total = pg.evaluate("document.body.scrollHeight") or h
                k = min(math.ceil(total / h), 40)
                for i in range(k):
                    _try(lambda i=i: pg.evaluate(f"scrollTo(0,{i * h})"), "scroll", soft)
                    _try(lambda: pg.wait_for_timeout(500), "hold", soft)
                    _prep(pg, soft)
                    f = Path(out) / f"s{i:02d}.png"
                    pg.screenshot(path=str(f))
                    _receipt(run_path, f, w, h, mode, target)
                print(f"saved {k} strips -> {out}")
            elif mode in ("states", "screens"):
                os.makedirs(out, exist_ok=True)
                man = {"via": "window-scroll", "n": 0, "labels": []}
                try:
                    man = pg.evaluate(CAPTURE_MANIFEST) or man
                except Exception as e:
                    soft.append(f"manifest: {type(e).__name__}")
                k = min(n, man["n"]) if man["n"] else n
                print(f"关键屏通路：**{man['via']}**"
                      + (f"（声明了 {man['n']} 个状态：{'、'.join(man['labels'][:6])}）"
                         if man["labels"] else f"（没有声明，滚动兜底，截 {k} 张）"))
                shots: list[tuple[Path, str]] = []
                for i in range(k):
                    via = "?"
                    try:
                        via = pg.evaluate(GOTO_STATE, i)
                    except Exception as e:
                        soft.append(f"goto-state{i}: {type(e).__name__}")
                    _try(lambda: pg.wait_for_timeout(700), "hold", soft)
                    _prep(pg, soft)
                    f = Path(out) / f"p{i + 1:02d}.png"
                    pg.screenshot(path=str(f))
                    _receipt(run_path, f, w, h, "states", target)
                    shots.append((f, via))
                print(f"saved {k} screens -> {out}")
                # 目标集合**全都一样**也必须 FAIL —— 这是"为空必须 FAIL"的对偶。
                digests: dict[str, list[str]] = {}
                for f, _v in shots:
                    digests.setdefault(runstate.sha256_file(f), []).append(f.name)
                same = [g for g in digests.values() if len(g) > 1]
                if len(shots) > 1 and same:
                    print(f"\n✗ {len(shots)} 张截图里只有 {len(digests)} 个不同的 sha256。"
                          f"完全相同的是：" + "；".join("=".join(g) for g in same))
                    if man["via"] in ("window-scroll", "screen-scroll"):
                        print("  你的产物没有声明 __UI_CAPTURE__，我只能滚动截图，"
                              "而这个页面不滚动（body 锁死、内容在内层容器里）。\n"
                              "  把下面这段贴进 </body> 之前，把 states 换成"
                              "你这一稿真实的状态：\n\n" + FIX_SNIPPET)
                    else:
                        print("  声明是有的，但那几个 `go` 跑完画面没变。两种成因，"
                              "先把上面那两张图读进来对一眼：\n"
                              "    ① 选择器不对 —— 改 __UI_CAPTURE__ 里那条 go\n"
                              "    ② 那个状态本身是空的（比如卡片展开后的详情区"
                              "还没写内容）—— 去把内容写上\n"
                              "  **不要靠多截几张凑数**：doc 的关键界面那一节会"
                              "原样收下它们，客户会看到同一张图出现三次。")
                    rc = 1
                elif not runstate.orchestrated():
                    print(f"\n下一步（关键屏要进 doc 的话，一条命令做完出图 + 内嵌 + 排版）：\n"
                          f"  python3 {Path(__file__).resolve().parent / 'pack_img.py'}"
                          f" --for-doc-screens {out} --out doc/screens")
            else:
                print(f"未知模式 {mode}")
                rc = 1

            if errs:
                print("PAGE_ERRORS " + " | ".join(errs[:3]))
            b.close()
    except Exception as e:
        print(f"SHOOT_FAILED {type(e).__name__}: {e}", file=sys.stderr)
        print("  替代路径（不要重试同一条命令）：宿主 http.server + open_url_in_browser "
              "+ take_screenshot 四调用链，见本文件开头。", file=sys.stderr)
        rc = 1
    finally:
        if srv:
            srv.close()

    if soft:
        print("软降级（不影响出图，但值得看一眼）：" + "、".join(soft))
    if not run_path:
        runstate.note_missing("截图")
    return rc


def _sheet(indir: str, out: str, cols: int) -> int:
    """把一批图拼成联络表。看十屏时一次看完比翻十次强。"""
    from PIL import Image, ImageDraw
    files = sorted(f for f in os.listdir(indir) if f.lower().endswith((".png", ".jpg")))
    if not files:
        print("没有图")
        return 1
    cw, ch = 300, 660
    rows = math.ceil(len(files) / cols)
    sheet = Image.new("RGB", (cols * cw, rows * ch), "#101013")
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        im = Image.open(os.path.join(indir, f)).convert("RGB")
        im.thumbnail((cw - 10, ch - 26))
        x, y = (i % cols) * cw + 5, (i // cols) * ch + 5
        sheet.paste(im, (x, y))
        d.text((x, y + ch - 20), f, fill="#8A8A93")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"saved {out}  ({len(files)} 张 / {cols} 列)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
