"""路由目标必须指向已上线 Skill。

历史缺陷：SKILL.md 的不适用清单与更深能力路由点名了 company-tearsheet、
earnings-analysis 等从未上线的 Skill，而收尾指令是"返回相邻任务然后停止"，
导致「给我一页小米速览」这类合理请求被路由到空地址后拒答。
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SHIPPED = {
    "company-analysis",
    "event-impact-analysis",
    "investment-opportunity-screening",
    "private-market-project-evaluation",
    "wealth-planning",
}

# 规划中但从未上线，不得出现在任何路由语境里
UNSHIPPED = [
    "company-tearsheet",
    "comparable-company-analysis",
    "dcf-valuation-modeling",
    "three-statement-forecasting",
    "earnings-analysis",
    "event-path-modeling",
    "catalyst-calendar",
    "macro-strategy",
    "regulatory-timeline-analysis",
    "universe-builder",
    "factor-backtesting",
    "watchlist-diff",
    "pair-trade-analysis",
    "lbo-analysis",
    "ic-memo",
    "cap-table-modeling",
    "commercial-due-diligence",
    "legal-tax-due-diligence",
    "retirement-monte-carlo",
    "personal-tax-planning",
    "estate-planning-intake",
    "insurance-needs-analysis",
]

ROUTING_VERBS = ["使用", "转向", "改用", "进入", "路由到", "交给", "请用"]


def test_no_routing_to_unshipped_skill():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for line in text.split("\n"):
        if line.lstrip().startswith(">") or "不得作为路由目标" in line:
            continue
        for name in UNSHIPPED:
            if name not in line:
                continue
            for verb in ROUTING_VERBS:
                pattern = rf"{verb}[^。；\n]{{0,12}}`?{re.escape(name)}`?"
                assert not re.search(pattern, line), (
                    f"{name} 未上线，不能作为路由目标：{line.strip()}"
                )


def test_out_of_scope_does_not_dead_end():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "不得把回答收尾在这五个之外的 Skill 名上" in text
    assert "无已上线 Skill 可承接" in text
    # 旧的一刀切停止指令不得复活
    assert "不适用时只返回正确相邻任务和下一步输入，然后停止。" not in text


def test_runtime_flags_declare_unshipped():
    cfg = json.loads((ROOT / "config" / "runtime.json").read_text(encoding="utf-8"))
    assert cfg["future_adjacent_skills_are_unshipped"] is True
    assert cfg["no_routing_to_unshipped_skills"] is True
    assert cfg["out_of_scope_degrades_in_skill_not_stop"] is True
    assert set(cfg["shipped_adjacent_skills"]) == SHIPPED
    overlap = set(cfg["future_adjacent_skills"]) & SHIPPED
    assert not overlap, f"future 与 shipped 不得重叠：{overlap}"


if __name__ == "__main__":
    test_no_routing_to_unshipped_skill()
    test_out_of_scope_does_not_dead_end()
    test_runtime_flags_declare_unshipped()
    print("routing_targets_test: OK")
