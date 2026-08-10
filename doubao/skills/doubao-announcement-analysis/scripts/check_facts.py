#!/usr/bin/env python3
"""校验 facts.json（finalize_report.py 门禁 1）。

facts.json 的职责只有一个：给正文里的关键数字和关键判断提供可追溯来源。它不是
研究数据库，规格见 `references/facts-template.md`。

这个脚本只阻断结构性错误（校验边界，不做业务合理性判断）：
1. JSON 无法解析 / claims 不是数组。
2. claim_id 缺失、重复或格式错误。
3. claim 缺少 source 或 usage_type。
4. hard_fact 明显来自 broker/media 来源（应改用更保守的 usage_type）。
5. author_calculation 缺少 calculation 字段。
6. meta 缺少必填字段，或日期格式/先后关系明显有问题。

其他问题（url/tier 缺失、period 口径提示等）只提示复核，不阻断——写作纪律不能
靠脚本机械穷举，脚本只兜底最容易出错、最容易被忽略的结构性问题。

退出码：
  0：无阻断性错误
  1：存在阻断性错误
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

CLAIM_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

BROKER_SOURCE_TYPES = {"broker_research", "broker_consensus", "sellside_research"}
MEDIA_SOURCE_TYPES = {"media", "news", "social", "forum", "xueqiu", "toutiao"}
CALC_SOURCE_TYPES = {"calculation", "author_calculation", "model_calculation"}
USAGE_TYPES = {
    "hard_fact",
    "company_statement",
    "management_guidance",
    "broker_estimate",
    "broker_forecast",
    "market_view",
    "author_calculation",
    "author_inference",
}
MARKETS = {"A股", "港股", "美股"}


class Reporter:
    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def info(self, msg: str) -> None:
        self.infos.append(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def emit(self) -> None:
        for msg in self.infos:
            print(f"[信息] {msg}")
        for msg in self.warnings:
            print(f"[警告] {msg}")
        for msg in self.errors:
            print(f"[错误] {msg}")
        print(f"汇总: {len(self.errors)} 错误, {len(self.warnings)} 警告, {len(self.infos)} 条信息")


def load_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"{path} 不包含合法的 JSON 对象")


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not DATE_RE.match(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def walk_sources(obj: Any, reporter: Reporter, path: str = "$") -> None:
    if isinstance(obj, dict):
        if "source" in obj:
            in_claim = bool(re.fullmatch(r"\$\.claims\[\d+\]", path))
            source = obj.get("source")
            if not isinstance(source, str) or not source.strip():
                reporter.warning(f"{path}.source 为空或非字符串")
            if "url" not in obj and not in_claim:
                reporter.warning(f"{path}.url 缺失")
        for key, value in obj.items():
            walk_sources(value, reporter, f"{path}.{key}")
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            walk_sources(value, reporter, f"{path}[{idx}]")


def validate_meta(facts: dict[str, Any], reporter: Reporter) -> None:
    meta = facts.get("meta")
    if not isinstance(meta, dict):
        reporter.error("meta 缺失")
        return

    for field in ("company", "market", "today"):
        if not meta.get(field):
            reporter.error(f"meta.{field} 缺失")

    market = meta.get("market")
    if market and market not in MARKETS:
        reporter.warning(f"meta.market 不在 A股/港股/美股 三个取值内：{market}")

    today = parse_date(meta.get("today"))
    if meta.get("today") and today is None:
        reporter.error("meta.today 格式错误，应为 YYYY-MM-DD")

    announcement_date = parse_date(meta.get("announcement_date"))
    if meta.get("announcement_date") and announcement_date is None:
        reporter.error("meta.announcement_date 格式错误，应为 YYYY-MM-DD")

    if today and announcement_date and announcement_date > today:
        reporter.error("meta.announcement_date 晚于 meta.today")

    if not meta.get("announcement_type"):
        reporter.warning("meta.announcement_type 缺失，建议标注对应的 playbook 分类")


def validate_claims(facts: dict[str, Any], reporter: Reporter) -> None:
    claims = facts.get("claims")
    if claims is None:
        reporter.warning("claims 缺失：lint_report 将无法做正文数字与事实表绑定提示")
        return
    if not isinstance(claims, list):
        reporter.error("claims 必须是数组")
        return

    seen: set[str] = set()
    for idx, claim in enumerate(claims):
        path = f"claims[{idx}]"
        if not isinstance(claim, dict):
            reporter.error(f"{path} 必须是对象")
            continue

        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not CLAIM_ID_RE.fullmatch(claim_id):
            reporter.error(f"{path}.claim_id 缺失或格式错误（需以字母开头，只含字母/数字/._-）")
        elif claim_id in seen:
            reporter.error(f"{path}.claim_id 重复：{claim_id}")
        else:
            seen.add(claim_id)

        if not claim.get("source"):
            reporter.error(f"{path}.source 缺失")
        usage_type = claim.get("usage_type")
        if not usage_type:
            reporter.error(f"{path}.usage_type 缺失")
        elif usage_type not in USAGE_TYPES:
            reporter.warning(f"{path}.usage_type 不在推荐枚举内：{usage_type}")

        if "value" not in claim and not any(claim.get(f) for f in ("text", "statement", "evidence")):
            reporter.warning(f"{path} 缺少 value/text/statement/evidence，display 仍可生成，但不利于回查事实内容")

        source_type = claim.get("source_type")
        tier = claim.get("tier")
        if usage_type == "hard_fact":
            if tier in {"broker", "media", "market"} or source_type in BROKER_SOURCE_TYPES | MEDIA_SOURCE_TYPES:
                reporter.error(
                    f"{path} 是 hard_fact，但来源指向 broker/media/market；"
                    "请改 usage_type（如 broker_estimate/market_view）或换成公司/交易所/官方数据库来源"
                )
        if (source_type in CALC_SOURCE_TYPES or usage_type == "author_calculation") and not claim.get("calculation"):
            reporter.error(f"{path} 是作者计算值（author_calculation）但缺少 calculation 字段，需写明算式")

        for field in ("allowed_wording", "suggested_wording", "required_caveat"):
            raw = claim.get(field)
            if raw is not None and not (
                (isinstance(raw, str) and raw.strip())
                or (isinstance(raw, list) and all(isinstance(item, str) and item.strip() for item in raw))
            ):
                reporter.warning(f"{path}.{field} 应为非空字符串，或非空字符串数组")


def validate(facts: dict[str, Any]) -> Reporter:
    r = Reporter()
    validate_meta(facts, r)
    validate_claims(facts, r)
    walk_sources(facts, r)
    return r


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验 facts.json（门禁 1）")
    parser.add_argument("facts_json", help="facts.json 文件路径")
    args = parser.parse_args(argv)

    try:
        facts = load_json(Path(args.facts_json))
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 JSON: {exc}", file=sys.stderr)
        return 1

    reporter = validate(facts)
    reporter.emit()
    return 1 if reporter.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
