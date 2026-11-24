"""Decimal arithmetic for explicit inputs; no financial or factual inference.

Use a UTF-8 JSON file or '-' for stdin. No network or output file writes.
"""
from decimal import Context, Decimal, DecimalException, InvalidOperation, localcontext
import argparse
import json
from pathlib import Path
import sys

MAX_BYTES = 1048576
MAX_ITEMS = 10000


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError('a finite decimal number is required')
    if len(str(value)) > 128:
        raise ValueError('number exceeds supported length')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid decimal number') from exc
    if not result.is_finite() or abs(result.adjusted()) > 100 or len(result.as_tuple().digits) > 96:
        raise ValueError('number exceeds supported precision or magnitude')
    return result


def numeric_list(value):
    if not isinstance(value, list) or not value or len(value) > MAX_ITEMS:
        raise ValueError('provide 1 to 10000 numbers')
    return [number(item) for item in value]


def quotient(a, b):
    with localcontext(Context(prec=28)):
        return a / b


def inspect(values):
    # Given the magnitude, precision and list bounds in number/numeric_list,
    # products span at most 592 decimal places, plus four places for summation.
    with localcontext(Context(prec=640)):
        return calculate(values)


def calculate(values):
    if not isinstance(values, dict):
        raise ValueError('input must be an object')
    operation = values.get('operation')
    fields = {
        'ratio': {'numerator', 'denominator'},
        'growth': {'before', 'after'},
        'per_share': {'amount', 'shares'},
        'difference': {'before', 'after'},
        'bridge': {'opening', 'changes'},
        'weighted_mean': {'values', 'weights'},
    }
    if not isinstance(operation, str) or operation not in fields:
        raise ValueError('unsupported operation')
    if set(values) != fields[operation] | {'operation'}:
        raise ValueError('provide only the fields required by the operation')
    if operation == 'ratio':
        numerator, denominator = number(values['numerator']), number(values['denominator'])
        if denominator == 0:
            raise ValueError('denominator must be nonzero')
        result = quotient(numerator, denominator)
        return {'ratio': str(result), 'percent': str(quotient(numerator * 100, denominator))}
    if operation in {'growth', 'difference'}:
        before, after = number(values['before']), number(values['after'])
        result = {'change': str(after - before)}
        if operation == 'growth':
            result['growth_percent'] = str(quotient((after - before) * 100, before)) if before > 0 else None
        return result
    if operation == 'per_share':
        amount, shares = number(values['amount']), number(values['shares'])
        if shares <= 0:
            raise ValueError('shares must be positive')
        return {'per_share': str(quotient(amount, shares))}
    if operation == 'bridge':
        opening = number(values['opening'])
        changes = values['changes']
        if not isinstance(changes, list) or len(changes) > MAX_ITEMS:
            raise ValueError('provide at most 10000 signed changes')
        total = sum((number(item) for item in changes), Decimal(0))
        return {'total_change': str(total), 'closing': str(opening + total)}
    observations, weights = numeric_list(values['values']), numeric_list(values['weights'])
    if len(observations) != len(weights) or any(weight < 0 for weight in weights):
        raise ValueError('weights must be nonnegative and match the values')
    weight_total = sum(weights, Decimal(0))
    if weight_total == 0:
        raise ValueError('total weight must be positive')
    weighted_sum = sum((value * weight for value, weight in zip(observations, weights)), Decimal(0))
    result = quotient(weighted_sum, weight_total)
    return {'weighted_mean': str(result), 'total_weight': str(weight_total)}


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def run_cli(function, description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('input', help="UTF-8 JSON file or '-' for stdin")
    args = parser.parse_args()
    try:
        if args.input == '-':
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with Path(args.input).open('rb') as stream:
                raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('input exceeds 1 MiB')
        values = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_keys,
                            parse_float=Decimal,
                            parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite number')))
        print(json.dumps(function(values), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, DecimalException, RecursionError) as exc:
        if isinstance(exc, OSError):
            message = 'cannot read input file'
        elif isinstance(exc, KeyError):
            message = 'missing required field'
        elif isinstance(exc, (UnicodeError, json.JSONDecodeError)):
            message = 'invalid UTF-8 or JSON input'
        else:
            message = str(exc)
        print(json.dumps({'status': 'error', 'error': message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(run_cli(inspect, __doc__))
