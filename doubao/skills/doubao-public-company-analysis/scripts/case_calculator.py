#!/usr/bin/env python3
import argparse,json,statistics
from pathlib import Path
def number(value,name):
    if value is None:return None
    if isinstance(value,bool) or not isinstance(value,(int,float)):raise SystemExit(f"{name} must be numeric")
    return float(value)
def ratio(a,b,name):
    a=number(a,name);b=number(b,name)
    if a is None or b is None:return None
    if b==0:raise SystemExit(f"{name} denominator is zero")
    return a/b
def main():
    p=argparse.ArgumentParser();p.add_argument("input");p.add_argument("--pretty",action="store_true");a=p.parse_args()
    d=json.loads(Path(a.input).read_text(encoding="utf-8"));cur=d.get("current");prev=d.get("previous",{})
    if not isinstance(cur,dict):raise SystemExit("current is required")
    if not d.get("period") or not d.get("currency"):raise SystemExit("period and currency are required")
    out={"period":d["period"],"currency":d["currency"],"capabilities":{"can_analyze":True,"can_value":False}}
    out.update({"revenue_growth":ratio(cur.get("revenue"),prev.get("revenue"),"revenue_growth"),"gross_margin":ratio(cur.get("gross_profit"),cur.get("revenue"),"gross_margin"),"operating_margin":ratio(cur.get("operating_income"),cur.get("revenue"),"operating_margin"),"net_margin":ratio(cur.get("net_income"),cur.get("revenue"),"net_margin")})
    if out["revenue_growth"] is not None:out["revenue_growth"]-=1
    ocf=number(cur.get("operating_cash_flow"),"operating_cash_flow");capex=number(cur.get("capex"),"capex")
    out["free_cash_flow"]=None if ocf is None or capex is None else ocf-capex
    out["fcf_conversion"]=ratio(out["free_cash_flow"],cur.get("net_income"),"fcf_conversion")
    valuation=d.get("valuation",{});vout={}
    dcf=valuation.get("dcf") if isinstance(valuation,dict) else None
    if dcf:
        flows=[number(x,"projected_fcf") for x in dcf.get("projected_fcf",[])]
        rate=number(dcf.get("discount_rate"),"discount_rate");growth=number(dcf.get("terminal_growth"),"terminal_growth")
        if not flows or rate is None or growth is None or rate<=growth or rate<=-1:raise SystemExit("invalid DCF inputs")
        pv=sum(value/(1+rate)**year for year,value in enumerate(flows,1))
        terminal=flows[-1]*(1+growth)/(rate-growth)
        vout["dcf_enterprise_value"]=pv+terminal/(1+rate)**len(flows)
    comps=valuation.get("comps") if isinstance(valuation,dict) else None
    if comps:
        metric=number(comps.get("target_metric"),"target_metric");multiples=[number(x,"peer_multiple") for x in comps.get("peer_multiples",[])]
        if metric is None or metric<0 or not multiples or any(x<0 for x in multiples):raise SystemExit("invalid comps inputs")
        vout["comps_enterprise_value"]=metric*statistics.median(multiples)
        vout["peer_multiple_range"]=[min(multiples),max(multiples)]
    out["valuation"]=vout;out["capabilities"]["can_value"]=bool(vout)
    print(json.dumps(out,ensure_ascii=False,indent=2 if a.pretty else None));return 0
if __name__=="__main__":raise SystemExit(main())
