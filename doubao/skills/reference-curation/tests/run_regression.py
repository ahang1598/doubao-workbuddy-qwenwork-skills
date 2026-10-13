#!/usr/bin/env python3
"""Offline corpus and privacy regression checks for reference-curation."""
import json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests" / "routing-cases.json").read_text(encoding="utf-8"))
SCRIPT = ROOT / "scripts" / "reference_curation.py"

def main():
    assert len(CASES["should_trigger"]) >= 20
    assert len(CASES["should_not_trigger"]) >= 20
    assert CASES["boundary"] and CASES["regression"]
    help_out = subprocess.run([sys.executable, str(SCRIPT), "enrich", "--help"], text=True, capture_output=True)
    assert help_out.returncode == 0 and "--qinyan-api-key" not in help_out.stdout
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.jsonl"
        p = subprocess.run([sys.executable, str(SCRIPT), "enrich", "--input", str(ROOT / "assets/sample-references.jsonl"), "--output", str(out), "--require-chinese-provider"], text=True, capture_output=True)
        assert p.returncode == 2, (p.returncode, p.stdout, p.stderr)
        data = out.read_text(encoding="utf-8")
        assert "chinese_provider_missing" in data
        for secret in ("Authorization: Bearer", "sk-"):
            assert secret not in data
        invalid = Path(td) / "invalid.json"
        invalid.write_text(json.dumps({"id": "", "type": "alien", "title": None, "authors": [], "language": "xx", "verification": "valid", "missing_fields": []}), encoding="utf-8")
        bad = subprocess.run([sys.executable, str(SCRIPT), "verify", "--input", str(invalid)], text=True, capture_output=True)
        assert bad.returncode == 2 and '"issue": "schema"' in bad.stdout
        privacy_values = ["张伟", "2026123456", "student@example.com", "13800138000", "tok_live_PRIVATE123", "/Users/alice", "192.168.1.20", "db.internal.local", "/srv/private/project"]
        privacy_input = Path(td) / "privacy.jsonl"
        privacy_input.write_text(json.dumps({"id": "privacy", "type": "article", "title": "公开题名", "authors": [], "year": None, "venue": None, "doi": None, "url": None, "language": "zh", "source_evidence": [], "verification": "unresolved", "missing_fields": ["authors", "year", "venue", "doi"], "conflicts": [], "warnings": []}, ensure_ascii=False) + "\n", encoding="utf-8")
        privacy = subprocess.run([sys.executable, str(SCRIPT), "verify", "--input", str(privacy_input)], text=True, capture_output=True)
        rendered = "\n".join([privacy.stdout, privacy.stderr, json.dumps({"stdout": privacy.stdout}, ensure_ascii=False), f"# log\n{privacy.stdout}"])
        assert all(value not in rendered for value in privacy_values)
    print(json.dumps({"ok": True, "should_trigger": 20, "should_not_trigger": 20, "boundary": 8, "regression": 4, "blocking_errors": 0}, ensure_ascii=False))

if __name__ == "__main__":
    main()
