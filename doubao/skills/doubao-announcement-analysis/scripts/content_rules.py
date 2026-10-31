"""Shared expression, source-attribution, and claim-reference rules.

Imported by render_structured_report.py to preserve the previous content gates.
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
# 成品报告禁止出现的内部流程词/文件名
INTERNAL_RE = re.compile(
    r"_INTERNAL_DO_NOT_DELIVER|facts\.json|check_facts|lint_report|normalize_report|"
    r"make_display_markdown|finalize_report|make_docx|report\.json|SUMMARY\.md|"
    r"DO_NOT_DELIVER__|FINAL_REPLY_BODY|00_RESUME_HERE|"
    r"delivery-pipeline|writing-style|markets-taxonomy|linked-signals|"
    r"output-rendering|output-formats|task-router|data-grading-and-citation|data-collection-protocol|"
    r"中间产物|交付清单|复算|门禁\s?[12１２]?"
)
# 内部分类/推理标签（skill 内部术语，不应出现在成品中）
INTERNAL_LEVEL_RE = re.compile(
    r"playbook|Tier\s*[123１２３](?![A-Za-z0-9])|"
    r"tier[123]-[a-z-]+|"
    r"深度\s*[0-4０-４零一二三四](?![A-Za-z])|当前深度|补到深度|推到深度|推理深度|"
    r"一级来源|二级来源|三级来源(?=[的，。；\s]|$)"
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
# 无算式推算值
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
BROKER_USAGE = {"broker_estimate", "broker_forecast"}
AUTHOR_INFERENCE_USAGE = {"author_inference"}
MEDIA_SOURCE_TYPES = {"media", "news", "social", "forum", "xueqiu", "toutiao"}
BROKER_SOURCE_TYPES = {"broker_research", "broker_consensus", "sellside_research"}


def load_facts(facts_path: Path | None) -> dict | None:
    if facts_path is None:
        return None
    try:
        return json.loads(facts_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_a_share(facts: dict | None) -> bool | None:
    """True=A股, False=非A股, None=unknown（没有 facts.json 或没有 meta 信息）。"""
    if facts is None:
        return None
    meta = facts.get("meta", {})
    market = meta.get("market")
    if market:
        return market == "A股"
    code = str(meta.get("code", ""))
    return bool(re.search(r"\.(SZ|SH|BJ)\b", code, re.IGNORECASE)) if code else None


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


def claim_risk(claim: dict, prose: str) -> str:
    usage = usage_type(claim)
    tier = source_tier(claim)
    stype = source_type(claim)
    if tier == "broker" or stype in BROKER_SOURCE_TYPES or usage in BROKER_USAGE:
        return "二级来源或券商转引被写成公司公告里的确定事实"
    if tier in {"media", "market"} or stype in MEDIA_SOURCE_TYPES:
        return "媒体、市场讨论或投资者评论区信息被写成确定事实"
    if usage in AUTHOR_INFERENCE_USAGE:
        return "作者推断被写成已经证实的结论"
    if usage in {"company_statement", "management_guidance"}:
        return "公司互动平台回复或管理层口径被写成正式公告事实，读者无法区分来源性质"
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

    if usage in {"company_statement", "management_guidance"}:
        prefix = "公司在互动平台回复称" if usage == "management_guidance" else "公司披露称"
        return f"{prefix}，{text}。"

    if usage in BROKER_USAGE or tier == "broker" or stype in BROKER_SOURCE_TYPES:
        prefix = "据券商研报估算" if usage in BROKER_USAGE else "有券商研报转引称"
        return f"{prefix}，{text}。"

    if tier in {"media", "market"} or stype in MEDIA_SOURCE_TYPES:
        return f"媒体报道或投资者评论区讨论称，{text}。"

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
                warnings, idx, line, claim_id, claim,
                f"正文未使用 allowed_wording 限定语（{' / '.join(allowed_words)}）", prose,
            )

    for caveat in required_caveats:
        if caveat not in prose:
            append_wording_warning(
                warnings, idx, line, claim_id, claim,
                f"正文缺少 required_caveat：{caveat}", prose,
            )

    if usage in BROKER_USAGE or tier == "broker" or stype in BROKER_SOURCE_TYPES:
        if not BROKER_CUE_RE.search(prose) and not allowed_missing:
            append_wording_warning(
                warnings, idx, line, claim_id, claim,
                "来自券商/外部估算，但正文未标明估算或转引语气", prose,
            )
        if CERTAIN_WORDING_RE.search(prose):
            append_wording_warning(
                warnings, idx, line, claim_id, claim, "券商/外部估算被写成确定事实", prose,
            )

    if tier in {"media", "market"} or stype in MEDIA_SOURCE_TYPES:
        if not MEDIA_CUE_RE.search(prose) and not allowed_missing:
            append_wording_warning(
                warnings, idx, line, claim_id, claim,
                "来自媒体/投资者评论区，但正文未标明来源性质", prose,
            )
        if CERTAIN_WORDING_RE.search(prose):
            append_wording_warning(
                warnings, idx, line, claim_id, claim, "媒体/投资者评论区讨论被写成确定事实", prose,
            )

    if usage in AUTHOR_INFERENCE_USAGE:
        if CERTAIN_WORDING_RE.search(prose):
            append_wording_warning(
                warnings, idx, line, claim_id, claim, "作者推断使用了确定性措辞", prose,
            )
        elif not INFERENCE_CUE_RE.search(prose):
            append_wording_warning(
                warnings, idx, line, claim_id, claim,
                "作者推断缺少\u201c可能/指向/后续验证\u201d等限制语", prose,
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
            "例如 `标的公司2025年净利润4187万元。{fact:np_2025}`。"
        )

    line_periods = canonical_periods(strip_fact_refs(line))
    for ref in refs:
        if not CLAIM_ID_RE.fullmatch(ref):
            errors.append(
                f"L{idx}: fact 引用 `{ref or '<空>'}` 格式错误；只能引用 facts.json claims[].claim_id，"
                "claim_id 需以字母开头且只含字母/数字/._-"
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
                f"风险：旧期间数据可能被当成当前事实；"
                f"{'建议改写：' + advice + '；' if advice else ''}当前：{line.strip()[:70]}"
            )
        check_claim_wording(idx, line, ref, claim, warnings)


def is_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def anchor_documented(facts: dict | None, metric_keywords: tuple[str, ...]) -> bool | None:
    """检查 facts.json 里是否有对应指标的预期锚（None=facts.json 不可用）。"""
    if facts is None:
        return None
    for s in collect_strings(facts):
        if "预期" in s and any(k in s for k in metric_keywords) and re.search(r"\d", s):
            return True
    return False

