#!/usr/bin/env python3
"""Generate risk mitigation strategy based on assessment results.

Produces actionable strategy recommendations for identified risks.
"""
import json
import sys


def generate(assessment: dict) -> dict:
    """Generate mitigation strategy from assessment."""
    level = assessment.get("risk_level", "low")
    strategies = {
        "high": [
            "立即停止涉风险行为",
            "向律协报告并寻求指导",
            "审查所有在办案件是否存在同类风险",
            "建立内部合规审查机制",
        ],
        "medium": [
            "审查涉风险行为的具体情况",
            "加强执业规范培训",
            "建立风险预警机制",
        ],
        "low": [
            "保持合规意识",
            "定期自查执业行为",
        ],
    }
    return {
        "risk_level": level,
        "strategies": strategies.get(level, strategies["low"]),
        "priority": "urgent" if level == "high" else "normal",
    }


def main():
    if len(sys.argv) > 1:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)
    result = generate(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
