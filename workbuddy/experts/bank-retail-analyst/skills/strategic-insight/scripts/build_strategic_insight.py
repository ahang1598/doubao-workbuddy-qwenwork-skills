#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from paths import (
    DATA_DIR,
    EXTRACTED_TEXT_DIR,
    OUTPUT_DIR,
    PARTIAL_DIR,
    TEXT_DIR,
    ensure_dirs,
    get_skill_config_file,
)


BANK_ORDER = ["中信", "招商", "兴业", "平安", "浦发", "光大", "民生"]

TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "财富管理": ("财富管理", "大财富管理", "财富顾问", "财富业务"),
    "私人银行": ("私人银行", "私行"),
    "养老金融": ("养老金融", "养老业务"),
    "个人养老金": ("个人养老金",),
    "信用卡": ("信用卡", "银行卡"),
    "零售客户": ("零售客户", "个人客户"),
    "AUM": ("AUM", "管理零售客户总资产", "零售管理资产", "管理资产"),
    "财富客户": ("财富客户", "贵宾客户", "金葵花", "富裕客户"),
    "数字金融": ("数字金融", "数智化", "数字化", "AI", "人工智能"),
    "综合金融": ("综合金融", "协同", "生态"),
    "交易结算": ("交易结算", "支付结算"),
    "跨境服务": ("跨境服务", "跨境金融", "外汇服务"),
    "综合融资": ("综合融资", "投行", "撮合"),
    "存款": ("存款", "负债"),
    "贷款": ("贷款", "个贷", "零售信贷"),
    "风险管理": ("风险管理", "风控", "不良", "资产质量"),
    "科技金融": ("科技金融",),
    "普惠金融": ("普惠金融",),
}

RETAIL_SECTION_WEIGHTS: dict[str, int] = {
    "零售": 12,
    "财富": 10,
    "私人银行": 10,
    "信用卡": 9,
    "客户经营": 8,
    "零售金融": 10,
    "养老": 8,
    "AUM": 8,
    "业务综述": 6,
    "经营情况": 5,
    "战略": 4,
    "数字": 4,
    "数智": 4,
}

RETAIL_NEGATIVE_WEIGHTS: dict[str, int] = {
    "公司治理": 10,
    "风险管理": 8,
    "财务报告": 8,
    "审计报告": 8,
    "股份变动": 7,
    "股东情况": 7,
    "释义": 6,
}

ORG_SECTION_WEIGHTS: dict[str, int] = {
    "组织架构": 14,
    "部门设置": 12,
    "治理架构": 10,
    "公司治理": 8,
    "报告期末部门设置情况": 14,
    "业务综述": 4,
    "零售": 5,
    "财富": 4,
    "私人银行": 4,
    "信用卡": 4,
    "数字金融": 4,
}

ORG_DEPARTMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "零售银行业务总部": ("零售银行业务总部", "零售银行总部"),
    "零售金融部": ("零售金融部", "零售金融业务部"),
    "零售板块": ("零售板块",),
    "零售平台部": ("零售平台部",),
    "零售业务部": ("零售业务部",),
    "财富管理部": ("财富管理部", "财富平台部", "财富业务部"),
    "私人银行部": ("私人银行部", "私人银行中心", "私人银行直营中心"),
    "信用卡中心": ("信用卡中心", "信用卡部"),
    "消费金融部": ("消费金融部",),
    "养老金融事业部": ("养老金融事业部", "养老金融部"),
    "数字金融部": ("数字金融部", "数字银行部", "网络金融部"),
}

GENERIC_DEPARTMENT_RE = re.compile(
    r"(零售[^，。；\n的]{0,8}(?:部|中心|业务总部|事业部|板块|直营中心)|"
    r"财富[^，。；\n的]{0,8}(?:部|中心|业务总部|事业部|板块|直营中心)|"
    r"私人银行[^，。；\n的]{0,8}(?:部|中心|业务总部|事业部|板块|直营中心)|"
    r"信用卡[^，。；\n的]{0,8}(?:部|中心|业务总部|事业部|板块|直营中心)|"
    r"数字金融[^，。；\n的]{0,8}(?:部|中心|业务总部|事业部|板块|直营中心)|"
    r"网络金融[^，。；\n的]{0,8}(?:部|中心|业务总部|事业部|板块|直营中心)|"
    r"养老金融[^，。；\n的]{0,8}(?:部|中心|业务总部|事业部|板块|直营中心))"
)

HEADING_RE = re.compile(r"^(#{1,6})\s*(.+?)\s*$")
YEAR_RE = re.compile(r"(\d{4})")


@dataclass
class Section:
    title: str
    level: int
    body: str
    score: int = 0
    matches: tuple[str, ...] = ()


def period_sort_key(label: str) -> tuple[int, int]:
    m = YEAR_RE.search(label)
    year = int(m.group(1)) if m else 0
    if "年度" in label:
        kind = 0
    elif "半年" in label:
        kind = 1
    elif "三季" in label:
        kind = 2
    elif "一季" in label:
        kind = 3
    else:
        kind = 9
    return year, -kind


def short_to_full() -> dict[str, str]:
    cfg = yaml.safe_load(get_skill_config_file("skill4", "banks.yaml").read_text())
    result = {cfg["base_bank"]["short_name"]: cfg["base_bank"]["name"]}
    for item in cfg.get("peer_banks", []):
        result[item["short_name"]] = item["name"]
    return result


def latest_annual_dirs() -> dict[str, list[tuple[str, Path]]]:
    result: dict[str, list[tuple[str, Path]]] = {}
    for bank in BANK_ORDER:
        bank_dir = EXTRACTED_TEXT_DIR / bank
        periods: list[tuple[str, Path]] = []
        if bank_dir.exists():
            for path in bank_dir.iterdir():
                if path.is_dir() and not path.name.startswith("_") and "年度" in path.name:
                    periods.append((path.name.split("_", 1)[1], path))
        result[bank] = sorted(periods, key=lambda item: period_sort_key(item[0]))
    return result


def find_md_full(period_dir: Path) -> Path | None:
    matches = sorted(period_dir.glob("*_md_full.md"))
    return matches[0] if matches else None


def split_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    current_title = "前言"
    current_level = 0
    current_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        m = HEADING_RE.match(line.strip())
        if m:
            if current_lines:
                sections.append(
                    Section(
                        title=current_title,
                        level=current_level,
                        body="\n".join(current_lines).strip(),
                    )
                )
            current_title = m.group(2).strip()
            current_level = len(m.group(1))
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append(
            Section(
                title=current_title,
                level=current_level,
                body="\n".join(current_lines).strip(),
            )
        )
    return [sec for sec in sections if sec.body]


def score_section(
    section: Section,
    positive_weights: dict[str, int],
    negative_weights: dict[str, int] | None = None,
) -> Section:
    score = 0
    matches: list[str] = []
    title = section.title
    body = section.body
    for kw, weight in positive_weights.items():
        title_hits = title.count(kw)
        body_hits = body.count(kw)
        if title_hits or body_hits:
            matches.append(kw)
        score += title_hits * weight * 3
        score += min(body_hits, 8) * weight
    for kw, weight in (negative_weights or {}).items():
        title_hits = title.count(kw)
        body_hits = body.count(kw)
        score -= title_hits * weight * 3
        score -= min(body_hits, 4) * weight
    section.score = score
    section.matches = tuple(sorted(set(matches)))
    return section


def extract_keyword_windows(text: str, keywords: tuple[str, ...], *, window: int = 1) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    hits: list[str] = []
    seen: set[str] = set()
    for idx, para in enumerate(paragraphs):
        if any(kw in para for kw in keywords):
            start = max(0, idx - window)
            end = min(len(paragraphs), idx + window + 1)
            chunk = "\n\n".join(paragraphs[start:end])
            key = chunk[:240]
            if key not in seen:
                seen.add(key)
                hits.append(chunk)
    return hits


def select_retail_sections(text: str) -> list[Section]:
    sections = [score_section(sec, RETAIL_SECTION_WEIGHTS, RETAIL_NEGATIVE_WEIGHTS) for sec in split_sections(text)]
    selected = [
        sec for sec in sections
        if sec.score >= 18 or (sec.score >= 8 and any(k in sec.matches for k in ("零售", "财富", "信用卡", "客户经营", "AUM", "养老")))
    ]
    selected = sorted(selected, key=lambda sec: (-sec.score, sec.title))[:10]
    if selected:
        return selected

    fallback_sections = []
    for idx, chunk in enumerate(
        extract_keyword_windows(text, ("零售", "财富管理", "私人银行", "信用卡", "AUM", "养老金融", "个人养老金"))
    ):
        fallback_sections.append(
            Section(title=f"fallback-{idx + 1}", level=0, body=chunk, score=10, matches=("fallback",))
        )
    return fallback_sections[:8]


def select_org_sections(text: str) -> list[Section]:
    sections = [score_section(sec, ORG_SECTION_WEIGHTS, RETAIL_NEGATIVE_WEIGHTS) for sec in split_sections(text)]
    selected = [
        sec for sec in sections
        if sec.score >= 16 or ("公司治理" in sec.title and sec.score >= 6)
    ]
    selected = sorted(selected, key=lambda sec: (-sec.score, sec.title))[:8]
    if selected:
        return selected
    return [
        Section(title=f"org-fallback-{idx + 1}", level=0, body=chunk, score=8, matches=("fallback",))
        for idx, chunk in enumerate(extract_keyword_windows(text, ("组织架构", "部门设置", "公司治理", "零售", "财富", "信用卡", "私人银行")))
    ][:6]


def count_terms(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for canonical, aliases in TERM_ALIASES.items():
        total = 0
        for alias in aliases:
            total += text.count(alias)
        if total:
            counts[canonical] = total
    return counts


def extract_departments(text: str) -> list[str]:
    found: set[str] = set()
    for canonical, aliases in ORG_DEPARTMENT_ALIASES.items():
        if any(alias in text for alias in aliases):
            found.add(canonical)
    for raw in GENERIC_DEPARTMENT_RE.findall(text):
        raw = raw.strip("：:，。；、 ")
        found.add(raw)
    return sorted(
        dept for dept in found
        if "业务分部" not in dept and not dept.endswith("业务")
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def latest_period(mapping: dict[str, Any]) -> str | None:
    periods = [k for k in mapping if "年度" in k]
    if not periods:
        periods = list(mapping)
    if not periods:
        return None
    return sorted(periods, key=period_sort_key)[-1]


def previous_period(mapping: dict[str, Any], current: str | None) -> str | None:
    if not current:
        return None
    periods = sorted([k for k in mapping if "年度" in k], key=period_sort_key)
    if current not in periods:
        return periods[-2] if len(periods) >= 2 else None
    idx = periods.index(current)
    return periods[idx - 1] if idx > 0 else None


def parse_numeric_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    cleaned = value.replace(",", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not m:
        return None
    num = float(m.group(0))
    if "万亿" in cleaned:
        return num * 10000
    if "亿户" in cleaned:
        return num * 10000
    if "亿张" in cleaned:
        return num * 10000
    return num


def first_not_none(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def _text_period_end_value(record: dict[str, Any]) -> float | None:
    return parse_numeric_value(
        first_not_none(
            record.get("period_end_value"),
            record.get("value"),
        )
    )


def metric_change(record: dict[str, Any]) -> float | None:
    for key in ("change_pct", "yoy_pct", "change"):
        value = parse_numeric_value(record.get(key))
        if value is not None:
            return value
    return None


def normalize_text_metrics(payload: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    by_period = payload.get("by_period", {})
    for period, block in by_period.items():
        metrics = block.get("metrics", [])
        period_map: dict[str, dict[str, Any]] = {}
        for item in metrics:
            name = item.get("standard_name") or item.get("name") or item.get("metric") or ""
            record = dict(item)
            values = item.get("values") or []
            selected = next(
                (value for value in values if value.get("period_label") == period),
                values[0] if values else {},
            )
            if isinstance(selected, dict):
                record.update(selected)
            if "AUM" in name:
                period_map["aum"] = record
            elif "零售客户" in name or "个人客户" in name:
                period_map["retail_customers"] = record
            elif "私行客户" in name or "私人银行客户" in name:
                period_map["private_bank_customers"] = record
            elif "财富管理手续费" in name or "零售财富管理手续费" in name or "理财业务手续费" in name:
                period_map["wealth_fee_income"] = record
            elif "信用卡交易" in name:
                period_map["credit_card_volume"] = record
            elif "信用卡贷款余额" in name:
                period_map["credit_card_loan_balance"] = record
        result[period] = period_map
    return result


def yoy(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev in (None, 0):
        return None
    return (curr - prev) / prev * 100.0


def format_pct(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "n/a"
    return f"{value:+.2f}%"


def format_num(value: float | None, unit: str = "") -> str:
    if value is None or math.isnan(value):
        return "n/a"
    if abs(value) >= 1000:
        return f"{value:,.2f}{unit}"
    return f"{value:.2f}{unit}"


def sanitize_growth(value: float | None, *, upper_bound: float = 200.0) -> float | None:
    if value is None:
        return None
    if abs(value) > upper_bound:
        return None
    return value


def get_latest_md_texts(periods: list[tuple[str, Path]]) -> tuple[tuple[str, str] | None, tuple[str, str] | None]:
    annuals: list[tuple[str, str]] = []
    for label, path in periods:
        md = find_md_full(path)
        if md:
            annuals.append((label, md.read_text()))
    if not annuals:
        return None, None
    annuals = sorted(annuals, key=lambda item: period_sort_key(item[0]))
    latest = annuals[-1]
    prev = annuals[-2] if len(annuals) >= 2 else None
    return latest, prev


def build_freqword_payload(
    bank_periods: dict[str, list[tuple[str, Path]]],
    base_bank: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"banks": {}, "cross_bank_trends": [], "base_specific": [], "bank_specific": {}}
    doc_freq: Counter[str] = Counter()
    total_counts: Counter[str] = Counter()
    cross_period_comparison: dict[str, str] = {}

    for bank in BANK_ORDER:
        latest_pair, prev_pair = get_latest_md_texts(bank_periods.get(bank, []))
        if latest_pair is None:
            payload["banks"][bank] = {"top_words": [], "retail_focus": [], "matched_sections": []}
            payload["bank_specific"][bank] = []
            continue

        _, latest_text = latest_pair
        latest_sections = select_retail_sections(latest_text)
        latest_blob = "\n\n".join(sec.body for sec in latest_sections)
        latest_counts = count_terms(latest_blob)

        prev_counts: Counter[str] = Counter()
        if prev_pair is not None:
            _, prev_text = prev_pair
            prev_sections = select_retail_sections(prev_text)
            prev_blob = "\n\n".join(sec.body for sec in prev_sections)
            prev_counts = count_terms(prev_blob)

        top_terms = latest_counts.most_common(8)
        retail_focus = [term for term, _ in top_terms[:5]]
        top_words = []
        for term, count in top_terms:
            prev_count = prev_counts.get(term, 0)
            if prev_count == 0 and count > 0:
                trend = "up"
            elif count > prev_count:
                trend = "up"
            elif count < prev_count:
                trend = "down"
            else:
                trend = "stable"
            top_words.append({"word": term, "count": count, "trend": trend})

        for term in latest_counts:
            doc_freq[term] += 1
            total_counts[term] += latest_counts[term]

        current_top = set(term for term, _ in top_terms[:5])
        previous_top = set(term for term, _ in prev_counts.most_common(5))
        added = [term for term in current_top if term not in previous_top]
        removed = [term for term in previous_top if term not in current_top]
        if added or removed:
            parts = []
            if added:
                parts.append(f"新增关注：{'、'.join(sorted(added))}")
            if removed:
                parts.append(f"弱化关注：{'、'.join(sorted(removed))}")
            cross_period_comparison[bank] = "；".join(parts)

        payload["banks"][bank] = {
            "top_words": top_words,
            "retail_focus": retail_focus,
            "matched_sections": [sec.title for sec in latest_sections[:6]],
        }

    for bank in BANK_ORDER:
        bank_words = [item["word"] for item in payload["banks"].get(bank, {}).get("top_words", [])]
        specific = [word for word in bank_words if doc_freq[word] <= 2][:5]
        if not specific:
            specific = payload["banks"].get(bank, {}).get("retail_focus", [])[:3]
        payload["bank_specific"][bank] = specific

    payload["cross_bank_trends"] = [
        word for word, _ in total_counts.most_common()
        if doc_freq[word] >= 3
    ][:6]
    payload["base_bank"] = base_bank
    payload["base_specific"] = payload["bank_specific"].get(base_bank, [])
    payload["cross_period_comparison"] = cross_period_comparison
    return payload


def build_org_payload(
    bank_periods: dict[str, list[tuple[str, Path]]],
    full_name_map: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Path]]:
    payload: dict[str, Any] = {"banks": {}, "industry_trends": []}
    detail_paths: dict[str, Path] = {}
    trend_counter: Counter[str] = Counter()

    for bank in BANK_ORDER:
        history: list[dict[str, Any]] = []
        for label, path in bank_periods.get(bank, []):
            md = find_md_full(path)
            if not md:
                continue
            text = md.read_text()
            org_sections = select_org_sections(text)
            combined = "\n\n".join([sec.title + "\n" + sec.body for sec in org_sections])
            departments = extract_departments(combined)
            found_sections = [sec.title for sec in org_sections]
            history.append({
                "year": YEAR_RE.search(label).group(1) if YEAR_RE.search(label) else label,
                "period": label,
                "retail_departments": departments,
                "found_sections": found_sections,
                "text_disclosure_only": bool(found_sections) and not departments,
            })

        current_struct = "公开文本未披露具体零售部门名称，可能主要存在于架构图/图片中"
        change_frequency = "未识别到明确的部门增撤变并"
        latest_action = "建议结合架构图或 OCR 邻近文本复核"
        org_changes: list[dict[str, Any]] = []
        latest_departments: list[str] = []
        latest_detail: dict[str, Any] | None = None
        prev_nonempty: dict[str, Any] | None = None

        for detail in reversed(history):
            if latest_detail is None:
                latest_detail = detail
            if detail["retail_departments"] and not latest_departments:
                latest_departments = detail["retail_departments"]
            elif detail["retail_departments"] and latest_departments and prev_nonempty is None:
                prev_nonempty = detail
                break

        if latest_departments:
            current_struct = "、".join(latest_departments)
        elif latest_detail and latest_detail["found_sections"]:
            current_struct = "命中治理/部门设置章节，但部门名称未文本化披露"

        if latest_departments and prev_nonempty:
            current_set = set(latest_departments)
            prev_set = set(prev_nonempty["retail_departments"])
            for dept in sorted(current_set - prev_set):
                org_changes.append({
                    "type": "新增",
                    "department": dept,
                    "description": f"{latest_detail['year']}年相比{prev_nonempty['year']}年新增：{dept}",
                    "year": latest_detail["year"],
                })
            for dept in sorted(prev_set - current_set):
                org_changes.append({
                    "type": "撤销",
                    "department": dept,
                    "description": f"{latest_detail['year']}年相比{prev_nonempty['year']}年弱化/不再披露：{dept}",
                    "year": latest_detail["year"],
                })
            if org_changes:
                change_frequency = f"近两次可识别披露共 {len(org_changes)} 项变化"
                latest_action = "；".join(change["description"] for change in org_changes[:3])
            else:
                change_frequency = "近两次可识别披露未见部门清单变化"
                latest_action = "零售组织表述总体延续"
        elif latest_detail and latest_detail["found_sections"]:
            change_frequency = "已命中组织章节，但主要为治理描述/图片"
            latest_action = "章节存在，建议结合架构图 OCR 做二次复核"

        for dept in latest_departments:
            if "财富" in dept or "私人银行" in dept:
                trend_counter["财富管理条线强化"] += 1
            if "数字" in dept or "网络金融" in dept:
                trend_counter["数字金融部门设立"] += 1
            if "养老" in dept:
                trend_counter["养老金融组织单列"] += 1

        detail_payload = {
            "org_structure_changes": org_changes,
            "retail_departments": latest_departments,
            "has_change": bool(org_changes),
            "details": history,
        }
        detail_path = PARTIAL_DIR / f"insight_orgchange_detail_{full_name_map[bank]}.json"
        detail_path.write_text(json.dumps(detail_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        detail_paths[bank] = detail_path

        payload["banks"][bank] = {
            "org_changes": org_changes,
            "retail_org_structure": current_struct,
            "change_frequency": change_frequency,
            "latest_changes": latest_action,
            "retail_departments": latest_departments,
            "found_sections": latest_detail["found_sections"] if latest_detail else [],
        }

    payload["industry_trends"] = [name for name, count in trend_counter.items() if count >= 1]
    return payload, detail_paths


def build_stratreview_payload(
    benchmark: dict[str, Any],
    text_payloads: dict[str, dict[str, Any]],
    freq_payload: dict[str, Any],
    base_bank: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"banks": {}, "cross_bank_execution_summary": "", "base_bank": base_bank}
    latest_year = latest_period(benchmark.get("by_bank", {}).get(base_bank, {}).get("periods", {}))

    aum_growth_samples: list[float] = []
    revenue_growth_samples: list[float] = []
    base_done_not_said: list[str] = []
    base_said_not_done: list[str] = []

    for bank in BANK_ORDER:
        bench_periods = benchmark["by_bank"].get(bank, {}).get("periods", {})
        current_period = latest_period(bench_periods)
        prev_period = previous_period(bench_periods, current_period)
        current = bench_periods.get(current_period, {}) if current_period else {}
        previous = bench_periods.get(prev_period, {}) if prev_period else {}

        text_norm = normalize_text_metrics(text_payloads.get(bank, {}))
        text_current = text_norm.get(current_period or "", {})
        text_previous = text_norm.get(prev_period or "", {})

        aum_now = first_not_none(
            current.get("零售AUM"),
            _text_period_end_value(text_current.get("aum") or {}),
        )
        aum_prev = first_not_none(
            previous.get("零售AUM"),
            _text_period_end_value(text_previous.get("aum") or {}),
        )
        aum_growth = sanitize_growth(yoy(aum_now, aum_prev))
        if aum_growth is None:
            aum_growth = metric_change(text_current.get("aum") or {})
        if aum_growth is not None:
            aum_growth_samples.append(aum_growth)

        retail_revenue_now = current.get("零售分部营业净收入")
        retail_revenue_prev = previous.get("零售分部营业净收入")
        retail_revenue_growth = yoy(retail_revenue_now, retail_revenue_prev)
        if retail_revenue_growth is not None:
            revenue_growth_samples.append(retail_revenue_growth)

        retail_profit_now = current.get("零售分部税前利润")
        retail_profit_prev = previous.get("零售分部税前利润")
        retail_profit_growth = yoy(retail_profit_now, retail_profit_prev)

        customer_growth = metric_change(text_current.get("retail_customers") or {})
        if customer_growth is None:
            customer_now = current.get("零售客户数")
            customer_prev = previous.get("零售客户数")
            customer_growth = yoy(customer_now, customer_prev)

        private_customer_growth = metric_change(text_current.get("private_bank_customers") or {})
        wealth_fee_growth = metric_change(text_current.get("wealth_fee_income") or {})
        npl = current.get("个人贷款-合计-不良贷款率")
        deposit_cost = current.get("个人存款成本率")
        top_terms = [item["word"] for item in freq_payload["banks"].get(bank, {}).get("top_words", [])[:4]]
        last_strategy = "、".join(top_terms) if top_terms else "未从零售/战略章节提炼出稳定主题"

        achieved: list[str] = []
        missed: list[str] = []
        unmentioned: list[str] = []

        if aum_growth is not None and aum_growth >= 8:
            achieved.append(f"AUM 保持较快增长（{format_pct(aum_growth)}）")
        if private_customer_growth is not None and private_customer_growth >= 10:
            achieved.append(f"私行客户扩张较快（{format_pct(private_customer_growth)}）")
        if wealth_fee_growth is not None and wealth_fee_growth >= 10:
            achieved.append(f"财富管理中收增长较快（{format_pct(wealth_fee_growth)}）")
        if retail_revenue_growth is not None and retail_revenue_growth <= -3:
            missed.append(f"零售营收承压（{format_pct(retail_revenue_growth)}）")
        if retail_profit_growth is not None and retail_profit_growth <= -8:
            missed.append(f"零售利润显著下滑（{format_pct(retail_profit_growth)}）")
        if npl is not None and npl >= 1.3:
            missed.append(f"个贷不良率偏高（{npl:.2f}%）")
        if deposit_cost is not None and deposit_cost <= 1.8 and "存款" not in top_terms:
            unmentioned.append(f"负债成本控制相对稳健（个人存款成本率 {deposit_cost:.2f}%）")

        if bank == base_bank:
            base_done_not_said = unmentioned[:]
            base_said_not_done = missed[:]

        payload["banks"][bank] = {
            "last_strategy": last_strategy,
            "execution_assessment": {
                "achieved": achieved or ["当前可识别的执行亮点有限，建议结合更多年度文本复核"],
                "missed": missed or ["未发现明显偏离项或需更多历史样本验证"],
                "unmentioned_but_good": unmentioned,
            },
            "key_metrics_2025": {
                "retail_revenue_growth": retail_revenue_growth,
                "retail_profit_growth": retail_profit_growth,
                "aum_growth": aum_growth,
                "customer_growth": customer_growth,
                "private_customer_growth": private_customer_growth,
                "wealth_fee_growth": wealth_fee_growth,
                "loan_npl": npl,
                "deposit_cost": deposit_cost,
            },
            "period": current_period,
        }

    common_theme = "财富管理与数智化" if "财富管理" in freq_payload.get("cross_bank_trends", []) else "零售战略表述"
    avg_aum = sum(aum_growth_samples) / len(aum_growth_samples) if aum_growth_samples else None
    avg_rev = sum(revenue_growth_samples) / len(revenue_growth_samples) if revenue_growth_samples else None
    payload["cross_bank_execution_summary"] = (
        f"最新年度同业整体围绕{common_theme}展开；"
        f"AUM 平均增速约 {format_pct(avg_aum)}，零售营收平均增速约 {format_pct(avg_rev)}。"
    )
    payload["base_done_not_said"] = base_done_not_said
    payload["base_said_not_done"] = base_said_not_done
    payload["latest_period"] = latest_year
    return payload


def rank_for(benchmark: dict[str, Any], metric: str, period: str, bank: str) -> int | None:
    return benchmark.get("rankings", {}).get(metric, {}).get(period, {}).get(bank, {}).get("rank")


def compose_insights(
    benchmark: dict[str, Any],
    freq_payload: dict[str, Any],
    org_payload: dict[str, Any],
    strat_payload: dict[str, Any],
    base_bank: str,
) -> tuple[list[str], list[dict[str, Any]]]:
    base = strat_payload["banks"][base_bank]
    latest_period = base["period"]
    key = base["key_metrics_2025"]
    by_bank = benchmark["by_bank"][base_bank]["periods"][latest_period]
    revenue_rank = rank_for(benchmark, "零售分部营业净收入", latest_period, base_bank)
    profit_rank = rank_for(benchmark, "零售分部税前利润", latest_period, base_bank)
    aum_growth = key.get("aum_growth")
    revenue_growth = key.get("retail_revenue_growth")
    profit_growth = key.get("retail_profit_growth")
    npl = key.get("loan_npl")
    deposit_cost = key.get("deposit_cost")
    base_specific = freq_payload.get("base_specific") or freq_payload.get("bank_specific", {}).get(base_bank, [])
    org_summary = org_payload["banks"][base_bank]["retail_org_structure"]

    executive_summary = [
        f"{latest_period} 同业零售战略文本仍以{'、'.join(freq_payload.get('cross_bank_trends', [])[:3]) or '财富管理、数智化、客户经营'}为主轴。",
        f"{base_bank}零售 AUM 增速为 {format_pct(aum_growth)}，零售营收排名第 {revenue_rank or 'n/a'}，营收同比 {format_pct(revenue_growth)}。",
        f"{base_bank}零售税前利润同比 {format_pct(profit_growth)}，当前利润排名第 {profit_rank or 'n/a'}。",
        f"个贷不良率为 {npl:.2f}% ，个人存款成本率为 {deposit_cost:.2f}% ，风险与负债成本整体处于可管理区间。"
        if npl is not None and deposit_cost is not None
        else "风险与负债成本需要结合更多结构化样本持续跟踪。",
        f"文本侧可识别的{base_bank}差异化标签主要集中在{'、'.join(base_specific[:3]) or '综合金融协同与数字金融'}；组织架构披露现状为：{org_summary}。",
    ]

    insights = [
        {
            "id": 1,
            "title": "AUM 扩张与营收转化需要联动检视",
            "priority_type": "增长机会",
            "data_basis": f"{base_bank} {latest_period} 零售 AUM 增速 {format_pct(aum_growth)}，零售营收同比 {format_pct(revenue_growth)}，零售税前利润同比 {format_pct(profit_growth)}。",
            "data_evidence": [
                {"metric": "零售 AUM 增速", "value": format_pct(aum_growth), "yoy": format_pct(aum_growth), "source": f"text/{base_bank}.json {latest_period}"},
                {"metric": "零售营收同比", "value": format_pct(revenue_growth), "yoy": format_pct(revenue_growth), "source": f"benchmark_database.json {latest_period}"},
                {"metric": "零售税前利润同比", "value": format_pct(profit_growth), "yoy": format_pct(profit_growth), "source": f"benchmark_database.json {latest_period}"},
            ],
            "business_meaning": "财富客户与资产规模增长需要同步转化为收入与利润，产品结构、费率结构和客户经营深度仍需持续评估。",
            "action_suggestion": "围绕高费率财富管理、养老金融、私行业务做二次转化追踪，建立 AUM 增量到手续费收入的联动看板。",
            "risk_note": "AUM 与收入口径来自文字与数据库混合口径，跨行比较仍需关注披露差异。",
            "source": f"benchmark_database.json + text/{base_bank}.json",
        },
        {
            "id": 2,
            "title": f"{base_bank}零售规模与盈利表现需要协同提升",
            "priority_type": "风险预警",
            "data_basis": f"{base_bank}零售营收排名第 {revenue_rank or 'n/a'}，零售税前利润排名第 {profit_rank or 'n/a'}；零售营收 {format_num(by_bank.get('零售分部营业净收入'))} 百万元，税前利润 {format_num(by_bank.get('零售分部税前利润'))} 百万元。",
            "data_evidence": [
                {"metric": "零售营收排名", "value": f"第 {revenue_rank or 'n/a'} 位", "yoy": "—", "source": f"benchmark_database.json {latest_period}"},
                {"metric": "零售税前利润排名", "value": f"第 {profit_rank or 'n/a'} 位", "yoy": "—", "source": f"benchmark_database.json {latest_period}"},
                {"metric": "零售营收（百万元）", "value": format_num(by_bank.get('零售分部营业净收入')), "yoy": format_pct(revenue_growth), "source": f"benchmark_database.json {latest_period}"},
                {"metric": "零售税前利润（百万元）", "value": format_num(by_bank.get('零售分部税前利润')), "yoy": format_pct(profit_growth), "source": f"benchmark_database.json {latest_period}"},
            ],
            "business_meaning": "规模位次与盈利能力需要同步观察，零售条线仍需平衡收入质量与风险成本。",
            "action_suggestion": "把零售利润拆解为净息差、财富中收、信用成本三条经营责任链，单独跟踪利润拖累项。",
            "risk_note": "部分同业缺少完整分部披露，利润排名样本并非全量 7 家。",
            "source": "benchmark_database.json",
        },
        {
            "id": 3,
            "title": "战略文本标签需要沉淀为稳定品牌资产",
            "priority_type": "效率提升",
            "data_basis": f"{base_bank}最新年报零售相关文本多次出现{'、'.join(base_specific[:4]) or '数字金融、养老金融、综合金融'}等表述。",
            "data_evidence": [
                {"metric": "高频战略标签", "value": '、'.join(base_specific[:4]) or '数字金融、养老金融、综合金融', "yoy": "—", "source": f"extracted_text/{base_bank} retail sections"},
            ],
            "business_meaning": "管理层口径已有差异化苗头，但仍需沉淀为可持续、可对外复述的零售战略标签体系。",
            "action_suggestion": "将核心战略标签打包为对外一致话术，并绑定可量化成果指标。",
            "risk_note": "文本标签来自零售章节打分切段，仍建议结合董事长致辞和业务综述做人工抽查。",
            "source": f"md_full retail sections + text/{base_bank}.json",
        },
        {
            "id": 4,
            "title": "组织架构披露需要形成连续证据链",
            "priority_type": "风险预警",
            "data_basis": f"{base_bank}组织架构抽取结果为“{org_summary}”，公开文本中的零售部门名单完整度有限。",
            "data_evidence": [
                {"metric": "零售条线核心部门", "value": org_summary, "yoy": "—", "source": f"insight_orgchange.json {base_bank}"},
            ],
            "business_meaning": "组织披露完整度会影响外部对零售战略承接力与跨期稳定性的判断。",
            "action_suggestion": "后续版本将架构图 OCR 邻近文本纳入抽取，同时沉淀一份人工校准的零售部门名单基线。",
            "risk_note": "当前判断主要反映公开文本可抽取性，不等于实际组织能力不足。",
            "source": "insight_orgchange.json + per-bank orgchange detail",
        },
    ]
    return executive_summary, insights


def build_report_ctx(
    benchmark: dict[str, Any],
    freq_payload: dict[str, Any],
    org_payload: dict[str, Any],
    strat_payload: dict[str, Any],
    base_bank: str,
    base_bank_full: str,
) -> dict[str, Any]:
    executive_summary, insights = compose_insights(
        benchmark, freq_payload, org_payload, strat_payload, base_bank,
    )
    base_org = org_payload["banks"][base_bank]
    latest_period = strat_payload.get("latest_period") or "最新年度"
    result = {
        "meta": {
            "title": "同业战略洞察报告",
            "subtitle": "基于 7 家股份制银行零售文本、组织架构与经营数据的综合洞察",
            "kicker": "SKILL 4 · STRATEGIC INSIGHT",
            "base_bank": base_bank,
            "base_bank_short": base_bank,
            "base_bank_full": base_bank_full,
            "cover_meta": [
                {"label": "基准行", "value": base_bank_full},
                {"label": "对标范围", "value": "7 家股份制银行"},
                {"label": "数据期", "value": latest_period},
            ],
        },
        "toc_items": [
            ("01", "执行摘要", ""),
            ("02", "行业全景", ""),
            ("03", f"{len(insights)} 条核心洞察", ""),
            ("04", f"{base_bank} vs 同业战略雷达", ""),
            ("05", f"给管理层的 {len(insights)} 条建议", ""),
            ("06", "附录", ""),
        ],
        "executive_summary": executive_summary,
        "insights": insights,
        "high_frequency_analysis": freq_payload,
        "industry_common_trends": "、".join(freq_payload.get("cross_bank_trends", [])[:5]),
        "cross_period_comparison": freq_payload.get("cross_period_comparison", {}),
        "org_structure_changes": org_payload,
        "org_primary_bank": base_bank_full,
        "org_primary": {
            "current_departments": base_org.get("retail_departments") or [base_org.get("retail_org_structure")],
            "change_frequency": base_org.get("change_frequency", "未识别到明确变化"),
            "latest_changes": base_org.get("latest_changes", "建议结合 OCR 复核"),
        },
        "org_other_banks": "；".join(org_payload.get("industry_trends", [])[:4]) or "未提炼出稳定的同业组织趋势",
        "strategic_execution_done_not_said": strat_payload.get("base_done_not_said", []),
        "strategic_execution_said_not_done": strat_payload.get("base_said_not_done", []),
        "insight_count": len(insights),
    }
    return result


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_pdf_runtime_dir() -> Path | None:
    skill_dir = Path(__file__).resolve().parents[1]
    repo_root = Path(__file__).resolve().parents[3]
    candidates = [
        repo_root / "shared" / "pdf-report-builder-runtime" / "scripts",
        skill_dir / "_vendor" / "pdf_report_builder_runtime" / "scripts",
    ]
    for candidate in candidates:
        if (candidate / "html_to_pdf.py").exists() and (candidate / "paths.py").exists():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build skill4 strategic insight artifacts")
    parser.add_argument("--with-pdf", action="store_true", help="Regenerate strategic insight PDF after JSON outputs")
    parser.add_argument(
        "--base-bank",
        help="报告客户简称/全称；默认读取 RETAIL_ANALYSIS_BASE_BANK 或 benchmark_database.meta.base_bank",
    )
    args = parser.parse_args()

    ensure_dirs()
    full_name_map = short_to_full()
    bank_periods = latest_annual_dirs()
    benchmark = load_json(DATA_DIR / "benchmark_database.json")
    requested_bank = args.base_bank or os.environ.get("RETAIL_ANALYSIS_BASE_BANK") or benchmark.get("meta", {}).get("base_bank")
    reverse_names = {full: short for short, full in full_name_map.items()}
    base_bank = reverse_names.get(requested_bank, requested_bank)
    if base_bank not in BANK_ORDER:
        raise ValueError(
            f"无法识别报告客户 {requested_bank!r}；可选客户：{', '.join(BANK_ORDER)}"
        )
    base_bank_full = f"{base_bank}银行"
    customer_output_dir = OUTPUT_DIR / base_bank
    customer_output_dir.mkdir(parents=True, exist_ok=True)
    text_payloads = {
        bank: load_json(TEXT_DIR / f"{bank}.json")
        for bank in BANK_ORDER
        if (TEXT_DIR / f"{bank}.json").exists()
    }
    # Schema 版本校验：读取 text-v1.0 前必须核对版本，避免旧 schema 静默失败
    # 契约定义：shared/config-schemas/text-v1.0.yaml
    for bank, payload in text_payloads.items():
        actual = payload.get("_schema_version")
        if actual != "text-v1.0":
            raise ValueError(
                f"text JSON schema mismatch for bank={bank!r}: "
                f"got {actual!r}, expected 'text-v1.0'. "
                f"Run Skill 2 normalize script first."
            )

    freq_payload = build_freqword_payload(bank_periods, base_bank)
    org_payload, _ = build_org_payload(bank_periods, full_name_map)
    strat_payload = build_stratreview_payload(benchmark, text_payloads, freq_payload, base_bank)
    report_ctx = build_report_ctx(
        benchmark, freq_payload, org_payload, strat_payload, base_bank, base_bank_full,
    )

    customer_partial_dir = PARTIAL_DIR / base_bank
    write_json(customer_partial_dir / "insight_freqword.json", freq_payload)
    write_json(customer_partial_dir / "insight_orgchange.json", org_payload)
    write_json(customer_partial_dir / "insight_stratreview.json", strat_payload)
    # data/ 保留机器可读兼容入口；output/<客户>/ 是本次客户的完整交付结果。
    write_json(DATA_DIR / "insight_result.json", report_ctx)
    write_json(customer_output_dir / "insight_result.json", report_ctx)

    if args.with_pdf:
        runtime_dir = resolve_pdf_runtime_dir()
        if runtime_dir is not None:
            import importlib
            import sys

            sys.path.insert(0, str(runtime_dir))
            sys.modules.pop("paths", None)
            sys.modules.pop("html_to_pdf", None)
            html_to_pdf = importlib.import_module("html_to_pdf")
            build_report = html_to_pdf.build_report

            build_report(
                ctx=report_ctx,
                template_path=str(Path(__file__).resolve().parents[1] / "assets" / "report_template.html"),
                output_html=str(customer_output_dir / "strategic_insight_report.html"),
                output_pdf=str(customer_output_dir / "同业战略洞察报告.pdf"),
                base_bank=base_bank,
                runtime_acknowledged=True,
                margin_top="25mm",
                margin_bottom="16mm",
                cover_height="296mm",
                header_text="同业战略洞察报告",
            )

    print(f"Customer {base_bank_full} ({base_bank})")
    print(f"Wrote {customer_partial_dir / 'insight_freqword.json'}")
    print(f"Wrote {customer_partial_dir / 'insight_orgchange.json'}")
    print(f"Wrote {customer_partial_dir / 'insight_stratreview.json'}")
    print(f"Wrote {DATA_DIR / 'insight_result.json'}")
    print(f"Wrote {customer_output_dir / 'insight_result.json'}")
    if args.with_pdf:
        print(f"Wrote {customer_output_dir / '同业战略洞察报告.pdf'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
