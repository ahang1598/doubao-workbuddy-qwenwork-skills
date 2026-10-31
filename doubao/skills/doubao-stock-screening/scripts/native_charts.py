"""Browser-rendered SVG charts shared by structured and legacy reports."""

import html
import math
import re

CHART_COLORS = ('#1a3554', '#b48945', '#13756e', '#aa4a48', '#667b9f')


def render_chart(spec):
    """Turn verified numeric data into browser-rendered SVG, without a PNG step."""
    if not isinstance(spec, dict):
        raise ValueError('图表数据必须是 JSON 对象')
    title, source = spec.get('title'), spec.get('source')
    labels, series = spec.get('x'), spec.get('series')
    if not isinstance(title, str) or not title.strip() or not isinstance(source, str) or not source.strip():
        raise ValueError('图表需要 title 和 source')
    if not isinstance(labels, list) or not labels or not all(isinstance(x, str) for x in labels):
        raise ValueError('图表 x 必须是非空文字数组')
    if not isinstance(series, list) or not series:
        raise ValueError('图表 series 必须是非空数组')
    checked = []
    for index, item in enumerate(series):
        if not isinstance(item, dict) or item.get('type') not in {'bar', 'line'}:
            raise ValueError('图表 series 仅支持 bar 或 line')
        values = item.get('values')
        if not isinstance(values, list) or len(values) != len(labels):
            raise ValueError('图表 series.values 长度必须与 x 一致')
        if any(v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)) for v in values):
            raise ValueError('图表数值必须是有限数字或 null')
        axis = item.get('axis', 'left')
        if axis not in {'left', 'right'}:
            raise ValueError('图表 axis 只能是 left 或 right')
        color = item.get('color', CHART_COLORS[index % len(CHART_COLORS)])
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('图表 color 必须是六位十六进制颜色')
        name = item.get('name')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('图表 series 需要 name')
        checked.append((item['type'], name, values, axis, color))
    events = spec.get('events', [])
    if not isinstance(events, list):
        raise ValueError('图表 events 必须是数组')
    for event in events:
        if not isinstance(event, dict) or event.get('at') not in labels or not isinstance(event.get('label'), str):
            raise ValueError('图表事件需要已存在于 x 的 at 和文字 label')

    width, height = 900, 470
    left, right, top, bottom = 76, 824, 104, 384
    plot_height, band = bottom - top, (right - left) / len(labels)
    has_right = any(s[3] == 'right' for s in checked)
    def limits(axis):
        active = [s for s in checked if s[3] == axis]
        numbers = [v for s in active for v in s[2] if v is not None]
        if not numbers:
            return 0.0, 1.0
        low, high = min(numbers), max(numbers)
        if any(s[0] == 'bar' for s in active):
            low, high = min(0, low), max(0, high)
        else:
            span = high - low or max(abs(high) * .1, 1)
            low, high = low - span * .12, high + span * .12
        if low == high:
            high = low + 1
        return low, high
    ranges = {'left': limits('left'), 'right': limits('right')}
    def ycoord(value, axis):
        lo, hi = ranges[axis]
        return bottom - (value - lo) / (hi - lo) * plot_height
    def fmt(value):
        return f'{value:,.2f}'.rstrip('0').rstrip('.') if abs(value) < 10000 else f'{value:,.0f}'
    def esc(value):
        return html.escape(str(value), quote=True)

    svg = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}" xmlns="http://www.w3.org/2000/svg">']
    svg.append('<style>text{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;fill:#607086;font-size:13px}.tick{font-size:12px}.value{font-size:12px;font-weight:600}.event{font-size:11px;fill:#aa4a48}</style>')
    for tick in range(5):
        yy = bottom - tick * plot_height / 4
        svg.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" stroke="#dbe3eb" stroke-dasharray="3 4"/>')
        for axis, xx, anchor in (('left', left - 9, 'end'), ('right', right + 9, 'start')):
            if axis == 'right' and not has_right:
                continue
            lo, hi = ranges[axis]
            svg.append(f'<text class="tick" x="{xx}" y="{yy + 4:.1f}" text-anchor="{anchor}">{esc(fmt(lo + tick * (hi - lo) / 4))}</text>')
    svg.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#607086"/>')
    for i, label in enumerate(labels):
        xx = left + band * (i + .5)
        if len(labels) > 8:
            svg.append(f'<text class="tick" x="{xx:.1f}" y="{bottom + 22}" transform="rotate(-35 {xx:.1f} {bottom + 22})" text-anchor="end">{esc(label)}</text>')
        else:
            svg.append(f'<text class="tick" x="{xx:.1f}" y="{bottom + 23}" text-anchor="middle">{esc(label)}</text>')
    bar_series = [s for s in checked if s[0] == 'bar']
    bar_width = min(52, band * .72 / max(1, len(bar_series)))
    for bar_index, (_, name, values, axis, color) in enumerate(bar_series):
        baseline = ycoord(0, axis) if ranges[axis][0] <= 0 <= ranges[axis][1] else bottom
        for i, value in enumerate(values):
            if value is None:
                continue
            center = left + band * (i + .5) + (bar_index - (len(bar_series) - 1) / 2) * bar_width
            yy = ycoord(value, axis)
            svg.append(f'<rect x="{center - bar_width * .43:.1f}" y="{min(yy, baseline):.1f}" width="{bar_width * .86:.1f}" height="{max(1, abs(yy - baseline)):.1f}" fill="{color}" rx="2"/>')
            if len(labels) <= 6:
                svg.append(f'<text class="value" x="{center:.1f}" y="{min(yy, baseline) - 7:.1f}" text-anchor="middle" style="fill:{color}">{esc(fmt(value))}</text>')
    for kind, name, values, axis, color in checked:
        if kind != 'line':
            continue
        segments, current = [], []
        for i, value in enumerate(values):
            if value is None:
                if current:
                    segments.append(current); current = []
                continue
            current.append((left + band * (i + .5), ycoord(value, axis), value))
        if current:
            segments.append(current)
        for segment in segments:
            points = ' '.join(f'{x:.1f},{y:.1f}' for x, y, _ in segment)
            if len(segment) > 1:
                svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round"/>')
            for x, y, value in segment:
                svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}"/>')
                if len(labels) <= 6:
                    value_label = fmt(value)
                    label_width = max(36, len(value_label) * 7.5 + 10)
                    svg.append(f'<rect x="{x - label_width / 2:.1f}" y="{y - 30:.1f}" width="{label_width:.1f}" height="17" fill="#fff" opacity=".94" rx="3"/>')
                    svg.append(f'<text class="value" x="{x:.1f}" y="{y - 17:.1f}" text-anchor="middle" style="fill:{color}">{esc(value_label)}</text>')
    for index, event in enumerate(events):
        xx = left + band * (labels.index(event['at']) + .5)
        svg.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{bottom}" stroke="#aa4a48" stroke-width="1.2" stroke-dasharray="5 4"/>')
        svg.append(f'<text class="event" x="{min(xx + 6, right - 8):.1f}" y="{68 + (index % 2) * 18}" text-anchor="{("end" if xx > right - 140 else "start")}">{esc(event["label"])}</text>')
    legend_x = left
    for kind, name, _, axis, color in checked:
        svg.append(f'<rect x="{legend_x}" y="20" width="12" height="12" fill="{color}" rx="2"/>')
        svg.append(f'<text x="{legend_x + 18}" y="31">{esc(name)}{("（右轴）" if axis == "right" else "")}</text>')
        legend_x += min(250, 38 + len(name) * 15 + (75 if axis == 'right' else 0))
    svg.append(f'<text class="tick" x="{left}" y="{height - 9}">{esc(spec.get("left_unit", ""))}</text>')
    if has_right:
        svg.append(f'<text class="tick" x="{right}" y="{height - 9}" text-anchor="end">{esc(spec.get("right_unit", ""))}</text>')
    svg.append('</svg>')
    note = spec.get('note', '')
    caption = f'<figcaption><strong>{esc(title)}</strong><span class="chart-meta">数据来源：{esc(source)}</span><span class="scroll-hint">左右滑动查看完整图表</span>'
    if note:
        caption += f'<span class="chart-meta">{esc(note)}</span>'
    caption += '</figcaption>'
    return '<figure class="report-chart"><div class="chart-scroll">' + ''.join(svg) + '</div>' + caption + '</figure>'
