"""Compute threshold scenarios, near misses and sequential funnels from one pool.

Input uses the normalized rules/rows/sort schema in references/script-api.md.
No evidence ledger, artifact inspection, network access or output file writes.
"""
import sys
from financial_checks import number, run_cli
from screening_checks import inspect as screen


def inspect(payload):
    if not isinstance(payload, dict) or set(payload) - {'rules', 'rows', 'sort', 'scenarios'}:
        raise ValueError('only rules, rows, sort and scenarios are supported')
    # The existing numeric engine owns rule, row, code and sort input protection.
    baseline = screen({k: payload[k] for k in ('rules', 'rows', 'sort') if k in payload})
    rules, rows = payload['rules'], payload['rows']
    sort = payload.get('sort', [])
    scenarios = payload.get('scenarios', [])
    if not isinstance(scenarios, list) or len(scenarios) > 16:
        raise ValueError('provide at most 16 threshold scenarios')

    def enrich(result, current_rules):
        decisions = result['decisions']
        result['near_miss_codes'] = [d['code'] for d in decisions
                                     if len(d['failed_rules']) == 1 and not d['unknown_rules']]
        remaining = list(decisions)
        funnel = []
        for rule in current_rules:
            states = {state: [d for d in remaining if d['conditions'][rule['id']] == state]
                      for state in ('pass', 'fail', 'unknown')}
            funnel.append({'rule': rule['id'], 'before': len(remaining),
                           'removed_fail': len(states['fail']),
                           'removed_unknown': len(states['unknown']),
                           'remaining': len(states['pass'])})
            remaining = states['pass']
        result['funnel'] = funnel
        result['independent_rule_counts'] = {
            rule['id']: {state: sum(d['conditions'][rule['id']] == state for d in decisions)
                         for state in ('pass', 'fail', 'unknown')} for rule in current_rules}
        return result

    results = {'baseline': enrich(baseline, rules)}
    ids = {r['id'] for r in rules}
    for scenario in scenarios:
        if not isinstance(scenario, dict) or set(scenario) != {'id', 'thresholds'}:
            raise ValueError('a scenario requires id and threshold changes')
        sid, changes = scenario['id'], scenario['thresholds']
        if not isinstance(sid, str) or not sid.strip() or sid in results:
            raise ValueError('scenario IDs must be nonempty and unique')
        if not isinstance(changes, dict) or not changes or not set(changes) <= ids:
            raise ValueError('change thresholds of existing rule IDs only')
        for value in changes.values():
            number(value)
        new_rules = [{**r, 'threshold': changes.get(r['id'], r['threshold'])} for r in rules]
        result = enrich(screen({'rules': new_rules, 'rows': rows, 'sort': sort}), new_rules)
        old, new = set(baseline['passing_codes']), set(result['passing_codes'])
        result['changes'] = {'added': sorted(new-old), 'removed': sorted(old-new)}
        results[sid] = result
    return {'results': results,
            'note': 'Same supplied pool and normalized definitions; AND conditions only. '
                    'Facts, disclosure scope, source timing and accounting meaning are not inferred.'}


if __name__ == '__main__':
    sys.exit(run_cli(inspect, __doc__))
