"""svg_lib/charts/waterfall.py

统一 API:  draw_waterfall(data, variant, palette, ...) -> str (SVG)

Data schema:
    data = {
        "steps": [(label, value, kind), ...]
    }
    kind ∈ {"total", "pos", "neg"}
    value: number  —  对 stacked_gradient variant，value 可以是
        list[(sub_label, sub_val)]（该 step 的子类别拆解，累加得该 step 的净值）

Variants (5 共享同一份 data):
    - default_flat        经典垂直瀑布，total 从零基线画，pos/neg 从 running 连接
    - subtotal_bridge     检测 data 里中间 kind='total' 的步骤，作为「小计」（更醒目）
    - cross_axis          支持累计值穿过 0 轴（自动检测正负 axis）
    - horizontal          横向瀑布（bar y=category, x=cumulative）
    - stacked_gradient    每个 pos/neg 步骤按子类别堆叠 + 渐变（读取 list value）
                          若某 step 的 value 是 scalar，则自动拆成单段
"""
from __future__ import annotations

import math

from ._shared import (

    resolve_palette,
    xesc,
    auto_font_size,
    viewbox_fs,
    svg_open,
    svg_close,
    _rgba_with_alpha,
    rgb_tuple,
    is_dark_palette,
)


from .._common import (_ACC, _INK, _INK2, _INK6, _prepend_bg_if_dark, _punchy_title_ink, _render_title_block, _resolve_font, _resolve_palette, _rgba_with_alpha, _wrap_with_auto_viewbox, _xesc, _variant_is_classic, _dispatch_to_svg_lib)
BODY_FONT = "Inter, sans-serif"
HEAD_FONT = "Georgia, serif"


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------

def draw_waterfall(
    data: dict,
    variant: str = "default_flat",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 540,
    title: str = None,
    subtitle: str = None,
) -> str:
    steps = data.get("steps") or []
    if not steps or len(steps) < 2:
        raise ValueError("draw_waterfall: data['steps'] needs at least 2 entries")

    for st in steps:
        if len(st) < 3:
            raise ValueError(f"draw_waterfall: each step must be (label, value, kind); got {st!r}")
        if st[2] not in ("total", "pos", "neg"):
            raise ValueError(f"draw_waterfall: kind must be total/pos/neg; got {st[2]!r}")

    pal = resolve_palette(palette)

    if variant == "default_flat":
        body_fn = _draw_default_flat
    elif variant == "subtotal_bridge":
        body_fn = _draw_subtotal_bridge
    elif variant == "cross_axis":
        body_fn = _draw_cross_axis
    elif variant == "horizontal":
        body_fn = _draw_horizontal
    elif variant == "stacked_gradient":
        body_fn = _draw_stacked_gradient
    else:
        raise ValueError(
            f"unknown variant {variant!r}. Supported: default_flat, subtotal_bridge, "
            "cross_axis, horizontal, stacked_gradient"
        )

    ctx = _Ctx(steps=steps, pal=pal, W=float(width), H=float(height),
               title=title, subtitle=subtitle)
    body = body_fn(ctx)

    return (
        svg_open(0, 0, ctx.W, ctx.H, bg=pal["bg"])
        + ctx.defs_svg()
        + _header(ctx)
        + body
        + svg_close()
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class _Ctx:
    def __init__(self, steps, pal, W, H, title, subtitle):
        self.steps = steps
        self.pal = pal
        self.W = W
        self.H = H
        self.title = title
        self.subtitle = subtitle
        self.n = len(steps)
        # 字号自适应：viewBox 尺寸 × 数据规模 双重驱动
        self.fs_label = viewbox_fs(W, H, self.n, role_mult=1.0)   # step 名字
        self.fs_value = viewbox_fs(W, H, self.n, role_mult=1.05)  # 数值（数字要大点）
        self.fs_tick = viewbox_fs(W, H, self.n, role_mult=0.85)   # Y 轴刻度
        self.header_h = 50 if title else 20
        if subtitle:
            self.header_h += 18
        self.plot_top = self.header_h + 20
        self.plot_bot = self.H - 60
        self.plot_h = self.plot_bot - self.plot_top
        self._defs = []

    def add_def(self, s):
        self._defs.append(s)

    def defs_svg(self):
        return "<defs>" + "".join(self._defs) + "</defs>" if self._defs else ""


def _header(ctx: _Ctx) -> str:
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    parts = []
    ML = 60
    if ctx.title:
        parts.append(
            f'<text x="{ML}" y="30" font-family="{HEAD_FONT}" font-size="20" '
            f'font-weight="600" fill="{ink}" letter-spacing=".03em">{xesc(ctx.title)}</text>'
        )
    if ctx.subtitle:
        y = 48 if ctx.title else 30
        parts.append(
            f'<text x="{ML}" y="{y}" font-family="{BODY_FONT}" font-size="11" '
            f'fill="{mut}" letter-spacing=".14em">{xesc(ctx.subtitle)}</text>'
        )
    if ctx.title:
        parts.append(
            f'<line x1="{ML}" y1="{ctx.header_h}" x2="{ctx.W - 30}" y2="{ctx.header_h}" '
            f'stroke="{ink}" stroke-width="0.6" opacity="0.4"/>'
        )
    return "".join(parts)


def _fmt(v):
    v = float(v)
    if abs(v) >= 10000:
        return f"{v:,.0f}"
    if float(int(v)) == v:
        return f"{int(v)}"
    return f"{v:.1f}"


def _step_net(value):
    """规整化 step 的 value: 支持 scalar 或 list[(sub_label, sub_val)]。返回 (net, segments)。

    segments: list[(sub_label, sub_val_abs)]（正数），供 stacked variant 使用；
              对 scalar 输入，返回 [("", abs(net))]。
    """
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
        segments = [(str(s[0]), float(s[1])) for s in value]
        net = sum(v for _, v in segments)
        return net, segments
    net = float(value)
    return net, [("", abs(net))]


def _compute_layout(steps):
    """把 steps 展开成 [(label, kind, sv, ev, disp, segments)]。

    - sv: start (running before)
    - ev: end (running after)
    - disp: signed magnitude for this step (for label)
    - segments: [(sub_label, abs_val), ...]
    """
    running = 0.0
    layout = []
    for label, val, kind in steps:
        net, segs = _step_net(val)
        if kind == "total":
            layout.append((str(label), kind, 0.0, net, net, segs))
            running = net
        elif kind == "pos":
            n = abs(net)
            layout.append((str(label), kind, running, running + n, n, segs))
            running += n
        else:  # neg
            n = abs(net)
            layout.append((str(label), kind, running, running - n, -n, segs))
            running -= n
    return layout


def _nice_ticks(v_min, v_max, target=5):
    span = max(1e-9, v_max - v_min)
    step = span / target
    mag = 10 ** math.floor(math.log10(step))
    frac = step / mag
    for nice in (1, 2, 2.5, 5, 10):
        if frac <= nice:
            tick_step = nice * mag
            break
    else:
        tick_step = 10 * mag
    v_lo = math.floor(v_min / tick_step) * tick_step
    v_hi = math.ceil(v_max / tick_step) * tick_step
    ticks = []
    t = v_lo
    while t <= v_hi + 1e-6:
        ticks.append(t)
        t += tick_step
    return v_lo, v_hi, ticks


def _colors(pal, kind):
    """Return the fill color for a bar of a given kind.

    Pos and neg MUST be visually distinct — the palette's `series[1]` can
    coincide with `accent` (e.g. exec_navy has both at `rgba(180,120,45,1)`),
    which would collapse pos/neg into one color. We therefore:
      * prefer `ink6` (a mid-gray derived from ink) for pos, which is the
        same feel the classic path uses (`c_pos_bar` = ink @ 0.6)
      * fall back to a series color only if it differs materially from accent
      * neg always returns `accent` (usually red/orange), and callers add a
        stroke/hatch so the shape is doubly distinct.
    """
    ink = pal["ink"]
    acc = pal["accent"]
    if kind == "total":
        return ink
    if kind == "pos":
        # Try series[1] but only if it's clearly different from accent.
        series = pal.get("series") or []
        cand = None
        acc_rgb = rgb_tuple(acc)
        for c in series[1:]:
            c_rgb = rgb_tuple(c)
            # squared color distance in RGB space; ~60 threshold ≈ perceptibly different
            dist2 = sum((a - b) ** 2 for a, b in zip(acc_rgb, c_rgb))
            if dist2 > 60 * 60:
                cand = c
                break
        if cand is None:
            # Fall back to a neutral ink-tinted mid-gray (matches classic pos_bar look)
            cand = pal.get("ink6") or _rgba_with_alpha(ink, 0.6)
        return cand
    # neg
    return acc


# ---------------------------------------------------------------------------
# 1) default_flat — vertical waterfall
# ---------------------------------------------------------------------------

def _est_text_width(s: str, fs: float) -> float:
    """Rough monospace-ish estimate of glyph run width for a text run."""
    if not s:
        return 0.0
    n_ascii = sum(1 for c in s if ord(c) < 128)
    n_cjk = len(s) - n_ascii
    return n_ascii * fs * 0.6 + n_cjk * fs * 1.05


def _emit_gridline_with_gaps(x0: float, x1: float, y: float, stroke: str,
                              stroke_width: float, dash: str,
                              text_bboxes: list, extra_attrs: str = "") -> str:
    """Emit a horizontal line as one or more <line> segments, skipping any
    x-ranges where y falls inside a text bbox's 15%-70% band (same band the
    validator uses to flag "line strikes through text").

    Used both for full-width gridlines and for shorter connector lines
    between waterfall bars. `extra_attrs` is appended verbatim to each
    <line> element (e.g. opacity for connectors).

    text_bboxes: list of (tx, ty, tw, th) tuples for value labels.
    """
    # Support callers that pass x0 > x1 (shouldn't normally happen for
    # horizontal lines, but be defensive).
    lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)
    # find bands covering y
    gaps = []
    for (tx, ty, tw, th) in text_bboxes:
        # validator band: [ty + th*0.15, ty + th*0.7]
        # widen slightly (0.05 top / 0.75 bottom) so borderline hits are also covered
        band_top = ty + th * 0.05
        band_bot = ty + th * 0.75
        if band_top <= y <= band_bot:
            # skip 3px pad on both sides
            gap_l = max(lo, tx - 3)
            gap_r = min(hi, tx + tw + 3)
            if gap_r > gap_l:
                gaps.append((gap_l, gap_r))
    if not gaps:
        return (
            f'<line x1="{lo:.1f}" y1="{y:.1f}" x2="{hi:.1f}" y2="{y:.1f}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" '
            f'stroke-dasharray="{dash}"{extra_attrs}/>'
        )
    # merge overlapping gaps
    gaps.sort()
    merged = [gaps[0]]
    for gl, gr in gaps[1:]:
        if gl <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], gr))
        else:
            merged.append((gl, gr))
    segs = []
    cur = lo
    for gl, gr in merged:
        if gl > cur:
            segs.append(
                f'<line x1="{cur:.1f}" y1="{y:.1f}" x2="{gl:.1f}" y2="{y:.1f}" '
                f'stroke="{stroke}" stroke-width="{stroke_width}" '
                f'stroke-dasharray="{dash}"{extra_attrs}/>'
            )
        cur = max(cur, gr)
    if cur < hi:
        segs.append(
            f'<line x1="{cur:.1f}" y1="{y:.1f}" x2="{hi:.1f}" y2="{y:.1f}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" '
            f'stroke-dasharray="{dash}"{extra_attrs}/>'
        )
    return "".join(segs)


def _draw_vertical_common(ctx: _Ctx, layout, show_subtotal_emphasis=False, zero_line=False):
    """通用 vertical waterfall renderer。default_flat / subtotal_bridge / cross_axis 共用。"""
    parts = []
    ML = 60
    MR = 40
    plot_left = ML + 30
    plot_right = ctx.W - MR
    n = len(layout)
    slot = (plot_right - plot_left) / n
    bar_w = min(60.0, slot * 0.62)

    # y-range: include all runnings, plus zero
    all_v = [0.0]
    for _, _, sv, ev, _, _ in layout:
        all_v.extend([sv, ev])
    v_min = min(all_v)
    v_max = max(all_v)
    if v_min == v_max:
        v_max = v_min + 1.0
    pad = (v_max - v_min) * 0.10
    v_lo, v_hi, ticks = _nice_ticks(v_min - pad * 0.4, v_max + pad, target=5)

    def yof(v):
        return ctx.plot_bot - (v - v_lo) / (v_hi - v_lo) * (ctx.plot_bot - ctx.plot_top)

    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    grid_col = _rgba_with_alpha(ink, 0.12)

    # -----------------------------------------------------------------
    # First pass: compute value-label bboxes so gridlines / connectors can
    # skip them. Geometry MUST match embed_svg_validator._collect_primitives
    # which reads text_y_attr from the <text> node and stores
    #   bbox.y = attr_y - fs * 0.8
    #   bbox.h = fs
    # The band the validator marks as "struck through" is
    #   [bbox.y + h*0.15, bbox.y + h*0.7]
    # Previously this pass used ty = baseline - fs which put our estimated
    # bbox ~0.2*fs too high, so gridlines sitting just above the text's
    # baseline slipped past our gap check while the validator still flagged
    # them (R11-brand '+40' case).
    # -----------------------------------------------------------------
    value_bboxes: list = []  # list of (tx, ty, tw, th)
    for i, (label, kind, sv, ev, disp, _segs) in enumerate(layout):
        x_c = plot_left + i * slot + slot / 2
        if kind == "total":
            txt = _fmt(ev)
            baseline_y = yof(ev) - 6
            fs = ctx.fs_value
        elif disp >= 0:
            txt = f"+{_fmt(abs(disp))}"
            baseline_y = yof(ev) - 6
            fs = ctx.fs_value
        else:
            txt = f"-{_fmt(abs(disp))}"
            baseline_y = yof(ev) + ctx.fs_value + 4
            fs = ctx.fs_value
        tw = _est_text_width(txt, fs)
        # Mirror validator: bbox.y = attr_y - fs*0.8 where attr_y is the <text>
        # element's y attribute (= baseline_y in our SVG output).
        ty = baseline_y - fs * 0.8
        tx = x_c - tw / 2
        value_bboxes.append((tx, ty, tw, fs))

    # y-axis + gridlines (segmented around value labels to avoid strike-through)
    for t in ticks:
        y = yof(t)
        parts.append(
            _emit_gridline_with_gaps(
                plot_left, plot_right, y, grid_col, 0.5, "2 3",
                value_bboxes,
            )
        )
        # y-axis tick label. The zero tick is rendered as "0" (not spelled out).
        parts.append(
            f'<text x="{plot_left - 8:.1f}" y="{y + 3:.1f}" text-anchor="end" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_tick}" fill="{mut}">{_fmt(t)}</text>'
        )

    # optional emphasized zero line
    if zero_line and v_lo <= 0.0 <= v_hi:
        y0 = yof(0.0)
        parts.append(
            f'<line x1="{plot_left:.1f}" y1="{y0:.1f}" x2="{plot_right:.1f}" y2="{y0:.1f}" '
            f'stroke="{ink}" stroke-width="1.3" opacity="0.85"/>'
        )

    prev_end_x = None
    prev_end_y = None
    for i, (label, kind, sv, ev, disp, _) in enumerate(layout):
        x_c = plot_left + i * slot + slot / 2
        x0 = x_c - bar_w / 2
        y_top = yof(max(sv, ev))
        y_bot = yof(min(sv, ev))
        h = max(1.0, y_bot - y_top)
        col = _colors(ctx.pal, kind)

        # subtotal emphasis: use a bolder/darker fill and slightly wider
        if show_subtotal_emphasis and kind == "total" and 0 < i < n - 1:
            # emphasize with an outline halo
            parts.append(
                f'<rect x="{x0 - 3:.1f}" y="{yof(ev) - 3:.1f}" width="{bar_w + 6:.1f}" '
                f'height="{yof(0.0) - yof(ev) + 6:.1f}" '
                f'fill="none" stroke="{ctx.pal["accent"]}" stroke-width="1.4" '
                f'stroke-dasharray="4 3"/>'
            )
            # bar from zero
            y_zero = yof(0.0)
            parts.append(
                f'<rect x="{x0:.1f}" y="{min(yof(ev), y_zero):.1f}" width="{bar_w:.1f}" '
                f'height="{abs(yof(ev) - y_zero):.1f}" fill="{col}"/>'
            )
        elif kind == "total":
            y_zero = yof(0.0)
            y_e = yof(ev)
            parts.append(
                f'<rect x="{x0:.1f}" y="{min(y_e, y_zero):.1f}" width="{bar_w:.1f}" '
                f'height="{abs(y_e - y_zero):.1f}" fill="{col}"/>'
            )
        else:
            if kind == "neg":
                # Neg bars: keep accent fill but add a darker outline + a light
                # diagonal-hatch pattern so pos vs neg is unambiguous even when
                # the palette's series[1] happens to equal accent. Pattern is
                # drawn as inline <line> segments (no <pattern> defs needed).
                parts.append(
                    f'<rect x="{x0:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" '
                    f'height="{h:.1f}" fill="{col}" stroke="{ink}" stroke-width="1.1"/>'
                )
                # 45° hatch inside bar (skip if bar is tiny)
                if h > 6 and bar_w > 6:
                    inset = 2.0
                    hx0, hx1 = x0 + inset, x0 + bar_w - inset
                    hy0, hy1 = y_top + inset, y_bot - inset
                    hbw = hx1 - hx0
                    hbh = hy1 - hy0
                    spacing = 6.0
                    k = 0.0
                    k_end = hbw + hbh
                    while k <= k_end:
                        dxa = max(0.0, k - hbh)
                        dxb = min(hbw, k)
                        if dxb > dxa:
                            xa = hx0 + dxa
                            xb = hx0 + dxb
                            ya = hy0 + (k - dxa)
                            yb = hy0 + (k - dxb)
                            parts.append(
                                f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" '
                                f'stroke="{ctx.pal["bg"]}" stroke-width="0.7" opacity="0.55"/>'
                            )
                        k += spacing
            else:
                parts.append(
                    f'<rect x="{x0:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" '
                    f'height="{h:.1f}" fill="{col}"/>'
                )

        # value label above/below bar
        sign = "+" if disp > 0 else ("-" if disp < 0 else "")
        if kind == "total":
            label_y = yof(ev) - 6
            parts.append(
                f'<text x="{x_c:.1f}" y="{label_y:.1f}" text-anchor="middle" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" '
                f'font-weight="800" fill="{ink}">{_fmt(ev)}</text>'
            )
        else:
            if disp >= 0:
                label_y = yof(ev) - 6
                parts.append(
                    f'<text x="{x_c:.1f}" y="{label_y:.1f}" text-anchor="middle" '
                    f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" '
                    f'font-weight="700" fill="{ink}">+{_fmt(abs(disp))}</text>'
                )
            else:
                label_y = yof(ev) + ctx.fs_value + 4
                parts.append(
                    f'<text x="{x_c:.1f}" y="{label_y:.1f}" text-anchor="middle" '
                    f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" '
                    f'font-weight="700" fill="{ctx.pal["accent"]}">-{_fmt(abs(disp))}</text>'
                )

        # connector from previous end to this start.  Segmented around any
        # value-label bbox it would otherwise strike (mirrors gridline pass).
        if i > 0 and prev_end_x is not None:
            y_conn = yof(sv)
            parts.append(
                _emit_gridline_with_gaps(
                    prev_end_x, x0, y_conn,
                    _rgba_with_alpha(ink, 0.45), 1, "3 3",
                    value_bboxes,
                )
            )
        prev_end_x = x0 + bar_w
        prev_end_y = yof(ev)

        # x-axis category label
        parts.append(
            f'<text x="{x_c:.1f}" y="{ctx.plot_bot + 18:.1f}" text-anchor="middle" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
            f'font-weight="600" fill="{mut}">{xesc(label)}</text>'
        )

    return "".join(parts)


def _draw_default_flat(ctx: _Ctx) -> str:
    layout = _compute_layout(ctx.steps)
    return _draw_vertical_common(ctx, layout, show_subtotal_emphasis=False, zero_line=False)


def _draw_subtotal_bridge(ctx: _Ctx) -> str:
    # subtotal_bridge: 检测中间 kind='total' 的步骤作为小计标注
    # 如果 data 里没有中间 subtotal，自动在每个 pos->neg / neg->pos 转折点
    # 插入一个隐式的小计（要求距上一个 subtotal >=3 步），从而让长序列被切成
    # 多个 running section，避免大数据集只在开头出现一次 subtotal 的问题。
    layout = _compute_layout(ctx.steps)
    n = len(layout)
    has_intermediate_total = any(
        i not in (0, n - 1) and layout[i][1] == "total" for i in range(n)
    )
    if not has_intermediate_total and n >= 5:
        # Scan for every pos<->neg turning point; insert Subtotal after each
        # turning point subject to a min-spacing of 3 steps from the previous
        # subtotal (or from index 0) so we don't clutter short sections.
        turning_points = []
        for i in range(1, n - 1):
            kind_i = layout[i][1]
            kind_next = layout[i + 1][1]
            if (kind_i == "pos" and kind_next == "neg") or (
                kind_i == "neg" and kind_next == "pos"
            ):
                turning_points.append(i + 1)  # insert BEFORE step i+1

        # Filter to keep min-spacing >=3 (in original layout indices)
        MIN_GAP = 3
        selected = []
        last = 0
        for tp in turning_points:
            if tp - last >= MIN_GAP and (n - 1) - tp >= MIN_GAP:
                selected.append(tp)
                last = tp

        if selected:
            # Build new_steps by walking original steps and inserting Subtotal
            # entries at each selected index. Because insertions shift indices,
            # process selected in ascending order and use an offset.
            new_steps = list(ctx.steps)
            offset = 0
            for insert_idx in selected:
                # Running value = ev of the step immediately before this insert
                # in the CURRENT (already-partly-mutated) layout. To keep this
                # simple, recompute layout each iteration.
                cur_layout = _compute_layout(new_steps)
                actual_idx = insert_idx + offset
                if 0 < actual_idx < len(cur_layout):
                    running_at = cur_layout[actual_idx - 1][3]
                    new_steps.insert(actual_idx, ("Subtotal", running_at, "total"))
                    offset += 1
            layout = _compute_layout(new_steps)
    return _draw_vertical_common(ctx, layout, show_subtotal_emphasis=True, zero_line=False)


def _draw_cross_axis(ctx: _Ctx) -> str:
    layout = _compute_layout(ctx.steps)
    return _draw_vertical_common(ctx, layout, show_subtotal_emphasis=False, zero_line=True)


# ---------------------------------------------------------------------------
# 4) horizontal
# ---------------------------------------------------------------------------

def _draw_horizontal(ctx: _Ctx) -> str:
    parts = []
    layout = _compute_layout(ctx.steps)
    n = len(layout)

    # figure out y-range on x-axis
    all_v = [0.0]
    for _, _, sv, ev, _, _ in layout:
        all_v.extend([sv, ev])
    v_min = min(all_v)
    v_max = max(all_v)
    if v_min == v_max:
        v_max = v_min + 1.0
    pad = (v_max - v_min) * 0.08
    v_lo, v_hi, ticks = _nice_ticks(v_min - pad * 0.4, v_max + pad, target=5)

    ML = 140    # left margin for category labels
    MR = 60
    plot_left = ML
    plot_right = ctx.W - MR

    # row layout
    row_h_target = ctx.plot_h / n
    row_h = max(24.0, min(56.0, row_h_target))
    bar_h = min(row_h * 0.55, 26.0)
    total_h = row_h * n
    top = ctx.plot_top + max(0, (ctx.plot_h - total_h) / 2)

    def xof(v):
        return plot_left + (v - v_lo) / (v_hi - v_lo) * (plot_right - plot_left)

    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    acc = ctx.pal["accent"]
    grid = _rgba_with_alpha(ink, 0.12)

    # vertical gridlines / x ticks
    for t in ticks:
        x = xof(t)
        parts.append(
            f'<line x1="{x:.1f}" y1="{top:.1f}" x2="{x:.1f}" y2="{top + total_h:.1f}" '
            f'stroke="{grid}" stroke-width="0.5" stroke-dasharray="2 3"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{top + total_h + 16:.1f}" text-anchor="middle" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_tick}" fill="{mut}">{_fmt(t)}</text>'
        )

    # zero line if in range
    if v_lo <= 0.0 <= v_hi:
        x0 = xof(0.0)
        parts.append(
            f'<line x1="{x0:.1f}" y1="{top:.1f}" x2="{x0:.1f}" y2="{top + total_h:.1f}" '
            f'stroke="{ink}" stroke-width="1.0" opacity="0.5"/>'
        )

    for i, (label, kind, sv, ev, disp, _) in enumerate(layout):
        cy = top + i * row_h + row_h / 2
        y_top = cy - bar_h / 2
        col = _colors(ctx.pal, kind)

        # category label
        parts.append(
            f'<text x="{plot_left - 10:.1f}" y="{cy + 4:.1f}" text-anchor="end" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
            f'font-weight="600" fill="{ink}">{xesc(label)}</text>'
        )

        if kind == "total":
            x_a = xof(0.0)
            x_b = xof(ev)
            x0, w = (x_a, x_b - x_a) if x_b >= x_a else (x_b, x_a - x_b)
            parts.append(
                f'<rect x="{x0:.1f}" y="{y_top:.1f}" width="{w:.1f}" height="{bar_h:.1f}" '
                f'fill="{col}"/>'
            )
            lx = x_b + 6 if x_b >= x_a else x_b - 6
            anchor = "start" if x_b >= x_a else "end"
            parts.append(
                f'<text x="{lx:.1f}" y="{cy + 4:.1f}" text-anchor="{anchor}" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" font-weight="800" '
                f'fill="{ink}">{_fmt(ev)}</text>'
            )
        elif kind == "pos":
            x_a = xof(sv)
            x_b = xof(ev)
            parts.append(
                f'<rect x="{x_a:.1f}" y="{y_top:.1f}" width="{x_b - x_a:.1f}" '
                f'height="{bar_h:.1f}" fill="{col}"/>'
            )
            parts.append(
                f'<text x="{x_b + 6:.1f}" y="{cy + 4:.1f}" font-family="{BODY_FONT}" '
                f'font-size="{ctx.fs_value}" font-weight="700" fill="{ink}">+{_fmt(abs(disp))}</text>'
            )
        else:  # neg
            x_a = xof(min(sv, ev))
            x_b = xof(max(sv, ev))
            parts.append(
                f'<rect x="{x_a:.1f}" y="{y_top:.1f}" width="{x_b - x_a:.1f}" '
                f'height="{bar_h:.1f}" fill="none" stroke="{acc}" stroke-width="1.4"/>'
            )
            parts.append(
                f'<text x="{x_a - 6:.1f}" y="{cy + 4:.1f}" text-anchor="end" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" font-weight="700" '
                f'fill="{acc}">-{_fmt(abs(disp))}</text>'
            )

        # connector: vertical from this bar bottom-end to next bar top-start
        if i < n - 1:
            x_end = xof(ev)
            next_cy = top + (i + 1) * row_h + row_h / 2
            next_y_top = next_cy - bar_h / 2
            parts.append(
                f'<line x1="{x_end:.1f}" y1="{y_top + bar_h:.1f}" x2="{x_end:.1f}" '
                f'y2="{next_y_top:.1f}" stroke="{_rgba_with_alpha(ink, 0.4)}" '
                f'stroke-width="1" stroke-dasharray="3 3"/>'
            )
    return "".join(parts)


# ---------------------------------------------------------------------------
# 5) stacked_gradient — 每个 step 按子类别堆叠 + 渐变
# ---------------------------------------------------------------------------

def _draw_stacked_gradient(ctx: _Ctx) -> str:
    parts = []
    layout = _compute_layout(ctx.steps)  # each has segments
    n = len(layout)

    all_v = [0.0]
    for _, _, sv, ev, _, _ in layout:
        all_v.extend([sv, ev])
    v_min = min(all_v)
    v_max = max(all_v)
    if v_min == v_max:
        v_max = v_min + 1.0
    pad = (v_max - v_min) * 0.12
    v_lo, v_hi, ticks = _nice_ticks(v_min - pad * 0.4, v_max + pad, target=5)

    ML = 60
    MR = 40
    plot_left = ML + 30
    plot_right = ctx.W - MR
    slot = (plot_right - plot_left) / n
    bar_w = min(64.0, slot * 0.62)

    def yof(v):
        return ctx.plot_bot - (v - v_lo) / (v_hi - v_lo) * (ctx.plot_bot - ctx.plot_top)

    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    grid = _rgba_with_alpha(ink, 0.12)
    series = ctx.pal.get("series") or [ctx.pal["accent"], ctx.pal["secondary"], ctx.pal["ink"]]

    grad_ct = 0

    # collect unique sub_labels for legend AND build a stable global sub_label→color map.
    # Previously each step allocated colors by per-step k-index, which meant "Fed" in Tax
    # step got Salary's color (both at k=0). Now every distinct sub_label gets a stable
    # color, and the legend matches the bars exactly.
    seen_subs = []
    for _, _, _, _, _, segs in layout:
        for lb, _ in segs:
            if lb and lb not in seen_subs:
                seen_subs.append(lb)

    # Expand palette when we have more sub_labels than series colors, so distinct labels
    # get distinct colors (via alpha cycling) instead of exact color collisions.
    def _extended_palette(n_needed):
        pal_list = list(series)
        alphas = [1.0, 0.55]
        out = []
        for a in alphas:
            for c in pal_list:
                out.append(_rgba_with_alpha(c, a) if a < 1.0 else c)
                if len(out) >= n_needed:
                    return out
        return out or pal_list

    ext = _extended_palette(max(len(seen_subs), len(series)))
    sub_color = {lb: ext[i % len(ext)] for i, lb in enumerate(seen_subs)}

    # Fallback per-bar palette used when NO segments carry a sub_label (i.e. the
    # input is a simple [(name, value, kind)] list — the harness's typical case).
    # In that case we cycle through the extended series so each bar gets a
    # visibly distinct hue instead of collapsing to a single color.
    _has_any_sub_label = bool(seen_subs)
    _bar_palette = _extended_palette(max(len(layout), len(series)))

    # ---- Pre-compute value-label bboxes so gridlines / connectors can skip
    # ---- them. Same geometry-match rationale as _draw_vertical_common:
    # ---- validator stores bbox.y = attr_y - fs*0.8, not attr_y - fs.
    value_bboxes: list = []
    for i, (label, kind, sv, ev, disp, segments) in enumerate(layout):
        x_c = plot_left + i * slot + slot / 2
        if kind == "total":
            txt = _fmt(ev)
            baseline_y = yof(max(ev, 0)) - 6
        else:
            step_total = sum(v for _, v in segments) or 0.0
            if kind == "pos":
                txt = f"+{_fmt(step_total)}"
                baseline_y = yof(ev) - 6
            else:
                txt = f"-{_fmt(step_total)}"
                baseline_y = yof(ev) + ctx.fs_value + 4
        fs = ctx.fs_value
        tw = _est_text_width(txt, fs)
        ty = baseline_y - fs * 0.8
        tx = x_c - tw / 2
        value_bboxes.append((tx, ty, tw, fs))

    # y-axis (segmented gridlines around value labels)
    for t in ticks:
        y = yof(t)
        parts.append(
            _emit_gridline_with_gaps(
                plot_left, plot_right, y, grid, 0.5, "2 3",
                value_bboxes,
            )
        )
        parts.append(
            f'<text x="{plot_left - 8:.1f}" y="{y + 3:.1f}" text-anchor="end" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_tick}" fill="{mut}">{_fmt(t)}</text>'
        )

    prev_end_x = None
    for i, (label, kind, sv, ev, disp, segments) in enumerate(layout):
        x_c = plot_left + i * slot + slot / 2
        x0 = x_c - bar_w / 2

        if kind == "total":
            v = ev
            y_top = yof(max(v, 0))
            y_bot = yof(0.0) if v >= 0 else yof(v)
            gid = f"wfsg_{grad_ct}"
            grad_ct += 1
            # Base color: use ink for totals if any sub_labels exist (they are the
            # visual anchor of a categorical stacked layout). If no sub_labels
            # exist (simple scalar input), cycle through _bar_palette so each
            # total bar can still be distinguished from pos/neg bars around it.
            _total_base = ink if _has_any_sub_label else _bar_palette[i % len(_bar_palette)]
            r, g, b = rgb_tuple(_total_base)
            ctx.add_def(
                f'<linearGradient id="{gid}" x1="0" y1="{y_top:.1f}" x2="0" y2="{y_bot:.1f}" '
                f'gradientUnits="userSpaceOnUse">'
                f'<stop offset="0%" stop-color="rgba({r},{g},{b},1)"/>'
                f'<stop offset="100%" stop-color="rgba({r},{g},{b},0.55)"/>'
                f'</linearGradient>'
            )
            parts.append(
                f'<rect x="{x0:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" '
                f'height="{max(1.0, y_bot - y_top):.1f}" fill="url(#{gid})"/>'
            )
            parts.append(
                f'<text x="{x_c:.1f}" y="{y_top - 6:.1f}" text-anchor="middle" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" font-weight="800" '
                f'fill="{ink}">{_fmt(v)}</text>'
            )
        else:
            # stacked segments between sv and ev
            step_total = sum(v for _, v in segments) or 1e-9
            sign = 1 if kind == "pos" else -1
            base_v = sv
            cur = base_v
            for k, (sub_lb, sub_val) in enumerate(segments):
                # Color lookup:
                #   - sub_label present → stable global sub_label → color map
                #   - sub_label absent AND no other bar has one either → cycle by
                #     BAR INDEX (i) so each bar gets a distinct color, not by
                #     segment index k (which collapsed every bar to series[0]).
                if sub_lb:
                    sub_col = sub_color.get(sub_lb, series[k % len(series)])
                elif _has_any_sub_label:
                    # mixed: this bar has no sub_label but others do → fall back
                    # to k-cycled series color (legacy behavior)
                    sub_col = series[k % len(series)]
                else:
                    # simple scalar input path: hue-shift per bar
                    sub_col = _bar_palette[i % len(_bar_palette)]
                if sign > 0:
                    seg_bot_v = cur
                    seg_top_v = cur + sub_val
                    cur = seg_top_v
                else:
                    seg_top_v = cur
                    seg_bot_v = cur - sub_val
                    cur = seg_bot_v
                y_seg_top = yof(seg_top_v)
                y_seg_bot = yof(seg_bot_v)
                seg_h = y_seg_bot - y_seg_top
                if seg_h < 0.5:
                    continue
                gid = f"wfsg_{grad_ct}"
                grad_ct += 1
                r, g, b = rgb_tuple(sub_col)
                ctx.add_def(
                    f'<linearGradient id="{gid}" x1="0" y1="{y_seg_top:.1f}" '
                    f'x2="0" y2="{y_seg_bot:.1f}" gradientUnits="userSpaceOnUse">'
                    f'<stop offset="0%" stop-color="rgba({r},{g},{b},1)"/>'
                    f'<stop offset="100%" stop-color="rgba({r},{g},{b},0.55)"/>'
                    f'</linearGradient>'
                )
                parts.append(
                    f'<rect x="{x0:.1f}" y="{y_seg_top:.1f}" width="{bar_w:.1f}" '
                    f'height="{seg_h:.1f}" fill="url(#{gid})"/>'
                )
                # small in-seg label if room
                if seg_h > ctx.fs_tick * 2 and sub_lb:
                    parts.append(
                        f'<text x="{x_c:.1f}" y="{y_seg_top + seg_h/2 + 3:.1f}" '
                        f'text-anchor="middle" font-family="{BODY_FONT}" '
                        f'font-size="{ctx.fs_tick}" font-weight="600" '
                        f'fill="rgba(255,255,255,0.95)">{xesc(sub_lb)} {_fmt(sub_val)}</text>'
                    )
            # total delta label
            if sign > 0:
                parts.append(
                    f'<text x="{x_c:.1f}" y="{yof(ev) - 6:.1f}" text-anchor="middle" '
                    f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" '
                    f'font-weight="800" fill="{ink}">+{_fmt(step_total)}</text>'
                )
            else:
                parts.append(
                    f'<text x="{x_c:.1f}" y="{yof(ev) + ctx.fs_value + 4:.1f}" '
                    f'text-anchor="middle" font-family="{BODY_FONT}" '
                    f'font-size="{ctx.fs_value}" font-weight="800" '
                    f'fill="{ctx.pal["accent"]}">-{_fmt(step_total)}</text>'
                )

        # connector to next (segmented around value labels; see
        # _draw_vertical_common for rationale)
        if i < n - 1:
            y_conn = yof(ev)
            nx = plot_left + (i + 1) * slot + slot / 2 - bar_w / 2
            parts.append(
                _emit_gridline_with_gaps(
                    x0 + bar_w, nx, y_conn,
                    _rgba_with_alpha(ink, 0.45), 1, "3 3",
                    value_bboxes,
                )
            )

        # category label
        parts.append(
            f'<text x="{x_c:.1f}" y="{ctx.plot_bot + 18:.1f}" text-anchor="middle" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
            f'font-weight="600" fill="{mut}">{xesc(label)}</text>'
        )

    # legend for sub categories — uses the SAME global sub_color map as the bars,
    # so legend colors are guaranteed to match segment colors.
    if seen_subs:
        lg_y = ctx.plot_bot + 38
        lg_x = plot_left
        for lb in seen_subs:
            col = sub_color[lb]
            parts.append(
                f'<rect x="{lg_x:.1f}" y="{lg_y - 9:.1f}" width="12" height="10" fill="{col}"/>'
            )
            parts.append(
                f'<text x="{lg_x + 16:.1f}" y="{lg_y:.1f}" font-family="{BODY_FONT}" '
                f'font-size="{ctx.fs_tick}" font-weight="600" fill="{ink}">{xesc(lb)}</text>'
            )
            lg_x += max(80, len(lb) * ctx.fs_tick * 0.7 + 30)

    return "".join(parts)


def make_waterfall(steps,
                   width: float = 1000.0,
                   height: float = 560.0,
                   value_fmt: str = "auto",
                   title: str = None,
                   subtitle: str = None,
                   figure_label: str = None,
                   font_family: str = None,
                   palette: dict = None,
                variant: str = None) -> str:
    """
    从起点到终点的逐项加减（Lupi 编辑体扁平风）：
    - total 柱（首尾）：纯黑实心，无描边无圆角
    - pos 柱：中灰（_INK6）实心，无描边无圆角
    - neg 柱：白底 + accent 描边 + accent 45° 斜纹填充，无圆角
    - 数据标签加粗贴柱顶（total/pos 用 _INK，neg 用 _ACC）
    - 连接虚线淡灰（_INK2）

    steps: [(name, value, kind), ...]
      - kind='total'：value 是绝对值（例如起点/终点）
      - kind='pos':  value 是增量（>=0），柱从当前 running 向上
      - kind='neg':  value 是增量（<0 或 >0 都可，函数按负数处理），柱从当前 running 向下

    value_fmt: 数值标签格式
      - "auto"（默认）：数据全整数不加小数；否则按 span 自动选精度
      - "int" / Python format string
    palette: 可选配色覆盖字典（None 时用编辑体默认）。支持字段：
      - "ink"     : 主墨色（total 柱、pos 数值、类别名、坐标网格；默认 rgba(28,28,26,1)）
      - "accent"  : 强调色（neg 柱描边/斜纹/数值；默认赤褐 rgba(163,88,50,1)）
      - "pos_bar" : pos 增量柱填色（默认 ink 60% 半透明的中灰）
      - "connect" : 连接虚线色（默认 ink 40% 半透明）
      - "grid"    : Y 轴网格线色（默认 ink 12% 半透明）
      - "muted"   : 类别标签色（默认 ink 60% 半透明）
      示例：palette={"accent":"rgba(56,102,168,1)","ink":"rgba(20,30,50,1)"}
    Y 轴刻度按量级整数化对齐（不出 88.8 / 101.6 这类半整数）。
    """
    if not _variant_is_classic('waterfall', variant):
        _data = {"steps": list(steps)}
        return _dispatch_to_svg_lib(
            'waterfall', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    if not steps or len(steps) < 2:
        raise ValueError("waterfall: need at least 2 steps (start + end)")
    # ---- 配色解析 ----
    def _rgba_with_alpha(rgba_str, alpha):
        import re as _re
        m = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', rgba_str)
        if not m:
            return f"rgba(28,28,26,{alpha})"
        return f"rgba({int(float(m.group(1)))},{int(float(m.group(2)))},{int(float(m.group(3)))},{alpha})"
    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    c_ink      = _pal.get("ink",      _INK)
    c_accent   = _pal.get("accent",   _ACC)
    c_pos_bar  = _pal.get("pos_bar",  _rgba_with_alpha(c_ink, 0.6))
    c_connect  = _pal.get("connect",  _rgba_with_alpha(c_ink, 0.4))
    c_grid     = _pal.get("grid",     _rgba_with_alpha(c_ink, 0.12))
    c_muted    = _pal.get("muted",    _rgba_with_alpha(c_ink, 0.6))
    c_stroke_z = _rgba_with_alpha(c_ink, 0.4)  # 零增量柱的空心描边
    running = 0.0
    all_v = []
    total_vals = []
    step_yvals = []
    for i, s in enumerate(steps):
        name, v, kind = s
        if kind == 'total':
            top = v
            running = v
            total_vals.append(v)
            step_yvals.append((top, None))
            all_v.append(v)
        elif kind == 'pos':
            bot = running
            top = running + abs(v)
            running += abs(v)
            step_yvals.append((top, bot))
            all_v.extend([top, bot])
        else:  # neg
            top = running
            bot = running - abs(v)
            running -= abs(v)
            step_yvals.append((top, bot))
            all_v.extend([top, bot])
    y_min_data = min(all_v + total_vals)
    y_max_data = max(all_v + total_vals)
    data_span = y_max_data - y_min_data or max(abs(y_max_data), 1) * 0.1
    y_min_raw = y_min_data - data_span * 0.15
    y_max_raw = y_max_data + data_span * 0.18
    raw_span = y_max_raw - y_min_raw
    # "nice number" 刻度算法：magnitude 支持小数（floor 而非 int），系数从 {1, 2, 2.5, 5, 10} 中挑最接近的
    step = max(1e-12, raw_span / 5)
    magnitude = 10 ** math.floor(math.log10(step))
    frac = step / magnitude
    for nice in (1, 2, 2.5, 5, 10):
        if frac <= nice:
            tick_step = nice * magnitude
            break
    else:
        tick_step = 10 * magnitude
    y_min = math.floor(y_min_raw / tick_step) * tick_step
    y_max = math.ceil(y_max_raw / tick_step) * tick_step
    span = y_max - y_min or 1
    for i, (top, bot) in enumerate(step_yvals):
        if bot is None:
            step_yvals[i] = (top, y_min)

    # 根据 tick_step 自动决定精度（数值标签 & Y 轴刻度共用一套精度，避免"0.850 vs 0.0"这种不一致）
    if tick_step >= 1:
        _tick_decimals = 0
    else:
        _tick_decimals = max(0, -math.floor(math.log10(tick_step)))

    def _fmt(v):
        if value_fmt == "auto":
            av = abs(v)
            all_int = all(abs(round(s[1]) - s[1]) < 1e-9 for s in steps)
            if all_int:
                return f"{int(round(v)):,}"
            # 数值标签精度沿用 tick 精度，避免上下不一致
            if _tick_decimals == 0:
                return f"{int(round(v)):,}"
            else:
                return f"{v:,.{_tick_decimals}f}"
        elif value_fmt == "int":
            return f"{int(round(v)):,}"
        else:
            return format(v, value_fmt)
    def _fmt_tick(v):
        if _tick_decimals == 0:
            return f"{int(round(v)):,}"
        return f"{v:,.{_tick_decimals}f}"

    axis_x0 = 90
    axis_x1 = width - 40
    top_y = 70
    bot_y = height - 60
    def yof(v):
        return bot_y - (v - y_min) / (y_max - y_min) * (bot_y - top_y)
    n = len(steps)
    slot = (axis_x1 - axis_x0 - 20) / n
    bar_w = min(110, slot * 0.6)

    parts = []
    # ---- 预先计算所有 value label bbox，让 Y 网格 & 连接虚线都能在标签处开洞
    # ---- （与 draw_waterfall variant path 用同一 helper 的做法一致）。
    # 几何 MUST match embed_svg_validator._collect_primitives：
    #   bbox.y = attr_y - fs * 0.8   (attr_y = <text> element's y attribute)
    #   bbox.h = fs
    # validator 判"line strikes through text"的横带是 [bbox.y+h*0.15, bbox.y+h*0.7]。
    # R12 fixer-2 只修了 draw_waterfall 的 variant path；R13 learn/brand 组
    # 又在 classic path 遇到同样问题，这里补上。
    value_bboxes: list = []  # list of (tx, ty, tw, th)
    for _i, (_name, _v, _kind) in enumerate(steps):
        _x = axis_x0 + 8 + _i * slot + (slot - bar_w) / 2
        _top_v, _bot_v = step_yvals[_i]
        _y_top = yof(_top_v)
        _y_bot = yof(_bot_v)
        _h_bar = _y_bot - _y_top
        _zero = (_kind in ('pos', 'neg')) and _h_bar < 1.0
        if _zero:
            _y_top = min(_y_top, _y_bot) - 0.75
            _y_bot = _y_top + 1.5
        if _kind == 'total':
            _txt = _fmt(_v)
            _fs = 16.0
            _baseline_y = _y_top - 5
        elif _kind == 'pos':
            _txt = f"+{_fmt(abs(_v))}"
            _fs = 14.0
            _baseline_y = _y_top - 4
        else:  # neg
            _txt = f"-{_fmt(abs(_v))}"
            _fs = 12.0
            _baseline_y = _y_bot + 11
        _tw = 0.0
        for _ch in _txt:
            _tw += _fs * (0.6 if ord(_ch) < 128 else 1.05)
        _cx = _x + bar_w / 2
        value_bboxes.append((_cx - _tw / 2, _baseline_y - _fs * 0.8, _tw, _fs))

    # Y 网格 + 刻度 (gridlines 走 _emit_gridline_with_gaps 跳过 value label bbox)
    tick = y_min
    while tick <= y_max + 1e-9:
        y = yof(tick)
        parts.append(
            _emit_gridline_with_gaps(
                axis_x0, axis_x1, y, c_grid, 0.5, "2 3",
                value_bboxes,
            )
        )
        parts.append(
            f'<text font-family="{_body_font}" x="{axis_x0-4}" y="{y+3:.1f}" font-size="12" fill="{c_muted}" text-anchor="end">{_fmt_tick(tick)}</text>'
        )
        tick += tick_step

    running = 0.0
    # 类别标签旋转策略：只要有任何一个标签宽度超过 slot*0.9，就统一全部旋转（避免同图内一半旋转一半不旋转）
    def _label_text_w(nm):
        n_ascii = sum(1 for c in nm if ord(c) < 128)
        n_cjk = len(nm) - n_ascii
        return n_ascii * 8 * 0.6 + n_cjk * 8 * 1.1
    _rotate_labels = any(_label_text_w(s[0]) > slot * 0.9 for s in steps)

    for i, (name, v, kind) in enumerate(steps):
        x = axis_x0 + 8 + i * slot + (slot - bar_w) / 2
        top_v, bot_v = step_yvals[i]
        y_top = yof(top_v)
        y_bot = yof(bot_v)
        h_bar = y_bot - y_top
        # 零增量柱占位：pos/neg 的 v==0（h_bar≈0）时画一根 1.5px 高的空心细框，避免"柱消失"
        _zero_bar = (kind in ('pos', 'neg')) and h_bar < 1.0
        if _zero_bar:
            y_top = min(y_top, y_bot) - 0.75
            y_bot = y_top + 1.5
            h_bar = 1.5
        if kind == 'total':
            # 主墨实心，无描边无圆角
            parts.append(
                f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" height="{h_bar:.1f}" fill="{c_ink}"/>'
            )
            parts.append(
                f'<text font-family="{_body_font}" x="{x+bar_w/2:.1f}" y="{y_top-5:.1f}" font-size="16" font-weight="800" '
                f'fill="{c_ink}" text-anchor="middle">{_fmt(v)}</text>'
            )
            running = v
        elif kind == 'pos':
            # 中灰实心；零增量退化成空心细框
            if _zero_bar:
                parts.append(
                    f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" height="{h_bar:.1f}" '
                    f'fill="none" stroke="{c_stroke_z}" stroke-width="0.8"/>'
                )
            else:
                parts.append(
                    f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" height="{h_bar:.1f}" fill="{c_pos_bar}"/>'
                )
            parts.append(
                f'<text font-family="{_body_font}" x="{x+bar_w/2:.1f}" y="{y_top-4:.1f}" font-size="14" font-weight="700" '
                f'fill="{c_ink}" text-anchor="middle">+{_fmt(abs(v))}</text>'
            )
            running += abs(v)
        else:  # neg
            # 白底 + accent 描边
            parts.append(
                f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" height="{h_bar:.1f}" '
                f'fill="none" stroke="{c_accent}" stroke-width="1.2"/>'
            )
            # 45° 斜纹（沿对角线等距铺满内区）
            inset = 2.0
            hx0, hx1 = x + inset, x + bar_w - inset
            hy0, hy1 = y_top + inset, y_bot - inset
            hbw = hx1 - hx0
            hbh = hy1 - hy0
            if hbw > 0 and hbh > 0:
                spacing = 4.0
                k = 0.0
                k_end = hbw + hbh
                while k <= k_end:
                    dxa = max(0.0, k - hbh)
                    dxb = min(hbw, k)
                    if dxb > dxa:
                        xa = hx0 + dxa
                        xb = hx0 + dxb
                        ya = hy0 + (k - dxa)
                        yb = hy0 + (k - dxb)
                        parts.append(
                            f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" '
                            f'stroke="{c_accent}" stroke-width="0.5" opacity="0.4"/>'
                        )
                    k += spacing
            parts.append(
                f'<text font-family="{_body_font}" x="{x+bar_w/2:.1f}" y="{y_bot+11:.1f}" font-size="12" font-weight="700" '
                f'fill="{c_accent}" text-anchor="middle">-{_fmt(abs(v))}</text>'
            )
            running -= abs(v)
        # 连接虚线到下一根 — 通过 value label bbox 时开洞（与 draw_waterfall variant path 一致，
        # 复用 _emit_gridline_with_gaps helper）
        if i < n - 1:
            connect_y = yof(running)
            nx = axis_x0 + 8 + (i + 1) * slot + (slot - bar_w) / 2
            parts.append(
                _emit_gridline_with_gaps(
                    x + bar_w, nx, connect_y,
                    c_connect, 1, "3 3",
                    value_bboxes,
                )
            )
        # 底部类别名：全局统一是否旋转（避免同图内首末旋转、中间不旋转）
        cx_lab = x + bar_w / 2
        y_lab = bot_y + 16
        name_esc = _xesc(name)
        if _rotate_labels:
            parts.append(
                f'<text font-family="{_body_font}" x="{cx_lab:.1f}" y="{y_lab:.1f}" font-size="13" font-weight="700" '
                f'fill="{c_muted}" text-anchor="end" letter-spacing=".04em" '
                f'transform="rotate(-30 {cx_lab:.1f} {y_lab:.1f})">{name_esc}</text>'
            )
        else:
            parts.append(
                f'<text font-family="{_body_font}" x="{cx_lab:.1f}" y="{y_lab:.1f}" font-size="13" font-weight="700" '
                f'fill="{c_muted}" text-anchor="middle" letter-spacing=".04em">{name_esc}</text>'
            )
    # 顶部标题栏（可选）
    # Round 10 微调：深底 palette 的 ink 常常是"暖米色/象牙"（e.g. rgba(240,235,222)），
    # 做正文/数值标签没问题，但用作 chart 大标题（Georgia serif · 20pt · 700）时
    # 对比不够 punchy——观感偏暗淡。这里用 _punchy_title_ink 让深底 palette 的
    # title 拉到 crisp near-white；浅底 palette 保持不变（硬规则要求）。
    _title_ink = _punchy_title_ink(_pal)
    _title_block, _ = _render_title_block(
        x_left=axis_x0, anchor_y=top_y - 6,
        width=axis_x1 - axis_x0,
        title=title, subtitle=subtitle, figure_label=figure_label,
        # 用 palette 解析出来的 c_ink（深底 palette 时是浅色 ink），而不是模块级 _INK。
        # 后者恒为深色 rgba(28,28,26,1)——在深底上直接消失。
        # title 参数走 punchy 色；subtitle / figure_label 由 muted 承载不受影响。
        ink=_title_ink, muted=c_muted,
        body_font=_body_font, heading_font=_head_font,
    )
    _svg_result = _wrap_with_auto_viewbox(_title_block + "".join(parts), extra_pad=12.0)
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 11) Gantt 甘特图
# ==============================================================
