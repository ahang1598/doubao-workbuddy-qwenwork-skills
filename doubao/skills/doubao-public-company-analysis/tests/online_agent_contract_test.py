#!/usr/bin/env python3
"""Ordinary research does not require a fixed search or audit pipeline."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from search_router import plan


def main():
    runtime=json.loads((ROOT/'config/runtime.json').read_text(encoding='utf-8'))
    loading=json.loads((ROOT/'config/loading-profile.json').read_text(encoding='utf-8'))
    routed=plan({'skill':'company-analysis-seed-finance','object_frozen':True,'needs_current_public_facts':True})
    assert routed['max_calls'] is None
    assert routed['max_calls_is_hard_limit'] is False
    assert routed['required_search_artifacts']==[]
    assert runtime['search_contract']['fixed_call_budget'] is False
    assert runtime['search_contract']['mandatory_claim_ledger'] is False
    assert all('online-agent-execution-contract.md' not in refs for refs in loading['mode_references'].values())
    print('PASS company research without fixed audit pipeline')


if __name__=='__main__':
    raise SystemExit(main())
