"""Hub fanout layout · dandelion sql_tree 风格 hero canvas mindmap.

参考 dandelion/sql_tree.svg 的顶级视觉设计:
  - 中心圆形 hub · deep bg + gold kicker + serif 大字 + stat + dashed 内环
  - 5-8 branches 左右分布 (奇数时左多右少) · S 形贝塞尔曲线连 hub 边
  - branch card 180×46 · 左 hue bar + M{i}·{meta} kicker + name + subtitle + 右上 N LEAVES
  - leaf pill 170×22 · dot + L01 编号 + name + · + note
  - 顶部 KPI 带 (与 fishbone 同款)

输出 kinds:
    hub_shadow, hub_circle, hub_inner_ring, hub_kicker,
    hub_divider, hub_name, hub_stat, hub_note,
    branch_curve, branch_card, leaf_curve, leaf_pill,
    (右侧 legend 由 preset render 单独处理)
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin, radians, atan2, sqrt
from typing import Any, Dict, List, Optional

from ..skins._base import _visual_width, _wrap_lines

__all__ = ["hub_fanout_layout", "LayoutOverflow", "HubFanoutParams"]


class LayoutOverflow(RuntimeError):
    pass


@dataclass
class HubFanoutParams:
    # canvas · 1400×720
    canvas_w: float = 1400.0
    canvas_h: float = 720.0
    # hub 圆心 (略偏下 · 顶部让位给 KPI 带 y=110~142)
    hub_cx: float = 680.0
    hub_cy: float = 420.0
    hub_r: float = 96.0
    hub_inner_r_delta: float = 10.0
    # branch card
    card_w: float = 210.0
    card_h: float = 78.0
    # branch anchor 位置
    left_card_x: float = 260.0
    right_card_x: float = 880.0
    # branch 竖向分布参数 · 左 3 右 2 时: 左侧 3 项分布 [hub_cy-210, hub_cy, hub_cy+210]
    branch_row_h: float = 240.0
    # leaf pill
    leaf_w: float = 190.0
    leaf_h: float = 32.0
    leaf_row_h: float = 38.0
    # leaf x offset
    leaf_x_offset_left: float = 200.0
    leaf_x_offset_right: float = 200.0
    leaf_card_gap: float = 26.0
    # branch curve control ratio
    branch_curve_ctrl_ratio: float = 0.5


def _iter_branches(tree: Any) -> List[Any]:
    root = getattr(tree, "root", None)
    if root is None:
        return []
    return list(getattr(root, "children", []) or [])


def hub_fanout_layout(
    tree: Any,
    x0: float, y0: float, x1: float, y1: float,
    *,
    params: Optional[HubFanoutParams] = None,
) -> List[Dict[str, Any]]:
    """sql_tree 风格 hero canvas mindmap layout.

    x0/y0/x1/y1 参数保留兼容 · 实际几何由 params 决定 (hero canvas 固定).

    Data schema (Tree):
        root: TreeNode
          label: hub 大字 (如 "SQL 5D")
          extra:
            kicker: 圆内顶部小字 (如 "CORE CURRICULUM")
            stat: 大 stat (如 "25 HOURS")
            stat_note: 底部微字 (如 "15 LESSONS · 5 MODULES")
          children: 3-8 branch nodes
            label: branch name (如 "SELECT / FROM")
            group: hue ("rust"/"blue"/"green"/"magenta"/"olive"/"cinnamon")
            extra:
              subtitle: str (如 "projection · scope")
              kicker: str (如 "M1 · 5 h" · 若未传则 f"M{idx+1}")
              n_leaf_label: str (如 "3 LESSONS" · 若未传则 f"{len(children)} LEAVES")
            children: leaf nodes
              label: leaf 显示文本 (如 "字段选择 · column pick")
              extra:
                code: str (如 "L01" · 若未传则 f"L{i:02d}" 全局编号)
    """
    p = params or HubFanoutParams()
    root = getattr(tree, "root", None)
    if root is None:
        return []

    branches = _iter_branches(tree)
    n = len(branches)
    if n == 0:
        return []
    if n > 8:
        raise LayoutOverflow(f"too many branches: {n} > 8")

    # ── hub_cy 按 branch 数动态: 少 branch 时上移让主体紧贴 KPI 带 ─
    n_left = (n + 1) // 2   # idx 0/2/4... 左
    n_right = n // 2        # idx 1/3/5... 右
    n_side_max = max(n_left, n_right, 1)
    # 计算最大 leaf 数 · 决定单个 branch 的实际内容半高
    max_leaves = max(
        (len(list(getattr(br, "children", []) or [])) for br in branches),
        default=0,
    )
    # 单个 branch 的内容半高 = max(card_h/2, leaves 总高/2)
    leaves_stack_h = max_leaves * p.leaf_row_h if max_leaves else 0
    single_branch_half_h = max(p.card_h / 2, leaves_stack_h / 2)
    # 主体总半高 = (n_side_max-1)*行距/2 + 单 branch 内容半高
    content_half_h = (n_side_max - 1) * p.branch_row_h / 2 + single_branch_half_h
    content_half_h = max(content_half_h, p.hub_r + 12)
    # 让主体顶 = KPI 底(180) + top_pad(20)
    top_of_content = 180 + 20
    hub_cy_dynamic = top_of_content + content_half_h
    # 兼容手动传 params.hub_cy
    if abs(p.hub_cy - 420.0) < 0.1:
        p_hub_cy = hub_cy_dynamic
    else:
        p_hub_cy = p.hub_cy

    out: List[Dict[str, Any]] = []

    # ── 1. hub 圆 ─────────────────────────────
    root_extra = getattr(root, "extra", {}) or {}
    out.append({
        "kind": "hub_shadow",
        "cx": p.hub_cx + 3, "cy": p_hub_cy + 4, "r": p.hub_r,
    })
    out.append({
        "kind": "hub_circle",
        "cx": p.hub_cx, "cy": p_hub_cy, "r": p.hub_r,
    })
    out.append({
        "kind": "hub_inner_ring",
        "cx": p.hub_cx, "cy": p_hub_cy, "r": p.hub_r - p.hub_inner_r_delta,
    })
    kicker = root_extra.get("kicker", "")
    if kicker:
        out.append({
            "kind": "hub_kicker",
            "cx": p.hub_cx, "cy": p_hub_cy - 44,
            "label": kicker,
        })
        out.append({
            "kind": "hub_divider",
            "x1": p.hub_cx - 30, "x2": p.hub_cx + 30,
            "y": p_hub_cy - 34,
        })
    name = str(getattr(root, "label", ""))
    if name:
        out.append({
            "kind": "hub_name",
            "cx": p.hub_cx, "cy": p_hub_cy - 8,
            "label": name,
        })
    stat = str(root_extra.get("stat", ""))
    if stat:
        out.append({
            "kind": "hub_stat",
            "cx": p.hub_cx, "cy": p_hub_cy + 24,
            "label": stat,
        })
    stat_note = str(root_extra.get("stat_note", ""))
    if stat_note:
        out.append({
            "kind": "hub_note",
            "cx": p.hub_cx, "cy": p_hub_cy + 52,
            "label": stat_note,
        })

    # ── 2. branch 分左右 · 奇数时左多右少 ─────────
    # 分配规则: idx 0 左, idx 1 右, idx 2 左, idx 3 右... 交替
    left_bs: List[Any] = []
    right_bs: List[Any] = []
    for i, br in enumerate(branches):
        (left_bs if i % 2 == 0 else right_bs).append(br)

    def _y_positions(count: int, hub_cy: float, row_h: float) -> List[float]:
        """竖向均分 count 个位置 · 以 hub_cy 为中心."""
        if count == 0:
            return []
        if count == 1:
            return [hub_cy]
        # count 项均分 · 总高 (count-1)*row_h · 顶端 = cy - (count-1)*row_h/2
        top = hub_cy - (count - 1) * row_h / 2
        return [top + i * row_h for i in range(count)]

    left_ys = _y_positions(len(left_bs), p_hub_cy, p.branch_row_h)
    right_ys = _y_positions(len(right_bs), p_hub_cy, p.branch_row_h)

    # ── 3. 遍历生成 branch + leaves ─────────
    global_leaf_idx = 0  # 全局 leaf 编号 L01, L02...
    for side, bs, ys, card_x_base in [
        ("left", left_bs, left_ys, p.left_card_x),
        ("right", right_bs, right_ys, p.right_card_x),
    ]:
        for k, br in enumerate(bs):
            hue = str(getattr(br, "group", "") or "rust")
            b_label = str(getattr(br, "label", ""))
            b_id = getattr(br, "id", f"b_{side}_{k}") or f"b_{side}_{k}"
            b_extra = getattr(br, "extra", {}) or {}
            subtitle = str(b_extra.get("subtitle", ""))
            leaves = list(getattr(br, "children", []) or [])
            n_leaf = len(leaves)
            # global_idx (M1..Mn) 由数据里传的 kicker 覆盖 · 否则按 branches 原序编号
            gi = branches.index(br)
            b_kicker = str(b_extra.get("kicker", f"M{gi + 1}"))
            n_leaf_label = str(b_extra.get("n_leaf_label", f"{n_leaf} LEAVES"))

            card_x = card_x_base
            card_y = ys[k] - p.card_h / 2

            # branch card
            # NOTE (R4 fix, 2026-09-13): anchor points on card edges (hub-side + leaf-side)
            # are stored explicitly so downstream draws never miss the line-endpoint.
            card_hub_anchor_x = card_x + p.card_w if side == "left" else card_x
            card_leaf_anchor_x = card_x if side == "left" else card_x + p.card_w
            card_anchor_y = card_y + p.card_h / 2

            out.append({
                "kind": "branch_card",
                "hue": hue,
                "x": card_x, "y": card_y,
                "w": p.card_w, "h": p.card_h,
                "label": b_label,
                "kicker": b_kicker,
                "subtitle": subtitle,
                "n_leaf_label": n_leaf_label,
                "n_leaf": n_leaf,
                "side": side,
                "index": gi,
                "id": b_id,
                # side-aware anchor points on card edges
                "hub_anchor_x": card_hub_anchor_x,
                "hub_anchor_y": card_anchor_y,
                "leaf_anchor_x": card_leaf_anchor_x,
                "leaf_anchor_y": card_anchor_y,
            })

            # branch → hub 的 S 形贝塞尔曲线
            # hub 侧端点: hub 圆边缘 (指向 card 中心方向)
            card_cx = card_x + p.card_w / 2
            card_cy = card_y + p.card_h / 2
            # 方向角
            dx = card_cx - p.hub_cx
            dy = card_cy - p_hub_cy
            dist = sqrt(dx * dx + dy * dy)
            ux = dx / dist if dist else 0
            uy = dy / dist if dist else 0
            # hub 表面端点
            hub_edge_x = p.hub_cx + ux * p.hub_r
            hub_edge_y = p_hub_cy + uy * p.hub_r
            # card 侧端点: 用之前计算的 hub_anchor (side-aware edge midpoint)
            card_edge_x = card_hub_anchor_x
            card_edge_y = card_anchor_y

            # S 形 Bezier: 控制点 1 在 hub 边右侧 · 控制点 2 在 card 边左侧 (side=left)
            # 用两个中垂线上的控制点
            mid_x = (hub_edge_x + card_edge_x) / 2
            ctrl1_x = mid_x
            ctrl1_y = hub_edge_y
            ctrl2_x = mid_x
            ctrl2_y = card_edge_y
            out.append({
                "kind": "branch_curve",
                "hue": hue,
                "d": f"M {hub_edge_x:.1f} {hub_edge_y:.1f} "
                     f"C {ctrl1_x:.1f} {ctrl1_y:.1f}, "
                     f"{ctrl2_x:.1f} {ctrl2_y:.1f}, "
                     f"{card_edge_x:.1f} {card_edge_y:.1f}",
                # 端点圆 (在 card 一侧)
                "dot_cx": card_edge_x,
                "dot_cy": card_edge_y,
                # explicit anchor endpoints for downstream verify (grep)
                "hub_anchor_x": hub_edge_x,
                "hub_anchor_y": hub_edge_y,
                "card_anchor_x": card_edge_x,
                "card_anchor_y": card_edge_y,
                # visibility hint · preset should honour this so curves are
                # not sub-pixel when SVG is scaled into small figure slots
                "stroke_width": 2.2,
            })

            # ── leaves ─────────
            if n_leaf == 0:
                continue
            # Measure the whole visible leaf row. The renderer places the dot at
            # the connector endpoint and aligns this combined label beside it.
            leaf_measures: List[Dict[str, Any]] = []
            for leaf in leaves:
                leaf_extra = getattr(leaf, "extra", {}) or {}
                l_code = str(leaf_extra.get("code", ""))
                l_label = str(getattr(leaf, "label", ""))
                display_label = f"{l_code}  {l_label}".strip() if l_code else l_label
                text_avail = p.leaf_w - 50
                # measure with font-size 15, char_w = size * 0.55 = 8.25
                char_w = 15.0 * 0.55
                lines = _wrap_lines(display_label, text_avail, char_w=char_w, max_lines=2)
                leaf_measures.append({
                    "leaf": leaf,
                    "code": l_code,
                    "label": l_label,
                    "display_label": display_label,
                    "lines": lines,
                    "n_lines": max(1, len(lines)),
                })
            # per-row pill height: base leaf_h if single line, else scale
            per_row_h = max(
                p.leaf_h,
                max((m["n_lines"] for m in leaf_measures), default=1) * (p.leaf_h * 0.72) + 6,
            )
            # per-row spacing must fit taller pills
            per_row_spacing = max(p.leaf_row_h, per_row_h + 6)
            total_leaf_h = n_leaf * per_row_spacing
            leaves_top = card_cy - total_leaf_h / 2 + per_row_spacing / 2 - per_row_h / 2

            if side == "left":
                leaf_x = card_x - p.leaf_card_gap - p.leaf_w
            else:
                leaf_x = card_x + p.card_w + p.leaf_card_gap

            for j, m in enumerate(leaf_measures):
                global_leaf_idx += 1
                leaf = m["leaf"]
                l_code = m["code"]
                l_label = m["label"]
                l_lines = m["lines"]
                l_y = leaves_top + j * per_row_spacing
                l_cy = l_y + per_row_h / 2

                # R4 fix: leaf pill's card-facing edge anchor (guarantee non-orphan)
                leaf_card_side_x = leaf_x + p.leaf_w if side == "left" else leaf_x
                leaf_anchor_x = leaf_card_side_x
                leaf_anchor_y = l_cy

                out.append({
                    "kind": "leaf_pill",
                    "hue": hue,
                    "x": leaf_x, "y": l_y,
                    "w": p.leaf_w, "h": per_row_h,
                    "code": l_code,
                    "label": l_label,
                    "display_label": m["display_label"],
                    "lines": l_lines,          # R4: pre-wrapped lines (list)
                    "n_lines": m["n_lines"],
                    "side": side,
                    "parent": b_id,
                    "index": j,
                    # R4: side-aware anchor · line endpoint MUST match this
                    "anchor_x": leaf_anchor_x,
                    "anchor_y": leaf_anchor_y,
                })

                # 从 branch card 到 leaf 的短 S 曲线
                # R4 fix: start point uses card's leaf_anchor (side-aware midpoint)
                # · end point uses leaf's card-facing anchor. Both are stored in
                # curve dict so grep-based unit tests can verify endpoint = leaf anchor.
                b_edge_x = card_leaf_anchor_x
                b_edge_y = card_anchor_y
                l_edge_x = leaf_anchor_x
                l_edge_y = leaf_anchor_y

                mid_lx = (b_edge_x + l_edge_x) / 2
                out.append({
                    "kind": "leaf_curve",
                    "hue": hue,
                    "d": f"M {b_edge_x:.1f} {b_edge_y:.1f} "
                         f"C {mid_lx:.1f} {b_edge_y:.1f}, "
                         f"{mid_lx:.1f} {l_edge_y:.1f}, "
                         f"{l_edge_x:.1f} {l_edge_y:.1f}",
                    # explicit endpoints for verify-by-grep
                    "card_anchor_x": b_edge_x,
                    "card_anchor_y": b_edge_y,
                    "leaf_anchor_x": l_edge_x,
                    "leaf_anchor_y": l_edge_y,
                    "parent": b_id,
                    "leaf_index": j,
                    # visibility hint · was 0.9 which is sub-pixel in tiny figure
                    # slots; bump to 1.4 so preset gets a non-zero stroke.
                    "stroke_width": 1.4,
                })

    return out
