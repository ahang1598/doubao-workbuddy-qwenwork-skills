#!/usr/bin/env python3
"""Lint report.md for tone/scope violations (门禁 2).

Usage:
  python3 lint_report.py report.md [facts.json]

Exit code:
  0: no blocking errors
  1: blocking errors exist
  2: usage error

Checks (deterministic, frees model attention for analysis):
  ERROR   first-person judgment phrases (违反语气三句式)
  ERROR   unnamed anchors (市场普遍认为/据了解/卖方一致认为)
  ERROR   leftover placeholders ({{...}}, 【图表占位, 【图:)
  ERROR   self-issued rating without attribution on the same line
  ERROR   US-filing terms for A-share targets (needs facts.json meta.code)
  ERROR   超预期/不达预期 wording without a documented anchor (红线 7)
  ERROR   guess values without formula 推算约/估算约 (红线 3)
  ERROR   internal jargon in deliverable: facts.json/writing-plan/复算/门禁 (红线 10)
  ERROR   internal reasoning labels: 深度0-4/当前深度/机制候选/结论分档等
  ERROR   draft-card structure leaked into deliverable: 机制一/现象描述/结论：已证实等
  ERROR   final markdown still contains draft corner quotes 「」/『』
  ERROR   inline footnote markers [^n] in final prose
  ERROR   {fact:...} used as a value placeholder, e.g. 为{fact:x}
  ERROR   ASCII double quotes wrapping Chinese prose
  WARNING numeric fact in prose/table lacks {fact:claim_id} when facts.json
          contains claims
  ERROR   {fact:...} is unknown, malformed, or not in claims[].claim_id
  WARNING explicit period wording conflicts with facts.json claims[].period
  WARNING broker/media/inference/company-statement claims may be written with
          unsafe certainty; warning includes suggested wording when possible
  WARNING bare 我们 usage, 上行空间 without attribution, missing
          后续应关注 / 未获取 sections, no clickable links,
          ASCII double quotes in Chinese prose outside code spans
  INFO    counts of links, 後续应关注 items
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# 否定语境（"非本报告判断""不代表我们观点"等免责表述）不算违规
JUDGMENT_RE = re.compile(
    r"(?<![非])(?:我们(?:认为|预计|预期|判断|测算|建议|给予|相信|倾向)|我们的(?:预测|判断|测算|观点)|本报告(?:认为|预计|判断)|笔者认为)"
)
UNNAMED_ANCHOR_RE = re.compile(r"市场普遍认为|据了解|卖方一致(认为|预期)|业内人士(透露|认为|表示)")
PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}|【图表占位|【图[:：]")
RATING_RE = re.compile(r"(给予|首次覆盖)[^，。；\n]{0,20}(买入|增持|中性|持有|减持|卖出|推荐|跑赢|跑输)")
ATTRIBUTION_RE = re.compile(r"引自|转引|引用")
UPSIDE_RE = re.compile(r"上行空间|下行空间|隐含.{0,6}(涨幅|跌幅)")
US_FILING_RE = re.compile(r"10-[QK]|8-K|\bSEC\b|EDGAR|Form\s+[0-9A-Z]|非\s*GAAP|Non-GAAP", re.IGNORECASE)
WATCHLIST_RE = re.compile(r"后续(应|需)?关注")
URL_RE = re.compile(r"https?://")
# 成品报告禁止出现的内部流程词（红线 10）
INTERNAL_RE = re.compile(
    r"_INTERNAL_DO_NOT_DELIVER|facts\.json|writing[-_]plan|check_facts|lint_report|make_charts|"
    r"company-brief|analysis-brief|reader-outline|report-source|report-display|analysis-source|"
    r"DO_NOT_DELIVER__|FINAL_REPLY_BODY|00_RESUME_HERE|"
    r"中间产物|交付清单|复算|门禁\s?[12１２]?"
)
# 内部推理标签（不应出现在成品中）。裸 L3 等可能是产品/行业术语，
# 只拦截明显来自内部流程的旧标签形态；中文深度标签可直接硬拦截。
INTERNAL_LEVEL_RE = re.compile(
    r"深度\s*[0-4０-４零一二三四](?![A-Za-z])|当前深度|补到深度|推到深度|解释深度阶梯|推理深度|"
    r"机制候选|假设空间|约束判断|结论分档|收入函数|"
    r"(?:当前|现处|停在|推到|补到|到达)\s*L[0-4]|"
    r"L[0-4]\s*(?:→|->|-|/)\s*L[0-4]|"
    r"L[0-4]\s*[：:(（]|"
    r"L1[-/至到]L4|L1/L2/L3/L4"
)
# 底稿卡片结构残留。只拦截行首/标题式模板，不拦正文里的普通“机制/结论”。
DRAFT_STRUCTURE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:[-*]\s*)?(?:"
    r"(?:机制\s*[一二三四五六七八九十0-9A-Za-z]+|现象描述|具体表现|为什么公司不能消解这个变化)"
    r"(?:\s*[:：]|[？?]|\s|$)|"
    r"结论\s*[:：]\s*(?:已证实|已证明|合理推断|单一解释)(?:\s|[（(，,。；;:：]|$)"
    r")"
)
HAN_RE = re.compile(r"[\u4e00-\u9fff]")
ASCII_QUOTED_HAN_RE = re.compile(r'"[^"\n]*[\u4e00-\u9fff][^"\n]*"')
ASCII_DOUBLE_QUOTE_RE = re.compile(r'"')
DRAFT_CORNER_QUOTE_RE = re.compile(r"[「」『』]")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
INLINE_FOOTNOTE_RE = re.compile(r"\[\^[0-9A-Za-z_-]+\]")
BARE_WE_RE = re.compile(r"我们")
# 锚点-措辞绑定：利润/收入类指标的超预期/不达预期措辞
PROFIT_BEAT_RE = re.compile(r"(归母净利润|净利润|净利|利润)[端的]?[^。；\n]{0,10}(大幅|显著)?(超出?|低于|不及|逊于)[^。；\n]{0,4}预期")
REVENUE_BEAT_RE = re.compile(r"(营业收入|营收|收入)[端的]?[^。；\n]{0,10}(大幅|显著)?(超出?|低于|不及|逊于)[^。；\n]{0,4}预期")
# 无算式推算值（红线 3）
GUESS_RE = re.compile(r"推算约|估算约|估计约")
FACT_REF_RE = re.compile(r"\{facts?:([^{}\n]*)\}")
CLAIM_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
FACT_VALUE_PLACEHOLDER_RE = re.compile(
    r"(?:(?<!因)为|达(?:到)?|录得|实现|"
    r"增长至|下降至|增至|降至|升至|提升至|扩大至|收窄至|至)"
    r"\s*\{facts?:[^{}\n]*\}"
)
FACT_ONLY_TABLE_CELL_RE = re.compile(r"\|\s*\{facts?:[^{}\n]*\}\s*(?=\|)")
NUMERIC_FACT_RE = re.compile(
    r"(?<![A-Za-z0-9])[-+＋−]?\d+(?:,\d{3})*(?:\.\d+)?\s*"
    r"(?:%|pct|pcts|个百分点|bp|bps|亿|亿元|万|万元|元|人民币|美元|港元|台|套|吨|平方米|项|次|倍|x|X)"
)
PERIOD_Q_RE = re.compile(r"(20\d{2})\s*[Qq]\s*([1-4])")
PERIOD_CN_Q_RE = re.compile(r"(20\d{2})\s*年\s*(?:第\s*)?([一二三四1-4])\s*(?:季度|季报|季)")
PERIOD_YEAR_RE = re.compile(r"(20\d{2})\s*(?:年|年度|年报)")
BROKER_CUE_RE = re.compile(r"券商|研报|机构|外部|转引|估算|测算|预计|预测|判断|认为|给出|一致预期")
MEDIA_CUE_RE = re.compile(r"媒体|新闻|报道|报道称|据.*?(?:报道|消息)|市场观点|市场说法|雪球|头条|论坛|投资者讨论|转引")
INFERENCE_CUE_RE = re.compile(r"可能|或许|指向|意味着|倾向|推断|说明|需要|后续|若|如果|取决于|仍需")
CERTAIN_WORDING_RE = re.compile(r"已达|已经达到|确定|证明|证实|必然|坐实|事实是|无疑")
NON_FACT_USAGE = {
    "external_estimate",
    "broker_estimate",
    "broker_forecast",
    "market_view",
    "author_inference",
}
BROKER_USAGE = {"external_estimate", "broker_estimate", "broker_forecast"}
AUTHOR_INFERENCE_USAGE = {"author_inference"}
MEDIA_SOURCE_TYPES = {"media", "news", "social", "forum", "xueqiu", "toutiao"}
BROKER_SOURCE_TYPES = {"broker_research", "broker_consensus", "sellside_research"}
MARKET_DATABASE_SOURCE_TYPES = {"market_database"}
INDUSTRY_DATA_SOURCE_TYPES = {"industry_data"}


def load_facts(facts_path: Path | None) -> dict | None:
    if facts_path is None:
        return None
    try:
        return json.loads(facts_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_a_share(facts: dict | None) -> bool | None:
    """True=A股, False=非A股, None=unknown (no facts.json)."""
    if facts is None:
        return None
    code = str(facts.get("meta", {}).get("code", ""))
    return bool(re.search(r"\.(SZ|SH|BJ)\b", code, re.IGNORECASE))


def collect_strings(obj) -> list[str]:
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(collect_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(collect_strings(v))
    return out


def strip_inline_code(line: str) -> str:
    return INLINE_CODE_RE.sub("", line)


def parse_fact_refs(line: str) -> list[str]:
    refs: list[str] = []
    for raw_group in FACT_REF_RE.findall(line):
        for raw_ref in re.split(r"[,，、]", raw_group):
            refs.append(raw_ref.strip())
    return refs


def strip_fact_refs(line: str) -> str:
    return FACT_REF_RE.sub("", line)


CN_QUARTERS = {"一": "1", "二": "2", "三": "3", "四": "4"}


def canonical_periods(text: str) -> set[str]:
    periods: set[str] = set()
    for year, quarter in PERIOD_Q_RE.findall(text):
        periods.add(f"{year}Q{quarter}")
    for year, quarter in PERIOD_CN_Q_RE.findall(text):
        periods.add(f"{year}Q{CN_QUARTERS.get(quarter, quarter)}")
    for year in PERIOD_YEAR_RE.findall(text):
        periods.add(year)
    return periods


def claim_periods(claim: dict) -> set[str]:
    raw_period = str(claim.get("period", ""))
    periods = canonical_periods(raw_period)
    if periods:
        return periods
    match = re.search(r"(20\d{2})", raw_period)
    return {match.group(1)} if match else set()


def collect_claims(facts: dict | None) -> dict[str, dict]:
    if not isinstance(facts, dict):
        return {}
    claims_raw = facts.get("claims")
    if not isinstance(claims_raw, list):
        return {}
    claims: dict[str, dict] = {}
    for item in claims_raw:
        if not isinstance(item, dict):
            continue
        claim_id = item.get("claim_id")
        if isinstance(claim_id, str) and CLAIM_ID_RE.fullmatch(claim_id):
            claims[claim_id] = item
    return claims


def is_numeric_fact_line(line: str) -> bool:
    prose = strip_inline_code(strip_fact_refs(line))
    if not NUMERIC_FACT_RE.search(prose):
        return False
    if re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*", prose):
        return False
    return True


def source_tier(claim: dict) -> str:
    return str(claim.get("tier", "")).strip()


def source_type(claim: dict) -> str:
    return str(claim.get("source_type", "")).strip()


def usage_type(claim: dict) -> str:
    return str(claim.get("usage_type", "")).strip()


def claim_list_field(claim: dict, key: str) -> list[str]:
    raw = claim.get(key)
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def claim_value_text(claim: dict) -> str:
    text = str(claim.get("text", "")).strip()
    if text:
        return text
    metric = str(claim.get("metric", "该事项")).strip() or "该事项"
    value = claim.get("value")
    unit = str(claim.get("unit", "")).strip()
    if value is None or value == "":
        statement = str(claim.get("statement", "")).strip()
        evidence = str(claim.get("evidence", "")).strip()
        return statement or evidence or metric
    return f"{metric}约{value}{unit}" if unit else f"{metric}约{value}"


def is_capacity_or_plan_claim(claim: dict, prose: str) -> bool:
    haystack = " ".join(
        str(claim.get(key, "")) for key in ("metric", "text", "evidence", "statement")
    )
    return bool(re.search(r"产能|场地|扩产|规划|建成|投产|释放", haystack))


def claim_risk(claim: dict, prose: str) -> str:
    usage = usage_type(claim)
    tier = source_tier(claim)
    stype = source_type(claim)
    if is_capacity_or_plan_claim(claim, prose):
        return "产能、规划或建设进度容易被拔高为已经完全释放的经营事实"
    if stype in MARKET_DATABASE_SOURCE_TYPES:
        return "行情或市场数据库数据需要注明日期和测算口径，避免被读成长期确定事实"
    if stype in INDUSTRY_DATA_SOURCE_TYPES:
        return "行业数据或二级转引需要保留来源性质，避免被写成公司披露事实"
    if tier == "broker" or stype in BROKER_SOURCE_TYPES:
        return "二级来源或券商转引被写成公司公告里的确定事实"
    if tier in {"media", "market"} or stype in MEDIA_SOURCE_TYPES:
        return "媒体、市场讨论或社交平台信息被写成确定事实"
    if usage in AUTHOR_INFERENCE_USAGE:
        return "作者推断被写成已经证实的结论"
    if usage in {"company_statement", "management_guidance"}:
        return "公司表述或管理层口径被写成独立事实，读者无法区分来源性质"
    return "正文语气可能超过证据强度"


def suggested_wording(claim: dict, prose: str) -> str:
    manual = claim_list_field(claim, "suggested_wording")
    if manual:
        return manual[0]

    required_caveats = claim_list_field(claim, "required_caveat")
    usage = usage_type(claim)
    tier = source_tier(claim)
    stype = source_type(claim)
    text = claim_value_text(claim).rstrip("。；;")

    if is_capacity_or_plan_claim(claim, prose):
        prefix = "有券商研报转引称" if tier == "broker" or stype in BROKER_SOURCE_TYPES else "公司披露称"
        caveat = "这不等同于当前产能已经完全释放，后续仍取决于设备投入和需求消化"
        return f"{prefix}，{text}；{caveat}。"

    if usage in {"company_statement", "management_guidance"}:
        prefix = "管理层表示" if usage == "management_guidance" else "公司披露称"
        return f"{prefix}，{text}。"

    if stype in MARKET_DATABASE_SOURCE_TYPES:
        period = str(claim.get("period", "")).strip()
        prefix = f"按{period}市场数据测算" if period else "按市场数据测算"
        return f"{prefix}，{text}。"

    if stype in INDUSTRY_DATA_SOURCE_TYPES:
        prefix = "据券商研报转引的行业数据" if tier == "broker" else "据行业数据"
        return f"{prefix}，{text}。"

    if usage in BROKER_USAGE or tier == "broker" or stype in BROKER_SOURCE_TYPES:
        prefix = "据券商研报估算" if usage in BROKER_USAGE else "有券商研报转引称"
        return f"{prefix}，{text}。"

    if tier in {"media", "market"} or stype in MEDIA_SOURCE_TYPES:
        return f"媒体报道或市场讨论称，{text}。"

    if usage == "author_calculation":
        return f"按公开数据测算，{text}。"

    if usage in AUTHOR_INFERENCE_USAGE:
        return f"这可能意味着{text}，后续仍需公开数据验证。"

    if required_caveats:
        return f"{text}；{required_caveats[0]}。"
    return ""


def append_wording_warning(
    warnings: list[str],
    idx: int,
    line: str,
    claim_id: str,
    claim: dict,
    problem: str,
    prose: str,
) -> None:
    context = f"usage_type={usage_type(claim) or '未填'}"
    parts = [
        f"L{idx}: {claim_id} 来源/语气复核：{problem}",
        context,
        f"风险：{claim_risk(claim, prose)}",
    ]
    advice = suggested_wording(claim, prose)
    if advice:
        parts.append(f"建议改写：{advice}")
    parts.append(f"当前：{line.strip()[:70]}")
    warnings.append("；".join(parts))


def check_claim_wording(idx: int, line: str, claim_id: str, claim: dict, warnings: list[str]) -> None:
    usage = usage_type(claim)
    tier = source_tier(claim)
    stype = source_type(claim)
    allowed_words = claim_list_field(claim, "allowed_wording")
    required_caveats = claim_list_field(claim, "required_caveat")
    prose = strip_fact_refs(strip_inline_code(line))

    allowed_missing = False
    if allowed_words:
        allowed_missing = not any(word in prose for word in allowed_words)
        if allowed_missing:
            append_wording_warning(
                warnings,
                idx,
                line,
                claim_id,
                claim,
                f"正文未使用 allowed_wording 限定语（{' / '.join(allowed_words)}）",
                prose,
            )

    for caveat in required_caveats:
        if caveat not in prose:
            append_wording_warning(
                warnings,
                idx,
                line,
                claim_id,
                claim,
                f"正文缺少 required_caveat：{caveat}",
                prose,
            )

    if usage in BROKER_USAGE or tier == "broker" or stype in BROKER_SOURCE_TYPES:
        if not BROKER_CUE_RE.search(prose) and not allowed_missing:
            append_wording_warning(
                warnings,
                idx,
                line,
                claim_id,
                claim,
                "来自券商/外部估算，但正文未标明估算或转引语气",
                prose,
            )
        if CERTAIN_WORDING_RE.search(prose):
            append_wording_warning(
                warnings,
                idx,
                line,
                claim_id,
                claim,
                "券商/外部估算被写成确定事实",
                prose,
            )

    if tier in {"media", "market"} or stype in MEDIA_SOURCE_TYPES:
        if not MEDIA_CUE_RE.search(prose) and not allowed_missing:
            append_wording_warning(
                warnings,
                idx,
                line,
                claim_id,
                claim,
                "来自媒体/市场讨论，但正文未标明来源性质",
                prose,
            )
        if CERTAIN_WORDING_RE.search(prose):
            append_wording_warning(
                warnings,
                idx,
                line,
                claim_id,
                claim,
                "媒体/市场讨论被写成确定事实",
                prose,
            )

    if usage in AUTHOR_INFERENCE_USAGE:
        if CERTAIN_WORDING_RE.search(prose):
            append_wording_warning(
                warnings,
                idx,
                line,
                claim_id,
                claim,
                "作者推断使用了确定性措辞",
                prose,
            )
        elif not INFERENCE_CUE_RE.search(prose):
            append_wording_warning(
                warnings,
                idx,
                line,
                claim_id,
                claim,
                "作者推断缺少“可能/指向/后续验证”等限制语",
                prose,
            )


def check_fact_refs(
    idx: int,
    line: str,
    claims: dict[str, dict],
    warnings: list[str],
    errors: list[str],
) -> None:
    refs = parse_fact_refs(line)
    if not refs:
        return

    placeholder_match = FACT_VALUE_PLACEHOLDER_RE.search(line)
    table_cell_match = FACT_ONLY_TABLE_CELL_RE.search(line)
    if placeholder_match or table_cell_match:
        matched = (placeholder_match or table_cell_match).group(0)
        errors.append(
            f"L{idx}: fact 绑定不能替代正文数字或表格值：`{matched}`。"
            "请先把事实值写成读者可见文本，再在完整数字/判断后绑定，"
            "例如 `资本开支达 1,263.79 亿元。{fact:capex_2026}`。"
        )

    line_periods = canonical_periods(strip_fact_refs(line))
    for ref in refs:
        if not CLAIM_ID_RE.fullmatch(ref):
            errors.append(
                f"L{idx}: fact 引用 `{ref or '<空>'}` 格式错误；只能引用 facts.json claims[].claim_id，"
                "claim_id 需以字母开头且只含字母/数字/._-，不得使用中文事实名或 other_facts.name"
            )
            continue
        claim = claims.get(ref)
        if claim is None:
            errors.append(f"L{idx}: 未知 fact 引用 `{ref}`；请补入 facts.json claims，或改为已有 claim_id")
            continue
        periods = claim_periods(claim)
        if line_periods and periods and line_periods.isdisjoint(periods):
            advice = suggested_wording(claim, strip_fact_refs(line))
            warnings.append(
                f"L{idx}: `{ref}` 期间口径复核：claim.period={claim.get('period')}，正文显式期间为 {sorted(line_periods)}；"
                f"风险：旧期间数据可能被当成当前事实；建议：若正文在讲当前判断，请补当前期间 claim，或在正文写明“据{claim.get('period')}来源/转引”；"
                f"{'建议改写：' + advice + '；' if advice else ''}当前：{line.strip()[:70]}"
            )
        check_claim_wording(idx, line, ref, claim, warnings)


def is_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def anchor_documented(facts: dict | None, metric_keywords: tuple[str, ...], value_keys: tuple[str, ...]) -> bool | None:
    """Check whether an expectation anchor for a metric exists in facts.json.

    True if consensus has a numeric value for the metric, or any string field
    documents a named anchor (metric keyword + 预期 + digits in one string).
    None if facts.json unavailable.
    """
    if facts is None:
        return None
    consensus = facts.get("consensus", {})
    if isinstance(consensus, dict):
        for key in value_keys:
            value = consensus.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return True
    for s in collect_strings(facts):
        if "预期" in s and any(k in s for k in metric_keywords) and re.search(r"\d", s):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint report markdown for tone, scope, source, and fact-binding issues."
    )
    parser.add_argument("report", help="Path to source markdown report")
    parser.add_argument("facts", nargs="?", default=None, help="Optional facts.json for source-aware checks")
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    facts_path = Path(args.facts) if args.facts else None
    if not report_path.exists():
        print(f"[错误] 找不到报告文件: {report_path}")
        return 1

    facts = load_facts(facts_path)
    claims = collect_claims(facts)
    a_share = is_a_share(facts)
    profit_anchor = anchor_documented(facts, ("净利", "利润", "EPS", "每股收益"), ("net_profit_yi", "eps_yuan"))
    revenue_anchor = anchor_documented(facts, ("收入", "营收"), ("revenue_yi",))
    lines = report_path.read_text(encoding="utf-8").splitlines()

    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []

    if facts_path is not None and not claims:
        warnings.append("facts.json 未提供 claims 数组，无法执行正文数字与事实表绑定提示")

    in_comment = False
    in_code = False
    body_lines: list[tuple[int, str]] = []
    for idx, raw in enumerate(lines, start=1):
        line = raw
        if is_fence(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        if "<!--" in line and "-->" not in line:
            in_comment = True
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        body_lines.append((idx, line))

    text = "\n".join(line for _, line in body_lines)

    in_sources_section = False
    for idx, line in body_lines:
        stripped_line = line.strip()
        if (
            stripped_line.startswith("## 数据来源")
            or stripped_line == "文中引用对应以下来源："
        ):
            in_sources_section = True
        elif in_sources_section and stripped_line.startswith("## ") and not stripped_line.startswith("## 数据来源"):
            in_sources_section = False

        check_line = line
        fact_refs = parse_fact_refs(check_line)
        if fact_refs and facts_path is None:
            errors.append(f"L{idx}: 正文含 fact 绑定标记但 finalize/lint 未提供 facts.json：{line.strip()[:70]}")
        elif fact_refs and facts_path is not None and not claims:
            errors.append(f"L{idx}: 正文含 fact 绑定标记，但 facts.json 无有效 claims：{line.strip()[:70]}")
        elif fact_refs:
            check_fact_refs(idx, check_line, claims, warnings, errors)
        if claims and not in_sources_section and not fact_refs and is_numeric_fact_line(check_line):
            warnings.append(
                f"L{idx}: 正文/表格含数字但未绑定 `{{fact:claim_id}}`，请复核是否为关键证据数字：{line.strip()[:70]}"
            )

        if DRAFT_CORNER_QUOTE_RE.search(strip_inline_code(check_line)):
            errors.append(
                f"L{idx}: 最终 Markdown 仍含草稿引号「」/『』，请先运行 python3 scripts/normalize_report.py {report_path}：{line.strip()[:60]}"
            )
        if INLINE_FOOTNOTE_RE.search(strip_inline_code(check_line)):
            errors.append(
                f"L{idx}: 正文不得使用 [^n] 脚注角标；请删除角标，并在文末「数据来源」统一列出来源：{line.strip()[:60]}"
            )
        for match in JUDGMENT_RE.finditer(check_line):
            errors.append(f"L{idx}: 自有判断表述「{match.group(0)}」违反语气三句式")
        for match in UNNAMED_ANCHOR_RE.finditer(check_line):
            errors.append(f"L{idx}: 无名锚表述「{match.group(0)}」")
        for match in PLACEHOLDER_RE.finditer(check_line):
            errors.append(f"L{idx}: 残留占位符「{match.group(0)}」")
        if RATING_RE.search(check_line) and not ATTRIBUTION_RE.search(check_line):
            errors.append(f"L{idx}: 疑似自有评级（同一行无『引自/转引』）：{line.strip()[:60]}")
        if UPSIDE_RE.search(check_line) and not ATTRIBUTION_RE.search(check_line):
            warnings.append(f"L{idx}: 「上行/下行空间」无同行转引标注，疑似用机构目标价推导自有结论")
        if US_FILING_RE.search(check_line):
            if a_share is True:
                errors.append(f"L{idx}: A 股标的出现美股口径词：{US_FILING_RE.search(check_line).group(0)}")
            elif a_share is None:
                warnings.append(f"L{idx}: 出现美股口径词（未提供 facts.json，无法判断标的市场）")
        if BARE_WE_RE.search(check_line) and not JUDGMENT_RE.search(check_line):
            warnings.append(f"L{idx}: 出现「我们」，请确认非自有判断：{line.strip()[:50]}")
        if PROFIT_BEAT_RE.search(check_line):
            if profit_anchor is False:
                errors.append(f"L{idx}: 利润类「超/低于预期」措辞但 facts.json 无利润锚（红线 7，降级为 vs 同比措辞）：{line.strip()[:60]}")
            elif profit_anchor is None:
                warnings.append(f"L{idx}: 利润类超预期/不达预期措辞（未提供 facts.json，无法核验锚点）")
        if REVENUE_BEAT_RE.search(check_line):
            if revenue_anchor is False:
                errors.append(f"L{idx}: 收入类「超/低于预期」措辞但 facts.json 无收入锚（红线 7）：{line.strip()[:60]}")
            elif revenue_anchor is None:
                warnings.append(f"L{idx}: 收入类超预期/不达预期措辞（未提供 facts.json，无法核验锚点）")
        for match in GUESS_RE.finditer(check_line):
            errors.append(f"L{idx}: 无算式推算值「{match.group(0)}…」（红线 3：写不出算式的数字不进正文，应写『未获取』或给出测算算式）")
        for match in INTERNAL_RE.finditer(check_line):
            errors.append(f"L{idx}: 内部流程词「{match.group(0)}」出现在成品报告（红线 10，改用读者可见语言，派生数字用『测算』）")
        for match in INTERNAL_LEVEL_RE.finditer(check_line):
            errors.append(f"L{idx}: 内部推理标签「{match.group(0)}」出现在成品报告，请改写为自然语言")
        if DRAFT_STRUCTURE_RE.search(strip_inline_code(check_line)):
            errors.append(f"L{idx}: 底稿卡片句式残留在成品报告：{line.strip()[:60]}")
        prose_line = strip_inline_code(check_line)
        if ASCII_QUOTED_HAN_RE.search(prose_line):
            errors.append(f"L{idx}: 中文词句被英文直引号包裹，草稿请改用「」后运行 normalize_report.py：{line.strip()[:60]}")
        elif ASCII_DOUBLE_QUOTE_RE.search(prose_line) and HAN_RE.search(prose_line):
            warnings.append(f"L{idx}: 中文正文含英文直引号；若不是代码/JSON/字段语法，建议草稿改用「」后运行 normalize_report.py：{line.strip()[:60]}")

    watch_count = len(WATCHLIST_RE.findall(text))
    if watch_count == 0:
        warnings.append("全文无「后续应关注」——缺少方向指引（关注清单为固定交付物）")
    url_count = len(URL_RE.findall(text))
    if url_count == 0:
        warnings.append("参考文献无任何可点击链接（http/https）——确认来源确无公开链接并已写明平台名")
    if "未获取" not in text:
        warnings.append("全文无「未获取」声明——若无任何数据缺口请在来源说明中写明『无未获取项』")

    infos.append(f"可点击链接 {url_count} 个；「后续应关注」{watch_count} 处；正文 {len(text)} 字符")
    if a_share is None:
        infos.append("未提供 facts.json：美股口径词检查降级为警告")

    for msg in infos:
        print(f"[信息] {msg}")
    for msg in warnings:
        print(f"[警告] {msg}")
    for msg in errors:
        print(f"[错误] {msg}")
    print(f"汇总: {len(errors)} 错误, {len(warnings)} 警告")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
