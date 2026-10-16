"""Vertical chain layout · dandelion why5_ladder 风格 hero canvas.

参考 dandelion/why5_ladder.svg 的顶级视觉:
  - 左侧竖排 SURFACE→ROOT 指示 + N 圆点节点 (对应 N 张 card)
  - 中央 N 张深色 card 竖排 (L0 ALERT / L1..L(n-2) FACT/FLAW / L(n-1) ROOT CAUSE)
  - card 间 WHY? 金色 pill 连接

Data schema (Tree):
    root: TreeNode
      label: incident 简述 (作为 L0 label)
      sublabel: L0 副标题
      extra:
        kicker: str · L0 kicker (如 "ALERT · INCIDENT")
        parallel_factor: {title, body, hint, tag}  · 右侧红框
        corrective_actions: List[(code, phase, text, sprint)] · A1..An 短卡
        kpis: List[{kicker, value, note, hue}] · 顶部 4 KPI 带
      children[0]: L1 · 依此嵌套 (推荐 5 层 · 支持 3-7)
        label / sublabel / group (hue) / type ('fact' / 'flaw' / 'root')
        extra.kicker: 覆盖默认的 "WHY N · FACT" kicker
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

__all__ = ["vertical_chain_layout", "LayoutOverflow", "VerticalChainParams"]


class LayoutOverflow(RuntimeError):
    pass


@dataclass
class VerticalChainParams:
    canvas_w: float = 1400.0
    canvas_h: float = 720.0
    chain_cx: float = 470.0
    chain_top_y: float = 176.0     # KPI 带下方开始
    card_w: float = 620.0
    card_h: float = 66.0
    card_gap: float = 10.0
    rail_x: float = 88.0
    sidebar_x: float = 826.0
    sidebar_w: float = 486.0


def _iter_chain(tree: Any) -> List[Any]:
    node = getattr(tree, "root", None)
    if node is None:
        return []
    chain = [node]
    while True:
        kids = list(getattr(node, "children", []) or [])
        if not kids:
            break
        node = kids[0]
        chain.append(node)
    return chain


def vertical_chain_layout(
    tree: Any,
    x0: float, y0: float, x1: float, y1: float,
    *,
    params: Optional[VerticalChainParams] = None,
) -> List[Dict[str, Any]]:
    p = params or VerticalChainParams()
    chain = _iter_chain(tree)
    n = len(chain)
    if n < 3:
        raise LayoutOverflow(f"chain too short: {n} < 3")
    if n > 8:
        raise LayoutOverflow(f"chain too long: {n} > 8")

    out: List[Dict[str, Any]] = []

    for i, node in enumerate(chain):
        y_top = p.chain_top_y + i * (p.card_h + p.card_gap)
        node_extra = getattr(node, "extra", {}) or {}
        label = str(getattr(node, "label", ""))
        sublabel = str(getattr(node, "sublabel", ""))
        ntype = str(getattr(node, "type", "")) or (
            "root" if i == n - 1 else ("alert" if i == 0 else "fact")
        )
        hue = str(getattr(node, "group", "")) or ("rust" if ntype == "root" else "cinnamon")
        if i == 0:
            kicker = node_extra.get("kicker", "ALERT · INCIDENT")
        elif i == n - 1:
            kicker = node_extra.get("kicker", "ROOT CAUSE")
        else:
            kind_lbl = ntype.upper() if ntype in ("fact", "flaw") else "WHY"
            kicker = node_extra.get("kicker", f"WHY {i} · {kind_lbl}")

        out.append({
            "kind": "chain_card",
            "index": i, "n_total": n,
            "x": p.chain_cx - p.card_w / 2, "y": y_top,
            "w": p.card_w, "h": p.card_h,
            "hue": hue,
            "ntype": ntype,
            "label": label,
            "sublabel": sublabel,
            "kicker": kicker,
            "level": f"L{i}",
            "is_root": (i == n - 1),
            "is_alert": (i == 0),
        })

        # 左侧 rail 圆点
        out.append({
            "kind": "rail_dot",
            "cx": p.rail_x + 20, "cy": y_top + p.card_h / 2,
            "index": i, "hue": hue,
            "is_root": (i == n - 1),
            "is_alert": (i == 0),
        })

        # WHY? pill · 最后 card 之后无
        if i < n - 1:
            pill_cy = y_top + p.card_h + p.card_gap / 2
            out.append({
                "kind": "why_pill",
                "cx": p.chain_cx, "cy": pill_cy,
                "index": i,
            })

    # 左侧 rail 竖线
    first_y = p.chain_top_y + p.card_h / 2
    last_y = p.chain_top_y + (n - 1) * (p.card_h + p.card_gap) + p.card_h / 2
    out.append({
        "kind": "rail_line",
        "x": p.rail_x + 20,
        "y1": first_y, "y2": last_y,
    })
    out.append({
        "kind": "rail_label_top",
        "x": p.rail_x + 20, "y": first_y - 22,
        "text": "SURFACE",
    })
    out.append({
        "kind": "rail_label_bot",
        "x": p.rail_x + 20, "y": last_y + 32,
        "text": "ROOT",
    })

    return out
