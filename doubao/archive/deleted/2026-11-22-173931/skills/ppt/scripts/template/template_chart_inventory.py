#!/usr/bin/env python3
"""Read native PPTX chart styles without importing or rewriting the presentation.

CLI: python3 template_chart_inventory.py --pptx source.pptx --output inventory.json
API: inventory(path) -> JSON-compatible dict; summarize(result) -> compact report.

Series names are source style labels. Cached values, categories, formulas, axis
bounds and sample titles are deliberately omitted: a template is not task data.
The index describes native chart frames, including combo plots and per-point
appearance overrides. Geometry groups are candidates, not inferred semantics.
Only stdlib ZIP/XML is used. Unspecified chart style colors remain unresolved.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import math
import posixpath
import re
import statistics
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'cx': 'http://schemas.microsoft.com/office/drawing/2014/chartex',
}
DEFAULT_COLOR_MAP = {'bg1': 'lt1', 'tx1': 'dk1', 'bg2': 'lt2', 'tx2': 'dk2'}
IDENTITY = (1., 0., 0., 1., 0., 0.)
EMU_PER_INCH = 914400


def _local(node):
    return node.tag.rsplit('}', 1)[-1]


def _value(node, path, default=None):
    elem = node.find(path, NS)
    return elem.get('val', default) if elem is not None else default


def _bool(value, default=False):
    return default if value is None else str(value).lower() not in ('0', 'false', 'off')


def _relationships(z, part):
    rel_part = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    if rel_part not in z.namelist():
        return {}
    result = {}
    for rel in ET.fromstring(z.read(rel_part)):
        target = rel.get('Target', '')
        external = rel.get('TargetMode') == 'External'
        result[rel.get('Id')] = {
            'type': rel.get('Type', '').rsplit('/', 1)[-1],
            'part': target if external else posixpath.normpath(
                target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(part), target)),
            'external': external,
        }
    return result


def _related(z, part, kind):
    return next((r['part'] for r in _relationships(z, part).values()
                 if r['type'] == kind and not r['external']), None)


def _slide_order(z):
    """Relationship order, not slide filename numbering, is the presentation order."""
    rels = _relationships(z, 'ppt/presentation.xml')
    root = ET.fromstring(z.read('ppt/presentation.xml'))
    slide_ids = root.findall('p:sldIdLst/p:sldId', NS)
    if slide_ids:
        return [(s.get('id'), rels[s.get(f"{{{NS['r']}}}id")]['part']) for s in slide_ids]
    # An empty sldIdLst is authoritative (zero-slide POTX/PPTX).
    if root.find('p:sldIdLst', NS) is not None:
        return []
    return [(None, n) for n in sorted(
        (n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
        key=lambda n: int(re.search(r'slide(\d+)', n).group(1)))]


def _rgb_literal(node):
    name = _local(node)
    value = node.get('lastClr') if name == 'sysClr' else node.get('val', '')
    if name in ('srgbClr', 'sysClr') and value and re.fullmatch('[0-9a-fA-F]{6}', value):
        return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    if name == 'scrgbClr':
        # scRGB is linear light; convert to sRGB for a reusable hexadecimal color.
        def channel(v):
            v = max(0., min(1., float(v) / 100000))
            return 12.92 * v if v <= .0031308 else 1.055 * v ** (1 / 2.4) - .055
        return tuple(channel(node.get(c, '0')) for c in ('r', 'g', 'b'))
    if name == 'hslClr':
        return colorsys.hls_to_rgb(float(node.get('hue', '0')) / 21600000,
                                  float(node.get('lum', '0')) / 100000,
                                  float(node.get('sat', '0')) / 100000)
    return None


def resolve_color(node, theme=None, color_map=None, *, source='explicit', theme_part=None):
    """Resolve DrawingML RGB/theme colors and common transforms; report uncertainty."""
    theme, color_map = theme or {}, color_map or DEFAULT_COLOR_MAP
    kind = _local(node)
    raw = node.get('val') or node.get('lastClr')
    rgb = theme.get(color_map.get(raw, raw)) if kind == 'schemeClr' else _rgb_literal(node)
    transforms = [{'type': _local(t), 'value': t.get('val')} for t in node]
    unsupported = []
    opacity = 1.
    for t in node:
        name = _local(t)
        val = float(t.get('val', '0')) / 100000
        if name == 'alpha':
            opacity = val
        elif name == 'alphaMod':
            opacity *= val
        elif name == 'alphaOff':
            opacity += val
        elif rgb is None:
            continue
        elif name in ('lumMod', 'lumOff', 'lum', 'satMod', 'satOff', 'sat', 'hueMod', 'hueOff', 'hue'):
            h, l, s = colorsys.rgb_to_hls(*rgb)
            if name == 'lumMod': l *= val
            elif name == 'lumOff': l += val
            elif name == 'lum': l = val
            elif name == 'satMod': s *= val
            elif name == 'satOff': s += val
            elif name == 'sat': s = val
            elif name == 'hueMod': h *= val
            elif name == 'hueOff': h += float(t.get('val', '0')) / 21600000
            elif name == 'hue': h = float(t.get('val', '0')) / 21600000
            rgb = colorsys.hls_to_rgb(h % 1, max(0., min(1., l)), max(0., min(1., s)))
        elif name == 'tint':
            rgb = tuple(c * val + 1 - val for c in rgb)
        elif name == 'shade':
            rgb = tuple(c * val for c in rgb)
        elif name in ('red', 'green', 'blue', 'redMod', 'greenMod', 'blueMod', 'redOff', 'greenOff', 'blueOff'):
            channels = list(rgb)
            index = ('red', 'green', 'blue').index(re.sub('(Mod|Off)$', '', name))
            channels[index] = channels[index] * val if name.endswith('Mod') else channels[index] + val if name.endswith('Off') else val
            rgb = tuple(channels)
        elif name == 'comp':
            h, l, s = colorsys.rgb_to_hls(*rgb)
            rgb = colorsys.hls_to_rgb((h + .5) % 1, l, s)
        elif name == 'inv':
            rgb = tuple(1 - c for c in rgb)
        else:
            unsupported.append(name)
    result = {
        'color': ('#' + ''.join(f'{max(0, min(255, round(c * 255))):02X}' for c in rgb)) if rgb is not None and not unsupported else None,
        'source': source, 'color_kind': kind, 'raw_value': raw,
        'resolved': rgb is not None and not unsupported,
        'transforms': transforms, 'opacity': round(max(0., min(1., opacity)), 4),
    }
    if kind == 'schemeClr':
        slot = color_map.get(raw, raw)
        result.update(scheme=raw, theme_slot=slot,
                      theme_part=theme_part.get(slot) if isinstance(theme_part, dict) else theme_part)
    if unsupported:
        result['unresolved_transforms'] = unsupported
    return result


def _theme_context(z, slide_part, chart_part):
    layout = _related(z, slide_part, 'slideLayout')
    master = _related(z, layout, 'slideMaster') if layout else None
    theme_part = (_related(z, chart_part, 'theme') or _related(z, slide_part, 'theme') or
                  (_related(z, master, 'theme') if master else None))
    color_map = dict(DEFAULT_COLOR_MAP)
    for part in (master, layout, slide_part, chart_part):
        if not part or part not in z.namelist():
            continue
        root = ET.fromstring(z.read(part))
        for path in ('p:clrMap', 'p:clrMapOvr/a:overrideClrMapping', 'c:clrMapOvr'):
            elem = root.find(path, NS)
            if elem is not None:
                color_map.update(elem.attrib)
    theme, origins = {}, {}
    override_part = _related(z, chart_part, 'themeOverride')
    for part in (theme_part, override_part):
        if not part or part not in z.namelist():
            continue
        root = ET.fromstring(z.read(part))
        scheme = root.find('.//a:clrScheme', NS)
        if scheme is not None:
            for slot in scheme:
                if len(slot):
                    rgb = _rgb_literal(slot[0])
                    if rgb is not None:
                        theme[_local(slot)] = rgb
                        origins[_local(slot)] = part
    return theme, color_map, origins


def _appearance(sp, context, source):
    """Use direct visible fills/lines only; hiddenFill extensions are not effective."""
    if sp is None:
        return [], {'fill': 'inherited', 'line': 'inherited'}
    colors, states = [], {}
    for channel, parent in (('fill', sp), ('line', sp.find('a:ln', NS))):
        states[channel] = 'inherited'
        if parent is None:
            continue
        if parent.find('a:noFill', NS) is not None:
            states[channel] = 'none'
            continue
        for fill_type in ('solidFill', 'gradFill', 'pattFill'):
            fill = parent.find(f'a:{fill_type}', NS)
            if fill is None:
                continue
            states[channel] = fill_type
            for clr in fill.iter():
                if _local(clr) in ('srgbClr', 'schemeClr', 'sysClr', 'scrgbClr', 'hslClr', 'prstClr'):
                    color = resolve_color(clr, context[0], context[1], source=f'{source}.{channel}', theme_part=context[2])
                    color['channel'] = channel
                    colors.append(color)
    return colors, states


def _series(ser, chart_type, context):
    name_node = ser.find('c:tx/c:v', NS)
    if name_node is None:
        values = ser.findall('c:tx/c:strRef/c:strCache/c:pt/c:v', NS)
        name = values[0].text if values else None
    else:
        name = name_node.text
    colors, appearance = _appearance(ser.find('c:spPr', NS), context, 'series.spPr')
    marker = ser.find('c:marker', NS)
    marker_info = None
    if marker is not None:
        marker_colors, marker_appearance = _appearance(marker.find('c:spPr', NS), context, 'series.marker.spPr')
        for color in marker_colors:
            color['channel'] = 'marker_' + color['channel']
        colors.extend(marker_colors)
        marker_info = {'symbol': _value(marker, 'c:symbol'), 'size': _value(marker, 'c:size'), 'appearance': marker_appearance}
    points = []
    for point in ser.findall('c:dPt', NS):
        point_colors, point_appearance = _appearance(point.find('c:spPr', NS), context, 'point.spPr')
        point_marker = point.find('c:marker', NS)
        if point_marker is not None:
            marker_colors, _ = _appearance(point_marker.find('c:spPr', NS), context, 'point.marker.spPr')
            for color in marker_colors:
                color['channel'] = 'marker_' + color['channel']
            point_colors.extend(marker_colors)
        points.append({'index': _value(point, 'c:idx'), 'colors': point_colors, 'appearance': point_appearance})
    return {
        'index': _value(ser, 'c:idx'), 'order': _value(ser, 'c:order'),
        'name': name, 'name_role': 'source_style_label', 'chart_type': chart_type,
        'colors': colors, 'appearance': appearance, 'marker': marker_info, 'point_overrides': points,
        # Structural cardinality only: values, category labels and formulas stay omitted.
        'point_count': max((int(n.get('val', '0')) for path in ('c:val', 'c:cat', 'c:yVal', 'c:xVal')
                            for parent in ser.findall(path, NS)
                            for n in parent.findall('.//c:ptCount', NS)), default=None),
        'color_resolution': 'explicit_or_theme' if colors else 'none_or_unresolved_inherited',
    }


def _value_signature(ser):
    """Read a cache only to verify a structural relation; never return its data."""
    ref = ser.find('c:val/c:numRef', NS)
    if ref is None: return None
    formula, cache = ref.find('c:f', NS), ref.find('c:numCache', NS)
    if formula is None or not (formula.text or '').strip() or cache is None: return None
    try:
        count = int(_value(cache, 'c:ptCount', '0')); values = {}
        for point in cache.findall('c:pt', NS):
            index = int(point.get('idx')); value = point.find('c:v', NS)
            number = Decimal(value.text) if value is not None else Decimal('NaN')
            if not 0 <= index < count or index in values or not number.is_finite(): return None
            values[index] = number
        if not count or not values: return None
        return formula.text.strip(), count, values
    except (ValueError, TypeError, InvalidOperation): return None


def _labels_off(ser, plot):
    own, inherited = ser.find('c:dLbls', NS), plot.find('c:dLbls', NS)
    for labels in (own, inherited):
        if labels is not None and (labels.find('c:dLbl', NS) is not None or labels.find('.//c:tx', NS) is not None): return False
    for key in ('showVal','showCatName','showSerName','showPercent','showLegendKey','showBubbleSize'):
        fallback = _value(inherited, 'c:'+key, '0') if inherited is not None else '0'
        if _bool(_value(own, 'c:'+key, fallback) if own is not None else fallback): return False
    return True


def _verified_hidden_duplicates(entries, series, root):
    """Only same-axis area + wholly invisible duplicate line, not range helpers."""
    blank_mode = _value(root, 'c:chart/c:dispBlanksAs')
    for index, (raw, plot, ser) in enumerate(entries):
        if (raw != 'lineChart' or _value(ser, 'c:marker/c:symbol') != 'none' or
                ser.find('c:spPr/a:ln/a:noFill', NS) is None or ser.find('.//c:errBars', NS) is not None or
                ser.find('.//c:trendline', NS) is not None or ser.find('c:dPt', NS) is not None or not _labels_off(ser, plot)):
            continue
        signature = _value_signature(ser)
        if signature is None: continue
        for target_index, (target_raw, target_plot, target) in enumerate(entries):
            if (target_raw != 'areaChart' or _value(target_plot, 'c:grouping') != 'standard' or
                    _value(plot, 'c:grouping') != 'standard' or
                    [a.get('val') for a in plot.findall('c:axId', NS)] != [a.get('val') for a in target_plot.findall('c:axId', NS)] or
                    target.find('.//c:errBars', NS) is not None or not _labels_off(target, target_plot) or
                    _value_signature(target) != signature):
                continue
            _, count, values = signature
            series[index].update(hidden_duplicate=True, helper_of=target_index,
                                 source_point_layout={'point_count':count, 'nonempty_positions':sorted(values),
                                                      'missing_positions':[n for n in range(count) if n not in values],
                                                      'blank_mode':blank_mode})
            break


def parse_chart(root, context=(None, None, None)):
    """Pure chart-style extraction; excludes all numerical source data and formulas."""
    plot = root.find('c:chart/c:plotArea', NS)
    if plot is None:
        return {'types': [], 'plot_types': [], 'series': [], 'axes': [], 'legend': {'present': False},
                'palette': [], 'unsupported_chart_schema': True}
    types, plots, series, axes, entries = [], [], [], [], []
    for elem in plot:
        tag = _local(elem)
        if elem.tag.startswith(f"{{{NS['c']}}}") and tag.endswith('Chart'):
            if tag not in types:
                types.append(tag)
            plots.append({'type': tag, 'grouping': _value(elem, 'c:grouping'),
                          'bar_direction': _value(elem, 'c:barDir'), 'scatter_style': _value(elem, 'c:scatterStyle'),
                          'gap_width': _value(elem, 'c:gapWidth'), 'overlap': _value(elem, 'c:overlap'),
                          'hole_size': _value(elem, 'c:holeSize'), 'first_slice_angle': _value(elem, 'c:firstSliceAng'),
                          'smooth': _bool(_value(elem, 'c:smooth')),
                          'vary_colors': _bool(_value(elem, 'c:varyColors')),
                          'axis_ids': [v.get('val') for v in elem.findall('c:axId', NS)]})
            for s in elem.findall('c:ser', NS):
                series.append(_series(s, tag, context)); entries.append((tag, elem, s))
        elif tag in ('catAx', 'valAx', 'dateAx', 'serAx'):
            fmt = elem.find('c:numFmt', NS)
            axes.append({'type': tag, 'axis_id': _value(elem, 'c:axId'),
                         'position': _value(elem, 'c:axPos'), 'deleted': _bool(_value(elem, 'c:delete')),
                         'cross_axis_id': _value(elem, 'c:crossAx'), 'orientation': _value(elem, 'c:scaling/c:orientation'),
                         'tick_label_position': _value(elem, 'c:tickLblPos'),
                         'major_tick_mark': _value(elem, 'c:majorTickMark'), 'minor_tick_mark': _value(elem, 'c:minorTickMark'),
                         'number_format': fmt.get('formatCode') if fmt is not None else None,
                         'major_gridlines': elem.find('c:majorGridlines', NS) is not None,
                         'minor_gridlines': elem.find('c:minorGridlines', NS) is not None})
    _verified_hidden_duplicates(entries, series, root)
    legend = root.find('c:chart/c:legend', NS)
    legend_info = {'present': legend is not None}
    if legend is not None:
        legend_info.update(position=_value(legend, 'c:legendPos'), overlay=_bool(_value(legend, 'c:overlay')),
                           hidden_series_indices=[_value(e, 'c:idx') for e in legend.findall('c:legendEntry', NS)
                                                  if _bool(_value(e, 'c:delete'))])
    palette = []
    for s in series:
        for color in s['colors'] + [c for p in s['point_overrides'] for c in p['colors']]:
            if color['resolved'] and color['opacity'] > 0 and color['color'] not in palette:
                palette.append(color['color'])
    return {'types': types, 'plot_types': plots, 'series': series, 'axes': axes, 'legend': legend_info,
            'palette': palette, 'style_id': _value(root, 'c:style')}


def _multiply(a, b):
    aa, ab, ac, ad, ae, af = a
    ba, bb, bc, bd, be, bf = b
    return (aa * ba + ac * bb, ab * ba + ad * bb, aa * bc + ac * bd,
            ab * bc + ad * bd, aa * be + ac * bf + ae, ab * be + ad * bf + af)


def _rotation(xfrm, x, y, w, h):
    theta = math.radians(float(xfrm.get('rot', '0')) / 60000)
    fx = -1. if _bool(xfrm.get('flipH')) else 1.
    fy = -1. if _bool(xfrm.get('flipV')) else 1.
    co, si = math.cos(theta), math.sin(theta)
    cx, cy = x + w / 2, y + h / 2
    rotate = (co * fx, si * fx, -si * fy, co * fy, 0., 0.)
    return _multiply((1., 0., 0., 1., cx, cy), _multiply(rotate, (1., 0., 0., 1., -cx, -cy)))


def _xfrm_values(xfrm):
    off, ext = xfrm.find('a:off', NS), xfrm.find('a:ext', NS)
    return (float(off.get('x', 0)), float(off.get('y', 0)), float(ext.get('cx', 0)), float(ext.get('cy', 0))) if off is not None and ext is not None else (0., 0., 0., 0.)


def _bbox(xfrm, parent):
    if xfrm is None:
        return None
    x, y, w, h = _xfrm_values(xfrm)
    a, b, c, d, e, f = _multiply(parent, _rotation(xfrm, x, y, w, h))
    points = [(a * px + c * py + e, b * px + d * py + f) for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h))]
    xs, ys = zip(*points)
    return {'left': round(min(xs)), 'top': round(min(ys)), 'width': round(max(xs) - min(xs)), 'height': round(max(ys) - min(ys))}


def _inch(box):
    return {k: round(v / EMU_PER_INCH, 4) for k, v in box.items()} if box else None


def _frames(tree, parent=IDENTITY, group_ids=()):
    if tree is None:
        return
    for elem in tree:
        if _local(elem) == 'grpSp':
            xfrm = elem.find('p:grpSpPr/a:xfrm', NS)
            transform = parent
            if xfrm is not None:
                x, y, w, h = _xfrm_values(xfrm)
                off, ext = xfrm.find('a:chOff', NS), xfrm.find('a:chExt', NS)
                ox, oy = (float(off.get('x', 0)), float(off.get('y', 0))) if off is not None else (0., 0.)
                cw, ch = (float(ext.get('cx', 0)), float(ext.get('cy', 0))) if ext is not None else (w, h)
                sx, sy = w / cw if cw else 1., h / ch if ch else 1.
                transform = _multiply(parent, _multiply(_rotation(xfrm, x, y, w, h), (sx, 0., 0., sy, x - ox * sx, y - oy * sy)))
            cnv = elem.find('p:nvGrpSpPr/p:cNvPr', NS)
            ids = group_ids + ((cnv.get('id'),) if cnv is not None else ())
            yield from _frames(elem, transform, ids)
        elif _local(elem) == 'graphicFrame':
            cnv = elem.find('p:nvGraphicFramePr/p:cNvPr', NS)
            seen = set()
            for chart in elem.iter():
                if chart.tag not in (f"{{{NS['c']}}}chart", f"{{{NS['cx']}}}chart"):
                    continue
                rid = chart.get(f"{{{NS['r']}}}id")
                if rid in seen:
                    continue
                seen.add(rid)
                yield {'element_id': cnv.get('id') if cnv is not None else None,
                       'element_name': cnv.get('name') if cnv is not None else None,
                       'element_hidden': _bool(cnv.get('hidden')) if cnv is not None else False,
                       'relationship_id': rid, 'parent_group_ids': list(group_ids),
                       'bbox_emu': _bbox(elem.find('p:xfrm', NS), parent)}
        elif _local(elem) in ('AlternateContent', 'Choice', 'Fallback'):
            # Some producers wrap native frames themselves in markup compatibility.
            yield from _frames(elem, parent, group_ids)


def small_multiple_groups(charts, slide_num):
    """Pure conservative same-type/aligned/proximate geometry grouping."""
    eligible = [c for c in charts if c.get('types') and c.get('bbox_emu') and
                c['bbox_emu']['width'] > 0 and c['bbox_emu']['height'] > 0 and not c.get('element_hidden')]
    groups, visited = [], set()
    def neighbors(a, b):
        if a['types'] != b['types']:
            return False
        x, y = a['bbox_emu'], b['bbox_emu']
        if any(min(x[k], y[k]) / max(x[k], y[k]) < .7 for k in ('width', 'height')):
            return False
        dx, dy = abs(x['left'] - y['left']), abs(x['top'] - y['top'])
        return ((dy <= .2 * max(x['height'], y['height']) and dx <= 1.8 * max(x['width'], y['width'])) or
                (dx <= .2 * max(x['width'], y['width']) and dy <= 1.8 * max(x['height'], y['height'])))
    for i in range(len(eligible)):
        if i in visited:
            continue
        component, pending = [], [i]
        visited.add(i)
        while pending:
            n = pending.pop()
            component.append(eligible[n])
            for j in range(len(eligible)):
                if j not in visited and neighbors(eligible[n], eligible[j]):
                    visited.add(j); pending.append(j)
        if len(component) < 2:
            continue
        def bands(key, size):
            tolerance = .2 * statistics.median(c['bbox_emu'][size] for c in component)
            centers = []
            for v in sorted(c['bbox_emu'][key] for c in component):
                if not centers or v - centers[-1] > tolerance:
                    centers.append(v)
            return centers
        rows, cols = bands('top', 'height'), bands('left', 'width')
        left = min(c['bbox_emu']['left'] for c in component)
        top = min(c['bbox_emu']['top'] for c in component)
        box = {'left': left, 'top': top,
               'width': max(c['bbox_emu']['left'] + c['bbox_emu']['width'] for c in component) - left,
               'height': max(c['bbox_emu']['top'] + c['bbox_emu']['height'] for c in component) - top}
        members = []
        for c in sorted(component, key=lambda c: (c['bbox_emu']['top'], c['bbox_emu']['left'])):
            members.append({'chart_id': c['chart_id'], 'element_id': c['element_id'],
                            'row': min(range(len(rows)), key=lambda i: abs(rows[i] - c['bbox_emu']['top'])) + 1,
                            'column': min(range(len(cols)), key=lambda i: abs(cols[i] - c['bbox_emu']['left'])) + 1,
                            'bbox_inch': c['bbox_inch']})
        members.sort(key=lambda member: (member['row'], member['column']))
        groups.append({'group_id': f'slide-{slide_num:02d}-charts-{len(groups) + 1}',
                       'candidate_only': True, 'basis': 'same_native_types_similar_size_aligned_nearby',
                       'types': component[0]['types'], 'rows': len(rows), 'columns': len(cols),
                       'bbox_inch': _inch(box), 'members': members})
    return groups


def inventory(pptx_path):
    """Read-only native chart inventory, including unresolved/damaged frame references."""
    slides, warnings = [], []
    with zipfile.ZipFile(pptx_path) as z:
        chart_parts = set()
        for name in z.namelist():
            if not re.fullmatch(r'ppt/charts/[^/]+\.xml', name):
                continue
            try:
                is_chart = _local(ET.fromstring(z.read(name))) == 'chartSpace'
            except ET.ParseError:
                # A damaged named chart is still a source part, not an absent chart.
                is_chart = bool(re.fullmatch(r'ppt/charts/chart(?:Ex)?\d+\.xml', name))
            if is_chart:
                chart_parts.add(name)
        for number, (page_id, part) in enumerate(_slide_order(z), 1):
            charts = []
            root = ET.fromstring(z.read(part))
            rels = _relationships(z, part)
            seen = set()
            for frame in _frames(root.find('p:cSld/p:spTree', NS)):
                rid = frame['relationship_id']
                key = (frame['element_id'], rid)
                if key in seen:
                    continue
                seen.add(key)
                rel = rels.get(rid, {})
                chart_part = rel.get('part')
                frame.update(source_slide_num=number, source_page_id=page_id, source_slide_part=part,
                             chart_part=chart_part, chart_part_id=Path(chart_part).stem if chart_part else None,
                             chart_id=f"slide-{number:02d}:element-{frame['element_id']}:{rid}",
                             bbox_inch=_inch(frame['bbox_emu']))
                try:
                    if rel.get('external') or not chart_part:
                        raise ValueError('missing or external chart relationship')
                    chart_root = ET.fromstring(z.read(chart_part))
                    frame.update(parse_chart(chart_root, _theme_context(z, part, chart_part)))
                    if frame.get('unsupported_chart_schema'):
                        warnings.append({'chart_id': frame['chart_id'], 'chart_part': chart_part, 'error': 'unsupported chart schema; inspect source native chart'})
                    frame['parsed'] = not frame.get('unsupported_chart_schema', False)
                except (KeyError, ValueError, ET.ParseError) as exc:
                    frame.update(types=[], plot_types=[], series=[], axes=[], legend={'present': None}, palette=[], parsed=False)
                    warnings.append({'chart_id': frame['chart_id'], 'chart_part': chart_part, 'error': str(exc)})
                charts.append(frame)
            slides.append({'slide_num': number, 'source_page_id': page_id, 'source_slide_part': part,
                           'chart_count': len(charts), 'charts': charts,
                           'small_multiple_groups': small_multiple_groups(charts, number)})
    return {'ok': True, 'schema_version': 1, 'source_pptx': str(Path(pptx_path).resolve()),
            'data_policy': {'sample_values_included': False, 'series_names_role': 'source_style_labels',
                            'omitted': ['category_labels', 'cached_values', 'formulas', 'axis_bounds', 'sample_titles'],
                            'reuse_instruction': 'Reuse source chart types, colors and geometry; replace all data and labels with current task inputs.'},
            'total_slides': len(slides), 'total_charts': sum(s['chart_count'] for s in slides),
            'parsed_chart_count': sum(c['parsed'] for s in slides for c in s['charts']),
            'chart_part_count': len(chart_parts), 'unreferenced_chart_parts': sorted(chart_parts - {c['chart_part'] for s in slides for c in s['charts']}),
            'warnings': warnings, 'slides': slides}


def summarize(result):
    """Compact discoverable report; detailed series/point metadata stays in the file."""
    types, palette = Counter(), Counter()
    for slide in result['slides']:
        for chart in slide['charts']:
            types.update(chart['types']); palette.update(chart['palette'])
    return {'ok': result['ok'], 'total_slides': result['total_slides'], 'total_charts': result['total_charts'],
            'parsed_chart_count': result['parsed_chart_count'], 'chart_part_count': result['chart_part_count'],
            'chart_counts_by_slide': [s['chart_count'] for s in result['slides']], 'types': dict(types),
            'palette': [{'color': color, 'chart_count': count} for color, count in palette.most_common()],
            'small_multiple_groups': [{'slide_num': s['slide_num'], 'group_id': g['group_id'],
                                       'rows': g['rows'], 'columns': g['columns'], 'chart_count': len(g['members'])}
                                      for s in result['slides'] for g in s['small_multiple_groups']],
            'warning_count': len(result['warnings'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pptx', required=True)
    parser.add_argument('--output', required=True, help='Full native chart inventory JSON path')
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    source = Path(args.pptx).resolve()
    if source == output:
        print(json.dumps({'ok': False, 'error': 'output must not overwrite source PPTX'}))
        return 2
    try:
        result = inventory(source)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    except (OSError, zipfile.BadZipFile, KeyError, ValueError, ET.ParseError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(dict(summarize(result), output_path=str(output)), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
