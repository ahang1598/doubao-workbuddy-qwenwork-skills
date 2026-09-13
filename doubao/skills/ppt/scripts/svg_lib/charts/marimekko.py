"""svg_lib/charts/marimekko.py

Marimekko 马赛克图 · 5 variant 统一 API：
- default_flat: BCG 经典风，我方 (we_key) 用 accent，其它用灰阶
- mekko_gradient: 每 sub 用 vertical linearGradient（顶亮底暗）
- mekko_outlined: 淡填 + 深描边
- shaded_residual: 各 sub 相对市场加权平均的偏差着色（正/负两向）
- treemap_flat: 每 market 内 sub 按份额垂直堆叠（不区分 we_key，用 series 轮转）

data schema：
  {
    "markets": [(name, market_share, [(sub, sub_share), ...]), ...],
    "we_key": str?  # 可选，标记哪个 sub_name 视为"我方"，仅 default_flat 使用
  }
  - market_share: 市场规模份额（推荐 sum=100 表示百分比，函数按输入总和归一）
  - sub_share: 该 market 内各 sub 的份额（推荐 sum=100 也按总和归一）
"""
from __future__ import annotations
from typing import Dict, Optional
import uuid
import warnings

from ._shared import (

    resolve_palette, xesc, svg_open, svg_close, auto_font_size,
    _rgba_with_alpha, rgb_tuple, gradient_def,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _prepend_bg_if_dark, _render_title_block, _resolve_font, _resolve_palette, _rgba_with_alpha, _variant_is_classic, _dispatch_to_svg_lib, _ink_on_bg)


def _luma(rgba_str):
    """从 rgba(r,g,b,...) 字符串计算感知亮度（0-255）。"""
    r, g, b = rgb_tuple(rgba_str)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _seg_text_color(fill_rgba, pal, min_contrast=60.0):
    """根据段填色亮度自适应挑选段内文字颜色，保证与 fill 的 luma 差 >= min_contrast。

    - 若 fill 已经"深"（luma < 128）→ 用浅色文字（palette 若已定义浅 ink 就用之，否则近白）
    - 若 fill 已经"浅"（luma >= 128）→ 用深色文字（近黑或深 ink）

    参考 _ink_on_bg：该函数只判断 palette.bg 与 palette.ink，无法处理每段不同 fill 的场景。
    此处按 fill 逐段决定，避免深绿底 + palette ink（也是深绿）导致的低对比。
    """
    fill_l = _luma(fill_rgba)
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink_l = _luma(ink)
    # 决定"浅"和"深"两个候选：优先复用 palette 内已经存在的颜色，
    # fallback 到硬编码 near-white / near-black 保证对比。
    if ink_l >= 200:  # palette.ink 本身就是浅色（深底 palette 典型）
        light_col = ink
        dark_col = "rgba(28,28,26,1)"
    elif ink_l <= 60:  # palette.ink 是深色（浅底 palette 典型）
        light_col = "rgba(248,246,240,1)"
        dark_col = ink
    else:
        light_col = "rgba(248,246,240,1)"
        dark_col = "rgba(28,28,26,1)"
    if fill_l < 128:
        candidate = light_col
    else:
        candidate = dark_col
    # 保底：若挑选的候选与 fill 仍然对比不足（异常配色），强制切到另一档
    if abs(_luma(candidate) - fill_l) < min_contrast:
        candidate = dark_col if candidate == light_col else light_col
    return candidate
VARIANTS = (
    "default_flat", "mekko_gradient", "mekko_outlined",
    "shaded_residual", "treemap_flat",
)


def _series_colors(pal, n):
    series = pal.get("series")
    if series:
        return [series[i % len(series)] for i in range(n)]
    # fallback
    ink, acc = pal["ink"], pal["accent"]
    return [acc, pal["secondary"], ink, pal["muted"]][:n] + [acc] * max(0, n - 4)


def draw_marimekko(
    data: Dict,
    variant: str = "default_flat",
    palette="archive_ink",
    width: float = 900,
    height: float = 540,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    figure_label: Optional[str] = None,
) -> str:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}. Available: {VARIANTS}")

    markets = data.get("markets") or []
    if not markets:
        raise ValueError("marimekko: at least one market required")
    we_key = data.get("we_key")

    pal = resolve_palette(palette)
    ink, ink6, ink4, ink2 = pal["ink"], pal["ink6"], pal["ink4"], pal["ink2"]
    bg = pal["bg"]
    accent = pal["accent"]
    series = _series_colors(pal, max(4, max(len(m[2]) for m in markets)))

    body_font = "Inter, sans-serif"
    head_font = "Georgia, serif"

    # 归一化 market_share
    total_mkt = sum(w for _, w, _ in markets) or 1.0
    if abs(total_mkt - 100) > 5 and total_mkt > 0:
        # 归一化不 warn，只按比例分配
        pass

    # layout
    ML = 80
    MR = 40
    # 顶部留足空间：figure label + title + subtitle + market header
    MT = 60 + (30 if title else 0) + (20 if subtitle else 0) + 40  # 40 for market header row
    MB = 60
    plot_x = ML
    plot_y = MT
    plot_w = width - ML - MR
    plot_h = height - MT - MB

    parts = [svg_open(0, 0, width, height, bg=bg)]

    # 唯一 ID 前缀：避免同一 deck 里多个 marimekko（尤其 mekko_gradient variant）
    # 共用 palette 时因固定 gid 撞车导致 duplicate_element_id。参考 matrix_heat R6.5 修法。
    _uid_prefix = uuid.uuid4().hex[:6]

    # title / subtitle
    if figure_label:
        parts.append(
            f'<text x="{ML}" y="24" font-family="{body_font}" font-size="10" '
            f'font-weight="700" fill="{pal["muted"]}" letter-spacing=".18em">{xesc(figure_label)}</text>'
        )
    title_y = 52
    if title:
        parts.append(
            f'<text x="{ML}" y="{title_y}" font-family="{head_font}" '
            f'font-size="22" font-weight="600" fill="{ink}">{xesc(title)}</text>'
        )
        title_y += 20
    if subtitle:
        parts.append(
            f'<text x="{ML}" y="{title_y}" font-family="{body_font}" font-size="11" '
            f'fill="{pal["muted"]}" letter-spacing=".08em">{xesc(subtitle)}</text>'
        )

    # 收集 defs（gradient 需要）
    defs_parts = []

    # 每个 market 一列，宽度按 market_share
    # 每列内 sub 按 sub_share 归一到 plot_h
    x_cursor = plot_x
    n_markets = len(markets)
    fs_hdr = auto_font_size(n_markets, base=12, min_size=9, max_size=14)
    fs_sub = auto_font_size(n_markets, base=10, min_size=8, max_size=11)

    # shaded_residual: 预算每 sub 的加权平均份额
    avg_sub = {}
    max_res = 1e-6
    if variant == "shaded_residual":
        all_subs = {}
        for _, mw, subs in markets:
            for name, sh in subs:
                all_subs.setdefault(name, []).append((mw, sh))
        for name, entries in all_subs.items():
            tw = sum(mw for mw, _ in entries) or 1
            avg_sub[name] = sum(mw * sh for mw, sh in entries) / tw
        for _, _mw, subs in markets:
            for sname, sh in subs:
                r = sh - avg_sub.get(sname, sh)
                if abs(r) > max_res:
                    max_res = abs(r)

    # 描边色（treemap / outlined）
    stroke_col = _rgba_with_alpha(ink, 0.45)

    # 主循环
    for mi, (mname, mw, subs) in enumerate(markets):
        col_w = plot_w * (mw / total_mkt)
        if col_w <= 0.5:
            x_cursor += col_w
            continue

        # market 顶部标签
        # 每字符估宽 ≈ fs_hdr * 0.55 (Latin) / fs_hdr (CJK)；预留 4px 视觉 padding。
        # 不允许 truncate → 逐步下调字号直到装得下，最后不行就 wrap 到 2 行 tspan。
        def _est_hdr_w(s, fs):
            return sum((fs if ord(c) > 127 else fs * 0.55) for c in s)
        avail_hdr_w = max(col_w - 4, 0)
        _fs_hdr_cur = float(fs_hdr)
        _fs_hdr_floor = 7.0
        while _fs_hdr_cur >= _fs_hdr_floor and _est_hdr_w(mname, _fs_hdr_cur) > avail_hdr_w:
            _fs_hdr_cur -= 0.5
        wrap_lines = None
        if _est_hdr_w(mname, _fs_hdr_cur) > avail_hdr_w and len(mname) >= 2:
            # 单行仍装不下（floor 已到）→ 均分为两行 tspan
            mid = len(mname) // 2
            # 优先按空格/-/. 断行
            split_i = mid
            for i in range(max(1, mid - 3), min(len(mname), mid + 3)):
                if mname[i] in " -._/":
                    split_i = i
                    break
            line_a = mname[:split_i].rstrip(" -._/")
            line_b = mname[split_i:].lstrip(" -._/")
            if line_a and line_b:
                wrap_lines = (line_a, line_b)
        if wrap_lines is not None:
            # 2 行时字号再压 0.85x 保证纵向仍在 header 空间内
            _fs_wrap = max(7.0, _fs_hdr_cur * 0.85)
            # 让两行文字仍尽量填不下就再降字号
            while _fs_wrap >= 7.0 and max(
                _est_hdr_w(wrap_lines[0], _fs_wrap),
                _est_hdr_w(wrap_lines[1], _fs_wrap),
            ) > avail_hdr_w:
                _fs_wrap -= 0.5
            cx_mid = x_cursor + col_w / 2
            parts.append(
                f'<text x="{cx_mid:.1f}" y="{plot_y - 26:.1f}" text-anchor="middle" '
                f'font-family="{body_font}" font-size="{_fs_wrap}" font-weight="700" '
                f'fill="{ink}">'
                f'<tspan x="{cx_mid:.1f}" dy="0">{xesc(wrap_lines[0])}</tspan>'
                f'<tspan x="{cx_mid:.1f}" dy="{_fs_wrap * 1.05:.1f}">{xesc(wrap_lines[1])}</tspan>'
                f'</text>'
            )
        else:
            parts.append(
                f'<text x="{x_cursor + col_w/2:.1f}" y="{plot_y - 20:.1f}" text-anchor="middle" '
                f'font-family="{body_font}" font-size="{_fs_hdr_cur}" font-weight="700" '
                f'fill="{ink}">{xesc(mname)}</text>'
            )
        parts.append(
            f'<text x="{x_cursor + col_w/2:.1f}" y="{plot_y - 6:.1f}" text-anchor="middle" '
            f'font-family="{body_font}" font-size="{fs_sub}" fill="{pal["muted"]}">'
            f'{mw/total_mkt*100:.0f}%</text>'
        )

        # 归一化 sub 到 plot_h
        total_sh = sum(sh for _, sh in subs) or 1.0
        y_cursor = plot_y

        # 灰阶轮转（default_flat 用）
        grays = [ink4, ink2, ink6, _rgba_with_alpha(ink, 0.32)]
        gi = 0

        for si, (sname, sh) in enumerate(subs):
            seg_h = plot_h * (sh / total_sh)
            if seg_h <= 0.3:
                y_cursor += seg_h
                continue

            # 决定填色
            if variant == "default_flat":
                if we_key is not None and sname == we_key:
                    fill = accent
                else:
                    fill = grays[gi % len(grays)]
                    gi += 1
                # 段内文字随 fill 亮度自适应，避免深底 + 深 ink 字对比不足
                text_col = _seg_text_color(fill, pal)
                stroke = ""
            elif variant == "mekko_gradient":
                base_col = series[si % len(series)]
                gid = f"mmk_g_{_uid_prefix}_{mi}_{si}"
                defs_parts.append(gradient_def(
                    gid, base_col, direction="vertical",
                    x1=x_cursor, y1=y_cursor, x2=x_cursor, y2=y_cursor + seg_h,
                ))
                fill = f"url(#{gid})"
                # gradient 中间亮度用 base_col 估算即可
                text_col = _seg_text_color(base_col, pal)
                stroke = ""
            elif variant == "mekko_outlined":
                base_col = series[si % len(series)]
                fill = _rgba_with_alpha(base_col, 0.22)
                # outlined 变体 fill 是低 alpha，实际视觉接近 bg → 用 _ink_on_bg 派生
                text_col = _ink_on_bg(pal)
                stroke = base_col
            elif variant == "shaded_residual":
                residual = sh - avg_sub.get(sname, sh)
                intensity = min(1.0, abs(residual) / (max_res + 1e-9))
                if residual > 0:
                    r, g, b = rgb_tuple(accent)
                    fill = f"rgba({r},{g},{b},{0.20 + 0.60 * intensity:.3f})"
                else:
                    # cool blue
                    fill = f"rgba(90,110,150,{0.20 + 0.60 * intensity:.3f})"
                # residual 变体半透明填色在 bg 上有效亮度接近 bg，用 _ink_on_bg 保底
                text_col = _ink_on_bg(pal)
                stroke = _rgba_with_alpha(ink, 0.3)
            elif variant == "treemap_flat":
                fill = series[si % len(series)]
                text_col = _seg_text_color(fill, pal)
                stroke = ""

            rect_stroke = (
                f' stroke="{stroke}" stroke-width="1.2"' if stroke else ""
            )
            # 白色/背景色分隔线间距
            gap = 1.5 if variant in ("default_flat", "treemap_flat") else 0
            parts.append(
                f'<rect x="{x_cursor:.1f}" y="{y_cursor:.1f}" '
                f'width="{max(col_w - gap, 0.5):.1f}" height="{max(seg_h - gap, 0.5):.1f}" '
                f'fill="{fill}"{rect_stroke}/>'
            )

            # 段内标签
            pct_str = f"{sh/total_sh*100:.0f}%"
            label = f"{sname} {pct_str}"
            fs_label = auto_font_size(len(subs), base=11, min_size=8, max_size=13)
            # font-size-aware CJK-aware width estimator：Latin ≈ fs*0.62, CJK ≈ fs
            def _est_w(txt, fs):
                return sum((fs if ord(c) > 127 else fs * 0.62) for c in txt) + 6
            est_w_full = _est_w(label, fs_label)
            est_w_pct = _est_w(pct_str, fs_label - 1)
            avail_w = col_w - 8  # 段内水平预留 padding
            if seg_h >= fs_label + 8 and est_w_full <= avail_w:
                parts.append(
                    f'<text x="{x_cursor + col_w/2:.1f}" y="{y_cursor + seg_h/2 + fs_label/3:.1f}" '
                    f'text-anchor="middle" font-family="{body_font}" font-size="{fs_label}" '
                    f'font-weight="700" fill="{text_col}">{xesc(label)}</text>'
                )
                # shaded_residual: 只在 seg 宽度 & 高度都够时才画 Δ 增量
                # 短 Δ 格式（整数）在窄 seg 下用，长格式（一位小数）在宽 seg 下用
                if variant == "shaded_residual" and seg_h >= fs_label * 2 + 10:
                    residual = sh - avg_sub.get(sname, sh)
                    delta_short = f"Δ{residual:+.0f}"
                    delta_full = f"Δ{residual:+.1f}"
                    fs_delta = fs_label - 2
                    est_delta_full = _est_w(delta_full, fs_delta)
                    est_delta_short = _est_w(delta_short, fs_delta)
                    delta_str = None
                    if est_delta_full <= avail_w:
                        delta_str = delta_full
                    elif est_delta_short <= avail_w:
                        delta_str = delta_short
                    if delta_str is not None:
                        parts.append(
                            f'<text x="{x_cursor + col_w/2:.1f}" y="{y_cursor + seg_h/2 + fs_label + 6:.1f}" '
                            f'text-anchor="middle" font-family="{body_font}" font-size="{fs_delta}" '
                            f'fill="{pal["muted"]}">{delta_str}</text>'
                        )
            elif seg_h >= fs_label + 6 and est_w_pct <= avail_w:
                # 窄 col 兜底：只画百分比数值（不画 vendor 名）
                parts.append(
                    f'<text x="{x_cursor + col_w/2:.1f}" y="{y_cursor + seg_h/2 + fs_label/3:.1f}" '
                    f'text-anchor="middle" font-family="{body_font}" font-size="{fs_label-1}" '
                    f'font-weight="700" fill="{text_col}">{pct_str}</text>'
                )
            y_cursor += seg_h

        x_cursor += col_w

    # legend for shaded_residual
    if variant == "shaded_residual":
        ly = height - MB + 22
        r, g, b = rgb_tuple(accent)
        parts.append(
            f'<rect x="{ML}" y="{ly}" width="14" height="10" fill="rgba({r},{g},{b},0.75)"/>'
        )
        parts.append(
            f'<text x="{ML + 20}" y="{ly + 9}" font-family="{body_font}" font-size="10" '
            f'fill="{ink}">Positive residual</text>'
        )
        parts.append(
            f'<rect x="{ML + 150}" y="{ly}" width="14" height="10" fill="rgba(90,110,150,0.75)"/>'
        )
        parts.append(
            f'<text x="{ML + 170}" y="{ly + 9}" font-family="{body_font}" font-size="10" '
            f'fill="{ink}">Negative residual</text>'
        )

    # we_key legend for default_flat
    if variant == "default_flat" and we_key is not None:
        ly = height - MB + 22
        parts.append(
            f'<rect x="{ML}" y="{ly}" width="14" height="10" fill="{accent}"/>'
        )
        parts.append(
            f'<text x="{ML + 20}" y="{ly + 9}" font-family="{body_font}" font-size="10" '
            f'fill="{ink}">{xesc(we_key)} (our vendor)</text>'
        )

    # 组装 defs
    if defs_parts:
        defs_str = "<defs>" + "".join(defs_parts) + "</defs>"
        parts.insert(1, defs_str)

    parts.append(svg_close())
    return "".join(parts)


def make_marimekko(markets,
                   width: float = 900.0,
                   height: float = 540.0,
                   we_key: str = "Us",
                   accent_rgb: Sequence[int] = None,
                   title: str = None,
                   subtitle: str = None,
                   figure_label: str = None,
                          font_family: str = None,
                          palette=None,
                variant: str = None) -> str:
    """
    双向占比：列宽 = 市场大小，列内高度 = 各竞品份额。管理咨询"业务组合矩阵"经典图种。
    我方（we_key 匹配）永远用 accent 主色实心，其他子项退到灰阶。

    markets: [(market_name, market_share, [(sub_name, inside_share), ...]), ...]
             market_share: 市场规模占比（总和不必=100，函数按输入总和归一）
             inside_share: **必须**是 0-100 的百分数（30 代表 30%）；如果传 0.30 会被识别为 0.3% 显示
             ——如果所有 inside_share 都 <= 1，函数会自动 × 100 并 warn。
    we_key:  哪个 sub_name 视为"我方"，用 accent 主色高亮
    accent_rgb: 高亮色 RGB 元组，缺省 None 时用默认赭石 (163,88,50)。
                想切品牌色（如 deep teal）时显式传，字符串 recolor 摸不到本参数烘焙进 fill 的自定义色。
    """
    if not _variant_is_classic('marimekko', variant):
        _data = {"markets": list(markets), "we_key": we_key}
        return _dispatch_to_svg_lib(
            'marimekko', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    # ---- palette 支持（模块级 helper 注入）----
    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    if not markets:
        raise ValueError("marimekko: at least one market required")
    if accent_rgb is not None:
        accent_color = f"rgba({accent_rgb[0]},{accent_rgb[1]},{accent_rgb[2]},1.0)"
    else:
        accent_color = _ACC
    # 自动检测 inside_share 单位：如果整体最大值 <= 1，认为是小数（0-1 之间），× 100
    all_inside = [sh for _, _, shs in markets for _, sh in shs]
    if all_inside and max(all_inside) <= 1.0 and any(v > 0 for v in all_inside):
        import warnings
        warnings.warn("marimekko: inside_share 都 <= 1，判定为小数形式（0.28 = 28%），自动 × 100")
        markets = [(mname, mw, [(s, sh * 100) for s, sh in shs]) for mname, mw, shs in markets]
    total_mkt = sum(w for _, w, _ in markets) or 1
    # 内容区距画布边缘留白：左 30 / 右 20 / 顶 55（给市场名 + 占比 2 行）/ 底 30
    x_left, x_right = 30.0, width - 20.0
    y_top, y_bot = 55.0, height - 30.0
    total_w = x_right - x_left
    parts = []
    cx = x_left
    # 灰阶轮转（跳过 we_key），保证多个非我方竞品用不同灰度区分
    _grays = [_INK4, _INK2, _INK6, _INK1]
    # ---------- 字号自适应（viewBox + 数据规模双重）----------
    # slide 里 3 图并列 ≈ 400px，viewBox=900 → 缩放 ~0.44x；字号需相应放大
    _n_mk_fs = len(markets)
    _fs_base = min(float(width), float(height)) * 0.022
    if _n_mk_fs <= 4:
        _fs_mult = 1.5
    elif _n_mk_fs <= 8:
        _fs_mult = 1.15
    elif _n_mk_fs <= 15:
        _fs_mult = 0.9
    else:
        _fs_mult = 0.72
    fs_market_name = max(18.0, _fs_base * 1.55 * _fs_mult)   # 顶部市场名
    fs_market_pct  = max(13.0, _fs_base * 1.05 * _fs_mult)   # 顶部占比
    fs_seg         = max(15.0, _fs_base * 1.25 * _fs_mult)   # 段内 label + %
    fs_seg_pct     = max(13.0, _fs_base * 1.05 * _fs_mult)   # 窄段只显示 %
    for mi, (mname, mw, shares) in enumerate(markets):
        col_w = mw / total_mkt * total_w
        # 若 col_w 装不下 market name 全宽，先按每字符 fs_market_name*0.85 (CJK) 估算，
        # 逐步下探字号到 min，仍不够则显示为省略号；否则相邻窄列的 header label
        # bbox 会相互重叠触发 embed_svg_bbox_overlap（"非洲"/"拉美" 相邻场景）。
        def _est_label_w(s, fs):
            return sum((fs if ord(c) > 127 else fs * 0.55) for c in s)
        _avail_hdr_w = max(col_w - 6.0, 0.0)  # 两侧各 3px padding
        _fs_hdr = fs_market_name
        # 允许字号一路下探到 7pt，避免早早触发截断/wrap
        _fs_hdr_floor = 7.0
        while _fs_hdr >= _fs_hdr_floor and _est_label_w(mname, _fs_hdr) > _avail_hdr_w:
            _fs_hdr -= 0.5
        _wrap_lines = None
        if _est_label_w(mname, _fs_hdr) > _avail_hdr_w and len(mname) >= 2:
            # 单行仍装不下 → 强制 wrap 到 2 行 tspan，不截断
            mid = len(mname) // 2
            split_i = mid
            for _i in range(max(1, mid - 3), min(len(mname), mid + 3)):
                if mname[_i] in " -._/":
                    split_i = _i
                    break
            _la = mname[:split_i].rstrip(" -._/")
            _lb = mname[split_i:].lstrip(" -._/")
            if _la and _lb:
                _wrap_lines = (_la, _lb)
                # 2 行时字号再压 0.85x，同时保证每行都装得下
                _fs_hdr = max(7.0, _fs_hdr * 0.85)
                while _fs_hdr >= 7.0 and max(
                    _est_label_w(_wrap_lines[0], _fs_hdr),
                    _est_label_w(_wrap_lines[1], _fs_hdr),
                ) > _avail_hdr_w:
                    _fs_hdr -= 0.5
        # 同理处理占比数字
        _pct_txt = f"{mw:g}%"
        _fs_pct = fs_market_pct
        _fs_pct_floor = max(8.0, fs_market_pct * 0.6)
        while _fs_pct >= _fs_pct_floor and _est_label_w(_pct_txt, _fs_pct) > _avail_hdr_w:
            _fs_pct -= 1.0
        # 保证 header name bbox 与 pct bbox 不相交：baseline gap ≥ fs_hdr*0.2 + fs_pct*0.8 + 2px
        _hdr_pct_gap = max(20.0, _fs_hdr * 0.2 + _fs_pct * 0.8 + 2.0)
        _pct_y = y_top - 10.0
        _hdr_y = _pct_y - _hdr_pct_gap
        _cx_mid = cx + col_w / 2
        if _wrap_lines is not None:
            # 2 行文本：让第二行 baseline 落在原 header y，第一行往上偏移
            _line_h = _fs_hdr * 1.05
            parts.append(
                f'<text font-family="{_body_font}" x="{_cx_mid:.1f}" y="{_hdr_y - _line_h:.1f}" '
                f'font-size="{_fs_hdr}" font-weight="700" fill="{_INK}" text-anchor="middle" '
                f'letter-spacing=".04em">'
                f'<tspan x="{_cx_mid:.1f}" dy="0">{_wrap_lines[0]}</tspan>'
                f'<tspan x="{_cx_mid:.1f}" dy="{_line_h:.1f}">{_wrap_lines[1]}</tspan>'
                f'</text>'
            )
        else:
            parts.append(f'<text font-family="{_body_font}" x="{_cx_mid:.1f}" y="{_hdr_y:.1f}" font-size="{_fs_hdr}" font-weight="700" fill="{_INK}" text-anchor="middle" letter-spacing=".08em">{mname}</text>')
        parts.append(f'<text font-family="{_body_font}" x="{_cx_mid:.1f}" y="{_pct_y:.1f}" font-size="{_fs_pct}" fill="{_INK6}" text-anchor="middle">{_pct_txt}</text>')
        cy = y_top
        total_share = sum(sh for _, sh in shares) or 100
        gray_i = 0
        for si, (sname, sh) in enumerate(shares):
            seg_h = sh / total_share * (y_bot - y_top)
            if sname == we_key:
                fill = accent_color  # 我方用 accent 主色高亮（可通过 accent_rgb 参数换色）
            else:
                fill = _grays[gray_i % len(_grays)]
                gray_i += 1
            # 段内文字随 fill 亮度自适应：深底 palette + 深 ink 会导致低对比，
            # 用 _seg_text_color 按 fill luma 反色（<128 深底用浅字，反之用深字）。
            text_color = _seg_text_color(fill, _pal)
            parts.append(f'<rect x="{cx+2:.1f}" y="{cy:.1f}" width="{max(col_w-4, 0.1):.1f}" height="{max(seg_h-2, 0.1):.1f}" fill="{fill}"/>')
            # 只有当段内空间容得下文字时才写标签
            pct_str = f"{sh:.0f}%" if abs(sh - round(sh)) < 0.05 else f"{sh:.1f}%"
            label = f"{sname} {pct_str}"
            # CJK 字符宽 ≈ fs, 拉丁字符宽 ≈ fs*0.55；随字号自适应估算
            _est_w = sum((fs_seg if ord(c) > 127 else fs_seg * 0.55) for c in label) + 6
            _min_seg_h = fs_seg * 1.4  # 段高至少能容纳一行标签
            if seg_h >= _min_seg_h and _est_w <= (col_w - 10):
                parts.append(f'<text font-family="{_body_font}" x="{cx + col_w/2:.1f}" y="{cy + seg_h/2 + fs_seg*0.35:.1f}" font-size="{fs_seg}" font-weight="700" fill="{text_color}" text-anchor="middle">{label}</text>')
            elif seg_h >= _min_seg_h and (col_w - 10) >= len(pct_str) * fs_seg_pct * 0.6:
                # 窄列：只显示百分比
                parts.append(f'<text font-family="{_body_font}" x="{cx + col_w/2:.1f}" y="{cy + seg_h/2 + fs_seg_pct*0.35:.1f}" font-size="{fs_seg_pct}" font-weight="700" fill="{text_color}" text-anchor="middle">{pct_str}</text>')
            cy += seg_h
        cx += col_w
    # 顶部标题栏（可选，用负 y 空间）
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    _title_block, _title_h = _render_title_block(
        x_left=0, anchor_y=-6, width=width,
        title=title, subtitle=subtitle, figure_label=figure_label,
        ink=_INK, muted=c_muted,
        body_font=_body_font, heading_font=_head_font,
    )
    # 显式 viewBox：保证宽高比稳定，避免自动包围盒把画布压扁
    body = _title_block + "".join(parts)
    pad = 12.0
    vb_y = -pad - _title_h
    vb_h = height + 2 * pad + _title_h
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad:.1f} {vb_y:.1f} {width + 2*pad:.1f} {vb_h:.1f}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 15) Matrix Heat 矩阵热力
# ==============================================================
