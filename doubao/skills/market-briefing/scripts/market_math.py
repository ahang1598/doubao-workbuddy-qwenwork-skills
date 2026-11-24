#!/usr/bin/env python3
"""Local table reading and market arithmetic. No network, report checking or writes."""
import argparse
import csv
import datetime as dt
import json
import math
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from itertools import islice
from pathlib import Path
from zipfile import BadZipFile


def number(value):
    """None/empty cells remain missing; ambiguous formatted numbers are not guessed."""
    if value is None or (isinstance(value, str) and value.strip() in ('', '—', 'NA', 'N/A')):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError('expected a finite number or missing cell')
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('non-finite number')
    return result


def sequence(values):
    if isinstance(values, (str, bytes, bytearray, dict)):
        raise ValueError('expected an array of numeric values')
    return list(values)


def complete(values):
    items = [number(v) for v in sequence(values)]
    return None if not items or any(v is None for v in items) else items


def finite(value):
    if value is not None and not math.isfinite(value):
        raise ValueError('non-finite arithmetic result')
    return value


def total(values):
    items = complete(values)
    if items is None:
        return None
    try:
        return finite(math.fsum(items))
    except OverflowError:
        return finite(float(sum(Fraction(v) for v in items)))


def mean(values):
    items = complete(values)
    if items is None:
        return None
    try:
        return finite(math.fsum(items) / len(items))
    except OverflowError:
        return finite(float(sum(Fraction(v) for v in items) / len(items)))


def ratio(numerator, denominator):
    a, b = number(numerator), number(denominator)
    return None if a is None or b is None or b == 0 else finite(a / b)


def change_pct(current, baseline):
    r = ratio(current, baseline)
    return None if r is None else finite((r - 1) * 100)


def price_return(start, end):
    a, b = number(start), number(end)
    if a is not None and a <= 0 or b is not None and b < 0:
        raise ValueError('price start must be positive and end nonnegative')
    if a is None or b is None:
        return None
    return change_pct(b, a)


def compound_return(returns_pct):
    items = [number(v) for v in sequence(returns_pct)]
    if any(v is not None and v < -100 for v in items):
        raise ValueError('simple returns cannot be below -100 percent')
    if not items or any(v is None for v in items):
        return None
    if -100 in items:
        return -100.0
    # Avoid overflowing or underflowing on intermediate products.
    mantissa, exponent = 1.0, 0
    for value in items:
        factor = 1 + value / 100
        fractional, shift = math.frexp(factor)
        mantissa, carry = math.frexp(mantissa * fractional)
        exponent += shift + carry
    try:
        return finite((math.ldexp(mantissa, exponent) - 1) * 100)
    except OverflowError as error:
        raise ValueError('compound result exceeds finite range') from error


def group_comparison(current, baseline):
    """Paired members only; aggregate ratio differs from average member ratio."""
    a, b = sequence(current), sequence(baseline)
    if len(a) != len(b) or not a:
        raise ValueError('matched nonempty member arrays required')
    at, bt = total(a), total(b)
    return {'current_total': at, 'baseline_total': bt,
            'ratio': ratio(at, bt), 'change_pct': change_pct(at, bt),
            'member_count': len(a)}


def weighted_return(returns_pct, weights, normalize=False):
    """Weights are decimal shares. Contributions are percentage points."""
    if type(normalize) is not bool:
        raise ValueError('normalize must be boolean')
    r, w = sequence(returns_pct), sequence(weights)
    if len(r) != len(w) or not r:
        raise ValueError('matched nonempty return and weight arrays required')
    rr, ww = complete(r), [number(v) for v in w]
    if any(v is not None and v < 0 for v in ww):
        raise ValueError('this index decomposition expects nonnegative weights')
    if any(v is None for v in ww):
        return {'return_pct': None, 'contributions_pp': None, 'weight_sum': None}
    ws = math.fsum(ww)
    if not normalize and not math.isclose(ws, 1.0, rel_tol=1e-8, abs_tol=1e-8):
        raise ValueError('full-index weights must sum to one; request normalization for a subset')
    if rr is None:
        return {'return_pct': None, 'contributions_pp': None, 'weight_sum': ws}
    if ws == 0:
        return {'return_pct': None, 'contributions_pp': None, 'weight_sum': 0.0}
    used = [v / ws for v in ww] if normalize else ww
    contributions = [finite(a * b) for a, b in zip(rr, used)]
    return {'return_pct': finite(math.fsum(contributions)),
            'contributions_pp': contributions, 'weight_sum': ws}


def breadth(up, flat, down):
    counts = (up, flat, down)
    if any(type(v) is not int or v < 0 for v in counts):
        raise ValueError('breadth needs exact nonnegative integer counts')
    n = sum(counts)
    return {'up': up, 'flat': flat, 'down': down, 'sample_count': n,
            'up_pct': None if n == 0 else up / n * 100}


def rolling_mean(values_by_date, sessions, target, n, include_current=False):
    """Explicit ordered session calendar; missing days are not replaced by older rows."""
    if type(n) is not int or n <= 0 or type(include_current) is not bool:
        raise ValueError('positive integer window and boolean include_current required')
    if type(values_by_date) is not dict:
        raise ValueError('values_by_date must be a date-to-value object')
    days = sequence(sessions)
    if not days or any(type(d) is not str for d in days):
        raise ValueError('unique ISO YYYY-MM-DD session dates required')
    if (len(set(days)) != len(days) or
            any(dt.date.fromisoformat(d).isoformat() != d for d in days)):
        raise ValueError('unique ISO YYYY-MM-DD session dates required')
    parsed = [dt.date.fromisoformat(d) for d in days]
    if parsed != sorted(parsed):
        raise ValueError('session dates must be chronological')
    if target not in days:
        raise ValueError('target must belong to supplied session calendar')
    stop = days.index(target) + (1 if include_current else 0)
    window = days[max(0, stop - n):stop]
    values = [number(values_by_date.get(d)) for d in window]
    missing = [d for d, v in zip(window, values) if v is None]
    return {'value': None if len(window) != n or missing else mean(values),
            'window_dates': window, 'missing_dates': missing,
            'required_sessions': n, 'calendar_sessions': len(window),
            'include_current': include_current}


def rank_rows(rows, field, descending=True, limit=None, tie_key=None):
    if type(descending) is not bool or (limit is not None and (type(limit) is not int or limit < 0)):
        raise ValueError('boolean direction and optional nonnegative integer limit required')
    if type(field) is not str or not field:
        raise ValueError('field must be a nonempty column name')
    if tie_key is not None and (type(tie_key) is not str or not tie_key):
        raise ValueError('tie_key must be a nonempty column name')
    eligible, missing = [], []
    for i, row in enumerate(sequence(rows)):
        if type(row) is not dict:
            raise ValueError('each ranked row must be an object')
        raw = row.get(field)
        if raw is None or isinstance(raw, str) and raw.strip() in ('', '—', 'NA', 'N/A'):
            missing.append(row)
            continue
        if type(raw) not in (int, float, str):
            raise ValueError('ranking needs finite numeric values')
        try:
            v = Decimal(str(raw))
        except InvalidOperation as error:
            raise ValueError('ranking needs finite numeric values') from error
        if not v.is_finite():
            raise ValueError('ranking needs finite numeric values')
        tie = str(row[tie_key]) if tie_key is not None else i
        eligible.append((v.copy_negate() if descending else v, tie, i, row))
    eligible.sort(key=lambda x: x[:3])
    selected = eligible if limit is None else eligible[:limit]
    return {'ranked': [x[3] for x in selected], 'missing_metric': missing}


def read_table(path, *, sheet=None, header_row=1, first_row=None, last_row=None,
               encoding='utf-8-sig', columns=None):
    """Stream a selected region. Formula results are not treated as raw observations."""
    if type(header_row) is not int or header_row < 1:
        raise ValueError('header_row is one-based')
    first = header_row + 1 if first_row is None else first_row
    if type(first) is not int or first <= header_row:
        raise ValueError('first_row must be after header_row')
    if last_row is not None and (type(last_row) is not int or last_row < first):
        raise ValueError('last_row must not precede first_row')
    if columns is not None:
        columns = sequence(columns)
        if not columns or any(type(c) is not int or c < 1 for c in columns):
            raise ValueError('columns must be one-based source positions')
    path = Path(path)
    workbook, stream = None, None
    rows, formula_cells, arrays = [], [], []
    headers, idx = None, None
    last_seen = 0
    try:
        if path.suffix.lower() == '.xlsx':
            import openpyxl
            from openpyxl.utils.cell import range_boundaries
            if tuple(int(x) for x in openpyxl.__version__.split('.')[:2]) < (3, 1):
                raise ImportError('XLSX reading requires openpyxl >= 3.1')
            if sheet is None:
                raise ValueError('select an explicit XLSX sheet')
            workbook = openpyxl.load_workbook(path, read_only=True, data_only=False, keep_links=False)
            worksheet = workbook[sheet]
            if last_row is not None and worksheet.max_row is not None and last_row > worksheet.max_row:
                raise ValueError('selected data range exceeds source')
            iterator = worksheet.iter_rows(max_row=last_row)
        elif path.suffix.lower() == '.csv':
            stream = path.open(encoding=encoding, newline='')
            iterator = csv.reader(stream, strict=True)
        else:
            raise ValueError('supported sources: CSV or XLSX')
        # Limit logical records; text decoding may still read ahead into buffered bytes.
        for line, original in enumerate(islice(iterator, last_row), 1):
            last_seen = line
            if workbook is not None:
                cells = original
                values = [c.value for c in cells]
                # Scan the selected row's full width: an array anchor can be outside chosen columns.
                for column, cell in enumerate(cells, 1):
                    value = cell.value
                    if getattr(cell, 'data_type', None) == 'f' and hasattr(value, 'ref'):
                        bounds = range_boundaries(value.ref)
                        arrays.append((bounds, getattr(value, 'text', None), value.ref))
            else:
                values = original
            if line == header_row:
                idx = list(range(len(values))) if columns is None else [c - 1 for c in columns]
                if any(i >= len(values) for i in idx):
                    raise ValueError('selected column exceeds header')
                headers = [str(values[i]).strip() if values[i] is not None else '' for i in idx]
                if not headers or any(not h for h in headers) or len(set(headers)) != len(headers):
                    raise ValueError('select unique nonempty headers explicitly')
            if line < first:
                continue
            if headers is None:
                raise ValueError('header row absent')
            output = {}
            for i, field in zip(idx, headers):
                value = values[i] if i < len(values) else None
                if workbook is not None:
                    array = next(((text, ref) for (c1, r1, c2, r2), text, ref in arrays
                                  if c1 <= i + 1 <= c2 and r1 <= line <= r2), None)
                    cell = cells[i] if i < len(cells) else None
                    if array is not None:
                        text, ref = array
                        formula_cells.append({'source_row': line, 'field': field,
                                              'formula': text, 'array_ref': ref})
                        value = None
                    elif getattr(cell, 'data_type', None) == 'f':
                        if not isinstance(value, str):
                            raise ValueError('unsupported XLSX formula type')
                        formula_cells.append({'source_row': line, 'field': field, 'formula': value})
                        value = None
                output[field] = value
            # Preserve selected records, including explicit missing and formula-only rows.
            rows.append({'source_row': line, 'values': output})
        if headers is None:
            raise ValueError('header row absent')
        if last_row is not None and last_seen < last_row:
            raise ValueError('selected data range exceeds source')
    finally:
        if workbook is not None:
            workbook.close()
        if stream is not None:
            stream.close()
    return {'source_path': str(path.resolve()), 'sheet': sheet, 'headers': headers,
            'rows': rows, 'formula_cells': formula_cells}


FUNCTIONS = {fn.__name__: fn for fn in (total, mean, ratio, change_pct, price_return,
              compound_return, group_comparison, weighted_return, breadth, rolling_mean, rank_rows)}


def argument_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate calculation argument key')
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError('JSON contains a non-finite number')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    reader = commands.add_parser('read')
    reader.add_argument('path')
    reader.add_argument('--sheet')
    reader.add_argument('--header-row', type=int, default=1)
    reader.add_argument('--first-row', type=int)
    reader.add_argument('--last-row', type=int)
    reader.add_argument('--columns', type=int, nargs='+')
    reader.add_argument('--encoding', default='utf-8-sig')
    calc = commands.add_parser('calc')
    calc.add_argument('operation', choices=FUNCTIONS)
    calc.add_argument('arguments', help='JSON object with named function arguments')
    args = vars(parser.parse_args())
    try:
        command = args.pop('command')
        if command == 'read':
            result = read_table(**args)
        else:
            parameters = json.loads(args['arguments'], object_pairs_hook=argument_object,
                                    parse_constant=reject_constant)
            if type(parameters) is not dict:
                raise ValueError('calculation arguments must be a JSON object')
            result = FUNCTIONS[args['operation']](**parameters)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False,
                         default=lambda value: value.isoformat() if isinstance(value, (dt.date, dt.datetime)) else str(value)))
        return 0
    except (ValueError, TypeError, OSError, LookupError, ImportError, OverflowError,
            BadZipFile, csv.Error, SyntaxError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
