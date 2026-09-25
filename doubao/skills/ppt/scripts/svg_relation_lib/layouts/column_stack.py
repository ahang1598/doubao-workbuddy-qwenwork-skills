"""Column stack layout · dandelion brand_pyramid 风格 hero canvas pyramid.

参考 dandelion/brand_pyramid.svg 的顶级视觉:
  - 中央 5 层金字塔 · 顶尖到底渐宽的梯形横带
  - 每层 · title (serif 大字) + em dash + subtitle + 内容行
  - 顶部 kicker + FIVE FLOORS 标注 · 底部 how-to-read 一行

不做的元素:
  - 左右两侧 SOUL/BELIEFS/WHY/WHAT 问答 (用户明确不要)
  - 右侧 PALETTE / TAGLINE

Data schema (Tree):
    root: TreeNode
      label: 金字塔总名 (仅记录 · 不显示在主体)
      extra:
        kicker: str (如 "FIGURE 27 · BRAND ARCHITECTURE")
        floors_note: str (如 "each level explains the one below it")
        how_to_read: str (底部一行 how-to-read)
      children: 3-6 floor nodes (从 top 到 bottom)
        label: floor 大标题 (如 "PURPOSE")
        sublabel: em dash 副标题 (如 "why we exist")
        detail: 内容行 (如 "To turn everyday moments...")
        group: hue key ("gold_p"/"cinnamon"/"magenta"/"blue"/"olive")

Params:
    hero canvas 1400×720 · pyramid cx=700 · top_y=170 · bot_y=640
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

__all__ = ["column_stack_layout", "LayoutOverflow", "ColumnStackParams"]


class LayoutOverflow(RuntimeError):
    pass


@dataclass
class ColumnStackParams:
    canvas_w: float = 1400.0
    canvas_h: float = 720.0
    pyramid_cx: float = 700.0
    pyramid_top_y: float = 130.0
    pyramid_bot_y: float = 680.0
    pyramid_top_w: float = 240.0
    pyramid_bot_w: float = 1200.0
    pyramid_apex_h: float = 0.0
    floor_gap_y: float = 0.0


def _iter_floors(tree: Any) -> List[Any]:
    root = getattr(tree, "root", None)
    if root is None:
        return []
    return list(getattr(root, "children", []) or [])


def column_stack_layout(
    tree: Any,
    x0: float, y0: float, x1: float, y1: float,
    *,
    params: Optional[ColumnStackParams] = None,
) -> List[Dict[str, Any]]:
    p = params or ColumnStackParams()
    floors = _iter_floors(tree)
    n = len(floors)
    if n == 0:
        return []
    if n > 6:
        raise LayoutOverflow(f"too many floors: {n} > 6")
    if n < 2:
        raise LayoutOverflow(f"too few floors: {n} < 2")

    out: List[Dict[str, Any]] = []

    total_h = p.pyramid_bot_y - p.pyramid_top_y
    gap_y = max(0.0, p.floor_gap_y)
    usable_h = total_h - gap_y * (n - 1)
    if usable_h <= 0:
        raise LayoutOverflow(
            f"pyramid floor gaps too large: total_h={total_h:.1f}, gap_y={gap_y:.1f}, floors={n}"
        )
    row_h = usable_h / n
    top_w = p.pyramid_top_w
    bot_w = p.pyramid_bot_w
    cx = p.pyramid_cx
    apex_y = p.pyramid_top_y - max(0.0, p.pyramid_apex_h)
    silhouette_h = p.pyramid_bot_y - apex_y

    def width_at_y(y: float) -> float:
        if p.pyramid_apex_h <= 0:
            t = (y - p.pyramid_top_y) / total_h
            return top_w + (bot_w - top_w) * t
        t = max(0.0, min(1.0, (y - apex_y) / silhouette_h))
        return bot_w * t

    for i, floor in enumerate(floors):
        y_top = p.pyramid_top_y + i * (row_h + gap_y)
        y_bot = y_top + row_h
        w_top = width_at_y(y_top)
        w_bot = width_at_y(y_bot)
        if i == 0 and p.pyramid_apex_h > 0:
            pts = [
                (cx, apex_y),
                (cx + w_bot / 2, y_bot),
                (cx - w_bot / 2, y_bot),
            ]
        else:
            pts = [
                (cx - w_top / 2, y_top),
                (cx + w_top / 2, y_top),
                (cx + w_bot / 2, y_bot),
                (cx - w_bot / 2, y_bot),
            ]
        d = (
            f"M {pts[0][0]:.1f} {pts[0][1]:.1f} "
            + " ".join(f"L {x:.1f} {y:.1f}" for x, y in pts[1:])
            + " Z"
        )

        hue = str(getattr(floor, "group", "") or "cinnamon")
        title = str(getattr(floor, "label", ""))
        sub = str(getattr(floor, "sublabel", ""))
        detail = str(getattr(floor, "detail", ""))

        out.append({
            "kind": "pyramid_floor",
            "d": d,
            "hue": hue,
            "index": i,
            "n_total": n,
            "cx": cx,
            "cy_top": y_top,
            "cy_bot": y_bot,
            "w_top": w_top,
            "w_bot": w_bot,
            "y_center": (y_top + y_bot) / 2,
            "title": title,
            "sub": sub,
            "detail": detail,
        })

        cy_center = (y_top + y_bot) / 2
        if row_h < 72:
            title_y = cy_center - 6
            sub_y = cy_center + 12
            detail_y = cy_center + 28
        else:
            title_y = cy_center - 7
            sub_y = cy_center + 16
            detail_y = cy_center + 35
        out[-1]["w_label"] = width_at_y(sub_y) if p.pyramid_apex_h > 0 else max(w_top, w_bot)

        out.append({
            "kind": "floor_title",
            "cx": cx, "y": title_y,
            "text": title, "hue": hue, "index": i,
        })
        if sub:
            out.append({
                "kind": "floor_sub",
                "cx": cx, "y": sub_y,
                "text": sub, "hue": hue, "index": i,
            })
        if detail:
            out.append({
                "kind": "floor_detail",
                "cx": cx, "y": detail_y,
                "text": detail, "hue": hue, "index": i,
            })

    return out
