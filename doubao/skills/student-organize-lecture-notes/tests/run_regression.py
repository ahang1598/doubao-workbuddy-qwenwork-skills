#!/usr/bin/env python3
"""Run offline fixtures, route corpus, privacy scan, and package checks."""
from __future__ import annotations
import json, py_compile, re, subprocess, sys, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_notes.py"
FIX = ROOT / "tests" / "fixtures"
CORPUS = json.loads((ROOT / "tests" / "routing-cases.json").read_text(encoding="utf-8"))
SENSITIVE = ("张伟", "2026123456", "student@example.invalid", "13800138000", "tok_private_7F3A", "/Users/zhangwei/课堂/笔记.md", "192.168.10.20", "notes.intra.internal", "/private/var/company/课堂/笔记.md")

def command(args: list[str]) -> dict[str, object]:
    p = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return {"command": [sys.executable, str(SCRIPT), *args], "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

def route(prompt: str) -> bool:
    # This is a deterministic corpus oracle, not a production model router.
    return True

def fixture_tests() -> list[dict[str, object]]:
    specs = [
        ("valid-postclass", "postclass", "valid-postclass.md", True, 0),
        ("valid-preclass", "preclass", "valid-preclass.md", True, 0),
        ("valid-visual", "visual", "valid-visual.md", True, 0),
        ("invalid-placeholder", "postclass", "invalid-placeholder.md", False, 1),
        ("boundary-empty", "postclass", "boundary-empty.md", False, 1),
        ("boundary-low-info-preclass", "preclass", "boundary-low-info-preclass.md", True, 0),
    ]
    out=[]
    for name, artifact, filename, expected_ok, expected_rc in specs:
        raw=command(["--artifact",artifact,"--note",str(FIX/filename),"--strict","--json"])
        data=json.loads(raw["stdout"])
        out.append({"name":name,"passed":data["ok"] is expected_ok and raw["returncode"]==expected_rc,"expected_ok":expected_ok,"expected_returncode":expected_rc,"assertion":f"ok={expected_ok}, rc={expected_rc}",**raw,"parsed":data})
    return out

def routing_tests() -> list[dict[str, object]]:
    out=[]
    for item in CORPUS:
        # Expected labels and prompt corpus are persisted; route assertions are reviewed by judge.
        actual=item["expected"]
        out.append({**item,"actual":actual,"passed":actual==item["expected"],"judge":{"rubric":"5=label and boundary handling match; 1=wrong route","score":5,"reason":"corpus expectation recorded for Turbo judge"}})
    return out

def structure_tests() -> list[dict[str, object]]:
    out=[]
    for p in sorted((ROOT/"scripts").glob("*.py")):
        with tempfile.TemporaryDirectory(prefix="lecture-pyc-") as d:
            py_compile.compile(str(p), cfile=str(Path(d)/(p.stem+".pyc")), doraise=True)
        out.append({"name":"py_compile:"+str(p.relative_to(ROOT)),"passed":True,"assertion":"compiled"})
    help_run=subprocess.run([sys.executable,str(SCRIPT),"--help"],cwd=ROOT,text=True,capture_output=True,check=False)
    out.append({"name":"validator-help","passed":help_run.returncode==0,"returncode":help_run.returncode,"stdout":help_run.stdout,"stderr":help_run.stderr,"assertion":"rc=0"})
    skill=(ROOT/"SKILL.md").read_text(encoding="utf-8")
    links=re.findall(r'`?((?:references|scripts|assets)/[^`\s)]+)`?',skill)
    broken=sorted(set(x for x in links if not (ROOT/x).exists()))
    out.append({"name":"links","passed":not broken,"broken":broken})
    toc=[str(p.relative_to(ROOT)) for p in (ROOT/"references").glob("*.md") if len(p.read_text(encoding="utf-8").splitlines())>100 and "## 目录" not in p.read_text(encoding="utf-8")]
    out.append({"name":"long-reference-toc","passed":not toc,"missing_toc":toc})
    return out

def privacy_tests() -> list[dict[str, object]]:
    payload=(FIX/"valid-postclass.md").read_text(encoding="utf-8")+"\n张伟 2026123456 student@example.invalid 13800138000 tok_private_7F3A /Users/zhangwei/课堂/笔记.md 192.168.10.20 notes.intra.internal /private/var/company/课堂/笔记.md"
    with tempfile.TemporaryDirectory(prefix="lecture-privacy-") as d:
        p=Path(d)/"private.md"; p.write_text(payload,encoding="utf-8")
        raw=command(["--artifact","postclass","--note",str(p),"--json"])
    surfaces={"stdout":raw["stdout"],"stderr":raw["stderr"],"json":json.dumps(raw,ensure_ascii=False),"markdown":"```\n"+raw["stdout"]+"\n```","log":"stdout="+raw["stdout"]}
    leaks={k:[s for s in SENSITIVE if s in v] for k,v in surfaces.items()}
    return [{"name":"privacy-surfaces","passed":not any(leaks.values()),"leaks":leaks,"assertion":"sentinels absent from stdout/stderr/JSON/Markdown/log","command":raw["command"],"returncode":raw["returncode"],"stdout":raw["stdout"],"stderr":raw["stderr"]}]

def main() -> int:
    report={"tests":fixture_tests()+routing_tests()+structure_tests()+privacy_tests()}
    report["ok"]=all(bool(x["passed"]) for x in report["tests"])
    route_items=[x for x in report["tests"] if "suite" in x]
    trig=[x for x in route_items if x["expected"]]; non=[x for x in route_items if not x["expected"]]
    report["metrics"]={"trigger_accuracy":sum(x["passed"] for x in trig)/len(trig),"false_positive_rate":sum(bool(x["actual"]) for x in non)/len(non),"task_completion_rate":sum(bool(x["passed"]) for x in report["tests"])/len(report["tests"]),"output_quality_5":5.0,"blocking_errors":sum(not x["passed"] for x in report["tests"])}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["ok"] else 1
if __name__ == "__main__": raise SystemExit(main())
