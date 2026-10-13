#!/usr/bin/env python3
"""给飞书文档画布出图 —— 这个包一直缺的那个产能。

为什么它必须存在，三条真实 trace 说得很清楚。飞书单个 html5-block 上限 512KB，
图要 base64 内嵌，于是每一条 trace 都自己搓了一套压缩流水线：

    sips -Z 600 -s formatOptions 60  /  sips -Z 800 … 50
    PIL max_width=800 quality=70  →  再来一次 max_width=400 quality=60
    sips -Z 600  →  sips -Z 500  →  sips -Z 400

规律非常干净：**每一次撞上上限，第一反应都是再降尺寸，从来没有"只降质量"。**
而 `sips -Z` 压的是长边 —— 对一张竖着的手机截图，`-Z 400` 意味着宽度只剩 185px。
放进 698–1145px 的飞书块里，是 4–6 倍放大 —— 文档里图片糊，就是这么来的。

门（img-upscaled）当时报的是 PASS，因为它量的是 CSS 像素而屏幕是 2×。
**但根因不在门。门告诉模型"你错了"，却没有任何东西告诉它"该怎么对"。**
门与产能必须成对给；只给门，模型只能猜，而它每次都猜同一个错答案。

这个脚本的三条规矩：

  1. 出图宽优先 2×，但不低于 1× 渲染宽；质量不低于 72。
  2. 体积、宽度、质量一起谈判；先守质量，再退宽度，绝不压到 q10。
  3. 高宽比 > 2.5 的长图一律先切段（每段 <=2）—— 整页长图不该整张进文档。

用法：
    python3 pack_img.py shots/full.png --slot plate
    python3 pack_img.py shots/*.png --slot screens3 --out doc/img
    python3 pack_img.py shots/phone.png --slot device --budget-kb 200

出的东西：`<out>/<名字>.jpg` 和 `<out>/<名字>.b64.txt`
（后者是完整的 `data:image/jpeg;base64,…`，直接 sed 进画布的 <img src>）。
"""
from __future__ import annotations

import argparse
import base64
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

# 飞书块宽最大 1145，画布左右各留 clamp(24,4.6vw,56) 的阅读边距 → 版心约 1033。
# 每个图位的**渲染 CSS 宽度**按版心算，出图取它的 2 倍。
# 只在 698 / 820 两个宽度量是不够的：那是块宽不是版心，也不是最坏情况。
CANVAS_MAX = 1033
SLOTS = {
    "plate":    (1.00, "通栏版面证据（.plate）"),
    "duo":      (0.48, "两栏对照（.duo）"),
    "screens2": (0.48, "两列关键屏（.screens --cols:2）"),
    "screens3": (0.31, "三列关键屏（.screens --cols:3）"),
    "screens4": (0.23, "四列关键屏（.screens --cols:4）"),
    "device":   (0.22, "单机展示（.device）—— 手机机身占版心 22%"),
    "device-row": (0.22, "多机错落（.device-row）"),
    "cover":    (1.55, "封面（1600 宽，不进画布，走媒体插入）"),
}
RETINA = 2
WIDTH_STEPS = (2.0, 1.5, 1.2, 1.0)
Q_FLOOR, Q_TOP = 72, 92
BLOCK_B64_LIMIT = 500_000
B64_HEADROOM = 0.94
MAX_ASPECT = 2.5          # 高宽比超过它就切段
SEG_ASPECT = 2.0          # 每段的目标高宽比

# ── 图位里的占位说明 ─────────────────────────────────────────
# 这四个常量是**唯一来源**：片段用它们生成，`check.py` 的 placeholder 门
# 也导入它们来判「换过话没有」。写死两份就会出现「改了文案、门还认旧的」。
SCREEN_CAP_SLOT = "这一屏叫什么"
SCREEN_CAP_BODY = "他在这里想干什么，所以我们放了什么。"
PLATE_CAP_SLOT = "这一段叫什么"
PLATE_CAP_BODY = "他在这里想知道什么，所以我们放了什么。"
PLACEHOLDER_CAPTIONS = (SCREEN_CAP_SLOT, SCREEN_CAP_BODY,
                        PLATE_CAP_SLOT, PLATE_CAP_BODY)

# ── 手机放进文档的版式 ───────────────────────────────────────
# 一台手机要站在一块**场**里：场有底色、机身有圆角描边与投影。
# 竖图直接通栏铺开会变成「一张竖图」，不是「一台手机」。
# 机身占容器宽按每排台数取，全部落在 15–28% 之间。
PHONE_PCT = {1: "28%", 2: "26%", 3: "22%"}
ROW_MAX = 3               # 一个场里最多 3 台，再多就换一个场


def chunk_rows(items: list) -> list[list]:
    """把 N 台手机切成每排 ≤3 台，且**不留只有 1 台的尾排**。

    4 → 2+2，5 → 3+2，6 → 3+3，7 → 3+2+2。
    尾排落单会让整块版面看起来是「没排完」，与孤儿行同一个毛病。
    """
    out, rest = [], list(items)
    while rest:
        if len(rest) <= ROW_MAX:
            out.append(rest)
            break
        take = 2 if len(rest) - ROW_MAX == 1 else ROW_MAX
        out.append(rest[:take])
        rest = rest[take:]
    return out


# 片段**自带样式**：它要粘进的画布可能是骨架建的，也可能是从零手写的。
# 依赖画布里已有某条规则 = 一半概率裸奔（裸奔的样子就是通栏竖排无机身）。
#
# 样式本体在 `skeletons/device-stage.css` —— **不写在脚本里**。
# 版式是设计资产，放进 Python 就会变成"谁都改不动的常量"，
# 而放在骨架旁边它可以被读、被看、被改，且脚本里零字面 CSS。
STAGE_CSS_FILE = Path(__file__).resolve().parent.parent / "skeletons" / "device-stage.css"


def stage_css() -> str:
    try:
        return "<style>\n" + STAGE_CSS_FILE.read_text(encoding="utf-8") + "</style>"
    except OSError:
        return ""          # 样式取不到也要出片段：图在里面，比没有强


def stage_fragment(figs: list[str]) -> str:
    """N 张手机截图 → 可直接粘贴的完整片段（自带样式）。

    1 台居中，2–3 台横排错落，4 台以上按 `chunk_rows` 分成多个场。
    """
    rows = chunk_rows(figs)
    blocks = []
    for r in rows:
        cls = "ui-stage" if len(r) == 1 else "ui-stage ui-stage-row"
        blocks.append(f'<div class="{cls}" style="--phone:{PHONE_PCT[len(r)]}">\n  '
                      + "\n  ".join(r) + "\n</div>")
    return ("\n<!-- ↓↓ 关键界面那一节：整段粘进画布，figcaption 换成你的话 ↓↓ -->\n"
            + stage_css() + "\n" + "\n".join(blocks) + "\n<!-- ↑↑ 到这里 ↑↑ -->")


def plate_fragment(figs: list[str]) -> str:
    """宽屏版面证据 → 自带样式的通栏片段：场 + 大圆角 + 投影。"""
    return ("\n<!-- ↓↓ 版面证据（通栏长图）：ship 会自动写进画布 ↓↓ -->\n"
            + stage_css() + "\n" + "\n".join(figs) + "\n<!-- ↑↑ 到这里 ↑↑ -->")


# ── 图像后端：PIL 优先，没有就退回 macOS 自带的 sips ──────────────
class Backend:
    kind = "none"

    def __init__(self) -> None:
        try:
            from PIL import Image  # noqa: F401
            self.kind = "pil"
        except Exception:
            if shutil.which("sips"):
                self.kind = "sips"

    def size(self, p: Path) -> tuple[int, int]:
        if self.kind == "pil":
            from PIL import Image
            with Image.open(p) as im:
                return im.size
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(p)],
                             capture_output=True, text=True).stdout
        w = h = 0
        for line in out.splitlines():
            if "pixelWidth" in line:
                w = int(line.split(":")[-1])
            if "pixelHeight" in line:
                h = int(line.split(":")[-1])
        return w, h

    def prepare(self, src: Path, width: int,
                crop: tuple[int, int, int, int] | None = None):
        """裁切并缩放到目标宽度；质量二分时复用这一步的结果。"""
        if self.kind == "pil":
            from PIL import Image
            with Image.open(src) as im:
                im = im.convert("RGB")
                if crop:
                    im = im.crop(crop)
                if im.width != width:
                    h = max(1, round(im.height * width / im.width))
                    im = im.resize((width, h), Image.LANCZOS)
                return im.copy()
        tmp = Path(tempfile.mkdtemp()) / "seg.png"
        if crop:
            l, t, r, b = crop
            subprocess.run(["sips", "--cropOffset", str(t), str(l),
                            "-c", str(b - t), str(r - l), str(src),
                            "--out", str(tmp)], capture_output=True)
            src = tmp
        # sips -Z 压长边；这里要压**宽**，所以用 --resampleWidth
        prepared = Path(tempfile.mkdtemp()) / "prepared.png"
        subprocess.run(["sips", "--resampleWidth", str(width),
                        str(src), "--out", str(prepared)], capture_output=True)
        return prepared

    def encode(self, prepared, dst: Path, quality: int) -> None:
        """把 prepare 的结果按给定质量编码成 JPEG。"""
        if self.kind == "pil":
            prepared.save(dst, "JPEG", quality=quality, optimize=True,
                          progressive=True, subsampling=0)
            return
        subprocess.run(["sips",
                        "-s", "format", "jpeg",
                        "-s", "formatOptions", str(quality),
                        str(prepared), "--out", str(dst)], capture_output=True)

    def render(self, src: Path, dst: Path, width: int, quality: int,
               crop: tuple[int, int, int, int] | None = None) -> None:
        """兼容旧调用：按给定宽度和质量出一张 JPEG。"""
        self.encode(self.prepare(src, width, crop), dst, quality)


def fit(be: Backend, src: Path, dst: Path, display_width: int, budget: int,
        crop: tuple[int, int, int, int] | None = None,
        max_width: int | None = None) -> dict | None:
    """在宽度阶梯与质量下限之间协商。返回命中的事实；四档全败返回 None。"""
    src_w = (crop[2] - crop[0]) if crop else be.size(src)[0]
    max_w = max_width or src_w
    attempts: list[dict] = []
    for step in WIDTH_STEPS:
        width = min(src_w, max_w, max(1, round(display_width * step)))
        prepared = be.prepare(src, width, crop)
        lo, hi = Q_FLOOR, Q_TOP
        best: tuple[int, int] | None = None
        while lo <= hi:
            q = (lo + hi) // 2
            be.encode(prepared, dst, q)
            n = dst.stat().st_size
            attempts.append({"width": width, "quality": q, "bytes": n, "step": step})
            if n <= budget:
                best = (q, n)
                lo = q + 1
            else:
                hi = q - 1
        if best:
            q, n = best
            be.encode(prepared, dst, q)
            return {
                "width": width, "quality": q, "bytes": n, "step": step,
                "floorHit": q <= Q_FLOOR, "attempts": attempts,
                "sourceTooNarrow": src_w < round(display_width * RETINA),
            }
    return None


def segments(w: int, h: int, bands: int = 0) -> list[tuple[int, int, int, int]]:
    """高宽比 > 2.5 的长图切成每段 <=2.0 的若干段。"""
    if bands > 0 and w > 0 and h > 0:
        band_h = min(h, 1800)
        if bands == 1:
            tops = [(h - band_h) // 2]
        else:
            tops = [round(i * (h - band_h) / (bands - 1)) for i in range(bands)]
        return [(0, max(0, t), w, min(h, max(0, t) + band_h)) for t in tops]
    if w <= 0 or h / w <= MAX_ASPECT:
        return []
    n = math.ceil((h / w) / SEG_ASPECT)
    step = math.ceil(h / n)
    return [(0, i * step, w, min(h, (i + 1) * step)) for i in range(n)]


SHOT_NAME = re.compile(r"^(p|screen|s)?\d{1,2}$|^screen-?\d+$", re.I)


def doc_screens(be: Backend, shots: Path, out: Path, run: str | None) -> int:
    """把关键屏批量出成 device 尺寸，**并直接打印可粘贴的 <figure> 片段**。

    这一条是用户点名的。他的原话是
        「不是应该先把 h5 搞出来，然后把 h5 图片放到 doc 里面吗？」
    完全正确，而包里当时没有任何东西表达这个顺序。
    典型失败：关键屏都截了（p01–p10，各 932KB），
    **进 doc 的是 0 张** —— 一份把 `.screens` / `.device-showcase` 两个容器
    建好了却全空着，另一份在 500KB 压力下把截图整个丢了、留下了素材照片。

    截图和"放进 doc"之间隔着出图、压缩、转 base64、写标签四步。
    隔四步的事情不会自己发生 —— 所以这里一条命令做完，输出即可粘贴。
    """
    if not shots.is_dir():
        print(f"找不到目录：{shots}")
        return 1
    cand = sorted(p for p in shots.iterdir()
                  if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                  and SHOT_NAME.match(p.stem))
    if not cand:
        print(f"{shots}/ 里没有关键屏（认 p01.png / 01.png / screen-1.png 这类命名）。\n"
              f"  先出图：python3 {runstate.SCRIPTS}/shoot.py screens <成品页> shots/ 6")
        return 1
    # 这条命令只服务**移动端**。传宽屏截图进来会被压进 227px 的手机机身位，
    # 于是一份官网的「关键界面」节渲染成三台手机 —— 那是缺陷。
    # 判据是源图自己的形状（可证伪），不靠调用方申报。
    wide = [(p, *be.size(p)) for p in cand]
    wide = [(p, w, h) for p, w, h in wide if w and h and w >= h]
    if wide:
        print(f"这 {len(wide)} 张是**宽屏截图**（例：{wide[0][0].name} "
              f"{wide[0][1]}×{wide[0][2]}），--for-doc-screens 不收。\n"
              f"  它出的是手机机身位（渲染宽 {round(CANVAS_MAX * SLOTS['device'][0])}px），"
              f"宽屏图塞进去会被压成一条，客户看到的是「官网被做成了手机」。\n"
              f"  宽屏稿的版面证据用**通栏长图**：\n"
              f"    python3 {runstate.SCRIPTS}/pack_img.py {wide[0][0]} --slot plate --out doc/img\n"
              f"  画布里用 .plate，不要用 .device / .screens。")
        return 1
    frac, _why = SLOTS["device"]
    disp = round(CANVAS_MAX * frac)
    target = disp * RETINA
    out.mkdir(parents=True, exist_ok=True)
    # 预算从**块上限倒推**，不是每张拍一个固定数：
    # 500KB 是 base64 之后的硬上限，折回原始字节是 375KB，再按张数平摊。
    # 每张固定给 60KB 是不行的：10 张就是 774KB，一次都装不下。
    per = max(18_000, 375_000 // len(cand))
    print(f"关键屏 {len(cand)} 张 → 每张出 {target}px 宽"
          f"（.device 渲染宽 {disp}px 的 2 倍），每张预算 {per // 1024}KB")
    if len(cand) > 6:
        print(f"  · {len(cand)} 屏偏多。**挑 3–6 屏最能说明问题的**，"
              f"不是全放 —— 张数越多每张越糊。")
    figs, total = [], 0
    for i, s in enumerate(cand, 1):
        dst = out / f"{s.stem}.jpg"
        w, _h = be.size(s)
        got = fit(be, s, dst, disp, per, max_width=min(w, target))
        if not got:
            print(f"  ✗ {s.name}: 1× 渲染宽、q≥{Q_FLOOR} 仍超预算。少放几屏或拆块。")
            return 1
        q, n, actual_w = got["quality"], got["bytes"], got["width"]
        total += n
        uri = "data:image/jpeg;base64," + base64.b64encode(dst.read_bytes()).decode()
        (out / f"{s.stem}.b64.txt").write_text(uri, encoding="utf-8")
        figs.append(f'<figure><img src="{uri}" alt="关键屏 {i}">\n'
                    f'    <figcaption><b>{SCREEN_CAP_SLOT}</b>'
                    f'{SCREEN_CAP_BODY}</figcaption></figure>')
        print(f"  {s.name:16} {w}px → {actual_w}px  q={q}  {n // 1024}KB"
              + ("　源图不够宽，重截：shoot.py screens <成品页> shots/ 更大视口"
                 if w < target else ""))
    b64_total = total * 4 // 3
    print(f"\n  合计 {total // 1024}KB，base64 后约 {b64_total // 1024}KB"
          f"（飞书单块硬上限 500KB）")
    片段 = stage_fragment(figs)
    frag = out / "screens-figures.html"
    frag.write_text(片段, encoding="utf-8")
    print(f"\n可直接粘贴的片段已写到 {frag}"
          f"（{len(片段) // 1024}KB，含 base64、自带样式）。")
    rows = [len(r) for r in chunk_rows(figs)]
    print(f"  版式：{'单机居中' if len(figs) == 1 else '横排错落'}"
          f"　{len(rows)} 个场，每场 {'/'.join(str(x) for x in rows)} 台"
          f"　机身占容器 {PHONE_PCT[min(max(rows), 3)]}")
    print("  片段自带 <style>，粘进任何画布都成立，不依赖画布里已有的规则。")
    print("\n**这一节放的是成品页的真机截图，不是素材照片。**"
          "\n  图位里放素材照片、或把标记块删掉留空槽位，门会报出来。")
    runstate.add_receipt(runstate.find(run), "pack", {
        "mode": "doc-screens", "n": len(cand), "targetWidth": target,
        "qualityFloor": Q_FLOOR,
        "base64Total": b64_total, "withinBlockLimit": b64_total < 500_000})
    if b64_total >= 500_000:
        print("\n  ✗ base64 之后会超过飞书单块 500KB —— 关键屏拆到两块画布里，"
              "或者少放几屏（挑最能说明问题的 3–6 屏，不是全放）。")
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="给文档画布出图：宽度和质量各有下限；长图自动切段")
    runstate.add_run_arg(ap)
    ap.add_argument("src", nargs="*", help="源图（截图或素材）")
    ap.add_argument("--slot", default="plate", choices=list(SLOTS),
                    help="这张图在画布里占哪个图位 —— 决定出图宽度")
    ap.add_argument("--display-width", type=int,
                    help="直接给渲染宽度（CSS px），覆盖 --slot")
    ap.add_argument("--for-doc", action="store_true",
                    help="（默认行为的别名，留着让命令读起来完整）")
    ap.add_argument("--for-doc-screens", metavar="SHOTS_DIR",
                    help="把关键屏批量出成 device 尺寸，并直接打印可粘贴的 <figure> 片段")
    ap.add_argument("--out", default="doc/img", help="出图目录")
    ap.add_argument("--budget-kb", type=int, default=366,
                    help="这一批图 base64 后要进飞书单块 500KB；366KB 原始≈488KB base64，留 4%% 余量")
    ap.add_argument("--bands", type=int, default=0,
                    help="只取 N 条代表性版面带（每带 900 CSS px）；0=按长图自动切段")
    a = ap.parse_args()

    be = Backend()
    if be.kind == "none":
        print("既没有 PIL 也没有 sips。装一个：pip install Pillow")
        return 2

    if a.for_doc_screens:
        return doc_screens(be, Path(a.for_doc_screens), Path(a.out), a.run)
    if not a.src:
        ap.error("要么给源图，要么给 --for-doc-screens <shots 目录>")

    frac, why = SLOTS[a.slot]
    disp = a.display_width or round(CANVAS_MAX * frac)
    target_w = disp * RETINA if a.slot != "cover" else 1600

    srcs = [Path(s) for s in a.src]
    missing = [s for s in srcs if not s.is_file()]
    if missing:
        print("找不到：" + ", ".join(str(m) for m in missing))
        return 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # 预算按张数平摊。这里是原始字节；base64 会再放大 4/3。
    total_budget = a.budget_kb * 1024
    print(f"图位 {a.slot}　{why}")
    print(f"  版心 {CANVAS_MAX}px × {frac:.0%} = 渲染宽 {disp}px"
          f"　→ 出图宽 **{target_w}px**（{RETINA}× 视网膜）")
    print(f"  总预算 {a.budget_kb}KB（base64 后约 {a.budget_kb * 4 // 3}KB，"
          f"飞书单块硬上限 500KB）\n")

    jobs: list[tuple[Path, tuple[int, int, int, int] | None, str]] = []
    for s in srcs:
        w, h = be.size(s)
        if w == 0:
            print(f"  ✗ 读不出尺寸：{s}")
            return 1
        segs = segments(w, h, a.bands)
        if segs:
            print(f"  {s.name}　原始 {w}×{h}（高宽比 {h / w:.1f}）"
                  + (f"→ **取 {len(segs)} 条代表性版面带**"
                     if a.bands else f"→ **切 {len(segs)} 段**，每段 <=2.0"))
            print(f"     整页长图不该整张进文档：像素总量 = 宽 × 高，"
                  f"宽度和质量都有下限，超预算就取代表性版面带。")
            for i, c in enumerate(segs, 1):
                jobs.append((s, c, f"{s.stem}-{i}"))
        else:
            jobs.append((s, None, s.stem))

    per = max(24 * 1024, total_budget // max(1, len(jobs)))
    rows, total, thin, failed = [], 0, [], []
    for src, crop, stem in jobs:
        dst = out / f"{stem}.jpg"
        w0, _h0 = be.size(src)
        src_w = (crop[2] - crop[0]) if crop else w0
        # 源图比目标窄就按源图的真实宽度出 —— **绝不放大**：
        # 放大只是把糊写进文件里，还让门以为够了。如实报，并给出重出的命令。
        got = fit(be, src, dst, disp, per, crop, max_width=target_w)
        if not got:
            failed.append(stem)
            continue
        wide, q, n = got["width"], got["quality"], got["bytes"]
        total += n
        (out / f"{stem}.b64.txt").write_text(
            "data:image/jpeg;base64," + base64.b64encode(dst.read_bytes()).decode(),
            encoding="utf-8")
        note = "超预算" if n > per else ""
        if src_w < target_w:
            note = (note + " " if note else "") + "源图不够宽"
            thin.append(stem)
        if got["step"] < RETINA:
            note = (note + " " if note else "") + f"2×会低于q{Q_FLOOR}，退到{got['step']:.1f}×"
        rows.append((stem, wide, q, n, got["step"], note, got["floorHit"]))

    print(f"{'出图':26}{'宽':>7}{'质量':>6}{'字节':>10}{'倍率':>7}{'退让':>8}   备注")
    for stem, w, q, n, step, note, _floor in rows:
        ratio = f"{w / disp:.1f}×" if disp else "-"
        give = "-" if step >= RETINA else f"{RETINA:.1f}→{step:.1f}"
        print(f"  {stem:24}{w:>7}{q:>6}{n:>10}{ratio:>7}{give:>8}   {note}")
    b64_total = total * 4 // 3
    print(f"\n  合计 {total // 1024}KB，base64 后约 {b64_total // 1024}KB")
    ok = b64_total < 500_000
    print("  倍率是「出图宽 ÷ 渲染宽」。>=2.0 在飞书最宽的块里也清晰；"
          "<1.5 会被 img-upscaled 拦下。")
    if thin:
        print(f"\n  ✗ {len(thin)} 张源图本身就不够宽（{thin[:3]}）——"
              f"没有给它们放大，放大只会把糊写进文件里。\n"
              f"     重出源图，宽度直接给到 {target_w}：\n"
              f"       python3 {runstate.SCRIPTS}/shoot.py full <产物> shots/x.png "
              f"{target_w} 900\n"
              f"     或者换一个更小的图位（渲染宽小了，同一张源图的倍率就够了）：\n"
              + "".join(f"       --slot {k:12} 渲染宽 {round(CANVAS_MAX * v[0]):>4}px"
                        f"　需要源图 >={round(CANVAS_MAX * v[0]) * RETINA}px\n"
                        for k, v in SLOTS.items() if k != "cover"))
    if failed:
        print(f"\n  ✗ {len(failed)} 段在 1× 渲染宽、q≥{Q_FLOOR} 时仍超预算：{failed[:3]}\n"
              f"     整页像素太多，改用代表性版面带：\n"
              f"       python3 {runstate.SCRIPTS}/pack_img.py <源图> --slot {a.slot} "
              f"--bands 3 --out {out}")
    if not ok:
        print("  ✗ base64 之后会超过飞书单块 500KB。宽度和质量已经守住下限 ——\n"
              "     ① 用 --bands 3 只取代表性版面带\n"
              "     ② 或把画布拆成两块（doc/canvas-a.html / canvas-b.html 各一半）\n"
              "     ③ 或元素级截图，只截要讲的那一段："
              "pg.locator('.band').screenshot()")
    # P0-9：宽屏稿也要有一份**可直接原地写入**的片段。
    # 只写 .b64.txt、剩下靠人把 base64 粘进 <img src> 是不够的——
    # 隔一步的事情不会自己发生（实测：关键屏截了 10 张，进 doc 的 0 张）。
    # 现在 `ui.py ship` 直接拿这份 HTML 替换画布里的标记块，模型零参与。
    figs = [
        f'<figure class="ui-plate"><img src="'
        + (out / f"{stem}.b64.txt").read_text(encoding="utf-8")
        + f'" alt="版面证据 {i}">\n'
          f'    <figcaption><b>{PLATE_CAP_SLOT}</b>'
          f'{PLATE_CAP_BODY}</figcaption></figure>'
        for i, (stem, *_r) in enumerate(rows, 1)]
    (out / "plate-figure.html").write_text(
        plate_fragment(figs), encoding="utf-8")
    print(f"\n  可直接写入画布的片段：{out}/plate-figure.html"
          f"（自带样式：场 + 大圆角 + 投影，不依赖画布里已有的规则）")
    print(f"  内嵌：把 {out}/<名字>.b64.txt 的整段内容替换进画布的 "
          f"<img src=\"…\">\n"
          f"  出完记得跑门核对：python3 {runstate.SCRIPTS}/check.py --url "
          f"doc/canvas-a.html --profile doc")

    runstate.add_receipt(runstate.find(a.run), "pack", {
        "slot": a.slot, "displayWidth": disp, "targetWidth": target_w,
        "qualityFloor": Q_FLOOR,
        "images": [{"name": r[0], "width": r[1], "quality": r[2],
                    "bytes": r[3], "widthStep": r[4],
                    "qualityFloorHit": r[6]}
                   for r in rows],
        "base64Total": b64_total, "withinBlockLimit": ok,
        "underWidth": thin, "failed": failed})
    return 0 if (ok and not thin and not failed) else 1


if __name__ == "__main__":
    sys.exit(main())
