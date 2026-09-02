#!/usr/bin/env python3
"""Scan for lawyer practice risk indicators in case data.

Identifies potential risk factors across 7 categories: conflict of interest,
evidence tampering, unauthorized practice, fee violations, confidentiality
breach, procedural violation, and professional misconduct.
"""
import json
import sys


RISK_CATEGORIES = [
    "conflict_of_interest",
    "evidence_tampering",
    "unauthorized_practice",
    "fee_violation",
    "confidentiality_breach",
    "procedural_violation",
    "professional_misconduct",
]


def scan(data: dict) -> dict:
    """Scan input data for risk indicators."""
    findings = []
    actions = data.get("actions", [])
    for action in actions:
        action_text = str(action).lower()
        for cat in RISK_CATEGORIES:
            if any(kw in action_text for kw in _keywords_for(cat)):
                findings.append({"category": cat, "source": action, "severity": "medium"})
    return {"total_findings": len(findings), "findings": findings}


def _keywords_for(category: str) -> list:
    keywords = {
        "conflict_of_interest": ["利益冲突", "双重代理", "前客户"],
        "evidence_tampering": ["隐匿证据", "毁灭证据", "伪造"],
        "unauthorized_practice": ["越权", "无权代理"],
        "fee_violation": ["风险代理", "违规收费"],
        "confidentiality_breach": ["泄露", "保密", "隐私"],
        "procedural_violation": ["程序违法", "违规会见"],
        "professional_misconduct": ["诱导", "串供", "虚假"],
    }
    return keywords.get(category, [])


def main():
    if len(sys.argv) > 1:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)
    result = scan(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
