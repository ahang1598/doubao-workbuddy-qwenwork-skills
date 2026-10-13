#!/usr/bin/env python3
"""Run deterministic contract, routing-count, privacy, and historical regressions."""
import json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

def run(name):
    return subprocess.run([PY, str(ROOT / "scripts/analyze_course_options.py"), str(ROOT / "tests/fixtures" / name)], text=True, capture_output=True)

def main():
    expected = {"positive.json": 0, "negative-invalid-date.json": 2, "boundary-stale-capacity.json": 0, "regression-same-course-sections.json": 0}
    results = {name: run(name) for name in expected}
    for name, code in expected.items():
        assert results[name].returncode == code, (name, results[name].stdout, results[name].stderr)
    assert "合法 YYYY-MM-DD" in results["negative-invalid-date.json"].stderr
    boundary = json.loads(results["boundary-stale-capacity.json"].stdout)
    assert boundary["course_results"][0]["eligible"] is False
    assert any("缺少已核验且当前有效" in x for x in boundary["course_results"][0]["blockers"])
    reg = json.loads(results["regression-same-course-sections.json"].stdout)
    assert len(reg["course_results"]) == 2
    manifest = json.loads((ROOT / "tests/routing-manifest.json").read_text(encoding="utf-8"))
    counts = {}
    for row in manifest: counts[row["category"]] = counts.get(row["category"], 0) + 1
    assert counts.get("should_trigger", 0) >= 20 and counts.get("should_not_trigger", 0) >= 20
    assert any(row.get("qid") == "R005" and row.get("expected") == "是" for row in manifest)
    private = ["张"+"伟", "2026"+"123456", "student"+"@example.com", "138"+"0013"+"8000", "tok_live_"+"PRIVATE123", "/Users/"+"alice", "192.168."+"1.20", "db.internal."+"local", "/srv/private/"+"project"]
    packet = json.loads((ROOT / "tests/fixtures/positive.json").read_text(encoding="utf-8")); packet["private_note"] = "|".join(private)
    with tempfile.TemporaryDirectory(prefix="course-privacy-") as td:
        p = Path(td) / "privacy.json"; p.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run([PY, str(ROOT / "scripts/analyze_course_options.py"), str(p)], text=True, capture_output=True)
        rendered = proc.stdout + proc.stderr + json.dumps({"stdout": proc.stdout, "stderr": proc.stderr}, ensure_ascii=False) + "\n# markdown\n" + proc.stdout + "\n# log\n" + proc.stderr
    assert proc.returncode == 0 and all(v not in rendered for v in private)
    privacy_fixture = ROOT / "tests/fixtures/privacy-small-class.txt"
    assert privacy_fixture.exists() and "禁止复述" in privacy_fixture.read_text(encoding="utf-8")
    print(json.dumps({"ok": True, "fixtures": 5, "routing": counts, "privacy_types": 9, "privacy_channels": ["stdout", "stderr", "json", "markdown", "log"], "blocking_errors": 0}, ensure_ascii=False))

if __name__ == "__main__": main()
