#!/usr/bin/env python3
"""Advise on documentation and record-keeping for risk mitigation.

Generates recommendations for what documentation should be maintained
to demonstrate compliance and mitigate future risk.
"""
import json
import sys


def advise(assessment: dict) -> dict:
    """Generate documentation advisory from assessment."""
    level = assessment.get("risk_level", "low")
    docs = {
        "high": [
            "风险事件完整记录",
            "律协沟通记录",
            "客户告知书及签收回执",
            "内部审查报告",
            "整改措施及执行记录",
        ],
        "medium": [
            "风险行为审查记录",
            "客户沟通记录",
            "培训记录",
        ],
        "low": [
            "定期自查记录",
            "合规学习记录",
        ],
    }
    return {
        "risk_level": level,
        "recommended_documents": docs.get(level, docs["low"]),
        "retention_period": "5年" if level == "high" else "3年",
    }


def main():
    if len(sys.argv) > 1:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)
    result = advise(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
