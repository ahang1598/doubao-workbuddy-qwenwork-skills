#!/usr/bin/env python3
"""Validate A-share earnings facts.json.

Exit code:
  0: no blocking errors
  1: blocking errors exist
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
CLAIM_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
OFFICIAL_SOURCE_TYPES = {
    "company_report",
    "company_annual_report",
    "company_quarterly_report",
    "company_announcement",
    "exchange_filing",
    "official_database",
}
BROKER_SOURCE_TYPES = {"broker_research", "broker_consensus", "sellside_research"}
MEDIA_SOURCE_TYPES = {"media", "news", "social", "forum", "xueqiu", "toutiao"}
CALC_SOURCE_TYPES = {"calculation", "author_calculation", "model_calculation"}
USAGE_TYPES = {
    "hard_fact",
    "company_statement",
    "management_guidance",
    "external_estimate",
    "broker_estimate",
    "broker_forecast",
    "market_view",
    "author_calculation",
    "author_inference",
}
# 报表类条目关键词：这些数字必须取自定期报告原文，media 来源给警告
FS_KEYWORD_RE = re.compile(
    r"费用|账款|款项|利润|净利|收入|营收|毛利|现金流|在建工程|存货|应收|应付|预付|利率|资产|负债|EPS|每股收益"
)


def load_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"{path} does not contain a JSON object")


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def pct_change(current: float, base: float) -> float | None:
    if base == 0:
        return None
    return (current / base - 1.0) * 100.0


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def fmt_num(value: float | None, unit: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}{unit}"


def canonical_period(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    match = re.search(r"(20\d{2})\s*[Qq]\s*([1-4])", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    cn_q = {"一": 1, "二": 2, "三": 3, "四": 4}
    match = re.search(r"(20\d{2})\s*年\s*第?([一二三四1-4])\s*季", text)
    if match:
        raw = match.group(2)
        return int(match.group(1)), cn_q.get(raw, int(raw) if raw.isdigit() else 0)
    return None


def previous_quarter(period: tuple[int, int]) -> tuple[int, int]:
    year, quarter = period
    if quarter == 1:
        return year - 1, 4
    return year, quarter - 1


def same_quarter_last_year(period: tuple[int, int]) -> tuple[int, int]:
    year, quarter = period
    return year - 1, quarter


def find_history(history: list[Any], period: tuple[int, int]) -> dict[str, Any] | None:
    for item in history:
        if isinstance(item, dict) and canonical_period(item.get("period")) == period:
            return item
    return None


def archetype_kind(raw: Any) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.lower()
    if "金融" in raw or text.startswith("b") or "financial" in text or "bank" in text:
        return "B"
    if "产品" in raw or text.startswith("a") or "product" in text:
        return "A"
    if "项目" in raw or text.startswith("c") or "project" in text:
        return "C"
    if "经常" in raw or " recurring" in text or text.startswith("d"):
        return "D"
    return None


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
            print(f"[复算/信息] {msg}")
        for msg in self.warnings:
            print(f"[警告] {msg}")
        for msg in self.errors:
            print(f"[错误] {msg}")
        print(f"汇总: {len(self.errors)} 错误, {len(self.warnings)} 警告, {len(self.infos)} 条复算/信息")


def walk_sources(obj: Any, reporter: Reporter, path: str = "$") -> None:
    if isinstance(obj, dict):
        has_source = "source" in obj
        if has_source:
            in_claim = bool(re.fullmatch(r"\$\.claims\[\d+\]", path))
            source = obj.get("source")
            if not isinstance(source, str) or not DATE_RE.search(source):
                reporter.warning(f"{path}.source 不含 YYYY-MM-DD 日期")
            if "url" not in obj and not in_claim:
                reporter.warning(f"{path}.url 缺失")
            if "tier" not in obj and not in_claim:
                reporter.warning(f"{path}.tier 缺失")
        for key, value in obj.items():
            walk_sources(value, reporter, f"{path}.{key}")
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            walk_sources(value, reporter, f"{path}[{idx}]")


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
        if not claim.get("usage_type"):
            reporter.error(f"{path}.usage_type 缺失")
        if "value" not in claim and not any(claim.get(field) for field in ("text", "statement", "evidence")):
            reporter.warning(f"{path} 缺少 value/text/statement/evidence，display 仍可生成，但不利于回查事实内容")
        tier = claim.get("tier")
        if tier and tier not in {"official", "broker", "media", "market"}:
            reporter.warning(f"{path}.tier 不在 official/broker/media/market：{tier}")

        source_type = claim.get("source_type")
        usage_type = claim.get("usage_type")
        if source_type in OFFICIAL_SOURCE_TYPES and tier and tier != "official":
            reporter.warning(f"{path}.source_type={source_type} 但 tier 不是 official")
        if source_type in BROKER_SOURCE_TYPES and tier and tier != "broker":
            reporter.warning(f"{path}.source_type={source_type} 但 tier 不是 broker")
        if source_type in MEDIA_SOURCE_TYPES and tier and tier not in {"media", "market"}:
            reporter.warning(f"{path}.source_type={source_type} 但 tier 不是 media/market")
        if usage_type and usage_type not in USAGE_TYPES:
            reporter.warning(f"{path}.usage_type 不在推荐枚举内：{usage_type}")
        if usage_type == "hard_fact":
            if tier in {"broker", "media", "market"} or source_type in BROKER_SOURCE_TYPES | MEDIA_SOURCE_TYPES:
                reporter.error(f"{path} 是 hard_fact，但来源指向 broker/media/market；请改 usage_type 或换官方/计算来源")
        if usage_type in {"broker_estimate", "broker_forecast"} and tier and tier != "broker":
            reporter.warning(f"{path}.usage_type={usage_type} 但 tier 不是 broker")
        if usage_type == "market_view" and tier and tier not in {"media", "market", "broker"}:
            reporter.warning(f"{path}.usage_type=market_view 通常不应来自 official 来源")

        if "value" in claim and "unit" not in claim:
            reporter.warning(f"{path} 有 value 但 unit 缺失")
        if source_type in CALC_SOURCE_TYPES or usage_type == "author_calculation":
            if not claim.get("calculation"):
                reporter.error(f"{path} 是作者计算值但 calculation 缺失")

        allowed = claim.get("allowed_wording")
        if allowed is not None and not (
            isinstance(allowed, list) and all(isinstance(item, str) and item.strip() for item in allowed)
        ):
            reporter.warning(f"{path}.allowed_wording 应为非空字符串数组；缺失或格式错误时 lint 会使用 usage_type 默认语气")

        for field in ("suggested_wording", "required_caveat"):
            raw = claim.get(field)
            if raw is not None and not (
                (isinstance(raw, str) and raw.strip())
                or (isinstance(raw, list) and all(isinstance(item, str) and item.strip() for item in raw))
            ):
                reporter.warning(f"{path}.{field} 应为非空字符串，或非空字符串数组")


def check_eps_share(
    reporter: Reporter,
    label: str,
    eps: float | None,
    shares_yi: float | None,
    net_profit_yi: float | None,
) -> None:
    if eps is None:
        return
    if shares_yi is None:
        reporter.warning(f"{label} 有 EPS 但 shares.total_yi 缺失，无法复算 EPS×股本")
        return
    if net_profit_yi is None:
        return
    implied = eps * shares_yi
    diff = abs(implied - net_profit_yi) / abs(net_profit_yi) if net_profit_yi else math.inf
    reporter.info(
        f"{label} EPS×股本 = {eps:.2f} × {shares_yi:.2f} = {implied:.1f} 亿元；"
        f"归母净利润 {net_profit_yi:.1f} 亿元；偏差 {diff * 100:.1f}%"
    )
    if diff > 0.15:
        reporter.error(f"{label} EPS×股本 与归母净利润偏差超过 15%")


def validate(facts: dict[str, Any]) -> Reporter:
    r = Reporter()

    meta = facts.get("meta")
    if not isinstance(meta, dict):
        r.error("meta 缺失")
        meta = {}

    for field in ["company", "code", "quarter", "today", "release_date"]:
        if not meta.get(field):
            r.error(f"meta.{field} 缺失")

    today = parse_date(meta.get("today"))
    release_date = parse_date(meta.get("release_date"))
    if meta.get("today") and today is None:
        r.error("meta.today 格式错误，应为 YYYY-MM-DD")
    if meta.get("release_date") and release_date is None:
        r.error("meta.release_date 格式错误，应为 YYYY-MM-DD")
    if today and release_date:
        if release_date > today:
            r.error("release_date 晚于 today")
        elif (today - release_date).days > 100:
            r.warning("release_date 距 today 超过 100 天，请确认不是拿错报告期")

    archetype = meta.get("archetype")
    kind = archetype_kind(archetype)
    if archetype and kind is None:
        r.warning("meta.archetype 不在 A/B/C/D 四种原型内")

    consensus = facts.get("consensus")
    if not isinstance(consensus, dict):
        consensus = {}
    available = consensus.get("available")
    if consensus and not isinstance(available, bool):
        r.warning("consensus.available 不是布尔值")
    if available is True:
        if number(consensus.get("revenue_yi")) is None and number(consensus.get("net_profit_yi")) is None:
            r.error("consensus.available=true 但无任何预期数字")
    if consensus.get("tier") == "media":
        r.error("consensus.tier 为 media，不能作为预期锚")

    actual = facts.get("actual")
    if not isinstance(actual, dict):
        actual = {}

    actual_rev = number(actual.get("revenue_yi"))
    actual_np = number(actual.get("net_profit_yi"))
    actual_deducted = number(actual.get("net_profit_deducted_yi"))
    if actual and actual_rev is None:
        r.warning("actual.revenue_yi 缺失；若正文引用收入，请用 claims 绑定")
    if actual and actual_np is None:
        r.warning("actual.net_profit_yi 缺失；若正文引用利润，请用 claims 绑定")
    if actual_rev is not None and actual_np is not None and actual_np >= actual_rev:
        r.error("归母净利润大于等于营业收入")

    gross_margin = number(actual.get("gross_margin_pct"))
    if kind == "B" and "gross_margin_pct" in actual and actual.get("gross_margin_pct") is not None:
        r.error("金融型公司 actual 填了 gross_margin_pct")
    if gross_margin is not None and not (0 <= gross_margin <= 100):
        r.error("gross_margin_pct 超出 [0, 100]")

    history_raw = facts.get("history")
    history = history_raw if isinstance(history_raw, list) else []
    period = canonical_period(meta.get("quarter")) or canonical_period(actual.get("period"))
    if period:
        yoy_item = find_history(history, same_quarter_last_year(period))
        if history_raw is not None and yoy_item is None:
            r.warning("history 缺上年同期数据，无法复算同比；正文不写同比时可接受")
        else:
            if actual_rev is not None:
                r.info(f"营业收入同比 = {fmt_pct(pct_change(actual_rev, number(yoy_item.get('revenue_yi')) or 0))}")
            if actual_np is not None:
                r.info(f"归母净利润同比 = {fmt_pct(pct_change(actual_np, number(yoy_item.get('net_profit_yi')) or 0))}")
        qoq_item = find_history(history, previous_quarter(period))
        if qoq_item is not None:
            if actual_rev is not None:
                r.info(f"营业收入环比 = {fmt_pct(pct_change(actual_rev, number(qoq_item.get('revenue_yi')) or 0))}")
            if actual_np is not None:
                r.info(f"归母净利润环比 = {fmt_pct(pct_change(actual_np, number(qoq_item.get('net_profit_yi')) or 0))}")
    else:
        r.warning("无法识别报告期，跳过同比/环比复算")

    if actual_rev is not None and actual_np is not None and actual_rev:
        net_margin = actual_np / actual_rev * 100
        r.info(f"本期归母净利率 = {net_margin:.1f}%")
        if kind != "B" and net_margin > 60:
            r.warning("非金融公司归母净利率 >60%，请复核")

    if actual_np is not None and actual_deducted is not None and actual_deducted > actual_np * 1.3:
        r.warning("扣非归母净利润 > 归母净利润 ×1.3，疑似填反或存在异常")

    shares = facts.get("shares") if isinstance(facts.get("shares"), dict) else {}
    shares_yi = number(shares.get("total_yi"))
    check_eps_share(r, "actual", number(actual.get("eps_yuan")), shares_yi, actual_np)

    annual_raw = facts.get("annual")
    annual = annual_raw if isinstance(annual_raw, list) else []
    forecast_raw = facts.get("forecast")
    forecast = forecast_raw if isinstance(forecast_raw, list) else []
    if forecast and not annual:
        r.warning("有 forecast 但无 annual，无法做年度预测与历史实际的合理性复核")

    latest_annual = annual[-1] if annual and isinstance(annual[-1], dict) else {}
    latest_rev = number(latest_annual.get("revenue_yi"))
    latest_np = number(latest_annual.get("net_profit_yi"))
    for idx, item in enumerate(forecast):
        if not isinstance(item, dict):
            continue
        label = f"forecast[{idx}] {item.get('year', '')}".strip()
        f_rev = number(item.get("revenue_yi"))
        f_np = number(item.get("net_profit_yi"))
        check_eps_share(r, label, number(item.get("eps_yuan")), shares_yi, f_np)
        if f_rev is not None and actual_rev is not None and f_rev < actual_rev:
            r.error(f"{label} 年度预测收入低于已披露本期单季实际收入")
        if f_np is not None and actual_np is not None and f_np < actual_np:
            r.error(f"{label} 年度预测归母净利润低于已披露本期单季实际")
        for field, forecast_value, annual_value in [
            ("revenue_yi", f_rev, latest_rev),
            ("net_profit_yi", f_np, latest_np),
        ]:
            if forecast_value is not None and annual_value is not None and annual_value:
                ratio = forecast_value / annual_value
                if ratio < 0.2 or ratio > 5:
                    r.error(f"{label}.{field} 与最近年度实际比值 {ratio:.2f} 超出 [0.2, 5]")
        if f_rev is not None and f_np is not None and f_rev:
            r.info(f"{label} 隐含归母净利率 = {f_np / f_rev * 100:.1f}%")

    price = facts.get("price") if isinstance(facts.get("price"), dict) else {}
    if price:
        price_date = parse_date(price.get("date"))
        if price_date is None:
            r.error("price 存在但 date 缺失或格式错误")
    price_value = number(price.get("value_yuan"))
    if price_value is not None:
        for idx, item in enumerate(forecast):
            if isinstance(item, dict):
                eps = number(item.get("eps_yuan"))
                if eps:
                    r.info(f"现价对应 {item.get('year', f'forecast[{idx}]')} PE = {price_value / eps:.1f}x")

    if available is True:
        c_rev = number(consensus.get("revenue_yi"))
        c_np = number(consensus.get("net_profit_yi"))
        if actual_rev is not None and c_rev:
            r.info(f"收入相对预期偏离 = {fmt_pct(pct_change(actual_rev, c_rev))}")
        if actual_np is not None and c_np:
            r.info(f"归母净利润相对预期偏离 = {fmt_pct(pct_change(actual_np, c_np))}")

    if isinstance(facts.get("guidance"), dict) and not isinstance(facts["guidance"].get("available"), bool):
        r.warning("guidance.available 不是布尔值")

    other_facts = facts.get("other_facts") if isinstance(facts.get("other_facts"), list) else []
    for idx, item in enumerate(other_facts):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))
        unit = str(item.get("unit", ""))
        if item.get("tier") == "media" and (FS_KEYWORD_RE.search(name) or "亿元" in unit):
            r.warning(
                f"other_facts[{idx}]「{name}」疑似三大报表数字但来源为 media——"
                f"报表数字必须取自定期报告原文，媒体只能补充经营性事实"
            )

    validate_claims(facts, r)
    walk_sources(facts, r)
    return r


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate earnings facts.json.")
    parser.add_argument("facts_json", help="Path to facts.json")
    args = parser.parse_args(argv)

    try:
        facts = load_json(Path(args.facts_json))
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 JSON: {exc}")
        return 1
    reporter = validate(facts)
    reporter.emit()
    return 1 if reporter.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
