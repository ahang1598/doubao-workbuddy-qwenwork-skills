"""Execute explicit AND conditions and lexicographic ranking on normalized values.

No source lookup, business classification, investment rating or factual validation.
See references/script-api.md. Use a UTF-8 JSON file or '-' for stdin.
"""
from itertools import groupby
import sys
from financial_checks import number, run_cli

OPERATORS = {
    '>=': lambda a, b: a >= b, '>': lambda a, b: a > b,
    '<=': lambda a, b: a <= b, '<': lambda a, b: a < b,
    '==': lambda a, b: a == b,
}


def inspect(payload):
    if not isinstance(payload, dict):
        raise ValueError('input must be an object')
    if set(payload) - {'rules', 'rows', 'sort'}:
        raise ValueError('only rules, rows and sort are supported; conditions use AND')
    rules, rows = payload.get('rules'), payload.get('rows')
    sort = payload.get('sort', [])
    if not isinstance(rules, list) or not 1 <= len(rules) <= 64:
        raise ValueError('provide 1 to 64 AND rules')
    if not isinstance(rows, list) or len(rows) > 10000:
        raise ValueError('provide at most 10000 rows')
    if not isinstance(sort, list) or len(sort) > 10:
        raise ValueError('provide at most 10 sort keys')
    ids = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) - {
            'id', 'field', 'operator', 'threshold', 'all_values', 'expected_count'
        }:
            raise ValueError('invalid rule schema')
        if not isinstance(rule.get('id'), str) or not rule['id'] or rule['id'] in ids:
            raise ValueError('rule IDs must be nonempty and unique')
        ids.add(rule['id'])
        if not isinstance(rule.get('field'), str) or not rule['field']:
            raise ValueError('rule field is required')
        if rule.get('operator') not in OPERATORS:
            raise ValueError('unsupported comparison operator')
        number(rule.get('threshold'))
        if not isinstance(rule.get('all_values', False), bool):
            raise ValueError('all_values must be boolean')
        if rule.get('all_values', False):
            count = rule.get('expected_count')
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 100:
                raise ValueError('all_values requires expected_count between 1 and 100')
        elif 'expected_count' in rule:
            raise ValueError('expected_count is only valid with all_values')
    for key in sort:
        if not isinstance(key, dict) or set(key) != {'field', 'descending'}:
            raise ValueError('sort keys require field and descending')
        if not isinstance(key['field'], str) or not key['field'] or not isinstance(key['descending'], bool):
            raise ValueError('invalid sort field or direction')
    if len({key['field'] for key in sort}) != len(sort):
        raise ValueError('duplicate sort field')
    codes, decisions, passing = set(), [], []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('code'), str) or not row['code']:
            raise ValueError('each row requires a string code')
        if row['code'] in codes:
            raise ValueError('duplicate code; resolve securities and company grain before screening')
        codes.add(row['code'])
        values = row.get('values')
        if not isinstance(values, dict):
            raise ValueError('row values must be an object')
        conditions, failed, unknown = {}, [], []
        for rule in rules:
            value = values.get(rule['field'])
            items = value if rule.get('all_values', False) else [value]
            if rule.get('all_values', False):
                if value is None:
                    items = [None] * rule['expected_count']
                elif not isinstance(value, list) or len(value) != rule['expected_count']:
                    raise ValueError('all_values length must match expected_count')
            outcomes = [None if item is None else OPERATORS[rule['operator']](
                number(item), number(rule['threshold'])) for item in items]
            state = 'fail' if False in outcomes else 'unknown' if None in outcomes else 'pass'
            conditions[rule['id']] = state
            if state == 'fail':
                failed.append(rule['id'])
            if None in outcomes:
                unknown.append(rule['id'])
        state = 'fail' if failed else 'unknown' if unknown else 'pass'
        decisions.append({'code': row['code'], 'status': state, 'conditions': conditions,
                          'failed_rules': failed, 'unknown_rules': unknown})
        if state == 'pass':
            passing.append(row)
    for row in passing:
        for key in sort:
            value = row['values'].get(key['field'])
            if value is not None:
                number(value)
    missing_sort, ranked = [], []

    def rank_group(group, depth, first_rank):
        if len(group) <= 1 or depth == len(sort):
            ranked.extend({'code': row['code'], 'rank': first_rank} for row in group)
            return
        key = sort[depth]
        field = key['field']
        missing = [row for row in group if row['values'].get(field) is None]
        if missing:
            missing_sort.extend({'code': row['code'], 'field': field} for row in missing)
            return
        def value(row):
            return number(row['values'][field])
        ordered = sorted(group, key=value, reverse=key['descending'])
        for _, members in groupby(ordered, key=value):
            tied = list(members)
            rank_group(tied, depth + 1, first_rank)
            first_rank += len(tied)

    if sort:
        rank_group(passing, 0, 1)
    return {
        'decisions': decisions, 'passing_codes': [r['code'] for r in passing],
        'counts': {s: sum(d['status'] == s for d in decisions) for s in ('pass', 'fail', 'unknown')},
        'ranked_passing': [] if missing_sort else ranked, 'missing_sort_values': missing_sort,
        'determined_ranks': ranked,
        'ranking_status': 'unknown' if missing_sort else 'complete' if sort else 'not_requested',
        'note': 'Normalized input diagnostics only; no source or accounting verification.',
    }


if __name__ == '__main__':
    sys.exit(run_cli(inspect, __doc__))
