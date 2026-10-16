# Bucket H · subtract_level default "L3" (2026-09-13)
"""HERO EMBED · 08_KP_kpi V2 · Hero canvas 1400×720 · KPI cascade reference.

参考 step1_reference/kpi_hero_reference.svg 1:1 复刻的视觉水准 +
具备完整数据可扩展性:
  - 顶部 chrome: serif title + caption + hairline + FIGURE 08 tag
  - 顶部 4 stat strip (可选 · 每张 kicker + big value + delta + note · rail 色)
  - cascade section header
  - north-star hub (gold-rimmed pill · big serif value · italic sub)
  - 4 driver card 一字排开 (可 3-6 · kicker + name + big serif stat + trend +
    hair divider + `N LAGGING BELOW` kicker + colored 12-week sparkline + target dash)
  - hub → driver spokes (双 elbow · hue tinted)
  - driver → leaf spokes (双 elbow · hue tinted 0.55)
  - 12 leaf card (每 driver 2-4 leaf · rail top · kicker + serif value + unit +
    trend delta + mini spark + target dash + ON/OFF/WATCH label)
  - 右侧 sidebar narrative (可选 · 每 driver 1 card · 底部 WATCH callout)
  - 左下 legend (north-star / driver / leaf / ↑ / → / ↓ / spark)
  - 底部 how-to-read + method + read-order + figure caption

build_kpi_data kwargs:
    kicker / figure_title / figure_caption / source / fig_tag / fig_tag_note
    north_star: {label, value, delta, target, note}
    stat_strip: [{kicker, value, delta, delta_hue, note, hue}]  · 0-4 项 (None 用 baseline)
    drivers: [{
        key, kicker, label, value, hue,
        delta, delta_hue, target, health ("on"/"watch"/"off"), sparkline_delta,
        leaves: [{
            label, value, unit, delta, delta_hue,
            health ("on"/"watch"/"off"),
            trend ("up"/"down"/"flat"), spark_kind ("up"/"down"/"flat")
        }]  · 2-4 leaf
    }] · 3-6 driver
    sidebar: [{index, kicker, hue, value_line, body_lines}] · optional · 与 drivers 平行
    watch_callout: {kicker, body}  · optional
    legend_items: [{kind, hue, title, sub}]  · optional
    read_order: [str]  · optional (bottom 3 lines · How to read / Method / Read order)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..skins.editorial_atelier import (
    BONE_RUST, HUE, FONT_SANS, FONT_SERIF,
)
from ..skins.registry import get_active_skin as _get_active_skin
from ..skins._base import _fit_font_size


def _try_skin_draw(kind: str, x: float, y: float, w: float, h: float,
                   label: str, palette, **kwargs):
    """opt-in skin 分流. skin 返回 SVG 片段 → 用; 返回 None → fallback."""
    # KPI tree cards carry dense, data-bound labels; several global skins draw
    # dark card bodies or fixed gold rails while this preset owns the text
    # colors. Keep the KPI cards on the local high-contrast renderer so the
    # online Slides atomizer does not produce unreadable or mismatched cards.
    if kind.startswith("kpi_"):
        return None
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
# baseline data · 对齐 step1 kpi_hero_reference.svg
# ═════════════════════════════════════════════════════════════════

BASELINE_NORTH_STAR: Dict[str, Any] = {
    "label":  "Net ARR",
    "value":  "$12.4M",
    "kicker": "NORTH STAR · NET ARR",
    "note":   "target $50M by FY28 · MRR × 12 · net churn",
}

BASELINE_STAT_STRIP: List[Dict[str, Any]] = [
    {"kicker": "NET ARR (NORTH STAR)", "value": "$12.4M", "delta": "+8.6% QoQ",
     "delta_hue": "green_ok", "note": "vs plan $12.0M · pacing +3.3%",
     "hue": "ink"},
    {"kicker": "DRIVER · NEW ARR",     "value": "$3.2M",  "delta": "+14% QoQ",
     "delta_hue": "green_ok", "note": "3 lagging metrics inside · on-track",
     "hue": "rust"},
    {"kicker": "DRIVER · EXPANSION",   "value": "$1.4M",  "delta": "+22% QoQ",
     "delta_hue": "green_ok", "note": "NRR 112% · seat penetration climbing",
     "hue": "green"},
    {"kicker": "RISK · GROSS CHURN",   "value": "5.8%",   "delta": "+0.6pp QoQ",
     "delta_hue": "red_off",  "note": "above 5.0% guardrail · watch",
     "hue": "gold_p", "value_hue": "red_off"},
]

BASELINE_DRIVERS: List[Dict[str, Any]] = [
    {
        "key": "new_arr", "kicker": "DRIVER 1 · LEADING",
        "label": "New ARR", "value": "$3.2M", "hue": "rust",
        "delta": "↑ +14% · target $3.0M", "delta_hue": "green_ok",
        "health": "on", "sparkline_delta": -0.30,
        "leaves": [
            {"label": "MQL",       "value": "1,240", "unit": "/mo",
             "delta": "↑ +8%",  "delta_hue": "green_ok",
             "health": "on",    "trend": "up",   "spark_kind": "up"},
            {"label": "PIPELINE",  "value": "$18M",  "unit": "/qtr",
             "delta": "↑ +12%", "delta_hue": "green_ok",
             "health": "on",    "trend": "up",   "spark_kind": "up"},
            {"label": "WIN RATE",  "value": "27%",   "unit": "target 30",
             "delta": "→ flat", "delta_hue": "gold_p",
             "health": "watch", "trend": "flat", "spark_kind": "flat"},
        ],
    },
    {
        "key": "expansion", "kicker": "DRIVER 2 · LEADING",
        "label": "Expansion", "value": "$1.4M", "hue": "green",
        "delta": "↑ +22% · target $1.2M", "delta_hue": "green_ok",
        "health": "on", "sparkline_delta": -0.45,
        "leaves": [
            {"label": "NPS",       "value": "48",  "unit": "target 45",
             "delta": "↑ +4",   "delta_hue": "green_ok",
             "health": "on",    "trend": "up",   "spark_kind": "up"},
            {"label": "SEAT PEN.", "value": "62%", "unit": "target 55",
             "delta": "↑ +7pp", "delta_hue": "green_ok",
             "health": "on",    "trend": "up",   "spark_kind": "up"},
            {"label": "TIER UP",   "value": "18%", "unit": "target 15",
             "delta": "↑ +3pp", "delta_hue": "green_ok",
             "health": "on",    "trend": "up",   "spark_kind": "up"},
        ],
    },
    {
        "key": "retention", "kicker": "DRIVER 3 · LEADING",
        "label": "Retention", "value": "94.2%", "hue": "blue",
        "delta": "→ flat · target 95%", "delta_hue": "gold_p",
        "health": "watch", "sparkline_delta": 0.0,
        "leaves": [
            {"label": "NRR",     "value": "112%", "unit": "target 110",
             "delta": "↑ +2pp", "delta_hue": "green_ok",
             "health": "on",    "trend": "up",   "spark_kind": "up"},
            {"label": "TICKETS", "value": "980",  "unit": "/mo · cap 850",
             "delta": "↑ +8%",  "delta_hue": "red_off",
             "health": "off",   "trend": "up",   "spark_kind": "up-bad"},
            {"label": "TTV",     "value": "6.2d", "unit": "target 7d",
             "delta": "↓ -0.8d","delta_hue": "green_ok",
             "health": "on",    "trend": "down", "spark_kind": "down"},
        ],
    },
    {
        "key": "pipeline", "kicker": "DRIVER 4 · LEADING",
        "label": "Pipeline health", "value": "$18M", "hue": "gold_p",
        "delta": "↑ +9% · target $16M", "delta_hue": "green_ok",
        "health": "on", "sparkline_delta": -0.30,
        "leaves": [
            {"label": "COVERAGE",   "value": "5.6×", "unit": "target 4×",
             "delta": "↑ +0.4×", "delta_hue": "green_ok",
             "health": "on",     "trend": "up",   "spark_kind": "up"},
            {"label": "STG-2 CVR", "value": "22%", "unit": "target 28",
             "delta": "↓ -4pp",  "delta_hue": "red_off",
             "health": "off",    "trend": "down", "spark_kind": "up-bad"},
            {"label": "AGE (DAYS)","value": "42d", "unit": "target <45d",
             "delta": "↓ -3d",   "delta_hue": "green_ok",
             "health": "on",     "trend": "down", "spark_kind": "down"},
        ],
    },
]

BASELINE_SIDEBAR: List[Dict[str, Any]] = [
    {"index": "01", "kicker": "01 · NEW ARR",         "hue": "rust",
     "value_line": "$3.2M · 26% of net ARR",
     "body_lines": [
         "Marketing MQL and pipeline creation both",
         "above plan; win-rate flat at 27% remains",
         "the constraint — enablement focus in Q4.",
     ]},
    {"index": "02", "kicker": "02 · EXPANSION",       "hue": "green",
     "value_line": "$1.4M · fastest-growing driver",
     "body_lines": [
         "NPS 48 (+4), seat penetration 62% (+7pp),",
         "tier upgrade 18% (+3pp) — the product-led",
         "flywheel is firing on all three cylinders.",
     ]},
    {"index": "03", "kicker": "03 · RETENTION",       "hue": "blue",
     "value_line": "94.2% · under 95% guardrail",
     "body_lines": [
         "Ticket volume up 8% breaches cap; TTV",
         "improved to 6.2d and NRR at 112% cushion",
         "the number — success playbook rolls in Q4.",
     ]},
    {"index": "04", "kicker": "04 · PIPELINE HEALTH", "hue": "gold_p",
     "value_line": "$18M · 5.6× next-quarter target",
     "body_lines": [
         "Coverage healthy but stage-2 conversion",
         "dipped to 22% — pipeline quality review",
         "scheduled for mid-quarter checkpoint.",
     ]},
]

BASELINE_WATCH: Dict[str, Any] = {
    "kicker": "WATCH · GROSS CHURN 5.8%",
    "body":   "above 5.0% guardrail — 3 enterprise renewals slipping into Q4",
}

BASELINE_LEGEND: List[Dict[str, Any]] = [
    {"kind": "swatch",     "hue": "gold_hub", "title": "north-star",   "sub": "outcome KPI"},
    {"kind": "swatch",     "hue": "rust",     "title": "driver KPI",   "sub": "leading indicator"},
    {"kind": "leaf-frame", "hue": "gray",     "title": "lagging leaf", "sub": "operational metric"},
    {"kind": "text",       "hue": "green_ok", "title": "↑ on target",  "sub": "Δ vs plan positive"},
    {"kind": "text",       "hue": "gold_p",   "title": "→ watch",      "sub": "flat vs plan"},
    {"kind": "text",       "hue": "red_off",  "title": "↓ off target", "sub": "Δ vs plan negative"},
    {"kind": "spark",      "hue": "ink",      "title": "spark",        "sub": "last 12wk · dashed target"},
]

BASELINE_READ_LINES: List[Tuple[str, str]] = [
    ("How to read.",
     "The tree fans down from one north-star KPI to leading drivers and lagging leaves. Each leaf shows value · unit · Δ vs plan · 12-week spark with a dashed target line. Green = on target, gold = watch, red = off target — a single glance reveals which branch of the cascade needs attention."),
    ("Method.",
     "Data pulled from Salesforce, Gainsight, and internal DWH · reporting date 2026-09-30 · pacing computed against FY26 board plan · illustrative values for the atelier reference."),
    ("Read order.",
     "① Net ARR headline · ② scan drivers left-to-right · ③ drop into a driver to inspect its leaves · ④ read the narrative sidebar for context and the watch callout at the bottom."),
]


# ═════════════════════════════════════════════════════════════════
# builder
# ═════════════════════════════════════════════════════════════════

def _has_cjk(txt: str) -> bool:
    """判定字符串是否含中日韩字符 (用于 i18n kicker 切换)."""
    if not txt:
        return False
    for ch in txt:
        code = ord(ch)
        if 0x3400 <= code <= 0x9FFF or 0x3000 <= code <= 0x30FF:
            return True
    return False


def _derive_stat_strip_from_drivers(
    drvs: List[Dict[str, Any]],
    north_star: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """当 user 只 override drivers 时 · 从 drivers 生成 stat strip.

    首张 = north_star · 其余 = 前 3 个 driver · 保证同语种.
    """
    out: List[Dict[str, Any]] = []
    ns_kicker = str(north_star.get("kicker", "NORTH STAR"))
    ns_label = str(north_star.get("label", ""))
    out.append({
        "kicker": ns_kicker,
        "value":  str(north_star.get("value", "")),
        "delta":  "",
        "delta_hue": "green_ok",
        "note":   str(north_star.get("note", "")),
        "hue":    "ink",
    })
    for d in drvs[:3]:
        health = d.get("health", "on")
        d_hue = {"on": "green_ok", "watch": "gold_p", "off": "red_off"}.get(
            health, "green_ok"
        )
        # R3 · 拆 delta 长串: `↑ +16% · target $3.6M` → delta='↑ +16%' + note='target $3.6M'
        # 避免 stat-strip chip 上 value + delta 挤在同一行 (right-anchored delta 尾巴太长会撞上 left-anchored value)
        delta_raw = str(d.get("delta", ""))
        if " · " in delta_raw:
            d_head, _, d_tail = delta_raw.partition(" · ")
            delta_out = d_head.strip()
            note_out = d_tail.strip()
        else:
            delta_out = delta_raw
            note_out = ""
        out.append({
            "kicker": str(d.get("kicker", "")) or f"DRIVER · {d.get('label','')}",
            "value":  str(d.get("value", "")),
            "delta":  delta_out,
            "delta_hue": d.get("delta_hue", d_hue),
            "note":   note_out,
            "hue":    d.get("hue", "rust"),
        })
    return out


def _derive_sidebar_from_drivers(
    drvs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """一个 driver 一张 sidebar card · 无 body body_lines (由 caller 补文案)."""
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(drvs):
        idx = f"{i+1:02d}"
        label = str(d.get("label", ""))
        kicker = str(d.get("kicker", ""))
        # kicker 若含 driver 序号则用它 · 否则合成 "{idx} · {LABEL}"
        card_kicker = kicker or f"{idx} · {label.upper()}"
        # R3 · delta 若含 " · target" · 只保留首段 · 避免 value_line 超长
        delta_raw = str(d.get("delta", ""))
        delta_short = delta_raw.split(" · ")[0].strip() if " · " in delta_raw else delta_raw
        out.append({
            "index": idx,
            "kicker": card_kicker,
            "hue": d.get("hue", "rust"),
            "value_line": f"{d.get('value','')} · {delta_short}".strip(" ·"),
            "body_lines": [],
        })
    return out


def build_kpi_data(
    north_star: Optional[Dict[str, Any]] = None,
    stat_strip: Optional[List[Dict[str, Any]]] = None,
    drivers: Optional[List[Dict[str, Any]]] = None,
    sidebar: Optional[List[Dict[str, Any]]] = None,
    watch_callout: Optional[Dict[str, Any]] = None,
    legend_items: Optional[List[Dict[str, Any]]] = None,
    read_lines: Optional[List[Tuple[str, str]]] = None,
    kicker: str = "",
    figure_title: str = "SaaS Series-B · KPI cascade",
    figure_caption: str = (
        "Net ARR $12.4M → $50M target · 1 north-star · 4 driver KPIs · "
        "12 lagging metrics · Q3 FY26 board review"
    ),
    source: str = "Figure 08 · KP · KPI cascade · dandelion reference",
    fig_tag: str = "FIGURE 08",
    fig_tag_note: str = "",
) -> Tree:
    """Build KPI cascade Tree.

    Params
    ------
    north_star: None ⇒ baseline. dict with keys {label, value, note}.
    stat_strip: None ⇒ 若 user 传了 drivers 则从 drivers 派生 (top-3 driver + north_star)·
                否则用 baseline. [] ⇒ 关闭 stat strip.
    drivers:    None ⇒ baseline. non-empty list required. 3-6 driver.
    sidebar:    None ⇒ 若 user 传了 drivers 则派生 (1 卡/driver · body 留空)·
                否则用 baseline. [] ⇒ 关闭 sidebar 面板.
    watch_callout: None ⇒ 若 user 传了 drivers 则空 · 否则 baseline. {} ⇒ 关闭 watch.
    legend_items: None ⇒ [] (chatter · 默认关). [] ⇒ 关闭 legend.
    read_lines:   None ⇒ [] (chatter · 默认关). [] ⇒ 关闭底部 read 段.

    schema 限制: drivers 3-6 · leaves 2-4 · drivers × leaves ≤ 14 (可渲染上限).
    """
    user_passed_drivers = drivers is not None
    ns = north_star if north_star is not None else BASELINE_NORTH_STAR
    drvs = drivers if drivers is not None else BASELINE_DRIVERS
    if not drvs:
        raise ValueError("build_kpi_data: `drivers` must be non-empty")
    if len(drvs) < 3 or len(drvs) > 6:
        raise ValueError(
            f"build_kpi_data: drivers count {len(drvs)} out of 3-6"
        )
    # H4 · schema hard cap · drivers × max_leaves 超过 15 layout 挤破
    total_leaves = sum(len(d.get("leaves") or []) for d in drvs)
    if total_leaves > 15:
        # 不 raise · 只 warn (兼容既有测试) · renderer 里会做视觉降级
        pass

    # H1 · stat_strip: user drivers → auto-derive · 否则 baseline
    if stat_strip is not None:
        strip = stat_strip
    elif user_passed_drivers:
        strip = _derive_stat_strip_from_drivers(drvs, ns)
    else:
        strip = BASELINE_STAT_STRIP

    # H5 · sidebar: user drivers → auto-derive (one card per driver)
    if sidebar is not None:
        sbar = sidebar
    elif user_passed_drivers:
        sbar = _derive_sidebar_from_drivers(drvs)
    else:
        sbar = BASELINE_SIDEBAR

    # H1 · watch_callout: user drivers → empty (baseline text is English SaaS)
    if watch_callout is not None:
        watch = watch_callout
    elif user_passed_drivers:
        watch = {}
    else:
        watch = BASELINE_WATCH

    # H7/H8 · legend / read_lines / fig_tag_note: 默认 chatter 关闭
    lgd = legend_items if legend_items is not None else []
    rls = read_lines if read_lines is not None else []

    root = TreeNode(
        id="root",
        label=str(ns.get("label", "")),
        sublabel=str(ns.get("value", "")),
        extra={
            "kicker": ns.get("kicker", "NORTH STAR"),
            "value":  ns.get("value", ""),
            "note":   ns.get("note", ""),
            "stat_strip": strip or None,
            "sidebar": sbar or None,
            "watch_callout": watch or None,
            "legend_items": lgd or None,
            "read_lines": rls or None,
            "fig_tag": fig_tag,
            "fig_tag_note": fig_tag_note,
        },
    )

    for i, d in enumerate(drvs):
        drv_key = d.get("key") or f"d{i}"
        drv_node = TreeNode(
            id=drv_key,
            label=str(d.get("label", "")),
            sublabel=str(d.get("value", "")),
            group=str(d.get("hue", "rust")),
            extra={
                "kicker": d.get("kicker", ""),
                "value":  d.get("value", ""),
                "delta":  d.get("delta", ""),
                "delta_hue": d.get("delta_hue", "green_ok"),
                "health": d.get("health", "on"),
                "sparkline_delta": d.get("sparkline_delta", -0.30),
            },
        )
        leaves = d.get("leaves") or []
        if len(leaves) < 2 or len(leaves) > 4:
            raise ValueError(
                f"driver `{drv_key}` has {len(leaves)} leaves; must be 2-4"
            )
        for j, leaf in enumerate(leaves):
            drv_node.children.append(TreeNode(
                id=f"{drv_key}_l{j}",
                label=str(leaf.get("label", "")),
                sublabel=str(leaf.get("value", "")),
                detail=str(leaf.get("unit", "")),
                group=str(d.get("hue", "rust")),
                extra={
                    "value": leaf.get("value", ""),
                    "unit":  leaf.get("unit", ""),
                    "delta": leaf.get("delta", ""),
                    "delta_hue": leaf.get("delta_hue", "green_ok"),
                    "health": leaf.get("health", "on"),
                    "trend": leaf.get("trend", "flat"),
                    "spark_kind": leaf.get("spark_kind", "flat"),
                },
            ))
        root.children.append(drv_node)

    return Tree(
        root=root,
        kicker=kicker,
        figure_title=figure_title,
        figure_caption=figure_caption,
        source=source,
        encoding_note="",
    )


# 向后兼容 · 老 API 名 (v1 用 build_kpi_tree; manifest 也用它)
def build_kpi_tree(**kwargs) -> Tree:
    return build_kpi_data(**kwargs)


HERO_KP_DATA = build_kpi_data()


# ═════════════════════════════════════════════════════════════════
# color · dandelion hue map (对齐 step1 reference RGB)
# ═════════════════════════════════════════════════════════════════

_DANDELION_HUE: Dict[str, str] = {
    "rust":     "rgba(163,96,80,1)",       # Driver 1 · NEW ARR
    "green":    "rgba(96,132,110,1)",      # Driver 2 · EXPANSION · on-target
    "blue":     "rgba(60,100,155,1)",      # Driver 3 · RETENTION
    "gold_p":   "rgba(190,145,80,1)",      # Driver 4 · PIPELINE / watch text
    "gold_hub": "rgba(214,166,80,1)",      # hub rim / north-star legend
    "green_ok": "rgba(96,132,110,1)",      # ↑ on-target color
    "red_off":  "rgba(180,60,60,1)",       # ↓ off-target color
    "ink":      "rgba(30,32,38,1)",
    "ink_dim":  "rgba(70,74,82,1)",
    "gray":     "rgba(120,124,132,1)",
    "gray_hair":"rgba(170,174,182,1)",
    "paper":    "rgba(250,248,242,1)",
    "olive":    "rgba(94,80,62,1)",
    "magenta":  "rgba(105,75,130,1)",
    "orange":   "rgba(163,96,80,1)",       # alias for rust
    "navy":     "rgba(28,34,52,1)",
    "slate":    "rgba(68,78,100,1)",
    "cinnamon": "rgba(178,144,72,1)",
}

_KPI_CHROME_HUE: Dict[str, str] = {
    "ink":       "rgba(24,30,40,1)",
    "ink_dim":   "rgba(67,75,88,1)",
    "gray":      "rgba(98,104,114,1)",
    "gray_hair": "rgba(42,48,58,0.30)",
    "paper":     "rgba(252,250,244,1)",
}


def _estimate_text_width(txt: str, font_size: float) -> float:
    """Atomizer-aligned rough width estimate for collision decisions."""
    width = 0.0
    for ch in str(txt or ""):
        code = ord(ch)
        if ch.isspace():
            width += font_size * 0.30
        elif 0x3400 <= code <= 0x9FFF or 0x3000 <= code <= 0x30FF:
            width += font_size * 0.92
        elif ch.isupper() or ch.isdigit():
            width += font_size * 0.62
        elif ch in "/:-_.·×%+<>":
            width += font_size * 0.38
        else:
            width += font_size * 0.52
    return width


def _clip_text_to_width(txt: str, max_width: float, font_size: float) -> str:
    """Hard-clip overlong single-line text before it reaches adjacent labels."""
    text = str(txt or "")
    if not text or _estimate_text_width(text, font_size) <= max_width:
        return text
    out = ""
    for ch in text:
        nxt = out + ch
        if _estimate_text_width(nxt, font_size) > max_width:
            break
        out = nxt
    return out or text[:1]


def _hex_to_rgba(c: str, alpha: float = 1.0) -> str:
    """#RRGGBB → rgba(r,g,b,alpha) · 已是 rgba(...) 直返."""
    if c.startswith("#"):
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha:.3f})"
    if c.startswith("rgba"):
        # 替换 alpha
        m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", c)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
    return c


def _skin_chrome_rgba(role: str, alpha: float = 1.0) -> str:
    """Resolve KPI-local chrome colors (ink / ink_dim / paper / gray / gray_hair).

    KPI embeds sit on their own light paper surface. Letting dark skins override
    these roles can make title/section text nearly invisible after atomization.
    """
    if role in _KPI_CHROME_HUE:
        return _hex_to_rgba(_KPI_CHROME_HUE[role], alpha)
    skin = _get_active_skin()
    pal = getattr(skin, "PALETTE", None) if skin is not None else None
    if pal is not None:
        if role == "ink":
            return _hex_to_rgba(pal.ink, alpha)
        if role == "ink_dim":
            # ink 加一点透明 → 次要 ink
            return _hex_to_rgba(pal.ink, alpha * 0.72)
        if role == "paper":
            return _hex_to_rgba(pal.bg, alpha)
        if role == "gray":
            g = getattr(pal, "gray", None)
            if g:
                return _hex_to_rgba(g, alpha) if not g.startswith("rgba") else g.replace("0.72", f"{alpha:.3f}")
        if role == "gray_hair":
            # hair 通常与 ink 同色但更淡
            hair = getattr(pal, "hair", None) or pal.ink
            return _hex_to_rgba(hair, alpha * 0.35)
    # fallback → dandelion
    if role in _DANDELION_HUE:
        return _hex_to_rgba(_DANDELION_HUE[role], alpha) if _DANDELION_HUE[role].startswith("#") else _hex_to_rgba(_DANDELION_HUE[role], alpha)
    return _DANDELION_HUE.get(role, "rgba(30,32,38,1.000)")


def _hue_str(name: str, alpha: float = 1.0) -> str:
    """Resolve hue name → rgba() str with alpha.

    chrome 角色 (ink/ink_dim/paper/gray/gray_hair) 走 skin-aware 通道 (H3 fix)·
    其余走 dandelion + editorial_atelier HUE.
    """
    # H3 · chrome 角色 · 跟着 active skin 走
    if name in {"ink", "ink_dim", "paper", "gray", "gray_hair"}:
        return _skin_chrome_rgba(name, alpha)
    if name in _DANDELION_HUE:
        base = _DANDELION_HUE[name]
        m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", base)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
        if base.startswith("#"):
            return _hex_to_rgba(base, alpha)
        return base
    c = HUE.get(name, HUE.get("rust", "#A35832"))
    if c.startswith("#"):
        h = c.lstrip("#")
        r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha:.3f})"
    return c


def _health_hue(health: str) -> str:
    return {"on": "green_ok", "watch": "gold_p", "off": "red_off"}.get(
        health, "green_ok"
    )


def _health_label(health: str) -> str:
    return {"on": "ON TARGET", "watch": "WATCH", "off": "OFF TARGET"}.get(
        health, "ON TARGET"
    )


def _health_label_short(health: str) -> str:
    """2026-09-13 P0 · 3-char 徽章 · 窄 leaf card (< 90px slide) 用 · 防截断.

    ON / WT / OFF · 单色由 _health_hue 提供 (green_ok / gold_p / red_off).
    与 _health_label 语义等价 · 视觉极简.
    """
    return {"on": "ON", "watch": "WT", "off": "OFF"}.get(health, "ON")


# ═════════════════════════════════════════════════════════════════
# layout params
# ═════════════════════════════════════════════════════════════════

@dataclass
class KPIHeroParams:
    # canvas
    view_w: float = 1400
    view_h: float = 720
    # chrome
    chrome_pad: float = 60
    title_y: float = 50
    caption_y: float = 78
    hair_y: float = 96
    fig_tag_y: float = 116
    # stat strip
    strip_y: float = 128
    strip_h: float = 80
    strip_gap: float = 10
    # section header
    section_header_y: float = 232
    # cascade tree bbox (left of sidebar)
    tree_x0: float = 60
    tree_x1: float = 870      # sidebar starts at ~884
    hub_y: float = 236
    hub_h: float = 84
    hub_w: float = 300
    driver_y: float = 348
    driver_h: float = 132
    leaf_y: float = 500
    leaf_h: float = 118
    # sidebar
    sidebar_x: float = 900
    sidebar_w: float = 424
    sidebar_hair_x: float = 884
    sidebar_hair_y0: float = 218
    sidebar_hair_y1: float = 640
    sidebar_top_kicker_y: float = 236
    sidebar_top_sub_y: float = 254
    sidebar_card_y0: float = 268
    sidebar_card_h: float = 88
    sidebar_card_gap: float = 8
    sidebar_watch_h: float = 42
    # legend
    legend_y: float = 596
    # footer
    footer_hair_y: float = 654
    footer_line1_y: float = 670
    footer_line2_y: float = 688
    footer_line3_y: float = 706
    footer_caption_y: float = 714


# ═════════════════════════════════════════════════════════════════
# layout compute · 数据自适应 driver × leaf slot 计算
# ═════════════════════════════════════════════════════════════════

def _compute_positions(
    data: Tree,
    p: KPIHeroParams,
    *,
    has_sidebar: bool,
    has_stat_strip: bool,
    force_compact: bool = False,
) -> Dict[str, Any]:
    """Compute all key positions · driver/leaf slot 均分.

    Collision guard: 若 has_sidebar 且 driver 数 ≥ 6 · driver row 与 sidebar 会撞.
    此时自动关掉 sidebar · 让 tree 拉宽到 1340 · sidebar_active=False 返回给 renderer.
    (dense 变体的典型 fix · sparse/baseline 保持 sidebar.)

    force_compact: R4 fix (2026-09-13) · L3 subtract 下强制 compact 纵向堆叠
    (无视 drv_w) · 使每 leaf 拿满 driver_w · 单行 label·value·health · 15+ leaf
    时视觉密度显著下降. L0 传 False · 保持横排宽卡 + sparkline 视觉水准.
    """
    drivers = list(data.root.children)
    n_drv = len(drivers)

    # collision guard: 6+ driver + sidebar → sidebar 让位给 tree
    sidebar_active = has_sidebar and n_drv < 6

    # tree body 右边界 · 若无 sidebar 或 sidebar_active 关掉 · 拉宽到 1340
    tree_x0 = p.tree_x0
    tree_x1 = p.tree_x1 if sidebar_active else 1340.0

    tree_w = tree_x1 - tree_x0
    # When the L3 variant removes the top stat strip, pull the cascade upward
    # so the headline band is not followed by a large unused void.
    no_strip_y_shift = 56.0 if not has_stat_strip else 0.0
    driver_y = p.driver_y - no_strip_y_shift
    leaf_y = p.leaf_y - no_strip_y_shift
    # driver card + gap
    drv_gap = 10.0
    drv_w = (tree_w - drv_gap * (n_drv - 1)) / n_drv
    # min 140 保底 (baseline / sparse 都能满足)
    # dense 6 driver · tree_w=1280 · drv_w=(1280-50)/6=205 ok
    drv_w = max(drv_w, 140.0)
    drv_xs = [tree_x0 + i * (drv_w + drv_gap) for i in range(n_drv)]

    # leaf: 每 driver 内 · 均分 driver_w
    # H4 · 当 driver_w 不足以放宽卡 (< 200px) · 改为 vertical stack (1 col × N rows)
    # 让每片叶子拿满 driver_w · 用 compact "text row" 样式 (label · value · health) 一行显示
    leaf_positions: List[List[Dict[str, Any]]] = []
    max_wrapped_rows = 1
    for i, d in enumerate(drivers):
        leaves = list(d.children)
        n_leaf = len(leaves)
        drv_x = drv_xs[i]
        # 决定 layout · 宽卡 (dw ≥ 200) 时横排 · 窄卡时纵向堆叠 compact rows
        # R4 (2026-09-13): L3 subtract 下强制 compact · 无视 drv_w · 15+ leaf
        # 场景下每 leaf 拿满 driver_w · 密度下降 · 目标 A ≥ 4
        compact = force_compact or (drv_w < 200.0)
        if compact:
            cols = 1
            rows = n_leaf
        else:
            cols = n_leaf
            rows = 1
        if compact:
            # 纵向 · 每行拿满 driver_w · 高度按 leaf_h / n_leaf 均分
            # R4 · min 从 24 → 28 · 给单行 label·value·health 足够 vertical breathing
            leaf_w = drv_w
            row_h = max(28.0, p.leaf_h / max(n_leaf, 1))
            leaf_gap_y = 5.0
        else:
            leaf_gap_x = 6.0
            leaf_w = (drv_w - leaf_gap_x * (cols - 1)) / cols
            row_h = p.leaf_h
            leaf_gap_y = 0.0
        max_wrapped_rows = max(max_wrapped_rows, rows)
        leaf_row: List[Dict[str, Any]] = []
        for j, leaf in enumerate(leaves):
            col = j % cols
            row = j // cols
            if compact:
                lx = drv_x
                ly = leaf_y + row * (row_h + leaf_gap_y)
            else:
                lx = drv_x + col * (leaf_w + leaf_gap_x)
                ly = leaf_y + row * (row_h + 6.0)
            leaf_row.append({
                "x": lx, "y": ly, "w": leaf_w, "h": row_h,
                "cx": lx + leaf_w / 2,
                "node": leaf,
                "driver_i": i, "leaf_j": j,
                "row": row, "col": col,
                "wrap_rows": rows, "wrap_cols": cols,
                "compact": compact,
            })
        leaf_positions.append(leaf_row)

    # hub center: 位于全部 driver 的中心带 (居中 · 但避免与 sidebar 冲突)
    # 参考 SVG · hub cx=475 · 恰是 driver cluster (60..870) 的中心 (465) 附近
    tree_cx = tree_x0 + tree_w / 2
    hub_x = tree_cx - p.hub_w / 2
    hub_y = p.hub_y - no_strip_y_shift

    # stat strip: 顶部 4 项 · 均分
    strip_positions: List[Dict[str, Any]] = []
    if has_stat_strip:
        strip_items = data.root.extra.get("stat_strip") or []
        n_strip = len(strip_items)
        if n_strip > 0:
            avail = 1400.0 - 60.0 * 2  # full page - 2×60 pad
            gap = p.strip_gap
            item_w = (avail - gap * (n_strip - 1)) / n_strip
            for k, it in enumerate(strip_items):
                sx = 60.0 + k * (item_w + gap)
                strip_positions.append({
                    "x": sx, "y": p.strip_y, "w": item_w, "h": p.strip_h,
                    "item": it,
                })

    return {
        "hub":    {"x": hub_x, "y": hub_y, "w": p.hub_w, "h": p.hub_h,
                   "cx": hub_x + p.hub_w / 2, "cy": hub_y + p.hub_h / 2},
        "drivers": [
            {"x": drv_xs[i], "y": driver_y, "w": drv_w, "h": p.driver_h,
             "cx": drv_xs[i] + drv_w / 2, "node": drivers[i], "i": i}
            for i in range(n_drv)
        ],
        "leaves": leaf_positions,
        "strip":  strip_positions,
        "tree_x0": tree_x0, "tree_x1": tree_x1, "tree_w": tree_w,
        "sidebar_active": sidebar_active,
        "max_wrapped_rows": max_wrapped_rows,
    }


# ═════════════════════════════════════════════════════════════════
# helpers · sparkline path generation
# ═════════════════════════════════════════════════════════════════

def _spark_path(x0: float, y0: float, w: float, h: float,
                kind: str = "up") -> str:
    """12-week sparkline · returns polyline points string."""
    n = 12
    step = w / (n - 1)
    # target line at mid-y; polyline moves per kind
    pts: List[Tuple[float, float]] = []
    if kind == "up":
        # 缓上升 · 尾端最高
        for i in range(n):
            t = i / (n - 1)
            y = y0 + h * (0.75 - 0.60 * t)
            pts.append((x0 + i * step, y))
    elif kind == "down":
        # 缓下降 · 尾端最低
        for i in range(n):
            t = i / (n - 1)
            y = y0 + h * (0.20 + 0.55 * t)
            pts.append((x0 + i * step, y))
    elif kind == "up-bad":
        # 上升但染红 · 用于超标情况
        for i in range(n):
            t = i / (n - 1)
            y = y0 + h * (0.75 - 0.55 * t)
            pts.append((x0 + i * step, y))
    else:
        # flat · 微波动
        for i in range(n):
            t = i / (n - 1)
            y = y0 + h * 0.5 + ((i % 2) - 0.5) * 2
            pts.append((x0 + i * step, y))
    return " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)


def _leaf_spark_path(x0: float, y0: float, w: float, h: float,
                     kind: str = "up") -> str:
    """mini sparkline for leaf card (fewer points, smaller amplitude)."""
    n = 9
    step = w / (n - 1)
    pts: List[Tuple[float, float]] = []
    if kind == "up":
        for i in range(n):
            t = i / (n - 1)
            y = y0 + h * (0.75 - 0.60 * t)
            pts.append((x0 + i * step, y))
    elif kind == "down":
        for i in range(n):
            t = i / (n - 1)
            y = y0 + h * (0.20 + 0.60 * t)
            pts.append((x0 + i * step, y))
    elif kind == "up-bad":
        for i in range(n):
            t = i / (n - 1)
            y = y0 + h * (0.80 - 0.55 * t)
            pts.append((x0 + i * step, y))
    else:
        for i in range(n):
            y = y0 + h * 0.5 + ((i % 2) - 0.5) * 1.5
            pts.append((x0 + i * step, y))
    return " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)


# ═════════════════════════════════════════════════════════════════
# render
# ═════════════════════════════════════════════════════════════════

VIEW_W = 1400
VIEW_H = 720
BG_COLOR = "rgba(250,248,242,1)"


# Bucket H (2026-09-13) · subtract_level default "L3" (极简)
# NOTE: kp_kpi self-contained · 未走 layout kind · skip_kinds 不生效 (API 兼容占位 · 需 P0 改造)
_SUBTRACT_L0: List[str] = []
_SUBTRACT_L1: List[str] = ["swatch"]
_SUBTRACT_L2: List[str] = ["swatch"]
_SUBTRACT_L3: List[str] = ["swatch", "spark"]
_SUBTRACT_MAP = {"L0": _SUBTRACT_L0, "L1": _SUBTRACT_L1,
                 "L2": _SUBTRACT_L2, "L3": _SUBTRACT_L3}


def _resolve_skip_kinds(skip_kinds: Optional[List[str]], subtract_level: str) -> set:
    if skip_kinds is not None:
        return set(skip_kinds)
    return set(_SUBTRACT_MAP.get(subtract_level, _SUBTRACT_L3))


def render_hero_embed_kp_kpi_v2(
    data: Tree = HERO_KP_DATA,
    palette: Palette = BONE_RUST,
    params: Optional[KPIHeroParams] = None,
    *,
    subtract_level: str = "L3",
    skip_kinds: Optional[List[str]] = None,
) -> str:
    """Render KPI cascade hero embed (1400×720).

    弹性维度:
        * drivers: 3-6
        * leaves per driver: 2-4
        * stat_strip: 0-4 (None ⇒ baseline)
        * sidebar: 可关 ([]) · 布局自动拉宽 tree
        * watch_callout: 可关
        * legend / read_lines: 可关
    """

    # [SKIN-PATCH-L1] globals patch: skin.PALETTE 覆写模块级色常量
    _MOD_L1 = globals()
    _ORIG_L1 = {k: _MOD_L1[k] for k in ("BG_COLOR",)}
    _SKIN_L1 = _get_active_skin()
    if _SKIN_L1 is not None:
        _SP_L1 = getattr(_SKIN_L1, 'PALETTE', None)
        if _SP_L1 is not None:
            if getattr(_SP_L1, 'bg', None): _MOD_L1['BG_COLOR'] = _SP_L1.bg
    # [FONT-PATCH-L1] font pass-through: editorial_atelier.FONT_SANS/SERIF 覆写
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
        p = params or KPIHeroParams()
        pal = palette or BONE_RUST
        root = data.root
        root_extra = getattr(root, "extra", {}) or {}

        # Bucket H (2026-09-13) · subtract_level 默认 L3 · 清空次要说明字段
        # kp_kpi self-contained · 不走 layout kind · 走 kwarg deepcopy 派
        # L1: 清 fig_tag_note / legend_items / read_lines / kicker
        # L2: L1 + sidebar / watch_callout / stat_strip.note / figure_caption
        # L3: L2 + fig_tag + north_star.note (root.extra.note) + leaf caps
        if subtract_level and subtract_level != "L0":
            import copy as _copy
            data = _copy.deepcopy(data)
            root = data.root
            root_extra = getattr(root, "extra", {}) or {}
            if subtract_level in ("L1", "L2", "L3"):
                root_extra["fig_tag_note"] = ""
                root_extra["legend_items"] = None
                root_extra["read_lines"] = None
                try:
                    data.kicker = ""
                except Exception:
                    pass
            if subtract_level in ("L2", "L3"):
                root_extra["sidebar"] = None
                root_extra["watch_callout"] = None
                try:
                    data.figure_caption = ""
                    data.source = ""
                except Exception:
                    pass
            if subtract_level == "L3":
                root_extra["fig_tag"] = ""
                root_extra["note"] = ""
                root_extra["stat_strip"] = None
            root.extra = root_extra

        has_sidebar = bool(root_extra.get("sidebar"))
        has_stat_strip = bool(root_extra.get("stat_strip"))

        # R4 (2026-09-13) · L3 且 leaf 密度大 (≥12) 时强制 compact vertical stack
        # 15-20 leaf 场景每 leaf 拿满 driver_w · 密度显著下降 · 目标 A ≥ 4
        # 稀疏数据 (<12 leaf) 保持既有 wide-card render · 不牺牲信息颗粒
        # L0 恒不强制 · 保持信息完整度 (sparkline / delta / unit 全展示)
        _total_leaves = sum(len(d.children) for d in root.children)
        _force_compact = (subtract_level == "L3") and (_total_leaves >= 12)

        positions = _compute_positions(
            data, p, has_sidebar=has_sidebar, has_stat_strip=has_stat_strip,
            force_compact=_force_compact,
        )
        # collision guard 可能关掉 sidebar (6+ driver) · 用 effective 值渲染
        has_sidebar = positions["sidebar_active"]

        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {VIEW_H}">',
        ]
        # defs · hub gradient only · 2026-09-13 P0 fix: 移除 kp-paperGrid pattern
        # · 之前 pattern url fill 走 _wrap_svg_embed 嵌入 slide 时 · shrink/rotate
        # 相关变换让 pattern 的 tile 出现大菱形 artifact 覆盖内容 · 换纯色 fill 稳定
        _paper_bg = _skin_chrome_rgba("paper")  # skin-aware 底色
        parts.append('<defs>')
        parts.append(
            '<radialGradient id="kp-hub-grad" cx="35%" cy="30%" r="70%">'
            '<stop offset="0%" stop-color="rgba(214,166,80,0.95)"/>'
            '<stop offset="100%" stop-color="rgba(190,140,60,0.65)"/>'
            '</radialGradient>'
        )
        parts.append('</defs>')

        # background · plain paper fill (无 dot pattern · 避免 atomize embed artifact)
        parts.append(
            f'<rect width="{VIEW_W}" height="{VIEW_H}" fill="{_paper_bg}"/>'
        )
        # H3 · 额外一层 "content paper" · 严格 < 90% 视口面积 · 避免被 shrink_bg / drop_bg 认成满版底
        # 让 preset 在任何 slide bg 下都有自己的 paper 底 · 深底 slide 也读得到文字
        # R3: 上延至 y=30 覆盖 figure_title (y_title=50) / caption (y=78) / hair (y=96) / fig_tag (y=116)
        # 保证 boardroom_navy 等深底 skin 上 chrome 文字仍在 paper 上可读
        _paper = _hue_str("paper")
        # 内缩 60 px 水平 · 30 px 顶部 · 40 px 底部
        # 覆盖率: (1400-120)*(720-70) / (1400*720) = 1280*650 / 1008000 = 82.5% < 90%
        _paper_inset_x = 60.0
        _paper_inset_y = 30.0  # R3: 从 100 改到 30 · 覆盖 title/caption/hair/fig_tag 区
        # R3 fix (2026-09-13 · kp_kpi): audit reports 背景大菱形水印仍残留 · 疑为
        # atomize embed 时 rounded-rect (rx=6) 大矩形被识别为菱形形状 artifact. 拆成
        # 4 条 hairline 边框 + 单独 fill rect (无 rx) · atomize 不再合成菱形.
        _paper_x = _paper_inset_x
        _paper_y = _paper_inset_y
        _paper_w = VIEW_W - 2 * _paper_inset_x
        _paper_h = VIEW_H - _paper_inset_y - 40
        parts.append(
            f'<rect x="{_paper_x}" y="{_paper_y}" '
            f'width="{_paper_w:.1f}" height="{_paper_h:.1f}" '
            f'fill="{_paper}"/>'
        )
        # No visible frame: online Slides screenshots showed this hairline as an
        # unintended gray box around the chart.

        # ─── chrome ───
        title = data.figure_title or ""
        caption = data.figure_caption or ""
        _cn_context = _has_cjk(title) or _has_cjk(caption)
        if title:
            parts.append(
                f'<text x="60" y="{p.title_y}" font-family="{FONT_SERIF}" '
                f'font-size="30" font-weight="700" fill="{_hue_str("ink")}" '
                f'letter-spacing="0.1">{esc(title)}</text>'
            )
        if caption:
            parts.append(
                f'<text x="60" y="{p.caption_y}" font-family="{FONT_SANS}" '
                f'font-size="18" fill="{_hue_str("ink_dim")}" '
                f'letter-spacing="0.2">{esc(caption)}</text>'
            )
        parts.append(
            f'<line x1="60" y1="{p.hair_y}" x2="1340" y2="{p.hair_y}" '
            f'stroke="{_hue_str("ink")}" stroke-width="0.8"/>'
        )
        fig_tag = root_extra.get("fig_tag", "")
        fig_tag_note = root_extra.get("fig_tag_note", "")
        if fig_tag:
            parts.append(
                f'<text x="60" y="{p.fig_tag_y}" font-family="{FONT_SANS}" '
                f'font-size="17" font-weight="700" fill="{_hue_str("ink_dim")}" '
                f'letter-spacing="1.5">{esc(fig_tag)}</text>'
            )
        if fig_tag_note:
            parts.append(
                f'<text x="170" y="{p.fig_tag_y}" font-family="{FONT_SANS}" '
                f'font-size="17" fill="{_hue_str("gray")}" '
                f'letter-spacing="0.4">{esc(fig_tag_note)}</text>'
            )

        # ─── stat strip (0-4 项) ───
        for sp in positions["strip"]:
            it = sp["item"]
            sx, sy, sw, sh = sp["x"], sp["y"], sp["w"], sp["h"]
            rail_hue = it.get("hue", "ink")
            value_hue = it.get("value_hue", None)  # for RISK cases (red value)
            value_color = _hue_str(value_hue) if value_hue else _hue_str(rail_hue if rail_hue != "ink" else "ink")
            parts.append(
                f'<rect x="{sx:.1f}" y="{sy}" width="{sw:.1f}" height="{sh}" '
                f'fill="{_hue_str("paper")}" stroke="{_hue_str("gray_hair")}" '
                f'stroke-width="0.8"/>'
            )
            parts.append(
                f'<rect x="{sx:.1f}" y="{sy}" width="4" height="{sh}" '
                f'fill="{_hue_str(rail_hue)}"/>'
            )
            kicker_txt = it.get("kicker", "")
            # shorten kicker if too long for chip (avoid overlap with neighbour chip)
            if sw < 320.0 and len(kicker_txt) > 20:
                if "·" in kicker_txt:
                    kicker_txt = kicker_txt.split("·")[0].strip()
            fs_k, kt = _fit_font_size(kicker_txt, sw - 24, 17.0, min_size=17.0)
            kt = _clip_text_to_width(kt, sw - 30, fs_k)
            parts.append(
                f'<text x="{sx + 16:.1f}" y="{sy + 22}" font-family="{FONT_SANS}" '
                f'font-size="{fs_k:.1f}" fill="{_hue_str("gray")}" '
                f'font-weight="700" letter-spacing="0.06em">{esc(kt)}</text>'
            )
            # big value · 值和 delta 分行显示 (避免撞)
            val_txt = it.get("value", "")
            fs_v, vt = _fit_font_size(val_txt, sw - 24, 24.0, min_size=18.0)
            vt = _clip_text_to_width(vt, sw - 54, fs_v)
            parts.append(
                f'<text x="{sx + 16:.1f}" y="{sy + 52}" font-family="{FONT_SERIF}" '
                f'font-size="{fs_v:.1f}" font-weight="800" fill="{value_color}">'
                f'{esc(vt)}</text>'
            )
            # delta (right of value, same line) · 只在有空间时显示
            d_txt = it.get("delta", "")
            d_hue = it.get("delta_hue", "green_ok")
            if d_txt:
                # R3 · 精确估算 value 末端 x + delta 长度 · 保证至少 12px 视觉 gap
                val_est_w = len(vt) * fs_v * 0.5
                val_end_x = sx + 16 + val_est_w
                delta_est_w = len(d_txt) * 16 * 0.5  # sans 16pt
                delta_start_x = (sx + sw - 12) - delta_est_w
                gap = delta_start_x - val_end_x
                if gap >= 12.0:
                    parts.append(
                        f'<text x="{sx + sw - 12:.1f}" y="{sy + 52}" '
                        f'text-anchor="end" font-family="{FONT_SANS}" '
                        f'font-size="17" font-weight="700" '
                        f'fill="{_hue_str(d_hue)}">{esc(d_txt)}</text>'
                    )
                elif gap >= 4.0:
                    # 紧但可挤 · 强制加 " · " 前缀作为视觉分隔
                    parts.append(
                        f'<text x="{sx + sw - 12:.1f}" y="{sy + 52}" '
                        f'text-anchor="end" font-family="{FONT_SANS}" '
                        f'font-size="17" font-weight="700" '
                        f'fill="{_hue_str(d_hue)}">· {esc(d_txt)}</text>'
                    )
                # 否则跳过 delta (太挤 · 避免撞 value)
            # note · body ≥ 16pt
            note_txt = it.get("note", "")
            # R3 · 窄 chip 时长 note (含 " · ") 会溢出 · 只保留首段
            if sw < 320.0 and " · " in note_txt and len(note_txt) > 20:
                note_txt = note_txt.split(" · ")[0].strip()
            fs_n, nt = _fit_font_size(
                note_txt, sw - 24, 17.0,
                min_size=17.0, char_w_ratio=0.48,
            )
            nt = _clip_text_to_width(nt, sw - 30, fs_n)
            parts.append(
                f'<text x="{sx + 16:.1f}" y="{sy + 72}" font-family="{FONT_SANS}" '
                f'font-size="{fs_n:.1f}" fill="{_hue_str("gray")}">'
                f'{esc(nt)}</text>'
            )

        # ─── cascade section header ─── (i18n: CN 时切中文)
        _section_hdr = "KPI 拆解树" if _cn_context else "KPI CASCADE TREE"
        _section_sub = (
            "北极星 → 驱动 → 前置指标 · 近 12 周走势"
            if _cn_context else
            "north-star → drivers → lagging leaves · last-12-wk trend"
        )
        _section_y = p.section_header_y if has_stat_strip else 150.0
        parts.append(
            f'<text x="60" y="{_section_y}" font-family="{FONT_SANS}" '
            f'font-size="17" font-weight="700" fill="{_hue_str("ink")}" '
            f'letter-spacing="1.4">{esc(_section_hdr)}</text>'
        )
        parts.append(
            f'<text x="320" y="{_section_y}" font-family="{FONT_SANS}" '
            f'font-size="17" fill="{_hue_str("gray")}" letter-spacing="0.3">'
            f'{esc(_section_sub)}</text>'
        )

        # ─── hub → driver spokes (before hub, so hub sits on top) ───
        hub = positions["hub"]
        hub_bottom_x = hub["cx"]
        hub_bottom_y = hub["y"] + hub["h"] + 2  # from bottom of hub
        for drv in positions["drivers"]:
            hue = drv["node"].group or "rust"
            target_x = drv["cx"]
            target_y = drv["y"] - 2
            elbow_y = hub_bottom_y + 18
            parts.append(
                f'<path d="M {hub_bottom_x:.1f} {hub_bottom_y:.1f} '
                f'V {elbow_y:.1f} H {target_x:.1f} V {target_y:.1f}" '
                f'fill="none" stroke="{_hue_str(hue, 0.75)}" stroke-width="1.8" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )

        # hub shadow ellipse
        parts.append(
            f'<ellipse cx="{hub["cx"]:.1f}" cy="{hub["y"] + hub["h"] + 4:.1f}" '
            f'rx="{hub["w"] / 2:.1f}" ry="8" '
            f'fill="rgba(30,32,38,0.10)"/>'
        )

        # ─── hub (north-star) ───
        skin_svg = _try_skin_draw(
            "kpi_hub_card", hub["x"], hub["y"], hub["w"], hub["h"],
            "", pal, hue="gold_hub",
        )
        if skin_svg:
            parts.append(skin_svg)
        else:
            parts.append(
                f'<rect x="{hub["x"]:.1f}" y="{hub["y"]}" '
                f'width="{hub["w"]:.1f}" height="{hub["h"]}" rx="8" '
                f'fill="{_hue_str("paper")}" '
                f'stroke="{_hue_str("gold_hub")}" stroke-width="2.2"/>'
            )
            parts.append(
                f'<rect x="{hub["x"]:.1f}" y="{hub["y"]}" '
                f'width="{hub["w"]:.1f}" height="4" rx="2" '
                f'fill="{_hue_str("gold_hub")}"/>'
            )
        ns_kicker = root_extra.get("kicker", "NORTH STAR · NET ARR")
        parts.append(
            f'<text x="{hub["cx"]:.1f}" y="{hub["y"] + 24}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="17" font-weight="700" '
            f'fill="{_hue_str("gold_p")}" letter-spacing="0.24em">'
            f'{esc(ns_kicker)}</text>'
        )
        ns_value = root_extra.get("value", "") or root.sublabel
        fs_hv, tv = _fit_font_size(ns_value, hub["w"] - 24, 28.0, min_size=20.0)
        tv = _clip_text_to_width(tv, hub["w"] - 80, fs_hv)
        parts.append(
            f'<text x="{hub["cx"]:.1f}" y="{hub["y"] + 56}" text-anchor="middle" '
            f'font-family="{FONT_SERIF}" font-size="{fs_hv:.1f}" '
            f'font-weight="800" fill="{_hue_str("ink")}">{esc(tv)}</text>'
        )
        parts.append(
            f'<line x1="{hub["x"] + 24:.1f}" y1="{hub["y"] + 64}" '
            f'x2="{hub["x"] + hub["w"] - 24:.1f}" y2="{hub["y"] + 64}" '
            f'stroke="{_hue_str("gold_hub", 0.4)}" stroke-width="0.7"/>'
        )
        ns_note = root_extra.get("note", "")
        # R3 · 长 ns_note (含 " · ") 在 hub 里溢出 · 只保留首段
        if ns_note and " · " in ns_note and len(ns_note) > 24:
            ns_note = ns_note.split(" · ")[0].strip()
        if ns_note:
            fs_hn, tn = _fit_font_size(
                ns_note, hub["w"] - 20, 17.0,
                min_size=17.0, char_w_ratio=0.48,
            )
            parts.append(
                f'<text x="{hub["cx"]:.1f}" y="{hub["y"] + 80}" '
                f'text-anchor="middle" font-family="{FONT_SERIF}" '
                f'font-size="{fs_hn:.1f}" font-style="italic" '
                f'fill="rgba(70,74,82,0.75)">{esc(tn)}</text>'
            )

        # ─── driver → leaf spokes (before driver cards, so cards on top of their tops) ───
        for i, drv in enumerate(positions["drivers"]):
            leaves = positions["leaves"][i]
            hue = drv["node"].group or "rust"
            drv_bottom_x = drv["cx"]
            drv_bottom_y = drv["y"] + drv["h"]
            elbow_y = drv_bottom_y + 12
            for leaf_pos in leaves:
                # H4 · wrap 时只连 row 0 (top row) · 下面的行是堆叠不再画线
                if leaf_pos.get("row", 0) != 0:
                    continue
                tx = leaf_pos["cx"]
                ty = leaf_pos["y"]
                parts.append(
                    f'<path d="M {drv_bottom_x:.1f} {drv_bottom_y:.1f} '
                    f'V {elbow_y:.1f} H {tx:.1f} V {ty:.1f}" '
                    f'fill="none" stroke="{_hue_str(hue, 0.55)}" '
                    f'stroke-width="1.1" stroke-linecap="round"/>'
                )

        # ─── driver cards ───
        for i, drv in enumerate(positions["drivers"]):
            node = drv["node"]
            hue = node.group or "rust"
            dx, dy, dw, dh = drv["x"], drv["y"], drv["w"], drv["h"]
            drv_extra = getattr(node, "extra", {}) or {}

            skin_svg = _try_skin_draw(
                "kpi_driver_card", dx, dy, dw, dh, "", pal, hue=hue,
            )
            if skin_svg:
                parts.append(skin_svg)
            else:
                parts.append(
                    f'<rect x="{dx:.1f}" y="{dy}" width="{dw:.1f}" height="{dh}" '
                    f'rx="8" fill="{_hue_str(hue, 0.06)}" '
                    f'stroke="{_hue_str(hue, 0.75)}" stroke-width="1.4"/>'
                )
                parts.append(
                    f'<rect x="{dx:.1f}" y="{dy}" width="{dw:.1f}" height="4" '
                    f'rx="2" fill="{_hue_str(hue)}"/>'
                )
            # kicker · 窄卡自动缩短 · 避免溢出撞邻居
            kicker_txt = drv_extra.get("kicker", "")
            if dw < 240.0 and len(kicker_txt) > 12:
                # 窄卡精简: "DRIVER 1 · LEADING" → "DRIVER 1"
                # "驱动 1 · 前置" → "驱动 1"
                if "·" in kicker_txt:
                    kicker_txt = kicker_txt.split("·")[0].strip()
            kicker_ls = "0.10em" if dw < 240.0 else "0.24em"
            fs_dk, tk = _fit_font_size(kicker_txt, dw - 24, 17.0, min_size=17.0)
            parts.append(
                f'<text x="{dx + 14:.1f}" y="{dy + 26}" font-family="{FONT_SANS}" '
                f'font-size="{fs_dk:.1f}" font-weight="700" '
                f'fill="{_hue_str(hue)}" letter-spacing="{kicker_ls}">'
                f'{esc(tk)}</text>'
            )
            # name only. The rotating secondary metric value used to sit on the
            # right and often looked like it belonged to a different column hue.
            drv_label = node.label
            fs_dn, tn2 = _fit_font_size(
                drv_label, (dw - 48) * 1.06, 24.0,
                min_size=17.0, char_w_ratio=0.48,
            )
            tn2 = _clip_text_to_width(tn2, dw - 48, fs_dn)
            parts.append(
                f'<text x="{dx + 14:.1f}" y="{dy + 56}" font-family="{FONT_SERIF}" '
                f'font-size="{fs_dn:.1f}" font-weight="800" '
                f'fill="{_hue_str("ink")}">{esc(tn2)}</text>'
            )
            _divider_y = dy + 88
            _lag_y = dy + 104
            _spark_y0 = dy + 110
            # hair divider
            parts.append(
                f'<line x1="{dx + 14:.1f}" y1="{_divider_y}" '
                f'x2="{dx + dw - 14:.1f}" y2="{_divider_y}" '
                f'stroke="{_hue_str(hue, 0.35)}" stroke-width="0.6"/>'
            )
            # N LAGGING kicker · i18n: CN 时切中文 · 窄卡精简 · 长文自动降 letter-spacing
            n_leaf = len(positions["leaves"][i])
            _is_cn = _has_cjk(drv_label) or _has_cjk(drv_extra.get("kicker", ""))
            if dw < 240.0:
                lag_kicker = f"{n_leaf} 前置" if _is_cn else f"{n_leaf} LAGGING"
                lag_ls = "0.06em"
            else:
                lag_kicker = f"{n_leaf} 个前置指标" if _is_cn else f"{n_leaf} LAGGING METRICS"
                lag_ls = "0.10em"
            fs_dl, tl2 = _fit_font_size(lag_kicker, dw - 24, 17.0, min_size=17.0)
            parts.append(
                f'<text x="{dx + 14:.1f}" y="{_lag_y}" font-family="{FONT_SANS}" '
                f'font-size="{fs_dl:.1f}" font-weight="700" '
                f'fill="rgba(94,80,62,0.7)" letter-spacing="{lag_ls}">'
                f'{esc(tl2)}</text>'
            )
            # driver-level sparkline
            spark_kind = "up" if drv_extra.get("health", "on") == "on" else (
                "flat" if drv_extra.get("health") == "watch" else "up-bad"
            )
            spark_x0 = dx + 14
            spark_y0 = _spark_y0
            spark_w = dw - 28
            spark_h = max(6.0, min(14, dy + dh - spark_y0 - 4))
            pts = _spark_path(spark_x0, spark_y0, spark_w, spark_h, kind=spark_kind)
            spark_color = _hue_str(hue, 0.85) if spark_kind != "up-bad" else _hue_str("red_off", 0.9)
            parts.append(
                f'<polyline points="{pts}" fill="none" '
                f'stroke="{spark_color}" stroke-width="1.4"/>'
            )
            # target dash line (mid-height of spark region)
            parts.append(
                f'<line x1="{spark_x0:.1f}" y1="{spark_y0 + spark_h * 0.55:.1f}" '
                f'x2="{spark_x0 + spark_w:.1f}" y2="{spark_y0 + spark_h * 0.55:.1f}" '
                f'stroke="{_hue_str("gray", 0.3)}" stroke-width="0.4" '
                f'stroke-dasharray="2 2"/>'
            )

        # ─── leaf cards (lagging metrics) ───
        for i, drv in enumerate(positions["drivers"]):
            hue = drv["node"].group or "rust"
            leaves = positions["leaves"][i]
            for lp in leaves:
                leaf = lp["node"]
                lex = getattr(leaf, "extra", {}) or {}
                lx, ly, lw, lh = lp["x"], lp["y"], lp["w"], lp["h"]
                compact = lp.get("compact", False)

                if compact:
                    # 单行 compact 样式: [rail] [label · value · health] 全 16pt
                    skin_svg = _try_skin_draw(
                        "kpi_leaf_card", lx, ly, lw, lh, "", pal, hue=hue, compact=True,
                    )
                    if skin_svg:
                        parts.append(skin_svg)
                    else:
                        parts.append(
                            f'<rect x="{lx:.1f}" y="{ly:.1f}" width="{lw:.1f}" height="{lh:.1f}" '
                            f'rx="3" fill="{_hue_str("paper")}" '
                            f'stroke="{_hue_str(hue, 0.35)}" stroke-width="0.6"/>'
                        )
                        parts.append(
                            f'<rect x="{lx:.1f}" y="{ly:.1f}" width="3" height="{lh:.1f}" '
                            f'fill="{_hue_str(hue, 0.8)}"/>'
                        )
                    # 短 health 符号 · compact 模式 · 右对齐
                    hlth = lex.get("health", "on")
                    h_lbl = {"on": "ON", "watch": "!", "off": "OFF"}.get(hlth, "ON")
                    h_hue = _health_hue(hlth)
                    h_w_est = 32.0  # 保守估计 health 占宽
                    # label · sans 16pt · 占左 45% · R3 保留 10pt slide-space 硬红线 (min_size=16 SVG)
                    # 但允许字符截断 · 使长 label 不撞 value
                    # 注意 · atomize 用 uppercase 0.7 × size 估宽 · 保守用 0.7
                    lbl = leaf.label
                    label_w = lw * 0.45 - 12
                    fs_lk, tlk = _fit_font_size(lbl, label_w, 17.0, min_size=17.0)
                    # letter-cut fallback · 匹配 atomize 的 uppercase 0.7 系数 · 减 padding 8
                    _cw = fs_lk * 0.7  # conservative uppercase char width in SVG-space
                    est_w = len(tlk) * _cw
                    if est_w > (label_w - fs_lk * 0.5):
                        max_chars = max(3, int((label_w - fs_lk * 0.5) / _cw))
                        tlk = tlk[:max_chars]
                    parts.append(
                        f'<text x="{lx + 10:.1f}" y="{ly + lh / 2 + 5:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="{fs_lk:.1f}" '
                        f'font-weight="700" fill="{_hue_str(hue)}" '
                        f'letter-spacing="0.02em">{esc(tlk)}</text>'
                    )
                    # value · serif 16pt · 右对齐到 (health 左边界 - 8) · R3 保留 10pt floor
                    val_l = lex.get("value", "") or leaf.sublabel
                    val_x_right = lx + lw - h_w_est - 8
                    val_w = lw - label_w - h_w_est - 24
                    fs_lv, tlv = _fit_font_size(val_l, val_w, 17.0, min_size=17.0)
                    # value letter-cut · 若 min 仍溢出 · 截断 (digits/lowercase 用 0.55)
                    _cwv = fs_lv * 0.6  # value 常含数字/符号 · 混合估宽
                    est_v = len(tlv) * _cwv
                    if est_v > (val_w - fs_lv * 0.5):
                        max_v = max(3, int((val_w - fs_lv * 0.5) / _cwv))
                        tlv = tlv[:max_v]
                    parts.append(
                        f'<text x="{val_x_right:.1f}" y="{ly + lh / 2 + 5:.1f}" '
                        f'text-anchor="end" font-family="{FONT_SERIF}" '
                        f'font-size="{fs_lv:.1f}" font-weight="800" '
                        f'fill="{_hue_str("ink")}">{esc(tlv)}</text>'
                    )
                    fs_lh, tlh = _fit_font_size(h_lbl, h_w_est, 17.0, min_size=17.0)
                    parts.append(
                        f'<text x="{lx + lw - 6:.1f}" y="{ly + lh / 2 + 5:.1f}" '
                        f'text-anchor="end" font-family="{FONT_SANS}" '
                        f'font-size="{fs_lh:.1f}" font-weight="700" '
                        f'fill="{_hue_str(h_hue)}" letter-spacing="0.02em">'
                        f'{esc(tlh)}</text>'
                    )
                    continue  # 跳过下面的 wide-card render

                # 宽卡 render (3 driver × 2-3 leaf 走这条)
                skin_svg = _try_skin_draw(
                    "kpi_leaf_card", lx, ly, lw, lh, "", pal, hue=hue, compact=False,
                )
                if skin_svg:
                    parts.append(skin_svg)
                else:
                    parts.append(
                        f'<rect x="{lx:.1f}" y="{ly:.1f}" width="{lw:.1f}" height="{lh:.1f}" '
                        f'rx="4" fill="{_hue_str("paper")}" '
                        f'stroke="{_hue_str(hue, 0.45)}" stroke-width="0.8"/>'
                    )
                    parts.append(
                        f'<rect x="{lx:.1f}" y="{ly:.1f}" width="{lw:.1f}" height="3" '
                        f'rx="1.5" fill="{_hue_str(hue, 0.7)}"/>'
                    )
                # label (kicker) · sans 16pt
                lbl = leaf.label
                fs_lk, tlk = _fit_font_size(lbl, (lw - 12) * 1.06, 17.0, min_size=17.0)
                parts.append(
                    f'<text x="{lx + 8:.1f}" y="{ly + 22:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="{fs_lk:.1f}" '
                    f'font-weight="700" fill="{_hue_str(hue)}" '
                    f'letter-spacing="0.06em">{esc(tlk)}</text>'
                )
                # value · body serif · ≥ 16pt
                val_l = lex.get("value", "") or leaf.sublabel
                fs_lv, tlv = _fit_font_size(
                    val_l, (lw - 12) * 1.10, 22.0,
                    min_size=17.0, char_w_ratio=0.48,
                )
                parts.append(
                    f'<text x="{lx + 8:.1f}" y="{ly + 46:.1f}" '
                    f'font-family="{FONT_SERIF}" font-size="{fs_lv:.1f}" '
                    f'font-weight="800" fill="{_hue_str("ink")}">'
                    f'{esc(tlv)}</text>'
                )
                # unit / secondary · sans 16pt
                unit_l = lex.get("unit", "") or leaf.detail
                if unit_l:
                    fs_lu, tlu = _fit_font_size(
                        unit_l, (lw - 8) * 1.10, 17.0,
                        min_size=17.0, char_w_ratio=0.48,
                    )
                    parts.append(
                        f'<text x="{lx + 8:.1f}" y="{ly + 62:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="{fs_lu:.1f}" '
                        f'fill="{_hue_str("gray")}">{esc(tlu)}</text>'
                    )
                # delta · sans 16pt
                d_l = lex.get("delta", "")
                d_l_hue = lex.get("delta_hue", "green_ok")
                if d_l:
                    fs_ld, tld = _fit_font_size(
                        d_l, (lw - 8) * 1.10, 17.0,
                        min_size=17.0, char_w_ratio=0.48,
                    )
                    parts.append(
                        f'<text x="{lx + 8:.1f}" y="{ly + 80:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="{fs_ld:.1f}" '
                        f'font-weight="700" fill="{_hue_str(d_l_hue)}">'
                        f'{esc(tld)}</text>'
                    )
                # mini sparkline
                spark_kind_l = lex.get("spark_kind", "flat")
                spark_x0 = lx + 6
                spark_y0 = ly + 90
                spark_w = lw - 12
                spark_h = 12
                pts_l = _leaf_spark_path(spark_x0, spark_y0, spark_w, spark_h,
                                           kind=spark_kind_l)
                spark_color_l = _hue_str(hue, 0.9) if spark_kind_l != "up-bad" else \
                    _hue_str("red_off", 0.9)
                parts.append(
                    f'<polyline points="{pts_l}" fill="none" '
                    f'stroke="{spark_color_l}" stroke-width="1.2"/>'
                )
                parts.append(
                    f'<line x1="{spark_x0:.1f}" y1="{spark_y0 + spark_h * 0.55:.1f}" '
                    f'x2="{spark_x0 + spark_w:.1f}" y2="{spark_y0 + spark_h * 0.55:.1f}" '
                    f'stroke="{_hue_str("gray", 0.3)}" stroke-width="0.4" '
                    f'stroke-dasharray="1 2"/>'
                )
                # health label
                hlth = lex.get("health", "on")
                # 2026-09-13 P0 fix: wide-card 但 leaf 宽 < 100px 时 "ON TARGET" (9 char)
                # min_size 17pt SVG 需 ~85px · leaf 常只有 55-90px · 溢出被邻居 card_bg 遮挡
                # (视觉截断 "ON TAR"). 窄 leaf 改用 3-char 徽章 · 与 legend/status hue 一致
                if lw < 100:
                    h_lbl = _health_label_short(hlth)
                else:
                    h_lbl = _health_label(hlth)
                h_hue = _health_hue(hlth)
                fs_lh, tlh = _fit_font_size(h_lbl, (lw - 8) * 1.06, 17.0, min_size=17.0)
                parts.append(
                    f'<text x="{lx + 8:.1f}" y="{ly + lh - 6:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="{fs_lh:.1f}" '
                    f'font-weight="700" fill="{_hue_str(h_hue)}" '
                    f'letter-spacing="0.06em">{esc(tlh)}</text>'
                )

        # ─── SIDEBAR narrative (right side) ───
        if has_sidebar:
            sbar = root_extra.get("sidebar") or []
            watch = root_extra.get("watch_callout") or {}
            _sbar_hdr = "驱动叙事" if _cn_context else "CASCADE NARRATIVE"
            _sbar_sub = (
                "本季度每个驱动的故事概览"
                if _cn_context else
                "the story each driver tells this quarter"
            )
            parts.append(
                f'<line x1="{p.sidebar_hair_x}" y1="{p.sidebar_hair_y0}" '
                f'x2="{p.sidebar_hair_x}" y2="{p.sidebar_hair_y1}" '
                f'stroke="{_hue_str("gray_hair", 0.6)}" stroke-width="0.5"/>'
            )
            parts.append(
                f'<text x="{p.sidebar_x}" y="{p.sidebar_top_kicker_y}" '
                f'font-family="{FONT_SANS}" font-size="17" font-weight="700" '
                f'fill="{_hue_str("ink")}" letter-spacing="1.4">'
                f'{esc(_sbar_hdr)}</text>'
            )
            parts.append(
                f'<text x="{p.sidebar_x}" y="{p.sidebar_top_sub_y}" '
                f'font-family="{FONT_SANS}" font-size="17" '
                f'fill="{_hue_str("gray")}">{esc(_sbar_sub)}</text>'
            )
            # figure out per-card height dynamically if has watch callout
            n_sbar = len(sbar)
            has_watch = bool(watch)
            card_gap = p.sidebar_card_gap
            avail_h = p.sidebar_hair_y1 - p.sidebar_card_y0
            if has_watch:
                avail_h -= (p.sidebar_watch_h + card_gap)
            card_h = (avail_h - card_gap * (n_sbar - 1)) / max(n_sbar, 1)
            card_h = min(card_h, p.sidebar_card_h)
            cur_y = p.sidebar_card_y0
            for entry in sbar:
                hue = entry.get("hue", "rust")
                kicker_e = entry.get("kicker", "")
                value_line = entry.get("value_line", "")
                body_lines = entry.get("body_lines") or []
                # bg
                parts.append(
                    f'<rect x="{p.sidebar_x}" y="{cur_y:.1f}" '
                    f'width="{p.sidebar_w}" height="{card_h:.1f}" rx="4" '
                    f'fill="{_hue_str(hue, 0.06)}" '
                    f'stroke="{_hue_str(hue, 0.35)}" stroke-width="0.6"/>'
                )
                parts.append(
                    f'<rect x="{p.sidebar_x}" y="{cur_y:.1f}" width="4" '
                    f'height="{card_h:.1f}" fill="{_hue_str(hue)}"/>'
                )
                parts.append(
                    f'<text x="{p.sidebar_x + 16}" y="{cur_y + 22:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="17" font-weight="700" '
                    f'fill="{_hue_str(hue)}" letter-spacing="0.22em">'
                    f'{esc(kicker_e)}</text>'
                )
                fs_vl, tvl = _fit_font_size(value_line, p.sidebar_w - 22, 18.0, min_size=17.0)
                parts.append(
                    f'<text x="{p.sidebar_x + 16}" y="{cur_y + 46:.1f}" '
                    f'font-family="{FONT_SERIF}" font-size="{fs_vl:.1f}" '
                    f'font-weight="700" fill="{_hue_str("ink")}">'
                    f'{esc(tvl)}</text>'
                )
                # body lines · 自适应 card_h · 每行 20px (16pt)
                # header 占 46+4=50px · 剩下分给 body
                body_avail_h = card_h - 60
                max_body_lines = max(int(body_avail_h / 20), 0)
                for k, line in enumerate(body_lines):
                    if k >= max_body_lines:
                        break
                    fs_bl, tbl = _fit_font_size(line, p.sidebar_w - 22, 17.0, min_size=17.0)
                    parts.append(
                        f'<text x="{p.sidebar_x + 16}" y="{cur_y + 68 + k * 20:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="{fs_bl:.1f}" '
                        f'fill="{_hue_str("ink_dim")}">{esc(tbl)}</text>'
                    )
                cur_y += card_h + card_gap

            # watch callout
            if has_watch:
                wh = p.sidebar_watch_h
                wy = cur_y
                parts.append(
                    f'<rect x="{p.sidebar_x}" y="{wy:.1f}" '
                    f'width="{p.sidebar_w}" height="{wh}" rx="4" '
                    f'fill="{_hue_str("red_off", 0.08)}" '
                    f'stroke="{_hue_str("red_off", 0.5)}" stroke-width="0.8"/>'
                )
                parts.append(
                    f'<rect x="{p.sidebar_x}" y="{wy:.1f}" width="4" '
                    f'height="{wh}" fill="{_hue_str("red_off")}"/>'
                )
                wk = watch.get("kicker", "")
                wb = watch.get("body", "")
                parts.append(
                    f'<text x="{p.sidebar_x + 16}" y="{wy + 20:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="17" font-weight="700" '
                    f'fill="{_hue_str("red_off")}" letter-spacing="0.22em">'
                    f'{esc(wk)}</text>'
                )
                fs_wb, twb = _fit_font_size(wb, p.sidebar_w - 22, 17.0, min_size=17.0)
                parts.append(
                    f'<text x="{p.sidebar_x + 16}" y="{wy + 36:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="{fs_wb:.1f}" '
                    f'fill="{_hue_str("ink_dim")}">{esc(twb)}</text>'
                )

        # ─── legend (bottom-left band) ───
        lgd_items = root_extra.get("legend_items") or []
        if lgd_items:
            legend_x0 = 60
            legend_y0 = p.legend_y
            legend_x1 = positions["tree_x1"]
            parts.append(
                f'<text x="{legend_x0}" y="{legend_y0}" font-family="{FONT_SANS}" '
                f'font-size="17" font-weight="700" fill="{_hue_str("ink")}" '
                f'letter-spacing="1.4">LEGEND</text>'
            )
            parts.append(
                f'<line x1="{legend_x0}" y1="{legend_y0 + 8}" '
                f'x2="{legend_x1}" y2="{legend_y0 + 8}" '
                f'stroke="{_hue_str("gray_hair", 0.7)}" stroke-width="0.4"/>'
            )
            n_l = len(lgd_items)
            span = legend_x1 - legend_x0
            # keep swatch-items narrow, text-only wide; give each item avg slot
            slot = span / max(n_l, 1)
            for k, it in enumerate(lgd_items):
                ix = legend_x0 + k * slot
                kind = it.get("kind", "text")
                hue = it.get("hue", "ink")
                title = it.get("title", "")
                sub = it.get("sub", "")
                text_x = ix
                if kind == "swatch":
                    parts.append(
                        f'<rect x="{ix:.1f}" y="{legend_y0 + 20}" '
                        f'width="20" height="12" rx="2" '
                        f'fill="{_hue_str(hue)}"/>'
                    )
                    text_x = ix + 28
                elif kind == "leaf-frame":
                    parts.append(
                        f'<rect x="{ix:.1f}" y="{legend_y0 + 20}" '
                        f'width="20" height="12" rx="2" '
                        f'fill="{_hue_str("paper")}" '
                        f'stroke="{_hue_str("gray")}" stroke-width="0.8"/>'
                    )
                    text_x = ix + 28
                elif kind == "spark":
                    # small spark
                    spx = ix
                    spy = legend_y0 + 26
                    pts_lg = f"{spx:.1f},{spy + 2:.1f} {spx + 10:.1f},{spy:.1f} {spx + 20:.1f},{spy - 2:.1f} {spx + 30:.1f},{spy - 4:.1f} {spx + 40:.1f},{spy - 6:.1f}"
                    parts.append(
                        f'<polyline points="{pts_lg}" fill="none" '
                        f'stroke="{_hue_str("ink_dim", 0.85)}" stroke-width="1.2"/>'
                    )
                    parts.append(
                        f'<line x1="{spx:.1f}" y1="{spy + 2:.1f}" '
                        f'x2="{spx + 40:.1f}" y2="{spy + 2:.1f}" '
                        f'stroke="{_hue_str("gray", 0.4)}" stroke-width="0.3" '
                        f'stroke-dasharray="1 2"/>'
                    )
                    text_x = ix + 46
                # title (colored if text-only kind or specified hue)
                title_color = _hue_str("ink") if kind in {"swatch", "leaf-frame", "spark"} else _hue_str(hue)
                parts.append(
                    f'<text x="{text_x:.1f}" y="{legend_y0 + 30}" '
                    f'font-family="{FONT_SANS}" font-size="17" '
                    f'font-weight="700" fill="{title_color}">'
                    f'{esc(title)}</text>'
                )
                parts.append(
                    f'<text x="{text_x:.1f}" y="{legend_y0 + 48}" '
                    f'font-family="{FONT_SANS}" font-size="17" '
                    f'fill="{_hue_str("gray")}">{esc(sub)}</text>'
                )

        # ─── footer method / how-to-read ───
        read_lines = root_extra.get("read_lines") or []
        if read_lines:
            parts.append(
                f'<line x1="60" y1="{p.footer_hair_y}" x2="1340" '
                f'y2="{p.footer_hair_y}" stroke="{_hue_str("gray_hair")}" '
                f'stroke-width="0.5"/>'
            )
            ys = [p.footer_line1_y, p.footer_line2_y, p.footer_line3_y]
            for k, entry in enumerate(read_lines[:3]):
                if isinstance(entry, (tuple, list)) and len(entry) >= 2:
                    bold_part, rest = entry[0], entry[1]
                else:
                    bold_part, rest = "", str(entry)
                y = ys[k]
                # bold prefix + normal rest via tspan
                parts.append(
                    f'<text x="60" y="{y}" font-family="{FONT_SANS}" '
                    f'font-size="17" fill="{_hue_str("ink_dim")}">'
                    f'<tspan font-weight="700">{esc(bold_part)}</tspan> '
                    f'{esc(rest)}</text>'
                )

        # source · bottom-right
        src = data.source or ""
        if src:
            parts.append(
                f'<text x="1340" y="{p.footer_caption_y}" text-anchor="end" '
                f'font-family="{FONT_SANS}" font-size="17" '
                f'fill="{_hue_str("gray")}" letter-spacing="0.3">'
                f'{esc(src)}</text>'
            )

        parts.append('</svg>')
        return "".join(parts)
    finally:
        _MOD_L1.update(_ORIG_L1)
__all__ = [
    "BASELINE_NORTH_STAR", "BASELINE_STAT_STRIP", "BASELINE_DRIVERS",
    "BASELINE_SIDEBAR", "BASELINE_WATCH", "BASELINE_LEGEND",
    "BASELINE_READ_LINES",
    "build_kpi_data", "build_kpi_tree",
    "HERO_KP_DATA",
    "KPIHeroParams",
    "render_hero_embed_kp_kpi_v2",
    "_DANDELION_HUE",
]
