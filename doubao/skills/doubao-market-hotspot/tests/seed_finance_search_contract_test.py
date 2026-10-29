#!/usr/bin/env python3
"""Price data can inform markets; policy status requires an appropriate source."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from event_runtime_guard import guard
from search_router import plan


def main():
    runtime=json.loads((ROOT/'config/runtime.json').read_text(encoding='utf-8'))
    routed=plan({'skill':'event-impact-analysis','object_frozen':True,'event_type':'regulatory','needs_public_rules':True})
    assert routed['source_order'][0]=='issuing_authority'
    assert 'market_price' in routed['seed_finance_policy']['allowed_scope']
    assert runtime['seed_finance_search']['library_result_is_primary'] is False
    assert routed['max_calls_is_hard_limit'] is False
    case={'status':'completed','gates':{'primary_source_gate_passed':True,'semantic_gate_passed':True},'search':{'mode':'optional'},'claims':[{'id':'event','claim_type':'event_identity','critical':True,'supported':True,'source_ids':['official']},{'id':'status','claim_type':'event_status','critical':True,'supported':True,'source_ids':['official']}],'market_evidence':[]}
    assert guard(case)['can_assess_priced_in'] is False
    print('PASS event source and market baseline boundaries')


if __name__=='__main__':
    raise SystemExit(main())
