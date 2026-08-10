#!/usr/bin/env python3
import argparse,json
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument("input");p.add_argument("--pretty",action="store_true");a=p.parse_args()
    d=json.loads(Path(a.input).read_text(encoding="utf-8"));status=str(d.get("event_status","")).lower();scenarios=d.get("scenarios",[])
    if status in {"rumor","unconfirmed","传闻","未确认"}:
        out={"capabilities":{"can_quantify_event":False},"event_status":status,"reason":"unconfirmed events cannot enter probability-weighted return calculations","scenario_names":[s.get("name") for s in scenarios]}
        print(json.dumps(out,ensure_ascii=False,indent=2 if a.pretty else None));return 0
    if status not in {"confirmed","official","已确认","正式"}:raise SystemExit("event_status must be confirmed or unconfirmed")
    current=float(d["current_value"])
    if current<=0 or not scenarios:raise SystemExit("positive current_value and scenarios required")
    rows=[];probability_sum=0;expected_terminal=0;horizons=set()
    for scenario in scenarios:
        probability=float(scenario["probability"]);terminal=float(scenario["terminal_value"]);years=float(scenario["years"])
        if not 0<=probability<=1 or terminal<0 or years<=0:raise SystemExit("invalid scenario")
        holding=terminal/current-1;annualized=(terminal/current)**(1/years)-1 if terminal>0 else -1
        rows.append({"name":scenario["name"],"probability":probability,"years":years,"terminal_value":terminal,"holding_period_return":holding,"annualized_return":annualized})
        probability_sum+=probability;expected_terminal+=probability*terminal;horizons.add(years)
    if abs(probability_sum-1)>1e-6:raise SystemExit("probabilities must sum to 1")
    out={"capabilities":{"can_quantify_event":True},"event_status":status,"probability_sum":probability_sum,"expected_terminal_value":expected_terminal,"expected_holding_period_return":expected_terminal/current-1 if len(horizons)==1 else None,"aggregation_note":"returns are not aggregated when scenario horizons differ","scenarios":rows}
    print(json.dumps(out,ensure_ascii=False,indent=2 if a.pretty else None));return 0
if __name__=="__main__":raise SystemExit(main())
