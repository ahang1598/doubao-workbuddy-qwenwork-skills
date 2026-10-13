#!/usr/bin/env python3
"""Deterministic share-class cost and disclosed-holding overlap helpers."""
from __future__ import annotations
import argparse, json

def holding_overlap(a: dict[str,float], b: dict[str,float]) -> float:
    return sum(min(a[k], b[k]) for k in a.keys() & b.keys())

def holding_cost(principal: float, years: float, annual: float, subscription: float=0, redemption: float=0, friction: float=0) -> dict:
    rate=annual*years+subscription+redemption+friction
    return {"rate":rate,"amount":principal*rate}

def main():
    p=argparse.ArgumentParser();p.add_argument("input");args=p.parse_args();d=json.load(open(args.input));
    if d["mode"]=="overlap": print(json.dumps({"overlap":holding_overlap(d["a"],d["b"])},indent=2))
    else: print(json.dumps(holding_cost(**d["params"]),indent=2))
if __name__=="__main__": main()
