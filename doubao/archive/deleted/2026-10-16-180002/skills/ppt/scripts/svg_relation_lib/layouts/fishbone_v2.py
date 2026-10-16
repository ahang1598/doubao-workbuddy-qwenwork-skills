"""Fishbone v2 layout · Ishikawa 风格 · hero canvas 1400×700

[R6 REBUILD 2026-09-13] 修 R3/R4/R5 三轮 P0 未修的 spine 断裂 · arrow 悬空 ·
effect box 缺失 · leader-line 悬空四大问题.

真正的 Ishikawa geometry:
  - spine: 水平粗线 · 左端 fish-tail 装饰 · 右端粗箭头指向 effect box
  - effect_box: 右端矩形 · 承载 problem/effect 标题 · 尾端箭头指入
  - ribs (category_slash): 从 spine anchor 出发 ±30° 斜线到 category card ·
    必要几何 · 不再进 subtract_level 名单
  - sub-bullets: 从 rib 上均匀分布 · 水平引线 · 端点圆点必落在 rib 上

输出位点 · preset 渲染 kind ∈ {
      spine, spine_arrow, spine_barb, spine_dot,
      effect_box,                          # ← 新增 · R6 · 右端方框
      category_slash, category_card, category_bar,
      primary_suspect_bar,
      sub_line, sub_dot_inner, sub_dot_outer, sub_label,
      sub_kicker,     # 类别编号 M1/M2/...
    }

Params:
    hero canvas: viewBox 1400×700 · body_x∈[70,1120] · body_y∈[110,690]
    spine_y = 330 (body 中部偏上)
    spine_x0 = 200 (fish-tail 起点), spine_x1 = 990 (给右侧 effect_box 留 200+30 px)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import math
from typing import Any, Dict, List, Optional

__all__ = ["fishbone_v2_layout", "LayoutOverflow", "FishboneParams"]


class LayoutOverflow(RuntimeError):
    pass


@dataclass
class FishboneParams:
    # canvas geometry (hero 1400×700)
    canvas_w: float = 1400.0
    canvas_h: float = 700.0
    spine_x0: float = 200.0
    spine_x1: float = 990.0
    spine_y: float = 330.0
    # category card 尺寸
    cat_card_w: float = 156.0
    cat_card_w_max: float = 240.0
    cat_card_h: float = 34.0
    # sub cause 竖间距
    sub_row_h: float = 44.0
    # sub label 靠近 rib 放置；引线至少覆盖短标签宽度，形成清晰的承托线。
    sub_line_len: float = 70.0
    sub_line_len_min: float = 48.0
    sub_label_gap: float = 22.0
    sub_line_pad: float = 4.0
    # 分支斜线的倾角
    branch_slope_dy: float = 120.0
    branch_slope_dx: float = 120.0
    # 分类间距
    cat_anchor_step: float = 110.0
    # 首个 category anchor 距 spine 起点的距离
    cat_anchor_start_offset: float = 130.0
    # sub-label 字号 (SVG-space) · 用于左边界安全推断
    sub_label_font_size: float = 15.0
    # sub-label 单行最大宽度；超过后拆成两行，避免跨到相邻 rib
    sub_label_max_width: float = 220.0
    # 仅在显式展示 primary suspect bar 时启用额外避让。
    avoid_primary_suspect_overlap: bool = False
    # 单字符宽度系数 · 估算文字宽度用 · font_size × 系数
    label_char_w_ratio: float = 0.58
    # SVG-space 左侧安全边界 · label 左端不能低于此 x
    left_safe_x: float = 20.0


def _iter_categories(tree: Any) -> List[Any]:
    root = getattr(tree, "root", None)
    if root is None:
        return []
    return list(getattr(root, "children", []) or [])


def _estimate_text_width(text: str, font_size: float, char_w_ratio: float = 0.58) -> float:
    """粗估文字 SVG-space 宽度 · 与 atomize_svg_to_slide 的 _char_width 逻辑对齐:
      - CJK (ord > 0x2E80): fs × 1.0
      - space:              fs × 0.35
      - upper / punct:      fs × 0.7
      - digit / lower:      fs × 0.55
    尾部再加 fs × 0.5 padding (与 atomizer 一致).
    """
    if not text:
        return 0.0
    total = 0.0
    for ch in text:
        cp = ord(ch)
        if cp > 0x2E80:  # CJK
            total += font_size * 1.0
        elif ch.isspace():
            total += font_size * 0.35
        elif ch in '·×→↑↓←◆◈§':
            total += font_size * 0.7
        elif ch.isupper():
            total += font_size * 0.7
        elif ch.isdigit():
            total += font_size * 0.55
        else:
            total += font_size * 0.55
    # padding · 与 atomizer 一致 · 避免右侧挤邻居
    return total + font_size * 0.5


def _wrap_label_lines(
    text: str,
    max_width: float,
    font_size: float,
    *,
    max_lines: int,
) -> List[str]:
    """Wrap text into visually balanced lines without orphaning the last word."""
    if not text:
        return []
    text_width = _estimate_text_width(text, font_size)
    if text_width <= max_width:
        return [text]

    source = text.strip()
    punctuation = ":：,，.。;；!?！？%)]}、/"
    has_space_breaks = any(char.isspace() for char in source)

    @lru_cache(maxsize=None)
    def solve(
        start: int,
        lines_left: int,
        target_width: float,
        allow_word_split: bool,
    ) -> Optional[tuple[float, tuple[str, ...]]]:
        while start < len(source) and source[start].isspace():
            start += 1
        if lines_left == 1:
            final = source[start:].strip()
            if final and _estimate_text_width(final, font_size) <= max_width:
                width = _estimate_text_width(final, font_size)
                return ((width - target_width) ** 2, (final,))
            return None

        best: Optional[tuple[float, List[str]]] = None
        for end in range(start + 1, len(source)):
            segment = source[start:end].rstrip()
            width = _estimate_text_width(segment, font_size)
            if width > max_width:
                break
            next_start = end
            while next_start < len(source) and source[next_start].isspace():
                next_start += 1
            if next_start >= len(source):
                break
            if source[next_start] in punctuation:
                continue
            natural_break = source[end].isspace() or source[end - 1] in "/-"
            if has_space_breaks and not natural_break and not allow_word_split:
                continue
            left_char = source[end - 1]
            right_char = source[next_start]
            splits_ascii_word = (
                left_char.isascii()
                and (left_char.isalnum() or left_char in "-_")
                and right_char.isascii()
                and (right_char.isalnum() or right_char in "-_")
            )
            if splits_ascii_word and not allow_word_split:
                continue
            split_penalty = max_width * max_width if splits_ascii_word else 0.0
            tail = solve(
                next_start,
                lines_left - 1,
                target_width,
                allow_word_split,
            )
            if tail is None:
                continue
            score = (width - target_width) ** 2 + split_penalty + tail[0]
            candidate = (score, (segment, *tail[1]))
            if best is None or candidate[0] < best[0]:
                best = candidate
        return best

    minimum_lines = max(2, math.ceil(text_width / max_width))
    for allow_word_split in (False, True):
        for line_count in range(minimum_lines, max_lines + 1):
            target_width = text_width / line_count
            result = solve(0, line_count, target_width, allow_word_split)
            if result is not None:
                return list(result[1])

    # The configured line cap is too small; keep the remaining text intact.
    return [source]


def fishbone_v2_layout(
    tree: Any,
    x0: float, y0: float, x1: float, y1: float,
    *,
    params: Optional[FishboneParams] = None,
) -> List[Dict[str, Any]]:
    """Dandelion Ishikawa layout.

    Data schema (Tree):
        root: TreeNode
          label: effect / problem statement
          extra:
            baseline: str (e.g. "820 ms")
            current: str (e.g. "1 132 ms")
            regression: str (e.g. "▲ +38.0%")
            onset: str (e.g. "Jul 12")
            baseline_note: str
            current_note: str
            regression_note: str
            onset_note: str
            problem_stat: str (e.g. "+38.0%")
            problem_kicker: str (e.g. "PROBLEM STATEMENT")
            problem_label: str (e.g. "p99 latency")
            problem_range: str (e.g. "820 ms → 1 132 ms")
          children: 3-6 category nodes
            label: category name (MODEL, SERVING, ...)
            group: hue key ("blue"/"orange"/"green"/"magenta"/"olive"/"cinnamon")
            extra:
              subtitle: str (e.g. "architecture · quant")
              pct: float (e.g. 22.0 → shown as "22%")
              primary_suspect: bool
              kicker: str (e.g. "M1", "M2", ...) — 若未传自动 M1..Mn
            children: N sub-cause nodes
              label: sub-cause text

    使用 hero canvas 1400×700 · body 内实际使用范围由 params 决定.
    """
    p = params or FishboneParams()
    root = getattr(tree, "root", None)
    if root is None:
        return []

    cats = _iter_categories(tree)
    n_cat = len(cats)
    if n_cat == 0:
        return []
    if n_cat > 6:
        raise LayoutOverflow(f"too many categories: {n_cat} > 6 · dandelion max 6")

    out: List[Dict[str, Any]] = []

    # ── 1. 先算 anchor · 决定 spine 实际终点 ───────
    # [FIX 2026-09-11] n_cat < 6 时 · 用与 6-cat 相同的固定 step (~128px) ·
    # 把 anchor 簇居中放置 · 避免 3-cat 时 anchors 平铺过宽把 slash + leader + label
    # 推出左画布边界 (旧逻辑 step=(970-330)/(n_cat-1) · 3-cat step=320 · slash_end_x=210 ·
    # label 右端 x=196 · 而 15pt label 宽 ~200px · 左端会落到 x < 0 越界)
    fixed_step = (p.spine_x1 - 20 - (p.spine_x0 + p.cat_anchor_start_offset)) / 5.0
    if n_cat == 1:
        anchor_xs = [(p.spine_x0 + p.spine_x1) / 2]
    elif n_cat >= 6:
        span_x0 = p.spine_x0 + p.cat_anchor_start_offset
        span_x1 = p.spine_x1 - 20
        step = (span_x1 - span_x0) / (n_cat - 1)
        anchor_xs = [span_x0 + step * i for i in range(n_cat)]
    else:
        # n_cat ∈ {2, 3, 4, 5}: 用 6-cat 的 fixed_step · 居中排布 anchor 簇
        span_center = (p.spine_x0 + p.spine_x1) / 2.0
        span_x0 = span_center - fixed_step * (n_cat - 1) / 2.0
        anchor_xs = [span_x0 + fixed_step * i for i in range(n_cat)]

    # ── Ishikawa 主脊柱 ─────────────────────────────
    # [R6 REBUILD 2026-09-13] 真正的 Ishikawa geometry:
    #   spine: 水平粗线 · 左端 (spine_x0) 至 effect_box 左缘 (spine_visual_end)
    #   spine_arrow: 大三角箭头 · 尖端指向 effect_box (RIGHT) · 与 dandelion 反向
    #   effect_box: 右端方框 · 承载 problem/effect 标题 · 由 preset 渲染
    # R5 之前 arrow 方向指错 (向左指空) + effect_box 从未 emit · 造成 spine 悬空.
    tip_x = p.spine_x0
    spine_visual_start = tip_x  # spine 起点在最左 anchor 之前 · 与 fish head 对齐

    # 鱼头 · 右端 · effect_box 按内容宽度收缩，避免短标签两侧留白过大。
    problem = (getattr(root, "extra", {}) or {}).get("problem", {}) or {}
    problem_label = str(problem.get("label", "")) or str(getattr(root, "label", ""))
    problem_stat = str(problem.get("stat", ""))
    problem_text_widths = [
        _estimate_text_width(problem_label, 17.0),
        _estimate_text_width(problem_stat, 30.0),
    ]
    effect_box_w = max(150.0, min(220.0, max(problem_text_widths, default=0.0) + 32.0))
    effect_box_h = 112.0
    effect_box_center_x = p.spine_x1 + 180.0
    effect_box_x = effect_box_center_x - effect_box_w / 2.0
    effect_box_y = p.spine_y - effect_box_h / 2.0
    # spine 在箭头尾部结束；箭头尖端与 effect box 留出窄缝，避免三者叠压。
    arrow_tip_x = effect_box_x - 8.0
    arrow_tail_x = arrow_tip_x - 32.0
    spine_visual_end = arrow_tail_x

    out.append({
        "kind": "spine",
        "x1": spine_visual_start, "y1": p.spine_y,
        "x2": spine_visual_end, "y2": p.spine_y,
    })

    # Effect box 先绘制，随后箭头覆盖其左边框，避免箭头尖端被边框截断。
    out.append({
        "kind": "effect_box",
        "x": effect_box_x, "y": effect_box_y,
        "w": effect_box_w, "h": effect_box_h,
    })

    # 大箭头指向 effect_box (右向) · 三角形独立连接，不覆盖 spine 或 box。
    out.append({
        "kind": "spine_arrow",
        "d": f"M {arrow_tip_x} {p.spine_y} "
             f"L {arrow_tail_x} {p.spine_y - 17} "
             f"L {arrow_tail_x} {p.spine_y + 17} Z",
    })

    # 鱼头 · 左端 · 装饰性 "fish-tail" 双分叉 · 视觉更 Ishikawa
    fish_tail_x = spine_visual_start
    out.append({
        "kind": "spine_arrow",
        "d": f"M {fish_tail_x} {p.spine_y} "
             f"L {fish_tail_x - 22} {p.spine_y - 14} "
             f"L {fish_tail_x - 10} {p.spine_y} "
             f"L {fish_tail_x - 22} {p.spine_y + 14} Z",
    })

    # 箭羽装饰 (5 根细线) · 位于左端 fish-tail 内部
    for i, dy in enumerate([-10, -5, 0, 5, 10]):
        out.append({
            "kind": "spine_barb",
            "x1": fish_tail_x - 18, "y1": p.spine_y + dy,
            "x2": fish_tail_x - 12, "y2": p.spine_y + dy * (-0.5),
        })

    # ── 2b. 预扫描 · 找出顶侧 primary_suspect chip 的 x/y 范围 ────
    # [FIX 2026-09-11 R3] 顶侧其他分支的 sub label (尤其 r 大 · 靠 card 一端) 单行 baseline
    # y = line_y - 6 · text 主要在 line 上方 · 当 label 长时 x 端向左延伸 · 可能横跨
    # MATERIAL primary_suspect chip 的 x 范围 · 造成 label 与 chip y/x 双重叠.
    # 预先算出 chip 的 (x0, x1, y_top, y_bot) · 后续 label 定位时若冲突就把 baseline 下移到
    # chip 底以下.
    # [FIX 2026-09-11 R4] 额外算 primary_suspect 分支 wrap block 底 y (SVG-space) ·
    # 后续顶侧非 primary 分支 sub 与其 x-overlap 时可下移到 wrap block 底之下 ·
    # 避免跨分支 label-label 撞 y (如 MATERIAL Filter L0 vs METHOD QA sampling).
    top_primary_chip: Optional[Dict[str, float]] = None
    for idx_scan, cat_scan in enumerate(cats):
        # 默认 subtract level 不显示 primary_suspect_bar，无需为不可见元素挪动标签。
        if not getattr(p, "avoid_primary_suspect_overlap", False):
            break
        side_scan = -1 if (idx_scan % 2 == 0) else 1
        if side_scan != -1:
            continue
        extra_scan = getattr(cat_scan, "extra", {}) or {}
        if not bool(extra_scan.get("primary_suspect", False)):
            continue
        anchor_x_scan = anchor_xs[idx_scan]
        slash_end_x_scan = anchor_x_scan - p.branch_slope_dx
        slash_end_y_scan = p.spine_y + side_scan * p.branch_slope_dy
        card_y_scan = slash_end_y_scan - p.cat_card_h - 8
        # chip rect (preset primary_suspect_bar): x=card_x, y=card_y+42, w=cat_card_w (可能被 preset 撑宽 · 保守用 148 SVG)
        # 实际 preset 会把 chip 加宽 到 text_w+padding · 保守取 cat_card_w × 1.4 覆盖大部分情况
        card_x_scan = slash_end_x_scan - p.cat_card_w_max / 2
        chip_w_est = p.cat_card_w_max
        chip_cx_scan = card_x_scan + p.cat_card_w_max / 2
        chip_x0 = chip_cx_scan - chip_w_est / 2
        chip_x1 = chip_cx_scan + chip_w_est / 2
        chip_y_top = card_y_scan + p.cat_card_h + 6
        chip_y_bot = chip_y_top + 18
        # [R4] 估算 primary 分支 wrap block 底 y-svg · 独立复现阶段 1+2 shift
        subs_scan = list(getattr(cat_scan, "children", []) or [])
        n_sub_scan = len(subs_scan)
        block_y_bot = chip_y_bot  # 默认无 sub 时就是 chip 底
        if n_sub_scan > 0:
            fs_ps = p.sub_label_font_size
            anchor_y_scan = p.spine_y
            if n_sub_scan == 1:
                ratios_ps = [0.55]
            else:
                r_start_ps = 0.22 if n_sub_scan <= 3 else 0.16
                ratios_ps = [
                    r_start_ps + (0.78 - r_start_ps) * (jj / (n_sub_scan - 1))
                    for jj in range(n_sub_scan)
                ]
            # per-sub 预扫 (与主 loop 一致 · 但简化)
            orig_line_ys_ps = []
            will_wraps_ps = []
            for jj, sub_ps in enumerate(subs_scan):
                lb = str(getattr(sub_ps, "label", ""))
                r_ps = ratios_ps[jj]
                end_x_ps = anchor_x_scan + (slash_end_x_scan - anchor_x_scan) * r_ps
                ly_ps = anchor_y_scan + (slash_end_y_scan - anchor_y_scan) * r_ps
                orig_line_ys_ps.append(ly_ps)
                line_x2_ps = end_x_ps - p.sub_line_len
                text_w_ps = _estimate_text_width(lb, fs_ps, p.label_char_w_ratio)
                lleft_ps = line_x2_ps - 6 - text_w_ps
                ww = text_w_ps > p.sub_label_max_width
                if not ww and lleft_ps < p.left_safe_x:
                    deficit_ps = p.left_safe_x - lleft_ps
                    ms_ps = p.sub_line_len - p.sub_line_len_min
                    as_ps = min(deficit_ps, ms_ps)
                    line_x2_a = line_x2_ps + as_ps
                    lleft_a = line_x2_a - 6 - text_w_ps
                    if lleft_a < p.left_safe_x:
                        ww = True
                will_wraps_ps.append(ww)
            # 阶段 1: branch_shift
            branch_shift_ps = 0.0
            for jj in range(n_sub_scan):
                if will_wraps_ps[jj]:
                    orig_l0 = orig_line_ys_ps[jj] - 13
                    min_l0 = chip_y_bot + 12.0 + fs_ps * 0.75
                    needed = min_l0 - orig_l0
                else:
                    orig_single = orig_line_ys_ps[jj] - 6
                    text_top = orig_single - fs_ps * 0.75
                    if text_top >= chip_y_bot + 15.0:
                        needed = 0.0
                    else:
                        needed = (chip_y_bot + 15.0 + fs_ps * 0.75) - orig_single
                if needed > branch_shift_ps:
                    branch_shift_ps = needed
            per_shift_ps = [branch_shift_ps] * n_sub_scan
            # 阶段 2: 累积
            wrap_l1_bot_off_ps = 12 + fs_ps * 1.6 - fs_ps * 0.75  # 24.75
            wrap_l0_top_off_ps = -13 - fs_ps * 0.75  # -24.25
            single_top_off_ps = -6 - fs_ps * 0.75  # -17.25
            gap_ps = 4.0
            for j_up in range(n_sub_scan - 1, 0, -1):
                if will_wraps_ps[j_up]:
                    upper_bot = orig_line_ys_ps[j_up] + per_shift_ps[j_up] + wrap_l1_bot_off_ps
                else:
                    upper_bot = orig_line_ys_ps[j_up] + per_shift_ps[j_up] - 6 + fs_ps * 1.6 - fs_ps * 0.75
                if will_wraps_ps[j_up - 1]:
                    lower_top = orig_line_ys_ps[j_up - 1] + per_shift_ps[j_up - 1] + wrap_l0_top_off_ps
                else:
                    lower_top = orig_line_ys_ps[j_up - 1] + per_shift_ps[j_up - 1] + single_top_off_ps
                if lower_top < upper_bot + gap_ps:
                    per_shift_ps[j_up - 1] += (upper_bot + gap_ps) - lower_top
            # 最深 y = sub[0] (最下 sub) L1_bot or single_bot
            if will_wraps_ps[0]:
                block_y_bot = orig_line_ys_ps[0] + per_shift_ps[0] + wrap_l1_bot_off_ps
            else:
                block_y_bot = orig_line_ys_ps[0] + per_shift_ps[0] - 6 + fs_ps * 1.6 - fs_ps * 0.75
        top_primary_chip = {
            "x0": chip_x0, "x1": chip_x1,
            "y_top": chip_y_top, "y_bot": chip_y_bot,
            "block_y_bot": block_y_bot,
        }
        break

    # ── 3. 遍历每个 category ──────────────────
    for idx, cat in enumerate(cats):
        side = -1 if (idx % 2 == 0) else 1  # 偶=上, 奇=下
        anchor_x = anchor_xs[idx]
        anchor_y = p.spine_y
        hue = getattr(cat, "group", "") or "blue"
        cat_label = str(getattr(cat, "label", ""))
        cat_id = getattr(cat, "id", f"c{idx}") or f"c{idx}"
        cat_extra = getattr(cat, "extra", {}) or {}
        # Round6: fishbone cards keep only the category title and percentage.
        # The subtitle was rendered as small gray text and made the diagram too dense.
        subtitle = ""
        pct = cat_extra.get("pct", None)
        pct_str = f"{pct:.0f}%" if pct is not None else ""
        primary_suspect = bool(cat_extra.get("primary_suspect", False))
        kicker = cat_extra.get("kicker", f"M{idx + 1}")
        category_title = " ".join(part for part in (cat_label, pct_str) if part)
        title_w = _estimate_text_width(category_title, 15.0, p.label_char_w_ratio)
        subtitle_font_size = 10.0
        card_content_w = title_w
        card_w = max(p.cat_card_w, min(p.cat_card_w_max, card_content_w + 24.0))
        card_inner_w = max(1.0, card_w - 24.0)
        title_lines = (
            [category_title]
            if title_w <= card_inner_w
            else _wrap_label_lines(
                category_title, card_inner_w, 15.0, max_lines=2
            )
        )
        title_lines = [line for line in title_lines if line.strip()] or [category_title]
        subtitle_lines: List[str] = []
        title_font_size = 13.0
        title_step = 14.0
        title_block_h = (
            title_font_size + max(0, len(title_lines) - 1) * title_step
        )
        subtitle_step = 13.0
        subtitle_block_h = len(subtitle_lines) * subtitle_step
        visible_block_h = title_block_h + subtitle_block_h
        card_h = max(
            p.cat_card_h,
            visible_block_h + 12.0,
        )
        title_baseline_y = (card_h - visible_block_h) / 2.0 + title_font_size * 0.85
        text_line_count = len(title_lines) + len(subtitle_lines)
        if text_line_count:
            if subtitle_lines:
                last_baseline_y = (
                    title_baseline_y
                    + len(title_lines) * title_step
                    + (len(subtitle_lines) - 1) * subtitle_step
                )
                last_font_size = subtitle_font_size
            else:
                last_baseline_y = (
                    title_baseline_y + (len(title_lines) - 1) * title_step
                )
                last_font_size = 13.0
            accent_rel_y = max(4.0, title_baseline_y - 13.0 * 0.75 - 1.0)
            accent_rel_bottom = min(
                card_h - 2.0,
                last_baseline_y + last_font_size * 0.35 + 4.0,
            )
            accent_h = max(18.0, accent_rel_bottom - accent_rel_y)
        else:
            accent_rel_y = 0.0
            accent_h = card_h

        subs = list(getattr(cat, "children", []) or [])
        n_sub = len(subs)
        if n_sub > 5:
            raise LayoutOverflow(f"too many sub-causes on {cat_label}: {n_sub} > 5")

        # 斜线终点 (category card 侧)
        slash_end_x = anchor_x - p.branch_slope_dx
        slash_end_y = p.spine_y + side * p.branch_slope_dy

        card_x = slash_end_x - card_w / 2
        if side == -1:
            card_y = slash_end_y - card_h - 8
        else:
            card_y = slash_end_y + 8

        out.append({
            "kind": "category_slash",
            "hue": hue,
            "x1": anchor_x, "y1": anchor_y,
            "x2": slash_end_x, "y2": slash_end_y,
            "side": side,
            "index": idx,
        })

        # M1/M2 kicker on slash · 放在靠 category card 一端 (斜线 85% 处)
        # 避开 sub label 引线区间 (25%-75%)
        kicker_pos_x = anchor_x + (slash_end_x - anchor_x) * 0.88
        kicker_pos_y = anchor_y + (slash_end_y - anchor_y) * 0.88
        if side == -1:
            # 上分支 · kicker 在斜线右侧 (card 内侧)
            kicker_pos_x += 12
            kicker_pos_y += 4
            # [FIX 2026-09-11 R2] primary_suspect 时 chip bar 位于 card 下方 y∈[card_y+42, card_y+60]
            # kicker 默认 baseline 位置会撞进 chip bar 底缘 · 推 kicker 再下移 18 SVG-px
            # (=slide 空间 12px · 保证 M-kicker text-top 与 chip 底部 ≥ 4pt clean gap)
            if primary_suspect:
                kicker_pos_y += 18
        else:
            # 下分支 · kicker 在斜线右侧
            kicker_pos_x += 12
            kicker_pos_y -= 4
        out.append({
            "kind": "sub_kicker",
            "hue": hue,
            "x": kicker_pos_x, "y": kicker_pos_y,
            "label": kicker,
            "side": side,
        })

        # category card
        out.append({
            "kind": "category_card",
            "hue": hue,
            "x": card_x, "y": card_y,
            "w": card_w, "h": card_h,
            "label": cat_label,
            "title": category_title,
            "title_lines": title_lines,
            "title_y": card_y + title_baseline_y,
            "title_step": title_step,
            "subtitle": subtitle,
            "subtitle_lines": subtitle_lines,
            "subtitle_font_size": subtitle_font_size,
            "accent_y": card_y + accent_rel_y,
            "accent_h": accent_h,
            "pct": pct_str,
            "primary_suspect": primary_suspect,
            "side": side,
            "index": idx,
            "id": cat_id,
        })

        # primary suspect 高亮条 (紧贴 card 下方)
        # [FIX 2026-09-11] 顶部 side (side=-1) 原本把 bar 放 card 上方 (card_y - 24) ·
        # 与 KPI band (y=[132,166]) 竖向重叠 14px. 改为无论上下 side · bar 都放在 card 下方 ·
        # 上分支时 bar 位于 card 与 spine 之间 · 不会撞到 KPI 带.
        if primary_suspect:
            bar_y = card_y + card_h + 6
            out.append({
                "kind": "primary_suspect_bar",
                "hue": hue,
                "x": card_x, "y": bar_y,
                "w": card_w, "h": 18,
                "label": "★ PRIMARY SUSPECT",
                "side": side,
            })

        # ── 4. sub-cause 引线 · 沿斜线均匀分布 ─────
        # dandelion 里 3 个 sub 分布在斜线 65% / 45% / 25% 处 (自 spine 起 · 靠 category 一侧)
        # 泛化: 充分使用 rib 两端空间，避免末级分支在中段堆叠。
        if n_sub == 0:
            continue
        if n_sub == 1:
            ratios = [0.55]
        else:
            if side == -1:
                r_start, r_end = (0.22 if n_sub <= 3 else 0.16), 0.78
            else:
                r_start, r_end = (0.36 if n_sub <= 3 else 0.26), 0.92
            ratios = [r_start + (r_end - r_start) * (j / (n_sub - 1)) for j in range(n_sub)]

        # [FIX 2026-09-11 R4] 计算本 category 分支每个 sub 的 y-shift (per_sub_shift[j])
        # ---------------------------------------------------------------
        # R3 的问题: 每个 sub 独立算 shift · 全部拉到同一 baseline min_l0_y ·
        #   → sub 之间的原有 y-spread (由 line_y_j 差异决定) 被抹平 · label-label 堆叠.
        # R4 修法: 分两阶段
        #   阶段 1 · 统一 branch_shift 保 chip 底: 找最需要 shift 的那个 sub 的 shift_i ·
        #     用最大 shift 统一下移每个 sub · 保持 sub 之间的原有 line_y 差 · 不抹平.
        #   阶段 2 · 从最上 sub (j=n-1) 到最下 sub (j=0) 累积检查 wrap L1_bot vs prev L0_top ·
        #     若相邻 sub 天然 y-spread 不够 (5-sub 全 wrap 场景 · L0 delta ≈ 22.5 SVG ·
        #     不足以容下 wrap L1 + label height) · 则再向下挤压 sub[j-1] 及以下 · 强制
        #     sub[j-1] L0_top ≥ sub[j] L1_bot + gap. 只对 wrap sub 之间做检查.
        # 触发条件与 R3 一致: side == -1 且 top_primary_chip 存在.
        per_sub_shift: List[float] = [0.0] * n_sub
        sub_will_wrap: List[bool] = [False] * n_sub
        sub_orig_line_y: List[float] = [0.0] * n_sub
        if side == -1 and top_primary_chip is not None:
            fs_pre = p.sub_label_font_size
            chip_y_bot_pre = top_primary_chip["y_bot"]
            # (阶段 0) 预扫每 sub · 判 wrap 与否 · 记 orig line_y
            branch_shift = 0.0
            for j_pre, sub_pre in enumerate(subs):
                sub_label_pre = str(getattr(sub_pre, "label", ""))
                r_pre = ratios[j_pre]
                end_x_pre = anchor_x + (slash_end_x - anchor_x) * r_pre
                line_y_pre = anchor_y + (slash_end_y - anchor_y) * r_pre
                sub_orig_line_y[j_pre] = line_y_pre
                line_x2_pre = end_x_pre - p.sub_line_len
                text_w_pre = _estimate_text_width(sub_label_pre, fs_pre, p.label_char_w_ratio)
                label_left_pre = line_x2_pre - 6 - text_w_pre
                will_wrap = text_w_pre > p.sub_label_max_width
                if not will_wrap and label_left_pre < p.left_safe_x:
                    deficit_pre = p.left_safe_x - label_left_pre
                    max_shift_pre = p.sub_line_len - p.sub_line_len_min
                    actual_shift_pre = min(deficit_pre, max_shift_pre)
                    line_x2_after = line_x2_pre + actual_shift_pre
                    label_left_after = line_x2_after - 6 - text_w_pre
                    if label_left_after < p.left_safe_x:
                        will_wrap = True
                sub_will_wrap[j_pre] = will_wrap
                # 计算该 sub 需要的最小 shift (让 label 位于 chip 下)
                # 只避 chip · 不跨分支避 wrap block · 避免顶侧 sub 侵入底侧空间.
                if will_wrap:
                    orig_l0_y = line_y_pre - 13  # 与主循环一致 (R4 改 -12→-13)
                    min_l0_y_pre = chip_y_bot_pre + 12.0 + fs_pre * 0.75
                    needed = min_l0_y_pre - orig_l0_y
                else:
                    orig_single_y = line_y_pre - 6
                    if primary_suspect:
                        x_overlap_pre = True
                    else:
                        label_x1_pre = line_x2_pre - 6
                        label_x0_pre = label_x1_pre - text_w_pre
                        x_overlap_pre = (
                            label_x0_pre < top_primary_chip["x1"]
                            and label_x1_pre > top_primary_chip["x0"]
                        )
                    if not x_overlap_pre:
                        needed = 0.0
                    else:
                        text_top_pre = orig_single_y - fs_pre * 0.75
                        if text_top_pre >= chip_y_bot_pre + 15.0:
                            needed = 0.0
                        else:
                            min_single_y = chip_y_bot_pre + 15.0 + fs_pre * 0.75
                            needed = min_single_y - orig_single_y
                if needed > branch_shift:
                    branch_shift = needed
            # (阶段 1) 每个 sub 应用 branch_shift · 保持相对 y 差
            for j_pre in range(n_sub):
                per_sub_shift[j_pre] = branch_shift

            # (阶段 2) 累积调整 · 从最上 sub 到最下 sub 检查相邻 y-overlap
            # side=-1 时 · j 越大越上 (line_y 越小). 从 j=n_sub-1 到 j=1 · 检查
            # sub[j-1] 是否需向下 push (即 orig y 更大方向) · 让 sub[j-1] L0_top
            # ≥ sub[j] L1_bot + gap. 只考虑 wrap sub 的 L1_bot (single-line 高度小 · 一般够).
            # SVG-space label 高度 ≈ fs * 1.6 = 15 * 1.6 = 24 SVG
            # wrap L1 y = line_y + 12 · L1_top ≈ (line_y+12) - fs*0.75 = line_y + 0.75
            # L1_bot = L1_top + fs*1.6 = line_y + 0.75 + 24 = line_y + 24.75
            # wrap L0 y = line_y - 13 · L0_top ≈ line_y - 13 - fs*0.75 = line_y - 24.25
            # 需 sub[j-1] L0_top ≥ sub[j] L1_bot + gap (gap=4 SVG)
            fs_wrap = p.sub_label_font_size
            wrap_l1_bot_off = 12 + fs_wrap * 1.6 - fs_wrap * 0.75  # = 12 + 24 - 11.25 = 24.75
            wrap_l0_top_off = -13 - fs_wrap * 0.75  # = -24.25
            single_top_off = -6 - fs_wrap * 0.75  # = -17.25
            gap_svg = 4.0
            for j_up in range(n_sub - 1, 0, -1):
                # sub[j_up] 在上 · sub[j_up-1] 在下
                # sub[j_up] 最终位置 · L1_bot (若 wrap) 或 single_bot
                if sub_will_wrap[j_up]:
                    upper_bot = (sub_orig_line_y[j_up] + per_sub_shift[j_up]) + wrap_l1_bot_off
                else:
                    # single: text_top = orig_single_y - fs*0.75 · bot = top + fs*1.6
                    upper_bot = (sub_orig_line_y[j_up] + per_sub_shift[j_up]) - 6 + fs_wrap * 1.6 - fs_wrap * 0.75
                # sub[j_up-1] L0_top or single_top
                if sub_will_wrap[j_up - 1]:
                    lower_top = (sub_orig_line_y[j_up - 1] + per_sub_shift[j_up - 1]) + wrap_l0_top_off
                else:
                    lower_top = (sub_orig_line_y[j_up - 1] + per_sub_shift[j_up - 1]) + single_top_off
                # 需 lower_top ≥ upper_bot + gap
                if lower_top < upper_bot + gap_svg:
                    extra = (upper_bot + gap_svg) - lower_top
                    per_sub_shift[j_up - 1] += extra

        for j, sub in enumerate(subs):
            sub_label = str(getattr(sub, "label", ""))
            r = ratios[j]
            end_x_on_slash = anchor_x + (slash_end_x - anchor_x) * r
            end_y_on_slash = anchor_y + (slash_end_y - anchor_y) * r

            # 水平引线: 从 slash 向左延伸，并覆盖标签宽度，形成承托线。
            line_x1 = end_x_on_slash
            line_y = end_y_on_slash

            # [FIX 2026-09-11 R2] 长英文 label 越出左边界的 regression 修复:
            # 估算 label SVG-space 宽度 · text-anchor=end 的锚点在 (line_x2 - 6):
            #   label_left = line_x2 - 6 - text_w
            # (a) 若 label_left < left_safe_x · 先把 line_x2 向右压缩 · 缩短 sub_line_len
            #     (但至少保留 sub_line_len_min 长度, 让 leader 仍可见).
            # (b) 若压缩到最小仍越界 · 把 label 切成两行 · 每行宽度约半 ·
            #     line1 在原 line_y 略上方 · line2 在略下方 · 视觉紧凑但不裁字.
            text_w = _estimate_text_width(sub_label, p.sub_label_font_size, p.label_char_w_ratio)
            wrap_lines: Optional[List[str]] = (
                _wrap_label_lines(
                    sub_label,
                    p.sub_label_max_width,
                    p.sub_label_font_size,
                    max_lines=2,
                )
                if text_w > p.sub_label_max_width
                else None
            )
            fitted_text_w = (
                max(
                    _estimate_text_width(line, p.sub_label_font_size, p.label_char_w_ratio)
                    for line in wrap_lines
                )
                if wrap_lines
                else text_w
            )
            label_x = end_x_on_slash - p.sub_label_gap
            label_left = label_x - fitted_text_w
            if label_left < p.left_safe_x:
                if label_left < p.left_safe_x and wrap_lines is None:
                    wrap_lines = _wrap_label_lines(
                        sub_label,
                        max(60.0, label_x - p.left_safe_x),
                        p.sub_label_font_size,
                        max_lines=2,
                    )
                    fitted_text_w = max(
                        _estimate_text_width(ln, p.sub_label_font_size, p.label_char_w_ratio)
                        for ln in wrap_lines
                    )
                label_x = min(
                    end_x_on_slash - p.sub_label_gap,
                    p.left_safe_x + fitted_text_w,
                )
                label_left = label_x - fitted_text_w

            line_span = max(
                p.sub_line_len,
                fitted_text_w + p.sub_label_gap + p.sub_line_pad,
            )
            line_x2 = max(p.left_safe_x, end_x_on_slash - line_span)

            out.append({
                "kind": "sub_line",
                "hue": hue,
                "x1": line_x1, "y1": line_y,
                "x2": line_x2, "y2": line_y,
            })
            # sub 端点 (在 slash 侧, 小实心圆)
            out.append({
                "kind": "sub_dot_inner",
                "hue": hue,
                "cx": line_x1, "cy": line_y, "r": 1.6,
            })
            # sub label 端点 (在 label 侧, 大空心圆)
            out.append({
                "kind": "sub_dot_outer",
                "hue": hue,
                "cx": line_x1, "cy": line_y, "r": 2.4,
            })
            # sub label · 支持两行 wrap (长英文 label 时)
            if wrap_lines is None:
                single_y = line_y - 8
                # [FIX 2026-09-11 R4] 顶侧 sub label (单行) · 应用 per-sub y-shift
                # (取代 R3 每 sub 独立 shift 到同一 baseline 造成的 label-label 堆叠).
                # per_sub_shift[j] 已在 sub 循环前预扫算好 · 阶段1 保 chip 底 ·
                # 阶段2 累积调整避免相邻 sub L1 vs L0 y-overlap.
                if per_sub_shift[j] > 0.0:
                    single_y += per_sub_shift[j]
                out.append({
                    "kind": "sub_label",
                    "hue": hue,
                    "x": label_x, "y": single_y,
                    "label": sub_label,
                    "parent": cat_id,
                    "index": j,
                })
            else:
                # 两行均置于引线上方，保留接近一行字高的间距。
                wrap_l0_y = line_y - 26
                wrap_l1_y = line_y - 8
                # [FIX 2026-09-11 R4] 顶侧 primary_suspect 分支 wrap · 应用 per-sub y-shift
                # (取代 R3 每 sub 独立 shift 到同一 baseline 造成的 label-label 堆叠).
                # per_sub_shift[j] 已在 sub 循环前预扫算好 · 阶段1 保 chip 底 ·
                # 阶段2 累积调整避免相邻 sub L1 vs L0 y-overlap.
                if per_sub_shift[j] > 0.0:
                    wrap_l0_y += per_sub_shift[j]
                    wrap_l1_y += per_sub_shift[j]
                out.append({
                    "kind": "sub_label",
                    "hue": hue,
                    "x": label_x, "y": wrap_l0_y,
                    "label": wrap_lines[0],
                    "parent": cat_id,
                    "index": j,
                    "wrap_line": 0,
                })
                out.append({
                    "kind": "sub_label",
                    "hue": hue,
                    "x": label_x, "y": wrap_l1_y,
                    "label": wrap_lines[1],
                    "parent": cat_id,
                    "index": j,
                    "wrap_line": 1,
                })

    # ── 5. spine 上的类别端点小圆 (每 category anchor 一个圆) ────
    for idx, ax in enumerate(anchor_xs):
        cat = cats[idx]
        hue = getattr(cat, "group", "") or "blue"
        out.append({
            "kind": "spine_dot",
            "hue": hue,
            "cx": ax, "cy": p.spine_y, "r": 3.4,
        })

    return out
