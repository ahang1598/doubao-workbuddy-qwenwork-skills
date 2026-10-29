#!/usr/bin/env python3
"""Default event research has no mandatory audit pipeline or search quota."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from search_router import plan


def main():
    runtime=json.loads((ROOT/'config/runtime.json').read_text(encoding='utf-8'))
    loading=json.loads((ROOT/'config/loading-profile.json').read_text(encoding='utf-8'))
    routed=plan({'skill':'event-impact-analysis','object_frozen':True,'event_type':'regulatory','needs_current_public_facts':True})
    assert routed['max_calls'] is None
    assert routed['max_calls_is_hard_limit'] is False
    assert routed['repair_calls_reserved_min']==0
    assert routed['query_stages']==[]
    assert not any('claim ledger' in item.lower() for item in routed['requirements'])
    assert runtime['search_contract']['fixed_call_budget'] is False
    assert runtime['search_contract']['mandatory_claim_ledger'] is False
    assert all('online-agent-execution-contract.md' not in refs for refs in loading['mode_references'].values())
    print('PASS event research without audit pipeline')


if __name__=='__main__':
    raise SystemExit(main())
