#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆包视觉创意 · 尺子与工人（四条命令）

    hostcheck              探测这台机器的写入通路，打印可粘贴的命令
    ground   --image <图>  量出这张图自己的安静区、结构线、主体区
    check    --slide <文件> 机械校验（装不下 / 压住 / 越界 / 看不清 / 语法坏）
    shots    --deck <目录>  把截图拼成一张缩略图墙

设计立场：**脚本只证明可证伪的事实，不做审美判断。**
`check` 全绿不代表这一页好看——好不好看由执行者对着截图按 `page-craft.md` 判。
所以这里的每一条判据都必须能用「量出来的数」说清，修法只指方向、不教打补丁。

依赖：标准库；Pillow 可选（没有它时像素类判据自动降级为提示，并明确说降了级）。
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

CANVAS_W, CANVAS_H = 960.0, 540.0
LINE_FACTOR = 1.5          # **容量预算**：设计上给一行留的高（字号 × 1.5）
INK_FACTOR = 1.25          # **字真正占的高**：判碰撞用它，不用预算值
AUTOFIT_FLOOR = 0.7        # autoFit 缩到 0.7× 就不再缩
MAX_ASPECT_DRIFT = 0.10    # 图窗与源图比例最多相差 10%；anchor 只能选边，不能豁免幅度
FOG_OPAQUE_SHARE = 0.65    # 大罩自身至少 65% 达到 α0.55，才算实质遮住这一侧
BOTTOM_CARD_GAP = 24.0     # 不透明、非出血浮动卡片到页面底边的最小呼吸

# ── 像素能力：真 Pillow 优先，拿不到就用包内标准库解码器 ──────────────
# **量不到 ≠ 合格。** 所以这里只有两种结局：要么拿到一个能用的实现，
# 要么把「本次没量过」如实说出去（`PIX-000` 与 `hostcheck` 都会印）。
PIXEL_SOURCE = "none"                   # "pillow" / "stdlib" / "none"
PIXEL_GAPS: list[str] = []              # 接口自检缺口（非空＝本次的像素判据不可信）
PIXEL_HINTS: list[str] = []             # 真 Pillow 不可用时，本机该怎么装
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import pixels as _pixels            # type: ignore
    PIXEL_SOURCE = _pixels.install()
    PIXEL_GAPS = _pixels.selfcheck()
    if PIXEL_SOURCE != "pillow":
        PIXEL_HINTS = _pixels.diagnose()[1]
except Exception:                       # noqa: BLE001 - 兜底本身出问题也不能拖垮整条链
    PIXEL_SOURCE, PIXEL_GAPS, PIXEL_HINTS = "none", [], []
finally:
    if sys.path and sys.path[0] == str(Path(__file__).resolve().parent):
        sys.path.pop(0)

try:                                    # 此时 PIL 要么是真的，要么是上面挂进来的兜底
    from PIL import Image               # type: ignore
    HAS_PIL = True
except Exception:                       # noqa: BLE001
    Image = None                        # type: ignore
    HAS_PIL = False
if PIXEL_GAPS:                          # 自检有缺口＝本次量出来的数不可信，当没有像素能力
    HAS_PIL = False
    PIXEL_SOURCE = "none"
elif HAS_PIL and PIXEL_SOURCE == "none":
    PIXEL_SOURCE = "pillow"             # 包内兜底缺席但机器上有真 Pillow


# ─────────────────────────── 通用小工具 ───────────────────────────

def _local(tag) -> str:
    return str(tag).split("}")[-1]


def _f(node, name: str, default: float = 0.0) -> float:
    try:
        return float(node.attrib.get(name, default))
    except (TypeError, ValueError):
        return default


def _box(node) -> tuple[float, float, float, float]:
    return (_f(node, "topLeftX"), _f(node, "topLeftY"),
            _f(node, "width"), _f(node, "height"))


def _text_of(node) -> str:
    return "".join(node.itertext()).strip()


def _rgba(value: str):
    """`rgba(r,g,b,a)` / `rgb(r,g,b)` / `#rrggbb` → (r,g,b,a)；解析不了返回 None。"""
    if not value:
        return None
    v = value.strip()
    m = re.match(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)", v)
    if m:
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (float(m.group(1)), float(m.group(2)), float(m.group(3)), a)
    m = re.match(r"#([0-9a-fA-F]{6})$", v)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    return None


def _lum(rgb) -> float:
    """WCAG 相对亮度。"""
    def ch(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def _contrast(a, b) -> float:
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _blend(fg, bg):
    """fg 带 alpha 压在 bg 上的实际颜色。"""
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def _text_width(text: str, pt: float) -> float:
    """一行文字的字面宽度（px）。CJK 按 1.0em，拉丁与数字按 0.55em，空格 0.3em。"""
    w = 0.0
    for ch in text:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF:
            w += 1.0
        elif ch == " ":
            w += 0.3
        else:
            w += 0.55
    return w * pt


def _parse_gradient(value: str):
    """`linear-gradient(90deg, rgba(...) 0%, …)` → (角度, [(位置0-1, alpha), …])。"""
    head = re.match(r"linear-gradient\(\s*(-?[\d.]+)deg\s*,(.*)\)\s*$", (value or "").strip(), re.S)
    if not head:
        return None
    stops = []
    for m in re.finditer(r"rgba?\(([^)]*)\)\s*([\d.]+)%", head.group(2)):
        parts = [float(x) for x in m.group(1).split(",")]
        stops.append((float(m.group(2)) / 100.0, parts[3] if len(parts) > 3 else 1.0))
    return (float(head.group(1)), sorted(stops)) if stops else None


def _grad_alpha_at(stops, pos: float) -> float:
    if pos <= stops[0][0]:
        return stops[0][1]
    if pos >= stops[-1][0]:
        return stops[-1][1]
    for (p0, a0), (p1, a1) in zip(stops, stops[1:]):
        if p0 <= pos <= p1:
            span = max(p1 - p0, 1e-9)
            return a0 + (a1 - a0) * (pos - p0) / span
    return stops[-1][1]


def _grad_axis_pos(deg: float, x: float, y: float, box) -> float:
    """CSS 口径：0deg 向上、90deg 向右。返回该点在渐变轴上的 0–1 位置。"""
    rad = math.radians(deg)
    dx, dy = math.sin(rad), -math.cos(rad)
    cx, cy = box[0] + box[2] / 2.0, box[1] + box[3] / 2.0
    span = abs(box[2] * dx) + abs(box[3] * dy)
    return 0.5 + ((x - cx) * dx + (y - cy) * dy) / max(span, 1e-9)


# ─────────────────────────── 页面模型 ───────────────────────────

class Block:
    """页面上的一个元素，判据都读它。"""

    def __init__(self, node, order: int):
        self.node = node
        self.order = order
        self.kind = _local(node.tag)                 # shape / img / line / chart / table
        self.type = node.attrib.get("type", "")      # text / rect / ellipse…
        self.box = _box(node)
        self.text = _text_of(node)
        self.src = node.attrib.get("src", "")
        # 裁切意图必须拆开记：anchor 只有与实际裁切轴同向才真的保护主体；
        # 四个 offset 是宿主回读形态，不是稳定的创作接口（slides-xml §二明确禁写）。
        self.crop_anchor = ""
        self.crop_offsets = (0.0, 0.0, 0.0, 0.0)
        for c in node.iter():
            if _local(c.tag) == "crop":
                self.crop_anchor = (c.attrib.get("anchor") or "").strip().lower()
                vals = []
                for k in ("leftOffset", "rightOffset", "topOffset", "bottomOffset"):
                    try:
                        vals.append(float(c.attrib.get(k, 0) or 0))
                    except (TypeError, ValueError):
                        vals.append(0.0)
                self.crop_offsets = tuple(vals)
                break
        self.crop_declared = bool(self.crop_anchor)
        content = next((c for c in node.iter() if _local(c.tag) == "content"), None)
        self.content = content
        self.text_type = (content.attrib.get("textType", "") if content is not None else "")
        self.autofit = (content.attrib.get("autoFit", "") if content is not None else "")
        self.fill = None
        for c in node.iter():
            if _local(c.tag) == "fillColor" and c.attrib.get("color"):
                self.fill = c.attrib["color"]
                break
        self.paras = self._paragraphs()

    def _paragraphs(self):
        """[(文本, 字号, bold)]，逐段——量容量必须逐段累加，只看最大字号会漏。"""
        out = []
        if self.content is None:
            return out
        base = _f(self.content, "fontSize", 0.0)
        for p in self.content.iter():
            if _local(p.tag) != "p":
                continue
            spans = [s for s in p.iter() if _local(s.tag) == "span"]
            txt = "".join(p.itertext())
            if spans:
                pt = max((_f(s, "fontSize", base) for s in spans), default=base)
                bold = any(str(s.attrib.get("bold", "")).lower() == "true" for s in spans)
            else:
                pt, bold = base, str(self.content.attrib.get("bold", "")).lower() == "true"
            out.append((txt, pt or base or 14.0, bold))
        return out

    @property
    def is_text(self) -> bool:
        return self.type == "text" or (self.content is not None and bool(self.text))

    @property
    def font_color(self):
        if self.content is None:
            return None
        for s in self.content.iter():
            if _local(s.tag) == "span" and s.attrib.get("color"):
                return _rgba(s.attrib["color"])
        return _rgba(self.content.attrib.get("color", ""))

    @property
    def max_pt(self) -> float:
        return max((p[1] for p in self.paras), default=0.0)


class Page:
    def __init__(self, path: Path, xml: str):
        self.path = path
        self.raw = xml
        self.header = " ".join(re.findall(r"<!--(.*?)-->", xml[:1200], re.S))
        self.root = ET.fromstring(xml)
        self.blocks = [Block(n, i) for i, n in enumerate(self.root.iter())
                       if _local(n.tag) in ("shape", "img", "line", "chart", "table")]
        self.ground_token = ""
        self.ground_color = ""
        style = next((c for c in self.root if _local(c.tag) == "style"), None)
        if style is not None:
            for n in style.iter():
                if _local(n.tag) == "fillImg" and n.attrib.get("src"):
                    self.ground_token = n.attrib["src"]
                if _local(n.tag) == "fillColor" and n.attrib.get("color"):
                    self.ground_color = n.attrib["color"]

    @property
    def texts(self):
        return [b for b in self.blocks if b.is_text and b.text]

    @property
    def images(self):
        return [b for b in self.blocks if b.kind == "img"]

    @property
    def canvas_image(self):
        """页地是不是一张画面（slide 级 fillImg 或近满版 <img>）。"""
        if self.ground_token:
            return (0.0, 0.0, CANVAS_W, CANVAS_H)
        for b in self.images:
            if b.box[2] * b.box[3] >= 0.85 * CANVAS_W * CANVAS_H:
                return b.box
        return None


def _header_value(page: "Page", key: str) -> str:
    """页头 `key=value`；值可用引号包住，或到下一个已知字段为止。"""
    head = page.header or ""
    quoted = re.search(rf"\b{re.escape(key)}\s*=\s*(['\"])(.*?)\1", head, re.S)
    if quoted:
        return quoted.group(2).strip()
    hit = re.search(
        rf"\b{re.escape(key)}\s*=\s*(.*?)"
        rf"(?=\s+(?:job|device|ground|reuse|deliver|cover)\s*=|$)", head, re.S)
    return hit.group(1).strip(" <>-；;") if hit else ""


def _side_cover(page: "Page"):
    """满版图上 ≥30% 的不透明实色覆盖块；只用于核对是否下过 E-b 空面订单。"""
    if page.canvas_image is None:
        return []
    out = []
    for b in page.blocks:
        if b.kind != "shape" or b.text or not b.fill or "gradient" in b.fill:
            continue
        rgba = _rgba(b.fill)
        share = b.box[2] * b.box[3] / (CANVAS_W * CANVAS_H)
        if rgba and rgba[3] >= 0.90 and share >= 0.30:
            out.append(b)
    return out




_TEXTURE_WORDS = ("底纹", "纹理", "材质", "肌理", "实色", "平色", "色地", "底板",
                  "backplate", "texture", "pattern")


def _ground_src(page: "Page") -> str:
    """这一页的地用的是哪张图（slide 级 fillImg，或近满版的那张 img）。"""
    return page.ground_token or next(
        (b.src for b in page.images if b.box[2] * b.box[3] >= 0.85 * CANVAS_W * CANVAS_H), "")


def _ground_is_picture(page: "Page", deck_dir: Path) -> bool:
    """这一页的地是**画面**（有主体、有焦点），还是只是一块底纹／实色？

    两个口径，真值优先：
      ① 图能在本地打开 → **按安静区判**：底纹几乎整张都是安静区（真稿实测 93–100%），
         画面只有一小片（31–48%）。
         ✗ 不要用「忙块占比」——密而浅的图案底纹忙块占比能到 0.41，比真画面还高，会被当成画面。
      ② 打不开（已换成宿主 token）→ 读页面头注释里执行者自己写的 `ground=…`。
    **底纹不是画面**：它盖住的地方仍然是空的——这一条决定「空档」那一族判不判。
    """
    if page.canvas_image is None:
        return False
    im = _load_asset(_ground_src(page), deck_dir)
    if im is not None:
        zone = _quiet_zone(im)
        share = (zone[2] * zone[3] / (CANVAS_W * CANVAS_H)) if zone else 0.0
        return share < TEXTURE_QUIET_MIN
    head = page.header
    if head and any(w in head for w in _TEXTURE_WORDS):
        return False
    return True


def _largest_empty_rect(page: "Page", cell: int = 20):
    """声明几何栅格化后最大的一块空矩形 → (占版, 方位, 像素框)。

    只给**事实**：这一片有多大、在哪。它是不是缺陷由执行者按 page-craft §五
    的遮挡测试判——面积本身分不开好坏（32% 空白的字体样张页是金标准）。
    """
    cx, cy = int(CANVAS_W // cell), int(CANVAS_H // cell)
    grid = [[True] * cx for _ in range(cy)]
    for b in page.blocks:
        x, y, w, h = b.box
        if w <= 0 or h <= 0 or w * h >= 0.85 * CANVAS_W * CANVAS_H:
            continue
        if b.is_text and b.max_pt <= 11:
            continue                                   # 家具层不算内容
        for gy in range(max(0, int(y // cell)), min(cy, int((y + h) // cell) + 1)):
            for gx in range(max(0, int(x // cell)), min(cx, int((x + w) // cell) + 1)):
                grid[gy][gx] = False
    best = (0, None)
    for y0 in range(cy):
        for y1 in range(y0 + 3, cy + 1):
            for x0 in range(cx):
                for x1 in range(x0 + 5, cx + 1):
                    if (x1 - x0) * (y1 - y0) <= best[0]:
                        continue
                    if all(grid[yy][xx] for yy in range(y0, y1) for xx in range(x0, x1)):
                        best = ((x1 - x0) * (y1 - y0), (x0, y0, x1, y1))
    if not best[1]:
        return 0.0, "", None
    x0, y0, x1, y1 = best[1]
    share = best[0] / (cx * cy)
    vert = "上" if y0 <= 1 else ("下" if y1 >= cy - 1 else "中")
    horz = "左" if x0 <= 1 else ("右" if x1 >= cx - 1 else "中")
    where = (vert + horz).replace("中中", "版心")
    return share, where, (x0 * cell, y0 * cell, (x1 - x0) * cell, (y1 - y0) * cell)


def _ink_box(b: "Block") -> tuple[float, float, float, float]:
    """字**真正占的那一块**。框常比字面宽得多，按框判会报出一堆假重叠/假半块底。"""
    x0, y0, w0, h0 = b.box
    ink_w = ink_h = 0.0
    for txt, pt, _bd in b.paras:
        if not txt.strip():
            ink_h += pt * INK_FACTOR
            continue
        lines = max(1, math.ceil(_text_width(txt, pt) / max(w0 * 1.04 - 4, 1)))
        ink_w = max(ink_w, min(w0, _text_width(txt, pt)))
        ink_h += lines * pt * INK_FACTOR
    return (x0, y0, min(w0, ink_w or w0), min(h0 + 4, ink_h or h0))


def _page_signature(page: "Page") -> tuple:
    """这一页的**骨架签名**：块按面积档与位置格粗粒度化。用来看跨页同构。"""
    sig = []
    for b in page.blocks:
        x, y, w, h = b.box
        if w <= 0 or h <= 0:
            continue
        if b.is_text and b.max_pt <= 11:
            continue
        kind = "I" if b.kind == "img" else ("T" if b.is_text else "S")
        sig.append((kind, int(x // 96), int(y // 54), int(w // 96), int(h // 54)))
    return tuple(sorted(sig))


# ─────────────────────────── 判据 ───────────────────────────

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF]")
MD_RE = re.compile(r"\*\*[^*\n]{1,40}\*\*|^\s*[-*]\s+|^#{1,6}\s+|`[^`\n]{1,30}`", re.M)
PLACEHOLDER_RE = re.compile(r"^@|^IMG_\d|<[A-Z_]+>|待填|TODO", re.I)


def _find(path: Path, deck_dir: Path | None = None):
    """返回 (errors, notes, page)；前两项每条是 (码, 文本)，page 供收尾的看图清单用。"""
    errors: list[tuple[str, str]] = []
    notes: list[tuple[str, str]] = []
    raw = path.read_text(encoding="utf-8", errors="replace")

    try:
        page = Page(path, raw)
    except ET.ParseError as exc:
        return [("XML-001", f"XML 不良构：{exc}。常见三种成因：注释里出现连续两个短横 `--`／"
                            "正文里的 & < > 没转义／标签没闭合")], [], None

    if "xmlns" not in raw[:400]:
        notes.append(("XML-002", "根元素没写 xmlns——多数宿主能容忍，但回读会不一致；"
                                 "照 slides-xml.md §一 补上。"))

    # ── 语法与写法 ─────────────────────────────────────────────
    ids: dict[str, int] = {}
    for b in page.blocks:
        bid = b.node.attrib.get("id", "")
        if bid:
            ids[bid] = ids.get(bid, 0) + 1
    for bid, n in ids.items():
        if n > 1:
            errors.append(("XML-003", f"id=\"{bid}\" 出现 {n} 次——服务端分配 id，自造的会跨页撞车。"
                                      "（slides-xml.md §一）"))

    for b in page.blocks:
        if b.type == "text" and b.content is not None and not any(
                _local(p.tag) == "p" for p in b.content.iter()):
            errors.append(("TXT-001", f"文本块 @{b.box[0]:.0f},{b.box[1]:.0f} 里没有 <p>——"
                                      "宿主会照建成空文本框，成稿与导出的 PPT 都是 0 字。"))
        if b.content is not None:
            ls = b.content.attrib.get("lineSpacing", "")
            if ls and not re.match(r"^(multiple|fixed):", ls):
                errors.append(("TXT-002", f"lineSpacing=\"{ls}\" 缺单位前缀，渲染层拒收（slides-xml.md §二④）。"))
            if b.content.attrib.get("align"):
                notes.append(("TXT-003", "`<content align=…>` 不生效；文字对齐写 textAlign。"))
        for attr in ("opacity", "fillOpacity"):
            if b.node.attrib.get(attr):
                notes.append(("TXT-004", f"`{attr}` 不生效；透明度写进 rgba(...) 的第四位。"))
        if (b.fill and "gradient" in b.fill and not _parse_gradient(b.fill)
                and not re.search(r"rgba?\([^)]*\)\s*[\d.]+%", b.fill)):
            errors.append(("FILL-001", f"渐变写法不合宿主要求：{b.fill[:60]}…——服务端会把整块回落成白色"
                                       "（写法见 slides-xml.md §三）。"))
        if b.kind == "img" and PLACEHOLDER_RE.search(b.src or ""):
            errors.append(("IMG-001", f"图片 src 还是占位符 `{b.src[:40]}`——宿主只认 file_token，外链与占位都不渲染。"))
    for b in page.texts:
        if EMOJI_RE.search(b.text):
            errors.append(("TXT-005", f"文字里有 emoji：「{EMOJI_RE.search(b.text).group(0)}」——全稿禁止。"))
        m = MD_RE.search(b.text)
        if m:
            errors.append(("TXT-006", f"文字里混进了 markdown：「{m.group(0)[:20]}」——渲染层不解析，"
                                      "这几个符号会原样印在页面上。"))

    if re.search(r"<prompt\b", raw):
        errors.append(("HOST-001", "payload 里出现 `<prompt>`——那是描述型写入工具的方言，"
                                   "它只读一段文字描述、会把你写的几何全部丢掉。"
                                   "本 Skill 提交的是完整 `<slide>` 几何（slides-xml.md §一）。"))

    # `<line>` 的几何：宿主只认起止点，写成 topLeft/width/height 会整页写入失败
    for node in page.root.iter():
        if _local(node.tag) != "line":
            continue
        if not {"startX", "startY", "endX", "endY"} <= set(node.attrib):
            errors.append(("LINE-001", "`<line>` 写成了 topLeft/width/height——"
                                       "宿主只认起止点，这样写**整页写入会被拒收**"
                                       "（竖线写 width=\"0\" 是最常见的一种）。"
                                       "正确写法见 slides-xml.md §4.8；"
                                       "要一条有厚度的色带就改用 `<shape type=\"rect\">`。"))
            break

    # 注释里的连续两个短横：XML 规定注释内不许出现，整页会解析不出来
    for m in re.finditer(r"<!--(.*?)-->", raw, re.S):
        if "--" in m.group(1):
            errors.append(("XML-004", "注释块里出现了连续两个短横（`--`）——"
                                      "XML 规定注释内不许有它，**整页会解析不出来**，"
                                      "这一页的判据一条都跑不了。"))
            break

    for b in page.blocks:
        # shape 里套 <style>：宿主 schema 不认，这块形渲不出填充
        if b.kind == "shape" and any(_local(c.tag) == "style" for c in b.node):
            errors.append(("SML-004", f"`<shape>` @{b.box[0]:.0f},{b.box[1]:.0f} 里套了 `<style>`"
                                      "——宿主 schema 不认，这块形渲不出填充"
                                      "（形的填充直接写 `<fill>`，见 slides-xml.md §三）。"))
        # 有面积、无填充、也无文字的形：宿主渲成完全透明＝页面上什么都没有
        if (b.kind == "shape" and b.type != "text" and not b.fill and not b.text
                and b.box[2] * b.box[3] >= 0.02 * CANVAS_W * CANVAS_H
                and not any(_local(c.tag) in ("fill", "outline", "stroke", "border",
                                              "shadow", "line", "img") for c in b.node)):
            errors.append(("FILL-002", f"一块 {b.box[2]:.0f}×{b.box[3]:.0f} 的形既没有 `<fill>` "
                                       "也没有描边和文字——宿主会把它渲成完全透明。"
                                       "它要么该有内容，要么该删掉。"))
        # 负字距 / 超大字距
        if b.content is not None:
            for node in b.node.iter():
                ls = node.attrib.get("letterSpacing")
                if ls is None:
                    continue
                try:
                    v = float(ls)
                except ValueError:
                    continue
                if v <= -6:
                    # 轻微负字距（参照样本用到 -1 ~ -3）是 display 的排版惯例；
                    # 真正的缺陷是 -10/-20 这一档：宿主原样执行，字面直接压叠。
                    errors.append(("TXT-013", f"字距 {v:g}——负到这一档宿主会把字面压叠在一起。"
                                              "字距只加宽不压缩（page-craft §3.2）。"))
                break

    # 一页出现多个满版块：宿主只保留一个，另一个会被降级，满版就此塌掉
    fulls = [b for b in page.blocks
             if b.box[2] >= 0.97 * CANVAS_W and b.box[3] >= 0.97 * CANVAS_H
             and (b.kind == "img" or b.fill)]
    if len(fulls) >= 2 and page.ground_token:
        errors.append(("LC-001", f"这一页有 {len(fulls)} 个满版块，而页地本身已经是一张满版图——"
                                 "宿主在两个满版之间只会保留一个，另一个会被降级成居中卡片，"
                                 "满版就此塌掉。地只能有一层（page-craft §L0）。"))

    # E-b 不是“半版看起来像不像”的审美门，而是订单有没有明确写过空面。
    # 只管本 Skill 自己带页头的页面；无页头的外部/金标准语料不触发。
    covers = _side_cover(page)
    owned_page = bool(re.search(r"\b(?:job|device|ground|deliver)\s*=", page.header or ""))
    if covers and owned_page:
        declared = _header_value(page, "cover")
        page.cover_reason = declared
        if not declared:
            b = covers[0]
            errors.append(("GRD-005", f"满版图上有一块 {b.box[2]:.0f}×{b.box[3]:.0f} 的不透明实色覆盖"
                                      "（占版 %.0f%%），但页头没有 `cover=`。这不是在判板好不好看，"
                                      "而是在核对：下单时有没有写死被盖侧是空面。没有这条订单，"
                                      "主体是否被板边切断在 XML 里无法证明。"
                                      "（下面是建议，按本页实际画面调整，不是必须照做：改用 E-a 侧图窗，"
                                      "或重新为 E-b 下单并把真实空面写进 `cover=`。）"
                                      % (b.box[2] * b.box[3] / (CANVAS_W * CANVAS_H) * 100)))
        else:
            notes.append(("GRD-005", f"本页 E-b 声明 `cover={declared}`；这只证明下过空面订单，"
                                     "不证明成品做对了，宿主截图还要核对主体有没有骑在分界上。"))

    # 声明了原生图表却没有 <chart>；以及用矩形拼柱子
    if re.search(r"graphic\s*=\s*G15", page.header):
        if not any(_local(n.tag) == "chart" for n in page.root.iter()):
            errors.append(("CHART-001", "页面头写了 `graphic=G15`（原生图表），但页面上没有 `<chart>` 元素。"
                                        "图表只认原生 `<chart>`——矩形拼的柱子是线框图，"
                                        "图表做成图片则连数字都改不了（page-craft D18）。"))
    bars = [b for b in page.blocks
            if b.kind == "shape" and b.type != "text" and b.fill and not b.text
            and b.box[2] > 0 and b.box[3] > 0 and b.box[3] > b.box[2] * 1.5
            and 0.002 <= b.box[2] * b.box[3] / (CANVAS_W * CANVAS_H) <= 0.10]
    if len(bars) >= 3:
        base = {round(b.box[1] + b.box[3]) for b in bars}
        if len(base) <= 2 and len({round(b.box[3]) for b in bars}) >= 3:
            digits = sum(1 for t in page.texts if re.fullmatch(r"[\d.,%％]+", t.text.strip()))
            if digits >= 2 and not any(_local(n.tag) == "chart" for n in page.root.iter()):
                notes.append(("CHART-002", f"有 {len(bars)} 根同基线、长短不一的无字矩形，"
                                           f"页面上还有 {digits} 个数字——**这看起来是用矩形拼的柱状图**。"
                                           "≥3 个可比数值就该用原生 `<chart>`（page-craft D18）。"))

    # 讲稿：渲染层的规矩是每页 3–5 句可直接照读的话
    note_node = next((n for n in page.root.iter() if _local(n.tag) == "note"), None)
    note_text = "".join(note_node.itertext()).strip() if note_node is not None else ""
    if note_node is None:
        errors.append(("NOTE-001", "这一页没有 `<note>` 讲稿。每页要 3–5 句可直接照读的话——"
                                   "它写在页面渲染之外，加它不动任何一处版面。"))
    elif len(note_text) < 20:
        notes.append(("NOTE-002", f"讲稿只有 {len(note_text)} 字——每页要 3–5 句可直接照读的话，"
                                  "这一页交出去演讲者得自己现编。"))

    # 托底板没包住它托的那块字
    for t in page.texts:
        if t.max_pt < 12:
            continue
        for b in page.blocks:
            if b.order >= t.order or b.kind != "shape" or not b.fill or b.text:
                continue
            f = _rgba(b.fill)
            if not f or f[3] < 0.25:
                continue
            tb = _ink_box(t)
            ox = min(b.box[0] + b.box[2], tb[0] + tb[2]) - max(b.box[0], tb[0])
            oy = min(b.box[1] + b.box[3], tb[1] + tb[3]) - max(b.box[1], tb[1])
            if ox <= 2 or oy <= 2:
                continue
            covered = ox * oy / max(tb[2] * tb[3], 1)
            panel_ratio = (b.box[2] * b.box[3]) / max(tb[2] * tb[3], 1)
            if 0.40 <= covered < 0.80 and panel_ratio <= 4.0:
                errors.append(("TXT-009", f"托底板 {b.box[2]:.0f}×{b.box[3]:.0f} 只盖住了"
                                          f"「{t.text[:8]}」的 {covered:.0%}——字有一截露在板外，"
                                          "读者看到的是半块底。托片要么完整包住它，要么不要用"
                                          "（page-craft §四）。"))
                break

    # ── 几何 ───────────────────────────────────────────────────
    for b in page.blocks:
        x, y, w, h = b.box
        if w <= 0 or h <= 0:
            continue
        # **容差要分方向、分块型。** 贴边 rail 与英文标签常压线 ≤16px，那不是缺陷；
        # 但 <24pt 的文字块越出**上下沿**从来不是手法——宿主按画布裁，
        # 渲染出来就是一行被切掉半截的字，而 XML 里一点痕迹都没有。
        BLEED = 24.0                                   # 图、色带、≥24pt 巨字的出血容差
        small_text = b.is_text and bool(b.text) and b.max_pt < 24
        v_bleed = 2.0 if small_text else BLEED         # 小字上下沿几乎零容差
        if (x < -BLEED or y < -v_bleed
                or x + w > CANVAS_W + BLEED or y + h > CANVAS_H + v_bleed):
            # 出血是成文手法：只有**文字块**越界才判（图与色块可以出血）
            ink_w = min(w, max((_text_width(t, pt) for t, pt, _bd in b.paras), default=w)) if b.paras else w
            over_right = x + ink_w > CANVAS_W + BLEED
            over_other = x < -BLEED or y < -v_bleed or y + h > CANVAS_H + v_bleed
            if small_text and (over_right or over_other):
                where = ("下沿" if y + h > CANVAS_H + v_bleed else
                         "上沿" if y < -v_bleed else "右界" if over_right else "左轴外")
                extra = ("——宿主按画布裁，这一行会被切掉半截，"
                         "而 XML 里看不出来。" if where in ("上沿", "下沿") else
                         "——出血是留给图、色带与 ≥24pt 巨字的手法，"
                         "正文出界只会被读成排版错误。")
                errors.append(("LAY-001", f"{b.max_pt:.0f}pt 文字块「{b.text[:10]}」越出画布"
                                          f"{where}：x{x:.0f} y{y:.0f} w{w:.0f} h{h:.0f}"
                                          f"（底沿 {y + h:.0f}，画布 "
                                          f"{CANVAS_W:.0f}×{CANVAS_H:.0f}）。" + extra))
            else:
                notes.append(("LAY-002", f"{b.kind} 越出画布 x{x:.0f} y{y:.0f} w{w:.0f} h{h:.0f}"
                                         "——出血是合法手法，确认这是你要的效果。"))

    # 底部呼吸只抓一个高分离形状：不透明、非出血、有面积的浮动矩形卡片贴底。
    # 裸的「内容离底 <N」会把页脚、通高色域、贴边图和半透明柱一起判死，所以不做。
    for b in page.blocks:
        x, y, w, h = b.box
        rgba = _rgba(b.fill or "")
        area = w * h
        non_bleed = x > 0.5 and x + w < CANVAS_W - 0.5 and y > 0.5
        if (b.kind == "shape" and b.type == "rect" and rgba and rgba[3] >= 0.90
                and non_bleed and 3000 <= area < 0.85 * CANVAS_W * CANVAS_H):
            gap = CANVAS_H - (y + h)
            if gap < BOTTOM_CARD_GAP:
                errors.append(("LAY-024", f"这块 {w:.0f}×{h:.0f} 的不透明浮动卡下沿在 y{y+h:.0f}，"
                                          f"离页面底边只有 {gap:.0f}px（本形状的呼吸线是 "
                                          f"{BOTTOM_CARD_GAP:.0f}px）。"
                                          "出血块、半透明通高色域与页脚家具不在此门内。"
                                          "（下面只是建议，必须按本页实际情况调整：把这一组整体上移，"
                                          "或压缩卡片高度，让卡片与页脚/底边重新分开。）"))

    # 文本容量：逐段累加，尊重 autoFit 的 0.7× 下限
    for b in page.texts:
        x, y, w, h = b.box
        if w <= 4 or h <= 4 or not b.paras:
            continue
        # **display 与单字巨字豁免**：巨字出框是成文手法（大字出血/幽灵字），
        # 参照库 135 页里容量比最高的十条全是 150–320pt 的单字。
        # 判据只管**真正装不下的正文**：多段、或字数够多的那一类。
        display = b.max_pt >= 40
        glyph_count = sum(len(t.strip()) for t, _pt, _bd in b.paras)
        if display and glyph_count <= 3:
            continue          # 巨号／幽灵巨字：框故意小于字面，压住下层是它的构图（D7/D9）
        body_chars = sum(len(t.strip()) for t, _pt, _bd in b.paras)
        if not display and body_chars <= 6 and len(b.paras) <= 1:
            continue
        scale = AUTOFIT_FLOOR if b.autofit else 1.0
        need = 0.0
        for txt, pt, _bold in b.paras:
            if not txt.strip():
                need += pt * scale * LINE_FACTOR
                continue
            lines = max(1, math.ceil(_text_width(txt, pt * scale) / max(w * 1.04 - 4, 1)))
            need += lines * pt * scale * LINE_FACTOR
        # 两种情形才算缺陷：① 严重装不下（>2.2×，参照库最大 2.16）；
        # ② 溢出的那几行**撞上了下面的块**——那是读者真的看到的损坏。
        # display 巨字出框是成文手法（大字出血、幽灵字），参照库里到处都是——
        # 所以巨字**不按"装不下"判**，只按"它溢出的行有没有压住下面的内容"判：
        # 那才是读者真正看到的损坏（封面标题压住副标题就是这一种）。
        severe = (need > h * 2.2 + 2) and not display
        # 碰撞按**字真正占的高**算：按预算值算会把「两行 72pt 紧挨着」这种
        # 正常的行叠判成碰撞（外部参照稿实测）。
        ink_need = need / LINE_FACTOR * INK_FACTOR
        collide = False
        if ink_need > h * 1.35 + 6:
            spill = (x, y + h, w, ink_need - h)
            for other in page.blocks:
                if other is b or other.kind == "line" or not (other.is_text or other.fill):
                    continue
                if other.box[2] <= 0 or other.box[3] <= 0:
                    continue
                if other.box[2] * other.box[3] >= 0.85 * CANVAS_W * CANVAS_H:
                    continue
                ox = min(spill[0] + spill[2], other.box[0] + other.box[2]) - max(spill[0], other.box[0])
                oy = min(spill[1] + spill[3], other.box[1] + other.box[3]) - max(spill[1], other.box[1])
                if ox > 8 and oy > 8:
                    collide = True
                    break
        if severe or collide:
            over = need - h
            fit_pt = max(6.0, b.max_pt * (h / max(need, 1e-6)))
            tail = ("；溢出的行正压在下面那一块上" if collide else "")
            errors.append(("TXT-010", f"「{b.text[:12]}」装不下自己的框{tail}："
                                      f"需要 {need:.0f}px，框只有 {h:.0f}px（差 {over:.0f}px）。"
                                      "容量不足的正解是**删、拆、换结构**，不是缩字号——字阶是全稿的（page-craft §3.2、§五文字预算）。"))

    # 文字互压
    # 幽灵层（alpha ≤0.5）与 display 巨字（≥40pt）叠印是成文装置（page-craft D9），
    # 判据只管**两块实色正文**真的叠在一起。
    solid = [b for b in page.texts
             if (b.font_color is None or b.font_color[3] >= 0.5)
             and 12 <= b.max_pt < 40]
    _ink = _ink_box

    def _cjk_ratio(t: str) -> float:
        letters = [ch for ch in t if not ch.isspace()]
        if not letters:
            return 0.0
        return sum(1 for ch in letters if 0x4E00 <= ord(ch) <= 0x9FFF) / len(letters)

    for i, a in enumerate(solid):
        for c in solid[i + 1:]:
            # 中文大字 ＋ 拉丁微标签的**贴叠**是成文装置（双语配对），不是碰撞
            if abs(_cjk_ratio(a.text) - _cjk_ratio(c.text)) > 0.5:
                continue
            if max(a.max_pt, c.max_pt) / max(min(a.max_pt, c.max_pt), 1) >= 1.8:
                continue                      # 标题压标签的层叠同理
            def _is_column(b: Block) -> bool:
                return b.box[3] >= 3 * max(b.box[2], 1)   # 高远大于宽＝竖排列
            if _is_column(a) and _is_column(c):
                continue                      # 两条竖排列：相邻列的声明框天然交叠
            ab, cb = _ink(a), _ink(c)
            ox = min(ab[0] + ab[2], cb[0] + cb[2]) - max(ab[0], cb[0])
            oy = min(ab[1] + ab[3], cb[1] + cb[3]) - max(ab[1], cb[1])
            if ox > 4 and oy > 4:
                if a.text.strip() == c.text.strip():
                    continue          # 同一句话的两块＝色板与其上文字，不是碰撞
                small = min(ab[2] * ab[3], cb[2] * cb[3])
                if ox * oy > 0.35 * small and ox * oy >= 400 and oy >= 8:
                    errors.append(("TXT-011", f"两块实色文字互压：「{a.text[:8]}」与「{c.text[:8]}」"
                                              f"重叠 {ox:.0f}×{oy:.0f}px。"
                                              "（两块实色正文叠在一起就是错的；幽灵层与巨字叠印是另一回事，见 page-craft D9。）"))

    # 图盖住文字（层序＝文档顺序）：纯几何、无像素依赖，对应 IMG-012。
    for img in page.images:
        ib = img.box
        if ib[2] * ib[3] >= 0.85 * CANVAS_W * CANVAS_H:
            continue                                  # 满版底层，文字压它是正常形态
        for t in page.texts:
            if t.order >= img.order:
                continue                              # 文字在图之后＝压在图上，那是正当手法
            if t.max_pt < 12 and t.text_type not in ("body", "title", "headline", "subtitle"):
                continue                              # 家具层小字豁免
            if (t.font_color and t.font_color[3] <= 0.5) or t.max_pt >= 40:
                continue                              # 幽灵字被主体部分遮挡是成文装置
            ox = min(ib[0] + ib[2], t.box[0] + t.box[2]) - max(ib[0], t.box[0])
            oy = min(ib[1] + ib[3], t.box[1] + t.box[3]) - max(ib[1], t.box[1])
            if ox > 2 and oy > 2:
                cover = ox * oy / max(t.box[2] * t.box[3], 1)
                if cover > 0.12 and re.search(r"\b(?:job|device|ground|deliver)\s*=", page.header or ""):
                    errors.append(("IMG-021", f"后写入的图 @{ib[0]:.0f},{ib[1]:.0f} "
                                               f"{ib[2]:.0f}×{ib[3]:.0f} 在层序上盖住了文字"
                                               f"「{t.text[:10]}」的 {cover:.0%}。这块字在宿主里会被图压住。"
                                               "（下面是建议，按本页实际关系调整，不是必须照做："
                                               "改变层序，或重排其中一块，直到两者不再互相遮挡。）"))

    # LAY-003 天沟：整列内容的边线与图的边线**完全重合**（不是"挨得近"，是被对齐到了图沿上）
    for img in page.images:
        ix, iy, iw, ih = img.box
        if iw <= 0 or ih <= 0 or iw * ih >= 0.85 * CANVAS_W * CANVAS_H:
            continue
        for side, edge in (("右", ix + iw), ("左", ix)):
            flush = [t for t in page.texts
                     if t.max_pt >= 12
                     and abs((t.box[0] if side == "右" else t.box[0] + t.box[2]) - edge) <= 2
                     and t.box[1] + t.box[3] > iy and t.box[1] < iy + ih]
            if len(flush) >= 2:
                want = edge + 24 if side == "右" else edge - 24
                errors.append(("LAY-003", f"{len(flush)} 块内容的边线与图{side}沿 x={edge:.0f} "
                                          f"**完全重合**（图 x{ix:.0f} y{iy:.0f} "
                                          f"w{iw:.0f} h{ih:.0f}）——字直接贴在图边上，没有天沟。"
                                          "——这不是「挨得近」，是整列的 x 被对齐到了图的边沿上。"
                                          "**修时整列一起挪**（只挪贴死的那一两块，剩下的会变成新的最紧处）；"
                                          "天沟规矩见 page-craft §3.3。"))
                break

    # 对比度：只在**实色地**上判（图上的对比度由看图判）
    bg = _rgba(page.ground_color) if page.ground_color else None
    if bg and not page.ground_token:
        for t in page.texts:
            fc = t.font_color
            if not fc:
                continue
            pt = t.max_pt
            if pt <= 11:
                continue                              # 家具层豁免（页码/眉标本来就该弱）
            if fc[3] <= 0.5:
                continue                              # 幽灵层：低对比是它的目的
            # **只判底下确实什么都没有的字。** 底下压着色块或图时，XML 说不清
            # 那一片究竟是什么颜色——猜出来的底会把"设计过的弱一档"判成缺陷
            # （参照库实测：色域块上的字算出来低到 1.0:1，而它们全都成立）。
            # 那一类交给 Step 7 看图判。
            covered = False
            for b in page.blocks:
                if b.order >= t.order or b is t:
                    continue
                if b.kind == "line" or (b.kind == "shape" and not b.fill):
                    continue
                ox = min(b.box[0] + b.box[2], t.box[0] + t.box[2]) - max(b.box[0], t.box[0])
                oy = min(b.box[1] + b.box[3], t.box[1] + t.box[3]) - max(b.box[1], t.box[1])
                if ox > 2 and oy > 2:
                    covered = True
                    break
            if covered:
                continue
            under = bg
            # **块自己带底色时，底就是它自己**（`<shape type="rect">` 同时承载文字
            # 是卡片的正解，文档里的数据卡骨架就是这么写的）。
            if t.fill and "gradient" not in t.fill:
                own = _rgba(t.fill)
                if own and own[3] >= 0.9:
                    under = own
            ratio = _contrast(_blend(fc, under[:3]), under[:3])
            # 参照库实测：设计过的「弱一档」正文低到 3.5:1 仍然成立，
            # 所以判据不按 WCAG 的 4.5 走，只抓**真看不清**的那一档。
            # 下沿取自参照样本：微字标签低到 1.9、正文与 display 低到 2.0 仍然成立。
            # 判据只抓**真看不清**（字色≈地色那一类），不判设计过的弱一档。
            need = 1.6 if pt <= 13 else 1.9
            if ratio < need:
                errors.append(("RD-001", f"「{t.text[:10]}」{pt:.0f}pt 在这块底上对比度只有 "
                                         f"{ratio:.1f}:1（这一档的下限是 {need:.1f}:1）——读者看不清。"
                                         "色彩纪律见 page-craft §3.1；✗ 加粗糊不过去。"))

    # ── 图与图窗的物理关系（要能打开源图；打不开就跳过，PIX-000 会说）──────
    for b in page.images:
        x, y, w, h = b.box
        if w <= 0 or h <= 0:
            continue
        im = _load_asset(b.src, deck_dir or path.parent)
        if im is None:
            continue
        sw, sh = im.size
        if sw <= 0 or sh <= 0:
            continue
        want, got = w / h, sw / sh
        drift = abs(want / got - 1) if got else 0
        if drift > MAX_ASPECT_DRIFT:
            lost = 1 - min(want, got) / max(want, got)
            axis = "纵向" if want > got else "横向"
            offsets = getattr(b, "crop_offsets", (0.0, 0.0, 0.0, 0.0))
            if any(abs(v) > 0.5 for v in offsets):
                crop_fact = ("本地 XML 还写了四个 crop offset "
                             f"{tuple(round(v, 1) for v in offsets)}；offset 会随宿主回读变化，"
                             "也不能证明主体完整。")
            elif b.crop_declared:
                anchor = b.crop_anchor
                valid = {"left", "right"} if axis == "横向" else {"top", "bottom"}
                if anchor not in valid:
                    crop_fact = (f"`anchor=\"{anchor or 'center'}\"` 还不在{axis}裁切轴上，"
                                 "宿主会在真正被裁的方向居中取景。")
                else:
                    cut_side = ({"left": "右侧", "right": "左侧", "top": "下侧", "bottom": "上侧"}
                                .get(anchor, "另一侧"))
                    crop_fact = (f"`anchor=\"{anchor}\"` 只会保住 {anchor} 侧、从{cut_side}裁掉约 "
                                 f"{lost:.0%}；它决定裁哪边，不能豁免裁多少。")
            else:
                crop_fact = f"没有 crop 声明，宿主会从中心{axis}裁掉约 {lost:.0%}。"
            errors.append(("IMG-002", f"图窗 {w:.0f}×{h:.0f}（比 {want:.2f}）与源图 "
                                      f"{sw}×{sh}（比 {got:.2f}）差 {drift:.0%}，超过 "
                                      f"{MAX_ASPECT_DRIFT:.0%} 上限。{crop_fact}"
                                      "比例不符的图不得进这个窗（image-direction §一、§六）。"
                                      "（下面只是建议，必须按本页实际情况调整：让图窗对齐源图；"
                                      "需要另一种画幅时重新检索/生成对应画幅，或换一张本来就是该画幅的图。）"))
        scale = max(w / sw, h / sh)
        if scale > 2.0:
            notes.append(("IMG-003", f"源图 {sw}×{sh} 要放大 {scale:.1f}× 才铺满 "
                                     f"{w:.0f}×{h:.0f} 的窗——渲染出来会糊。"))
        if 0.10 <= w * h / (CANVAS_W * CANVAS_H) <= 0.60:
            idle = _idle_band(im)
            if idle >= 0.28:
                notes.append(("IMG-004", f"这张图自己有 {idle:.0%} 的宽度是空的，"
                                         f"而它在页面上只占 {w*h/(CANVAS_W*CANVAS_H):.0%} 版面"
                                         "——非满版的图再自带留白，整页就空掉两次"
                                         "（image-direction §八·1：留白是满版页的做法）。"))

    # ── 装饰条横穿画面中部 ────────────────────────────────────────
    for b in page.images:
        x, y, w, h = b.box
        if w < 0.75 * CANVAS_W or h > 0.16 * CANVAS_H or h <= 0:
            continue
        if y < 0.14 * CANVAS_H or y + h > 0.86 * CANVAS_H:
            continue
        under = [o for o in page.images if o is not b
                 and o.box[2] * o.box[3] >= 0.30 * CANVAS_W * CANVAS_H
                 and o.box[1] <= y and o.box[1] + o.box[3] >= y + h]
        if under or page.ground_token:
            notes.append(("DEV-001", f"一条 {w:.0f}×{h:.0f} 的横带压在画面中部 "
                                     f"(y{y:.0f})——它没有信息职责时就是把画面切成两半。"
                                     "装饰件的位置在页缘（page-craft §一 L4）。"))
            break

    # ── 一簇大小不一的彩色形状在假装成一张画 ────────────────────────
    cluster = [b for b in page.blocks
               if b.kind == "shape" and b.type != "text" and not b.text and b.fill
               and "gradient" not in b.fill
               and (_rgba(b.fill) or (0, 0, 0, 0))[3] >= 0.5
               and b.box[2] * b.box[3] >= 0.002 * CANVAS_W * CANVAS_H]
    if len(cluster) >= 6 and not page.images:
        boxes = [b.box for b in cluster]
        bb = (min(b[0] for b in boxes), min(b[1] for b in boxes),
              max(b[0] + b[2] for b in boxes) - min(b[0] for b in boxes),
              max(b[1] + b[3] for b in boxes) - min(b[1] for b in boxes))
        share = bb[2] * bb[3] / (CANVAS_W * CANVAS_H)
        hues = {tuple(int(v) // 40 for v in (_rgba(b.fill) or (0, 0, 0, 0))[:3]) for b in cluster}
        sizes = collections.Counter((int(round(b[2] / 8)) * 8, int(round(b[3] / 8)) * 8)
                                    for b in boxes)
        uniform = sizes.most_common(1)[0][1] / len(boxes)
        if share >= 0.12 and len(hues) >= 3 and uniform < 0.55:
            notes.append(("COL-001", f"这一区是 {len(cluster)} 个大小不一的彩色形状拼出来的"
                                     f"（{len(hues)} 种颜色，占版 {share:.0%}），里面没有一张真图"
                                     "——用矩形和椭圆拼出来的人/产品/场景，读者一眼就看出是线框。"
                                     "**尺寸齐整的网格（色卡、数据卡、四象限）不在此列**，"
                                     "那是信息图形（`page-craft.md` §二 D13–D22）。"))

    # ── 像素类判据（需要底图落盘 + Pillow）────────────────────────
    _pixel_findings(page, deck_dir or path.parent, errors, notes)

    # ── 空：页面内容覆盖率过低 ───────────────────────────────────
    ink = 0.0
    for b in page.blocks:
        x, y, w, h = b.box
        if w <= 0 or h <= 0 or w * h >= 0.85 * CANVAS_W * CANVAS_H:
            continue
        if b.kind == "line":
            continue
        if b.is_text and b.max_pt <= 11:
            continue                                   # 家具层不算内容
        ink += min(w, CANVAS_W) * min(h, CANVAS_H)
    # 浮图空档：地不是画面、图既不贴边也没有托底/边框，页面还留着成片的空
    if not _ground_is_picture(page, deck_dir or path.parent):
        floats = []
        for b in page.images:
            x, y, w, h = b.box
            share = w * h / (CANVAS_W * CANVAS_H)
            if share < 0.03 or share >= 0.85:
                continue
            # **贴边出血是构图，碰到一条边不是。** 出血的判据是它把一整个方向占满，
            # 或者压住两条以上页缘；只挨着一条边的半版窗仍然是"悬浮的图"。
            edges = sum((x <= 4, y <= 4, x + w >= CANVAS_W - 4, y + h >= CANVAS_H - 4))
            if h >= 0.88 * CANVAS_H or w >= 0.88 * CANVAS_W or edges >= 2:
                continue                                # 出血／撑满＝成文形态
            framed = any(
                o.kind == "shape" and o.fill and o.order < b.order
                and o.box[0] <= x + 2 and o.box[1] <= y + 2
                and o.box[0] + o.box[2] >= x + w - 2 and o.box[1] + o.box[3] >= y + h - 2
                and o.box[0] >= x - 40 and o.box[1] >= y - 40
                for o in page.blocks)
            if not framed:
                floats.append(b.box)
        if len(floats) >= 2:
            share, where, rect = _largest_empty_rect(page)
            if share >= 0.15 and rect:
                notes.append(("LAY-011", f"{len(floats)} 张图悬浮在非画面的地上（不贴边、无托底/边框），"
                                         f"而{where}还留着一片 {share:.0%} 版面的空"
                                         f"（x{rect[0]} y{rect[1]} w{rect[2]} h{rect[3]}）。"
                                         "**这是「底纹/实色地＋悬浮图＋大片空」这一类的形状**——"
                                         "按 page-craft §五做遮挡测试：挡住那片空，构图还完整吗？"
                                         "答不上就说明这一页还没排完——空要么交给内容，"
                                         "要么让图自己占满它（page-craft §五）。"))
    if page.canvas_image is None and ink < 0.18 * CANVAS_W * CANVAS_H and page.texts:
        notes.append(("LAY-010", f"这一页的内容只覆盖了 {ink/(CANVAS_W*CANVAS_H):.0%} 版面，"
                                 "地又不是画面——多半是「还没放东西」。"
                                 "按 page-craft §五做遮挡测试：挡住那片空，构图还完整吗？"
                                 "答不上就重新分布内容或换版式。"))

    # ── 影像：孤零零的小图（提示）────────────────────────────────
    #   ✗ 这里**不判**「一张图跨页复用」：参照库 11 份里 8 份都在跨页复用内容图
    #     （通用底板铺 5 页、材质带铺 4 页、母题小件页页同位），页内同图也有 21 处。
    #     复用是成文机制不是缺陷——全稿的复用账由 `check --deck` 的 IMG-006 只报事实。
    for b, near in _orphan_images(page):
        notes.append(("IMG-005",
                      f"这一页有一张 {b.box[2]:.0f}×{b.box[3]:.0f} 的图"
                      f"（占版 {b.box[2]*b.box[3]/(CANVAS_W*CANVAS_H):.1%}），"
                      f"四周最近的块在 {near:.0f}px 外，与页面上任何块都不共对齐轴。"
                      "**图不是装饰**：要么让它成组（与别的图共用顶线底线、间距相等），"
                      "要么放大到能承担画面，说不出它服务哪一句话就删掉（page-craft §三·3.3）。"))

    # ── 版式：声明的装置 ↔ 实际几何（提示）──────────────────────
    for name, want, got in _device_mismatch(page):
        notes.append(("DEV-002",
                      f"页首写的是 {name}（{want}），但{got}。"
                      "要么把几何做成这个装置该有的样子，要么把 `device=` 改成你实际做的那个"
                      "（page-craft §二）。"))
    return errors, notes, page


#: 上传时写下的「token ↔ 本地文件」对照表文件名。
TOKEN_MAP = "tokens.tsv"


def _asset_dirs(deck_dir: Path):
    """找本地素材的候选目录（顺序固定，供解析与报错口径共用）。"""
    return (deck_dir, deck_dir / "assets", deck_dir.parent,
            deck_dir.parent / "assets", Path("assets"), Path("."))


def _token_map(deck_dir: Path) -> dict:
    """读 `tokens.tsv`：每行 `<file_token>\\t<本地文件名或路径>`。

    **这一张表是像素判据的开关。** 页面 XML 里的 `src` 必须是宿主 token
    （外链与本地路径都不渲染），于是判据在写页之后就再也找不到底图了——
    安静区、大罩、叠图整族因此静默。上传时顺手写一行，它们就全部活过来。
    `hostcheck` 打印的上传命令自带这一行，不需要额外动作。
    """
    table: dict = {}
    for base in _asset_dirs(deck_dir):
        path = base / TOKEN_MAP
        try:
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = re.split(r"[\t=,]| {2,}", line, maxsplit=1)
                if len(parts) != 2:
                    continue
                a, b = parts[0].strip(), parts[1].strip()
                if not a or not b:
                    continue
                # 两个方向都收：`token<TAB>文件` 与 `文件<TAB>token` 都认得。
                table.setdefault(a, b)
                table.setdefault(b, a)
        except OSError:
            continue
    return table


def _token_rows(deck_dir: Path):
    """返回第一份 `tokens.tsv` 的有效行；全稿资产账只跑这一份，避免重复报。"""
    for base in _asset_dirs(deck_dir):
        path = base / TOKEN_MAP
        try:
            if not path.is_file():
                continue
            rows = []
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                parts = re.split(r"[\t=,]| {2,}", line.strip(), maxsplit=1)
                if len(parts) != 2:
                    continue
                a, b = (x.strip() for x in parts)
                if re.fullmatch(r"[A-Za-z0-9_-]{16,80}", a):
                    rows.append((a, b))
                elif re.fullmatch(r"[A-Za-z0-9_-]{16,80}", b):
                    rows.append((b, a))
            return path, rows
        except OSError:
            continue
    return None, []


def _resolve_asset(src: str, deck_dir: Path):
    """把 `<img src>` / fillImg 的值解析成本地文件路径；解析不到返回 None。"""
    if not src:
        return None
    raw = str(src).lstrip("@").lstrip("./")
    candidates = [raw, Path(raw).name]
    mapped = _token_map(deck_dir).get(raw) or _token_map(deck_dir).get(Path(raw).name)
    if mapped:
        candidates = [mapped, Path(mapped).name] + candidates
    for name in candidates:
        if not name:
            continue
        direct = Path(name)
        if direct.is_absolute() and direct.is_file():
            return direct
        for base in _asset_dirs(deck_dir):
            cand = base / name
            if cand.is_file():
                return cand
    return None


def _pix_blind_why(src: str, deck_dir: Path) -> str:
    """底图取不到时，说清是**哪一种**取不到，并给出这一种的下一步。

    三种成因的修法完全不同，混成一句话等于没说：
      ① 这台机器量不了像素   → 装 Pillow（`hostcheck` 印了本机该跑哪条）
      ② token 查不到对照表   → 补一行 `tokens.tsv`
      ③ 表里有但文件没了     → 点名那个文件
    """
    tail = ("——**「这一页的字落在画面的哪一块上」「大罩压住画面」「满版上叠内容图」"
            "这三条判不了**。它们是最常见的三类缺陷，截图出来时必须亲自看这一页。")
    if not HAS_PIL:
        return ("底图取不到：这台机器的像素测量不可用（`hostcheck` 的【像素测量能力】"
                "那一段印了本机该怎么修）" + tail)
    raw = str(src or "").lstrip("@").lstrip("./")
    table = _token_map(deck_dir)
    if raw and raw in table:
        return (f"底图取不到：`{TOKEN_MAP}` 里 `{raw}` 指向 `{table[raw]}`，"
                "但这个文件现在不在素材目录里（被删了或换了名字）" + tail)
    if raw and not re.search(r"[./\\]", raw):
        return (f"底图取不到：`{raw}` 是宿主 token，本地没有对照表可查。"
                f"上传时把 `<file_token>\t<本地文件名>` 追加进 `assets/{TOKEN_MAP}`"
                "（`hostcheck` 打印的上传命令自带这一行），这一族判据就能量到底图" + tail)
    return (f"底图取不到：`{raw or '（空）'}` 在素材目录里找不到"
            "（图还没落盘，或不在 `assets/` 下）" + tail)


def _load_asset(src: str, deck_dir: Path):
    """解析并打开底图；打不开返回 None（上层必须把「没量过」说出去）。"""
    if not src or not HAS_PIL:
        return None
    path = _resolve_asset(src, deck_dir)
    if path is None:
        return None
    try:
        return Image.open(path).convert("RGB")
    except Exception:                                  # noqa: BLE001
        return None


def _quiet_zone(im, cell: int = 20):
    """这张图自己**最大的一块连续低信息区**（画布坐标）。ground 与 check 共用这一份。"""
    try:
        grid = _busy_grid(im, cell)
    except Exception:                                  # noqa: BLE001
        return None
    cx_n, cy_n = int(CANVAS_W // cell), int(CANVAS_H // cell)
    quiet = [[grid.get((x * cell, y * cell), 999) <= 26 for x in range(cx_n)]
             for y in range(cy_n)]
    best = (0, None)
    for y0 in range(cy_n):
        for y1 in range(y0 + 2, cy_n + 1):
            for x0 in range(cx_n):
                for x1 in range(x0 + 3, cx_n + 1):
                    if (x1 - x0) * (y1 - y0) <= best[0]:
                        continue
                    if all(quiet[y][x] for y in range(y0, y1) for x in range(x0, x1)):
                        best = ((x1 - x0) * (y1 - y0), (x0, y0, x1, y1))
    if not best[1]:
        return None
    x0, y0, x1, y1 = best[1]
    return (x0 * cell, y0 * cell, (x1 - x0) * cell, (y1 - y0) * cell)


def _subject_box(im, cell: int = 20):
    """画面最忙的一片（主体多半在这里）。`ground` 与 `check` 共用这一份。"""
    try:
        grid = _busy_grid(im, cell)
    except Exception:                                  # noqa: BLE001
        return None
    busy = [(x, y) for (x, y), v in grid.items() if v > 45]
    if not busy:
        return None
    xs = [c[0] for c in busy]
    ys = [c[1] for c in busy]
    return (min(xs), min(ys), max(xs) - min(xs) + cell, max(ys) - min(ys) + cell)


def _structure_lines(im):
    """贯穿画幅的强结构线；`ground` 与每页 `check` 共用同一份计算。"""
    try:
        im2 = im.resize((int(CANVAS_W), int(CANVAS_H)))
        px = im2.load()
    except Exception:                                  # noqa: BLE001
        return []
    lines = []
    for y in range(8, int(CANVAS_H) - 8, 4):
        jump = 0
        for x in range(0, int(CANVAS_W), 8):
            a = sum(px[x, y - 4]) / 3
            b = sum(px[x, y + 4]) / 3
            if abs(a - b) > 60:
                jump += 1
        if jump > 0.75 * (CANVAS_W // 8):
            lines.append(("横", y))
    for x in range(8, int(CANVAS_W) - 8, 4):
        jump = 0
        for y in range(0, int(CANVAS_H), 8):
            a = sum(px[x - 4, y]) / 3
            b = sum(px[x + 4, y]) / 3
            if abs(a - b) > 60:
                jump += 1
        if jump > 0.75 * (CANVAS_H // 8):
            lines.append(("竖", x))
    merged = []
    for direction, value in lines:
        if not any(d == direction and abs(v - value) < 24 for d, v in merged):
            merged.append((direction, value))
    return merged


#: 一张图能不能当**跨页底纹**的两条判据（都从真稿量出来的）。
#: ① 安静区要覆盖几乎整张图——参照库的底纹是 93–100%，纹理一重就掉到个位数；
#: ② 中区不许有贯穿画幅的缝——**贴页缘的边框不算**，它不切版面。
#: 参照库 11 份成稿的**标题级句子指纹**（`fontSize ≥18` 且 ≥6 个汉字，去空白后取 sha1 前 12 位）。
#: 只存哈希不存原文：一来参考库内容要匿名，二来不给执行者一份可抄的句子表。
#: 标定：参照库 11 份两两自排除后**互撞 0 条**（拉丁通用词被「≥6 个汉字」挡在门外）；
#: 标定样本中成稿撞条数分布为 0 / 1 / 2 / 8——撞 8 条的样本连稿名、章节名与四条页标题都发生复用。
_GOLD_TITLE_FP = {
    "09f51db56188", "13f5695f09c8", "142ce80390f4", "164b53993d54", "19633befda5d", "1bfc5fc726ab",
    "1f4a5e1d17c1", "23327199d445", "2a87f46003f6", "31e7e8a5254c", "32cd34c9fa3a", "37c0fd518d7b",
    "39d06411b5a0", "39fdea238c8b", "4135f999d022", "43939b36b528", "4594911b60f5", "485a72977637",
    "4866342f2469", "4cde181bdd72", "4ee56d9ae368", "51ba3b4fba87", "560c41d73c0f", "58e717810105",
    "5a114e8fe380", "5f89c6c2f141", "6085f9967d4d", "6092ffaefdb2", "75a78b094f6b", "83f2ea895ffa",
    "8b5ae1a65dd7", "8f0334210078", "8f127d162f01", "9207d4963ac4", "9533e771355e", "98be414a18da",
    "a208306bea49", "a28a537a22d4", "a49c11ac7bb2", "a749305611a1", "ae4a5ea9b02c", "aea402fae53f",
    "afa9bc087fb6", "b0b1a06b67e3", "be6b13ef9aaf", "be7f72dcb694", "c273b9fd8e97", "c891d63a8fff",
    "cc4b791ba491", "cd4bcd7236e3", "d0e58d32ec6e", "d347a576cb0c", "de82b6aea0ca", "e5e1109946fd",
    "e87c543b9b16", "e8b28cf7f82d", "ea2389d84ce9", "ed1957e87bc7", "ef10dce101d6", "f2f883ed5ff5",
    "f791efc135a6", "f873c7e9e8a3", "fd3a370c4947", "fe2016e724b3", "ffd4ef6fe982",
}

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _title_lines(page: "Page"):
    """这一页的**标题级句子**：`fontSize ≥18` 且 ≥6 个汉字，去空白。

    只取标题级：正文与小字里撞几个字是巧合，标题撞了就是把别人的骨架搬过来了。
    """
    out = []
    # 用 ET 走，不用正则：页面里有大量**自闭合**的 `<content …/>`（矩形块上的空 content），
    # 正则的 `(.*?)</content>` 会从它开始一路吞到下一个真 `</content>`，把中间的标题整块吃掉。
    for node in page.root.iter():
        if _local(node.tag) != "content":
            continue
        try:
            pt = float(node.attrib.get("fontSize") or 0)
        except ValueError:
            pt = 0.0
        if pt < 18:
            continue
        txt = re.sub(r"\s+", "", "".join(node.itertext()))
        if len(_CJK_RE.findall(txt)) >= 6:
            out.append(txt)
    return out


def _gold_title_hits(pages):
    """全稿有几条标题与参照库逐字相同。返回**执行者自己写的那几句**（不回显参照库的原文）。

    注：拿参照稿本身来跑这条会 100% 命中——那是同义反复，不是误伤。
    它的标定语料是**别的成稿**：参照库 11 份两两自排除后互撞 0 条，
    八份用户亲判过的成稿（104 页）命中 0 条。
    """
    hits = []
    for pg in pages:
        for t in _title_lines(pg):
            if hashlib.sha1(t.encode("utf-8")).hexdigest()[:12] in _GOLD_TITLE_FP:
                hits.append(t)
    return sorted(set(hits))


TEXTURE_QUIET_MIN = 0.85       # 安静区占版下限
#: **氛围底图**（D）那一支的下限：它不是纹理，允许有光位与纵深，只要还剩成片的低信息区。
#: 标定：参照库里用一张氛围底图铺 10 页的那一份，实测安静区 70%——它过不了纹理线，
#: 但它正是那一档的地。低于这条线的图只能当单页画面。
AMBIENT_QUIET_MIN = 0.40
SEAM_EDGE_BAND = 0.08          # 距页缘这个比例以内是「边框带」，不参与判定
SEAM_JUMP = 20.0               # 明度阶跃门槛（24 漏掉色差分幅，16 起开始误伤）
SEAM_COVER = 0.75              # 这条线要覆盖该方向的比例
SEAM_REACH = 0.04              # 且要真的抵达两侧页缘——版面里的发丝线是内收的
#: 采样窗口（半宽，px）。**只有 ±4 时两条像素实现给出同一结论。**
#: 标准库兜底只解 JPEG 的 DC 系数（1/8 精度），一条细硬缝（纸质折痕、印刷线）会被摊进一个
#: 8px 块里；窗口窄于半个块（±3）时真 Pillow 看不到它，宽于一个块（±5）时又会被两侧的地拉平——
#: 实测 2048 宽的底纹上一条 2px 硬缝：±3 与 ±5 两条实现结论相反，±4 一致。
#: **换台机器结论就变，比漏报更糟**，所以这个数不许随手改（回归里有双实现一致性断言）。
SEAM_WIN = 4


def _mid_seams(im, jump: float = SEAM_JUMP):
    """**中区**贯穿画幅的缝：色差分幅、折痕、通宽线条。返回 [(方向, 坐标)]。

    三条口径缺一不可：
      · 只看距页缘 `SEAM_EDGE_BAND` 以外的中区——**四周的边框不切版面**，一律豁免；
      · 覆盖该方向 ≥`SEAM_COVER`；
      · **必须抵达两侧页缘**——页面上的发丝线是内收的，图里的缝是通到底的，这一条把两者分开。
    """
    try:
        im2 = im.resize((int(CANVAS_W), int(CANVAS_H)))
        px = im2.load()
    except Exception:                                  # noqa: BLE001
        return []
    w, h = int(CANVAS_W), int(CANVAS_H)
    out = []

    def _mean(c):
        return (c[0] + c[1] + c[2]) / 3.0

    for y in range(max(SEAM_WIN, int(h * SEAM_EDGE_BAND)),
                   min(h - SEAM_WIN, int(h * (1 - SEAM_EDGE_BAND))), 4):
        hits = [x for x in range(0, w, 6)
                if abs(_mean(px[x, y - SEAM_WIN]) - _mean(px[x, y + SEAM_WIN])) > jump]
        if (len(hits) > SEAM_COVER * (w // 6) and hits
                and hits[0] <= w * SEAM_REACH and hits[-1] >= w * (1 - SEAM_REACH)):
            out.append(("横", y))
    for x in range(max(SEAM_WIN, int(w * SEAM_EDGE_BAND)),
                   min(w - SEAM_WIN, int(w * (1 - SEAM_EDGE_BAND))), 4):
        hits = [y for y in range(0, h, 6)
                if abs(_mean(px[x - SEAM_WIN, y]) - _mean(px[x + SEAM_WIN, y])) > jump]
        if (len(hits) > SEAM_COVER * (h // 6) and hits
                and hits[0] <= h * SEAM_REACH and hits[-1] >= h * (1 - SEAM_REACH)):
            out.append(("竖", x))
    merged = []
    for d, v in out:
        if not any(dd == d and abs(vv - v) < 24 for dd, vv in merged):
            merged.append((d, v))
    return merged


def _texture_verdict(im):
    """这张图能不能当跨页底纹。返回 (合格?, 安静区占版, 局部中位极差, 中区缝)。"""
    zone = _quiet_zone(im)
    share = (zone[2] * zone[3] / (CANVAS_W * CANVAS_H)) if zone else 0.0
    try:
        vals = sorted(_busy_grid(im).values())
        local = vals[len(vals) // 2] if vals else 0
    except Exception:                                  # noqa: BLE001
        local = 0
    seams = _mid_seams(im)
    return (share >= TEXTURE_QUIET_MIN and not seams), share, local, seams


def _ground_report(im):
    """满版图分诊事实；独立 `ground` 与必经 `check` 共享，避免同一张图两套口径。"""
    zone = _quiet_zone(im)
    _ok, share, local, seams = _texture_verdict(im)
    subject = _subject_box(im)
    lines = _structure_lines(im)
    try:
        sample = im.resize((96, 54))
        vals = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in sample.getdata()]
        mean = sum(vals) / max(1, len(vals))
        std = math.sqrt(sum((v - mean) ** 2 for v in vals) / max(1, len(vals)))
        colors = len({(r // 8, g // 8, b // 8) for r, g, b in sample.getdata()})
        placeholder = std < 3.0 and colors <= 8
    except Exception:                                  # noqa: BLE001
        std, colors, placeholder = 0.0, 0, False
    role = ("纹理地" if share >= TEXTURE_QUIET_MIN else
            "氛围底图" if share >= AMBIENT_QUIET_MIN else "单页画面")
    return {"zone": zone, "share": share, "local": local, "seams": seams,
            "subject": subject, "lines": lines, "role": role,
            "placeholder": placeholder, "std": std, "colors": colors}


def _idle_band(im, cell: int = 20) -> float:
    """这张图**自己**左/右侧有多少宽度是空的（连续低信息竖带）。"""
    try:
        grid = _busy_grid(im, cell)
    except Exception:                                  # noqa: BLE001
        return 0.0
    cols = collections.defaultdict(list)
    for (cx, _cy), v in grid.items():
        cols[cx].append(v)
    if not cols:
        return 0.0
    quiet = {cx for cx, vs in cols.items() if max(vs) <= 24}
    best = run = 0
    for cx in sorted(cols):
        run = run + 1 if cx in quiet else 0
        best = max(best, run)
    return best / max(len(cols), 1)


#: 同一页里 `_busy_grid` 会被安静区、主体区、忙碌度、叠图判据各要一次。
#: 纯标准库解码时它是最贵的一段，按 (图对象, 格宽) 记一次账就够。
_GRID_MEMO: dict = {}


def _busy_grid(im, cell: int = 20):
    """把画面切成 cell 网格，每格算明度极差 → 判「这一块忙不忙」。"""
    # **键里存一份图对象的强引用**：只用 id() 当键时，图被回收后新对象可能拿到同一个 id，
    # 于是下一页会拿到上一页的网格——那种错比慢一秒贵得多。
    key = (id(im), cell)
    got = _GRID_MEMO.get(key)
    if got is not None and got[0] is im:
        return got[1]
    src = im
    im = im.resize((int(CANVAS_W), int(CANVAS_H)))
    px = im.load()
    grid = {}
    for cy in range(0, int(CANVAS_H), cell):
        for cx in range(0, int(CANVAS_W), cell):
            vals = []
            for y in range(cy, min(cy + cell, int(CANVAS_H)), 4):
                for x in range(cx, min(cx + cell, int(CANVAS_W)), 4):
                    r, g, b = px[x, y]
                    vals.append((r * 299 + g * 587 + b * 114) // 1000)
            if not vals:
                continue
            vals.sort()
            grid[(cx, cy)] = vals[int(len(vals) * 0.95)] - vals[int(len(vals) * 0.05)]
    if len(_GRID_MEMO) > 24:
        _GRID_MEMO.clear()
    _GRID_MEMO[(id(src), cell)] = (src, grid)
    return grid


def _busy_in(grid, box, thresh: int = 30) -> float:
    x, y, w, h = box
    hit = tot = 0
    for (cx, cy), v in grid.items():
        if cx + 20 <= x or cx >= x + w or cy + 20 <= y or cy >= y + h:
            continue
        tot += 1
        if v > thresh:
            hit += 1
    return hit / tot if tot else 0.0


def _under_color(page: Page, im, block, x: int, y: int):
    """(x, y) 这一点上，`block` 底下**实际是什么颜色**。

    从底图那一点起，把排在 `block` 之前、盖住这一点的每一块填充色依次压上去。
    **不合成就量不准**：参照稿常在满版图上铺一层通幅压淡/压暗层再排字，
    只量原图会把"压淡之后完全读得清"算成"对比度 1.1:1"。
    """
    px = im.load()
    base = px[min(max(int(x), 0), im.size[0] - 1), min(max(int(y), 0), im.size[1] - 1)]
    for o in page.blocks:
        if o.order >= block.order or o is block or not o.fill or o.kind == "line":
            continue
        ox, oy, ow, oh = o.box
        if not (ox - 1 <= x <= ox + ow + 1 and oy - 1 <= y <= oy + oh + 1):
            continue
        if "gradient" in o.fill:
            parsed = _parse_gradient(o.fill)
            if not parsed:
                continue
            _deg, stops = parsed
            t = (x - ox) / ow if ow > 4 and abs(_deg % 180 - 90) > 45 else \
                ((y - oy) / oh if oh > 4 else 0.5)
            a = _grad_alpha_at(stops, min(1.0, max(0.0, t)))
            rgb = _rgba(re.search(r"rgba?\([^)]*\)", o.fill).group(0)) if \
                re.search(r"rgba?\([^)]*\)", o.fill) else None
            if rgb:
                base = tuple(rgb[i] * a + base[i] * (1 - a) for i in range(3))
            continue
        c = _rgba(o.fill)
        if c:
            base = _blend(c, base)
    return base


def _text_on_picture(page: Page, im, block):
    """这一块字压在画面上时，与身下那片地的**中位对比度**与**低对比面积占比**。

    量不了返回 None。两个数都只是事实：参照稿里有意做的同色系巨字低到 1.2:1
    也成立，所以这一族**只报数不设门**——设了就会判死金标准。
    """
    fc = block.font_color
    if not fc or block.max_pt <= 0 or fc[3] <= 0.5 or block.fill:
        return None
    x, y, w, h = block.box
    x0, y0 = int(max(0, x)), int(max(0, y))
    x1, y1 = int(min(CANVAS_W, x + w)), int(min(CANVAS_H, y + h))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    sx, sy = max(1, (x1 - x0) // 24), max(1, (y1 - y0) // 12)
    unders = [_under_color(page, im, block, xx, yy)
              for yy in range(y0, y1, sy) for xx in range(x0, x1, sx)]
    if not unders:
        return None
    unders.sort(key=_lum)
    mid = unders[len(unders) // 2]
    ratio = _contrast(_blend(fc, mid), mid)
    weak = sum(1 for c in unders if _contrast(_blend(fc, c), c) < 3.0) / len(unders)
    return ratio, weak


#: 页头 `ground=` 里表明「这一页的地是一张有内容的画面」的说法。
_PICTURE_WORDS = ("影像", "画面", "实景", "照片", "场景", "composite", "photo", "scene")


def _ground_declared(page: "Page") -> str:
    """执行者在页头 `ground=` 里**声明**这一页的地是什么：底纹 / 画面 / 没说。

    **声明决定「打算当什么用」，像素决定「够不够格」**——两件事分开。
    声明成画面而像素看着像底纹时，判据仍按画面那一支说话（否则判词会和页头打架，
    执行者会以为脚本读错了它的页）。
    """
    head = page.header or ""
    if not head:
        return ""
    if any(w in head for w in _TEXTURE_WORDS):
        return "底纹"
    if any(w in head for w in _PICTURE_WORDS):
        return "画面"
    return ""


def _looks_like_texture(page: "Page") -> bool:
    """执行者在页头 `ground=` 里自己声明成底纹／底板／材质的那一类。"""
    return _ground_declared(page) == "底纹"


def _pixel_findings(page: Page, deck_dir: Path, errors, notes):
    """需要底图像素才能判的两件事：大罩盖住画面 / 满版主体上叠图。"""
    ground = page.canvas_image
    if ground is None:
        return
    src = _ground_src(page)
    im = _load_asset(src, deck_dir)
    if im is not None:
        report = _ground_report(im)
        page.ground_report = report
        # `fillImg` 必然会铺满 16:9；源图比例差得很远时，XML 仍可能“合法”，但宿主里
        # 往往只能通过大幅裁掉两侧/上下或把图拉伸来完成。普通 `<img>` 已有 10% 硬门；
        # 满版画面保留海报式、电影式非常规裁法，所以这里只把风险送进 LOOK-24，不判死。
        sw, sh = im.size
        source_ratio = sw / max(sh, 1)
        target_ratio = CANVAS_W / CANVAS_H
        ratio_drift = abs(source_ratio / target_ratio - 1.0)
        if ratio_drift > 0.10:
            page.ground_aspect_risk = (sw, sh, source_ratio, target_ratio, ratio_drift)
            notes.append(("GND-006", f"这张满版源图是 {sw}×{sh}（{source_ratio:.2f}:1），"
                                      f"页面是 {target_ratio:.2f}:1，比例偏差 {ratio_drift:.0%}。"
                                      "它不在 XML 阶段判死：非常规满版裁法有时是有意设计；"
                                      "但宿主截图的 LOOK-24 必须核对左右/上下是否被硬截、拉伸或出现拼接条。"))
        grid = _busy_grid(im)
        # ── 先分清这一页的地是**跨页底纹**还是**画面**：两者要说的话完全不同 ──
        # 底纹的正解是「它不合格就重新生成它」；画面的正解是「把字迁进它的安静区」。
        # 对底纹说后面那句话是做不到的（安静区只有 6% 时，一页的字排不进去），
        # 而**做不到的处方会连同它正确的诊断一起被丢掉**。
        tex_ok, tex_share, tex_local, tex_seams = _texture_verdict(im)
        # **「打算当什么用」与「够不够格」是两个问题。** 页头声明成底纹／底板／材质的，
        # 就按底纹判——哪怕它不合格（不合格正是要报的那件事）。
        declared = _ground_declared(page)
        as_texture = (declared == "底纹") if declared else (tex_share >= TEXTURE_QUIET_MIN)
        page.ground_kind = "底纹" if as_texture else "画面"
        page.ground_seams = tex_seams
        page.ground_quiet_share = tex_share
        if report["placeholder"]:
            errors.append(("GND-005", f"这张满版图的像素标准差只有 {report['std']:.1f}、"
                                      f"量化后只有 {report['colors']} 种颜色，像宿主灰色占位图或空白底。"
                                      "占位图不能当成已验过的画面；若本意只是纯色，请改用 fillColor。"
                                      "（下面只是建议，必须按本页实际情况调整：重新取得真实素材，"
                                      "或重新生成/检索后再走同一条 check。）"))
        if as_texture:
            if not tex_ok:
                bits = []
                if tex_share < TEXTURE_QUIET_MIN:
                    bits.append(f"安静区只占 {tex_share:.0%}（合格线 ≥{TEXTURE_QUIET_MIN:.0%}，"
                                f"真稿的底纹是 93–100%）、局部明度极差中位 {tex_local:.0f}"
                                "（真稿 4–10）——纹理太重，字压上去会被图案干扰")
                if tex_seams:
                    bits.append("中区有 %d 条贯穿画幅的缝（%s）——它们会把版面框死"
                                "（贴页缘的边框不算，那不切版面）"
                                % (len(tex_seams),
                                   "、".join(f"{d}向 {v}" for d, v in tex_seams[:3])))
                notes.append(("GRD-004",
                              "这一页的地是跨页底纹，但**这张底纹不合格**：" + "；".join(bits) + "。"
                              "正解是**重新生成这张底纹**（`ground --image <图> --as-texture` 会印出口径），"
                              "不是把这一页的字挤进它剩下的那一小块——那是排不进去的。"
                              "底纹要复用到很多页上，一张不合格的会把整稿一起拖下去。"))
            elif PIXEL_SOURCE == "stdlib":
                notes.append(("GRD-006",
                              "这一页的地是跨页底纹，按本机能量到的精度看是合格的；"
                              "但**本机走的是包内标准库解码器（1/8 精度），极细密的图案量不出来**——"
                              "截图上亲自看一眼最小的那几行字（页码、眉标、图注、来源行）读不读得清。"))
            return                                     # 底纹地不再走「把字迁进安静区」那一支
        # ✗ **满版画面地不判分割线。** 图里铺一片承文面（占住一侧、文字整叠落进去）
        #   是成文做法（image-direction §八 ①b、page-craft D2），它与背景之间那条边是**设计**，
        #   不是缺陷。分割线的要求只对**跨页底纹**成立——底纹要复用到很多页上，一条缝会把每一页都框死。
        # **把安静区直接送到手上**：满版底图上有字时，文字该落在哪只有像素知道。
        # 真机上执行者常常不会为此另跑一条命令，所以这一步由 check 主动给出。
        texts_on = [b for b in page.texts if b.max_pt >= 12]
        if texts_on:
            zone = report["zone"]
            if zone:
                zx, zy, zw, zh = zone
                outside = [b for b in texts_on
                           if not (b.box[0] >= zx - 8 and b.box[1] >= zy - 8
                                   and b.box[0] + b.box[2] <= zx + zw + 8
                                   and b.box[1] + b.box[3] <= zy + zh + 8)]
                msg = (f"这一页的地是一张图，它自己的安静区在 x{zx:.0f} y{zy:.0f} "
                       f"w{zw:.0f} h{zh:.0f}（占版 {zw*zh/(CANVAS_W*CANVAS_H):.0%}）。")
                if outside:
                    msg += (f"现在有 {len(outside)} 块字落在它之外。"
                            "承文阶梯的第一档就是**把整叠字迁进这块安静区，零形状**"
                            "（page-craft §四）。")
                    # **把「读不读得清」也量出来送到手上。** 只报数不设门：
                    # 参照稿里有意做的同色系巨字实测低到 1.2:1 也成立，设门会判死它。
                    ranked = []
                    for t in outside:
                        got = _text_on_picture(page, im, t)
                        if got:
                            ranked.append((got[0], got[1], t))
                    ranked.sort(key=lambda r: r[0])
                    hard = [r for r in ranked if r[0] < 3.0]
                    page.text_on_picture = ranked
                    subj = report["subject"]
                    page.subject_box = subj
                    if subj:
                        on_subject = [t for t in texts_on
                                      if t.box[0] < subj[0] + subj[2] and t.box[0] + t.box[2] > subj[0]
                                      and t.box[1] < subj[1] + subj[3] and t.box[1] + t.box[3] > subj[1]]
                        page.face_overlap_candidates = on_subject
                        msg += (f"画面最忙的一片（主体多半在这里）是 x{subj[0]} y{subj[1]} "
                                f"w{subj[2]} h{subj[3]}，有 {len(on_subject)} 块字压在它上面"
                                "——**「压住主体/人脸」只有截图看得出来**，"
                                "这一页必须亲自看这几块。")
                    busy_texts = [(t, _busy_in(grid, t.box)) for t in outside]
                    busy_texts.sort(key=lambda x: x[1], reverse=True)
                    page.busy_texts = [x for x in busy_texts if x[1] >= 0.28]
                    if page.busy_texts:
                        msg += ("机器还量到这些字框底下有明显画面内容：" + "；".join(
                            f"「{t.text[:10]}」{t.max_pt:.0f}pt → 忙碌 {busy:.0%}"
                            for t, busy in page.busy_texts[:5])
                            + "。这些是截图 LOOK-21 必须逐项核对的对象。")
                    if hard:
                        msg += (f"其中 {len(hard)} 块与身下画面的中位对比度低于 3:1："
                                + "；".join(
                                    f"「{t.text[:10]}」{t.max_pt:.0f}pt → {r:.1f}:1"
                                    f"（框内 {w_:.0%} 的面积低于 3:1）"
                                    for r, w_, t in hard[:3])
                                + "。对比度、忙碌度、主体框都不能单独判死页面；"
                                "截图上必须核对：这些字是否真的读得清、是否压住主体或人脸。")

                    # GRD-003 不把「有字在安静区外」直接判死：海报式满版页经常有意这么做。
                    # 只抓一种高分离形状——底图已经给出一侧通高承文带，而主要文字系统却横跨
                    # 这条带进入忙画面。它是「承文合同与文字几何不一致」，不是审美偏好。
                    zone_share = zw * zh / (CANVAS_W * CANVAS_H)
                    side_zone = (zh >= 0.70 * CANVAS_H and zone_share <= 0.40
                                 and (zx <= 0.08 * CANVAS_W
                                      or zx + zw >= 0.92 * CANVAS_W))
                    tx0 = min(t.box[0] for t in texts_on)
                    tx1 = max(t.box[0] + t.box[2] for t in texts_on)
                    centers_out = [t for t in texts_on
                                   if not (zx - 8 <= t.box[0] + t.box[2] / 2 <= zx + zw + 8
                                           and zy - 8 <= t.box[1] + t.box[3] / 2 <= zy + zh + 8)]
                    contract_broken = (side_zone and len(texts_on) >= 3
                                       and len(outside) >= max(3, math.ceil(len(texts_on) * 0.60))
                                       and len(centers_out) >= 2
                                       and (tx1 - tx0) >= 2.0 * max(zw, 1)
                                       and len(page.busy_texts) >= 2)
                    if contract_broken:
                        errors.append(("GRD-003",
                                       f"底图已经形成一侧通高承文带 x{zx:.0f} y{zy:.0f} "
                                       f"w{zw:.0f} h{zh:.0f}（占版 {zone_share:.0%}），"
                                       f"但 {len(texts_on)} 块主要文字里有 {len(outside)} 块越出，"
                                       f"文字系统横跨 {tx1-tx0:.0f}px（承文带宽 {zw:.0f}px），"
                                       f"且至少 {len(page.busy_texts)} 块进入忙画面。"
                                       "这不是『安静区偏小』，而是承文合同与文字几何互相矛盾。"
                                       "（下面只是建议，必须按本页实际内容调整：把完整文字系统收进承文带并减字，"
                                       "或改成纯色地＋贴边图窗，或重新生成能承载当前文字量的底图；"
                                       "不要在现有画面上追加大罩或实色补丁。）"))
                else:
                    msg += "本页的字都落在里面了，不需要任何托底。"
                notes.append(("GRD-001", msg))
            else:
                notes.append(("GRD-002", "这一页的地是一张图，但它**没有像样的安静区**"
                                         "（找不到连续的低信息块）——字压上去多半读不清。"
                                         "承文阶梯里这一档的正解是**重新生成这一页的底图**，"
                                         "prompt 写明给文字留一片低细节区（page-craft §四）。"))
        if not as_texture:
            vertical = [v for d, v in report["lines"] if d == "竖"]
            left = [v for v in vertical if v <= 0.15 * CANVAS_W]
            right = [v for v in vertical if v >= 0.85 * CANVAS_W]
            if left and right:
                pair = (min(left), max(right))
                page.ground_edge_lines = pair
                notes.append(("GND-004", f"这张满版地上量到贴近两侧的竖向结构线 x{pair[0]} / x{pair[1]} "
                                         f"（距左右边 {pair[0]/CANVAS_W:.1%} / "
                                         f"{(CANVAS_W-pair[1])/CANVAS_W:.1%}）。"
                                         "它们可能是正常建筑边，也可能是拼接缝或源图左右已经被截断；"
                                         "单凭像素不能判死，宿主截图会追加 LOOK-24 逐项核对。"))
    if im is None:
        # **量不到 ≠ 合格。** 底图取不到时，安静区／大罩／叠图整族失效——
        # 必须说出来，而且要说清是**哪一种**取不到，否则执行者只能干等着。
        notes.append(("PIX-000", _pix_blind_why(src, deck_dir)))
        return

    # 小托底：不是硬门，只把几何事实交给 LOOK。它可能是标签家具，也可能是不必要的补丁。
    quiet = _quiet_zone(im)
    for b in page.blocks:
        if b.kind != "shape" or b.text or not b.fill or "gradient" in b.fill:
            continue
        rgba = _rgba(b.fill)
        share = b.box[2] * b.box[3] / (CANVAS_W * CANVAS_H)
        in_quiet = bool(quiet and b.box[0] >= quiet[0] - 8 and b.box[1] >= quiet[1] - 8
                        and b.box[0] + b.box[2] <= quiet[0] + quiet[2] + 8
                        and b.box[1] + b.box[3] <= quiet[1] + quiet[3] + 8)
        if rgba and rgba[3] >= 0.50 and 0.03 <= share < 0.30 and not in_quiet:
            notes.append(("IMG-022", f"画面上有一块 {b.box[2]:.0f}×{b.box[3]:.0f} 的实色托底"
                                      f"（占版 {share:.0%}），它没有完整落在图自己的安静区。"
                                      "这只是需要看图的事实：它可能是必要家具，也可能在替错误落位兜底；"
                                      "如需调整，可结合本页内容另选迁字、换字色、重排或换图，"
                                      "这些方向都只是建议，不是必须照做的处方。"))
            break

    # 大罩：覆盖 ≥35% 画布、峰值 α≥0.70，且**被盖那一侧真有内容**
    for b in page.blocks:
        if b.kind != "shape" or not b.fill or b.text:
            continue
        share = b.box[2] * b.box[3] / (CANVAS_W * CANVAS_H)
        if share < 0.35:
            continue
        cover_boxes = []
        peak = 0.0
        if "gradient" in b.fill:
            parsed = _parse_gradient(b.fill)
            if not parsed:
                continue
            deg, stops = parsed
            samples = [_grad_alpha_at(stops, t / 40.0) for t in range(41)]
            peak = max(samples)
            if peak - min(samples) <= 0.12 and peak <= 0.60:
                continue                                # 匀质暗罩＝成文正路（承文⑤）
            for cy in range(int(b.box[1]), int(b.box[1] + b.box[3]), 20):
                for cx in range(int(b.box[0]), int(b.box[0] + b.box[2]), 20):
                    pos = _grad_axis_pos(deg, cx + 10, cy + 10, b.box)
                    if _grad_alpha_at(stops, min(1.0, max(0.0, pos))) >= 0.55:
                        cover_boxes.append((cx, cy))
        else:
            f = _rgba(b.fill)
            if not f or f[3] < 0.30 or f[3] >= 0.995:
                continue
            peak = f[3]
            if peak < 0.55:
                continue
            cover_boxes = [(cx, cy) for cx in range(int(b.box[0]), int(b.box[0] + b.box[2]), 20)
                           for cy in range(int(b.box[1]), int(b.box[1] + b.box[3]), 20)]
        opaque_share = len(cover_boxes) * 400 / max(b.box[2] * b.box[3], 1.0)
        if peak < 0.70 or opaque_share < FOG_OPAQUE_SHARE:
            continue
        xs = [c[0] for c in cover_boxes]
        ys = [c[1] for c in cover_boxes]
        cbox = (min(xs), min(ys), max(xs) - min(xs) + 20, max(ys) - min(ys) + 20)
        busy = _busy_in(grid, cbox)
        pct = len(cover_boxes) * 400 / (CANVAS_W * CANVAS_H)
        if busy >= 0.35:
            errors.append(("FOG-001", f"一块 α{peak:.2f} 的罩压掉了 {pct:.0%} 画布，"
                                      f"而被盖那一侧 {busy:.0%} 是画面内容——读者看到的是"
                                      "「背景被截断/画面洗成一块板」，人物头脸也可能被罩掉。"
                                      "只把 alpha 调低可能让代码消失，却没有解决文字究竟该落在哪里。"
                                      + ("本页同时有文字落在忙画面上，必须与 GRD-001/LOOK-21 一起结账。"
                                         if getattr(page, "busy_texts", None) else "")
                                      + "可结合实际尝试迁字、换字色、重排、换图或重新下单；"
                                        "这些都只是建议，必须按截图实际情况选择，不是绝对执行方案。"))
        else:
            notes.append(("FOG-002", f"α{peak:.2f} 的罩压掉 {pct:.0%} 画布，但被盖那侧只有 "
                                     f"{busy:.0%} 是内容——这一档成立，截图确认一眼即可。"))

    # 满版主体上叠内容图
    small = [b for b in page.images
             if 0.02 <= b.box[2] * b.box[3] / (CANVAS_W * CANVAS_H) < 0.85]
    if small and page.ground_token:
        gx = [b for b in small
              if _busy_in(grid, b.box) >= 0.35]
        if gx:
            rows = "；".join(f"{b.box[2]:.0f}×{b.box[3]:.0f}@{b.box[0]:.0f},{b.box[1]:.0f}"
                             for b in gx[:3])
            errors.append(("IMG-020", f"满版画面上贴了 {len(gx)} 张内容图（{rows}），"
                                      "它们底下正是画面有内容的地方——盖住的很可能是主体。"
                                      "**满版主体画面上不再叠内容图**——地与图要在同一层里解决"
                                      "（page-craft §L0 与 §四）。"))


# ─────────────────────────── 命令 ───────────────────────────

_IT_WORDS = ("文字", "字样", "标题文字", "字体", "logo", "标语", "slogan", "caption",
             "text", "typography", "lettering", "写着", "标注")
_IT_SAFE = ("no text", "no words", "no logo", "no lettering", "无文字", "不含文字", "无可读")


# ─────────────────────── 这一页要看的几问（`check` 的收尾）───────────────────────
#
# **落点是这里，不是文档里。** 每页写完必跑 `check`，它已经解析完这一页的全部几何，
# 所以「这一页该看什么」由它按本页的形状长出来，不需要执行者再去翻别的文件、
# 也不需要多跑一条命令。恒问四条 ＋ 按本页几何触发的条件问，最多十条。
#
# 每一条都是**问句**，不是处方：看不看得出问题由执行者对着截图判。

#: 页面职责里属于「落地效果」的那一类——这一档用矩形拼样机什么都证明不了。
_APPLY_JOBS = ("application", "evidence", "product", "space", "store", "material",
               "showcase", "retail", "packaging", "应用", "物料", "门店", "落地")

#: 常见画幅的下单短边（image-direction §六）：短边取 1024–1536，两个数都取 8 的倍数。
_ORDER_SHORT = 1280


def _order_size(w: float, h: float):
    """按图窗几何算出重新生成时该下单的 width/height。

    **这不是处方，是确定性算术**：目标比＝图窗宽/高，短边取 1024–1536、
    两个数都取 8 的倍数（image-direction §六）。同一个图窗只有一个正确答案，
    执行者自己按同一条规则算也会得到它。
    """
    if w <= 0 or h <= 0:
        return None
    ratio = w / h
    if ratio >= 1:
        hh = _ORDER_SHORT
        ww = int(round(hh * ratio / 8)) * 8
    else:
        ww = _ORDER_SHORT
        hh = int(round(ww / ratio / 8)) * 8
    return int(round(ww / 8)) * 8, int(round(hh / 8)) * 8


#: 画面块贴不贴页缘：≥12% 版面的图块，四边至少碰到一条才叫「切到页缘」。
#: 标定自参照库 11 份 135 页——103 个 ≥12% 版面的画面块里 97 个（94%）贴边，
#: 8/11 份是 100%、最低一份 78%。**只报事实，不设门**：四边留白是 6% 的少数做法
#: （样张、色卡、单件产品图），设门会判死它们。
BLEED_MIN_AREA = 0.12
BLEED_TOL = 2.0

#: 孤图：四个条件**同时**成立才算——面积小、四周空、不共轴、不在页缘家具带内。
#: 合取是故意的：本轮四份真机产出 26 张图命中 0 张（成组的小图共用边线，第三条就不成立）。
ORPHAN_MAX_AREA = 0.04
ORPHAN_MIN_GAP = 40.0
ORPHAN_ALIGN_TOL = 4.0
ORPHAN_EDGE_BAND = 0.05


def _touches_edge(box) -> bool:
    x, y, w, h = box
    return (x <= BLEED_TOL or y <= BLEED_TOL
            or x + w >= CANVAS_W - BLEED_TOL or y + h >= CANVAS_H - BLEED_TOL)


def _page_bleeds(page: "Page") -> bool:
    """这一页有没有 ≥12% 版面的画面块切到页缘（slide 级满版地天然算）。"""
    if page.ground_token:
        return True
    for b in page.images:
        if b.box[2] * b.box[3] >= BLEED_MIN_AREA * CANVAS_W * CANVAS_H and _touches_edge(b.box):
            return True
    return False


def _inset_images(page: "Page"):
    """≥12% 版面、却四边都留白的图块——参照库里只有 6% 是这么排的。"""
    out = []
    for b in page.images:
        if b.box[2] * b.box[3] < BLEED_MIN_AREA * CANVAS_W * CANVAS_H:
            continue
        if _touches_edge(b.box):
            continue
        x, y, w, h = b.box
        out.append((b, x, y, CANVAS_W - (x + w), CANVAS_H - (y + h)))
    return out


def _gap(a, b) -> float:
    dx = max(0.0, max(a[0] - (b[0] + b[2]), b[0] - (a[0] + a[2])))
    dy = max(0.0, max(a[1] - (b[1] + b[3]), b[1] - (a[1] + a[3])))
    return (dx * dx + dy * dy) ** 0.5


def _shares_axis(a, b, tol: float = ORPHAN_ALIGN_TOL) -> bool:
    ax = (a[0], a[0] + a[2], a[0] + a[2] / 2)
    bx = (b[0], b[0] + b[2], b[0] + b[2] / 2)
    ay = (a[1], a[1] + a[3], a[1] + a[3] / 2)
    by = (b[1], b[1] + b[3], b[1] + b[3] / 2)
    return (any(abs(u - v) <= tol for u in ax for v in bx)
            or any(abs(u - v) <= tol for u in ay for v in by))


def _orphan_images(page: "Page"):
    """孤零零的小图：小、四周空、与任何块都不共轴、又不在页缘的家具带里。"""
    out = []
    others_all = [b for b in page.blocks if b.box[2] > 0 and b.box[3] > 0]
    for b in page.images:
        x, y, w, h = b.box
        if w <= 0 or h <= 0:
            continue
        if w * h > ORPHAN_MAX_AREA * CANVAS_W * CANVAS_H:
            continue
        if (x <= CANVAS_W * ORPHAN_EDGE_BAND or y <= CANVAS_H * ORPHAN_EDGE_BAND
                or x + w >= CANVAS_W * (1 - ORPHAN_EDGE_BAND)
                or y + h >= CANVAS_H * (1 - ORPHAN_EDGE_BAND)):
            continue
        others = [o for o in others_all if o is not b]
        if not others:
            continue
        near = min(_gap(b.box, o.box) for o in others)
        if near < ORPHAN_MIN_GAP:
            continue
        if any(_shares_axis(b.box, o.box) for o in others):
            continue
        out.append((b, near))
    return out


#: 页首 `device=` 里那几个几何含义无歧义的装置，与实际几何对账（page-craft §二）。
#: 只挑「装置描述里直接写了几何」的八个：写了却没做到，是执行者自己的两句话对不上，
#: 不是审美判断——参照稿没有声明，天然不会被判死。
_DEVICE_GEOM = {
    "1":  ("D1 满版影像＋巨字", "整页一张图"),
    "2":  ("D2 半版竖图贴边", "图占 40–56% 版面、贴一侧三边"),
    "3":  ("D3 上图带＋下多栏", "上半一条满宽图带"),
    "4":  ("D4 多图编辑拼贴", "3–6 张图，其中 1–2 张贴边出血"),
    "5":  ("D5 竖条切片带", "3–6 条等高竖图并排"),
    "7":  ("D7 巨号章节页", "一个 120–220pt 的编号"),
    "11": ("D11 左图右词条卡", "图通高、占 40–45% 版面"),
    "12": ("D12 对开双栏", "版心分左右两栏、中缝一条线"),
}


def _device_ids(page: "Page"):
    m = re.search(r"device\s*=\s*([^\s>]+)", page.header or "")
    if not m:
        return []
    return re.findall(r"[Dd](\d+)", m.group(1))


def _device_mismatch(page: "Page"):
    """声明的装置与写出来的几何对不上时，报哪一条对不上、实际是什么。"""
    ids = [i for i in _device_ids(page) if i in _DEVICE_GEOM]
    if not ids:
        return []
    imgs = list(page.images)
    area = lambda b: b.box[2] * b.box[3] / (CANVAS_W * CANVAS_H)
    biggest = max(imgs, key=area) if imgs else None
    maxpt = max((b.max_pt for b in page.texts), default=0.0)
    out = []
    for i in ids:
        name, want = _DEVICE_GEOM[i]
        got = None
        if i == "1":
            if page.canvas_image is None:
                got = (f"这一页没有铺满整页的图（最大的图占版 {area(biggest):.0%}）"
                       if biggest else "这一页一张图都没有")
        elif i == "2":
            ok = any(0.35 <= area(b) <= 0.62 and _touches_edge(b.box) for b in imgs)
            if not ok:
                got = ("这一页的图都没有贴到页缘"
                       if imgs else "这一页一张图都没有")
        elif i == "3":
            ok = any(b.box[2] >= 0.95 * CANVAS_W and b.box[1] < 0.5 * CANVAS_H for b in imgs)
            if not ok:
                got = "这一页没有位于上半的满宽图带"
        elif i == "4":
            if len(imgs) < 3:
                got = f"这一页只有 {len(imgs)} 张图"
            elif not any(_touches_edge(b.box) for b in imgs):
                got = "这几张图没有一张贴边出血"
        elif i == "5":
            tall = [b for b in imgs if b.box[3] > b.box[2]]
            if len(tall) < 3:
                got = f"这一页只有 {len(tall)} 条竖图"
        elif i == "7":
            if maxpt < 120:
                got = f"这一页最大的字只有 {maxpt:.0f}pt"
        elif i == "11":
            tallimg = [b for b in imgs if b.box[3] >= 0.80 * CANVAS_H]
            if not tallimg:
                got = (f"这一页最大的图是 {biggest.box[2]:.0f}×{biggest.box[3]:.0f}"
                       f"（上下各留 {biggest.box[1]:.0f}/{CANVAS_H - biggest.box[1] - biggest.box[3]:.0f}px）"
                       if biggest else "这一页一张图都没有")
        elif i == "12":
            mid = CANVAS_W / 2
            crossing = [b for b in page.blocks
                        if b.box[2] > 0 and b.box[0] < mid - 8 and b.box[0] + b.box[2] > mid + 8
                        and b.box[2] * b.box[3] >= 0.10 * CANVAS_W * CANVAS_H]
            left = any(b.box[0] + b.box[2] <= mid + 8 for b in page.blocks if b.text)
            right = any(b.box[0] >= mid - 8 for b in page.blocks if b.text)
            if crossing or not (left and right):
                got = "版心没有真的分成左右两栏"
        if got:
            out.append((name, want, got))
    return out


#: 宿主实测：写了会**静默回落**成默认字形的字体名（slides-xml.md §三·B 的同一份名单）。
#: 两处必须同源——文档改了这里不改，执行者就会照着文档写出一个报不出来的名字。
_FONT_FALLBACK = (
    "SimHei", "黑体", "宋体", "仿宋", "隶书", "幼圆", "等线", "微软雅黑", "Microsoft YaHei",
    "苹方", "PingFang SC", "华文黑体", "方正黑体", "方正兰亭黑", "汉仪旗黑", "阿里巴巴普惠体",
    "思源等宽", "Arial", "Arial Black", "Helvetica", "Verdana", "Tahoma", "Trebuchet MS",
    "Georgia", "Futura", "Optima", "Gill Sans", "Avenir", "Century Gothic", "Impact",
    "Comic Sans MS", "Segoe UI", "Menlo", "Monaco", "Consolas", "Space Grotesk", "Space Mono",
    "JetBrains Mono", "Fira Code", "IBM Plex Mono", "Archivo Black", "Manrope", "Outfit",
    "Sora", "Orbitron", "Staatliches",
)

#: 中文真的会换字形的那几款（其余中文字体名只换拉丁，中文回落成默认黑体）。
_FONT_CJK = ("思源黑体", "Noto Sans SC", "思源宋体", "Noto Serif SC",
             "圆体", "ChillReunion_Round", "抖音美好体", "站酷快乐体")


def _fonts_used(page: "Page"):
    return set(re.findall(r'fontFamily="([^"]+)"', page.raw))


def _reuse_reason(page: "Page") -> str:
    """页首 `reuse=<一句原因>`；只有 `_reuse_user_reason` 认可的用户授权可豁免。"""
    m = re.search(r"reuse\s*=\s*([^\n>]+)", page.header or "")
    return m.group(1).strip(" -") if m else ""


def _reuse_user_reason(page: "Page") -> str:
    """只认 `reuse=user:<用户明确要求>`；普通设计理由不能冒充用户授权。"""
    raw = _reuse_reason(page)
    m = re.match(r"user\s*:\s*(.+)", raw, re.I)
    return m.group(1).strip() if m else ""


def _is_reusable_plate(src: str, pages, deck_dir: Path):
    """跨页底板按图片角色判，不按“已经用了几页”反推角色。"""
    if len(pages) < 3:
        return False, "不足三页", None
    im = _load_asset(src, deck_dir)
    if im is None:
        return True, "素材不可打开，按离线口径处理", None
    report = _ground_report(im)
    if report["placeholder"]:
        return False, "占位图", report["share"]
    return (report["share"] >= AMBIENT_QUIET_MIN,
            report["role"], report["share"])


#: LOOK 只认写入宿主后的真页截图；`hostshots/` 是默认目录，`shots/` 兼容旧项目。
def _shot_of(slide: Path, host_only=False):
    stem = slide.stem
    roots = [slide.parent.parent / "hostshots", slide.parent / "hostshots", Path("hostshots"),
             slide.parent.parent / "shots", slide.parent / "shots", Path("shots")]
    if not host_only:
        roots += [slide.parent.parent, slide.parent]
        for r in roots:
            for ext in (".png", ".jpg", ".jpeg"):
                q = r / (stem + ext)
                try:
                    if q.is_file():
                        return q
                except OSError:
                    continue
    # 宿主截真页时文件名形如 `<pid>_p001_<sid>_2.jpg`——按 `p<页号>` 这个**有分隔的**标记找。
    # ✗ 不要用 `*<页号>*` 裸模糊匹配：任何带这串数字的无关图片都会被当成这一页的截图。
    num = re.search(r"(\d+)", stem)
    if num:
        n = int(num.group(1))
        marks = (f"_p{n:03d}_", f"_p{n:03d}.", f"_p{n:02d}_", f"_p{n:02d}.",
                 f"_p{n}_", f"_p{n}.", f"-p{n:03d}-", f"-{n:02d}.")
        for r in roots:
            try:
                cands = [q for q in sorted(r.iterdir())
                         if q.is_file() and q.suffix.lower() in (".png", ".jpg", ".jpeg")
                         and any(m in q.name for m in marks)]
            except OSError:
                continue
            if cands:
                return cands[0]
    return None


def _shot_staleness(slide: Path, host_only=False):
    """看的是不是**这一版**这一页。返回 None ＝ 没问题，否则返回一句话说明。

    只比时间戳，不做别的判断：**改完不重截，看的就还是改动之前的那张图**——
    这一条会发生：同一页改完之后直接拿旧图回答。
    """
    shot = _shot_of(slide, host_only=host_only)
    if shot is None:
        return ("还没有这一页的宿主真页截图。LOOK 不能用写入前本地预览代替——"
                "先写入、回读，再用 presentation + slide-id 截图。")
    try:
        if shot.stat().st_mtime + 1.0 < slide.stat().st_mtime:
            return (f"`{shot.name}` 比 `{slide.name}` 旧——这一页改过之后没有重新截图。")
    except OSError:
        return None
    return None


def _print_repair_ladder() -> None:
    """修法四档。**第四档是整页推翻重做**——它不在选项里，模型就不会走它。"""
    print("  下面四档只是帮助思考的候选方向，必须结合本页内容与宿主截图调整，不是绝对执行方案：")
    print("    ① **删掉可能更好**（压主体的板、空框、凑数的小图、多余装饰）；")
    print("    ② **挪位／换字色／重排这一叠**；")
    print("    ③ **这张图本身不对**（主体被裁、构图错、字下不安静、比例不符）→ "
          "改 prompt 按新画幅重新生图、这一页重排；")
    print("    ④ **整页推翻重做**——同一页改到第三次还不过，或这一页的内容本来就不该由这个装置承载"
          "（例：讲落地效果却拿一堆矩形拼界面）→ 回 Step 3 重新给这一页选装置与承载，"
          "重写 XML、重新备料。**推翻一页比在坏骨架上打七个补丁便宜。**")
    print("  新增加罩、加板或大面积托底前，先确认它解决的是页面关系本身，而不只是遮住症状。")


def _write_cmds(slide: Path):
    """机械 check=0 后给一条复合命令：写入 → 回读 → 宿主截图 → 打印 LOOK。"""
    cli = _which("lark-cli") or "lark-cli"
    readback = f"readback/{slide.stem}.xml"
    return [
        'DECK_ID="<id>" && mkdir -p readback hostshots && \\',
        f'SLIDE_ID="$({cli} slides xml_presentation.slide create \\',
        '  --params "{\\"xml_presentation_id\\":\\"$DECK_ID\\"}" \\',
        f'  --data "$(jq -n --rawfile c {slide} \'{{slide:{{content:$c}}}}\')" \\',
        '  --jq \'.data.slide_id // .slide_id // empty\' | tr -d \'"\')" && \\',
        'test -n "$SLIDE_ID" && \\',
        f'{cli} slides +xml-get --presentation "$DECK_ID" --slide-id "$SLIDE_ID" --output {readback} && \\',
        f'{cli} slides +screenshot --presentation "$DECK_ID" --slide-id "$SLIDE_ID" --output-dir hostshots && \\',
        f'python3 "$SKILL_ROOT/scripts/deck.py" check --slide {slide} --wrote {readback}',
    ]


def _after_write_cmds(slide: Path):
    """首次写入已由 `_write_cmds` 合并；保留函数避免旧调用点分叉。"""
    num = int(re.search(r"(\d+)", slide.stem).group(1)) if re.search(r"(\d+)", slide.stem) else 1
    return [
        f"# 宿主截图文件名应含页码 p{num:03d}；Read hostshots/ 下该页图片，再回答 LOOK。",
    ]


def _read_wrote(raw: str):
    if not raw:
        return ""
    p = Path(raw)
    try:
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else raw
    except OSError:
        return raw


def _wrote_check(page: Page, raw: str):
    """核对宿主回读 XML 与本地页骨架相符；不把 API 退出码当成功。"""
    text = _read_wrote(raw)
    if "<slide" not in text:
        return "`--wrote` 需要宿主回读的单页 XML 文件；只有 slide_id 或退出码不能证明写入内容正确。"
    try:
        host = Page(Path("<host-readback>"), text)
    except Exception as exc:                          # noqa: BLE001
        return f"宿主回读 XML 解析失败：{exc}"
    local_kinds = [b.kind for b in page.blocks]
    host_kinds = [b.kind for b in host.blocks]
    if abs(len(local_kinds) - len(host_kinds)) > 1:
        return f"宿主回读有 {len(host_kinds)} 块，本地 XML 有 {len(local_kinds)} 块，骨架没有完整写入。"
    local_text = [_norm_txt(b.text) for b in page.texts if len(_norm_txt(b.text)) >= 4]
    host_raw = _norm_txt(" ".join(b.text for b in host.texts))
    missed = [t for t in local_text[:5] if t[:4] not in host_raw]
    if missed:
        return "宿主回读缺少本地页文字：" + "、".join(x[:10] for x in missed[:3])
    return ""


def _deck_root_for_slide(slide: Path) -> Path:
    """把 `deck/slides/slide-NN.xml` 与 `deck/slide-NN.xml` 归到同一个运行目录。"""
    return slide.parent.parent if slide.parent.name == "slides" else slide.parent


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _write_look_receipt(slide: Path, wrote_raw: str, codes, answers) -> Path | None:
    """逐页 LOOK 通过后落一张可复算收据；它在项目运行目录，不增加 Skill 文件。"""
    root = _deck_root_for_slide(slide)
    outdir = root / ".visual-check"
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        wrote = Path(wrote_raw)
        shot = _shot_of(slide, host_only=True)
        payload = {
            "slide": str(slide.resolve()),
            "local_sha256": _file_sha256(slide),
            "readback": str(wrote.resolve()) if wrote.is_file() else "",
            "readback_sha256": _file_sha256(wrote) if wrote.is_file() else "",
            "hostshot": str(shot.resolve()) if shot and shot.is_file() else "",
            "answers": {c: {"result": answers[c][0], "observation": answers[c][1]}
                        for c in codes if c in answers},
        }
        target = outdir / f"{slide.stem}.json"
        temp = outdir / f".{slide.stem}.tmp"
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(target)
        return target
    except OSError:
        return None


def _delivery_receipts(looked) -> tuple[bool, int, list[str]]:
    """返回（是否进入交付模式、覆盖页数、问题清单）。离线语料扫描不伪装成交付。"""
    roots = {_deck_root_for_slide(p) for p, _pg in looked}
    active = any((r / ".visual-check").is_dir() or (r / "readback").is_dir()
                 or (r / "hostshots").is_dir() for r in roots)
    if not active:
        return False, 0, []
    covered = 0
    bad = []
    for path, page in looked:
        receipt = _deck_root_for_slide(path) / ".visual-check" / f"{path.stem}.json"
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            bad.append(f"{path.name}: 缺逐页 LOOK 收据")
            continue
        if data.get("local_sha256") != _file_sha256(path):
            bad.append(f"{path.name}: XML 在 LOOK 后又改过")
            continue
        rb = Path(data.get("readback") or "")
        if not rb.is_file() or data.get("readback_sha256") != _file_sha256(rb):
            bad.append(f"{path.name}: 回读缺失或已变化")
            continue
        wrote_error = _wrote_check(page, str(rb))
        if wrote_error:
            bad.append(f"{path.name}: {wrote_error}")
            continue
        shot = Path(data.get("hostshot") or "")
        if not shot.is_file():
            bad.append(f"{path.name}: 缺宿主真页截图")
            continue
        ans = data.get("answers") or {}
        if "02" not in ans or ans["02"].get("result") != "ok":
            bad.append(f"{path.name}: LOOK-02 没有逐图身份完整性观察")
            continue
        n_img = len(page.images) + (1 if page.ground_token else 0)
        face_texts = [t.text[:12] for t in getattr(page, "face_overlap_candidates", []) if t.text]
        identity_error = _identity_answer_error(ans["02"].get("observation", ""), n_img, face_texts)
        if identity_error:
            bad.append(f"{path.name}: LOOK-02 {identity_error}")
            continue
        if page.canvas_image is not None and _ground_is_picture(page, _deck_root_for_slide(path)):
            if "24" not in ans or ans["24"].get("result") != "ok":
                bad.append(f"{path.name}: 满版画面缺 LOOK-24 源质观察")
                continue
            source_error = _source_quality_answer_error(ans["24"].get("observation", ""))
            if source_error:
                bad.append(f"{path.name}: LOOK-24 {source_error}")
                continue
        covered += 1
    return True, covered, bad


def _delivery_ready_path(root: Path) -> Path:
    return root / ".visual-check" / "DELIVERY-READY"


def _clear_delivery_ready(root: Path) -> None:
    try:
        _delivery_ready_path(root).unlink(missing_ok=True)
    except OSError:
        pass


def _write_delivery_ready(root: Path, looked) -> str:
    """终验真值落盘；下一次 check --deck 开始即作废，避免旧钥匙跨稿沿用。"""
    rows = []
    deck_ids = set()
    for path, _page in looked:
        receipt = root / ".visual-check" / f"{path.stem}.json"
        rows.append(f"{path.name}:{_file_sha256(path)}:{_file_sha256(receipt)}")
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
            shot = Path(data.get("hostshot") or "")
            m = re.match(r"(.+)_p\d+", shot.stem)
            if m:
                deck_ids.add(m.group(1))
            rows.append(f"{_file_sha256(Path(data.get('readback') or ''))}:{_file_sha256(shot)}")
        except (OSError, json.JSONDecodeError):
            pass
    deck_id = next(iter(deck_ids)) if len(deck_ids) == 1 else root.resolve().name
    digest = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()[:12]
    line = f"READY {deck_id} {len(looked)}页 覆盖{len(looked)}/{len(looked)} {digest}"
    target = _delivery_ready_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(".DELIVERY-READY.tmp")
    temp.write_text(line + "\n", encoding="utf-8")
    temp.replace(target)
    return line


def _covered_pairs(page: Page):
    """**上层把下层盖住**的那几对——只报事实，是不是有意的由执行者看截图判。

    排除三类正当叠印，否则一页会报出十几条噪音：
      ① 上层完整落在下层的无字色块里（＝卡片／相纸边框，那是成文手法）；
      ② 字完整落在自己的托片里；③ 幽灵层（α<0.5）压内容。
    也**不报正常文字行的行盒相接**（那是 -6px，每页十几处，全是噪音）。
    """
    bs = [b for b in page.blocks if b.box[2] > 2 and b.box[3] > 2]
    out = []
    for i, a in enumerate(bs):
        for c in bs[i + 1:]:
            if (a.box[2] * a.box[3] >= 0.85 * CANVAS_W * CANVAS_H
                    or c.box[2] * c.box[3] >= 0.85 * CANVAS_W * CANVAS_H):
                continue                               # 满版底层，GRD 那一族管
            if a.kind == "line" or c.kind == "line":
                continue
            lo, hi = (a, c) if a.order < c.order else (c, a)
            ox = min(a.box[0] + a.box[2], c.box[0] + c.box[2]) - max(a.box[0], c.box[0])
            oy = min(a.box[1] + a.box[3], c.box[1] + c.box[3]) - max(a.box[1], c.box[1])
            if ox <= 2 or oy <= 2:
                continue
            lx, ly, lw, lh = lo.box
            hx, hy, hw, hh = hi.box
            inside = (lx - 2 <= hx and ly - 2 <= hy
                      and lx + lw + 2 >= hx + hw and ly + lh + 2 >= hy + hh)
            if lo.kind == "shape" and lo.fill and inside:
                continue                               # 托片／相纸边框；字落在自己的托片里
            if hi.is_text and (hi.font_color or (0, 0, 0, 1))[3] < 0.5:
                continue                               # 幽灵层压内容是成文装置
            if hi.kind == "shape" and hi.fill and not hi.text and "gradient" in (hi.fill or ""):
                continue                               # 通幅渐变承文，FOG 那一族管
            covered = ox * oy / max(lw * lh, 1)
            if lo.kind == "img" or (lo.is_text and lo.text and covered >= 0.30):
                out.append((covered, lo, hi, ox, oy))
    out.sort(key=lambda r: -r[0])
    return out


def _blk_name(b) -> str:
    t = (b.text or "").strip()[:10]
    return ("「%s」" % t) if t else {"img": "图", "shape": "形状", "chart": "图表",
                                     "table": "表格"}.get(b.kind, b.kind)


def _small_texts(page: "Page"):
    """这一页 ≤12pt 的那几行字（去掉太短的）。

    它们逐页天生不同（页码 `01 / 18`、眉行、来源行）——标定样本中的成稿
    **64 页 64 种互不相同的小字集合、0 页没有小字**。所以「把它们照抄回来」
    这件事，**一串常量答案在第二页上必然对不上**。
    """
    out = []
    for b in page.texts:
        if 0 < b.max_pt <= 12:
            s = (b.text or "").strip()
            if len(_norm_txt(s)) >= 4:
                out.append(s)
    return out


def _norm_txt(s: str) -> str:
    """比对用的归一化：去空白与标点，只留字母数字与汉字。"""
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", s or "")


def _quotes_page_text(answer: str, page: "Page", only=None) -> bool:
    """理由是否引用了这一页真实存在的文字，而不是复述规则名。"""
    a = _norm_txt(answer)
    blocks = only if only is not None else page.texts
    for b in blocks:
        n = _norm_txt(b.text if hasattr(b, "text") else str(b))
        if len(n) >= 4 and any(n[i:i + 4] in a for i in range(len(n) - 3)):
            return True
    return False


def _quotes_page_evidence(answer: str, page: "Page") -> bool:
    """页内证据＝真实文字，或带坐标/尺寸语义且命中本页几何的数字。"""
    if _quotes_page_text(answer, page):
        return True
    if not re.search(r"坐标|尺寸|位置|宽|高|左|右|上|下|x|y|w|h", answer, re.I):
        return False
    nums = {int(float(x)) for x in re.findall(r"\d+(?:\.\d+)?", answer)}
    geom = {int(round(v)) for b in page.blocks for v in b.box}
    return bool(nums & geom)


def _quotes_small_text(answer: str, page: "Page") -> bool:
    """答案里有没有真的抄回这一页的某一句小字（≥4 字连续匹配）。"""
    a = _norm_txt(answer)
    if len(a) < 4:
        return False
    for s in _small_texts(page):
        n = _norm_txt(s)
        if len(n) < 4:
            continue
        if n in a:
            return True
        # 抄一半也算（页码/眉行常被截断），要求连续 ≥4 字
        for i in range(len(n) - 3):
            if n[i:i + 4] in a:
                return True
    return False


def _small_text_dispute(page: "Page", deck_dir: Path) -> str:
    """最小的那几行字，机器有没有不利读数（对比度不足 / 底纹太重）。

    有读数就把它附在 LOOK-05 后面，并把这一条标成「机器有异议」——
    那时空 `ok` 不被接受，要写一句为什么它其实读得清。
    """
    smalls = [b for b in page.texts if 0 < b.max_pt <= 12]
    if not smalls:
        return ""
    bits = []
    share = getattr(page, "ground_quiet_share", None)
    if share is not None and share < TEXTURE_QUIET_MIN:
        # **这一页的地是哪一种，说法就得跟着变**：底纹的合格线是 85%，
        # 而满版画面／氛围底图本来就不该满屏安静——对它们说「达不到 85%」是误导。
        if getattr(page, "ground_kind", "") == "底纹":
            bits.append(f"这一页的纹理地安静区只占 {share:.0%}（合格线 {TEXTURE_QUIET_MIN:.0%}）")
        else:
            bits.append(f"这一页的地是画面，它的安静区只占 {share:.0%}——"
                        "落在安静区外的小字要在截图上确认读得清")
    ranked = getattr(page, "text_on_picture", None)
    if ranked:
        worst = [r for r in ranked if r[0] < 3.0 and r[2].max_pt <= 12]
        if worst:
            bits.append(f"最小的字里有 {len(worst)} 块压在画面上、中位对比度低到 {worst[0][0]:.1f}:1")
    if not bits:
        return ""
    return "（机器读数：" + "；".join(bits) + "）"


def _look_items(page: Page, path: Path, deck_dir: Path):
    """这一页要看的几问：恒问三条 ＋ 最多三条按风险排序的条件问。

    **这些问句是给执行者（模型）看的，不是给人类设计师看的。**
    「眯眼看」「凭感觉」这类动作模型做不了；能做的是**数、指认、照读**——
    所以每条写成「一个可执行的动作 ＋ 要交回的具体内容」，
    并把 `check` 已经算出的数值附在后面：**答案与打印出来的事实对不上时是看得出来的**。
    """
    items: list[tuple[str, str]] = []
    imgs = list(page.images)
    n_img = len(imgs) + (1 if page.ground_token else 0)
    shapes = [b for b in page.blocks if b.kind == "shape" and b.fill and not b.text]
    job = ""
    m = re.search(r"job\s*=\s*([^\s]+)", page.header or "")
    if m:
        job = m.group(1).strip()

    # ── 恒问三条：遮挡、身份完整性、视觉重点；其余能机判的已经下沉到 error/note ──
    covers = _covered_pairs(page)
    if covers:
        lines_ = "；".join(
            "%s被%s盖住 %.0f×%.0fpx（盖住它 %.0f%%）"
            % (_blk_name(lo), _blk_name(hi), ox, oy, cv * 100)
            for cv, lo, hi, ox, oy in covers[:3])
        tail = f"（几何上算出 {len(covers)} 处：{lines_}）"
    else:
        tail = "（几何上算不出重叠，但图压图、图压细字这类在截图上才看得见）"
    items.append(("LOOK-01", "截图上**有几处遮挡**？逐处说出**谁压住了谁**"
                             "（图压文字／文字压图／板压图／小图压大图）。"
                             "每一处再答：**这是有意的堆叠吗？**被压住的那块还认得出来吗？" + tail,
                  bool(covers)))
    face_candidates = list(dict.fromkeys(t.text[:12] for t in
                                         getattr(page, "face_overlap_candidates", []) if t.text))
    face_tail = ""
    if face_candidates:
        face_tail = ("机器量到主体候选框与这些文字相交："
                     + "、".join(f"「{x}」" for x in face_candidates[:5])
                     + "。逐块看五官与脸轮廓；都没压就追加 `|压脸=无（已核对「…」）` 并列全这些字，"
                       "任一块压住眼、鼻、嘴、眉或脸轮廓就答 fix 并点名那块字。")
    items.append(("LOOK-02", f"逐张看这 {max(1, n_img)} 张画面，用固定格式逐图结账："
                             "`图1=主体名|头顶=内|额头=内|下巴=内|左脸界=内|右脸界=内`；"
                             "纯风景/纹理/排版写 `图1=纯场景`，产品写 `图1=产品名|轮廓=内`。"
                             "头脸任一边界不是完整在画面内就答 fix；半脸、触边或越界不得以 bleed、"
                             "艺术化裁切、仍可辨认或设计意图翻转。若源图本身缺像素，只能按实际情况换素材。"
                             + face_tail, bool(face_candidates)))
    items.append(("LOOK-09", "不读文字内容，只看形状与明暗——**最先抓住视线的是哪一块？**"
                             "说出它的位置和它是什么。那是你想让读者先看的那一块吗？"
                             "**如果最先看到的是一块底板、一条分隔线或一行小字，这一页就没有视觉重点。**", False))

    cond: list[tuple[str, str]] = []

    # 满版图的源质不能靠 XML 判：它可能是拼接截图、左右已截断，或自带段落/气泡/页眉。
    # 每张画面地只缴一问，场景原生招牌不与资料文字混为一谈。
    if page.canvas_image is not None and _ground_is_picture(page, deck_dir):
        edges = getattr(page, "ground_edge_lines", None)
        edge_fact = (f"机器还量到贴边竖线 x{edges[0]} / x{edges[1]}；" if edges else "")
        aspect = getattr(page, "ground_aspect_risk", None)
        aspect_fact = (f"源图 {aspect[0]}×{aspect[1]} 与页面比例偏差 {aspect[4]:.0%}；"
                       if aspect else "")
        cond.append(("LOOK-24", "这是一张满版画面。" + aspect_fact + edge_fact
                                + "按固定格式回答 `源图=单一完整画面|边缘=完整|资料字=无`。"
                                  "逐项看：左右是否自然延续、有没有拼接条/占位灰块/被截断；"
                                  "图内有没有段落、气泡、页眉、图注等资料文字。"
                                  "场景本来就有的招牌或 Logo 可另写 `|场景字=「…」`，不算资料字；"
                                  "只要源图不是单一完整画面、边缘不完整或资料字不为无，就答 fix，"
                                  "换素材或重新生图；这些修法只是方向，按本页实际情况调整。"))

    # 旧 LOOK-03/04/06/07/08 已由 OVL/GRD/DEV/IMG/DIV 等机械事实覆盖；
    # 只有机器真的量到小字风险时，才把原 LOOK-05 拉回来，避免每页固定缴费。
    hard_small = _small_text_dispute(page, deck_dir)
    n_small = len(_small_texts(page))
    if hard_small:
        cond.append(("LOOK-05", f"截图上最小的那几行字（这一页有 {n_small} 处）里有机器不利读数。"
                                "把其中任意一句照抄回答案里；读不出来就是不合格。" + hard_small))

    # E-b 只凭 `cover=` 订单不能结账：宿主真图必须证明被盖侧确实为空，且主体不骑分界。
    if getattr(page, "cover_reason", ""):
        cond.append(("LOOK-23", f"本页声明 `cover={page.cover_reason}`。对着宿主截图逐项回答："
                                "被盖侧在覆盖前是否真的是空面？人物/角色/产品有没有骑在色块分界上，"
                                "被切头、切脸、切身体或切产品？回答要点名实际主体或页面文字。"))

    # ① 地是画面 / 地是纹理：字落在哪、读不读得清（把 check 量到的数附给恒问 05）
    if page.canvas_image is not None and getattr(page, "ground_kind", "画面") != "底纹":
        measured = hasattr(page, "ground_kind")       # 地图能打开＝像素判据跑过了
        ranked = getattr(page, "text_on_picture", None)
        if not measured:
            cond.append(("LOOK-21", "这一页的地是画面，但这台机器量不到它（见上面的 PIX-000）——"
                                    "截图上**亲自找**那片安静区：每一叠字底下是安静面还是画面内容？"
                                    "有没有压住人脸／主体？"))
        else:
            worst = ranked[0] if ranked else None
            busy = getattr(page, "busy_texts", [])
            if busy or worst:
                names = [t.text[:14] for t, _v in busy[:5]] or [worst[2].text[:14]]
                cond.append(("LOOK-21", "这一页的地是画面。请在宿主截图中逐项核对 "
                                        + "、".join(f"「{x}」" for x in names)
                                        + "：字是否完整落在可承文区域、是否越出承字区、是否盖住人物/角色/产品。"
                                          "答案必须照抄至少一段上述页面文字，并说出它与画面的实际关系。"
                                          "如有问题，可按实际情况考虑迁字、换字色、重排或换图；"
                                          "这些只是建议，不是绝对执行方案。"))
    if page.canvas_image is not None and getattr(page, "ground_kind", "") == "底纹":
        share = getattr(page, "ground_quiet_share", None)
        if share is not None and share < TEXTURE_QUIET_MIN:
            cond.append(("LOOK-21", "这一页的地是纹理地，而这张纹理的安静区只占 %.0f%%——纹理偏重。"
                                    "截图上最小的那几行字要是读不出来，就是这张纹理不合格，"
                                    "**重新生成它**（image-direction §八·2），"
                                    "✗ 不要靠加托底或把字放大来救。" % (share * 100)))

    # ② 多图：成组
    if len(imgs) >= 2:
        ws = {round(b.box[2]) for b in imgs}
        hs = {round(b.box[3]) for b in imgs}
        tops = {round(b.box[1]) for b in imgs}
        cond.append(("LOOK-11", f"这一页有 {len(imgs)} 张图（宽 {len(ws)} 种、高 {len(hs)} 种、"
                                f"顶线 {len(tops)} 条）：并排的几张同宽同高、共用顶线底线、"
                                "间距相等吗？主图面积 ≥ 最小图的 2.5 倍吗？"
                                "不成组的几张图，读者看到的是「临时贴上去的」。"))

    # ③ 左右并排：天沟
    if imgs and page.texts:
        for b in imgs:
            right = b.box[0] + b.box[2]
            cols = [x for x in page.texts if x.box[0] >= right - 2 and x.box[0] < right + 30
                    and x.box[1] + x.box[3] > b.box[1] and x.box[1] < b.box[1] + b.box[3]]
            if cols:
                gap = min(x.box[0] for x in cols) - right
                cond.append(("LOOK-12", f"图右沿 x{right:.0f}，右边那一列内容从 x"
                                        f"{min(x.box[0] for x in cols):.0f} 起——天沟只有 {gap:.0f}px。"
                                        "图与内容列之间要 ≥24px，挨得近不是紧凑是没留缝；修时整列一起挪。"))
                break

    # ④ 出血：≥12% 版面却四边都留白
    for b, ml, mt, mr, mb in _inset_images(page):
        cond.append(("LOOK-13", f"这张 {b.box[2]:.0f}×{b.box[3]:.0f} 的图"
                                f"（占版 {b.box[2]*b.box[3]/(CANVAS_W*CANVAS_H):.0%}）"
                                f"四边分别留了 {ml:.0f}/{mt:.0f}/{mr:.0f}/{mb:.0f}px，一条页缘都没碰到。"
                                "**参照库里 ≥12% 版面的画面块有 94% 至少切到一条页缘**——"
                                "四边留白只在「这块图本身是一件被展示的物件」"
                                "（样张、色卡、单件产品图）时成立。它是吗？不是就让它切到一条页缘。"))
        break

    # ⑤ 图窗比与源图比不符
    for b in imgs:
        w, h = b.box[2], b.box[3]
        if w <= 0 or h <= 0:
            continue
        im = _load_asset(b.src, deck_dir)
        if im is None:
            continue
        sw, sh = im.size
        if sw <= 0 or sh <= 0:
            continue
        want, got = w / h, sw / sh
        if abs(want - got) / max(want, got) <= 0.08:
            continue
        cut = 1 - min(want, got) / max(want, got)
        order = _order_size(w, h)
        tail = (f"要整图就**按新画幅重新生成**：`width={order[0]} height={order[1]}`"
                "（image-direction §六）" if order else "")
        cond.append(("LOOK-22", f"图窗 {w:.0f}×{h:.0f}（比 {want:.2f}）与源图 {sw}×{sh}"
                                f"（比 {got:.2f}）对不上：宿主会从中心裁掉约 {cut:.0%}。"
                                f"截图上看主体是不是被切了——切了就不要靠 crop 反复试，{tail}。"))
        break

    # ⑥ 一张图都没有、却拿一堆矩形拼「东西的样子」
    n_rect = len([b for b in page.blocks if b.kind == "shape" and b.fill and not b.text])
    if n_img == 0 and n_rect >= 8:
        low = job.lower()
        hit = any(k in low for k in _APPLY_JOBS)
        head = (f"这一页 0 张图、{n_rect} 个填充形状，job={job or '未写'}。"
                if hit or not job else f"这一页 0 张图、{n_rect} 个填充形状。")
        cond.append(("LOOK-14", head +
                     "**把页面上所有文字删掉之后，读者还能看出这是哪个对象的什么东西吗？**"
                     "看不出来就是线框图不是画面——讲规范时矩形是图解、成立；"
                     "讲落地效果（应用/门店/物料/界面/产品）时它什么都没证明，"
                     "这一页要放真实素材或高保真图。"))

    # ⑦ 有图：每张图的名分
    if imgs:
        cond.append(("LOOK-15", f"逐张问这 {len(imgs)} 张图：它服务本页哪一句话？"
                                "说不出来的删掉或换成对得上的那一张；"
                                "正文点名了几个对象，配图就要逐个对应。"))

    # ⑧ 图表
    if any(b.kind in ("chart", "table") for b in page.blocks):
        cond.append(("LOOK-16", "这一页有原生图表/表格：关键数值直标在柱/线端了吗？"
                                "读者要靠坐标轴估读就不算读得到。"))

    # ⑨ 大面积罩/板：承文走到第几档
    big = [b for b in shapes if b.box[2] * b.box[3] >= 0.35 * CANVAS_W * CANVAS_H]
    if big and page.canvas_image is not None:
        cond.append(("LOOK-17", f"画面上盖着一块 {big[0].box[2]:.0f}×{big[0].box[3]:.0f} 的填充形状："
                                "它盖住的是空面还是主体/细节？为什么本页需要走到这一档？"
                                "迁字、换字色、重排、换图或保留都只是候选方向，"
                                "必须按宿主截图实际情况判断，不是绝对执行方案。"))

    # ⑩ 文字预算
    chars = sum(len(x.text) for x in page.texts if x.max_pt > 11)
    if chars > 180:
        cond.append(("LOOK-18", f"可见文字约 {chars} 字（章节页 ≤40／视觉页 ≤120／论证页 ≤180）："
                                "读者会读完吗？超了就**删、拆、换结构**，不是缩字号。"))

    # ⑪ 装置声明 ↔ 几何（DEV-001 已报事实，这里问它在截图上长什么样）
    for name, want, got in _device_mismatch(page)[:1]:
        cond.append(("LOOK-19", f"页首写的是 {name}（{want}），但{got}——"
                                "截图上这一页是不是就成了「白边里浮着一块内容」？"
                                "要么把几何做成这个装置该有的样子，要么把 `device=` 改成实际做的那个。"))

    # ⑫ 孤图
    for b, near in _orphan_images(page)[:1]:
        cond.append(("LOOK-20", f"那张 {b.box[2]:.0f}×{b.box[3]:.0f} 的小图"
                                f"（四周最近的块在 {near:.0f}px 外、与任何块都不共轴）"
                                "服务本页哪一句话？说不出来就删掉——删除永远合法。"))

    # 条件问是**按几何触发**的——它们出现本身就意味着机器算出了一个不利事实，
    # 所以一律标为「机器有异议」：这几条的 `ok` 必须带一句理由。
    return items + [(c, txt, True) for c, txt in cond[:3]]


def _parse_looked(raw: str):
    """把 `--looked '01:ok 02:fix 图注读不出来'` 解析成 {码: (判词, 说明)}。

    只认两个词：`ok`（这条过了）与 `fix`（要改）；理由跟在后面，`ok@理由` 与 `ok:理由` 等价。
    **机器有异议的那几问，`ok` 后面必须有理由**——理由是用来翻转机器读数的。
    一般问句不校验说明措辞；LOOK-02 例外，必须留下逐图的身份完整性观察，
    否则「有意裁切」会再次替代真正的看图。
    """
    out: dict[str, tuple[str, str]] = {}
    if not raw:
        return out
    # 说明里可以有数字（问句本来就问「占多少」「有几处」）——
    # 断句只靠「空白 ＋ 两位数 ＋ 冒号」这个下一问的起手式，不靠「说明里不许出现数字」。
    for m in re.finditer(r"(?:LOOK[-_]?)?(\d{1,2})\s*[:：]\s*(ok|fix|OK|FIX)\b(.*?)"
                         r"(?=(?:\s+(?:LOOK[-_]?)?\d{1,2}\s*[:：]\s*(?:ok|fix|OK|FIX)\b)|$)",
                         raw, re.S):
        why = m.group(3).strip(" ，,、;；")
        # `ok@<理由>` 与 `ok:<理由>` 都收；@ 只是把「这是翻转机器读数的理由」说清楚
        why = why.lstrip("@:：").strip()
        out[m.group(1).zfill(2)] = (m.group(2).lower(), why)
    return out


_IDENTITY_EXCUSES = ("艺术化", "设计意图", "bleed", "有意裁切", "半脸", "半张脸",
                     "关键特征", "仍可辨", "可辨认")
_IDENTITY_EMPTY = ("纯场景", "纯风景", "纯纹理", "纯排版", "无人物", "无角色", "无产品")
_IDENTITY_BOUNDS = ("头顶=内", "额头=内", "下巴=内", "左脸界=内", "右脸界=内")


def _identity_answer_error(raw: str, image_count: int, face_texts=None) -> str:
    """LOOK-02 的结构门：逐图、逐边界；身份红线不得被自由文本翻转。"""
    text = (raw or "").strip()
    hit = next((w for w in _IDENTITY_EXCUSES if w.lower() in text.lower()), "")
    if hit:
        return f"身份完整性答案用了『{hit}』翻转红线"
    clauses = re.findall(r"图(\d+)\s*=\s*(.*?)(?=(?:[；;]\s*)?图\d+\s*=|$)", text)
    need = max(1, image_count)
    if len(clauses) != need or {int(n) for n, _v in clauses} != set(range(1, need + 1)):
        return f"必须按图1…图{need}逐张结账（现在识别到 {len(clauses)} 张）"
    for n, value in clauses:
        if any(w in value for w in _IDENTITY_EMPTY):
            continue
        if "轮廓=内" in value:
            continue
        missing = [x for x in _IDENTITY_BOUNDS if x not in value]
        if missing:
            return f"图{n}缺少身份边界：{'、'.join(missing)}"
    wanted = [str(x) for x in (face_texts or []) if str(x).strip()]
    if wanted:
        if "压脸=无" not in text:
            return "本页文字与主体候选框相交，缺少 `压脸=无（已核对…）`；若确实压脸应直接答 fix"
        norm = _norm_txt(text)
        missed = [x for x in wanted if _norm_txt(x) not in norm]
        if missed:
            return "压脸答案没有逐块点回本页候选文字：" + "、".join(f"「{x}」" for x in missed[:5])
    return ""


def _source_quality_answer_error(raw: str) -> str:
    """LOOK-24 的结构门：满版源图必须对边缘与图内资料字分别结账。"""
    text = re.sub(r"\s+", "", raw or "")
    need = ["源图=单一完整画面", "边缘=完整", "资料字=无"]
    missing = [x for x in need if x not in text]
    return ("缺少结构化源质结论：" + "、".join(missing)) if missing else ""



def _rgba_ls(color: str):
    """从 `rgba(r,g,b,a)` 里取出明度(0–255)与饱和度(0–1)。取不到返回 None。"""
    m = re.findall(r"[\d.]+", color or "")
    if len(m) < 3:
        return None
    r, g, b = (float(m[0]), float(m[1]), float(m[2]))
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    mx, mn = max(r, g, b), min(r, g, b)
    return lum, (0.0 if mx <= 0 else (mx - mn) / mx)


def _img_ls(im):
    """一张图的明度中位与饱和中位（缩到 96×54 再量，够用且快）。"""
    sm = im.resize((96, 54))
    px = list(sm.getdata())
    lums, sats = [], []
    for r, g, b in px:
        lums.append(0.299 * r + 0.587 * g + 0.114 * b)
        mx, mn = max(r, g, b), min(r, g, b)
        sats.append(0.0 if mx <= 0 else (mx - mn) / mx)
    lums.sort(); sats.sort()
    return lums[len(lums) // 2], sats[len(sats) // 2]


def _print_ground_composition(looked, deck_dir) -> None:
    """地的构成账与明暗饱和账（码 GND-002）——**只报事实，不设门**。

    `GND-001` 只说「铺满整页的底图 N 页」，**不区分那 N 页的底图里装的是纹理还是画面**；
    而"最高频的那张地"就是这一稿的脸，这一笔账要把它摆出来。

    ✗ 不设阈值：参照库逐份「整页一张画面」从 0% 到 100% 都有，明度中位跨 39–221、
    饱和中位跨 0.03–0.66——任何配比门都会判死其中几份（同类门作废过一次）。
    """
    if deck_dir is None:
        return
    picture = ambient = texture = flat = 0
    lums, sats = [], []
    freq: dict = {}
    measured = 0
    for _pth, pg in looked:
        if pg.canvas_image is not None:
            src = _ground_src(pg)
            if src:
                freq[src] = freq.get(src, 0) + 1
            im = _load_asset(src, deck_dir)
            if im is None:
                continue
            measured += 1
            _ok, share, _lo, _se = _texture_verdict(im)
            if share >= TEXTURE_QUIET_MIN:
                texture += 1
            elif share >= AMBIENT_QUIET_MIN:
                ambient += 1
            else:
                picture += 1
            l, sa = _img_ls(im)
            lums.append(l); sats.append(sa)
        else:
            flat += 1
            ls = _rgba_ls(pg.ground_color)
            if ls:
                measured += 1
                lums.append(ls[0]); sats.append(ls[1])
    if measured < 3:
        return
    lums.sort(); sats.sort()
    lmed = lums[len(lums) // 2]
    smed = sats[len(sats) // 2]
    band = ("极暗" if lmed <= 60 else "暗" if lmed <= 120 else "中" if lmed <= 180 else "亮")
    sband = ("近无彩" if smed <= 0.05 else "低" if smed <= 0.15 else "中" if smed <= 0.30 else "高")
    print(f"· [GND-002] 地的构成：满版画面 {picture} 页 · 氛围底图 {ambient} 页 · "
          f"纹理地 {texture} 页 · 纯平色地 {flat} 页。")
    if freq:
        top_src, top_n = max(freq.items(), key=lambda kv: kv[1])
        if top_n >= 2:
            kind = "？"
            im = _load_asset(top_src, deck_dir)
            if im is not None:
                _o, sh, _l, _s = _texture_verdict(im)
                kind = ("纹理" if sh >= TEXTURE_QUIET_MIN
                        else "氛围底图" if sh >= AMBIENT_QUIET_MIN else "画面")
            print(f"            **最高频的那张地铺了 {top_n} 页，它是一张「{kind}」**——"
                  "这就是这一稿的脸。读者该记住的是它吗？")
    print(f"            全稿明度中位 {lmed:.0f}（{band}带）· 饱和中位 {smed:.2f}（{sband}）"
          "——按每页的地量的，不是整页渲染。")
    print("            参照库 11 份逐份：整页一张画面 0%–100%（中位 58%）· "
          "明度中位 39–221 · 饱和中位 0.03–0.66。**这是坐标不是门**——"
          "两端都成立，中间那一带才是「哪一份都像」的地方（`_routing.md` 六个旋钮）。")


def _contract_items(raw: str):
    """交付合同支持一行一项，或 JSON list / `{items:[...]}`；不引入额外脚本。"""
    if not raw:
        return []
    text = _read_wrote(raw)
    try:
        obj = json.loads(text)
        vals = obj.get("items", []) if isinstance(obj, dict) else obj
        if isinstance(vals, list):
            return [str(x).strip() for x in vals if str(x).strip()]
    except Exception:                                  # noqa: BLE001
        pass
    return [re.sub(r"^\s*[-*\d.、]+\s*", "", x).strip()
            for x in text.splitlines() if x.strip() and not x.lstrip().startswith("#")]


def _full_deck_accounts(looked, deck_dir: Path, contract: str):
    """合同与资产账并入同一次全稿 check。返回新增 error 数。"""
    errors = 0
    items = _contract_items(contract)
    if items:
        claims = _norm_txt(" ".join(pg.header for _p, pg in looked))
        missing = [x for x in items if _norm_txt(x) not in claims]
        if missing:
            errors += len(missing)
            print(f"✗ [CT-001] 交付合同有 {len(missing)} 项没有被任何页头 `deliver=` 承接："
                  + "、".join(missing[:5]))
            print("            页面如何承接由内容与设计决定；拆页、合并或改承载都只是建议，"
                  "不是必须照做的处方。")
        else:
            print(f"· [CT-001] 交付合同 {len(items)} 项都能在页头 `deliver=` 找到承接页。")

    table_path, rows = _token_rows(deck_dir)
    if rows:
        declared = {tok for tok, _name in rows}
        used = {src for _p, pg in looked for src in
                ([pg.ground_token] + [b.src for b in pg.images]) if src}
        tokenish = {x for x in used if re.fullmatch(r"[A-Za-z0-9_-]{16,80}", x)}
        unused = sorted(declared - used)
        missing = sorted(tokenish - declared)
        if unused:
            errors += len(unused)
            print(f"✗ [AS-001] `{table_path}` 有 {len(unused)} 个已上传资产没有进入任何页面。"
                  "上传而未使用通常意味着交付漏项；也可能是已废弃素材，请按本稿事实处理。")
        if missing:
            errors += len(missing)
            print(f"✗ [AS-002] 有 {len(missing)} 个页面 token 不在 `{table_path}`："
                  "像素检查会失明，也无法核对素材是否入稿。")
        digests: dict[str, list[str]] = collections.defaultdict(list)
        for _tok, name in rows:
            p = _resolve_asset(name, deck_dir)
            if p:
                try:
                    digests[hashlib.md5(p.read_bytes()).hexdigest()].append(name)  # noqa: S324
                except OSError:
                    pass
        dup = [v for v in digests.values() if len(v) > 1]
        if dup:
            print(f"· [AS-003] 资产表里有 {len(dup)} 组像素完全相同的文件："
                  + "；".join("/".join(x[:3]) for x in dup[:3])
                  + "。它可能是有意复用，也可能是重复备料；只报事实，不设门。")
    return errors


def cmd_check(args) -> int:
    if getattr(args, "prompt", None):
        bad = []
        for i, one in enumerate(args.prompt, 1):
            low = one.lower()
            if any(w in low for w in _IT_SAFE):
                continue
            hit = [w for w in _IT_WORDS if w in low]
            if hit:
                bad.append((i, hit[:3]))
        for i, hit in bad:
            print(f"  ✗ [IT-001] 第 {i} 条 prompt 里有 {hit}——生图工具画不出正确的可读文字，"
                  "写了就是一堆假字母压在画面上（「PPT 套 PPT」）。")
        if bad:
            print("  屏幕/店招/包装面上要有内容时，写**面上是什么材质、什么图形**，"
                  "不要写要显示什么字；每条 prompt 末尾带 `no text, no numbers, no logos`"
                  "（image-direction §四）。")
            return 1
        print("CHECK prompt: 没有图内文字风险。")
        return 0
    targets: list[Path] = []
    if args.slide:
        targets += [Path(p) for p in args.slide]
    if args.deck:
        # **按 hostcheck 教的目录形状找**：页面通常落在 `<deck>/slides/`，
        # 文件名 `slide-NN.xml` 或 `pNN.xml` 都有人写。只认一种形状 = 全稿模式永远找不到东西。
        root = Path(args.deck)
        found: list[Path] = []
        for base in (root, root / "slides"):
            for pat in ("slide-*.xml", "p*.xml", "slide_*.xml"):
                found += [q for q in base.glob(pat) if q.is_file()]
        seen_paths = set()
        for q in sorted(found, key=lambda x: (
                x.parent.as_posix(),
                int(re.search(r"(\d+)", x.stem).group(1)) if re.search(r"(\d+)", x.stem) else 10**9,
                x.name)):
            if q.resolve() not in seen_paths:
                seen_paths.add(q.resolve())
                targets.append(q)
    targets = [p for p in targets if p.is_file()]
    if not targets:
        print("BLOCK: 没找到要检查的文件。用 --slide <文件> 或 --deck <目录>。")
        return 2
    deck_dir = Path(args.deck) if args.deck else None
    if deck_dir is not None:
        _clear_delivery_ready(deck_dir)
    total_e = 0
    pix_blind: list[tuple[str, str]] = []
    thin_notes: list[str] = []
    signatures: list[tuple[str, tuple]] = []
    looked: list[tuple[Path, Page]] = []
    grounds: dict = {}
    ground_src: dict = {}
    for path in targets:
        errors, notes, page_obj = _find(path, deck_dir or path.parent)
        if page_obj is not None:
            looked.append((path, page_obj))
            if page_obj.canvas_image is None:
                grounds[path.name] = "实色"
            else:
                grounds[path.name] = getattr(page_obj, "ground_kind", None) or (
                    "底纹" if _looks_like_texture(page_obj) else "画面")
                ground_src[path.name] = _ground_src(page_obj)
        total_e += len(errors)
        shown = [(c, m) for c, m in notes if c not in ("PIX-000", "NOTE-002")]
        for c, m in notes:
            if c == "PIX-000":
                pix_blind.append((path.name, m))
        if any(c == "NOTE-002" for c, _m in notes):
            thin_notes.append(path.name)
        try:
            size = len(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            size = 0
        nblk = len(page_obj.blocks) if page_obj is not None else 0
        bulk = ""
        if size > 12000:
            bulk = ("  ⚠ 这一页 %.1fKB——真稿单页中位 4.5KB、最多 10.5KB，"
                    "超过 12KB 基本是塞了两页的内容：先拆页再写。"
                    "（写这一页的回合越长，会话中断的概率越高。）" % (size / 1000))
        print(f"── {path.name}  error {len(errors)} · note {len(shown)}"
              f" · {size} 字符 / {nblk} 块{bulk}")
        for code, msg in errors:
            print(f"  ✗ [{code}] {msg}")
        for code, msg in shown:
            print(f"  · [{code}] {msg}")
        try:
            signatures.append((path.name, _page_signature(
                Page(path, path.read_text(encoding="utf-8", errors="replace")))))
        except Exception:                              # noqa: BLE001
            pass
    print()
    if thin_notes:
        print(f"· [NOTE-002] 有 {len(thin_notes)} 页的讲稿几乎没写"
              f"（{', '.join(thin_notes[:3])}{'…' if len(thin_notes) > 3 else ''}）："
              "每页要 3–5 句可直接照读的话，它写在页面渲染之外，加它不动任何一处版面。")
    if pix_blind:
        names = ", ".join(n for n, _m in pix_blind[:3])
        print(f"· [PIX-000] 有 {len(pix_blind)} 页的底图在本地取不到"
              f"（{names}{'…' if len(pix_blind) > 3 else ''}）。"
              + pix_blind[0][1].split("：", 1)[-1])
    if args.deck:
        total_e += _full_deck_accounts(looked, deck_dir, getattr(args, "contract", ""))
    # ── 地与出血：只报**几何事实**，不做设计分类，不设门 ────────────
    #   「地」是一个方案空间（page-craft §一 L0 七种，可互相叠），不是三选一的分类题；
    #   配比也没有可用的全局数——参照库里有一份稿 19/19 页地是图，
    #   也有一份稿一半以上页面是纯平色地，两份都成立。所以这里只播报数，判断交给执行者。
    if len(grounds) >= 5:
        n = len(grounds)
        img_ground = sum(1 for k in grounds.values() if k in ("画面", "底纹"))
        flat = n - img_ground
        bleed = sum(1 for _pth, pg in looked if _page_bleeds(pg))
        inset_pages = [pth.name for pth, pg in looked
                       if _inset_images(pg) and not _page_bleeds(pg)]
        print(f"· [GND-001] 全稿 {n} 页：铺满整页的底图 {img_ground} 页 · 纯平色地 {flat} 页。"
              f"画面块切到页缘的 {bleed} 页（{bleed/n:.0%}）——"
              "参照库 11 份的这个数是 42%–100%、中位 72%。")
        if inset_pages:
            print(f"            其中 {len(inset_pages)} 页的图四边都留白"
                  f"（{', '.join(inset_pages[:4])}{'…' if len(inset_pages) > 4 else ''}）："
                  "参照库里 ≥12% 版面的画面块 94% 至少切到一条页缘，四边留白是 6% 的少数做法。")
        print("            地成不成套、配比合不合适，对着缩略图墙判"
              "（page-craft §一 L0 的方案库）。")
        _print_ground_composition(looked, deck_dir)

    # ── 影像复用账：只报事实，不设门 ────────────────────────────
    #   参照库的做法是**用少量图铺满图位**（一份稿 14 张唯一图铺 15 个图位）——
    #   复用率高本身是优点；要自己判的是「同一张有没有当两页的主视觉」。
    if len(looked) >= 5:
        slots: dict = {}
        for pth, pg in looked:
            for b in pg.images:
                if b.src:
                    slots.setdefault(b.src, []).append(
                        (pth.name, b.box[2] * b.box[3] / (CANVAS_W * CANVAS_H)))
            if pg.ground_token:
                slots.setdefault(pg.ground_token, []).append((pth.name, 1.0))
        n_slot = sum(len(v) for v in slots.values())
        if n_slot:
            # **一图多用只在全稿终验判**（逐页看不出来这张图在别处用过）。
            #   口径：同一张在 ≥2 页上都占 ≥25% 版面（作为地也算）；
            #   **排除通用底板**（在 ≥3 页上当地的那张）——那是设计做法。
            #   标定：参照库 11 份里 7 份共 10 处命中，多数是首尾呼应或连续几页共用一件材质带
            #   → **只报事实并问一句，不判缺陷**。
            gpages: dict = {}
            for pth, pg in looked:
                g = _ground_src(pg)
                if g:
                    gpages.setdefault(g, []).append(pth.name)
            names = [pth.name for pth, _pg in looked]
            page_by_name = {pth.name: pg for pth, pg in looked}
            ground_plate_facts = {s: _is_reusable_plate(s, ps, deck_dir)
                                  for s, ps in gpages.items() if len(ps) >= 3}
            ground_plates = {s for s, fact in ground_plate_facts.items() if fact[0]}
            for s, fact in ground_plate_facts.items():
                if fact[0] or fact[2] is None:
                    continue
                print(f"· [GND-003] 满版地 {s[:12]}… 的安静区只占 {fact[2]:.0%}，分诊角色是"
                      f"「{fact[1]}」，但它被铺在 {len(gpages[s])} 页：{', '.join(gpages[s])}。"
                      "它不是可跨页复用的纹理/氛围底板；下面 IMG-006 会按主体画面处理。")
            # 有些金标准用 `<img>` 而不是 slide fill 铺连续场景板：同一来源连续 ≥3 页、
            # 每页合计覆盖 ≥85%，本质仍是跨页地/场景板，不是三次独立主视觉。
            sequence_plates = set()
            for s, v in slots.items():
                if _load_asset(s, deck_dir) is not None:
                    continue                         # 真素材能打开时按角色判，不再按“连续用了三页”倒推豁免
                totals = collections.defaultdict(float)
                for pn, a in v:
                    totals[pn] += a
                ps = [n for n in names if totals.get(n, 0.0) >= 0.85]
                if len(ps) >= 3 and all(names.index(ps[j + 1]) - names.index(ps[j]) == 1
                                        for j in range(len(ps) - 1)):
                    sequence_plates.add(s)
            user_plates = set()
            user_reasons = {}
            for s, v in slots.items():
                used = sorted({pn for pn, _a in v}, key=names.index)
                reasons = [_reuse_user_reason(page_by_name[pn]) for pn in used]
                if len(used) >= 2 and all(reasons) and len(set(reasons)) == 1:
                    user_plates.add(s)
                    user_reasons[s] = reasons[0]
            plates = ground_plates | sequence_plates | user_plates

            # 默认合同：可打开的主体画面只能承担一页；纹理/氛围底板按角色豁免。
            # 用户明确要求复用时，每一处都要写同一个 `reuse=user:<原因>`，否则不算授权。
            # 素材打不开的离线参照库无法做角色分诊，按“最多两页”的离线口径并明确沉默。
            overused = []
            for s, v in slots.items():
                if s in plates:
                    continue
                totals = collections.defaultdict(float)
                for pn, a in v:
                    totals[pn] += a
                pages = [n for n in names if totals.get(n, 0.0) >= 0.25]
                measured = _load_asset(s, deck_dir) is not None
                if len(pages) > (1 if measured else 2):
                    overused.append((s, pages, measured))
            for s, pages, measured in overused:
                print(f"✗ [IMG-006] 内容图 {s[:12]}… 被用在 {len(pages)} 页：{', '.join(pages)}。"
                      + ("素材像素可打开，分诊不是纹理/氛围底板，所以主体画面默认只能承担一页。"
                         if measured else
                         "素材像素不可打开，本次只能按离线口径处理；即便如此也已超过两页。")
                      + "只有用户明确要求时，才可在每个使用页写同一个 `reuse=user:<用户要求>`；"
                      "如何换图或重分角色必须按本稿实际内容决定。")
            total_e += len(overused)

            # IMG-023 抓「逐页都成立、并排才看出重复」的那一种：相邻两页都只有这一张内容图，
            # 同源、同侧贴边、画幅仅小幅变化。多图系统、材质带、首尾呼应均不落入这个形状。
            adjacent_same = []
            for i in range(len(looked) - 1):
                (pa, ga), (pb, gb) = looked[i], looked[i + 1]
                sa = [(b.src, b.box) for b in ga.images if b.src and b.src not in plates]
                sb = [(b.src, b.box) for b in gb.images if b.src and b.src not in plates]
                if ga.ground_token and ga.ground_token not in plates:
                    sa.append((ga.ground_token, (0.0, 0.0, CANVAS_W, CANVAS_H)))
                if gb.ground_token and gb.ground_token not in plates:
                    sb.append((gb.ground_token, (0.0, 0.0, CANVAS_W, CANVAS_H)))
                if len(sa) != 1 or len(sb) != 1 or sa[0][0] != sb[0][0]:
                    continue
                src_, ba, bb = sa[0][0], sa[0][1], sb[0][1]
                ea = {k for k, hit in (("L", ba[0] <= 2), ("R", ba[0] + ba[2] >= CANVAS_W - 2),
                                       ("T", ba[1] <= 2), ("B", ba[1] + ba[3] >= CANVAS_H - 2)) if hit}
                eb = {k for k, hit in (("L", bb[0] <= 2), ("R", bb[0] + bb[2] >= CANVAS_W - 2),
                                       ("T", bb[1] <= 2), ("B", bb[1] + bb[3] >= CANVAS_H - 2)) if hit}
                area_a, area_b = ba[2] * ba[3], bb[2] * bb[3]
                near_frame = (min(area_a, area_b) / max(area_a, area_b, 1) >= 0.75
                              and abs(ba[2] / max(ba[3], 1) - bb[2] / max(bb[3], 1)) <= 0.18)
                if ea & eb and near_frame and min(area_a, area_b) >= 0.25 * CANVAS_W * CANVAS_H:
                    adjacent_same.append((src_, pa.name, pb.name, ba, bb))
            for src_, a, b, ba, bb in adjacent_same:
                print(f"✗ [IMG-023] {a} 与 {b} 相邻，且都只用内容图 {src_[:12]}…；"
                      f"两页都贴同一侧，图窗 {ba[2]:.0f}×{ba[3]:.0f} / {bb[2]:.0f}×{bb[3]:.0f} "
                      "仅小幅变化，读者会把它读成同一张主视觉重复。"
                      "这不是按次数打补丁：多图系统、同页材质带与跨页底板不在此门内；"
                      "可按实际内容换素材、换主体角色或真正改变构图。")
            total_e += len(adjacent_same)

            reused = []
            for s, v in slots.items():
                if s in plates:
                    continue
                best: dict = {}
                for pgname, a in v:
                    best[pgname] = max(best.get(pgname, 0.0), a)
                ps = sorted(pn for pn, a in best.items() if a >= 0.25)
                if len(ps) >= 2:
                    reused.append((s, ps))
            # **不含通用底板**（在 ≥3 页当地的那张）：一张纹理铺 13 页会把这个数顶上去，
            #   而那恰恰是"图很少"那一类稿的形状。这里量的是**内容图**。
            body = {sc: v for sc, v in slots.items() if sc not in plates}
            _bn = sum(len(v) for v in body.values())
            _avg = _bn / max(1, len(body))
            if not body:
                print("            （全稿一张内容图都没有，只有跨页复用的底板——"
                      "这一稿靠什么撑版面？信息图形与原生图表也成立，"
                      "但如果本来该有图而没进稿，先补图再写页。）")
            print(f"· [IMG-006] **内容图**（不含通用底板）每张平均出现 {_avg:.1f} 次"
                  f"（{_bn} 个图位 / {len(body)} 张）"
                  "——参照库 10 份（≥5 页的那些）**用同一段代码量出来**是 1.0–3.2、中位 1.4；"
                  "离线参照库的素材打不开，因此这组历史分布只用于报告，不会替代本项目的像素角色分诊。"
                  "本项目可打开的主体画面默认只承担一页；纹理/氛围底板与用户明确授权复用另计。")
            print(f"            全稿 {n_slot} 个图位 / {len(slots)} 张唯一图"
                  f"（复用率 {1 - len(slots)/n_slot:.0%}）。"
                  "复用率只是一笔事实账，不能单独证明优劣；角色是否变化由 IMG-023 与缩略图通读共同判断。")
            if plates:
                bits = []
                for s in sorted(plates)[:3]:
                    if s in user_plates:
                        bits.append(f"{s[:10]}… 用户授权：{user_reasons[s]}")
                    elif s in ground_plates:
                        bits.append(f"{s[:10]}… 当地铺 {len(gpages[s])} 页")
                    else:
                        bits.append(f"{s[:10]}… 离线连续场景板")
                print("            跨页底板/用户授权/离线连续场景板 " + "、".join(bits)
                      + "——它们按角色而不是文件次数识别，正常。")
            for s, ps in reused[:4]:
                first_last = names and ps[0] == names[0] and ps[-1] in names[-2:]
                adjacent = all(names.index(ps[i+1]) - names.index(ps[i]) == 1
                               for i in range(len(ps) - 1))
                hint = ("（首尾呼应）" if first_last else
                        "（连续页共用一件）" if adjacent else
                        "**←— 既不是首尾呼应也不是连续页，多半是同一张当了两次主视觉**")
                print(f"            ⚠ {s[:10]}… 在 {', '.join(ps)} 都占了 ≥25% 版面{hint}")
            if reused:
                print("            上面只列未豁免的重复事实；可打开的主体画面会由 IMG-006 直接阻断，"
                      "素材不可打开时必须在缩略图通读中人工核对。")

    # ── 用户点名要复用的素材：把 `reuse=` 声明的页连原因列出来，交付时逐条核对 ──
    if looked:
        declared = [(pth.name, _reuse_user_reason(pg)) for pth, pg in looked if _reuse_user_reason(pg)]
        if declared:
            print(f"· [IMG-007] 有 {len(declared)} 页写了 `reuse=user:`（用户点名要复用的素材）——交付时逐条核对："
                  + "；".join(f"{n} → {why}" for n, why in declared[:5])
                  + ("…" if len(declared) > 5 else ""))

    # ── 左右结构账：E-a 侧图窗 + E-b 满图空面覆盖，只报占比，不设门 ──
    if len(looked) >= 5:
        side_pages = []
        for pth, pg in looked:
            side_img = any(b.box[3] >= 0.90 * CANVAS_H and
                           0.25 <= b.box[2] / CANVAS_W <= 0.65 and
                           (b.box[0] <= 2 or b.box[0] + b.box[2] >= CANVAS_W - 2)
                           for b in pg.images)
            if side_img or _side_cover(pg):
                side_pages.append(pth.name)
        print(f"· [LAY-005] 一侧实色/承文面 ＋ 一侧图的结构有 {len(side_pages)}/{len(looked)} 页"
              f"（{len(side_pages)/len(looked):.0%}）。参照库逐份区间 0%–42%；"
              "这是坐标不是门，重点看它有没有跨章反复成为默认答案。"
              + (f"命中页：{', '.join(side_pages[:6])}{'…' if len(side_pages) > 6 else ''}。"
                 if side_pages else ""))

    # ── 版面账：块数与图位（问题「顶部空、内容挤在下面」的可证伪那一半）──
    #   注意：**低墨量不是缺陷**——参照库里最疏的一份全页墨只有 12%，那是它那一档的气质。
    #   真正量得出来的是**块数**：同样多的字被切成越多小框，越像"挤"。
    #   标定（用的就是下面这个计数口径，不是另一套算术）：
    #     参照库 11 份的**全稿块数中位** 9–27（中位 16）；**最多的那一页** 12–40（中位 26）。
    #   → 中位数区间很宽、判不出东西；**判据落在「最多的那一页」**。
    if len(looked) >= 5:
        counts = [(len([b for b in pg.blocks if b.box[2] * b.box[3] > 0]), pth.name)
                   for pth, pg in looked]
        nb = sorted(n for n, _nm in counts)
        med = nb[len(nb) // 2]
        worst = max(counts)
        nimg = sum(len(pg.images) + (1 if pg.ground_token else 0) for _pth, pg in looked)
        print(f"· [LAY-020] 全稿块数中位 {med}（最多的一页 {worst[0]} 块：{worst[1]}）· "
              f"图位 {nimg} 个 / {len(looked)} 页。"
              "参照库 11 份：全稿中位 9–27、最多的那一页 12–40。")
        if worst[0] > 40:
            print(f"            **{worst[1]} 那一页 {worst[0]} 块，比参照库最多的那一页（40）还多**——"
                  "同样多的字被切成更多小框，读者看到的是「挤」而不是「密」。"
                  "**先问这一页的内容能不能做成一件图形**"
                  "（数据卡／色卡／时间线／对比块／编号列／原生图表，`page-craft.md` §二 D13–D22），"
                  "而不是切成更多文字块。")

    # ── 字体角色账：同一个角色在全稿是不是同一款字 ────────────────
    #   标定：参照库正文最高频字体占比 中位 72%、p10 33% → **只报事实，不设门**
    #   （有几份参照稿的正文确实是混排的）。要的是「同一角色一款字」这个设计决定，
    #   它在 Step 2 由设计系统卡的角色表定，不由这里判。
    if len(looked) >= 5:
        import collections as _c
        role = _c.defaultdict(_c.Counter)
        for _pth, pg in looked:
            for m in re.finditer(r"<content([^>]*)>", pg.raw):
                at = m.group(1)
                fm = re.search(r'fontFamily="([^"]+)"', at)
                sm = re.search(r'fontSize="(\d+)"', at)
                if not (fm and sm):
                    continue
                pt = int(sm.group(1))
                r = "标题" if pt >= 28 else ("正文" if 13 <= pt <= 20 else ("小字" if pt <= 12 else "中间"))
                role[r][fm.group(1)] += 1
        bits = []
        for r in ("标题", "正文", "小字"):
            c = role.get(r)
            if not c:
                continue
            top, n = c.most_common(1)[0]
            bits.append(f"{r} {len(c)} 款（{top} 占 {n/sum(c.values()):.0%}）")
        if bits:
            print(f"· [FNT-002] 字体角色账：{' · '.join(bits)}。"
                  "参照库同一角色的最高频字体占比 中位：标题 100%、正文 72%、小字 86%。"
                  "**同一个角色在全稿只用同一款字**是设计语言的一部分——"
                  "角色表在设计系统卡上（标题/正文/微标签/数字），Step 2 定死、全程不改。")

    # ── 字体：用了会静默回落的名字（**只在全稿模式说一次**，不逐页重复）──
    if looked and len(looked) >= 2:
        used: set = set()
        for _pth, pg in looked:
            used |= _fonts_used(pg)
        if used:
            fell = sorted(f for f in used if f in _FONT_FALLBACK)
            if fell:
                print(f"· [FNT-001] 这几个字体名在宿主上会**静默回落**成默认字形"
                      f"（写了等于没写）：{', '.join(fell)}。"
                      "可用的名字见 `slides-xml.md` §三·B 宿主字体表，"
                      "或跑 `hostcheck` 让它在这台机器上现探一遍。")
            # ✗ 这里**不判**「全稿只用了一款字体」：参照库里有一份稿的身份就是**单字体品牌**，
            #   判它等于判死金标准。字体配对是设计决定，在 Step 2 由设计系统卡定，不在这里判。

    # ── 与参照库撞标题：参照稿的文案是占位性质的，标题是这一稿自己的判断 ──
    #   标定：参照库 11 份自排除后互撞 0 条，所以这条不会误伤成稿；
    #   ≥3 条＝整副骨架搬过来了（实测那一份连稿名与章节名一起搬），按 error 处理。
    if len(looked) >= 3:
        dup = _gold_title_hits([pg for _p, pg in looked])
        if dup:
            quoted = "、".join(f"「{t}」" for t in dup[:5])
            tail = "…" if len(dup) > 5 else ""
            head = "✗ [DUP-001]" if len(dup) >= 3 else "· [DUP-001]"
            print(f"{head} 有 {len(dup)} 条标题与参照库逐字相同：{quoted}{tail}")
            print("            参照稿的文案是**占位性质**的，它的稿名、章节名、页标题都不是内容——"
                  "**标题是这一稿自己的判断，借不来**（`_routing.md` 的看图口径：只看明暗带、"
                  "密度落差、图的画幅、家具层四件事）。逐条换成你这一稿自己的判断句。")
            if len(dup) >= 3:
                total_e += 1

    # 跨页同构：只给事实（哪两页骨架一样），是不是缺陷由执行者判
    if len(signatures) >= 3:
        same: dict[tuple, list[str]] = {}
        for name, sig in signatures:
            if len(sig) >= 3:
                same.setdefault(sig, []).append(name)
        runs = [v for v in same.values() if len(v) >= 3]
        if runs:
            worst = max(runs, key=len)
            print(f"· [DIV-001] 有 {len(worst)} 页共用同一套骨架（{', '.join(worst[:4])}"
                  f"{'…' if len(worst) > 4 else ''}）。"
                  "**同一章内共用骨架是杂志感的来源，跨章共用是「同一张脸」**——"
                  "看一眼这几页是不是同一章；跨章就挑几页换装置重排（page-craft §二）。")
        kinds = len({sig for _n, sig in signatures if len(sig) >= 3})
        if kinds and len(signatures) >= 8 and kinds <= max(3, len(signatures) // 4):
            print(f"· [DIV-002] 全稿 {len(signatures)} 页只有 {kinds} 种骨架——"
                  "翻页读起来会是一个模板。目标是每 4–6 页换一次气"
                  "（章节页／满版氛围页），连续两页至少两个维度不同。")

    delivery_mode = False
    delivery_covered = 0
    if args.deck:
        delivery_mode, delivery_covered, receipt_bad = _delivery_receipts(looked)
        if delivery_mode:
            print(f"· [RCPT-002] 逐页闭环覆盖 {delivery_covered}/{len(looked)} 页。")
            for msg in receipt_bad[:8]:
                print(f"✗ [RCPT-002] {msg}")
            if len(receipt_bad) > 8:
                print(f"✗ [RCPT-002] 另有 {len(receipt_bad)-8} 页未结清。")
            total_e += len(receipt_bad)
        else:
            print("· [RCPT-002] 本目录没有 readback/hostshots/逐页收据，按离线语料扫描处理；"
                  "可以做回归，但不会获得交付钥匙。")
    if total_e:
        print(f"CHECK: error_count={total_e} —— **必须改到 0 才写入**。"
              "每条都带实测数值与修法；改完重跑这条命令。")
        _print_repair_ladder()
        return 1
    if args.deck:
        if delivery_mode and delivery_covered == len(looked):
            ready = _write_delivery_ready(Path(args.deck), looked)
            print(f"DELIVERY-READY: {len(looked)} 页的本地 XML、宿主回读、真页截图与 LOOK 收据均可复算；"
                  "全稿合同/资产/跨页复用账 error_count=0。")
            print(f"交付首行必须逐字照抄 `.visual-check/DELIVERY-READY`：{ready}")
        else:
            print("CHECK: error_count=0（离线语料扫描通过），但没有 DELIVERY-READY；不得据此交付真实稿。")
        return 0
    looked_raw = getattr(args, "looked", None)
    wrote_raw = getattr(args, "wrote", None)
    if isinstance(looked_raw, str) and wrote_raw is None:
        print("BLOCK [WP-001]: LOOK 只认已经写入并回读的宿主真页。先按本次 check 打印的命令"
              "写入、回读、截宿主图，再带 `--wrote <回读XML>` 回来。")
        return 1
    if len(looked) == 1 and wrote_raw is None:
        path, _page_obj = looked[0]
        print("CHECK: error_count=0 —— 合同/几何/资产/图文关系的可证伪项已过；现在写入这一页。")
        for line in _write_cmds(path) + _after_write_cmds(path):
            print(f"     {line}")
        print("  必须保留写入返回的 slide_id；回读和宿主截图完成前，不进入 LOOK。")
        return 0
    if len(looked) == 1 and wrote_raw is not None:
        wrote_error = _wrote_check(looked[0][1], wrote_raw)
        if wrote_error:
            print(f"BLOCK [WP-001]: {wrote_error}")
            return 1
        print("· [WP-001] 宿主单页回读与本地骨架一致；下面的 LOOK 必须对着宿主真页截图回答。")
    items = []
    if len(looked) == 1:
        path, page_obj = looked[0]
        items = _look_items(page_obj, path, deck_dir or path.parent)
    answers = _parse_looked(looked_raw) if isinstance(looked_raw, str) else {}
    codes = [c.split("-")[-1] for c, _x, _d in items]
    disputed = {c.split("-")[-1] for c, _x, d in items if d}

    # ── `--looked` 带了答案：核对之后决定给不给写入命令 ──────────
    if isinstance(looked_raw, str) and looked_raw.strip():
        # ① 时间戳只能提示，不能当真值：跨机器复制、宿主下载都会改 mtime。
        #    把它做成硬门会让执行者为绕门直接砍掉 LOOK，因此保留显眼警告但继续验答案。
        stale = _shot_staleness(path, host_only=True)
        if stale is not None:
            print(f"⚠ [SHOT-001] {stale}")
            print("  时间戳不是内容证据，本次不因此打回；仍应确认 Read 的是当前 slide_id 的宿主真页。")
        # ② 答案集合要与**这一页的问句集合完全一致**：少答打回，**多答也打回**。
        #    多答＝这串答案不是为这一页写的（标定：一串常量答案被写进 shell 循环套在 3–6 页上）。
        missing = [c for c in codes if c not in answers]
        extra = [c for c in answers if c not in codes]
        if missing or extra:
            if missing:
                print(f"LOOKED: 还有 {len(missing)} 问没答（{', '.join('LOOK-' + c for c in missing)}）。"
                      "每问一句：`ok` / `fix:<一句>`；**LOOK-02 与带 ⚠ 的问都要写 `ok@<观察>`**。")
            if extra:
                print(f"LOOKED: 答案里有 {len(extra)} 个**这一页没问的码**"
                      f"（{', '.join('LOOK-' + c for c in sorted(extra))}）——"
                      "这串答案不是为这一页写的。**每一页的问句集合不一样，答案不能复用**。")
            for code, text, d in items:
                if code.split("-")[-1] in missing:
                    print(f"  {'⚠' if d else '·'} [{code}] {text}")
            return 1
        # ③ LOOK-02 必须逐图、逐边界结账；自由文本不能再把半脸翻成「艺术化裁切」。
        if "02" in codes and answers["02"][0] == "ok":
            n_img = len(page_obj.images) + (1 if page_obj.ground_token else 0)
            face_texts = [t.text[:12] for t in getattr(page_obj, "face_overlap_candidates", []) if t.text]
            identity_error = _identity_answer_error(answers["02"][1], n_img, face_texts)
            if identity_error:
                print(f"LOOKED: LOOK-02 {identity_error}。")
                print("        人物按 `图1=主体名|头顶=内|额头=内|下巴=内|左脸界=内|右脸界=内`；"
                      "纯场景写 `图1=纯场景`，产品写 `图1=产品名|轮廓=内`。任一边界不完整就答 fix；"
                      "出现压脸候选时还要把本页候选文字逐块点回。")
                return 1
        if "24" in codes and answers["24"][0] == "ok":
            source_error = _source_quality_answer_error(answers["24"][1])
            if source_error:
                print(f"LOOKED: LOOK-24 {source_error}。")
                print("        合格答案按 `源图=单一完整画面|边缘=完整|资料字=无`；"
                      "发现拼接、截断、占位块或图内资料文字时应答 fix。")
                return 1
        # ④ LOOK-05 要把这一页最小的那几行字**照抄回来**——它逐页天生不同，
        #    一串常量答案在这里必然对不上（标定：64 页对应 64 种小字集合）。
        if "05" in codes and _small_texts(page_obj) and answers["05"][0] == "ok":
            if not _quotes_small_text(answers["05"][1], page_obj):
                print("LOOKED: LOOK-05 要把这一页最小的那几行字**照抄回来**，只答 `ok` 不算。")
                print("        写成 `05:ok@<照抄的那一句>`——照抄是为了证明这次回答是对着这一页给的。")
                return 1
        # ⑤ 机器有异议的 `ok` 必须引用本页文字或几何；复述规则名不能翻转读数。
        bare = [c for c in codes
                if c in disputed and answers[c][0] == "ok"
                and c != "24"
                and not _quotes_page_evidence(answers[c][1], page_obj)]
        if bare:
            print(f"LOOKED: 有 {len(bare)} 问机器给出了不利读数，"
                  f"理由没有引用本页证据（{', '.join('LOOK-' + c for c in bare)}）。")
            print("  只写规则名、档位或『符合规范』不算。答 `ok@…` 时必须照抄本页真实文字，"
                  "或写出本页实际位置/坐标/尺寸与画面关系；也可以答 `fix:<一句>`。")
            for code, text, d in items:
                if code.split("-")[-1] in bare:
                    print(f"  ⚠ [{code}] {text}")
            return 1
        if "21" in codes and answers.get("21", ("", ""))[0] == "ok":
            busy = [t for t, _v in getattr(page_obj, "busy_texts", [])]
            if busy and not _quotes_page_text(answers["21"][1], page_obj, busy):
                print("LOOKED: LOOK-21 必须照抄它点名的那叠页面文字，再说明文字与主体/承字区的关系；"
                      "引用别处小字或规则名不能证明看过这一处。")
                return 1
        # ⑥ 有 fix 就是这一页还没做完
        bad = [(c, answers[c][1]) for c in codes if answers[c][0] == "fix"]
        if bad:
            print(f"LOOKED: 这一页还没改完——{len(bad)} 问答了 `fix`：")
            for c, why in bad:
                print(f"  ✗ LOOK-{c} {why or '（没写原因）'}")
            _print_repair_ladder()
            print("  可按本页实际情况重排或重做；这些方向只是建议。改完先用 `+replace-slide` 写回同一页，"
                  "再回读、重截宿主图、重跑 `check --wrote` 与 LOOK，直到没有 `fix`。")
            return 1
        n_d = len(disputed)
        receipt = _write_look_receipt(path, wrote_raw, codes, answers)
        print(f"LOOKED: {len(codes)} 问逐条答完，没有 `fix`"
              + (f"（其中 {n_d} 问以本页证据翻转机器读数）" if n_d else "")
              + "。这一页已完成写入、回读、宿主截图与逐页结账；继续下一页。")
        if receipt:
            print(f"· [RCPT-001] 已记录逐页收据 `{receipt}`；XML、回读或截图变化后必须重结账。")
        else:
            print("⚠ [RCPT-001] 逐页收据写入失败；这一页不能计入最终交付覆盖率。")
        return 0

    print(f"CHECK: error_count=0 · look_items={len(items)} —— 机械缺陷没有了，"
          "**但机械缺陷不是缺陷的全部**。")
    if not items:
        print("  这一页好不好看要对着截图判：构图、节奏、图文关系、家具层一致性，"
              "逐页按 page-craft §七红线过一遍。")
        return 0
    # ── `--looked` 不带值：只把这一页的几问重印一遍（看完图记不清时一步拉回） ──
    if isinstance(looked_raw, str):
        print("  这一页要逐条回答的几问（**⚠ 是机器已经算出不利读数的，那几条的 `ok` 要带理由**）：")
        for code, text, d in items:
            print(f"  {'⚠' if d else '·'} [{code}] {text}")
        print(f"  答完带回来：`... check --slide {path} --looked "
              f"'{' '.join(c + (':ok@<逐图观察>' if c == '02' else (':ok@<理由>' if c in disputed else ':ok')) for c in codes[:3])} …'`")
        return 0
    print("  Read `hostshots/` 下这页由 presentation + slide-id 截出的宿主真图，"
          "对着下面问句逐条回答；写入前本地预览不能替代这一步：")
    for code, text, d in items:
        print(f"  {'⚠' if d else '·'} [{code}] {text}")
    if disputed:
        print(f"  ⚠ 上面有 {len(disputed)} 问**机器已经算出不利读数**"
              f"（{', '.join('LOOK-' + c for c in sorted(disputed))}）——"
              "这几条只答 `ok` 不算回答：要么 `fix:<一句>` 去改，"
              "要么 `ok@<一句为什么它其实不是缺陷>`。")
    _print_repair_ladder()
    print("  ⚠ **看完把结论逐条带回来**：")
    print(f"     python3 \"$SKILL_ROOT/scripts/deck.py\" check --slide {path} \\")
    print(f"       --wrote {wrote_raw} --looked '{' '.join(c + (':ok@<逐图观察>' if c == '02' else ':ok') for c in codes)}'")
    print("     每问一句：`ok` 或 `fix:<一句>`；**标 ⚠ 的那几问只答 `ok` 不算回答**——"
          "要么 `fix` 去改，要么 `ok@<一句为什么它其实不是缺陷>`。"
          "`LOOK-02` 必须逐图点名主体与头脸边界并按需核对压脸；"
          "`LOOK-24` 按源图/边缘/资料字结账；`LOOK-05` 出现时要把小字照抄回来。"
          "记不清清单就跑一次不带值的 `--looked`。")
    print("  若任一问是 `fix`，用 `+replace-slide` 写回原 slide_id，回读与宿主截图后再结账。")
    return 0


def _print_texture_verdict(path: Path, im) -> int:
    """这张图能不能当**跨页底纹**——它要复用到很多页上，一张不合格会把整稿拖下去。

    只报事实与结论，不给可抄的参数：不合格时的正解永远是**按新口径重新生成这一张**，
    不是把字挤进它剩下的那一小块安静区（那是做不到的，做不到的处方会连诊断一起被丢掉）。
    """
    ok, share, local, seams = _texture_verdict(im)
    ow, oh = im.size
    print(f"TEXTURE {path.name}  源图 {ow}×{oh}")
    if ok:
        print(f"  ✓ **合格**：安静区占版 {share:.0%} · 局部明度极差中位 {local:.0f} · 中区无贯穿缝。")
        print("    可以跨页复用——字落在它上面的任何位置都读得清。")
        if PIXEL_SOURCE == "stdlib":
            print("    ⚠ 本机走的是包内标准库解码器（1/8 精度）：**极细密的图案可能量不出来**。"
                  "第一页用上它之后，截图上再看一眼最小的那几行字（页码、眉标、图注）读不读得清。")
        return 0
    print("  ✗ **不合格，不要拿它当跨页底纹**")
    if share < TEXTURE_QUIET_MIN:
        print(f"    · 安静区只占 {share:.0%}（合格线 ≥{TEXTURE_QUIET_MIN:.0%}，真稿的底纹是 93–100%）"
              f"——纹理太重，局部明度极差中位 {local:.0f}（真稿的底纹是 4–10）。"
              "字压上去会被图案干扰。")
    if seams:
        where = "、".join(f"{d}向 {v}" for d, v in seams[:4])
        print(f"    · 中区有 {len(seams)} 条贯穿画幅的缝（{where}）——它们会把版面框死，"
              "上下左右怎么排都被切开。（**贴页缘的边框不算**，那不切版面。）")
    print("    正解是**把同一个方案压浅一档重新生成这一张**（image-direction §八·2）——"
          "不是换一种图案，也不是把字挤进它剩下的那一小块安静区。")
    print("      **图案本身不禁**（点阵、格纹、笔触、纤维都成立），禁的是「重」："
          "同一个图案，配色浅一档就从不合格变合格。")
    print("      中间不许有缝（`no seam, no fold, no split, no colour break across the middle`），"
          "四周的细边框、压边、暗角**是允许的**。")
    print("    ✗ 不合格的纹理地不许用在任何一页上。")
    if share >= AMBIENT_QUIET_MIN:
        print(f"    ⟂ **另一条岔路**：这张图的安静区 {share:.0%} 落在 **氛围底图** 那一支的区间里"
              f"（{AMBIENT_QUIET_MIN:.0%}–{TEXTURE_QUIET_MIN:.0%}）。"
              "如果你要的本来就是「有光位、有纵深、没有主体」的**氛围底图**而不是纹理，"
              "**不要按上面那条改**——去掉 `--as-texture` 重跑，那一支的合格线不一样，"
              "它同样可以跨页复用一张铺 6–10 页（image-direction §八·1）。")
    return 1


def cmd_ground(args) -> int:
    path = Path(args.image)
    if not path.is_file():
        print(f"BLOCK: 找不到图片 {path}")
        return 2
    if not HAS_PIL:
        if getattr(args, "as_texture", False):
            # **量不到 ≠ 合格。** 退出码 0 会被读成「这张底纹通过了」，所以这一档必须非零。
            print(f"TEXTURE {path.name}  → **没验过**（这台机器的像素测量不可用）")
            for line in PIXEL_HINTS:
                print("  " + line.lstrip())
            print("  在验得了之前，这张底纹只能靠截图判：第一页用上它之后，"
                  "看最小的那几行字（页码、眉标、图注）读不读得清，"
                  "以及中间有没有一条把版面切开的缝（四周的边框不算）。")
            return 2
        print("GROUND: 这台机器的像素测量不可用，量不了安静区。")
        for line in PIXEL_HINTS:
            print("  " + line.lstrip())
        print("  装不上时的出路：先把图放进页面、截图出来，用肉眼挑一片干净区域再排字；")
        print("  或者按 image-direction §八·1 的 ①b 下单——让生图直接画出承文面，坐标由订单给死。")
        return 0
    im = Image.open(path).convert("RGB")
    ow, oh = im.size
    if getattr(args, "as_texture", False):
        return _print_texture_verdict(path, im)
    report = _ground_report(im)
    zone = report["zone"]
    print(f"GROUND {path.name}  源图 {ow}×{oh}（比例 {ow/oh:.2f}）")
    if zone:
        bx, by, bw, bh = zone
        print(f"  安静区（可直接写进 topLeft/width/height）：x{bx:.0f} y{by:.0f} w{bw:.0f} h{bh:.0f}"
              f"，占版 {bw*bh/(CANVAS_W*CANVAS_H):.0%}")
        print(f"  内收 24px 后的文字列：x{bx+24:.0f} y{by+24:.0f} "
              f"w{max(40, bw-48):.0f} h{max(24, bh-48):.0f}")
        print("  → 整叠文字落进它，**图一个像素都不动**：不加渐变、不加罩、不加托片。")
    else:
        print("  这张图没有像样的安静区（≥60×40 的连续低信息块都找不到）。")
        print("  → 按 page-craft §四承文阶梯：**重新生成这一页的底图**，"
              "prompt 里写明「给文字留一片低细节区/暗部」；重做优先于叠东西。")
    # 结构线：贯穿画幅的明度阶跃
    lines = report["lines"]
    if lines:
        print("  ⚠ 结构线（折痕/门框/柱/拼接缝）：" +
              "、".join(f"{d}向 {v}" for d, v in lines[:4]) +
              " —— 横排文字骑上去会被劈成两半，整叠字落在线的一侧、两边各留 ≥24px。")
    # 主体区：最忙的连续块（与 `check` 的 GRD-001 共用同一份实现）
    subj = report["subject"]
    if subj:
        print(f"  主体区（画面最忙的一片）：x{subj[0]} y{subj[1]} "
              f"w{subj[2]} h{subj[3]} —— 文字、板、图都不要压它。")
    _print_ground_use(im, subj)
    return 0


def _print_ground_use(im, subj) -> None:
    """这张图**适合当哪一种地**——用的就是纹理那一支已经算过的安静区占比，只是多说一句。

    七种地里能"一张铺满全稿"的不止纹理一种：一张无主体、有光位有纵深的**氛围底图**
    同样可以铺 6–10 页，而且它比纹理更能定这一稿的气质。这里只报事实与它落在哪一档，
    怎么下单见 `image-direction.md` §八·1。
    """
    _ok, share, _local, _seams = _texture_verdict(im)
    print(f"  这张图适合怎么用（安静区占版 {share:.0%}）：")
    if share >= TEXTURE_QUIET_MIN:
        print("    → **纹理地**：字落在它上面的任何位置都读得清，可以跨页复用一张撑起全稿。"
              "但它只提供质感，**这一稿的气质得由别的东西给**——"
              "全稿最高频的那张地就是这一稿的脸，先想清楚读者该记住的是不是一层纹理。")
    elif share >= AMBIENT_QUIET_MIN:
        print(f"    → **氛围底图**：安静区 {share:.0%} 达不到纹理线（{TEXTURE_QUIET_MIN:.0%}），"
              "但还剩成片的低信息区——**这一档同样可以跨页复用一张铺 6–10 页**，"
              "而且比纹理更能定气质。字落进上面印出的安静区；"
              "✗ 不要跑 `--as-texture`：那不是它的门。")
        if subj:
            print("      ⚠ 它有一片明显的主体区——跨页复现另一种画幅时要**按新比例重生/重检索**，"
                  "同一张同画幅铺很多页会被读成「这稿没图了」。")
    else:
        print(f"    → **只当单页画面**：安静区只有 {share:.0%}，撑不起跨页复用。"
              "字按 `page-craft.md` §四 承文阶梯往下走；"
              "**同题材可在别页换画幅再出现**（满版／半版／窄条／缩略），但要按新比例重生/重检索。")



#: 渲染层（宿主自带的 Slides 技能包）在不同机器上落在不同目录。
#: **按能力找，不按名字找**：任何 `*slide*` 技能包里的 `references/xml/` 都算。
#: 顺序是「显式指定 → 环境变量 → 常见根 → 本包同级 → 当前工作区」，每一档都只扫有限深度。
_SKILL_ROOTS = (
    ".agents/skills", ".codex/skills", ".doubao/skills",
    ".doubao/agent_mode/workspace/.skills",
)
_SKILL_ROOT_GLOBS = (
    "Library/Application Support/*/*/.doubao/agent_mode/workspace/.skills",
    "AppData/Roaming/*/*/.doubao/agent_mode/workspace/.skills",
    "AppData/Local/*/*/.doubao/agent_mode/workspace/.skills",
    ".config/*/*/.doubao/agent_mode/workspace/.skills",
)


def _package_siblings() -> list[Path]:
    """本包装在技能根里时，渲染层就是它的同级目录。"""
    out: list[Path] = []
    try:
        here = Path(__file__).resolve()
    except OSError:
        return out
    for up in (2, 3):
        try:
            cand = here.parents[up]
        except IndexError:
            continue
        if cand not in out:
            out.append(cand)
    return out


def _renderer_docs(explicit: str = "") -> list[str]:
    """找渲染层自带的语法文档，返回可直接粘贴的 Read 行。"""
    bases: list[Path] = []
    if explicit:
        bases.append(Path(explicit))
    env = os.environ.get("DOUBAO_SKILLS_ROOT", "")
    if env:
        bases += [Path(x) for x in env.split(os.pathsep) if x]
    try:
        home = Path.home()
    except RuntimeError:
        home = None
    if home is not None:
        bases += [home / rel for rel in _SKILL_ROOTS]
        for pattern in _SKILL_ROOT_GLOBS:
            bases += list(home.glob(pattern))
    bases += _package_siblings()
    bases.append(Path.cwd() / ".skills")
    found: list[Path] = []
    seen: set[str] = set()
    for base in bases:
        try:
            if not base.is_dir():
                continue
        except OSError:
            continue
        for pat in ("*slide*/references/xml/*.md", "*slide*/references/xml/*.xml",
                    "*ppt*/references/xml/*.md", "*slide*/SKILL.md"):
            try:
                for hit in base.glob(pat):
                    key = hit.name
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append(hit)
            except OSError:
                continue
        if found:
            break
    if not found:
        return ["  （这台机器上没找到渲染层自带的语法文档：按本包 references/slides-xml.md 写，"
                "写完务必回读核对。若你知道它在哪，用 --skills-root <目录> 再跑一次。）"]
    out = ["  语法真值以这几份为准（本包 slides-xml.md 是补充）："]
    for hit in sorted(found)[:6]:
        out.append(f"  · Read \"{hit}\"")
    return out


def _which(*names):
    for n in names:
        if shutil.which(n):
            return n
    return ""


def _print_leftovers() -> None:
    """当前目录里有没有上一次留下的半成品。

    会话在半路断掉时（宿主超时、用户重开），素材、token 对照表、已写入的页都还在。
    **重新建稿等于把它们全扔掉**——所以开工前先把这件事摆到眼前。
    """
    here = Path.cwd()
    bits = []
    for base in (here, here / "assets"):
        tk = base / TOKEN_MAP
        if tk.is_file():
            try:
                n = len([1 for ln in tk.read_text(encoding="utf-8", errors="replace").splitlines()
                         if ln.strip() and not ln.startswith("#")])
            except OSError:
                n = 0
            bits.append(f"`{tk.relative_to(here) if tk.is_relative_to(here) else tk}` 里有 {n} 张图的 token")
            break
    for base in (here, here / "slides"):
        pages = sorted([q for pat in ("slide-*.xml", "p*.xml") for q in base.glob(pat)]) \
            if base.is_dir() else []
        if pages:
            bits.append(f"`{base.name if base != here else '.'}/` 下有 {len(pages)} 页本地 XML")
            break
    if not bits:
        return
    print("【这个目录里已经有半成品】")
    for b in bits:
        print("  · " + b)
    print("  多半是会话在半路断过。**先回读宿主确认已经落了几页，从下一页接着做**——")
    print("  ✗ 不要重新建稿、不要重新生图：素材与 token 都还在，重来一遍等于把它们全扔掉。")
    print()


#: 探测用的候选字体，按用途分组；探不到时这张表就是 slides-xml.md §三·B 的默认表。
_FONT_PROBE = [
    ("中文 · 黑体", "思源黑体"), ("中文 · 宋体", "思源宋体"),
    ("中文 · 细书宋", "寒蝉锦书宋"), ("中文 · 毛笔行楷", "有字库龙藏体"),
    ("中文 · 圆体", "圆体"), ("中文 · 厚圆黄油体", "站酷庆科黄油体"),
    ("中文 · 粗圆黑", "抖音美好体"), ("中文 · 粗圆手写感", "站酷快乐体"),
    ("拉丁 · 窄体巨字", "Bebas Neue"), ("拉丁 · 重型 display", "Anton"),
    ("拉丁 · 窄体", "Oswald"), ("拉丁 · 几何无衬线", "Montserrat"),
    ("拉丁 · 人文无衬线", "Inter"), ("拉丁 · 高对比衬线", "Playfair Display"),
    ("拉丁 · 老式衬线", "EB Garamond"), ("拉丁 · 圆润", "Comfortaa"),
    ("拉丁 · 等宽", "Roboto Mono"),
]
_FONT_PROBE_CTRL = "__NO_SUCH_FONT_PROBE__"
#: 一页放得下几行：8px 起排、行距 38px、画布 540px 高 → 最多 13 行还留得住底边。
_PROBE_ROWS = 13


def _font_probe_xml(names) -> str:
    """一页 N 行，每行一款字、同字号同几何——行位相同才比得出字形差异。

    样张里**中文与拉丁都要够长**：只放三五个拉丁字母时，拉丁 display 的差异摊到整行的
    平均像素差里会低于阈值，真实存在的字体会被误报成「回落」。
    """
    rows = []
    for i, fam in enumerate(names):
        y = 8 + i * 38
        rows.append(f'<shape type="text" topLeftX="16" topLeftY="{y}" width="928" height="34">'
                    f'<content fontSize="26" fontFamily="{fam}" color="rgba(0,0,0,1)" '
                    f'autoFit="normal-auto-fit"><p>国字样张 Handgloves ABC 2026</p></content></shape>')
    return ('<slide xmlns="https://www.larkoffice.com/sml/2.0">'
            '<style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style>'
            '<data>' + "".join(rows) + '</data></slide>')


def _probe_fonts(cli: str):
    """在这台机器上现探一遍：渲染候选页与对照页，逐行比像素。

    对照组写一个**不存在的字体名**——与它逐像素相同就是静默回落（写了等于没写）。
    渲染或像素能力缺一样就返回 None，调用方回落到包内默认表。
    """
    if not cli or not HAS_PIL:
        return None
    tmp = None
    try:
        # **截图命令的 --output-dir 必须落在当前工作目录里**（宿主的硬约束：
        # 指到 cwd 之外会被判 invalid_argument）。所以探测目录建在 cwd 下，跑完就删。
        tmp = Path(tempfile.mkdtemp(prefix=".fontprobe-", dir="."))
        out = []
        # **一页最多放 _PROBE_ROWS 行**：行距 38px、画布只有 540px 高，
        # 排到画布外面的行截图上根本不存在，两张图都是空白 → 会被误报成「静默回落」。
        # （多加三款字就足以把最后三行挤出画布——真实存在的字体因此被判死。）
        for start in range(0, len(_FONT_PROBE), _PROBE_ROWS):
            chunk = _FONT_PROBE[start:start + _PROBE_ROWS]
            names = [f for _u, f in chunk]
            shots = []
            for tag, xs in ((f"c{start}", names), (f"k{start}", [_FONT_PROBE_CTRL] * len(names))):
                xml = tmp / f"{tag}.xml"
                xml.write_text(_font_probe_xml(xs), encoding="utf-8")
                r = subprocess.run([cli, "slides", "+screenshot", "--content", f"@{xml}",
                                    "--output-dir", str(tmp), "--output-name", tag],
                                   capture_output=True, text=True, timeout=90)
                png = tmp / f"{tag}.png"
                if r.returncode != 0 or not png.is_file():
                    return None
                shots.append(Image.open(png).convert("L"))
            cand, ctrl = shots
            if cand.size != ctrl.size:
                return None
            w, h = cand.size
            sc = h / CANVAS_H
            for i, (use, fam) in enumerate(chunk):
                y0, y1 = int((8 + i * 38) * sc), int((8 + i * 38 + 34) * sc)
                a = cand.crop((int(14 * sc), y0, int(946 * sc), y1))
                b = ctrl.crop((int(14 * sc), y0, int(946 * sc), y1))
                diff = sum(abs(x - y) for x, y in zip(a.getdata(), b.getdata())) / max(1, w * (y1 - y0))
                out.append((use, fam, diff >= 0.6))
        return out
    except Exception:                                   # noqa: BLE001
        return None
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


def cmd_hostcheck(args) -> int:
    root = Path(__file__).resolve().parent.parent
    print(f"HOSTCHECK · SKILL_ROOT = {root}")
    print()
    cli = _which("lark-cli")
    if getattr(args, "carrier", "slides") == "document":
        print("【文档载体】这一路交付的是**文档**，不是幻灯片。")
        if cli:
            print(f"  ✓ 走 `{cli} docs`：")
            print(f"     建文档   {cli} docs +create --title \"<标题>\" --file <正文文件>")
            print(f"     追加内容 {cli} docs +update --command append --document <id> --file <片段>")
            print(f"     回读全文 {cli} docs +fetch --document <id> --output readback.md")
            print("     具体参数以 `--help` 为准。")
        else:
            print("  ✗ 没找到 `lark-cli`：文档线没有写入通路。")
        print("  ⚠ **不许用本地 .docx 冒充交付**：交付必须是可访问的文档链接，")
        print("     拿不到通路时把内容与素材整理成交付包并在交付语里说清。")
        print("  版面工艺仍按 references/page-craft.md：文档是**画册**不是报告——")
        print("     封面满幅图开场、每章满幅 hero 起章、图文穿插、满宽表格。")
        return 0
    _print_leftovers()
    print("【写入通路】")
    if cli:
        print(f"  ✓ 找到 `{cli}`——Slides 走它的 slides 子命令。")
        try:
            out = subprocess.run([cli, "slides", "--help"], capture_output=True,
                                 text=True, timeout=20).stdout
        except Exception:                              # noqa: BLE001
            out = ""
        verbs = sorted(set(re.findall(r"^\s{2}(\+[a-z-]+)", out, re.M)))
        if verbs:
            print(f"    可用快捷命令：{' '.join(verbs)}")
        print()
        print("【可直接粘贴的命令】")
        print("  ① 建空稿（记下 xml_presentation_id 与 url）")
        print(f"     {cli} slides +create --title \"<标题>\"")
        print("  ② 上传图片拿 file_token —— **同时把对照表写下来**（每张图一次）")
        print(f"     tok=$({cli} slides +media-upload --file assets/<图>.jpg \\")
        print("            --presentation <id> --jq '.data.file_token') \\")
        print(f"       && printf '%s\\t%s\\n' \"$tok\" \"<图>.jpg\" >> assets/{TOKEN_MAP}")
        print(f"     `assets/{TOKEN_MAP}` 是**像素判据的开关**：页面 XML 里的 src 必须是 token，")
        print("     没有这张表时 `check` 找不到底图——安静区、大罩、叠图整族会静默失效。")
        print("  ③ 每页先跑唯一机械门；0 error 后它会打印一条复合命令")
        print("     python3 \"$SKILL_ROOT/scripts/deck.py\" check --slide slides/slide-01.xml")
        print("     复合命令一次完成：写入 → 保存 slide_id → 回读 → 宿主截图 → `--wrote` 对账并打印 LOOK。")
        print("  ④ Read 宿主真页，再把回读与 LOOK 合并成一次结账")
        print("     python3 \"$SKILL_ROOT/scripts/deck.py\" check --slide slides/slide-01.xml \\")
        print("       --wrote readback/slide-01.xml --looked \\")
        print("       '01:ok 02:ok@图1=<主体>|头顶=内|额头=内|下巴=内|左脸界=内|右脸界=内 09:ok …'")
        print("     全答完会写 `.visual-check/slide-01.json`；一页一条，✗ 不要套 shell 循环。")
        print("  ⑤ 全稿终验时回读全文")
        print(f"     {cli} slides +xml-get --presentation <id> --output readback.xml")
        print("     python3 \"$SKILL_ROOT/scripts/deck.py\" check --deck . --contract contract.txt")
        print("     只有逐页收据全覆盖且跨页账为 0，才会写 `.visual-check/DELIVERY-READY`。")
        print("  ⑥ LOOK 有 fix 时局部替换 / 整页重做，再走 ③→⑤")
        print(f"     {cli} slides +replace-slide --presentation <id> --slide-id <sid> …")
        print(f"     {cli} slides +replace-pages --presentation <id> …")
        print()
        print("  ⚠ 每条命令的完整参数以 `--help` 为准；写入前先看 `lark-cli schema slides.<res>.<method>`。")
        print("  ⚠ 上传命令**先打印一行进度再打印 JSON**：直接 `json.load` 会炸——")
        print("     用上面 ② 的 `--jq`，或先剥掉 JSON 之前的行（`… | sed -n '/^{/,$p'`）。")
        print("  ⚠ `--output-dir` 必须是**当前目录下**的相对路径，写 `../` 会被拒。")
    else:
        print("  ✗ 没找到 `lark-cli`。")
        print("    出路：① 这台机器如果有别的 Slides 写入工具（宿主原生工具），改用它，")
        print("    但**必须是能提交完整 XML 几何的那种**——只吃一段文字描述的写入工具会丢掉全部版式；")
        print("    ② 都没有时，把逐页 XML 与素材整理成交付包给用户，并在交付语里说清没有写入通路。")

    print()
    print("【渲染层自带的语法文档】——语法真值以它为准，本包的 slides-xml.md 是补充")
    print("  " + "、".join(f"{p}" for p in []) if False else "", end="")
    for line in _renderer_docs(getattr(args, "skills_root", "")):
        print(line)

    print()
    print("【像素测量能力】")
    if PIXEL_SOURCE == "pillow":
        print("  ✓ 走 Pillow：`ground` 能量安静区，`check` 能判「字落在画面的哪一块上」、"
              "大罩、叠图。")
    elif PIXEL_SOURCE == "stdlib":
        print("  ✓ 走**包内标准库解码器**（这台机器没有可用的 Pillow）：安静区、忙碌度、")
        print("    主体区都量得到，精度 1/8（判据用的网格比它粗，够用）。")
        print("    ✗ 但**改图**的动作（抠底 floodfill、拼缩略图墙）仍然需要真 Pillow：")
        for line in PIXEL_HINTS:
            if "装不上也不阻塞" in line:
                continue                               # 这一档已经在走兜底，不必再说一遍
            print("    " + line.lstrip())
    else:
        print("  ✗ 像素测量不可用：`ground` 量不了安静区，`check` 的像素类判据整族跳过。")
        print("    **量不到 ≠ 合格**——先把它装上，这一步只要十几秒：")
        fallback = [f'    "{sys.executable}" -m pip install --user '
                    "--force-reinstall --no-cache-dir pillow",
                    "    （命令里写死的是**正在跑本脚本的解释器**，装到 PATH 上另一个 "
                    "python3 等于没装；若报 externally-managed-environment 就再加 "
                    "--break-system-packages）"]
        for line in PIXEL_HINTS or fallback:
            print("    " + line.lstrip())
        if PIXEL_GAPS:
            print("    （包内兜底解码器自检有缺口：" + "；".join(PIXEL_GAPS[:3]) + "）")
        print("    装不上就只能靠截图肉眼判——那时每一页都必须亲自看，不许跳过。")

    print()
    print("【字体】——写一个宿主没有的名字**不会报错，会静默回落**，在 XML 里看不出来")
    probe = _probe_fonts(_which("lark-cli"))
    if probe is None:
        print("  这台机器上探不到（渲染或像素能力缺一样）：按包内默认表用，"
              "完整三栏见 `references/slides-xml.md` §三·B。")
        for use, fam in _FONT_PROBE:
            print(f"    {use:<18} {fam}")
    else:
        ok = [(u, f) for u, f, good in probe if good]
        no = [f for _u, f, good in probe if not good]
        print(f"  实探 {len(probe)} 款，这台机器上真的有 {len(ok)} 款：")
        for use, fam in ok:
            print(f"    {use:<18} {fam}")
        if no:
            print(f"  ✗ 会静默回落（写了等于没写）：{', '.join(no)}")
        print("  完整名单（含 40 多款拉丁与会回落的名字）见 `references/slides-xml.md` §三·B。")
    print("  **中文 8 种真字形 × 拉丁 40 多种**——两边都够用，一稿最多两款中文 ＋ 一款拉丁。")
    print("  **角色分工**（标题／正文／拉丁微标签／数字各一款）由设计系统卡上的**字体角色表**定，选定后全程不改。")
    print()
    print("【下一步】")
    print("  1. 读 references/design-systems/_routing.md 选设计系统")
    print("  2. 策划全稿（读 page-craft.md）→ 备料（读 image-direction.md）")
    print("  3. 建空稿 → 发开工通知")
    print("  4. 逐页闭环：XML → `check` → 写入 → 回读 → 宿主截图 → Read → LOOK → 必要时替换。")
    print("     同一个 `check` 合并合同/几何/资产/图文关系，并在 `--wrote` 后打印本页问句；")
    print("     一页一页来，不要攒批——攒批会让缺陷堆在一起、写入失败被埋住。")
    return 0


def cmd_shots(args) -> int:
    deck = Path(args.deck)
    shot_dir = next((p for p in (deck / "hostshots", deck / "shots") if p.is_dir()), deck)
    shots = sorted([p for p in shot_dir.glob("*")
                    if p.suffix.lower() in (".png", ".jpg", ".jpeg")])
    if not shots:
        print(f"BLOCK: {deck} 下没找到截图（找 shots/ 或目录本身的 png/jpg）。")
        return 2
    if not HAS_PIL:
        print("SHOTS: 像素测量不可用，拼不了缩略图墙。逐张 Read 这些文件也一样能做二轮通读：")
        for p in shots:
            print(f"  {p}")
        return 0
    cols = 4
    tw, th = 480, 270
    rows = math.ceil(len(shots) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * th), (250, 250, 250))
    for i, p in enumerate(shots):
        try:
            im = Image.open(p).convert("RGB").resize((tw, th))
        except Exception:                              # noqa: BLE001
            continue
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    out = deck / "_contact-sheet.jpg"
    sheet.save(out, quality=86)
    print(f"SHOTS: {len(shots)} 页拼成 {out}")
    print("  用它做二轮通读：Read 这一张，眯眼看——")
    print("  有没有视觉高潮与节奏换挡？有没有连续三页同构？明暗分布是不是同一套系统？")
    print(f"  然后与 references/gold/<你选的设计系统>.jpg 并排比一眼。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="deck.py", description="豆包视觉创意 · 尺子与工人")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("hostcheck", help="探测写入通路，打印可粘贴的命令")
    p.add_argument("--carrier", default="slides")
    p.add_argument("--skills-root", default="", help="渲染层技能包所在目录（找不到时手动指定）")
    p.set_defaults(func=cmd_hostcheck)

    p = sub.add_parser("check", help="机械校验一页或整册")
    p.add_argument("--slide", action="append", default=[])
    p.add_argument("--deck", default="")
    p.add_argument("--prompt", action="append", default=[],
                   help="改查生图 prompt 的图内文字风险（可重复）")
    p.add_argument("--contract", default="",
                   help="全稿交付合同：一行一项或 JSON；与 --deck 同跑，核对页头 deliver=")
    p.add_argument("--wrote", default=None,
                   help="单页写入后的宿主回读 XML；通过后才打印 LOOK，不能只给退出码")
    p.add_argument("--looked", nargs="?", const="", default=None,
                   help="看完这一页的截图之后，把几问的结论逐条带回来："
                        "`--looked '01:ok 02:fix 主体被切'`（每问 ok 或 fix:<一句>）。"
                        "必须同时带 --wrote；全部 ok 才结清这一页。不带值时重印本页问句。")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("ground", help="量出图自己的安静区/结构线/主体区")
    p.add_argument("--image", required=True)
    p.add_argument("--as-texture", action="store_true",
                   help="判这张图能不能当跨页纹理地（安静区是否覆盖几乎整张 + 中区有没有贯穿缝）")
    p.set_defaults(func=cmd_ground)

    p = sub.add_parser("shots", help="把截图拼成缩略图墙")
    p.add_argument("--deck", required=True)
    p.set_defaults(func=cmd_shots)

    args, unknown = ap.parse_known_args()
    if unknown:
        print(f"（忽略不认识的参数：{' '.join(unknown)}）", file=sys.stderr)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
