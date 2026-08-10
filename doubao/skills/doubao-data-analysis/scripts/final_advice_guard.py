#!/usr/bin/env python3
"""Reject numeric directives or unsupported future targets in a draft answer.

This validator checks generic recommendation language. It does not contain
domain entities, case values, expected answers, or platform-specific terms.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


NUMBER = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:%|％|元|美元|天|周|小时|次|单)|"
    r"[$¥￥]\s*\d+(?:\.\d+)?|"
    r"\d+(?:\.\d+)?\s*(?:[-~～至]\s*\d+(?:\.\d+)?)\s*(?:%|％))",
    re.IGNORECASE,
)
CONTROL_ACTION = re.compile(
    r"(?:提价|降价|上调|下调|调高|调低|增加竞价|降低竞价|"
    r"增加预算|降低预算|调价|改价|设为|调整到|"
    r"\bincrease\b|\bdecrease\b|\braise\b|\blower\b|\bset\s+(?:to|at)\b)",
    re.IGNORECASE,
)
FUTURE_TARGET = re.compile(
    r"(?:预计|预期|目标|恢复至|回升至|提升至|下降至|达到|控制在|"
    r"维持在|稳定在|将在|将会|"
    r"\bforecast\b|\bexpect(?:ed)?\b|\btarget\b|\brecover\b)",
    re.IGNORECASE,
)
BID_STATE_CLAIM = re.compile(
    r"(?:(?:竞价|出价|预算|\bbid\b).{0,10}(?:偏低|偏高|过低|过高|不足|太低|太高)|"
    r"(?:偏低|偏高|过低|过高|不足|太低|太高).{0,10}(?:竞价|出价|预算|\bbid\b))",
    re.IGNORECASE,
)
UNCERTAINTY = re.compile(
    r"(?:未知|待核验|待验证|假设|可能|无法判断|不能判断|数据不足|证据不足|"
    r"\bunknown\b|\bhypothesis\b|\bverify\b|\buncertain\b)",
    re.IGNORECASE,
)
IMMEDIATE = re.compile(r"(?:立即|马上|直接|当日|第\s*1\s*天)", re.IGNORECASE)
REDUCTION = re.compile(
    r"(?:否定|删除|移除|停投|暂停|关停|削减|降价|降低竞价|下调竞价|"
    r"\bnegative\b|\bremove\b|\bdelete\b|\bpause\b|\bstop\b)",
    re.IGNORECASE,
)
PLATFORM_MECHANISM = re.compile(
    r"(?:质量分|内部权重|算法权重|学习期|流量惩罚|账户权重|"
    r"\bquality\s+score\b|\blearning\s+phase\b)",
    re.IGNORECASE,
)
CAUSAL_WORD = re.compile(
    r"(?:导致|造成|拉低|抑制|拖累|因此|所以|使得|从而|"
    r"\bcause(?:s|d)?\b|\blead(?:s)?\s+to\b|\btherefore\b)",
    re.IGNORECASE,
)


def validate(draft: str, plan: dict) -> list[str]:
    errors: list[str] = []
    context = plan.get("context") or {}
    actual_config_known = context.get("actual_config_known") is True
    response_type = str(context.get("response_evidence_type") or "none").lower()
    mechanism_evidence = context.get("platform_mechanism_evidence")
    conditional_reduction = any(
        isinstance(action, dict)
        and str(action.get("execution_status") or "").lower() == "conditional"
        and str(action.get("impact_direction") or "").lower()
        in {"decrease", "remove"}
        for action in (plan.get("actions") or [])
    )

    for line_no, line in enumerate(draft.splitlines(), start=1):
        compact = line.strip()
        if not compact:
            continue
        if (
            not actual_config_known
            and BID_STATE_CLAIM.search(compact)
            and not UNCERTAINTY.search(compact)
        ):
            errors.append(
                f"line {line_no}: 实际配置未知，不能断言竞价、出价或预算偏高/偏低: "
                f"{compact[:120]}"
            )
        if (
            PLATFORM_MECHANISM.search(compact)
            and CAUSAL_WORD.search(compact)
            and not mechanism_evidence
        ):
            errors.append(
                f"line {line_no}: 缺少可追溯平台机制证据，不能把内部机制写成原因: "
                f"{compact[:120]}"
            )
        if (
            conditional_reduction
            and IMMEDIATE.search(compact)
            and REDUCTION.search(draft)
        ):
            errors.append(
                f"line {line_no}: 计划含条件式削减，却把含削减动作的章节标为立即执行: "
                f"{compact[:120]}"
            )
        if not NUMBER.search(compact):
            continue
        if not actual_config_known and CONTROL_ACTION.search(compact):
            errors.append(
                f"line {line_no}: 实际配置未知，正文仍含数值化控制动作: {compact[:120]}"
            )
        if response_type == "none" and FUTURE_TARGET.search(compact):
            errors.append(
                f"line {line_no}: 无响应证据，正文仍含数值化未来目标或预测: {compact[:120]}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft_md", help="最终回答草稿 Markdown")
    parser.add_argument("plan_json", help="已通过 decision_guard 的计划 JSON")
    args = parser.parse_args()

    try:
        draft = Path(args.draft_md).read_text(encoding="utf-8")
        plan = json.loads(Path(args.plan_json).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL\n- 无法读取输入: {exc}")
        return 1

    errors = validate(draft, plan)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
