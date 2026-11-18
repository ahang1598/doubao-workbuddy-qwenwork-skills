#!/usr/bin/env python3
"""Deterministic search mode, time-anchor discipline, and source priority planner for event analysis."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MAX_INPUT_BYTES = 1_048_576

CHANNEL_BY_QUERY_TYPE = {
    "structured_financial_data": "structured_market_financial_lookup",
    "announcements_and_research_reports": "filings_and_research_search",
    "other_public_information": "authoritative_public_search",
}

EVENT_SKILL_NAME = "doubao-market-hotspot"
SUPPORTED_SKILLS = {EVENT_SKILL_NAME, "event-impact-analysis"}

DEFAULT_SOURCE_ORDER = [
    "issuing_authority",
    "law_or_regulation",
    "implementing_authority",
    "industry_primary",
    "reputable_secondary",
]

SOURCE_ORDER_BY_EVENT_TYPE = {
    "company": [
        "company_ir",
        "exchange_filing",
        "regulator_filing",
        "reputable_secondary",
    ],
    "regulatory": [
        "issuing_authority",
        "law_or_regulation",
        "implementing_authority",
        "reputable_secondary",
    ],
    "supply_demand": [
        "official_organization",
        "authoritative_physical_data",
        "industry_primary",
        "reputable_secondary",
    ],
}

CURRENT_RE = r"最新|当前|截至|近期|今日|现在|本周|本月|本季度|本年度"
CUTOFF_RE = r"信息截点|截止时间|截止日|截至\s*\d{4}\s*年|不得使用.{0,12}之后"
RULE_RE = r"政策|法规|监管|规则|关税|限制|合规|官方文件|公告"
METHOD_ONLY_RE = r"模板|方法论|框架示例|如何分析|怎么分析|计算公式|空白表格"
USER_SOURCE_ONLY_RE = r"仅使用.{0,12}(附件|材料|数据)|只基于.{0,12}(附件|材料|数据)|封闭材料"
AMBIGUOUS_RE = r"某.{0,4}(公司|项目|政策|事件|监管)|一家企业|一个标的|随便选|你帮我选"
COMPANY_EVENT_RE = r"并购|收购|财报|业绩|指引|资本开支|回购|分红|定增|公司公告|企业公告|发行人公告"
REGULATORY_EVENT_RE = r"政策|法规|监管|制裁|关税|退税|调查|限制|规则|法案|征求意见"
SUPPLY_DEMAND_EVENT_RE = r"供给|供应|需求|产量|库存|停产|减产|增产|中断|短缺"


class RouterInputError(ValueError):
    """Raised when router input is invalid."""


def matches(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, flags=re.I))


def infer_signals(
    skill: str, prompt: str, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Infer routing and time-anchor signals from user prompt and optional context."""
    if skill not in SUPPORTED_SKILLS:
        raise RouterInputError(f"unsupported skill: {skill}")
    context = context or {}
    if not isinstance(context, dict):
        raise RouterInputError("context must be an object")
    text = prompt or ""
    if not isinstance(text, str):
        raise RouterInputError("prompt must be a string")

    attachments_present = bool(context.get("attachments_present"))
    attachments_sufficient = bool(context.get("attachments_sufficient"))
    source_only = bool(context.get("closed_materials")) or matches(USER_SOURCE_ONLY_RE, text)
    explicit_cutoff = bool(context.get("as_of")) or matches(CUTOFF_RE, text)
    method_only = matches(METHOD_ONLY_RE, text)
    ambiguous = matches(AMBIGUOUS_RE, text)
    current = matches(CURRENT_RE, text)
    rules = matches(RULE_RE, text)

    object_frozen = context.get("object_frozen")
    if object_frozen is None:
        object_frozen = not ambiguous
    jurisdiction_frozen = context.get("jurisdiction_frozen")
    if jurisdiction_frozen is None:
        jurisdiction_frozen = bool(
            matches(
                r"中国大陆|中国香港|香港|美国|新加坡|欧盟|日本|人民币|美元|港元|欧元|日元",
                text,
            )
        )

    needs_current_public_facts = (
        not method_only
        and not attachments_sufficient
        and (current or matches(r"事件|政策|监管|并购|制裁|关税|退税|调查|限制|影响|传导|反映", text))
    )
    needs_public_rules = rules and not method_only

    if matches(COMPANY_EVENT_RE, text):
        default_event_type = "company"
    elif matches(REGULATORY_EVENT_RE, text):
        default_event_type = "regulatory"
    elif matches(SUPPLY_DEMAND_EVENT_RE, text):
        default_event_type = "supply_demand"
    else:
        default_event_type = "generic"
    event_type = context.get("event_type", default_event_type)

    time_anchor_mode = (
        "closed_materials"
        if source_only
        else "explicit_cutoff"
        if explicit_cutoff
        else "open_current_timeline"
    )

    return {
        "skill": EVENT_SKILL_NAME,
        "prompt": text,
        "as_of": context.get("as_of"),
        "time_anchor_mode": time_anchor_mode,
        "object_frozen": bool(object_frozen),
        "jurisdiction_frozen": bool(jurisdiction_frozen),
        "attachments_present": attachments_present,
        "attachments_sufficient": attachments_sufficient,
        "closed_materials": source_only,
        "user_forbids_search": bool(context.get("user_forbids_search")),
        "needs_current_public_facts": bool(needs_current_public_facts),
        "needs_public_rules": bool(needs_public_rules),
        "event_type": event_type,
        "inference": {
            "current_language": current,
            "explicit_cutoff": explicit_cutoff,
            "rule_language": rules,
            "method_only": method_only,
            "source_only": source_only,
            "ambiguous_object": ambiguous,
        },
    }


def plan(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RouterInputError("input payload must be a JSON object")
    skill_raw = payload.get("skill", EVENT_SKILL_NAME)
    if not isinstance(skill_raw, str) or skill_raw not in SUPPORTED_SKILLS:
        raise RouterInputError(f"unsupported skill: {skill_raw!r}")

    if "prompt" in payload and not any(
        key in payload for key in ("needs_current_public_facts", "needs_public_rules")
    ):
        payload = infer_signals(
            skill_raw, payload.get("prompt", ""), payload.get("context")
        )

    time_anchor_mode = payload.get("time_anchor_mode") or (
        "closed_materials"
        if payload.get("closed_materials")
        else "explicit_cutoff"
        if payload.get("as_of")
        else "open_current_timeline"
    )

    if payload.get("closed_materials") or payload.get("user_forbids_search"):
        mode, reason = "off", "closed materials or user disabled external search"
    elif payload.get("inference", {}).get("method_only"):
        mode, reason = "off", "method, template or pure calculation task"
    elif not payload.get("object_frozen", False):
        mode, reason = "blocked", "target event or entity is not specified"
    elif (
        payload.get("attachments_present")
        and payload.get("attachments_sufficient")
        and (payload.get("needs_current_public_facts") or payload.get("needs_public_rules"))
    ):
        mode, reason = "optional", "attachments are sufficient; external search may only corroborate"
    elif payload.get("needs_current_public_facts") or payload.get("needs_public_rules"):
        mode, reason = "required", "current public evidence is necessary"
    else:
        mode, reason = "optional", "external search can supplement if material gaps remain"

    event_type = payload.get("event_type", "generic")
    source_order = SOURCE_ORDER_BY_EVENT_TYPE.get(event_type, DEFAULT_SOURCE_ORDER)

    guidelines = [
        "query only for facts needed by the current event question",
        "verify official status with the issuing authority when legal effect matters",
        "use a comparable pre-event baseline when assessing whether markets already reacted",
        "stop searching once the current judgment has sufficient support",
    ]
    if time_anchor_mode in {"closed_materials", "explicit_cutoff"}:
        guidelines.append(
            "enforce publication timestamp and market close timezone against cutoff; exclude post-cutoff retrospective reports"
        )
    else:
        guidelines.append(
            "verify subsequent developments from event date to present and calibrate if premise has evolved"
        )

    return {
        "mode": mode,
        "reason": reason,
        "skill": EVENT_SKILL_NAME,
        "as_of": payload.get("as_of"),
        "time_anchor_mode": time_anchor_mode,
        "event_type": event_type,
        "source_order": source_order,
        "channel_order": [
            "authoritative_public_search",
            "filings_and_research_search",
            "structured_market_financial_lookup",
        ],
        "channel_by_query_type": CHANNEL_BY_QUERY_TYPE.copy(),
        "guidelines": guidelines,
        "signals": {
            key: payload.get(key)
            for key in (
                "object_frozen",
                "jurisdiction_frozen",
                "attachments_present",
                "attachments_sufficient",
                "needs_current_public_facts",
                "needs_public_rules",
            )
        },
        "inference": payload.get("inference", {}),
    }


def _read_raw_input(source: str) -> str:
    if source == "-":
        raw = sys.stdin.read()
    elif source.lstrip().startswith("{"):
        raw = source
    else:
        path = Path(source)
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise RouterInputError(f"input file exceeds {MAX_INPUT_BYTES} bytes")
        raw = path.read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) > MAX_INPUT_BYTES:
        raise RouterInputError(f"input payload exceeds {MAX_INPUT_BYTES} bytes")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan search mode, time-anchor discipline, and source priority for event analysis."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input JSON file path, inline JSON string, or - for stdin (default).",
    )
    parser.add_argument("--output", help="Optional output JSON file path.")
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print emitted JSON."
    )
    args = parser.parse_args(argv)
    try:
        raw = _read_raw_input(args.input)
        payload = json.loads(raw)
        result = plan(payload)
        text = (
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2 if args.pretty else None,
                sort_keys=args.pretty,
            )
            + "\n"
        )
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    except (OSError, json.JSONDecodeError, RouterInputError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
