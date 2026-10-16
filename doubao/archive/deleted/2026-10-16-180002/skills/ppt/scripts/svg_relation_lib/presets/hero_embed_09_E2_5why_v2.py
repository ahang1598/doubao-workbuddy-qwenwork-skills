"""HERO EMBED · 09_E2_5why V2 · dandelion why5_ladder 风格

彻底重写: 参考 dandelion/why5_ladder.svg 的顶级视觉:
  - 左侧 SURFACE→ROOT rail + N 圆点
  - 中央 N 张深色 card 竖排 · card 间 WHY? 金色 pill
  - 顶部 4 KPI 带
  - 右侧 PARALLEL FACTOR 红底方框 + CORRECTIVE ACTIONS 短卡列表
  - viewBox 1400×720 hero canvas · 自适应 shrink 去右下留白

build_kwargs:
    - incident: str · L0 label
    - incident_sub: str · L0 sublabel
    - whys: List[(label, sublabel, hue, ntype)] · L1..Lroot 剩余层 · type ∈ {fact,flaw,root}
    - kicker / figure_title / figure_caption / source
    - kpis: List[{kicker, value, note, hue}] · [] 关闭
    - parallel_factor: {title, body, hint, tag}
    - corrective_actions: List[(code, phase, text, sprint)]
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..layouts.vertical_chain import (
    vertical_chain_layout, LayoutOverflow, VerticalChainParams,
)
from ..skins.editorial_atelier import (
    BONE_RUST, HUE, FONT_SANS, FONT_SERIF,
)
from ..skins._base import _fit_font_size, _wrap_lines
from ..skins.registry import get_active_skin as _get_active_skin


def _try_skin_draw(kind: str, x: float, y: float, w: float, h: float,
                   label: str, palette, **kwargs):
    skin_mod = _get_active_skin()
    if skin_mod is None:
        return None
    skin_inst = getattr(skin_mod, "SKIN_INSTANCE", None)
    if skin_inst is None:
        return None
    draw_fn = getattr(skin_inst, "draw_node", None)
    if draw_fn is None:
        return None
    try:
        return draw_fn(x, y, w, h, label, palette, kind=kind, **kwargs)
    except Exception:
        return None


# ═════════════════════════════════════════════════════════════════
# baseline data · 对齐 dandelion/why5_ladder.svg
# ═════════════════════════════════════════════════════════════════

BASELINE_WHYS: List[Tuple[str, str, str, str]] = [
    # (label, sublabel, hue, ntype)
    ("数据库连接池被打满",         "— pool util > 100% for 42 min —",         "cinnamon", "fact"),
    ("空闲连接超时保留 30 分钟未回收", "— idle_timeout = 1800s —",                "cinnamon", "flaw"),
    ("pg_bouncer keepalive 参数配置错误", "— tcp_keepalive=off 且未在 IaC 中管控 —", "magenta",  "flaw"),
    ("发布回滚脚本没检查配置差异",   "— last rollback drift: 2025-11 —",        "cinnamon", "fact"),
    ("回滚路径上没有配置漂移告警",   "— no drift alert on prod cluster —",       "rust",     "root"),
]

BASELINE_KPIS = [
    {"kicker": "INCIDENT",   "value": "42-min",       "note": "P1 checkout outage",     "hue": "cinnamon"},
    {"kicker": "DEPTH",      "value": "5 WHYs",       "note": "ladder length",          "hue": "olive"},
    {"kicker": "ROOT CAUSE", "value": "DRIFT ALERT MISSING", "note": "no config-drift signal", "hue": "rust"},
    {"kicker": "ACTIONS",    "value": "5",            "note": "2 immediate · 3 later",  "hue": "green"},
]

BASELINE_PARALLEL = {
    "tag":   "1× LOAD",
    "title": "PARALLEL FACTOR",
    "body":  "客户端重试导致流量放大 4×",
    "hint":  "— checkout-svc 没有指数退避 · 触发雪崩重试 → AMPLIFIED THE ORIGINAL ALERT —",
}

BASELINE_ACTIONS: List[Tuple[str, str, str, str]] = [
    # (code, phase, text, sprint)
    ("A1", "IMMEDIATE", "在 IaC 管控 pg_bouncer 参数",             "this sprint"),
    ("A2", "IMMEDIATE", "增加配置漂移告警",                            "this sprint"),
    ("A3", "SHORT",     "客户端加指数退避 + 熔断",                     "2 sprints"),
    ("A4", "PROCESS",   "每季度回滚演练",                              "ongoing"),
    ("A5", "MONITOR",   "连接池指标接入 SLO 板",                        "1 sprint"),
]


_UNSET = object()  # sentinel · 区分 caller "省略参数" (走 BASELINE) vs "显式传 None/[]" (关闭)
_HUE_KEYS = {"blue", "cinnamon", "green", "magenta", "olive", "rust", "orange", "gold_p"}
_TYPE_KEYS = {"alert", "fact", "flaw", "root", "decision", "neutral"}
_HUE_FALLBACK = ["blue", "green", "orange", "olive", "rust", "cinnamon", "magenta"]


def _default_why_type(index: int, total: int) -> str:
    return "root" if index == total - 1 else "fact"


def _normalize_why_tuple(tup: Tuple[Any, ...], index: int, total: int) -> Dict[str, str]:
    """Accept both legacy and generated case tuple orders.

    Legacy preset data uses (label, sublabel, hue, type). The trace case catalog
    emits (why_no, cause, evidence, hue). Normalize here so the case file stays
    untouched and this fix remains scoped to the E2 definition.
    """
    items = tuple("" if item is None else str(item) for item in tup)
    if len(items) == 4:
        a, b, c, d = items
        if d in _HUE_KEYS and c not in _HUE_KEYS:
            return {
                "label": b,
                "sublabel": c,
                "hue": d,
                "ntype": _default_why_type(index, total),
                "kicker": a,
            }
        hue = c if c in _HUE_KEYS else _HUE_FALLBACK[index % len(_HUE_FALLBACK)]
        ntype = d if d in _TYPE_KEYS else _default_why_type(index, total)
        return {"label": a, "sublabel": b, "hue": hue, "ntype": ntype, "kicker": ""}
    if len(items) == 3:
        a, b, c = items
        hue = c if c in _HUE_KEYS else _HUE_FALLBACK[index % len(_HUE_FALLBACK)]
        return {"label": a, "sublabel": b, "hue": hue, "ntype": _default_why_type(index, total), "kicker": ""}
    if len(items) == 2:
        a, b = items
        return {
            "label": a,
            "sublabel": b,
            "hue": _HUE_FALLBACK[index % len(_HUE_FALLBACK)],
            "ntype": _default_why_type(index, total),
            "kicker": "",
        }
    raise ValueError(f"why tuple must be 2/3/4-item, got {len(tup)}")


def build_e2_tree(
    incident: str = "结账服务超时 42 分钟",
    incident_sub: str = "— 2026-09-08 14:03 · P1 incident —",
    whys: Optional[List[Tuple[str, str, str, str]]] = None,
    kicker: str = "",
    figure_title: str = "5-Why 追问 · 结账服务 42 分钟宕机",
    figure_caption: str = "Sakichi Toyoda root-cause ladder · 5 追问 · 1 平行因素 · 5 整改",
    source: str = "Source · Sev-1 checkout outage · Postmortem draft",
    kpis: Any = _UNSET,
    parallel_factor: Any = _UNSET,
    corrective_actions: Any = _UNSET,
    show_sidebar: bool = True,
    post_fix_kpis: Any = _UNSET,
    fig_ref: str = "",
) -> Tree:
    """Build why5_ladder Tree.

    whys: List of (label, sublabel, hue, ntype) · type ∈ {'fact','flaw','root'}
      默认给出 5 层 (BASELINE_WHYS).

    R4-fix · 参数语义:
      - 未传 whys 的纯 baseline 演示保留 BASELINE_* 辅助信息
      - 显式传 whys 的真实 case 默认移除顶部 KPI band，保留右侧说明/行动区
      - 显式传 [] / None → 关闭对应区块
      - 显式传 list/dict → 用 caller 数据
    """
    src = whys if whys is not None else BASELINE_WHYS
    # sentinel-check:
    # - pure baseline demo (whys omitted) keeps showcase KPI content
    # - generated real cases pass whys explicitly; remove only the top KPI band,
    #   which the audit table explicitly asked to delete. Keep the chain rail,
    #   WHY connectors, and side explanations; fix their layout instead.
    _baseline_aux = whys is None
    _kpis = (BASELINE_KPIS if _baseline_aux else []) if kpis is _UNSET else (kpis or [])
    _parallel = BASELINE_PARALLEL if parallel_factor is _UNSET else (parallel_factor or None)
    _actions = BASELINE_ACTIONS if corrective_actions is _UNSET else (corrective_actions or [])
    if not show_sidebar:
        _parallel = None
        _actions = []
    root = TreeNode(
        id="e0", label=incident, sublabel=incident_sub,
        type="alert",
        group=(_kpis[0]["hue"] if _kpis else "rust"),
        extra={
            "kicker": "ALERT · INCIDENT",
            "kpis": _kpis,
            "parallel_factor": _parallel,
            "corrective_actions": _actions,
            "post_fix_kpis": [] if post_fix_kpis is _UNSET else (post_fix_kpis or []),
            "fig_ref": fig_ref,
        },
    )
    parent = root
    for i, tup in enumerate(src):
        why = _normalize_why_tuple(tuple(tup), i, len(src))
        n = TreeNode(
            id=f"e{i + 1}", label=why["label"], sublabel=why["sublabel"],
            group=why["hue"], type=why["ntype"],
            extra={"kicker": why["kicker"]} if why["kicker"] else {},
        )
        parent.children.append(n)
        parent = n

    return Tree(
        root=root, kicker=kicker,
        figure_title=figure_title,
        figure_caption=figure_caption,
        source=source,
        encoding_note=f"{len(src)} whys · root · postmortem",
    )


HERO_E2_DATA = build_e2_tree()
build_5why_data = build_e2_tree


# ═════════════════════════════════════════════════════════════════
# color fallback · dandelion 深墨色系
# ═════════════════════════════════════════════════════════════════

_DANDELION_HUE = {
    "blue":     "rgba(22,40,70,1)",
    "cinnamon": "rgba(88,42,50,1)",     # card 深墨红棕
    "green":    "rgba(16,106,82,1)",
    "magenta":  "rgba(120,68,108,1)",
    "olive":    "rgba(120,88,42,1)",
    "rust":     "rgba(140,42,55,1)",
    "orange":   "rgba(168,88,42,1)",
    "gold_p":   "rgba(212,168,88,1)",
}


def _hue(name: str, _palette: Palette) -> str:
    """Hue resolution with skin-aware fallback.

    优先级 (对齐 tx_taxonomy fix):
      1. Active skin's HUE dict (让 boardroom_navy / mbb_consulting 真的染色 card body)
      2. Module-level HUE (= editorial_atelier.HUE · reflect skin=editorial_atelier)
      3. _DANDELION_HUE 硬编码 baseline fallback
    """
    # 1. active skin HUE first (mbb_consulting / boardroom_navy 走这里)
    try:
        skin = _get_active_skin()
        if skin is not None:
            skin_hue = getattr(skin, "HUE", None)
            if skin_hue and name in skin_hue:
                c = skin_hue[name]
                if c:
                    return c
    except Exception:
        pass
    # 2. module-level HUE (editorial_atelier.HUE · 反映 _skin_override 覆写)
    c = HUE.get(name)
    if c and (c.startswith("#") or c.startswith("rgba") or c.startswith("rgb")):
        return c
    # 3. dandelion baseline fallback
    return _DANDELION_HUE.get(name, _DANDELION_HUE["cinnamon"])


def _hue_rgba(name: str, palette: Palette, alpha: float = 1.0) -> str:
    c = _hue(name, palette)
    if c.startswith("#"):
        h = c.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha:.2f})"
    if c.startswith("rgba"):
        import re
        m = re.match(r"rgba\((\d+),(\d+),(\d+),[\d.]+\)", c)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.2f})"
    return c


def _rgb_channels(color: str) -> Optional[Tuple[int, int, int]]:
    if not color:
        return None
    c = color.strip()
    if c.startswith("#") and len(c) >= 7:
        h = c.lstrip("#")
        try:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            return None
    if c.startswith("rgb"):
        import re
        m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", c)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def _luma(color: str) -> float:
    rgb = _rgb_channels(color)
    if rgb is None:
        return 0.0
    r, g, b = (ch / 255.0 for ch in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_text(fill: str) -> str:
    return "rgba(30,32,38,1)" if _luma(fill) >= 0.58 else "rgba(247,240,226,1)"


def _skin_overrides_why_card() -> bool:
    """检测 active skin 是否为 why_chain_card 提供了自绘分支.

    - editorial_atelier: SKIN_INSTANCE 无 _why_chain_card → 走 fallback ·
      preset 用 hue-color (深红棕/rust) 填 body · 标签用 pal.bg (cream) 反白.
    - boardroom_navy / mbb_consulting: 有 _why_chain_card 且填 pal.bg (ivory/白) ·
      标签必须用 pal.ink 深色否则同色不可见 (R1 regression 根因).
    参考 tx_taxonomy 的探测手法.
    """
    skin_mod = _get_active_skin()
    if skin_mod is None:
        return False
    skin_inst = getattr(skin_mod, "SKIN_INSTANCE", None)
    if skin_inst is None:
        return False
    return hasattr(skin_inst, "_why_chain_card")


def _card_text_palette(pal: Palette) -> Dict[str, str]:
    """基于 active skin 决定 card 内 4 类文字颜色 · 保证 fill 和 text 高对比.

    two modes:
      - dark_body (fallback · editorial): body = hue (deep rust) · text = pal.bg (cream/ivory)
      - light_body (skin override · boardroom/mbb): body = pal.bg (ivory/白) · text = pal.ink (深)

    返回: {label, sublabel, kicker, level, root_tag_text, root_tag_fill}
    root_tag: gold 底 + 深字 (两种 mode 均如此)
    """
    gold = _hue("gold_p", pal)
    if _skin_overrides_why_card():
        # light body · dark label 模式
        return {
            "label":    pal.ink,
            "sublabel": _rgba_from_str(pal.ink, 0.72),
            "kicker":   _hue("rust", pal),           # 深红/深墨作 kicker · 而非 gold_p 淡色
            "level":    _rgba_from_str(pal.ink, 0.55),
            "root_tag_text": _contrast_text(gold),
            "root_tag_fill": gold,
            "sublabel_min_alpha": True,
        }
    # dark body · light label (editorial default)
    return {
        "label":    pal.bg,
        "sublabel": "rgba(247,240,226,0.75)",
        "kicker":   gold,
        "level":    "rgba(247,240,226,0.55)",
        "root_tag_text": _contrast_text(gold),
        "root_tag_fill": gold,
        "sublabel_min_alpha": False,
    }


def _rgba_from_str(color: str, alpha: float) -> str:
    """把 '#RRGGBB' / 'rgba(r,g,b,a)' 转成 'rgba(r,g,b,alpha)'."""
    if color.startswith("#"):
        h = color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha:.2f})"
    if color.startswith("rgba"):
        import re
        m = re.match(r"rgba\((\d+),(\d+),(\d+),[\d.]+\)", color)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.2f})"
    if color.startswith("rgb"):
        import re
        m = re.match(r"rgb\((\d+),(\d+),(\d+)\)", color)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.2f})"
    return color


VIEW_W = 1400
VIEW_H = 720


# Bucket H (2026-09-13) · subtract_level default "L3" (极简)
_SUBTRACT_L0: List[str] = []
_SUBTRACT_L1: List[str] = ["rail_label_bot"]
_SUBTRACT_L2: List[str] = ["rail_label_bot", "rail_label_top"]
_SUBTRACT_L3: List[str] = []
_SUBTRACT_MAP = {"L0": _SUBTRACT_L0, "L1": _SUBTRACT_L1,
                 "L2": _SUBTRACT_L2, "L3": _SUBTRACT_L3}


def _resolve_skip_kinds(skip_kinds: Optional[List[str]], subtract_level: str) -> set:
    if skip_kinds is not None:
        return set(skip_kinds)
    return set(_SUBTRACT_MAP.get(subtract_level, _SUBTRACT_L3))


def _compute_layout_params(n_chain: int, has_kpis: bool, has_sidebar: bool) -> VerticalChainParams:
    """按链条长度 + top/right 内容存在情况选 card_h / gap / top_y.

    R2-fix (chain_top vs KPI overlap regression):
    KPI 带 SVG y=112..154 · rail_label_top y = first_y - 22 = chain_top + card_h/2 - 22.
    R1 用 chain_top=148 让 rail_label 落到 y=153 · 恰好挤在 KPI 带 x=90..1310 内部 ·
    slide 上呈现 "SURFACE" 撞 KPI value 事故. R2 把 has_kpis 分支 top_y 抬到 176 ·
    保证 rail_label / 第一 card 都彻底掉出 KPI 带.

    R2 chain 7 whys 数验: top=176 · card_h=54 · gap=6 → bottom = 176 + 8*54 + 7*6 = 650 SVG ·
    atomize (650-15)*0.624 + 110 = 506 slide · 稳过 540 硬红线.

    R5-fix: 保留原有 rail / WHY pill / 右侧说明区，只通过拉开顶区、卡片 gap、
    右侧行高与换行来解决线上 atomize 后的重叠。
    """
    top_y_base = 230 if has_kpis else 170  # R5-fix: enough chrome gap after atomization
    if has_kpis:
        if n_chain <= 3:
            card_h, card_gap = 84, 18
            top_y = top_y_base + 18
        elif n_chain == 4:
            card_h, card_gap = 72, 16
            top_y = top_y_base + 8
        elif n_chain == 5:
            card_h, card_gap = 62, 16
            top_y = top_y_base
        elif n_chain == 6:
            card_h, card_gap = 52, 18
            top_y = top_y_base
        elif n_chain == 7:
            card_h, card_gap = 46, 14
            top_y = top_y_base
        else:
            card_h, card_gap = 38, 12
            top_y = top_y_base
    else:
        if n_chain <= 3:
            card_h, card_gap = 96, 28
            top_y = top_y_base + 28
        elif n_chain == 4:
            card_h, card_gap = 82, 24
            top_y = top_y_base + 12
        elif n_chain == 5:
            card_h, card_gap = 72, 26
            top_y = top_y_base
        elif n_chain == 6:
            card_h, card_gap = 64, 30
            top_y = top_y_base
        elif n_chain == 7:
            card_h, card_gap = 50, 24
            top_y = top_y_base
        else:
            card_h, card_gap = 44, 20
            top_y = top_y_base

    # 有右侧栏时 chain 居左窄栏 · 无侧栏时链条居中占宽
    if has_sidebar:
        chain_cx = 470.0
        card_w = 620.0
        sidebar_x = 826.0
        sidebar_w = 486.0
    else:
        chain_cx = 700.0        # 居中
        card_w = 820.0          # 拉宽 card 让 2-why 场景不空
        sidebar_x = 1200.0      # 藏到画布外
        sidebar_w = 486.0

    return VerticalChainParams(
        canvas_w=VIEW_W, canvas_h=VIEW_H,
        chain_cx=chain_cx, chain_top_y=float(top_y),
        card_w=card_w, card_h=float(card_h), card_gap=float(card_gap),
        rail_x=88.0, sidebar_x=sidebar_x, sidebar_w=sidebar_w,
    )


def render_hero_embed_e2_5why_v2(
    data: Tree = HERO_E2_DATA,
    palette: Palette = BONE_RUST,
    params: Optional[VerticalChainParams] = None,
    *,
    subtract_level: str = "L3",
    skip_kinds: Optional[List[str]] = None,
) -> str:
    """渲染 dandelion why5_ladder 风格. viewBox 1400×720."""
    # [FONT-PATCH-L1] font pass-through (standalone): ea.FONT_SANS/SERIF 覆写
    _MOD_FONT = globals()
    _ORIG_FONT = {k: _MOD_FONT[k] for k in ('FONT_SANS', 'FONT_SERIF') if k in _MOD_FONT}
    try:
        from ..skins import editorial_atelier as _ea_font
        if 'FONT_SANS' in _MOD_FONT and _ea_font.FONT_SANS != _MOD_FONT['FONT_SANS']:
            _MOD_FONT['FONT_SANS'] = _ea_font.FONT_SANS
        if 'FONT_SERIF' in _MOD_FONT and _ea_font.FONT_SERIF != _MOD_FONT['FONT_SERIF']:
            _MOD_FONT['FONT_SERIF'] = _ea_font.FONT_SERIF
    except Exception:
        pass
    try:
        pal = palette or BONE_RUST

        root = getattr(data, "root", None)
        if root is None:
            raise LayoutOverflow("5why: no root")
        root_extra = getattr(root, "extra", {}) or {}
        kpis = root_extra.get("kpis", []) or []
        parallel = root_extra.get("parallel_factor") or {}
        actions = root_extra.get("corrective_actions") or []

        # 数链条长度
        _chain_len = 1
        _cur = root
        while True:
            _kids = list(getattr(_cur, "children", []) or [])
            if not _kids:
                break
            _cur = _kids[0]
            _chain_len += 1

        has_sidebar = bool(parallel or actions)
        # R1-fix: 自适应 layout 参数
        p = params or _compute_layout_params(_chain_len, bool(kpis), has_sidebar)

        positions = vertical_chain_layout(data, 70, 100, 1330, 690, params=p)
        # Bucket H · subtraction filter
        _skips = _resolve_skip_kinds(skip_kinds, subtract_level)
        if _skips:
            positions = [pos for pos in positions if pos.get("kind") not in _skips]

        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {VIEW_H}">',
        ]
        parts.append(f'<rect x="0" y="0" width="{VIEW_W}" height="{VIEW_H}" '
                     f'fill="{pal.bg}"/>')

        # ── 顶部 chrome ──
        # R1-fix: font-size 全面提升 · atomize scale ≈ 0.624 (slide_w=900/vb_w≈1250 · slide_h=440/vb_h≈705)
        # slide-native 10pt 硬红线 → SVG ≥ 16pt (16*0.624=9.98 → round 10). label 主体 20pt+ → 13pt slide.
        if getattr(data, "kicker", ""):
            parts.append(
                f'<text x="90" y="32" font-family="{FONT_SANS}" font-size="16" '
                f'fill="{_hue("rust", pal)}" font-weight="700" '
                f'letter-spacing="0.22em">{esc(data.kicker.upper())}</text>'
            )
        parts.append(
            f'<text x="90" y="82" font-family="{FONT_SERIF}" font-size="26" '
            f'font-weight="600" fill="{pal.ink}" letter-spacing="0.4">'
            f'{esc(data.figure_title)}</text>'
        )
        if getattr(data, "figure_caption", ""):
            parts.append(
                f'<text x="90" y="132" font-family="{FONT_SANS}" font-size="16" '
                f'fill="rgba(64,70,82,1)" letter-spacing="0.2">'
                f'{esc(data.figure_caption)}</text>'
            )
        parts.append(
            f'<line x1="90" y1="152" x2="1310" y2="152" '
            f'stroke="{pal.ink}" stroke-width="0.8"/>'
        )

        # ── KPI 带 ──
        # R1-fix: kicker 8.5→16 · value 13→22 · note 9.5→16 · kpi_h 30→42 容大字
        # R3-fix (2026-09-14 · atomize collision):
        #   value + note 同 y=kpi_y+36 时 · 长 value ("DRIFT ALERT MISSING")
        #   与 end-anchored 长 note ("no config-drift signal") 会叠字 ·
        #   value 尾字被 note 首字覆盖. 把 note 挪到 value 下一行 (kpi_y+56) ·
        #   相应把 kpi_h 42→60 让 3 行 (kicker/value/note) 各占一行.
        if kpis:
            kpi_y = 154
            kpi_w = 280            # 拉宽给 note 留白
            kpi_h = 60             # was 42 · 加高容 3 行 (kicker/value/note)
            kpi_start_x = 90
            kpi_gap = 24
            # 若 kpi 数 <4 自动缩宽
            n_kpi = min(len(kpis), 4)
            avail_w = 1220 - kpi_start_x
            kpi_w = min(kpi_w, (avail_w - (n_kpi - 1) * kpi_gap) / n_kpi)
            for i, k in enumerate(kpis[:4]):
                kx = kpi_start_x + i * (kpi_w + kpi_gap)
                hue = k.get("hue", "blue")
                c = _hue(hue, pal)
                parts.append(
                    f'<rect x="{kx:.1f}" y="{kpi_y}" width="{kpi_w:.1f}" height="{kpi_h}" '
                    f'fill="rgba(243,235,218,1)" stroke="rgba(175,178,188,1)" '
                    f'stroke-width="0.6"/>'
                )
                parts.append(
                    f'<rect x="{kx:.1f}" y="{kpi_y}" width="4" height="{kpi_h}" fill="{c}"/>'
                )
                parts.append(
                    f'<text x="{kx + 14:.1f}" y="{kpi_y + 17}" font-family="{FONT_SANS}" '
                    f'font-size="16" fill="rgba(115,120,132,1)" font-weight="600" '
                    f'letter-spacing="1.2">{esc(str(k.get("kicker", "")).upper())}</text>'
                )
                parts.append(
                    f'<text x="{kx + 14:.1f}" y="{kpi_y + 36}" font-family="{FONT_SERIF}" '
                    f'font-size="22" fill="{pal.ink}" font-weight="700">'
                    f'{esc(str(k.get("value", "")))}</text>'
                )
                if k.get("note"):
                    # R3-fix: note 换到 value 下行 (kpi_y+54) · 不再与 value 同 y
                    # 抖动 · 消除 "DRIFT ALERT MISSING" 尾字被 note 首字覆盖
                    parts.append(
                        f'<text x="{kx + 14:.1f}" y="{kpi_y + 54}" '
                        f'font-family="{FONT_SANS}" '
                        f'font-size="16" fill="rgba(115,120,132,1)">'
                        f'{esc(str(k["note"]))}</text>'
                    )

        # ── 左侧 rail 竖线 + SURFACE / ROOT 标签 ──
        # R1-fix chatter: rail label 只在链条 ≥ 4 时显示 · 2-why 场景 hide 减 noise
        # R2-fix: KPI 存在时 · rail_label_top 会撞进 KPI 横带 (x=90..1310 y=112..154) ·
        # 直接 hide top label · KPI 带本身已足够作 SURFACE 位视觉锚点
        _show_rail_top = (_chain_len >= 4) and (not kpis)
        _show_rail_bot = _chain_len >= 4
        for pos in positions:
            if pos["kind"] == "rail_line":
                parts.append(
                    f'<line x1="{pos["x"]}" y1="{pos["y1"]}" '
                    f'x2="{pos["x"]}" y2="{pos["y2"]}" '
                    f'stroke="rgba(115,120,132,0.5)" stroke-width="1"/>'
                )
            elif pos["kind"] == "rail_label_top" and _show_rail_top:
                parts.append(
                    f'<text x="{pos["x"]}" y="{pos["y"]}" text-anchor="middle" '
                    f'font-family="{FONT_SANS}" font-size="16" '
                    f'fill="rgba(115,120,132,1)" font-weight="700" '
                    f'letter-spacing="0.24em">{esc(pos["text"])}</text>'
                )
            elif pos["kind"] == "rail_label_bot" and _show_rail_bot:
                parts.append(
                    f'<text x="{pos["x"]}" y="{pos["y"]}" text-anchor="middle" '
                    f'font-family="{FONT_SANS}" font-size="16" '
                    f'fill="rgba(115,120,132,1)" font-weight="700" '
                    f'letter-spacing="0.24em">{esc(pos["text"])}</text>'
                )

        # ── 左侧 rail 圆点 ──
        for pos in positions:
            if pos["kind"] != "rail_dot":
                continue
            c = _hue(pos["hue"], pal)
            # 外圆 (是根/警告时高亮)
            if pos["is_root"] or pos["is_alert"]:
                parts.append(
                    f'<circle cx="{pos["cx"]}" cy="{pos["cy"]}" r="9" '
                    f'fill="{c}" opacity="0.15"/>'
                )
            parts.append(
                f'<circle cx="{pos["cx"]}" cy="{pos["cy"]}" r="6" '
                f'fill="{pal.bg}" stroke="{c}" stroke-width="2"/>'
            )
            parts.append(
                f'<circle cx="{pos["cx"]}" cy="{pos["cy"]}" r="2.5" fill="{c}"/>'
            )

        # ── 主链 card ──
        # R1-fix: kicker 8.5→16 · label 17→20 · sublabel 10.5→16 · L-badge 16→18
        # card_h 由 _compute_layout_params 决定 · 6+ whys 时 card 稍窄留白 · 少 whys 时拉大
        # R2-fix: card body fill 与 label text 的对比 由 _card_text_palette() 统一派生 ·
        # 避免 boardroom/mbb skin 下 body=pal.bg 与 label 也用 pal.bg 造成 invisible 灾难.
        _cpal = _card_text_palette(pal)
        for pos in positions:
            if pos["kind"] != "chain_card":
                continue
            c = _hue(pos["hue"], pal)
            skin_svg = _try_skin_draw(
                "why_chain_card", pos["x"], pos["y"], pos["w"], pos["h"], "", pal,
                hue=pos["hue"], hue_color=c, is_root=pos["is_root"],
            )
            if skin_svg:
                parts.append(skin_svg)
            else:
                # 深墨 card
                parts.append(
                    f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'width="{pos["w"]}" height="{pos["h"]}" fill="{c}"/>'
                )
                # 左侧 hue bar (更深/更亮) · 用金色高亮 root
                bar_color = _hue("gold_p", pal) if pos["is_root"] else _hue_rgba("gold_p", pal, 0.7)
                parts.append(
                    f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'width="4" height="{pos["h"]}" fill="{bar_color}"/>'
                )
            if skin_svg:
                card_fill = pal.bg
            else:
                card_fill = c
            label_fill = _contrast_text(card_fill)
            sublabel_fill = _rgba_from_str(label_fill, 0.76)
            kicker_fill = _cpal["kicker"]
            if _luma(card_fill) >= 0.58 and _luma(kicker_fill) >= 0.58:
                kicker_fill = label_fill
            level_fill = _rgba_from_str(label_fill, 0.60)
            # 卡内 y 分配 · 按 card_h 自适应 (6+ whys 时 card_h=54~58 · 3 行紧贴)
            _ch = float(pos["h"])
            if _ch >= 76:
                _y_kick, _y_lbl, _y_sub = 18, 48, 68
            elif _ch >= 64:
                _y_kick, _y_lbl, _y_sub = 16, 44, 61
            else:  # tight 54~62
                _y_kick, _y_lbl, _y_sub = 14, 36, 0
            # kicker · light body → 深红 kicker · dark body → gold kicker
            parts.append(
                f'<text x="{pos["x"] + 18:.1f}" y="{pos["y"] + _y_kick:.1f}" '
                f'font-family="{FONT_SANS}" font-size="16" fill="{kicker_fill}" '
                f'font-weight="700" letter-spacing="0.2em">'
                f'{esc(pos["kicker"])}</text>'
            )
            # label (大字 serif)
            label_avail = pos["w"] - (230 if pos["is_root"] else 120)
            _base_lbl = 22.0 if _ch >= 76 else (20.0 if _ch >= 64 else 18.0)
            fs, txt = _fit_font_size(pos["label"], label_avail, _base_lbl, min_size=16.0)
            parts.append(
                f'<text x="{pos["x"] + 18:.1f}" y="{pos["y"] + _y_lbl:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="{fs:.1f}" fill="{label_fill}" '
                f'font-weight="700">{esc(txt)}</text>'
            )
            # sublabel (italic 副标题) · 只在有空间时显示
            if pos.get("sublabel") and _ch >= 64:
                sub_avail = pos["w"] - (230 if pos["is_root"] else 40)
                _base_sub = 17.0 if _ch >= 76 else 16.0
                sfs, stxt = _fit_font_size(pos["sublabel"], sub_avail, _base_sub, min_size=16.0)
                parts.append(
                    f'<text x="{pos["x"] + 18:.1f}" y="{pos["y"] + _y_sub:.1f}" '
                    f'font-family="{FONT_SERIF}" font-size="{sfs:.1f}" '
                    f'fill="{sublabel_fill}" font-style="italic">'
                    f'{esc(stxt)}</text>'
                )
            # 右上 L0..L(n-1) 标签 (18pt · slide 11)
            if not pos["is_root"]:
                parts.append(
                    f'<text x="{pos["x"] + pos["w"] - 16:.1f}" y="{pos["y"] + _y_kick + 4:.1f}" '
                    f'text-anchor="end" font-family="{FONT_SERIF}" font-size="18" '
                    f'fill="{level_fill}" font-weight="700" font-style="italic">'
                    f'{pos["level"]}</text>'
                )
            # 根节点右侧 ★ ROOT CAUSE 标签 · 16pt tag text (slide 10)
            if pos["is_root"]:
                root_tag_x = pos["x"] + pos["w"] - 18
                root_tag_y = pos["y"] + pos["h"] / 2 + 6
                parts.append(
                    f'<text x="{root_tag_x:.1f}" y="{root_tag_y:.1f}" '
                    f'text-anchor="end" font-family="{FONT_SANS}" font-size="16" '
                    f'fill="{label_fill}" font-weight="700" letter-spacing="0.18em">'
                    f'{esc(pos["level"])} · ROOT CAUSE</text>'
                )

        # ── WHY? 金色 pill 连接 ──
        # R5-fix: keep the connector, but size it to the actual inter-card gap.
        # Fixed 24px pills overlap card boxes when the chain has many levels.
        for pos in positions:
            if pos["kind"] != "why_pill":
                continue
            pill_h = min(20.0, max(8.0, p.card_gap - 10.0))
            pill_w = 96 if pill_h >= 18 else 76
            pill_fs = min(16.0, max(10.0, pill_h * 0.68))
            px = pos["cx"] - pill_w / 2
            py = pos["cy"] - pill_h / 2
            gold = _hue("gold_p", pal)
            parts.append(
                f'<rect x="{px:.1f}" y="{py:.1f}" width="{pill_w}" height="{pill_h}" '
                f'rx="{pill_h / 2:.1f}" fill="{pal.bg}" stroke="{gold}" stroke-width="1.4"/>'
            )
            parts.append(
                f'<text x="{pos["cx"]:.1f}" y="{pos["cy"] + pill_fs * 0.35:.1f}" '
                f'text-anchor="middle" font-family="{FONT_SANS}" font-size="{pill_fs:.1f}" '
                f'fill="{gold}" font-weight="700" letter-spacing="0.2em">'
                f'WHY?</text>'
            )

        # ── 右侧 PARALLEL FACTOR 红底方框 ──
        # R1-fix: tag 9→16 · title 9→16 · body 18 保持 · hint 10→16 · box 128→116 更紧
        # 右侧 parallel factor 保留原版结构，内部通过分行避免标题/tag/body 互相压住
        if parallel and has_sidebar:
            pf_x = p.sidebar_x
            pf_y = 230 if kpis else 190
            pf_w = p.sidebar_w
            pf_h = 142
            pf_c = _hue("rust", pal)
            pf_text = _contrast_text(pf_c)
            pf_muted = _rgba_from_str(pf_text, 0.78)
            parts.append(
                f'<rect x="{pf_x}" y="{pf_y}" width="{pf_w}" height="{pf_h}" '
                f'fill="{pf_c}"/>'
            )
            # 右上 tag
            tag_w = 0
            if parallel.get("tag"):
                tag_w = 210
                tag_h = 26
                tx = pf_x + pf_w - tag_w - 14
                ty = pf_y + 12
                parts.append(
                    f'<rect x="{tx}" y="{ty}" width="{tag_w}" height="{tag_h}" '
                    f'rx="3" fill="{_hue("gold_p", pal)}" opacity="0.92"/>'
                )
                parts.append(
                    f'<text x="{tx + tag_w / 2}" y="{ty + 18}" text-anchor="middle" '
                    f'font-family="{FONT_SANS}" font-size="16" '
                    f'fill="{_contrast_text(_hue("gold_p", pal))}" font-weight="700" letter-spacing="0.18em">'
                    f'{esc(str(parallel["tag"]))}</text>'
                )
            # title kicker (gold)
            title_fs, title_txt = _fit_font_size(
                str(parallel.get("title", "PARALLEL FACTOR")),
                pf_w - 40,
                14.0,
                min_size=10.0,
            )
            parts.append(
                f'<text x="{pf_x + 12}" y="{pf_y + 66}" font-family="{FONT_SANS}" '
                f'font-size="{title_fs:.1f}" fill="{pf_text}" font-weight="700" '
                f'letter-spacing="0">{esc(title_txt)}</text>'
            )
            # body 大字 · 支持两行，避免长英文/混排内容溢出红框
            body_lines = _wrap_lines(str(parallel.get("body", "")), pf_w - 40,
                                     char_w=10.0, max_lines=2)
            for li, line in enumerate(body_lines):
                parts.append(
                    f'<text x="{pf_x + 12}" y="{pf_y + 94 + li * 20}" '
                    f'font-family="{FONT_SERIF}" font-size="16" '
                    f'fill="{pf_text}" font-weight="700">{esc(line)}</text>'
                )
            # hint italic 16pt
            if parallel.get("hint"):
                hint_lines = _wrap_lines(str(parallel["hint"]), pf_w - 40,
                                           char_w=8.4, max_lines=2)
                for li, line in enumerate(hint_lines):
                    parts.append(
                        f'<text x="{pf_x + 20}" y="{pf_y + 132 + li * 16}" '
                        f'font-family="{FONT_SERIF}" font-size="14" '
                        f'fill="{pf_muted}" font-style="italic">'
                        f'{esc(line)}</text>'
                    )

        # ── 右侧 CORRECTIVE ACTIONS 短卡列表 ──
        # R1-fix: title 10→16 · code/phase/sprint 9→16 · action text 12→17 · row 46→50
        if actions and has_sidebar:
            ca_x = p.sidebar_x
            # 位置 · parallel 结束下方
            ca_y_start = (pf_y + pf_h + 24) if parallel else (190 if kpis else 116)
            parts.append(
                f'<text x="{ca_x}" y="{ca_y_start}" font-family="{FONT_SANS}" '
                f'font-size="16" fill="rgba(115,120,132,1)" font-weight="600" '
                f'letter-spacing="0.22em">CORRECTIVE ACTIONS · {len(actions)}</text>'
            )
            parts.append(
                f'<line x1="{ca_x}" y1="{ca_y_start + 8}" x2="{ca_x + p.sidebar_w}" '
                f'y2="{ca_y_start + 8}" stroke="{pal.ink}" stroke-width="0.6"/>'
            )
            # row_h 由 actions 数决定 · 支持正文两行，避免右侧 rows 文字互相压住
            n_act = min(len(actions), 6)
            avail_h = max(240, 650 - (ca_y_start + 24))
            row_h = min(66.0, max(60.0, avail_h / max(n_act, 1)))
            for i, act in enumerate(actions[:6]):
                if len(act) == 4:
                    code, phase, text, sprint = act
                elif len(act) == 3:
                    code, phase, text = act; sprint = ""
                else:
                    continue
                row_y = ca_y_start + 24 + i * row_h
                # 左描 hue bar
                phase_hue = {
                    "IMMEDIATE": "rust",
                    "SHORT":     "cinnamon",
                    "PROCESS":   "olive",
                    "MONITOR":   "green",
                }.get(phase.upper(), "blue")
                hc = _hue(phase_hue, pal)
                parts.append(
                    f'<rect x="{ca_x}" y="{row_y:.1f}" width="4" height="{row_h - 8:.1f}" '
                    f'fill="{hc}"/>'
                )
                meta = f"{code} · {phase.upper()}"
                meta_fs, meta_txt = _fit_font_size(meta, p.sidebar_w - 150, 12.0, min_size=10.0)
                parts.append(
                    f'<text x="{ca_x + 18}" y="{row_y + 16:.1f}" font-family="{FONT_SANS}" '
                    f'font-size="{meta_fs:.1f}" fill="{hc}" font-weight="700" '
                    f'letter-spacing="0">{esc(meta_txt)}</text>'
                )
                if sprint:
                    sprint_fs, sprint_txt = _fit_font_size(str(sprint), 130.0, 12.0, min_size=10.0)
                    parts.append(
                        f'<text x="{ca_x + p.sidebar_w - 8}" y="{row_y + 30:.1f}" '
                        f'text-anchor="end" font-family="{FONT_SANS}" font-size="{sprint_fs:.1f}" '
                        f'fill="rgba(115,120,132,1)" font-style="italic">'
                        f'{esc(sprint_txt)}</text>'
                    )
                # text (主体) · 最多两行，避免长 action 文案和下一行相互覆盖
                avail = p.sidebar_w - 28
                text_lines = _wrap_lines(str(text), avail, char_w=8.0, max_lines=2)
                for li, line in enumerate(text_lines[:2]):
                    parts.append(
                        f'<text x="{ca_x + 18}" y="{row_y + 42 + li * 16:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="16" fill="{pal.ink}" '
                        f'font-weight="500">{esc(line)}</text>'
                    )
                # 下横线
                parts.append(
                    f'<line x1="{ca_x}" y1="{row_y + row_h - 4:.1f}" '
                    f'x2="{ca_x + p.sidebar_w}" y2="{row_y + row_h - 4:.1f}" '
                    f'stroke="rgba(175,178,188,0.5)" stroke-width="0.5"/>'
                )

        parts.append('</svg>')
        return "".join(parts)
    finally:
        _MOD_FONT.update(_ORIG_FONT)
__all__ = [
    "HERO_E2_DATA", "build_e2_tree", "build_5why_data", "render_hero_embed_e2_5why_v2",
    "BASELINE_WHYS", "BASELINE_KPIS", "BASELINE_PARALLEL", "BASELINE_ACTIONS",
]
