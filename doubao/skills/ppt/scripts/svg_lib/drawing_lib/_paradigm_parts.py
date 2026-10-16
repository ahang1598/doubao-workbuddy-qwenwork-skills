"""Experimental-paradigm figure: ``trial_sequence`` (obliquely stacked stimulus screens with durations and a time arrow)."""

from __future__ import annotations

import math

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _el, _mix, _check_style, _finish
from ._geometry import Box, _finite, label
from ._help import _drawing_api

_INK = "#2A2A33"


def _tw(s, fs, bold=False):
    return label(str(s), font_size=fs, font_weight="bold" if bold else "normal").bounds.width


def _t(x, cy, s, fs, fill, *, anchor="middle", bold=False, italic=False, family=None):
    t = _el(
        "text",
        x=x,
        y=cy + fs * 0.35,
        font_size=fs,
        fill=fill,
        text_anchor=anchor,
        font_weight="bold" if bold else None,
        font_style="italic" if italic else None,
        font_family=family,
    )
    t.text = str(s)
    return t


def _norm(sc):
    if isinstance(sc, str):
        sc = {"content": sc}
    if not isinstance(sc, dict):
        raise TypeError('each screen is a dict like {"label": "刺激", "dur": "500 ms", "content": "K"}')
    return dict(
        label=sc.get("label"),
        dur=sc.get("dur"),
        content=sc.get("content", ""),
        kind=sc.get("kind"),
        note=sc.get("note"),
        color=sc.get("color"),
    )


@_drawing_api(
    "parts",
    purpose="实验范式 / 试次序列（心理物理、认知任务）：斜向层叠的显示器屏幕卡片（注视点 +、刺激字母/词/图形、反应提示、空屏），每屏标时长，旁边一条时间箭头；适用于 n-back、Stroop、Go/No-go、Flanker、启动、视觉搜索等任意范式。",
    returns="Geometry（原点在中心；端口 screen{i}/screen{i}_label/screen{i}_dur/time_start/time_end）",
    semantics=(
        'screens 每项 {"label": 阶段名, "dur": "500 ms", "content": 屏上内容, "kind": "fixation"|"text"|"blank"|"response"|"symbol", "note": 屏下小字}；'
        'content="+" 或 kind="fixation" 画注视十字；kind="response" 画按键提示（content 为按键说明，如 "匹配→F"）；"blank" 空屏；'
        'kind="symbol" 的 content 取 circle/square/triangle/arrow_left/arrow_right/face 画几何刺激；其余按文字居中显示（字号随屏幕自动）。',
        'layout="diagonal"（默认，后一屏向右下错开、前屏压后屏，经典范式图）或 "row"（水平一排，屏间小箭头）。',
        "screen=(w, h) 为单屏尺寸；step=(dx, dy) 为斜向错位（默认 0.62w, 0.5h）；screen_color 屏底色（默认黑底白字，也可浅灰）。",
        'time_arrow=True 沿错位方向画时间箭头（标 time_label，默认 "时间"）；阶段名与时长叠放在每屏右侧（row 布局为屏上/屏下），不压屏。',
        'repeat="×20 试次" 等在最后一屏后标重复说明；全部原生可编辑。',
    ),
    example='d.place(trial_sequence([{"label": "注视", "dur": "500 ms", "content": "+"}, {"label": "刺激", "dur": "500 ms", "content": "K"},\n'
    '        {"label": "间隔", "dur": "1500 ms", "kind": "blank"}, {"label": "反应", "dur": "≤2000 ms", "kind": "response", "content": "匹配→F"}]),\n'
    '        at=(480, 270), key="nback")',
    rank=32,
)
def trial_sequence(
    screens,
    *,
    layout="diagonal",
    time_arrow=True,
    time_label="时间",
    screen=(150, 96),
    step=None,
    screen_color="#1E1F24",
    text_color="#FFFFFF",
    frame="#5A5D66",
    accent="#E0A23A",
    font_size=13,
    repeat=None,
    style="rich",
):
    rich = _check_style(style)
    if layout not in ("diagonal", "row"):
        raise ValueError('layout must be "diagonal" or "row"')
    screens = [_norm(s) for s in screens]
    if not screens:
        raise ValueError("screens must list at least one screen")
    sw_, sh_ = screen
    _finite(sw_, sh_, font_size)
    fs = float(font_size)
    bez = max(5.0, sh_ * 0.07)
    W, Hs = sw_ + 2 * bez, sh_ + 2 * bez
    if step is None:
        step = (W * 0.62, Hs * 0.52) if layout == "diagonal" else (W + fs * 3.2, 0)
    dx, dy = step
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    dark_screen = (
        sum(int(screen_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)) < 300 if len(screen_color) == 7 else True
    )
    tc = text_color if dark_screen else _INK
    x0 = 0
    y0 = fs * 1.6 if layout == "row" else 0
    ports, pts, texts = {}, [], []
    cards = []
    for i, s in enumerate(screens):
        x, y = x0 + dx * i, y0 + dy * i
        cards.append((x, y, s))
    for i, (x, y, s) in enumerate(cards):  # later screens in front, as in a time-ordered stack
        g = []
        g.append(
            _el(
                "rect",
                x=x,
                y=y,
                width=W,
                height=Hs,
                rx=bez * 0.9,
                fill=frame,
                stroke=_mix(frame, "#000000", 0.45),
                stroke_width=1.2,
                data_outline="1" if i == 0 else None,
            )
        )
        scol = s["color"] or screen_color
        if rich:
            g.append(
                _el(
                    "path",
                    d=f"M{fmt(x + bez * 0.9)} {fmt(y + 1.6)} L{fmt(x + W - bez * 0.9)} {fmt(y + 1.6)}",
                    fill="none",
                    stroke=_mix(frame, "#FFFFFF", 0.45),
                    stroke_width=1.2,
                    stroke_linecap="round",
                )
            )
        g.append(_el("rect", x=x + bez, y=y + bez, width=sw_, height=sh_, rx=2, fill=scol))
        cx, cy = x + W / 2, y + Hs / 2
        kind = s["kind"] or (
            "fixation" if str(s["content"]).strip() == "+" else "blank" if not s["content"] else "text"
        )
        m = min(sw_, sh_)
        if kind == "fixation":
            a, t = m * 0.11, max(1.6, m * 0.028)
            g.append(
                _el(
                    "path",
                    d=f"M{fmt(cx - a)} {fmt(cy)} L{fmt(cx + a)} {fmt(cy)} M{fmt(cx)} {fmt(cy - a)} L{fmt(cx)} {fmt(cy + a)}",
                    fill="none",
                    stroke=tc,
                    stroke_width=t,
                    stroke_linecap="butt",
                )
            )
        elif kind == "symbol":
            sym, r = str(s["content"]), m * 0.2
            col = accent
            if sym == "circle":
                g.append(_el("circle", cx=cx, cy=cy, r=r, fill=col))
            elif sym == "square":
                g.append(_el("rect", x=cx - r, y=cy - r, width=2 * r, height=2 * r, fill=col))
            elif sym == "triangle":
                g.append(
                    _el(
                        "path",
                        d=f"M{fmt(cx)} {fmt(cy - r)} L{fmt(cx + r * 1.1)} {fmt(cy + r * 0.8)} L{fmt(cx - r * 1.1)} {fmt(cy + r * 0.8)} Z",
                        fill=col,
                    )
                )
            elif sym in ("arrow_left", "arrow_right"):
                k = -1 if sym == "arrow_left" else 1
                p = [
                    (cx - k * r * 1.3, cy - r * 0.3),
                    (cx + k * r * 0.1, cy - r * 0.3),
                    (cx + k * r * 0.1, cy - r * 0.75),
                    (cx + k * r * 1.3, cy),
                    (cx + k * r * 0.1, cy + r * 0.75),
                    (cx + k * r * 0.1, cy + r * 0.3),
                    (cx - k * r * 1.3, cy + r * 0.3),
                ]
                g.append(_el("path", d="M" + " L".join(f"{fmt(a)} {fmt(b)}" for a, b in p) + " Z", fill=col))
            elif sym == "face":
                g.append(
                    _el("circle", cx=cx, cy=cy, r=r * 1.1, fill="none", stroke=col, stroke_width=max(1.4, r * 0.12))
                )
                g.append(
                    _el(
                        "path",
                        d=f"M{fmt(cx - r * 0.55)} {fmt(cy + r * 0.3)} Q{fmt(cx)} {fmt(cy + r * 0.8)} {fmt(cx + r * 0.55)} {fmt(cy + r * 0.3)}",
                        fill="none",
                        stroke=col,
                        stroke_width=max(1.4, r * 0.12),
                        stroke_linecap="round",
                    )
                )
                g.append(
                    _el(
                        "path",
                        d=f"M{fmt(cx - r * 0.4)} {fmt(cy - r * 0.25)} m-{fmt(r * 0.12)} 0 a{fmt(r * 0.12)} {fmt(r * 0.12)} 0 1 0 {fmt(r * 0.24)} 0 "
                        f"a{fmt(r * 0.12)} {fmt(r * 0.12)} 0 1 0 -{fmt(r * 0.24)} 0 M{fmt(cx + r * 0.4)} {fmt(cy - r * 0.25)} "
                        f"m-{fmt(r * 0.12)} 0 a{fmt(r * 0.12)} {fmt(r * 0.12)} 0 1 0 {fmt(r * 0.24)} 0 a{fmt(r * 0.12)} {fmt(r * 0.12)} 0 1 0 -{fmt(r * 0.24)} 0",
                        fill=col,
                    )
                )
            else:
                raise ValueError("symbol content must be circle/square/triangle/arrow_left/arrow_right/face")
        elif kind == "response":
            kw, kh = m * 0.3, m * 0.26
            g.append(
                _el(
                    "rect",
                    x=cx - kw / 2,
                    y=cy - kh * 0.95,
                    width=kw,
                    height=kh,
                    rx=3,
                    fill=_mix(scol, "#FFFFFF", 0.85),
                    stroke=accent,
                    stroke_width=1.6,
                )
            )
            g.append(
                _el(
                    "rect",
                    x=cx - kw / 2,
                    y=cy - kh * 0.95 + kh * 0.78,
                    width=kw,
                    height=kh * 0.22,
                    rx=2,
                    fill=_mix(accent, "#000000", 0.1),
                )
            )
            if s["content"]:
                rfs = min(fs, sw_ * 0.9 / max(1, len(str(s["content"])) * 0.62))
                g.append(_t(cx, cy + kh * 0.55, s["content"], rfs, tc))
        elif kind == "text":
            c = str(s["content"])
            sfs = min(sh_ * 0.42, sw_ * 0.82 / max(1.0, _tw(c, 1.0, True)))
            g.append(_t(cx, cy, c, sfs, tc, bold=True, family="Arial"))
        holder.extend(g)
        ports[f"screen{i}"] = (cx, cy)
        pts += [(x, y), (x + W, y + Hs)]
    # labels (phase names) and durations, outside every screen
    for i, (x, y, s) in enumerate(cards):
        if layout == "diagonal":
            # phase name + duration stacked right of the screen, in the band above the next screen
            tx = x + W + fs * 0.6
            ly = y + fs * 0.95
            if s["label"]:
                texts.append(_t(tx, ly, s["label"], fs, _INK, anchor="start", bold=True))
                ports[f"screen{i}_label"] = (tx, ly)
                pts.append((tx + _tw(s["label"], fs, True), ly - fs * 0.8))
            if s["dur"]:
                dyl = ly + fs * 1.35 if s["label"] else ly
                texts.append(_t(tx, dyl, s["dur"], fs, _mix(accent, "#000000", 0.35), anchor="start"))
                ports[f"screen{i}_dur"] = (tx, dyl)
                pts.append((tx + _tw(s["dur"], fs), dyl + fs * 0.6))
        else:
            if s["label"]:
                texts.append(_t(x + W / 2, y - fs * 0.9, s["label"], fs, _INK, bold=True))
                ports[f"screen{i}_label"] = (x + W / 2, y - fs * 0.9)
                pts.append((x + W / 2, y - fs * 1.7))
            if s["dur"]:
                texts.append(_t(x + W / 2, y + Hs + fs * 0.95, s["dur"], fs, _mix(accent, "#000000", 0.35), bold=True))
                ports[f"screen{i}_dur"] = (x + W / 2, y + Hs + fs * 0.95)
                pts.append((x + W / 2, y + Hs + fs * 1.7))
        if s["note"]:
            ny = y + Hs + fs * (2.2 if layout == "row" else 0.95)
            nx = x + W / 2 if layout == "row" else x + W * 0.3
            texts.append(_t(nx, ny, s["note"], fs * 0.85, "#6A6A76"))
            pts.append((nx - _tw(s["note"], fs * 0.85) / 2, ny + fs * 0.6))
            pts.append((nx + _tw(s["note"], fs * 0.85) / 2, ny + fs * 0.6))
    if layout == "row":
        for (xa, ya, _), (xb, yb, _) in zip(cards, cards[1:]):
            a, b, ym = xa + W + fs * 0.5, xb - fs * 0.5, ya + Hs / 2
            holder.append(
                _el(
                    "path", d=f"M{fmt(a)} {fmt(ym)} L{fmt(b - 6)} {fmt(ym)}", fill="none", stroke=_INK, stroke_width=1.6
                )
            )
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(b)} {fmt(ym)} L{fmt(b - 8)} {fmt(ym - 4.5)} L{fmt(b - 8)} {fmt(ym + 4.5)} Z",
                    fill=_INK,
                )
            )
    if time_arrow:
        lx, ly = cards[0][0], cards[0][1]
        ex, ey = cards[-1][0], cards[-1][1]
        if layout == "diagonal":
            off = fs * 2.2
            ax0, ay0 = lx + W * 0.2, ly + Hs + off
            ax1, ay1 = ex + W * 0.2 + dx * 0.3, ey + Hs + off + dy * 0.3
        else:
            ax0, ay0 = lx, ly + Hs + fs * (3.6 if any(s["note"] for s in screens) else 2.4)
            ax1, ay1 = ex + W, ay0
        L = math.hypot(ax1 - ax0, ay1 - ay0) or 1
        ux, uy = (ax1 - ax0) / L, (ay1 - ay0) / L
        hs = 10.0
        holder.append(
            _el(
                "path",
                d=f"M{fmt(ax0)} {fmt(ay0)} L{fmt(ax1 - ux * hs * 0.8)} {fmt(ay1 - uy * hs * 0.8)}",
                fill="none",
                stroke=_INK,
                stroke_width=2,
            )
        )
        bx, by = ax1 - ux * hs, ay1 - uy * hs
        holder.append(
            _el(
                "path",
                d=f"M{fmt(ax1)} {fmt(ay1)} L{fmt(bx - uy * hs * 0.5)} {fmt(by + ux * hs * 0.5)} L{fmt(bx + uy * hs * 0.5)} {fmt(by - ux * hs * 0.5)} Z",
                fill=_INK,
            )
        )
        if time_label:
            if layout == "diagonal":
                tx, ty = ax1 + ux * fs * 0.4, ay1 + uy * fs * 0.4 + fs * 0.3
                texts.append(_t(tx, ty, time_label, fs, _INK, anchor="start", bold=True))
                pts.append((tx + _tw(time_label, fs, True), ty + fs * 0.6))
            else:
                texts.append(_t(ax1 + fs * 0.4, ay1, time_label, fs, _INK, anchor="start", bold=True))
                pts.append((ax1 + fs * 0.4 + _tw(time_label, fs, True), ay1 + fs * 0.6))
        pts += [(ax0, ay0), (ax1, ay1 + 4), (ax1 + 6, ay1)]
        ports.update(time_start=(ax0, ay0), time_end=(ax1, ay1))
    if repeat:
        ex, ey = cards[-1][0], cards[-1][1]
        rx_, ry_ = (ex + W + fs * 0.6, ey + fs * 3.9) if layout == "diagonal" else (ex + W + fs * 0.6, ey + Hs / 2)
        texts.append(_t(rx_, ry_, repeat, fs, "#6A6A76", anchor="start", italic=True))
        pts.append((rx_ + _tw(repeat, fs), ry_ + fs * 0.6))
        pts.append((rx_, ry_ - fs * 0.6))
    holder.extend(texts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return _finish(holder, defs, Box(min(xs) - 1, min(ys) - 1, max(xs) - min(xs) + 2, max(ys) - min(ys) + 2), **ports)
