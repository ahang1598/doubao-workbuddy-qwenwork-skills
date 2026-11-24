#!/usr/bin/env python3
"""Format declared metrics and compute comparisons for text, charts and notes.

Units and value scale come from the task data definition, not guessed from a
template label. Results describe arithmetic/ranks, not causes or forecasts.
"""
import argparse
from decimal import Decimal,ROUND_HALF_UP,InvalidOperation
import hashlib
import json
from pathlib import Path

def _decimal(value):
    if isinstance(value,bool):raise ValueError('A metric value must be numeric')
    number=Decimal(str(value))
    if not number.is_finite():raise ValueError('A metric value must be finite')
    return number

def format_metric(value,*,unit,scale='native',digits=1):
    """Return one display string using explicit unit/scale; None is unmeasured."""
    if value is None:return '未测量'
    if not isinstance(digits,int) or isinstance(digits,bool) or not 0<=digits<=10:
        raise ValueError('digits must be an integer from0 to10')
    number=_decimal(value)
    if unit=='percent':
        if scale=='fraction':number*=100
        elif scale not in {'percent','native'}:raise ValueError('Percent scale is fraction or percent')
        suffix='%'
    else:
        if scale not in {'native','number'}:raise ValueError('Only percentages use fraction scaling')
        suffix={'score':'分','number':'','count':'','currency':''}.get(unit,unit)
    quantized=number.quantize(Decimal(1).scaleb(-digits),rounding=ROUND_HALF_UP)
    return format(quantized,f'.{digits}f')+suffix

def compare_values(before,after):
    """Compute change; growth/fold wording requires a positive measured baseline."""
    before,after=_decimal(before),_decimal(after)
    delta=after-before
    return {'before':float(before),'after':float(after),'delta':float(delta),
            'relative_change_pct':float(delta/before*100) if before>0 else None,
            'ratio':float(after/before) if before>0 else None,
            'doubled':bool(before>0 and after>=before*2)}

def _metric_endpoint(value, kind, scale):
    if value is None:
        return None
    if kind == 'rate' and isinstance(value, dict):
        if 'numerator' not in value or 'denominator' not in value:
            raise ValueError('A rate endpoint needs numerator and denominator')
        numerator, denominator = value['numerator'], value['denominator']
        if numerator is None or denominator is None:
            return None
        denominator = _decimal(denominator)
        if denominator == 0:
            return None
        if denominator < 0:
            raise ValueError('A measured rate denominator must be positive')
        return _decimal(numerator) / denominator * 100
    number = _decimal(value)
    if kind == 'rate':
        if scale not in {'fraction', 'percent'}:
            raise ValueError('Scalar rate endpoints need fraction or percent scale')
        return number * 100 if scale == 'fraction' else number
    return number

def _display_value(value, unit, digits, *, signed=False, missing='未测量'):
    if value is None:
        return missing
    if type(digits) is not int or not 0 <= digits <= 10:
        raise ValueError('Display digits must be an integer from0 to10')
    rounded = value.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    if rounded == 0:
        rounded = abs(rounded)
    return format(rounded, ('+' if signed else '') + f'.{digits}f') + unit

def build_metric_values(data):
    """Build shared display strings from explicit, already-computed endpoints.

    Each metric declares id/label/kind/unit/scope/period/before/after. Period is
    {before: label, after: label}; kind is quantity or rate. Scalar rates declare
    scale=fraction|percent; ratio endpoints declare numerator/denominator.
    Literals are copied verbatim. Arithmetic uses unrounded endpoints.
    """
    if not isinstance(data, dict) or not isinstance(data.get('metrics'), list):
        raise ValueError('Input needs an explicit metrics array')
    values, metrics, by_id = {}, [], {}
    for metric in data['metrics']:
        if not isinstance(metric, dict):
            raise ValueError('Every metric must be an object')
        for field in ('id', 'label', 'unit', 'scope'):
            if not isinstance(metric.get(field), str) or not metric[field].strip():
                raise ValueError('Every metric needs explicit ' + field)
        identifier = metric['id']
        if identifier in by_id:
            raise ValueError('Duplicate metric id: ' + identifier)
        kind = metric.get('kind')
        if kind not in {'quantity', 'rate'}:
            raise ValueError('Metric kind must be quantity or rate')
        if kind == 'rate' and metric['unit'] != '%':
            raise ValueError('Rate display unit must be %')
        period = metric.get('period')
        if not isinstance(period, dict) or any(not isinstance(period.get(k), str) or
                not period[k].strip() for k in ('before', 'after')):
            raise ValueError('Every comparison needs before and after period labels')
        if 'before' not in metric or 'after' not in metric:
            raise ValueError('Endpoints must be explicit; use null for unmeasured data')
        try:
            before = _metric_endpoint(metric['before'], kind, metric.get('scale'))
            after = _metric_endpoint(metric['after'], kind, metric.get('scale'))
        except InvalidOperation as exc:
            raise ValueError('A metric endpoint must be numeric or null') from exc
        delta = after - before if before is not None and after is not None else None
        relative = delta / before * 100 if delta is not None and before > 0 else None
        direction = ('不可比较' if delta is None else
                     '增加' if delta > 0 else '减少' if delta < 0 else '不变')
        digits = metric.get('digits', 1)
        change_digits = metric.get('change_digits', digits)
        relative_digits = metric.get('relative_digits', 1)
        unit = metric['unit']
        change_unit = '个百分点' if kind == 'rate' else unit
        display = {
            'label': metric['label'], 'unit': unit, 'scope': metric['scope'],
            'period.before': period['before'], 'period.after': period['after'],
            'before': _display_value(before, unit, digits),
            'after': _display_value(after, unit, digits),
            'absolute_change': _display_value(delta, change_unit, change_digits,
                                               signed=True, missing='不可算'),
            'relative_change': _display_value(relative, '%', relative_digits,
                                               signed=True, missing='不可算'),
            'percentage_points': (_display_value(delta, '个百分点', change_digits,
                signed=True, missing='不可算') if kind == 'rate' else '不适用'),
            'direction': direction,
        }
        summary = (f"{metric['label']}（{metric['scope']}，{period['before']}→{period['after']}）："
                   f"{display['before']}→{display['after']}")
        if delta is not None:
            summary += '，' + direction + _display_value(abs(delta), change_unit, change_digits)
            if relative is not None:
                summary += '，相对变化' + display['relative_change']
        else:
            summary += '，变化不可算'
        display['summary'] = summary + '。'
        for key, value in display.items():
            values[identifier + '.' + key] = value
        row = {key: metric[key] for key in ('id', 'label', 'kind', 'unit', 'scope', 'period')}
        row.update(before=float(before) if before is not None else None,
                   after=float(after) if after is not None else None,
                   absolute_change=float(delta) if delta is not None else None,
                   relative_change_pct=float(relative) if relative is not None else None,
                   percentage_points=float(delta) if kind == 'rate' and delta is not None else None,
                   direction=direction, display=display)
        metrics.append(row)
        by_id[identifier] = row
    literals = data.get('literals', {})
    if not isinstance(literals, dict) or any(not isinstance(k, str) or not k.strip() or
            not isinstance(v, str) for k, v in literals.items()):
        raise ValueError('Literal values must be an explicit string mapping')
    if values.keys() & literals.keys():
        raise ValueError('Literal and metric value keys must be distinct')
    values.update(literals)
    groups = []
    for group in data.get('groups', []):
        if not isinstance(group, dict) or not isinstance(group.get('id'), str) or not group['id'].strip():
            raise ValueError('Chart group needs an explicit id')
        ids = group.get('metrics')
        if not isinstance(ids, list) or not ids or any(i not in by_id for i in ids):
            raise ValueError('Chart group must reference existing metric ids')
        members = [by_id[i] for i in ids]
        same_unit = len({r['unit'] for r in members}) == 1
        same_scope = len({r['scope'] for r in members}) == 1
        same_period = all(r['period'] == members[0]['period'] for r in members)
        comparable = same_unit and same_scope and same_period
        groups.append({'id': group['id'], 'metrics': ids, 'same_unit': same_unit,
            'same_scope': same_scope, 'same_period': same_period, 'comparable': comparable,
            'stack_recommended': False if not same_unit else None,
            'suggested_layout': 'shared_axis' if comparable else 'separate_panels'})
    return {'values': values, 'metrics': metrics, 'groups': groups, 'literals': literals}

def write_metric_values(input_file, output_file, receipt_file=None):
    """Save a string mapping with its exact input snapshot and arithmetic receipt."""
    source = Path(input_file).resolve()
    output = Path(output_file).resolve()
    receipt = Path(receipt_file).resolve() if receipt_file else output.with_suffix('.receipt.json')
    snapshot = receipt.with_suffix('.source.json')
    if len({source, output, receipt, snapshot}) != 4:
        raise ValueError('Input, values, receipt and source snapshot need separate paths')
    raw = source.read_bytes()
    built = build_metric_values(json.loads(raw))
    value_raw = (json.dumps(built['values'], ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    result = {'schema_version': 1, 'source': {'path': str(source),
        'sha256': hashlib.sha256(raw).hexdigest(), 'snapshot': str(snapshot)},
        'values': {'path': str(output), 'sha256': hashlib.sha256(value_raw).hexdigest()},
        'metrics': built['metrics'], 'groups': built['groups'], 'literals': built['literals']}
    receipt_raw = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    artifacts = {output: value_raw, receipt: receipt_raw, snapshot: raw}
    for path, content in artifacts.items():
        if path.exists() and (not path.is_file() or path.read_bytes() != content):
            raise ValueError('Existing values artifact differs: ' + str(path))
    for path, content in artifacts.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(content)
    return result

def matrix_extrema(row_labels,column_labels,values):
    """Return row/column extrema including ties and the exceptions to global claims."""
    if not row_labels or not column_labels or len(values)!=len(row_labels):
        raise ValueError('Matrix dimensions must match declared labels')
    if any(len(row)!=len(column_labels) for row in values):raise ValueError('Matrix columns must match labels')
    numeric=[[None if value is None else _decimal(value) for value in row] for row in values]
    def extrema(items):
        available=[(label,value) for label,value in items if value is not None]
        if not available:return None,None,[],[]
        minimum=min(v for _,v in available);maximum=max(v for _,v in available)
        return float(minimum),float(maximum),[k for k,v in available if v==minimum],[k for k,v in available if v==maximum]
    rows=[];columns=[]
    for label,row in zip(row_labels,numeric):
        low,high,minima,maxima=extrema(zip(column_labels,row))
        rows.append({'row':label,'min':low,'max':high,'min_columns':minima,'max_columns':maxima})
    for i,label in enumerate(column_labels):
        low,high,minima,maxima=extrema((name,row[i]) for name,row in zip(row_labels,numeric))
        columns.append({'column':label,'min':low,'max':high,'min_rows':minima,'max_rows':maxima})
    all_leaders=[label for label in row_labels if all(label in col['max_rows'] for col in columns)]
    return {'rows':rows,'columns':columns,'all_column_leaders':all_leaders}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    fmt=commands.add_parser('format');fmt.add_argument('--value',required=True);fmt.add_argument('--unit',required=True)
    fmt.add_argument('--scale',default='native');fmt.add_argument('--digits',type=int,default=1)
    cmp=commands.add_parser('compare');cmp.add_argument('--before',required=True);cmp.add_argument('--after',required=True)
    matrix=commands.add_parser('matrix');matrix.add_argument('--input',required=True);matrix.add_argument('--output')
    values=commands.add_parser('values');values.add_argument('--input',required=True)
    values.add_argument('--output',required=True);values.add_argument('--receipt')
    args=parser.parse_args(argv)
    if args.command=='format':print(format_metric(args.value,unit=args.unit,scale=args.scale,digits=args.digits));return
    if args.command=='values':
        print(json.dumps(write_metric_values(args.input,args.output,args.receipt),ensure_ascii=False,indent=2));return
    if args.command=='compare':result=compare_values(args.before,args.after)
    else:
        data=json.loads(Path(args.input).read_text());result=matrix_extrema(data['row_labels'],data['column_labels'],data['values'])
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if getattr(args,'output',None):Path(args.output).write_text(text+'\n')
    else:print(text)

if __name__=='__main__':main()
