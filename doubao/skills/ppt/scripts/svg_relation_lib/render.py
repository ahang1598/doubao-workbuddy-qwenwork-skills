"""
顶层 render() 入口 · 支持当前保留关系图的组合式 API

组合管线：
    1. attrs   → resolve channels (attribute 层)
    2. chrome  → top_chrome (kicker / title / encoding_note)
    3. layout  → positions [{"id","x","y","w","h",...}] (支持 rect / circle / arc)
    4. skin    → draw_node / draw_edge (per element)
    5. chrome  → bottom_chrome (caption / source)
    6. wrap    → svg_wrapper (900×400 viewBox)

layout 输出归一化（不同 layout 返回不同形状）：
    * 矩形形式  {"id","x","y","w","h",...}
    * 圆形形式  {"id","cx","cy","r",...}
    * 环形形式  {"id","cx","cy","r_in","r_out","a_start","a_end",...}
    render 都把它们转成矩形 bbox 传给 skin.draw_node · edges 用中心点。

铁律：
    * 保持当前 11 个 relation preset 的渲染路径稳定
    * 不改 composite/ · 不改 svg_lib/
    * 纯 stdlib
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .palettes import Palette, GS_RESEARCH
from .engine import svg_wrapper, text as _text
from .chrome import BODY, top_chrome, bottom_chrome
from .attributes import resolve_channels
from .attributes.apply import apply_attributes
from .skins.editorial_atelier import HERO_CANVAS, EMBED_CANVAS, CanvasProfile


# ═════════════════════════════════════════════════════════════════
# ChromeConfig
# ═════════════════════════════════════════════════════════════════

@dataclass
class ChromeConfig:
    """chrome 配置 · 决定 top_chrome / bottom_chrome 的文案。"""
    kicker: str = ""
    title: str = ""
    encoding_note: str = ""
    caption: str = ""
    source: str = ""
    # v2 hero canvas 扩展字段 (canvas="embed" 时忽略)
    subtitle: str = ""
    column_headers: Optional[List[Tuple[str, float]]] = None
    read_lines: Optional[List[str]] = None
    # canvas profile 切换 · "embed" (默认 900×336 legacy) 或 "hero" (1400×820)
    canvas: str = "embed"

    @classmethod
    def from_schema(cls, schema: Any) -> "ChromeConfig":
        """从 schema 的 chrome metadata 抽取一份默认 ChromeConfig。

        当前保留的 Graph / Tree schema 都带 figure_title / figure_caption /
        source / encoding_note / kicker 五个字段。
        """
        return cls(
            kicker=getattr(schema, "kicker", "") or "",
            title=getattr(schema, "figure_title", "") or "",
            encoding_note=getattr(schema, "encoding_note", "") or "",
            caption=getattr(schema, "figure_caption", "") or "",
            source=getattr(schema, "source", "") or "",
            subtitle=getattr(schema, "subtitle", "") or "",
            column_headers=getattr(schema, "column_headers", None),
            read_lines=getattr(schema, "read_lines", None),
        )

    def get_canvas_profile(self) -> CanvasProfile:
        """返回对应 CanvasProfile · 供 render() 组装 SVG。"""
        return HERO_CANVAS if self.canvas == "hero" else EMBED_CANVAS


# ═════════════════════════════════════════════════════════════════
# helpers · schema element → dict (供 apply_attributes 使用)
# ═════════════════════════════════════════════════════════════════

_KNOWN_FIELDS = (
    "id", "label", "group", "type", "status", "size", "weight",
    "highlight", "role", "sublabel", "detail", "x", "y",
    # edge-only
    "src", "dst", "directed",
)


def _element_dict(element: Any) -> Dict[str, Any]:
    """把 schema 元素（dataclass / dict）转成 dict · 用于 apply_attributes。"""
    if element is None:
        return {}
    if isinstance(element, dict):
        return dict(element)
    out: Dict[str, Any] = {}
    for name in _KNOWN_FIELDS:
        if hasattr(element, name):
            out[name] = getattr(element, name)
    extra = getattr(element, "extra", None)
    if isinstance(extra, dict):
        for k, v in extra.items():
            out.setdefault(k, v)
    return out


def _walk_tree(root: Any) -> List[Any]:
    """DFS · root first · 展开 Tree.root 所有节点为 flat list。"""
    if root is None:
        return []
    out: List[Any] = []
    stack = [root]
    while stack:
        cur = stack.pop()
        out.append(cur)
        children = list(getattr(cur, "children", []) or [])
        # reverse 保证 DFS 顺序稳定 (children[0] 先出)
        for c in reversed(children):
            stack.append(c)
    return out


def _tree_edges(root: Any) -> List[Tuple[str, str]]:
    """返回 tree 的 parent→child (id, id) 对。"""
    if root is None:
        return []
    edges: List[Tuple[str, str]] = []
    stack = [root]
    while stack:
        cur = stack.pop()
        pid = getattr(cur, "id", "") or ""
        for c in list(getattr(cur, "children", []) or []):
            cid = getattr(c, "id", "") or ""
            edges.append((pid, cid))
            stack.append(c)
    return edges


def _get_schema_element(schema: Any, elem_id: str) -> Any:
    """根据 id 定位 schema 里的元素。支持 Tree / Graph / Flow。"""
    if not elem_id:
        return None
    # Graph-like · nodes 列表
    nodes = getattr(schema, "nodes", None)
    if nodes:
        for n in nodes:
            if getattr(n, "id", "") == elem_id:
                return n
    # Tree-like · root + children
    root = getattr(schema, "root", None)
    if root is not None:
        for n in _walk_tree(root):
            if getattr(n, "id", "") == elem_id:
                return n
    return None


# ═════════════════════════════════════════════════════════════════
# position 归一化 · 把 layout 输出统一成 (x, y, w, h, cx, cy)
# ═════════════════════════════════════════════════════════════════

def _normalize_position(pos: Dict[str, Any]) -> Dict[str, float]:
    """把不同 layout 的 output 归一化成 bbox + centre。

    输入 pos 可能形如：
        {"x","y","w","h"}                  # treemap / fishbone effect
        {"x","y"}                          # fishbone spine / category tip
        {"cx","cy","r"}                    # nested_circle
        {"cx","cy","r_in","r_out","a_start","a_end"}   # sunburst
    输出统一含 x/y/w/h/cx/cy 六个字段。
    附带 shape 字段: "rect" | "circle" | "arc" 供 render 决定 skin kind hint。
    """
    if "w" in pos and "h" in pos:
        x = float(pos.get("x", 0.0))
        y = float(pos.get("y", 0.0))
        w = float(pos.get("w", 0.0))
        h = float(pos.get("h", 0.0))
        # fishbone "effect" 的 x/y 是中心 · w/h 是尺寸
        if pos.get("kind") == "effect":
            return {"x": x - w / 2, "y": y - h / 2, "w": w, "h": h,
                    "cx": x, "cy": y, "shape": "rect"}
        return {"x": x, "y": y, "w": w, "h": h,
                "cx": x + w / 2.0, "cy": y + h / 2.0, "shape": "rect"}
    if "r" in pos:
        cx = float(pos.get("cx", 0.0))
        cy = float(pos.get("cy", 0.0))
        r = float(pos.get("r", 0.0))
        return {"x": cx - r, "y": cy - r, "w": 2 * r, "h": 2 * r,
                "cx": cx, "cy": cy, "shape": "circle", "r": r}
    if "r_out" in pos:
        cx = float(pos.get("cx", 0.0))
        cy = float(pos.get("cy", 0.0))
        r_in = float(pos.get("r_in", 0.0))
        r_out = float(pos.get("r_out", 0.0))
        a0 = float(pos.get("a_start", 0.0))
        a1 = float(pos.get("a_end", 0.0))
        # 环形段中心点在 (r_mid, a_mid) 极坐标
        r_mid = (r_in + r_out) / 2.0
        a_mid = (a0 + a1) / 2.0
        px = cx + r_mid * math.cos(a_mid)
        py = cy + r_mid * math.sin(a_mid)
        # 用弧宽近似作 bbox
        arc_w = max((r_out - r_in), 8.0)
        arc_h = max((a1 - a0) * r_mid, 8.0)
        return {"x": px - arc_w / 2, "y": py - arc_h / 2,
                "w": arc_w, "h": arc_h, "cx": px, "cy": py,
                "shape": "arc"}
    # 只有 x,y · 无尺寸 · fishbone category / subcause tip 走这条路
    x = float(pos.get("x", 0.0))
    y = float(pos.get("y", 0.0))
    kind = pos.get("kind", "")
    if kind == "category":
        # 分类标签 · 宽度按 label 估
        label = pos.get("label", "") or ""
        w = max(len(label) * 6 + 12, 50)
        h = 20
    elif kind == "subcause":
        label = pos.get("label", "") or ""
        w = max(len(label) * 5 + 8, 40)
        h = 16
    else:
        w, h = 40, 24
    return {"x": x - w / 2, "y": y - h / 2, "w": w, "h": h,
            "cx": x, "cy": y, "shape": "rect"}


# ═════════════════════════════════════════════════════════════════
# 属性 overlay · apply_attributes 的输出叠加到 svg 片段
# ═════════════════════════════════════════════════════════════════

_STYLE_KEYS = ("opacity", "fill", "stroke", "stroke-width", "stroke-dasharray")


def _overlay_style(inner_svg: str, style_attrs: Dict[str, Any]) -> str:
    """把 opacity/stroke 之类可以从外层 <g> 继承的属性套在 SVG 片段外。

    只挑出可 <g> 继承的 style · 其他的（比如 stroke fill · 每个 shape 自定义）
    通过 <g fill=... stroke=...> 继承。为保持 v1 preset byte-identical · 我们
    只在有属性时才添加 <g> · attrs 空时直接返回 inner_svg。
    """
    if not style_attrs:
        return inner_svg
    pairs = []
    for k in _STYLE_KEYS:
        v = style_attrs.get(k)
        if v is None:
            continue
        if isinstance(v, float):
            pairs.append(f'{k}="{v:.3f}"')
        else:
            pairs.append(f'{k}="{v}"')
    if not pairs:
        return inner_svg
    return f'<g {" ".join(pairs)}>{inner_svg}</g>'


# ═════════════════════════════════════════════════════════════════
# skin call helpers · 优雅降级 · skin 缺失时用简易 fallback
# ═════════════════════════════════════════════════════════════════

def _fallback_node(x: float, y: float, w: float, h: float,
                   label: str, palette: Palette) -> str:
    """skin=None 时的最小节点渲染 · 用 rect + label · 保证 render 可运行。"""
    from .engine import rect as _rect
    return (_rect(x, y, w, h, fill=palette.bg, stroke=palette.ink, sw=1.2) +
            _text(x + w / 2, y + h / 2 + 4, label,
                  size=10, color=palette.ink, family=palette.body_family,
                  anchor="middle"))


def _fallback_edge(x1: float, y1: float, x2: float, y2: float,
                   label: str, palette: Palette) -> str:
    from .engine import line as _line
    return _line(x1, y1, x2, y2, color=palette.ink, w=1.0)


def _call_skin_draw_node(skin: Any, pos: Dict[str, Any],
                          label: str, palette: Palette,
                          extra_kwargs: Dict[str, Any]) -> str:
    if skin is None:
        return _fallback_node(pos["x"], pos["y"], pos["w"], pos["h"],
                              label, palette)
    return skin.draw_node(pos["x"], pos["y"], pos["w"], pos["h"],
                          label, palette, **extra_kwargs)


def _call_skin_draw_edge(skin: Any, src_pos: Dict[str, Any], dst_pos: Dict[str, Any],
                          label: str, palette: Palette,
                          extra_kwargs: Dict[str, Any]) -> str:
    x1 = src_pos["cx"]
    y1 = src_pos["cy"]
    x2 = dst_pos["cx"]
    y2 = dst_pos["cy"]
    if skin is None:
        return _fallback_edge(x1, y1, x2, y2, label, palette)
    return skin.draw_edge(x1, y1, x2, y2, label, palette, **extra_kwargs)


def _skin_kwargs_from_element(element: Any) -> Dict[str, Any]:
    """从 schema element 抽出 skin 关心的额外 kwargs (kind / sublabel / numeral)。"""
    if element is None:
        return {}
    kwargs: Dict[str, Any] = {}
    # kind · 优先 type · 再 extra['kind'] · 最后 role
    kind = getattr(element, "type", "") or ""
    if not kind:
        extra = getattr(element, "extra", None) or {}
        kind = extra.get("kind", "") or ""
    if kind:
        kwargs["kind"] = kind
    sublabel = getattr(element, "sublabel", "") or ""
    if sublabel:
        kwargs["sublabel"] = sublabel
    return kwargs


# skin name → shape-friendly kind 映射
_SHAPE_KIND_MAP: Dict[str, Dict[str, str]] = {
    "napkin":         {"circle": "bubble",       "rect": "task",   "arc": "task"},
    "editorial":      {"circle": "item",         "rect": "item",   "arc": "item"},
}


def _default_kind_for_shape(skin: Any, shape: str) -> str:
    """根据 skin.name + shape 建议一个默认 kind。找不到就返回空 (skin 走 default)。"""
    name = getattr(skin, "name", "") if skin else ""
    m = _SHAPE_KIND_MAP.get(name, {})
    return m.get(shape, "")



# ═════════════════════════════════════════════════════════════════
# 主入口 · render()
# ═════════════════════════════════════════════════════════════════

def render(
    schema: Any,
    *,
    layout: Optional[Callable[..., List[Dict[str, Any]]]] = None,
    skin: Optional[Any] = None,
    attrs: Optional[List[Any]] = None,
    palette: Optional[Palette] = None,
    chrome: Optional[ChromeConfig] = None,
) -> str:
    """v2 顶层 render 入口 · 4 层组合。

    Args:
        schema:  Layer 1 · Tree / Graph.
        layout:  Layer 2 · 函数 (schema, x0, y0, x1, y1, **kwargs) → List[dict]
                 亦支持圆形 layout · signature (schema, cx, cy, r) —
                 我们通过 signature 探测决定调用形式。
        skin:    Layer 3 · Skin 实例 (draw_node / draw_edge / defs)。缺省时
                 用一个最小 fallback (rect + label) · 供数据结构验证。
        attrs:   Layer 4 · List[Attribute] · 按声明顺序 resolve channel。
        palette: 5 signature palette 之一 · 缺省 GS_RESEARCH。
        chrome:  ChromeConfig · 缺省从 schema 抽取。

    Returns:
        Complete SVG string · viewBox 900×400 · 含 top/bottom chrome。
    """
    attrs = attrs or []
    palette = palette or GS_RESEARCH
    chrome = chrome or ChromeConfig.from_schema(schema)
    channels = resolve_channels(attrs)

    parts: List[str] = []
    is_hero = chrome.canvas == "hero"
    profile = chrome.get_canvas_profile()

    # skin defs (filter / marker) · 若 skin 有则前置
    if skin is not None and hasattr(skin, "defs"):
        try:
            defs_svg = skin.defs(palette)
            if defs_svg:
                parts.append(defs_svg)
        except Exception:
            pass

    # ── top chrome ─────────────────────────────────────────────
    if is_hero:
        # hero canvas 用 editorial_atelier.hero_chrome
        from .skins.editorial_atelier import hero_chrome, hero_footer
        parts.append(hero_chrome(
            kicker=chrome.kicker,
            title=chrome.title,
            subtitle=chrome.subtitle,
            column_headers=chrome.column_headers,
            encoding_note_right=chrome.encoding_note,
            palette=palette,
            canvas=profile,
        ))
    else:
        parts.append(top_chrome(chrome.kicker, chrome.title, palette,
                                 encoding_note=chrome.encoding_note))

    # ── layout · 归一化 · id → position map ────────────────────
    positions: List[Dict[str, Any]] = []
    if layout is not None:
        positions = _invoke_layout(layout, schema, profile if is_hero else None)
    pos_by_id: Dict[str, Dict[str, Any]] = {}
    normalized: List[Dict[str, Any]] = []
    for pos in positions:
        norm = _normalize_position(pos)
        # 保留 layout 附带的语义字段 (kind / label / depth ...)
        for k in ("id", "label", "kind", "depth", "parent", "side", "angle",
                   "anchor_x", "anchor_y", "r_in", "r_out", "a_start", "a_end"):
            if k in pos:
                norm[k] = pos[k]
        normalized.append(norm)
        pid = pos.get("id", "")
        if pid:
            pos_by_id[pid] = norm

    # ── containers · 若 layout 返回 depth · 先绘 depth 大的 (内层)
    #    这里我们只绘制"真节点" (即有 label) 的容器 · 内层后画
    #    treemap / nested_circle / sunburst 里 depth==0 是 root 大 container
    max_depth = max((p.get("depth", 0) for p in normalized), default=0)
    has_depth = any("depth" in p for p in normalized)

    # ── 节点绘制 ────────────────────────────────────────────────
    # 跳过纯"结构 anchor" (spine_start / spine_end) — 无 label · 无实体
    node_svgs: List[Tuple[float, str]] = []   # (depth, svg) · depth 小的先绘
    fishbone_like_check = any(p.get("kind") in ("spine_start", "spine_end", "category", "subcause")
                              for p in normalized)
    for pos in normalized:
        kind_hint = pos.get("kind", "")
        if kind_hint in ("spine_start", "spine_end", "category_anchor"):
            continue
        elem_id = pos.get("id", "")
        element = _get_schema_element(schema, elem_id)
        if element is None:
            # tree layout 里的中间 anchor · 直接用 pos.label
            element_dict = {"id": elem_id, "label": pos.get("label", "")}
            has_children = False
        else:
            element_dict = _element_dict(element)
            has_children = bool(getattr(element, "children", None))
        label = element_dict.get("label", "") or pos.get("label", "") or ""

        # attribute apply
        style_attrs = apply_attributes(element_dict, attrs, palette, channels)

        # skin extra kwargs
        skin_kwargs = _skin_kwargs_from_element(element) if element else {}
        shape = pos.get("shape", "rect")

        # shape → skin kind hint (只在 skin 没被 element.type 指定时)
        if "kind" not in skin_kwargs and skin is not None:
            skin_kwargs["kind"] = _default_kind_for_shape(skin, shape)

        # 层级 spatial layout · 内部节点走 draw_container · 更符合"嵌套"语义
        use_container = (
            has_children and has_depth and not fishbone_like_check
            and skin is not None and hasattr(skin, "draw_container")
        )
        if use_container:
            container_kwargs = dict(skin_kwargs)
            # container 的 kind space 与 node 不同 · 让 skin 走 default
            container_kwargs.pop("kind", None)
            try:
                node_svg = skin.draw_container(pos["x"], pos["y"], pos["w"], pos["h"],
                                                label, palette, **container_kwargs)
            except Exception:
                node_svg = _call_skin_draw_node(skin, pos, label, palette, skin_kwargs)
        else:
            node_svg = _call_skin_draw_node(skin, pos, label, palette, skin_kwargs)
        node_svg = _overlay_style(node_svg, style_attrs)
        depth = pos.get("depth", 0)
        node_svgs.append((depth, node_svg))

    # depth 从小到大绘制（root 最先 · 叶子最后 · 内层覆盖外层）
    node_svgs.sort(key=lambda t: t[0])

    # ── edge 绘制 ──────────────────────────────────────────────
    edges = _collect_edges(schema)
    # Tree schema · schema.edges 空 · 决定是否补 parent→child 边：
    #   - hierarchical spatial layout
    #     不需要 tree edges · 因为空间包含关系已经表达了层级
    #   - fishbone layout · 用 anchor_x/anchor_y 走特殊 spine+branch 几何
    #   - 其余 (无 layout · 或线性 layout) 才画 parent→child 直线
    spatial_hier_layout = has_depth and any(
        (("depth" in p) and (p.get("depth", 0) > 0)) for p in normalized
    )
    fishbone_like = any(p.get("kind") in ("spine_start", "spine_end", "category", "subcause")
                        for p in normalized)

    # fishbone · 骨架线在 node 前 (线被 node 盖住)
    if fishbone_like:
        parts.append(_render_fishbone_lines(normalized, palette, skin))

    for _, svg in node_svgs:
        parts.append(svg)

    # 常规 edge (Graph / Tree parent→child)
    if not fishbone_like:
        if not edges and not spatial_hier_layout:
            root = getattr(schema, "root", None)
            if root is not None:
                for pid, cid in _tree_edges(root):
                    edges.append({"src": pid, "dst": cid, "label": "",
                                  "raw": None})

        for edge in edges:
            src_id = edge.get("src", "")
            dst_id = edge.get("dst", "")
            src_pos = pos_by_id.get(src_id)
            dst_pos = pos_by_id.get(dst_id)
            if src_pos is None or dst_pos is None:
                continue
            label = edge.get("label", "") or ""
            raw = edge.get("raw")
            edge_dict = _element_dict(raw) if raw is not None else {"src": src_id, "dst": dst_id, "label": label}
            edge_style = apply_attributes(edge_dict, attrs, palette, channels)
            edge_kwargs: Dict[str, Any] = {}
            if raw is not None:
                ek = _skin_kwargs_from_element(raw)
                edge_kwargs.update(ek)
            edge_svg = _call_skin_draw_edge(skin, src_pos, dst_pos, label,
                                             palette, edge_kwargs)
            edge_svg = _overlay_style(edge_svg, edge_style)
            parts.append(edge_svg)

    # ── bottom chrome ─────────────────────────────────────────
    if is_hero:
        from .skins.editorial_atelier import hero_footer
        parts.append(hero_footer(
            caption=chrome.caption,
            source=chrome.source,
            read_lines=chrome.read_lines,
            palette=palette,
            canvas=profile,
        ))
    else:
        parts.append(bottom_chrome(chrome.caption, chrome.source, palette))

    # canvas 尺寸切换 · 老代码走 900×400 default · hero 走 1400×820
    if is_hero:
        return svg_wrapper("".join(parts), w=profile.w, h=profile.h,
                           bg=palette.bg)
    return svg_wrapper("".join(parts))


# ═════════════════════════════════════════════════════════════════
# fishbone 专属几何 · 绘 spine + branch 线段（用 skin 的 arrow / line 语义）
# ═════════════════════════════════════════════════════════════════

def _render_fishbone_lines(normalized: List[Dict[str, Any]],
                            palette: Palette, skin: Any) -> str:
    """把 fishbone 的 spine + branch + subcause whisker 画出来。

    fishbone_layout 返回：
        spine_start / spine_end : 用来画中央脊柱
        category 节点带 anchor_x/anchor_y : 骨干支从 anchor 到 category tip
        subcause 节点带 anchor_x/anchor_y : whisker 从 anchor 到 sub 位置

    我们直接用 engine.arrow / line · 保持 fishbone 传统外观 · 不走 skin.draw_edge
    以免让 fishbone 的骨感被 skin 干扰。
    """
    from .engine import line as _line, arrow as _arrow
    ink = palette.ink
    accent = palette.accent

    parts: List[str] = []
    spine_start = None
    spine_end = None
    for p in normalized:
        if p.get("kind") == "spine_start":
            spine_start = p
        elif p.get("kind") == "spine_end":
            spine_end = p

    # 主脊柱 · 带箭头指向 effect
    if spine_start and spine_end:
        parts.append(_arrow(spine_start["cx"], spine_start["cy"],
                             spine_end["cx"], spine_end["cy"],
                             color=ink, w=1.8, head=10))

    # 分支 + whisker
    for p in normalized:
        k = p.get("kind")
        if k == "category":
            ax = p.get("anchor_x")
            ay = p.get("anchor_y")
            if ax is None or ay is None:
                continue
            parts.append(_line(ax, ay, p["cx"], p["cy"], color=ink, w=1.4))
        elif k == "subcause":
            ax = p.get("anchor_x")
            ay = p.get("anchor_y")
            if ax is None or ay is None:
                continue
            parts.append(_line(ax, ay, p["cx"], p["cy"],
                                color=palette.gray, w=1.0))

    return "".join(parts)


def _invoke_layout(layout: Callable, schema: Any,
                    hero_profile: Optional[CanvasProfile] = None) -> List[Dict[str, Any]]:
    """按 layout 的参数名探测调用形式。

    * fishbone_layout / treemap : (tree, x0, y0, x1, y1)
    * nested_circle              : (tree, cx, cy, r_outer)
    * sunburst_radial            : (tree, cx, cy, r_max)

    hero_profile: 若非 None · body 取 hero canvas 区域 (y=128→700) ·
                  否则用 legacy BODY (y=66→296)。
    """
    import inspect
    try:
        sig = inspect.signature(layout)
        params = list(sig.parameters.keys())
    except (TypeError, ValueError):
        params = []

    # polar layout 惯例: 第 2/3/4 arg 是 cx/cy/r
    is_polar = len(params) >= 4 and any(p in params[1:5] for p in ("cx", "r_outer", "r_max"))

    # 决定 body 边界
    if hero_profile is not None:
        bx0, by0 = hero_profile.margin_x, hero_profile.body_y0
        bx1, by1 = hero_profile.w - hero_profile.margin_x, hero_profile.body_y1
    else:
        bx = BODY
        bx0, by0, bx1, by1 = bx.x0, bx.y0, bx.x1, bx.y1

    if is_polar:
        cx = (bx0 + bx1) / 2
        cy = (by0 + by1) / 2
        # 半径取较小边的一半 · 留 4px 边距
        r = min(bx1 - bx0, by1 - by0) / 2 - 4
        try:
            return list(layout(schema, cx, cy, r))
        except TypeError:
            # 有的 sunburst_radial 签名: (tree, cx, cy, r_max, r_min=0)
            return list(layout(schema, cx, cy, r, 0.0))
    else:
        return list(layout(schema, bx0, by0, bx1, by1))


# ═════════════════════════════════════════════════════════════════
# edge 收集 · Graph 从 schema.edges · Tree 从 parent-child · 其他跳过
# ═════════════════════════════════════════════════════════════════

def _collect_edges(schema: Any) -> List[Dict[str, Any]]:
    """把 schema 的 edges 转成通用 dict [{"src","dst","label","raw"}]。"""
    out: List[Dict[str, Any]] = []
    raw_edges = getattr(schema, "edges", None)
    if raw_edges:
        for e in raw_edges:
            out.append({
                "src": getattr(e, "src", "") or "",
                "dst": getattr(e, "dst", "") or "",
                "label": getattr(e, "label", "") or "",
                "raw": e,
            })
    return out


__all__ = ["render", "ChromeConfig"]
