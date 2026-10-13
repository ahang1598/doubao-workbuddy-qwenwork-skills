"""Standalone, offline arithmetic resource for industry research; JSON in/out."""
import json
import math
import sys
from pathlib import Path


def keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('Expected fields: ' + ', '.join(sorted(expected)))


def number(value, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('A finite number, not a boolean, is required')
    if nonnegative and value < 0:
        raise ValueError('Negative input is not allowed here')
    return value


def nullable(value, nonnegative=False):
    return None if value is None else number(value, nonnegative)


def label(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Nonempty text is required')
    return value


def members(rows, field, nonnegative=False):
    if not isinstance(rows, list) or not rows:
        raise ValueError('A nonempty list is required')
    result = {}
    for row in rows:
        keys(row, {'id', field})
        identifier = label(row['id'])
        if identifier in result:
            raise ValueError('Duplicate member id')
        result[identifier] = nullable(row[field], nonnegative)
    return result


def total(values):
    values = list(values)
    return None if any(v is None for v in values) else math.fsum(values)


def calculate(data):
    keys(data, {'operation', 'scope', 'inputs'})
    scope = data['scope']
    keys(scope, {'object', 'region', 'unit', 'basis'})
    for value in scope.values():
        label(value)
    op, inp = data['operation'], data['inputs']
    if op == 'growth':
        keys(inp, {'start', 'end', 'years'})
        start, end = nullable(inp['start'], True), nullable(inp['end'], True)
        years = number(inp['years'], True)
        if years <= 0 or start == 0:
            raise ValueError('Positive start and positive years required')
        if start is None or end is None:
            result = {'growth_pct': None, 'cagr_pct': None, 'status': 'missing'}
        else:
            result = {'growth_pct': (end / start - 1) * 100,
                      'cagr_pct': ((end / start) ** (1 / years) - 1) * 100,
                      'status': 'calculated'}
    elif op == 'reconcile':
        keys(inp, {'total', 'components'})
        stated = nullable(inp['total'], True)
        parts = members(inp['components'], 'value', True)
        summed = total(parts.values())
        delta = None if stated is None or summed is None else summed - stated
        result = {'component_sum': summed, 'delta_components_minus_total': delta,
                  'coverage_ratio': None if stated in (None, 0) or summed is None else summed / stated,
                  'status': 'missing' if delta is None else 'calculated'}
    elif op == 'profit_pool':
        keys(inp, {'before_period', 'after_period', 'before', 'after'})
        if label(inp['before_period']) == label(inp['after_period']):
            raise ValueError('Distinct comparison periods required')
        before, after = members(inp['before'], 'profit'), members(inp['after'], 'profit')
        if set(before) != set(after):
            raise ValueError('Profit pool membership differs across periods')
        btotal, atotal = total(before.values()), total(after.values())
        rows = []
        for name in before:
            b, a = before[name], after[name]
            bs = None if b is None or btotal is None or btotal <= 0 else b / btotal
            ass = None if a is None or atotal is None or atotal <= 0 else a / atotal
            rows.append({'id': name, 'profit_change': None if b is None or a is None else a - b,
                         'before_share': bs, 'after_share': ass,
                         'share_change_pp': None if bs is None or ass is None else (ass - bs) * 100})
        result = {'before_total': btotal, 'after_total': atotal, 'rows': rows,
                  'status': 'missing' if btotal is None or atotal is None else 'calculated',
                  'share_limit': 'Shares omitted when a period total is missing or nonpositive; signed components may yield shares outside [0,1].'}
    elif op == 'inventory':
        keys(inp, {'opening', 'inflow', 'outflow', 'adjustments'})
        values = {k: nullable(v, k != 'adjustments') for k, v in inp.items()}
        closing = None if any(v is None for v in values.values()) else math.fsum([
            values['opening'], values['inflow'], -values['outflow'], values['adjustments']])
        result = {'closing': closing, 'status': 'missing' if closing is None else (
            'inconsistent_flow' if closing < 0 else 'calculated')}
    else:
        raise ValueError('Unknown operation')
    output = {'operation': op, 'scope': scope, 'result': result}
    json.dumps(output, allow_nan=False)
    return output


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('Nonfinite JSON constant: ' + value)


def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError('Use industry_metrics.py INPUT.json or - for stdin')
        raw = sys.stdin.read() if sys.argv[1] == '-' else Path(sys.argv[1]).read_text()
        data = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
        print(json.dumps(calculate(data), ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, TypeError, OverflowError, OSError, KeyError, ZeroDivisionError) as exc:
        print(json.dumps({'error': {'message': str(exc) or type(exc).__name__}}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
