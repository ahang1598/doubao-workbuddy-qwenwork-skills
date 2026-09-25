"""C4 container v2 layout · hero canvas 1400×720 · dandelion-migrated.

参考 step1 手绘 SVG `c4_hero_reference.svg`:
    * 顶部 chrome (kicker / title / subtitle / hairline / figure line)
    * N 条水平 boundary 色带 (每条 tint bg + 左侧粗竖 rib + 顶部 label + 右侧 note)
    * 每条 boundary 内 M 个 container 卡片 (top hue bar + name + tech tag + kicker)
    * 底部 legend / footer notes

本 layout 只负责**位置**：boundary rows + container cells。
edges 的锚点在 preset 端按 boundary 内 container 索引寻址（更灵活）。

弹性维度:
    * n_boundaries ∈ [2, 5] · 每 boundary 有独立 height 权重
    * n_containers_per_boundary ∈ [1, 6]  (v1 baseline 4)
    * container name / tech tag 长度不定 → preset 用 _fit_font_size / _wrap_lines
    * boundary height 按 max_containers_per_row 自适应 · 支持双行 container 排布

canvas 契约:
    * 硬 viewBox 1400×720 · 出口 shrink 后随内容变
    * 顶部 chrome 占 60-140 · 底部 legend/footer 占 620-720
    * body area = (60, 140, 1340, 610) · boundary 均分该高度

输出 kind:
    boundary     · 色带矩形 · 含 hue / label / note / rib_x
    container    · 卡片矩形 · 含 hue (继承 boundary) / name / tech / kicker
    edges        · 每边 label 的位置 hint (包含 halo bbox + 20px border-avoid) ·
                    preset 可直接消费; 若 preset 有自定义 label placement 逻辑,
                    这里的 halo bbox 也可以作为 collision-check 输入.

数据 schema:
    Tree
    ├─ root (system · figure_title/subtitle 承担)
    │  extra = {kicker, subtitle, figure_note, source, encoding_note, edges}
    │           edges: List of {src, dst, label, kind, ...}
    └─ children = boundaries
       每 boundary (TreeNode)
        · label: "EDGE" / "ORCHESTRATION" ...
        · sublabel: 右侧 note
        · group: hue key ("purple" 会 fallback 到 magenta)
        · extra: {index}
        · children = containers
          每 container (TreeNode)
           · label: "Client SDK"
           · sublabel: 技术栈 (italic) · "Python · TypeScript · Go"
           · detail: kicker 小字 · "SDK · STREAMING"

R4 fix (2026-09-13):
    * Stage 1 measure: 每 container 用 _visual_width 估 name + tech + kicker 需要的最
      小宽度; 每 edge label 也预测量 halo bbox 尺寸.
    * Stage 2 place:
        - Container width 按 max(measured, container_min_w) + padding.
        - Row 中 container 数量若 < 该 boundary 的 grid columns 数 (= max row_n
          in that boundary), **stretch 填满** avail_inner_w (2-item row: 每个
          占 half; 3 of 4: 每个占 1/3 of avail).
        - Edge label 输出 halo hint (rect fill=white bbox) + 20px container-border
          avoid margin (label 中心距任何 container 边界 ≥ 20px 时 ok).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations
from typing import Any, Dict, List, Optional, Tuple

from ..skins._base import _visual_width, _wrap_lines

__all__ = [
    "c4_container_v2_layout",
    "LayoutOverflow",
    "C4ContainerParams",
]


class LayoutOverflow(RuntimeError):
    """position 无法放下 · 提示 preset 减 container/boundary."""


@dataclass
class C4ContainerParams:
    """c4_container_v2 参数 · 一次性覆盖默认视觉常数.

    body_* 为 boundary 布局 area (顶部 chrome 之下 · legend 之上).
    """
    body_x0: float = 60.0
    body_y0: float = 140.0
    body_x1: float = 1340.0
    body_y1: float = 630.0        # 630 之下留 legend / footer 空间 (canvas 760 · 130px footer band)
    boundary_gap_y: float = 18.0  # 跨 boundary 竖直边走这段 gap
    boundary_pad_x: float = 60.0  # container 起始距 boundary 左内边距
    boundary_pad_top: float = 48.0  # boundary label 下方留白 · 也是同行 top gutter
    boundary_pad_bottom: float = 22.0  # 同行 bottom gutter · 存放绕行 detour + label
    container_gap_x: float = 26.0
    container_row_gap_y: float = 16.0  # 同 boundary 内多行 container 的行距
    container_min_h: float = 62.0
    container_max_h: float = 86.0
    container_min_w: float = 150.0
    container_max_w: float = 400.0  # 卡片过宽显得空 · 用此收敛 (grid 满行时生效)
    boundary_min_h: float = 110.0    # 硬下限 (label + card + pad)
    max_boundaries: int = 5
    min_boundaries: int = 2
    max_containers_per_boundary: int = 6
    min_containers_per_boundary: int = 1
    # boundary heights 按权重分 (可选) · 空则均分
    # weight = max(containers_of_this_boundary, 1)
    weight_by_container_count: bool = True

    # ── R4 measure-then-place 参数 ──
    # container 内部 text 尺寸估计 (SVG font-size · atomize scale 通过 char_w 系数体现)
    measure_name_fs: float = 21.45      # ≈ _fs(13) · 大 card
    measure_tech_fs: float = 16.5       # ≈ _fs(10) · tech tag
    measure_kicker_fs: float = 16.5     # ≈ _fs(10) · kicker caps
    measure_char_w_ratio: float = 0.55  # SVG char width per unit fs (atomize)
    measure_pad_x: float = 16.0         # container 内 text 左右 padding
    # container_min_w 至少满足 max(measured name, measured tech, measured kicker) + 2*pad
    measure_bump_min_w: bool = True     # True: container_min_w 依据实测 bump

    # ── R4 edge label 参数 ──
    edge_label_fs: float = 16.5         # ≈ _fs(10) · matches preset _emit_bundle_label
    edge_label_halo_pad_x: float = 8.0
    edge_label_halo_pad_y: float = 2.0  # preset HALO_H = fs*1.6 + 4
    edge_label_char_w_ratio: float = 0.6  # atomize-ish estimate
    # container border avoid margin: label 中心距任何 container 边界 ≥ 20px
    edge_label_border_avoid_px: float = 20.0
    # halo rect fill color (默认 cream · preset 端已按 skin 用 CREAM_BG)
    edge_label_halo_fill: str = "rgba(250,246,235,1)"
    # Layout midpoint labels are kept for legacy callers only. The C4 preset
    # uses route-aware label placement because rendered polylines may detour.
    emit_edge_label_hints: bool = False

    # 是否 stretch 未满行 (row_n < grid_cols) container 到 avail_inner_w
    stretch_partial_rows: bool = True


def _iter_boundaries(tree: Any) -> Tuple[Any, List[Any]]:
    """Tree schema: root 是 system meta · root.children 是 boundaries."""
    root = getattr(tree, "root", None)
    if root is None:
        raise LayoutOverflow("c4_container_v2 expects Tree.root != None")
    boundaries = list(getattr(root, "children", []) or [])
    return root, boundaries


# ═══════════════════════════════════════════════════════════════════
# R4 · Stage 1 · measure helpers
# ═══════════════════════════════════════════════════════════════════

def _measure_container_min_w(
    node: Any, p: C4ContainerParams,
) -> float:
    """预估 container 卡片需要的最小内容宽度.

    使用 _visual_width (来自 skins._base) 分别估 name / tech / kicker 三行文字
    需要的宽度, 返回 max + 2*pad_x. 上层将其与 container_min_w 取 max.

    注: `_visual_width(text, char_w)` 里 char_w = fs * char_w_ratio. atomize
    实际渲染宽度略大于此估算 (CJK 用 1.8x, digit 0.75x). 我们只用此保证 label 不
    被切成 <10px 边距的窄卡; 精确 fit 仍由 preset _fit_font_size 承担.
    """
    if node is None:
        return p.container_min_w
    name = (getattr(node, "label", "") or "").strip()
    tech = (getattr(node, "sublabel", "") or "").strip()
    kicker = (getattr(node, "detail", "") or "").strip()
    if not (name or tech or kicker):
        return p.container_min_w

    def _est(text: str, fs: float) -> float:
        if not text:
            return 0.0
        return _visual_width(text, fs * p.measure_char_w_ratio)

    w_name = _est(name, p.measure_name_fs)
    w_tech = _est(tech, p.measure_tech_fs)
    w_kicker = _est(kicker, p.measure_kicker_fs)
    # kicker 会 upper() · 上限增加 ~15%
    w_kicker *= 1.15
    max_text_w = max(w_name, w_tech, w_kicker)
    # 至少留 2 * pad_x 内边距
    return max_text_w + 2 * p.measure_pad_x


def _measure_edge_label(
    label: str, p: C4ContainerParams,
) -> Tuple[float, float]:
    """预估 edge label + halo 的 bbox 尺寸.

    Returns (halo_w, halo_h). halo 包含 label 全部字形 + 2*pad_x/2*pad_y.
    与 preset _emit_bundle_label / _render_edge 里的 HALO_TOP/HALO_H 计算保持
    一致 (HALO_TOP = fs*1.15 · HALO_H = fs*1.6 + 4).
    """
    if not label:
        return 0.0, 0.0
    fs = p.edge_label_fs
    label_w = _visual_width(label, fs * p.edge_label_char_w_ratio)
    halo_w = label_w + 2 * p.edge_label_halo_pad_x
    halo_h = fs * 1.6 + 2 * p.edge_label_halo_pad_y
    return halo_w, halo_h


# ═══════════════════════════════════════════════════════════════════
# R4 · Stage 2 · place · edge label position hint
# ═══════════════════════════════════════════════════════════════════

def _container_pos_by_key(
    container_positions: List[Dict[str, Any]],
) -> Dict[Tuple[int, int], Dict[str, Any]]:
    """(boundary_index, index_in_boundary) → container_pos dict."""
    out: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for cp in container_positions:
        key = (cp["boundary_index"], cp["index_in_boundary"])
        out[key] = cp
    return out


def _edge_midpoint(
    src_cp: Dict[str, Any], dst_cp: Dict[str, Any],
) -> Tuple[float, float]:
    """两 container 中心的中点 · 作为 edge label 的默认位置 hint."""
    sx = src_cp["x"] + src_cp["w"] / 2
    sy = src_cp["y"] + src_cp["h"] / 2
    dx = dst_cp["x"] + dst_cp["w"] / 2
    dy = dst_cp["y"] + dst_cp["h"] / 2
    return (sx + dx) / 2, (sy + dy) / 2


def _label_pos_avoid_border(
    mx: float, my: float,
    halo_w: float, halo_h: float,
    all_cps: List[Dict[str, Any]],
    src_id: str, dst_id: str,
    border_avoid_px: float,
) -> Tuple[float, float]:
    """把 (mx, my) 调整到距任何 container 边界 ≥ border_avoid_px.

    - 若 (mx, my) 已在容器 border 附近 (距离 <20px) · 沿 y 轴逐步 push 出去.
    - src/dst 端点也算 · edge label 不应贴到 endpoint border.
    - 若 20 步内 push 不出去 · 返回原始 (mx, my) (由 preset collision 逻辑再修).
    """
    def _too_close(cx: float, cy: float) -> bool:
        for cp in all_cps:
            # halo bbox 距离 container 边界
            hx0 = cx - halo_w / 2
            hx1 = cx + halo_w / 2
            hy0 = cy - halo_h / 2
            hy1 = cy + halo_h / 2
            # container 边界距 halo 的最短距离 (若 halo 落在 container 外)
            # 若 halo 与 container 重叠 · dist 定义为 0.
            rx0, ry0 = cp["x"], cp["y"]
            rx1, ry1 = cp["x"] + cp["w"], cp["y"] + cp["h"]
            # halo overlaps container?
            overlap_x = (hx1 > rx0) and (hx0 < rx1)
            overlap_y = (hy1 > ry0) and (hy0 < ry1)
            if overlap_x and overlap_y:
                # 重叠 · 视为距离 0
                return True
            # halo 完全在 container 外 · 计算最短水平/竖直距离
            dx = 0.0
            if hx1 <= rx0:
                dx = rx0 - hx1
            elif hx0 >= rx1:
                dx = hx0 - rx1
            dy = 0.0
            if hy1 <= ry0:
                dy = ry0 - hy1
            elif hy0 >= ry1:
                dy = hy0 - ry1
            # 若 halo 边跟 container 边距 < border_avoid_px
            # only care if we're close to a border (i.e., either dx or dy < threshold)
            # AND the other axis has overlap (i.e., halo aligned with container band)
            if overlap_y and dx < border_avoid_px:
                return True
            if overlap_x and dy < border_avoid_px:
                return True
        return False

    if not _too_close(mx, my):
        return mx, my
    # push my up/down alternately
    step = 6.0
    for k in range(1, 21):
        for sign in (1, -1):
            cy2 = my + sign * k * step
            if not _too_close(mx, cy2):
                return mx, cy2
    return mx, my


def _resolve_edge_endpoints_meta(
    edge: Dict[str, Any],
    containers_by_key: Dict[Tuple[int, int], Dict[str, Any]],
    all_cps: List[Dict[str, Any]],
    p: C4ContainerParams,
) -> Optional[Dict[str, Any]]:
    """给一条 edge 计算 label 位置 hint · 返回 dict 或 None."""
    src_key = edge.get("src")
    dst_key = edge.get("dst")
    if not (isinstance(src_key, tuple) and isinstance(dst_key, tuple)):
        return None
    if src_key not in containers_by_key or dst_key not in containers_by_key:
        return None
    src_cp = containers_by_key[src_key]
    dst_cp = containers_by_key[dst_key]
    label = edge.get("label", "") or ""
    halo_w, halo_h = _measure_edge_label(label, p)
    mx, my = _edge_midpoint(src_cp, dst_cp)
    # 沿 edge 中点 · 避开 container 边界 20px
    if label:
        mx, my = _label_pos_avoid_border(
            mx, my, halo_w, halo_h, all_cps,
            src_id=src_cp["id"], dst_id=dst_cp["id"],
            border_avoid_px=p.edge_label_border_avoid_px,
        )
    # halo bbox (SVG rect anchor at top-left)
    halo_x0 = mx - halo_w / 2
    halo_y0 = my - halo_h / 2
    return {
        "kind": "edge",
        "src": src_key,
        "dst": dst_key,
        "src_id": src_cp["id"],
        "dst_id": dst_cp["id"],
        "label": label,
        "arrow_kind": edge.get("kind", "sync"),
        "hue": edge.get("hue"),
        "route": edge.get("route"),
        "anchor_src": edge.get("anchor_src"),
        "anchor_dst": edge.get("anchor_dst"),
        # label + halo hint
        "label_mx": mx,
        "label_my": my,
        "halo_w": halo_w,
        "halo_h": halo_h,
        "halo_x": halo_x0,
        "halo_y": halo_y0,
        "halo_fill": p.edge_label_halo_fill,
        "border_avoid_px": p.edge_label_border_avoid_px,
    }


def _edge_optimized_orders(
    root: Any,
    n_containers_per_b: List[int],
) -> List[List[int]]:
    """Compute low-cost visual order for each boundary from edge topology.

    C4 container graphs are tiny here (<=5 boundaries, <=6 containers each).
    We can therefore enumerate each boundary's local permutations and run a few
    coordinate-descent passes. This is deterministic and bounded:
    O(iterations * boundaries * 6! * edges^2), which is small for this schema.
    """
    orders = [list(range(n)) for n in n_containers_per_b]
    src_edges = (getattr(root, "extra", {}) or {}).get("edges") or []
    valid_edges: List[Dict[str, Any]] = []
    for e in src_edges:
        if e.get("route"):
            continue
        src = e.get("src")
        dst = e.get("dst")
        if not (isinstance(src, tuple) and isinstance(dst, tuple)):
            continue
        sb, si = src
        db, di = dst
        if not (isinstance(sb, int) and isinstance(si, int)
                and isinstance(db, int) and isinstance(di, int)):
            continue
        if sb < 0 or db < 0 or sb >= len(n_containers_per_b) \
                or db >= len(n_containers_per_b):
            continue
        if si < 0 or di < 0 or si >= n_containers_per_b[sb] \
                or di >= n_containers_per_b[db]:
            continue
        valid_edges.append(e)

    if not valid_edges:
        return orders

    def _pos_maps(cur_orders: List[List[int]]) -> List[Dict[int, int]]:
        return [
            {idx: pos for pos, idx in enumerate(order)}
            for order in cur_orders
        ]

    def _norm(pos: int, n: int) -> float:
        return 0.5 if n <= 1 else pos / (n - 1)

    def _crosses(e1: Dict[str, Any], e2: Dict[str, Any],
                 bidx: int, pos: List[Dict[int, int]]) -> bool:
        s1 = e1.get("src"); d1 = e1.get("dst")
        s2 = e2.get("src"); d2 = e2.get("dst")
        if not (isinstance(s1, tuple) and isinstance(d1, tuple)
                and isinstance(s2, tuple) and isinstance(d2, tuple)):
            return False
        if s1[0] == d1[0] or s2[0] == d2[0]:
            return False
        other1 = d1 if s1[0] == bidx else s1 if d1[0] == bidx else None
        other2 = d2 if s2[0] == bidx else s2 if d2[0] == bidx else None
        here1 = s1 if s1[0] == bidx else d1 if d1[0] == bidx else None
        here2 = s2 if s2[0] == bidx else d2 if d2[0] == bidx else None
        if other1 is None or other2 is None or here1 is None or here2 is None:
            return False
        if other1[0] != other2[0] or here1[1] == here2[1]:
            return False
        a = pos[bidx][here1[1]] - pos[bidx][here2[1]]
        b = pos[other1[0]][other1[1]] - pos[other2[0]][other2[1]]
        return a * b < 0

    def _score_boundary(
        bidx: int,
        perm: Tuple[int, ...],
        cur_orders: List[List[int]],
    ) -> float:
        trial = [list(order) for order in cur_orders]
        trial[bidx] = list(perm)
        pos = _pos_maps(trial)
        n = n_containers_per_b[bidx]
        score = 0.0

        # Keep output stable unless edge topology gives a clear reason.
        for p, idx in enumerate(perm):
            score += 0.035 * abs(p - idx)

        touching_cross: List[Dict[str, Any]] = []
        for e in valid_edges:
            src = e["src"]; dst = e["dst"]
            sb, si = src; db, di = dst
            if sb == bidx and db == bidx:
                delta = pos[bidx][di] - pos[bidx][si]
                score += 0.18 * abs(delta)
                if delta < 0:
                    score += 2.75
                continue
            if sb == bidx or db == bidx:
                touching_cross.append(e)
                this = src if sb == bidx else dst
                other = dst if sb == bidx else src
                other_n = n_containers_per_b[other[0]]
                score += 0.55 * abs(
                    _norm(pos[bidx][this[1]], n)
                    - _norm(pos[other[0]][other[1]], other_n)
                )

        for i in range(len(touching_cross)):
            for j in range(i + 1, len(touching_cross)):
                if _crosses(touching_cross[i], touching_cross[j], bidx, pos):
                    score += 3.5
        return score

    for _ in range(4):
        changed = False
        for bidx, n in enumerate(n_containers_per_b):
            if n <= 2:
                continue
            current = tuple(orders[bidx])
            best = current
            best_score = _score_boundary(bidx, current, orders)
            for perm in permutations(range(n)):
                cand_score = _score_boundary(bidx, perm, orders)
                if cand_score + 1e-6 < best_score:
                    best = perm
                    best_score = cand_score
            if best != current:
                orders[bidx] = list(best)
                changed = True
        if not changed:
            break
    return orders


# ═══════════════════════════════════════════════════════════════════

def c4_container_v2_layout(
    tree: Any,
    *,
    params: Optional[C4ContainerParams] = None,
) -> Dict[str, Any]:
    """C4 container v2 layout · dandelion-migrated · hero 1400×720.

    Returns
    -------
    dict {
        "boundaries": List[boundary_pos_dict],
        "containers": List[container_pos_dict],
        "edges": List[edge_meta_dict],   # R4 · edge label + halo hint
        "meta": {body_x0, body_y0, body_x1, body_y1, ...},
    }

    每 boundary_pos_dict:
        id, label, sublabel, hue, x, y, w, h, rib_x, index
    每 container_pos_dict:
        id, boundary_id, boundary_index, index_in_boundary,
        label, sublabel, detail, hue, x, y, w, h, cx, cy,
        measured_min_w (R4 · text-measure derived)
    每 edge_meta_dict (R4):
        src, dst, src_id, dst_id, label, arrow_kind, hue, route,
        label_mx, label_my, halo_w, halo_h, halo_x, halo_y, halo_fill,
        border_avoid_px
    """
    p = params or C4ContainerParams()
    root, boundaries = _iter_boundaries(tree)
    n_b = len(boundaries)
    if n_b < p.min_boundaries:
        raise LayoutOverflow(
            f"n_boundaries={n_b} < min {p.min_boundaries}"
        )
    if n_b > p.max_boundaries:
        raise LayoutOverflow(
            f"n_boundaries={n_b} > max {p.max_boundaries}"
        )

    # 每 boundary 的 container 数
    n_containers_per_b: List[int] = []
    for b in boundaries:
        cs = list(getattr(b, "children", []) or [])
        n = len(cs)
        if n < p.min_containers_per_boundary:
            raise LayoutOverflow(
                f"boundary {getattr(b, 'label', '?')!r} has {n} < min "
                f"{p.min_containers_per_boundary} containers"
            )
        if n > p.max_containers_per_boundary:
            raise LayoutOverflow(
                f"boundary {getattr(b, 'label', '?')!r} has {n} > max "
                f"{p.max_containers_per_boundary} containers"
            )
        n_containers_per_b.append(n)

    # ── 分 boundary 高度 ──
    body_w = p.body_x1 - p.body_x0
    body_h = p.body_y1 - p.body_y0
    total_gap = (n_b - 1) * p.boundary_gap_y
    avail_h = body_h - total_gap
    if avail_h < 60 * n_b:
        raise LayoutOverflow(
            f"body_h={body_h:.0f} too small for {n_b} boundaries"
        )

    if p.weight_by_container_count:
        # 权重 = 需要多少行 · n≤4 → 1 · n≥5 → 2 · 让 2-row boundary 拿到 2x 高度
        weights = [2.0 if n >= 5 else 1.0 for n in n_containers_per_b]
    else:
        weights = [1.0] * n_b
    w_sum = sum(weights)
    boundary_heights = [avail_h * w / w_sum for w in weights]

    # 每 boundary 至少留出 header + 一行 container + pad
    min_boundary_h = p.boundary_min_h
    # 若总 avail_h 都装不下所有 boundary min · 主动放宽 body_y1 (拉高 body)
    total_min = min_boundary_h * n_b
    if avail_h < total_min:
        extend = min(total_min - avail_h, 60)  # 最多再借 60px
        avail_h += extend
    else:
        extend = 0
    # 按权重再算一次 (avail_h 可能已变)
    boundary_heights = [avail_h * w / w_sum for w in weights]
    # 内容自适应上限: 单行 boundary 最多 (pad_top + max_h + pad_bottom + 12 breathing)
    # 双行 boundary 最多 2*max_h + row_gap + pad_top + pad_bottom + 20
    for i, w in enumerate(weights):
        n_c = n_containers_per_b[i]
        needs_two_rows = n_c >= 5
        if needs_two_rows:
            content_max = (p.boundary_pad_top + 2 * p.container_max_h
                            + p.container_row_gap_y
                            + p.boundary_pad_bottom + 20)
        else:
            content_max = (p.boundary_pad_top + p.container_max_h
                            + p.boundary_pad_bottom + 16)
        if boundary_heights[i] > content_max:
            boundary_heights[i] = content_max
    for i, h in enumerate(boundary_heights):
        if h < min_boundary_h:
            deficit = min_boundary_h - h
            j = boundary_heights.index(max(boundary_heights))
            if boundary_heights[j] - deficit < min_boundary_h:
                # 均给 min
                boundary_heights = [min_boundary_h] * n_b
                break
            boundary_heights[j] -= deficit
            boundary_heights[i] = min_boundary_h

    # ═══════════════════════════════════════════════════════════════
    # R4 · Stage 1 · MEASURE
    # 每 container 用 _visual_width 估最小需要宽度 (bump container_min_w)
    # 每 edge 提前测 halo 尺寸 (用于后面 label 位置 hint)
    # ═══════════════════════════════════════════════════════════════
    measured_min_w_per_container: List[List[float]] = []  # [b_idx][c_idx]
    for b in boundaries:
        cs = list(getattr(b, "children", []) or [])
        row = [_measure_container_min_w(c, p) for c in cs]
        measured_min_w_per_container.append(row)

    # R4 · deck-wide grid columns (max row width across all boundaries).
    # Fixes P3 academic issue: a 2-item boundary inside a 4-boundary deck should
    # know the deck-wide "natural grid" is 4 · so it stretches its 2 items to
    # fill instead of clamping to container_max_w and floating center-aligned.
    # If we only compute grid_cols per-boundary from its own per_row (as before),
    # a lone 2-item boundary computes grid_cols=2 == row_n=2 → no stretch.
    def _est_per_row(n_c: int) -> List[int]:
        if n_c >= 5:
            top = (n_c + 1) // 2
            bot = n_c - top
            return [top, bot]
        return [n_c]

    deck_grid_cols = 1
    for n_c in n_containers_per_b:
        for rn in _est_per_row(n_c):
            if rn > deck_grid_cols:
                deck_grid_cols = rn
    visual_orders = _edge_optimized_orders(root, n_containers_per_b)

    # ── 装配 boundary + container positions ──
    boundary_positions: List[Dict[str, Any]] = []
    container_positions: List[Dict[str, Any]] = []

    cursor_y = p.body_y0
    for i, (b, b_h, n_c) in enumerate(
            zip(boundaries, boundary_heights, n_containers_per_b)):
        b_extra = getattr(b, "extra", {}) or {}
        hue = (getattr(b, "group", "") or getattr(b, "category", "")
                or b_extra.get("hue", "") or "rust")
        b_id = getattr(b, "id", f"b{i}") or f"b{i}"

        boundary_pos = {
            "id": b_id,
            "kind": "boundary",
            "index": i,
            "label": getattr(b, "label", "") or "",
            "sublabel": getattr(b, "sublabel", "") or "",  # note 右侧
            "detail": getattr(b, "detail", "") or "",
            "hue": hue,
            "x": p.body_x0,
            "y": cursor_y,
            "w": body_w,
            "h": b_h,
            "rib_x": p.body_x0,
        }
        boundary_positions.append(boundary_pos)

        # ── 该 boundary 内 container 排布 ──
        avail_inner_w = body_w - 2 * p.boundary_pad_x
        # 尝试一行放下所有
        one_row_gap_total = (n_c - 1) * p.container_gap_x
        one_row_container_w = ((avail_inner_w - one_row_gap_total) / n_c
                                if n_c > 0 else avail_inner_w)

        # measured min_w for this boundary (per container)
        measured_row = measured_min_w_per_container[i] if i < len(measured_min_w_per_container) else []
        max_measured_min_w = max(measured_row) if measured_row else p.container_min_w
        # 有效 container_min_w = max(p.container_min_w, max_measured_min_w)
        # (bump 后需要 stretch 行的宽度也不 fall below 这个下限)
        effective_min_w = max(p.container_min_w,
                              max_measured_min_w if p.measure_bump_min_w
                              else p.container_min_w)

        # Prefer one row whenever measured text can fit. Dense C4 graphs become
        # much harder to read when a boundary is split into two rows because
        # same-boundary edges must cross the row gap.
        single_row_allowed = (
            n_c <= p.max_containers_per_boundary
            and one_row_container_w >= p.container_min_w
        )
        force_two_rows = (
            n_c >= 5
            and not single_row_allowed
            and one_row_container_w < effective_min_w
            and b_h >= (p.boundary_pad_top
                         + 2 * p.container_min_h
                         + p.container_row_gap_y
                         + p.boundary_pad_bottom)
        )
        if not force_two_rows and (
                single_row_allowed or one_row_container_w >= effective_min_w or n_c <= 4):
            n_rows = 1
            per_row = [n_c]
        else:
            # 2 行 · 上行放 ceil(n/2) 下行放 floor(n/2)
            n_rows = 2
            top = (n_c + 1) // 2
            bot = n_c - top
            per_row = [top, bot]

        # ═══════════════════════════════════════════════════════════
        # R4 · Stage 2 · PLACE with row-stretch
        # grid_cols = max(this boundary's per_row, deck_grid_cols).
        # 未满行 (row_n < grid_cols) stretch 到 avail_inner_w
        # (ignore container_max_w · P3 fix: 2-item boundary in a 4-col deck
        # stretches to fill instead of clamping to 400 and floating center).
        # ═══════════════════════════════════════════════════════════
        local_grid_cols = max(per_row) if per_row else n_c
        grid_cols = max(local_grid_cols, deck_grid_cols)

        # 该 boundary 里 container 可用高度
        inner_h = b_h - p.boundary_pad_top - p.boundary_pad_bottom
        if n_rows == 1:
            cell_h = inner_h
        else:
            cell_h = (inner_h - p.container_row_gap_y) / 2

        # 卡片高度 · 至少 min · 最多 max (太高不好看)
        card_h = max(min(cell_h, p.container_max_h), p.container_min_h)

        container_y_row0 = cursor_y + p.boundary_pad_top + (cell_h - card_h) / 2
        if n_rows == 2:
            container_y_row1 = (cursor_y + p.boundary_pad_top + cell_h
                                 + p.container_row_gap_y + (cell_h - card_h) / 2)
        else:
            container_y_row1 = 0

        cs = list(getattr(b, "children", []) or [])
        visual_order = visual_orders[i] if i < len(visual_orders) else list(range(n_c))
        for j_row, row_n in enumerate(per_row):
            row_start_idx = 0 if j_row == 0 else per_row[0]
            row_indices = visual_order[row_start_idx:row_start_idx + row_n]
            row_gap_total = (row_n - 1) * p.container_gap_x
            # R4 · row stretch:
            # 计算基础 container_w (grid-based) 和 stretched container_w (full-width)
            if row_n <= 0:
                container_w = avail_inner_w
            elif p.stretch_partial_rows and row_n < grid_cols:
                # 未满行 · stretch 铺满 · ignore container_max_w
                container_w = (avail_inner_w - row_gap_total) / row_n
                # 但仍不能违反 measured effective_min_w (若 row 里某 container measured 太宽)
                # 用 row 内 max measured 作 lower bound
                if measured_row:
                    row_measured = [
                        measured_row[idx] for idx in row_indices
                        if idx < len(measured_row)
                    ]
                    row_max_measured = max(row_measured) if row_measured else effective_min_w
                    container_w = max(container_w, row_max_measured)
                # stretch 时: 允许超过 container_max_w · 因为 2-item row 剩余空间较大
            else:
                # 满行 (row_n == grid_cols) · 走 grid 均分 · 保留 container_max_w 上限
                container_w = (avail_inner_w - row_gap_total) / row_n
                if container_w < effective_min_w:
                    container_w = max(container_w, 80.0)  # 尽力
                if container_w > p.container_max_w:
                    container_w = p.container_max_w

            # 居中 or 撑满
            row_total_w = row_n * container_w + row_gap_total
            if p.stretch_partial_rows and row_n < grid_cols \
                    and abs(row_total_w - avail_inner_w) < 0.5:
                # 完全撑满 avail_inner_w · row_x_start = body_x0 + boundary_pad_x
                row_x_start = p.body_x0 + p.boundary_pad_x
            else:
                # 居中 (满行时通常 row_total_w == avail_inner_w · 也 fall through 到这)
                row_x_start = p.body_x0 + (body_w - row_total_w) / 2

            row_y = container_y_row0 if j_row == 0 else container_y_row1
            for k in range(row_n):
                idx_in_b = row_indices[k]
                c = cs[idx_in_b]
                c_x = row_x_start + k * (container_w + p.container_gap_x)
                c_extra = getattr(c, "extra", {}) or {}
                # container hue 继承 boundary · 除非自定
                c_hue = (getattr(c, "group", "") or getattr(c, "category", "")
                          or c_extra.get("hue", "") or hue)
                # measured min_w for this container
                c_measured_min_w = (measured_row[idx_in_b]
                                     if idx_in_b < len(measured_row) else 0.0)
                container_positions.append({
                    "id": getattr(c, "id", f"{b_id}_c{idx_in_b}"),
                    "kind": "container",
                    "boundary_id": b_id,
                    "boundary_index": i,
                    "index_in_boundary": idx_in_b,
                    "row": j_row,
                    "col": k,
                    "grid_cols": grid_cols,
                    "row_n": row_n,
                    "label": getattr(c, "label", "") or "",
                    "sublabel": getattr(c, "sublabel", "") or "",  # tech tag
                    "detail": getattr(c, "detail", "") or "",       # kicker
                    "hue": c_hue,
                    "x": c_x,
                    "y": row_y,
                    "w": container_w,
                    "h": card_h,
                    "cx": c_x + container_w / 2,
                    "cy": row_y + card_h / 2,
                    "top_hue_bar_h": 4.0,
                    "measured_min_w": c_measured_min_w,
                })

        cursor_y += b_h + p.boundary_gap_y

    # ═══════════════════════════════════════════════════════════════
    # R4 · Stage 2 (cont'd) · edges · label position hint + halo bbox
    # ═══════════════════════════════════════════════════════════════
    edges_out: List[Dict[str, Any]] = []
    root_extra = getattr(root, "extra", {}) or {}
    src_edges = root_extra.get("edges") or []
    if p.emit_edge_label_hints and src_edges:
        containers_by_key = _container_pos_by_key(container_positions)
        for e in src_edges:
            meta = _resolve_edge_endpoints_meta(
                e, containers_by_key, container_positions, p,
            )
            if meta is not None:
                edges_out.append(meta)

    return {
        "boundaries": boundary_positions,
        "containers": container_positions,
        "edges": edges_out,
        "meta": {
            "body_x0": p.body_x0,
            "body_y0": p.body_y0,
            "body_x1": p.body_x1,
            "body_y1": p.body_y1,
            "n_boundaries": n_b,
            "n_containers_total": len(container_positions),
            "n_edges": len(edges_out),
            # R4 audit hooks
            "edge_label_halo_fill": p.edge_label_halo_fill,
            "edge_label_border_avoid_px": p.edge_label_border_avoid_px,
            "stretch_partial_rows": p.stretch_partial_rows,
            "measure_bump_min_w": p.measure_bump_min_w,
        },
    }
