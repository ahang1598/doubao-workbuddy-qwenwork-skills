#!/usr/bin/env python3
import json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
def run(*args):return subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True)
def main():
    facts=ROOT/"schemas/facts.example.json";config=json.loads((ROOT/"config/runtime.json").read_text(encoding="utf-8"))
    capabilities=ROOT/"schemas/capabilities.test.json"
    result=run(ROOT/"scripts/validate_facts.py",facts,"--capabilities-out",capabilities);assert result.returncode==0,result.stdout+result.stderr
    tool=ROOT/config["deterministic_tool"];name=tool.name
    example_dir=ROOT/"schemas/deterministic-tool-example";example_file=ROOT/"schemas/deterministic-tool.example.json"
    if name=="company_cashflow_bridge.py":
        command=[tool,example_dir]
    elif name=="screening_engine.py":
        command=[tool,"--candidates",example_dir/"candidates.csv","--config",example_dir/"screening_config.json","--theme-evidence",example_dir/"theme_evidence.json","--dictionary",example_dir/"data_dictionary.json"]
    else:
        command=[tool,example_file,"--pretty"]
    result=run(*command);assert result.returncode==0,result.stdout+result.stderr
    tool_result=json.loads(result.stdout);assert isinstance(tool_result,dict) and tool_result
    expected={"company_cashflow_bridge.py":"bridges","screening_engine.py":"funnel","private_market_engine.py":"metrics","wealth_planning_engine.py":"runway","event_claim_engine.py":"event_capability_gate"}[name]
    assert expected in tool_result,(name,tool_result.keys())
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp);data=json.loads(facts.read_text(encoding="utf-8"));data["claims"][1]["input_claims"]=["missing_claim"]
        bad=temp/"bad-facts.json";bad.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        assert run(ROOT/"scripts/validate_facts.py",bad).returncode!=0
        evals=[{"id":"smoke-response","type":"positive","prompt":"smoke","assertions":[{"type":"must_include","value":"PASS_MARKER"}]}]
        eval_path=temp/"evals.json";eval_path.write_text(json.dumps(evals),encoding="utf-8")
        response_dir=temp/"responses";response_dir.mkdir();response=response_dir/"smoke-response.md";response.write_text("PASS_MARKER",encoding="utf-8")
        assert run(ROOT/"scripts/eval_harness.py",eval_path,"--responses-dir",response_dir).returncode==0
        response.write_text("missing marker",encoding="utf-8")
        assert run(ROOT/"scripts/eval_harness.py",eval_path,"--responses-dir",response_dir).returncode!=0
        mode=data["meta"]["mode"];sections=config["modes"][mode]["required_sections"];body=["# 测试报告"]
        for spec in sections:
            title=spec["aliases"][0];content="这是有实质内容的测试段落，说明来源、假设、机制与局限。"
            if spec.get("fact_binding"):content+=" {fact:example_fact}"
            body+=["",f"## {title}","",content]
        body+=["","本报告仅供研究参考，不构成投资建议。"]
        report=temp/"report.md";report.write_text("\n".join(body),encoding="utf-8")
        result=run(ROOT/"scripts/finalize_report.py",report,facts);assert result.returncode==0,result.stdout+result.stderr
        assert report.with_name("report-display.md").exists()
        assert report.with_name("report-manifest.json").exists()
        assert not report.with_suffix(".docx").exists()
    print("PASS event-impact-analysis V3");return 0
if __name__=="__main__":raise SystemExit(main())
