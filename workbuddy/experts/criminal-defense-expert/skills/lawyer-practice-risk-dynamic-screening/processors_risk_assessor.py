#!/usr/bin/env python3
"""Assess and grade identified risks from the risk scanner.

Takes scan findings and produces a graded risk assessment with
recommendations for mitigation.
"""
import json
import sys


SEVERITY_SCORES = {"high": 3, "medium": 2, "low": 1}


def assess(scan_result: dict) -> dict:
    """Assess scan findings and produce graded report."""
    findings = scan_result.get("findings", [])
    total_score = sum(SEVERITY_SCORES.get(f.get("severity", "low"), 1) for f in findings)
    
    if total_score >= 6:
        level = "high"
    elif total_score >= 3:
        level = "medium"
    else:
        level = "low"
    
    return {
        "risk_level": level,
        "total_score": total_score,
        "finding_count": len(findings),
        "recommendation": _recommendation(level),
    }


def _recommendation(level: str) -> str:
    recs = {
        "high": "存在高风险执业行为，建议立即停止相关行为并咨询律协",
        "medium": "存在中等风险，建议审查相关行为并采取预防措施",
        "low": "风险较低，建议保持合规意识",
    }
    return recs.get(level, "")


def main():
    if len(sys.argv) > 1:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)
    result = assess(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
