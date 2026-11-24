#!/usr/bin/env python3
"""Source-native chart fragments and a single-page preflight (stdlib only).

build_chart(inventory, chart_id, new_data, series_map=[...], bbox=..., adaptation_reason=...)
build_group(inventory, group_id, panels=[{'data': ..., 'series_map': [...]}], value_axis=..., ...)
build_table(inventory, table_data, bbox=...)
validate_chart_contract(one_slide_xml, contract, inventory=..., bindings=...)

Results contain `xml` (native SML fragments), `contract` and external `bindings`.
No remote writes, source-cache reads or cross-page style/diversity counters.
Mapping positions refer to inventory.series; point indices refer to OOXML (0-based).
Changing series/point roles or group cardinality requires a recorded reason.
Source chart IDs and new task values are separate contract fields. Unsupported
source types/range encodings are reported honestly, never silently substituted.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import re
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

SML = 'https://www.larkoffice.com/sml/2.0'
ALTERNATIVES = ['column', 'bar', 'line', 'area', 'pie', 'native_table']
BBOX_KEYS = ('left', 'top', 'width', 'height')
SML_BBOX = ('topLeftX', 'topLeftY', 'width', 'height')
TYPE_MAP = {'lineChart': 'line', 'areaChart': 'area', 'pieChart': 'pie', 'doughnutChart': 'pie'}


class ChartContractError(ValueError):
    def __init__(self, code, message, alternatives=None):
        super().__init__(message)
        self.code = code
        self.alternatives = list(alternatives or [])

    def as_dict(self):
        return {'code': self.code, 'message': str(self), 'alternatives': self.alternatives}


def _fail(code, message, alternatives=None):
    raise ChartContractError(code, message, alternatives)


def _local(node):
    return node.tag.rsplit('}', 1)[-1]


def _child(node, name):
    return next((n for n in node if _local(n) == name), None) if node is not None else None


def _children(node, name):
    return [n for n in node if _local(n) == name] if node is not None else []


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _number(value):
    if isinstance(value, bool):
        _fail('invalid_new_data', 'Boolean is not a chart number')
    try:
        number = float(value)
    except (TypeError, ValueError):
        _fail('invalid_new_data', f'Chart data must be numeric: {value!r}')
    if not math.isfinite(number):
        _fail('invalid_new_data', 'Chart data must be finite')
    return int(number) if number.is_integer() else number


def _fmt(value):
    return str(_number(value))


def _bbox(value):
    if not isinstance(value, dict) or set(BBOX_KEYS) - value.keys():
        _fail('invalid_bbox', 'bbox requires left/top/width/height')
    box = {k: _number(value[k]) for k in BBOX_KEYS}
    if box['width'] <= 0 or box['height'] <= 0 or box['left'] < 0 or box['top'] < 0:
        _fail('invalid_bbox', 'Chart bbox must have positive size and nonnegative position')
    return box


def _source_bbox(source):
    box = source.get('bbox_inch')
    if not box:
        _fail('missing_source_geometry', 'Selected source has no chart/group bbox; supply a target bbox')
    return _bbox({k: float(box[k])*72 for k in BBOX_KEYS})


def _chart(inventory, chart_id):
    matches = [c for s in inventory.get('slides', []) for c in s.get('charts', []) if c.get('chart_id') == chart_id]
    if len(matches) != 1:
        _fail('source_chart_not_found', f'Expected one real source chart ID: {chart_id}')
    source = matches[0]
    if not source.get('parsed', True):
        _fail('unparsed_source_chart', 'Source chart was not parsed; recover the source inventory before building', ALTERNATIVES)
    return source


def _group(inventory, group_id):
    matches = [g for s in inventory.get('slides', []) for g in s.get('small_multiple_groups', []) if g.get('group_id') == group_id]
    if len(matches) != 1:
        _fail('source_group_not_found', f'Expected one real source group ID: {group_id}')
    return matches[0]


def _visible_format(value):
    if not isinstance(value, str) or not value.strip() or not value.replace(';', '').strip():
        _fail('invalid_new_data', 'Readability number format must display values, not an empty/hidden ;;; format')
    return value


def _visible_color(value):
    paint = _paint_value(value)
    if not isinstance(paint, tuple) or len(paint) != 4 or not all(0 <= c <= 255 for c in paint[:3]) or not 0 < paint[3] <= 1:
        _fail('invalid_new_data', 'Explicit label/legend colors need visible SML RGB/RGBA paint')
    return value


def _value_axis(value, *, group=False):
    if not isinstance(value, dict) or set(value)-{'min', 'max', 'shared', 'include_zero', 'format', 'label_color'}:
        _fail('invalid_value_axis', 'value_axis accepts min/max, shared, include_zero, format and label_color')
    axis = copy.deepcopy(value)
    for key in ('shared', 'include_zero'):
        if key in axis and not isinstance(axis[key], bool):
            _fail('invalid_value_axis', f'{key} must be a boolean')
    if group:
        if axis.get('shared', True) is not True:
            _fail('invalid_value_axis', 'Group value_axis describes a shared scale')
        axis['shared'] = True
    elif 'shared' in axis:
        _fail('invalid_value_axis', 'shared is a group setting; chart data needs explicit min/max')
    if not group and not {'min', 'max'} <= axis.keys():
        _fail('invalid_value_axis', 'One chart value_axis needs explicit min and max')
    for key in ('min', 'max'):
        if key in axis:
            axis[key] = _number(axis[key])
            if not isinstance(axis[key], int):
                _fail('unsupported_operator_axis_bounds', 'Native SML min/max require integers; choose outward integer bounds without changing the data', ALTERNATIVES)
    if 'min' in axis and 'max' in axis and axis['min'] >= axis['max']:
        _fail('invalid_value_axis', 'min must be less than max')
    if 'format' in axis: axis['format'] = _visible_format(axis['format'])
    if 'label_color' in axis: axis['label_color'] = _visible_color(axis['label_color'])
    return axis


def _data_labels(value):
    allowed = {'value', 'category', 'series', 'percentage', 'position', 'format', 'font_size', 'color', 'separator'}
    if not isinstance(value, dict) or set(value)-allowed:
        _fail('invalid_new_data', 'data_labels needs explicit SML label settings')
    labels = {'value': True, 'category': False, 'series': False, 'percentage': False, **copy.deepcopy(value)}
    for key in ('value', 'category', 'series', 'percentage'):
        if not isinstance(labels[key], bool): _fail('invalid_new_data', f'data_labels.{key} must be a boolean')
    if not any(labels[k] for k in ('value', 'category', 'percentage')):
        _fail('invalid_new_data', 'Data labels must show value, category or percentage')
    if 'position' in labels and labels['position'] not in ('auto', 'top', 'bottom', 'left', 'right', 'center', 'inside', 'outside'):
        _fail('invalid_new_data', 'Unsupported data label position')
    if 'format' in labels: labels['format'] = _visible_format(labels['format'])
    if 'font_size' in labels:
        labels['font_size'] = _number(labels['font_size'])
        if not 1 <= labels['font_size'] <= 4000: _fail('invalid_new_data', 'Label font_size must be in SML range 1..4000')
    if 'color' in labels:
        labels['color'] = _visible_color(labels['color'])
    if 'separator' in labels and not isinstance(labels['separator'], str): _fail('invalid_new_data', 'Label separator must be text')
    return labels


def _label_attrs(labels, data, kind, groups, value_axis=None, *, series_level=False):
    if not labels: return None
    if labels.get('series') and kind not in ('column', 'bar'):
        _fail('unsupported_operator_series_labels', 'Native series-name labels are supported for bar/column plots; use an explicit legend for other types', ALTERNATIVES)
    position = 'inside' if groups and kind in ('column','bar') else 'auto' if kind in ('combo','line','area') else 'outside'
    position = labels.get('position', position)
    if series_level:
        allowed = (('auto',) if kind in ('line','area') else ('inside','outside') if kind == 'pie'
                   else ('inside','center','top','bottom') if groups else ('outside','inside','center','top','bottom'))
        if position not in allowed:
            _fail('unsupported_operator_label_position', f'Native {kind} series labels support {", ".join(allowed)}; choose the source plot appropriate position', ALTERNATIVES)
    attrs = {'position': position, 'fontSize': _fmt(labels.get('font_size', 10)),
             'color': labels.get('color', 'rgb(31,35,41)'),
             **{k: str(labels[k]).lower() for k in ('value', 'category', 'series', 'percentage')}}
    attrs['format'] = labels.get('format', data.get('value_format', value_axis['format'] if value_axis else 'General'))
    if 'separator' in labels: attrs['separator'] = labels['separator']
    return attrs


def _new_data(data):
    if not isinstance(data, dict):
        _fail('invalid_new_data', 'new_data must be an explicit object')
    categories, series = data.get('categories'), data.get('series')
    if not isinstance(categories, list) or not categories or not all(isinstance(c, str) and c.strip() for c in categories):
        _fail('invalid_new_data', 'Provide nonempty string categories')
    if not isinstance(series, list) or not series:
        _fail('invalid_new_data', 'Provide explicit new data series')
    out = []
    for s in series:
        if not isinstance(s, dict) or not isinstance(s.get('name'), str) or not s['name'].strip():
            _fail('invalid_new_data', 'Each new data series needs its own name')
        values = s.get('values')
        if not isinstance(values, list) or len(values) != len(categories):
            _fail('invalid_new_data', 'Series values must match category count')
        record = {'name': s['name'], 'values': [_number(v) for v in values]}
        if 'data_labels' in s:
            record['data_labels'] = False if s['data_labels'] is False else _data_labels(s['data_labels'])
        if 'hidden_duplicate' in s or 'helper_of' in s:
            target = s.get('helper_of')
            if s.get('hidden_duplicate') is not True or not isinstance(target, int) or isinstance(target, bool) or target < 0:
                _fail('invalid_new_data', 'Hidden duplicate needs hidden_duplicate=true and a 0-based new-series helper_of')
            record.update(hidden_duplicate=True, helper_of=target)
        out.append(record)
    if len({s['name'] for s in out}) != len(out):
        _fail('invalid_new_data', 'New series names must be distinct')
    result = {'categories': list(categories), 'category_name': data.get('category_name', '类别'),
              'series': out, 'kind': data.get('kind', 'categorical')}
    if not isinstance(result['category_name'],str) or not result['category_name'].strip():
        _fail('invalid_new_data','New category field needs a nonempty name')
    if data.get('title') is not None:
        if not isinstance(data['title'], str): _fail('invalid_new_data', 'Title must be text from the new task')
        result['title'] = data['title']
    if 'value_format' in data:
        result['value_format']=_visible_format(data['value_format'])
    if 'value_axis' in data: result['value_axis'] = _value_axis(data['value_axis'])
    if 'data_labels' in data: result['data_labels'] = _data_labels(data['data_labels'])
    if 'source_gap_policy' in data:
        if data['source_gap_policy'] not in ('continuous_new_data', 'preserve'):
            _fail('invalid_new_data', 'source_gap_policy must explicitly choose continuous_new_data or preserve')
        result['source_gap_policy'] = data['source_gap_policy']
    if 'legend' in data:
        legend=data['legend']
        if (not isinstance(legend,dict) or set(legend)-{'present','position','color'} or
                not isinstance(legend.get('present'),bool) or
                legend['present'] and legend.get('position') not in ('top','bottom','left','right')):
            _fail('invalid_new_data','Legend adaptation needs present and a valid SML position')
        if 'color' in legend: _visible_color(legend['color'])
        result['legend']=copy.deepcopy(legend)
    return result


def _resolve_value_axis(request, sources_and_data):
    """Resolve only supplied NEW values; source contributes plot/stack semantics."""
    bounds, zero_default, formats = [], False, set()
    for source, data in sources_and_data:
        _, kinds = _source_types(source)
        if len(kinds) != 1 or kinds[0] == 'pie':
            _fail('unsupported_shared_value_axis', 'Explicit/common value axes require one categorical Cartesian plot; combo axes and pies need an operator adapter', ALTERNATIVES)
        if not any(a.get('type') == 'valAx' for a in source.get('axes', [])):
            _fail('unsupported_operator_axis', 'Source has no resolved value-axis metadata; explicit bounds cannot be silently omitted', ALTERNATIVES)
        plot = source['plot_types'][0]
        if plot.get('grouping') == 'percentStacked':
            _fail('unsupported_shared_value_axis', 'Percentage stacks use a normalized domain; an explicit operator domain adapter is required', ALTERNATIVES)
        zero_default |= kinds[0] in ('column', 'bar', 'area')
        if plot.get('grouping') == 'stacked':
            for values in zip(*(s['values'] for s in data['series'])):
                bounds.extend((sum(v for v in values if v < 0), sum(v for v in values if v > 0)))
        else: bounds.extend(v for s in data['series'] for v in s['values'])
        for format_value in (data.get('value_format'), data.get('data_labels', {}).get('format'), data.get('value_axis', {}).get('format')):
            if format_value is not None: formats.add(format_value)
    if request.get('format') is not None: formats.add(request['format'])
    if len(formats) > 1: _fail('shared_value_format_mismatch', 'A shared metric axis needs one consistent explicit value/label format')
    include_zero = request.get('include_zero', zero_default)
    if include_zero: bounds.append(0)
    low, high = min(bounds), max(bounds)
    minimum, maximum = request.get('min', math.floor(low)), request.get('max', math.ceil(high))
    if minimum == maximum:
        if 'min' not in request and minimum < 0: minimum -= 1
        elif 'max' not in request: maximum += 1
        elif 'min' not in request: minimum -= 1
    if minimum >= maximum or minimum > low or maximum < high:
        _fail('value_axis_clips_new_data', 'Axis bounds must contain every NEW value/stack extent and the requested zero baseline')
    result = {'min': minimum, 'max': maximum, 'include_zero': include_zero, 'format': next(iter(formats), 'General')}
    if 'label_color' in request: result['label_color'] = request['label_color']
    return result


def _mapping(source, series_map, count, categories, reason):
    if not isinstance(series_map, list) or len(series_map) != count:
        _fail('source_series_mapping_required', 'Provide explicit series_map for every new series')
    mappings = []
    changed = count != len(source.get('series', []))
    for entry in series_map:
        entry = {'series': entry} if isinstance(entry, int) and not isinstance(entry, bool) else copy.deepcopy(entry)
        if not isinstance(entry, dict) or set(entry) - {'series', 'color_point', 'point_map'}:
            _fail('invalid_source_series_mapping', 'Mapping accepts series, color_point or point_map')
        index = entry.get('series')
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(source.get('series', [])):
            _fail('invalid_source_series_mapping', 'series must select a real source inventory series position')
        s = source['series'][index]
        if 'color_point' in entry and 'point_map' in entry:
            _fail('invalid_source_series_mapping', 'Select a uniform source point color or a point_map, not both')
        if 'color_point' in entry:
            _point_color(s, entry['color_point']); changed = True
        if 'point_map' in entry:
            points = entry['point_map']
            if not isinstance(points, list) or len(points) != categories:
                _fail('invalid_source_point_mapping', 'point_map must cover every new category')
            for point in points:
                if point is not None: _point_color(s, point)
            changed = True
        elif s.get('point_overrides') and 'color_point' not in entry:
            source_count = s.get('point_count') or max(int(p['index'])+1 for p in s['point_overrides'])
            if source_count != categories:
                _fail('source_point_mapping_required', 'Changed category roles require explicit point_map or color_point plus a reason')
        mappings.append(entry)
    if changed and not (isinstance(reason, str) and reason.strip()):
        _fail('adaptation_reason_required', 'Changed series or source point roles require an adaptation reason')
    return mappings


def _resolved_color(colors, channel):
    return next((c for c in colors if c.get('channel') == channel and c.get('resolved') and c.get('color') and c.get('opacity', 1) > 0), None)


def _paint(record):
    if record is None:
        _fail('unresolved_source_color', 'Selected source data color is unresolved; select another explicit source series/point color', ALTERNATIVES)
    match = re.fullmatch(r'#([0-9A-Fa-f]{6})', record.get('color', ''))
    if not match:
        _fail('unresolved_source_color', 'Source color is not a resolved six-digit RGB value')
    raw = match.group(1); rgb = [int(raw[i:i+2], 16) for i in (0, 2, 4)]
    alpha = float(record.get('opacity', 1))
    return f'rgb({rgb[0]},{rgb[1]},{rgb[2]})' if alpha == 1 else f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha:g})'


def _point_color(series, index):
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        _fail('invalid_source_point_mapping', 'Source point index must be a nonnegative integer')
    points = [p for p in series.get('point_overrides', []) if str(p.get('index')) == str(index)]
    if len(points) != 1:
        _fail('invalid_source_point_mapping', f'No explicit source point color at index {index}')
    point = points[0]
    record = _resolved_color(point.get('colors', []), 'fill') or _resolved_color(point.get('colors', []), 'marker_fill')
    if record is None:
        _fail('unresolved_source_color', f'Source point {index} has no visible resolved fill color')
    return record


def _kind(source, raw):
    if raw == 'barChart':
        plot = next((p for p in source.get('plot_types', []) if p.get('type') == raw), {})
        direction = plot.get('bar_direction')
        if direction not in ('col', 'bar'):
            _fail('unsupported_source_configuration', 'Source bar direction is unresolved; inspect source', ALTERNATIVES)
        return 'column' if direction == 'col' else 'bar'
    if raw not in TYPE_MAP:
        _fail('unsupported_source_type', f'Unsupported source type {raw}; operator capability is bounded, not source quality', ALTERNATIVES)
    return TYPE_MAP[raw]


def _source_identity(source):
    return {k: source.get(k) for k in ('chart_id', 'source_slide_num', 'source_page_id', 'source_slide_part', 'element_id', 'chart_part', 'chart_part_id')}


def _csv(values):
    stream = io.StringIO(); csv.writer(stream, lineterminator='').writerow(values)
    return stream.getvalue()


def _source_types(source):
    raw_types = source.get('types', [])
    if not raw_types:
        _fail('unsupported_source_type', 'Source type is unresolved', ALTERNATIVES)
    if any('scatter' in t.lower() for t in raw_types):
        _fail('unsupported_source_type', 'Source scatter/range combo needs explicit x/y conditions and an operator adapter; this categorical builder does not guess', ALTERNATIVES)
    kinds = [_kind(source, t) for t in raw_types]
    plot_types=[p.get('type') for p in source.get('plot_types',[])]
    if len(plot_types)!=len(set(plot_types)):
        _fail('unsupported_source_configuration','Multiple source plots of the same type need an explicit plot/axis adapter',ALTERNATIVES)
    if any(p.get('type')=='barChart' and p.get('grouping') in ('stacked','percentStacked') for p in source.get('plot_types',[])):
        if any(s.get('chart_type')=='barChart' and (s.get('appearance',{}).get('fill')=='none' or
                any(p.get('appearance',{}).get('fill')=='none' for p in s.get('point_overrides',[])))
                for s in source.get('series',[])):
            _fail('unsupported_source_range','Source stacked columns have explicit hidden baselines/points and may encode floating ranges; an operator range adapter is required, not a guessed ordinary bar',ALTERNATIVES)
    return raw_types,kinds


def _hidden_duplicate(source, data, mapping, index):
    """A verified invisible duplicate may mirror NEW area data, never hide a metric."""
    record = source['series'][mapping[index]['series']]; new = data['series'][index]
    if (record.get('hidden_duplicate') is not True or record.get('chart_type') != 'lineChart' or
            record.get('appearance', {}).get('line') != 'none' or (record.get('marker') or {}).get('symbol') != 'none'):
        _fail('unsupported_source_range', 'NoStroke is allowed only for an inventory-verified invisible duplicate; range/error-bar/scaffold helpers still need an adapter', ALTERNATIVES)
    target = new['helper_of']; source_target = record.get('helper_of')
    if (target == index or not 0 <= target < len(data['series']) or not isinstance(source_target, int) or
            not 0 <= source_target < len(source['series']) or mapping[target]['series'] != source_target or
            source['series'][source_target]['chart_type'] != 'areaChart' or data['series'][target].get('hidden_duplicate') or
            new['values'] != data['series'][target]['values']):
        _fail('hidden_duplicate_data_mismatch', 'helper_of must bind the matching visible source area and exactly duplicate its supplied NEW values')
    if set(mapping[index]) != {'series'} or new.get('data_labels', False) is not False:
        _fail('hidden_duplicate_visibility_mismatch', 'An invisible duplicate cannot acquire point colors or visible data labels')
    if data.get('legend', source.get('legend', {})).get('present'):
        _fail('unsupported_operator_legend', 'SML cannot omit only the hidden helper legend entry; use legend.present=false and identify the visible area through its title/categories')
    if record.get('source_point_layout', {}).get('missing_positions') and data.get('source_gap_policy') != 'continuous_new_data':
        _fail('unsupported_operator_gaps', 'Source segmented gaps are not implemented; continuous NEW data needs source_gap_policy=continuous_new_data and a reason for changing that category/segment role', ALTERNATIVES)
    return True


def _node(source, data, mapping, box, reason=None):
    raw_types,kinds=_source_types(source)
    combo = len(kinds) > 1
    if not combo and data.get('kind') != 'categorical':
        _fail('unsupported_data_semantics','Range/scatter data cannot be hard-set as an ordinary categorical chart',ALTERNATIVES)
    if combo and (data.get('kind') != 'combo' or {source['series'][m['series']]['chart_type'] for m in mapping} != set(raw_types)):
        _fail('combo_data_conditions_required', 'Combo requires kind=combo and explicit mapping covering each source plot type', ALTERNATIVES)
    if combo and any(k in ('bar', 'pie') for k in kinds):
        _fail('unsupported_source_configuration', 'SML combo cannot express this source bar/pie configuration faithfully', ALTERNATIVES)
    hidden_helpers = [s.get('hidden_duplicate') is True for s in data['series']]
    for index, hidden in enumerate(hidden_helpers):
        if hidden: _hidden_duplicate(source, data, mapping, index)
    series_label_mode = any(hidden_helpers) or any('data_labels' in s for s in data['series'])
    readability = series_label_mode or any(k in data for k in ('legend', 'value_format', 'value_axis', 'data_labels'))
    if readability and not (isinstance(reason,str) and reason.strip()):
        _fail('adaptation_reason_required','New value units/labels, axis or legend configuration require an adaptation reason')
    value_axis = _resolve_value_axis(data['value_axis'], [(source, data)]) if 'value_axis' in data else None
    attrs=dict(zip(SML_BBOX, (_fmt(box[k]) for k in BBOX_KEYS)))
    attrs['ooxml']='true'  # Source settings use the operator's imported-OOXML semantics.
    chart = ET.Element('chart', attrs)
    area = ET.SubElement(chart, 'chartPlotArea'); plot = ET.SubElement(area, 'chartPlot', {'type': 'combo' if combo else kinds[0]})
    extra = ET.SubElement(plot, 'chartExtra')
    groups = {p.get('grouping') for p in source.get('plot_types', []) if p.get('grouping') in ('stacked', 'percentStacked')}
    if groups:
        if combo and any(p.get('grouping') not in groups for p in source.get('plot_types',[])):
            _fail('unsupported_operator_combo_stack','Mixed source plot stack configurations cannot be applied through one global SML stack; use another applicable source or an adapter',ALTERNATIVES)
        if len(groups) > 1: _fail('unsupported_source_configuration', 'Mixed percentage/absolute stacks need a dedicated operator adapter', ALTERNATIVES)
        ET.SubElement(extra, 'chartStack', {'percentage': 'true'} if 'percentStacked' in groups else {})
    smoothing=[bool(p.get('smooth')) for p in source.get('plot_types',[])]
    if combo and any(smoothing) and not all(smoothing):
        _fail('unsupported_operator_combo_smoothing','Mixed source smoothing requires a per-plot operator adapter',ALTERNATIVES)
    if any(smoothing):
        ET.SubElement(extra, 'chartSmooth')
    labels = data.get('data_labels')
    if labels is None and (data.get('value_format') or value_axis): labels = _data_labels({})
    policies = [False if hidden else s.get('data_labels', labels) for s, hidden in zip(data['series'], hidden_helpers)]
    if series_label_mode and not any(p and (p['value'] or p['percentage']) for p in policies):
        if not ((data.get('value_format') or value_axis) and any(a.get('type') == 'valAx' for a in source.get('axes', []))):
            _fail('chart_readability_required', 'Disabling all series value labels requires an explicit readable number format on a real value axis')
    label_attrs = _label_attrs(labels, data, 'combo' if combo else kinds[0], groups, value_axis) if not series_label_mode else None
    if label_attrs:
        ET.SubElement(plot, 'chartLabels', label_attrs)
    series_list = ET.SubElement(plot, 'chartSeriesList'); palette = []; series_identities = []
    for n, m in enumerate(mapping, 1):
        s = source['series'][m['series']]; raw = s['chart_type']; kind = _kind(source, raw)
        source_plot = next((p for p in source['plot_types'] if p['type'] == raw), {})
        channel = 'line' if kind == 'line' else 'fill'
        record = _resolved_color(s.get('colors', []), channel)
        if s.get('appearance', {}).get(channel) == 'none' and not hidden_helpers[n-1]:
            _fail('unsupported_source_range', 'Invisible source series needs an explicit verified hidden_duplicate/helper_of contract, or a range adapter', ALTERNATIVES)
        if 'color_point' in m: record = _point_color(s, m['color_point'])
        paint = 'rgba(0,0,0,0)' if hidden_helpers[n-1] else _paint(record)
        if not hidden_helpers[n-1]: palette.append(paint)
        attrs = {'index': str(n)}
        if combo:
            attrs['comboType'] = kind
            axis_ids = source_plot.get('axis_ids', [])
            axis = next((a for a in source.get('axes', []) if a.get('axis_id') in axis_ids and a.get('type') == 'valAx'), {})
            attrs['yAxisPosition'] = 'right' if axis.get('position') == 'r' else 'left'
        series = ET.SubElement(series_list, 'chartSeries', attrs)
        # Imported charts can have per-series label visibility. Override at the
        # series level too. Selective policies omit the global node, so a series
        # with data_labels=False stays off rather than inheriting global labels.
        policy = policies[n-1]
        effective_attrs = _label_attrs(policy, data, kind, groups, value_axis, series_level=True) if series_label_mode else label_attrs
        series_labels = ET.SubElement(series, 'chartLabels', effective_attrs) if effective_attrs else None
        series_identities.append(bool(effective_attrs and effective_attrs.get('series') == 'true'))
        if series_labels is not None and groups and effective_attrs['position'] in ('inside', 'center', 'top', 'bottom') and 'color' not in (policy or {}):
            # Series identity inside a dark source fill must remain visible.
            # This changes label ink, never the source data palette.
            rgb = _paint_value(paint)
            channels = [(c*rgb[3]+255*(1-rgb[3]))/255 for c in rgb[:3]]
            linear = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in channels]
            luminance = sum(c*w for c,w in zip(linear, (.2126,.7152,.0722)))
            if 1.05/(luminance+.05) > (luminance+.05)/.066:
                series_labels.set('color', 'rgb(255,255,255)')
        if kind in ('bar', 'column'):
            attrs = {'color': paint}
            for field, key in (('gap_width', 'gapWidth'), ('overlap', 'overlap')):
                if source_plot.get(field) is not None: attrs[key] = _fmt(source_plot[field])
            styling = ET.SubElement(series, 'chartBars', attrs); item = 'chartBar'
        elif kind == 'area':
            styling = ET.SubElement(series, 'chartArea', {'color': paint}); item = None
        elif kind == 'line':
            ET.SubElement(series, 'chartLine', {'color': paint})
            marker=s.get('marker') or {};symbol=marker.get('symbol','none')
            marker_paint=_paint(_resolved_color(s.get('colors',[]),'marker_fill')) if _resolved_color(s.get('colors',[]),'marker_fill') else paint
            point_attrs={'color':marker_paint,'size':'0'}
            if symbol!='none':
                shape={'circle':'circle','square':'square','triangle':'triangle','diamond':'diamond'}.get(symbol)
                if shape is None or marker.get('size') is None:
                    _fail('unsupported_operator_marker','SML needs a supported source marker shape and resolved size; inherited/other marker styles need an adapter',ALTERNATIVES)
                point_attrs.update(shape=shape,size=_fmt(marker['size']))
            styling = ET.SubElement(series, 'chartPoints', point_attrs); item = 'chartPoint'
            if not hidden_helpers[n-1]: palette.append(marker_paint)
        else:
            attrs = {}
            if raw == 'doughnutChart':
                if source_plot.get('hole_size') is None:
                    _fail('unsupported_source_configuration','Source doughnut hole size is unresolved; choose an explicit source pie/ring configuration',ALTERNATIVES)
                attrs['innerRadius'] = _fmt(float(source_plot['hole_size'])/100)
            if source_plot.get('first_slice_angle') is not None: attrs['startAngle'] = _fmt(source_plot['first_slice_angle'])
            styling = ET.SubElement(series, 'chartSectors', attrs); item = 'chartSector'
        point_map = m.get('point_map')
        if item and 'color_point' not in m:
            for index in range(len(data['categories'])):
                source_index = point_map[index] if point_map is not None else index
                if source_index is None: continue
                point = next((p for p in s.get('point_overrides', []) if str(p.get('index')) == str(source_index)), None)
                if point is not None:
                    color = _paint(_point_color(s, source_index))
                    ET.SubElement(styling, item, {'index': str(index+1), 'color': color})
                    palette.append(color)
    axes = ET.SubElement(area, 'chartAxes') if any(k != 'pie' for k in kinds) else None
    seen_axes = set()
    for a in source.get('axes', []) if axes is not None else []:
        kind = 'x' if a.get('type') in ('catAx', 'dateAx') else 'y'
        pos = 'right' if a.get('position') == 'r' else 'left'
        key = (kind, pos if kind == 'y' else None)
        if key in seen_axes: continue
        seen_axes.add(key)
        attrs = {'type': kind}
        if kind == 'y': attrs['position'] = pos
        if kind == 'y' and value_axis:
            attrs.update(min=_fmt(value_axis['min']), max=_fmt(value_axis['max']), crosses='autoZero')
        if a.get('orientation') in ('minMax', 'maxMin'): attrs['orientation'] = a['orientation']
        hidden = a.get('deleted') or a.get('tick_label_position') == 'none'
        if a.get('deleted'): attrs['domainWidth'] = '0'
        axis = ET.SubElement(axes, 'chartAxis', attrs)
        labels = {'fontSize': '10'}
        show_values = kind == 'y' and (data.get('value_format') or value_axis or data.get('data_labels') or series_label_mode)
        show_categories = kind == 'x' and (data.get('data_labels') or series_label_mode or data.get('legend', {}).get('present') is False)
        if show_values:
            labels.update(color=value_axis.get('label_color', 'rgb(31,35,41)') if value_axis else 'rgb(31,35,41)', format=data.get('value_format', value_axis['format'] if value_axis else data.get('data_labels', {}).get('format', 'General')))
        elif show_categories: labels['color'] = 'rgb(31,35,41)'
        elif hidden: labels.update(color='rgba(0,0,0,0)', format=';;;')
        elif a.get('number_format'): labels['format'] = a['number_format']
        ET.SubElement(axis, 'chartLabel', labels)
        if a.get('major_gridlines') and not a.get('deleted'): ET.SubElement(axis, 'chartGridLine')
        if a.get('minor_gridlines') and not a.get('deleted'): ET.SubElement(axis, 'chartMinorGridLine')
    legend = source.get('legend', {})
    if 'legend' in data:
        override=data['legend']
        legend={'present':override['present'],'position':{'top':'t','bottom':'b','left':'l','right':'r'}.get(override.get('position'))}
    if groups and len(data['series']) > 1 and not legend.get('present') and not all(series_identities):
        _fail('series_identity_required', 'Multi-series stacks need an explicit readable legend or supported series-name data labels')
    if legend.get('present'):
        if legend.get('overlay') or legend.get('hidden_series_indices'):
            _fail('unsupported_operator_legend', 'SML legend cannot preserve overlay/deleted legend entries; choose an applicable source configuration', ALTERNATIVES)
        position = {'b':'bottom', 't':'top', 'l':'left', 'r':'right', 'tr':'right'}.get(legend.get('position'))
        if position is None: _fail('unsupported_operator_legend', 'Source legend position is unresolved', ALTERNATIVES)
        attrs = {'position': position, 'fontSize': '10'}
        if 'legend' in data: attrs['color'] = data['legend'].get('color', 'rgb(31,35,41)')
        ET.SubElement(chart, 'chartLegend', attrs)
    fields = ET.SubElement(chart, 'chartData'); dim1 = ET.SubElement(fields, 'dim1'); dim2 = ET.SubElement(fields, 'dim2')
    ET.SubElement(dim1, 'chartField', {'name': str(data['category_name']), 'valueType':'string'}).text = _csv(data['categories'])
    for s in data['series']:
        ET.SubElement(dim2, 'chartField', {'name': s['name'], 'valueType':'number'}).text = _csv([_fmt(v) for v in s['values']])
    if data.get('title'): ET.SubElement(chart, 'chartTitle', {'fontSize':'12'}).text = data['title']
    style = ET.SubElement(chart, 'chartStyle'); ET.SubElement(style, 'chartBackground', {'color':'rgba(0,0,0,0)'})
    colors = ET.SubElement(style, 'chartColorTheme')
    for paint in dict.fromkeys(palette): ET.SubElement(colors, 'color', {'value':paint})
    return chart


def make_page_contract(inventory, *, role='data_page'):
    if role not in ('data_page', 'cover', 'ending', 'table_page'):
        _fail('invalid_page_role', 'Use data_page, table_page, cover or ending')
    if role == 'table_page':
        _fail('table_data_required', 'table_page requires explicit user data; use build_table')
    return {'schema_version': 1, 'kind':'source-native-chart-contract', 'role':role,
            'source_inventory_sha256':_digest(inventory),
            # Complete source identity catalogue, not a requirement to place every chart.
            'source_chart_ids':[c['chart_id'] for s in inventory.get('slides',[]) for c in s.get('charts',[])],
            'charts':[], 'groups':[], 'tables':[]}


def build_chart(inventory, chart_id, new_data, *, series_map=None, bbox=None, adaptation_reason=None):
    source = _chart(inventory, chart_id)
    _source_types(source)  # Report operator type limitations before unrelated point-count adaptations.
    data = _new_data(new_data)
    mapping = _mapping(source, series_map, len(data['series']), len(data['categories']), adaptation_reason)
    box = _bbox(bbox) if bbox is not None else _source_bbox(source)
    node = _node(source, data, mapping, box, adaptation_reason)
    contract = make_page_contract(inventory)
    contract['charts'] = [{'source_chart_id':chart_id, 'source_identity':_source_identity(source),
                           'new_data':data, 'new_data_sha256':_digest(data),
                           'series_map':mapping, 'bbox':box, 'adaptation_reason':adaptation_reason}]
    return {'xml':ET.tostring(node, encoding='unicode'), 'contract':contract,
            'bindings':{'chart_sources':{'chart_index:0':chart_id}}}


def _group_boxes(group, count, box):
    members = sorted(group['members'], key=lambda m:(m['row'],m['column']))
    if not isinstance(count,int) or isinstance(count,bool) or count<=0:
        _fail('invalid_group_contract','Active panel count must be a positive integer')
    active=copy.deepcopy(members[:count])
    original=copy.deepcopy(group['bbox_inch'])
    if count > len(members):
        row_positions=[statistics.median(m['bbox_inch']['top'] for m in members if m['row']==row)
                       for row in sorted({m['row'] for m in members})]
        if len(row_positions)<2:
            _fail('unsupported_group_extension','A one-row source provides no vertical spacing law; select a multirow source or supply a separate layout adapter',ALTERNATIVES)
        row_step=statistics.median(b-a for a,b in zip(row_positions,row_positions[1:]))
        columns=group['columns']
        for index in range(count-len(members)):
            column=index%columns+1;row=group['rows']+index//columns+1
            candidates=[m for m in members if m['column']==column]
            if not candidates: _fail('unsupported_group_extension','Source grid has an unresolved column',ALTERNATIVES)
            prototype=copy.deepcopy(candidates[index%len(candidates)])
            prototype['row']=row;prototype['column']=column
            prototype['bbox_inch']['top']=row_positions[-1]+(row-group['rows'])*row_step
            active.append(prototype)
        original['height']=max(m['bbox_inch']['top']+m['bbox_inch']['height'] for m in active)-original['top']
    out = []
    for member in active:
        b = member['bbox_inch']
        out.append({'left':box['left']+(b['left']-original['left'])/original['width']*box['width'],
                    'top':box['top']+(b['top']-original['top'])/original['height']*box['height'],
                    'width':b['width']/original['width']*box['width'], 'height':b['height']/original['height']*box['height']})
    return members,active,[{k:round(v,6) for k,v in b.items()} for b in out]


def build_group(inventory, group_id, panels, *, bbox=None, adaptation_reason=None, value_axis=None):
    """Build source facets; opt into a common NEW-data scale with value_axis.

    value_axis={'shared': True, 'include_zero': True, 'format': '0.0"%"'}
    computes outward integer bounds. Explicit min/max may replace either bound.
    All active panels receive those bounds and one consistent number format.
    The integer requirement is the native SML schema, never data rounding.
    """
    group = _group(inventory, group_id)
    if not isinstance(panels, list) or not panels:
        _fail('invalid_new_data', 'Provide explicit new data for every active panel')
    if len(panels) != len(group['members']) and not (isinstance(adaptation_reason, str) and adaptation_reason.strip()):
        _fail('adaptation_reason_required', 'Changed panel count requires a reason; preserve the complete source group contract')
    box = _bbox(bbox) if bbox is not None else _source_bbox(group)
    members,active,boxes = _group_boxes(group, len(panels), box)
    prepared = []
    for panel in panels:
        if not isinstance(panel, dict) or 'data' not in panel:
            _fail('invalid_new_data', 'Each panel needs data and series_map')
        prepared.append(_new_data(panel['data']))
    axis_request, shared_axis = None, None
    if value_axis is not None:
        axis_request = _value_axis(value_axis, group=True)
        if not (isinstance(adaptation_reason, str) and adaptation_reason.strip()):
            _fail('adaptation_reason_required', 'A group common value axis requires its new-data comparison reason')
        shared_axis = _resolve_value_axis(axis_request, [(_chart(inventory, member['chart_id']), data) for member, data in zip(active, prepared)])
        for data in prepared:
            if 'value_axis' in data and any(data['value_axis'].get(k, shared_axis.get(k)) != shared_axis.get(k) for k in ('min', 'max', 'include_zero', 'format', 'label_color')):
                _fail('shared_value_axis_mismatch', 'Panel value_axis conflicts with the requested common scale')
            data['value_axis'] = copy.deepcopy(shared_axis)
            data['value_format'] = shared_axis['format']
    fragments, charts, bindings = [], [], {}
    for index, (panel, member, b) in enumerate(zip(panels, active, boxes)):
        if not isinstance(panel, dict) or 'data' not in panel:
            _fail('invalid_new_data', 'Each panel needs data and series_map')
        built = build_chart(inventory, member['chart_id'], prepared[index], series_map=panel.get('series_map'), bbox=b,
                            adaptation_reason=panel.get('adaptation_reason') or adaptation_reason)
        fragments.append(built['xml']); charts.extend(built['contract']['charts']); bindings[f'chart_index:{index}'] = member['chart_id']
    contract = make_page_contract(inventory); contract['charts'] = charts
    contract['groups'] = [{'source_group_id':group_id, 'source_chart_ids':[m['chart_id'] for m in members],
                           'source_rows':group['rows'], 'source_columns':group['columns'],
                           'source_members':copy.deepcopy(group['members']), 'active_chart_count':len(panels),
                           'bbox':box, 'adaptation_reason':adaptation_reason}]
    if axis_request is not None:
        contract['groups'][0].update(value_axis=axis_request, value_axis_sha256=_digest(axis_request), resolved_value_axis=shared_axis)
    return {'xml':''.join(fragments), 'contract':contract, 'bindings':{'chart_sources':bindings}}


def _table_data(data):
    if not isinstance(data, dict) or not isinstance(data.get('headers'), list) or not data['headers']:
        _fail('table_data_required', 'Provide explicit table headers and user rows')
    headers = data['headers']; rows = data.get('rows')
    if not all(isinstance(h,str) and h.strip() for h in headers) or not isinstance(rows,list) or not rows:
        _fail('table_data_required', 'Native table requires nonempty headers and user rows')
    cells = []
    for row in rows:
        if not isinstance(row,list) or len(row) != len(headers): _fail('invalid_table_data', 'Table row width must match headers')
        converted = []
        for value in row:
            if isinstance(value,str): converted.append(value)
            elif value is not None: converted.append(_fmt(value))
            else: _fail('invalid_table_data', 'Explicit table cells cannot be missing')
        cells.append(converted)
    return {'headers':list(headers), 'rows':cells}


def build_table(inventory, table_data, *, bbox):
    data = _table_data(table_data); box = _bbox(bbox)
    table = ET.Element('table', dict(zip(SML_BBOX, (_fmt(box[k]) for k in BBOX_KEYS))))
    cols = ET.SubElement(table, 'colgroup')
    for _ in data['headers']: ET.SubElement(cols, 'col')
    for index, values in enumerate([data['headers']]+data['rows']):
        row = ET.SubElement(table, 'tr')
        for value in values:
            cell = ET.SubElement(row, 'td'); attrs={'fontSize':'12'}
            if index == 0:
                fill = ET.SubElement(cell, 'fill'); ET.SubElement(fill, 'fillColor', {'color':'rgb(33,55,82)'})
                attrs.update(color='rgb(255,255,255)', bold='true')
            else: attrs['color']='rgb(31,35,41)'
            content = ET.SubElement(cell, 'content', attrs); ET.SubElement(content,'p').text = value
    contract = make_page_contract(inventory, role='cover'); contract['role']='table_page'
    contract['tables'] = [{'new_data':data, 'new_data_sha256':_digest(data), 'bbox':box}]
    return {'xml':ET.tostring(table,encoding='unicode'), 'contract':contract, 'bindings':{}}


def _paint_value(value):
    if value is None: return None
    match = re.fullmatch(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([0-9.]+))?\s*\)', value)
    if not match: return ('invalid',value)
    return tuple(int(match.group(i)) for i in (1,2,3)) + (float(match.group(4) or 1),)


def _read_data(chart):
    data = _child(chart,'chartData'); dim1, dim2 = _child(data,'dim1'), _child(data,'dim2')
    first = _children(dim1,'chartField')
    if len(first) != 1: _fail('new_data_mismatch', 'Native chart needs one explicit category field')
    try:
        categories = next(csv.reader(io.StringIO(first[0].text or '')))
        series = [{'name':f.get('name'), 'values':[_number(v) for v in next(csv.reader(io.StringIO(f.text or '')))]}
                  for f in _children(dim2,'chartField')]
    except (StopIteration,csv.Error): _fail('new_data_mismatch', 'Chart CSV data is incomplete')
    return {'categories':categories,'category_name':first[0].get('name'),'series':series}


def _config_signature(chart):
    area = _child(chart,'chartPlotArea'); plot = _child(area,'chartPlot')
    if plot is None: return {'type':None}
    extra = _child(plot,'chartExtra'); stack = _child(extra,'chartStack')
    series = []
    for s in _children(_child(plot,'chartSeriesList'),'chartSeries'):
        values = {'index':s.get('index'), 'comboType':s.get('comboType'), 'yAxisPosition':s.get('yAxisPosition')}
        for name,attrs in [('chartBars',('gapWidth','overlap')),('chartSectors',('innerRadius','startAngle')),('chartPoints',('size','shape'))]:
            node = _child(s,name)
            if node is not None: values[name] = {key:_number(node.get(key)) if key!='shape' else node.get(key) for key in attrs if node.get(key) is not None}
        series.append(values)
    axes = []
    for a in _children(_child(area,'chartAxes'),'chartAxis'):
        label = _child(a,'chartLabel')
        axes.append({'type':a.get('type'),'position':a.get('position'),'orientation':a.get('orientation'),
                     'crosses':a.get('crosses'),
                     'min':_number(a.get('min')) if a.get('min') is not None else None,
                     'max':_number(a.get('max')) if a.get('max') is not None else None,
                     'domainWidth':_number(a.get('domainWidth')) if a.get('domainWidth') is not None else None,
                     'label_format':label.get('format') if label is not None else None,
                     'label_color':_paint_value(label.get('color')) if label is not None else None,
                     'label_font_size':_number(label.get('fontSize')) if label is not None and label.get('fontSize') is not None else None,
                     'major_gridlines':_child(a,'chartGridLine') is not None,'minor_gridlines':_child(a,'chartMinorGridLine') is not None})
    legend = _child(chart,'chartLegend')
    return {'ooxml':chart.get('ooxml') in ('true','1'),
            'type':plot.get('type'), 'stack':dict(stack.attrib) if stack is not None else None,
            'smooth':_child(extra,'chartSmooth') is not None, 'series':series,'axes':axes,
            'legend':{'position':legend.get('position','bottom'), 'color':_paint_value(legend.get('color')),
                      'fontSize':_number(legend.get('fontSize')) if legend.get('fontSize') is not None else None} if legend is not None else None}


def _label_signature(chart):
    """Include all global/series/point overrides, which can hide explicit labels."""
    result = []
    def walk(node, path):
        if _local(node) == 'chartLabels':
            attrs = {k:node.get(k, 'true' if k == 'value' else 'false') in ('true', '1')
                     for k in ('value', 'category', 'series', 'percentage', 'legendKey', 'showGuidLine')}
            attrs.update(position=node.get('position', 'auto'), format=node.get('format'), separator=node.get('separator'),
                         color=_paint_value(node.get('color')), fontSize=_number(node.get('fontSize')) if node.get('fontSize') is not None else None)
            result.append((path, attrs))
        counts = {}
        for child in node:
            name = _local(child); counts[name] = counts.get(name, 0)+1
            walk(child, path+((name, counts[name]),))
    walk(chart, ())
    return result


def _color_signature(chart, series_count, category_count):
    plot = _child(_child(chart,'chartPlotArea'),'chartPlot')
    style = _child(chart,'chartStyle'); theme = _children(_child(style,'chartColorTheme'),'color')
    default = [_paint_value(c.get('value')) for c in theme]
    series = _children(_child(plot,'chartSeriesList'),'chartSeries')
    by_index = {int(s.get('index','0')):s for s in series}
    result = []
    for index in range(1,series_count+1):
        s = by_index.get(index); typ = s.get('comboType') if s is not None and plot.get('type')=='combo' else plot.get('type')
        kind = 'chartBars' if typ in ('column','bar') else 'chartLine' if typ=='line' else 'chartArea' if typ=='area' else 'chartSectors'
        styling = _child(s,kind); base = _paint_value(styling.get('color')) if styling is not None and styling.get('color') else (default[(index-1)%len(default)] if default else None)
        point_kind = 'chartBar' if kind=='chartBars' else 'chartSector' if kind=='chartSectors' else 'chartPoint'
        owner = _child(s,'chartPoints') if kind=='chartLine' else styling
        point_base=_paint_value(owner.get('color')) if kind=='chartLine' and owner is not None and owner.get('color') else base
        points = [point_base]*category_count
        for point in _children(owner,point_kind):
            number = int(point.get('index','0'))
            if 1 <= number <= category_count and point.get('color'): points[number-1] = _paint_value(point.get('color'))
        result.append({'base':base,'points':points})
    return result


def validate_chart_contract(sml, contract, *, inventory, bindings=None, tolerance=.01):
    """Validate one authored slide against selected source style and explicit new data."""
    errors = []
    result = {'ok':False,'errors':errors,'checked_charts':0,'checked_tables':0}
    def error(code,message,**extra): errors.append({'code':code,'message':message,**extra})
    try:
        if not isinstance(contract,dict) or contract.get('kind')!='source-native-chart-contract' or contract.get('schema_version')!=1:
            _fail('invalid_contract','Expected a source-native-chart-contract')
        if contract.get('source_inventory_sha256') != _digest(inventory):
            _fail('source_inventory_mismatch','Contract does not identify the supplied source inventory')
        if contract.get('source_chart_ids') != [c['chart_id'] for s in inventory.get('slides',[]) for c in s.get('charts',[])]:
            _fail('source_catalog_mismatch','Contract must retain all source chart IDs separately from active charts/new data')
        role=contract.get('role')
        if role not in ('data_page','table_page','cover','ending'): _fail('invalid_page_role','Unknown page role')
        if isinstance(sml,ET.Element): root=sml
        else:
            if re.search(r'<!\s*(DOCTYPE|ENTITY)\b',sml.decode() if isinstance(sml,bytes) else sml,re.I): _fail('invalid_sml','DTD/entities are unsupported')
            root=ET.fromstring(sml)
        if _local(root)!='slide': _fail('invalid_sml','Preflight accepts exactly one slide')
        data=_child(root,'data'); charts=[n for n in _children(data,'chart') if n.tag=='chart' or n.tag==f'{{{SML}}}chart']
        tables=[n for n in _children(data,'table') if n.tag=='table' or n.tag==f'{{{SML}}}table']; expected=contract.get('charts',[])
        if role=='data_page' and not charts: error('native_chart_required','Declared data_page has no native chart; shape bars/host references are not source-native charts')
        if len(charts)!=len(expected): error('native_chart_count_mismatch','Native chart count differs from the selected source contract',expected=len(expected),actual=len(charts))
        source_bindings=(bindings or {}).get('chart_sources',{})
        if charts and not isinstance(source_bindings,dict): _fail('invalid_bindings','chart_sources must map chart_index:N to source IDs')
        for index,record in enumerate(expected):
            source=_chart(inventory,record.get('source_chart_id'))
            if record.get('source_identity') != _source_identity(source): error('source_chart_binding_mismatch','Source identity fields were changed',chart_index=index)
            if source_bindings.get(f'chart_index:{index}')!=source['chart_id']: error('source_chart_binding_mismatch','Bind every native chart to its selected source chart ID',chart_index=index)
            new_data=_new_data(record.get('new_data')); mapping=_mapping(source,record.get('series_map'),len(new_data['series']),len(new_data['categories']),record.get('adaptation_reason'))
            if record.get('new_data_sha256')!=_digest(new_data):
                error('new_data_contract_mismatch','Explicit new task data changed after contract creation; rebuild the binding from the intended inputs',chart_index=index)
            expected_node=_node(source,new_data,mapping,_bbox(record.get('bbox')),record.get('adaptation_reason'))
            if index>=len(charts): continue
            actual=charts[index];result['checked_charts']+=1
            wanted={k:new_data[k] for k in ('categories','category_name')}
            wanted['series'] = [{k:s[k] for k in ('name', 'values')} for s in new_data['series']]
            if _read_data(actual)!=wanted: error('new_data_mismatch','Authored chart data differs from explicitly supplied new task data',chart_index=index)
            if _config_signature(actual)!=_config_signature(expected_node): error('source_chart_config_mismatch','Authored plot type/stack/axes/legend/source configuration differs',chart_index=index)
            if _label_signature(actual)!=_label_signature(expected_node): error('chart_readability_mismatch','Actual data labels differ from explicit NEW-task labels or contain hidden series/point overrides',chart_index=index)
            if _color_signature(actual,len(new_data['series']),len(new_data['categories']))!=_color_signature(expected_node,len(new_data['series']),len(new_data['categories'])):
                error('source_palette_mismatch','Actual series/point colors differ from selected source data colors; logo palette is not a substitute',chart_index=index)
            try: box={k:float(actual.get(a)) for k,a in zip(BBOX_KEYS,SML_BBOX)}
            except (TypeError,ValueError): box={}
            if any(k not in box or not math.isfinite(box[k]) or abs(box[k]-record['bbox'][k])>tolerance for k in BBOX_KEYS): error('source_chart_geometry_mismatch','Authored chart bbox differs from bound source/target geometry',chart_index=index)
        for group_record in contract.get('groups',[]):
            group=_group(inventory,group_record.get('source_group_id')); count=group_record.get('active_chart_count')
            members,active,boxes=_group_boxes(group,count,_bbox(group_record.get('bbox')))
            if (group_record.get('source_chart_ids')!=[m['chart_id'] for m in members] or group_record.get('source_members')!=group['members'] or
                    group_record.get('source_rows')!=group['rows'] or group_record.get('source_columns')!=group['columns']): error('source_group_binding_mismatch','Keep the complete selected source group and row/column layout')
            if count!=len(group['members']) and not (isinstance(group_record.get('adaptation_reason'),str) and group_record['adaptation_reason'].strip()): error('adaptation_reason_required','Changed active panel count requires a reason')
            if len(expected)!=count or any(expected[i].get('source_chart_id')!=active[i]['chart_id'] or any(abs(expected[i]['bbox'][k]-boxes[i][k])>tolerance for k in BBOX_KEYS) for i in range(min(len(expected),count))): error('source_group_geometry_mismatch','Selected facets cannot be silently collapsed or moved out of their source grid')
            if 'value_axis' in group_record:
                request = _value_axis(group_record['value_axis'], group=True)
                resolved = _resolve_value_axis(request, [(_chart(inventory, r['source_chart_id']), _new_data(r['new_data'])) for r in expected])
                if (group_record.get('value_axis_sha256') != _digest(request) or group_record.get('resolved_value_axis') != resolved or
                        any(r['new_data'].get('value_axis') != resolved or r['new_data'].get('value_format') != resolved['format'] for r in expected)):
                    error('shared_value_axis_mismatch', 'Every active same-metric panel must retain the shared NEW-data bounds and format')
        table_records=contract.get('tables',[])
        if role=='table_page' and (not tables or not table_records): error('native_table_required','table_page needs a real native table with bound user data; shape bars do not qualify')
        if len(tables)!=len(table_records) and role=='table_page': error('native_table_count_mismatch','Table count differs from explicit user data')
        for index,record in enumerate(table_records):
            expected_data=_table_data(record.get('new_data'))
            if record.get('new_data_sha256')!=_digest(expected_data): error('new_data_contract_mismatch','Explicit table user data changed after contract creation',table_index=index)
            if index>=len(tables): continue
            actual_rows=[[''.join(c.itertext()).strip() for c in _children(r,'td')] for r in _children(tables[index],'tr')]
            if actual_rows != [expected_data['headers']]+expected_data['rows']: error('table_data_mismatch','Native table cells differ from explicitly supplied user data',table_index=index)
            result['checked_tables']+=1
    except ChartContractError as exc: errors.append(exc.as_dict())
    except (ET.ParseError,KeyError,TypeError,ValueError,AttributeError) as exc: error('invalid_contract_or_sml',str(exc))
    result['ok']=not errors
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',required=True,type=Path)
    parser.add_argument('--chart-id');parser.add_argument('--group-id')
    parser.add_argument('--data',type=Path);parser.add_argument('--series-map',type=Path)
    parser.add_argument('--bbox',help='JSON left/top/width/height object');parser.add_argument('--reason')
    parser.add_argument('--value-axis',help='Group shared scale JSON: shared, min/max, include_zero, format, label_color; single charts use new_data.value_axis')
    parser.add_argument('--output',type=Path);parser.add_argument('--contract-output',type=Path);parser.add_argument('--bindings-output',type=Path)
    parser.add_argument('--sml',type=Path);parser.add_argument('--contract',type=Path);parser.add_argument('--bindings',type=Path)
    args=parser.parse_args(argv)
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    try:
        inventory=read(args.inventory)
        if args.sml or args.contract:
            if not args.sml or not args.contract: _fail('invalid_arguments','--sml and --contract are required together')
            result=validate_chart_contract(args.sml.read_text(encoding='utf-8'),read(args.contract),inventory=inventory,bindings=read(args.bindings) if args.bindings else None)
            print(json.dumps(result,ensure_ascii=False));return 0 if result['ok'] else 1
        if not args.data or bool(args.chart_id)==bool(args.group_id): _fail('invalid_arguments','Choose --chart-id or --group-id and explicit --data')
        box=json.loads(args.bbox) if args.bbox else None
        if args.value_axis and not args.group_id: _fail('invalid_arguments', '--value-axis is a group option; one chart uses its explicit new_data.value_axis')
        built=build_group(inventory,args.group_id,read(args.data),bbox=box,adaptation_reason=args.reason,value_axis=json.loads(args.value_axis) if args.value_axis else None) if args.group_id else build_chart(inventory,args.chart_id,read(args.data),series_map=read(args.series_map) if args.series_map else None,bbox=box,adaptation_reason=args.reason)
        if not all((args.output,args.contract_output,args.bindings_output)): _fail('invalid_arguments','Generation needs --output, --contract-output and --bindings-output')
        paths=[args.output,args.contract_output,args.bindings_output]
        if len({p.resolve() for p in paths})!=3 or any(p.resolve() in {args.inventory.resolve(),args.data.resolve()} for p in paths): _fail('invalid_arguments','Outputs must be distinct from input artifacts')
        for p in paths:
            if p.exists(): _fail('output_exists',f'Output already exists: {p}')
        for path,key in zip(paths,('xml','contract','bindings')):
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(built[key] if key=='xml' else json.dumps(built[key],ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ok':True,'charts':len(built['contract']['charts']),'source_chart_ids':[c['source_chart_id'] for c in built['contract']['charts']],'output':str(args.output.resolve())},ensure_ascii=False));return 0
    except (ChartContractError,OSError,ValueError,TypeError) as exc:
        print(json.dumps({'ok':False,'error':exc.as_dict() if isinstance(exc,ChartContractError) else str(exc)},ensure_ascii=False));return 1


if __name__=='__main__':
    raise SystemExit(main())
