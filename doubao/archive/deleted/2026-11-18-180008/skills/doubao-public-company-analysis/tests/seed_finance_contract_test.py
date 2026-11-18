#!/usr/bin/env python3
"""Financial data can support standard fields without replacing company disclosures."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from search_router import plan


def main():
    runtime=json.loads((ROOT/'config/runtime.json').read_text(encoding='utf-8'))
    routed=plan({'skill':'company-analysis-seed-finance','object_frozen':True,'needs_current_public_facts':True})
    assert 'seed_finance_search' in routed['tool_order']
    assert 'general_search' in routed['tool_order']
    assert routed['max_calls_is_hard_limit'] is False
    assert runtime['search_contract']['routing_policy']=='query_facts_needed_for_current_decision'
    source=(ROOT/'references/source-policy.md').read_text(encoding='utf-8')
    assert '标准价格、股本和财务字段' in source
    assert '公司 IR' in source
    print('PASS public financial data roles')


if __name__=='__main__':
    raise SystemExit(main())
