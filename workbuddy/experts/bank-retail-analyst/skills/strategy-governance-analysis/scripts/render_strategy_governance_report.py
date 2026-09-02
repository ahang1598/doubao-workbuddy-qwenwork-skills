#!/usr/bin/env python3
"""将 Skill 5 结构化结果与 12 个 partial 组装为完整 HTML/PDF 报告。"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from paths import DATA_DIR, OUTPUT_DIR, PARTIAL_DIR


SKILL_DIR = Path(__file__).resolve().parents[1]
EXPECTED_SCHEMA_VERSION = "sg-v1.1"
STANDARD_TEMPLATE = SKILL_DIR / "assets" / "report_template.html"
REQUIRED_PARTIAL_NAMES = (
    "cycle_timeline",
    "leader_profiles",
    "org_heatmap",
    "narrative_matrix",
    "consistency_matrix",
    "continuity_score",
    "scenario_context",
    "decision_logic",
    "counterfactual",
    "board_activity",
    "shareholder_impact",
    "resilience_score",
)
BANK_ORDER = ["浦发银行", "招商银行", "兴业银行", "平安银行", "中信银行", "光大银行"]
BACKGROUND_LABELS = {
    "internal": "内部晋升",
    "system": "系统内调任",
    "regulator": "监管背景",
    "external": "外部引入",
}
PDF_TEXT_TRANSLATION = str.maketrans({"⻣": "骨", "⻆": "角", "⻚": "页"})


def load_json(path: Path, *, required: bool = True) -> Any:
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"文件不存在：{path}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def partial(name: str) -> dict[str, Any]:
    payload = load_json(PARTIAL_DIR / f"sg_{name}.json", required=False)
    return payload if isinstance(payload, dict) else {}


def short_name(full_name: str) -> str:
    return str(full_name).removesuffix("股份有限公司").removesuffix("银行")


def validate_standard_inputs(result: Any, *, expected_bank: str) -> None:
    """在写任何报告产物前执行标准入口硬校验。"""
    errors: list[str] = []
    if not isinstance(result, dict):
        raise ValueError("Skill 5 主结果必须是 JSON object")

    meta = result.get("meta")
    if not isinstance(meta, dict):
        errors.append("缺少 meta object")
        meta = {}
    schema_version = meta.get("schema_version")
    if schema_version != EXPECTED_SCHEMA_VERSION:
        errors.append(
            f"meta.schema_version 必须为 {EXPECTED_SCHEMA_VERSION!r}，实际为 {schema_version!r}；"
            "禁止把临时或实验 schema 直接交给正式报告渲染器"
        )
    result_bank = str(meta.get("base_bank") or "").strip()
    if not result_bank:
        errors.append("meta.base_bank 不能为空")
    elif short_name(result_bank) != short_name(expected_bank):
        errors.append(
            f"基准行不一致：命令参数为 {expected_bank!r}，result.json 为 {result_bank!r}"
        )

    missing_partials: list[str] = []
    invalid_partials: list[str] = []
    for name in REQUIRED_PARTIAL_NAMES:
        filename = f"sg_{name}.json"
        path = PARTIAL_DIR / filename
        if not path.is_file():
            missing_partials.append(filename)
            continue
        try:
            payload = load_json(path)
        except (OSError, json.JSONDecodeError):
            invalid_partials.append(filename)
            continue
        if not isinstance(payload, dict) or not payload:
            invalid_partials.append(filename)
    if missing_partials:
        errors.append("缺少 12 个标准 partial 中的：" + "、".join(missing_partials))
    if invalid_partials:
        errors.append("partial 不是非空 JSON object：" + "、".join(invalid_partials))

    template_text = STANDARD_TEMPLATE.read_text(encoding="utf-8") if STANDARD_TEMPLATE.is_file() else ""
    if not template_text:
        errors.append(f"标准模板不存在：{STANDARD_TEMPLATE}")
    else:
        required_template_markers = (
            '{% extends "base_template.html" %}',
            'class="leader-timeline"',
            'class="org-heatmap"',
            'class="counterfactual-range"',
            'class="swing-card"',
            'class="recommendation-grid"',
        )
        missing_markers = [marker for marker in required_template_markers if marker not in template_text]
        if missing_markers:
            errors.append("标准模板结构不完整，缺少：" + "、".join(missing_markers))

    if errors:
        raise ValueError("Skill 5 正式渲染前置校验失败：\n- " + "\n- ".join(errors))


def _has_table_rows(value: Any) -> bool:
    text = str(value or "")
    return "<tbody>" in text and "<tbody></tbody>" not in text


def _filled(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return value not in (None, [], {})


def validate_report_context(ctx: dict[str, Any]) -> None:
    """拒绝占位符、缺章节和不完整建议进入正式模板。"""
    errors: list[str] = []
    phase1 = ctx.get("phase1") or {}
    phase2 = ctx.get("phase2") or {}
    phase3 = ctx.get("phase3") or {}
    phase4 = ctx.get("phase4") or {}

    if not phase1.get("cycles"):
        errors.append("phase1.cycles 为空")
    if not _has_table_rows(phase1.get("leader_timeline_html")):
        errors.append("phase1.leader_timeline_html 没有数据行")
    if not _has_table_rows(phase1.get("org_heatmap_html")):
        errors.append("phase1.org_heatmap_html 没有数据行")
    if not _has_table_rows(phase2.get("consistency_table_html")):
        errors.append("phase2.consistency_table_html 没有数据行")
    if not phase2.get("continuity_items"):
        errors.append("phase2.continuity_items 为空")

    key_nodes = phase3.get("key_nodes") or []
    if len(key_nodes) != 5:
        errors.append(f"phase3.key_nodes 必须恰好 5 个，实际为 {len(key_nodes)} 个")
    for index, node in enumerate(key_nodes, start=1):
        if not isinstance(node, dict) or not node.get("decisions") or not node.get("what_if"):
            errors.append(f"phase3.key_nodes[{index}] 缺少 decisions 或 what_if")

    if not _has_table_rows(phase4.get("board_activity_html")):
        errors.append("phase4.board_activity_html 没有数据行")
    if not phase4.get("shareholder_events"):
        errors.append("phase4.shareholder_events 为空")
    if not phase4.get("resilience_scores"):
        errors.append("phase4.resilience_scores 为空")

    swings = ctx.get("swing_points") or []
    if len(swings) < 2:
        errors.append(f"swing_points 至少 2 个，实际为 {len(swings)} 个")
    required_swing_fields = ("year", "event", "root_cause", "cost_assessment", "lesson")
    for index, item in enumerate(swings, start=1):
        missing = [field for field in required_swing_fields if not _filled(item.get(field))]
        if missing:
            errors.append(f"swing_points[{index}] 缺少字段：{'、'.join(missing)}")
        if len(item.get("evidence") or []) < 2:
            errors.append(f"swing_points[{index}] 至少需要 2 类证据")

    recommendations = ctx.get("recommendations") or {}
    required_rec_fields = (
        "action",
        "rationale",
        "data_evidence",
        "expected_effect",
        "responsible_role",
        "time_window",
    )
    for category in ("strategy_insulation", "governance_resilience", "key_personnel"):
        items = recommendations.get(category) or []
        if not 3 <= len(items) <= 5:
            errors.append(f"recommendations.{category} 必须为 3~5 条，实际为 {len(items)} 条")
        for index, item in enumerate(items, start=1):
            missing = [field for field in required_rec_fields if not _filled(item.get(field))]
            if missing:
                errors.append(
                    f"recommendations.{category}[{index}] 缺少六要素字段：{'、'.join(missing)}"
                )

    if errors:
        raise ValueError("Skill 5 PDF 上下文完整性校验失败：\n- " + "\n- ".join(errors))


def _normalize_pdf_text(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).translate(PDF_TEXT_TRANSLATION).split())


def validate_generated_pdf(pdf_path: Path) -> dict[str, Any]:
    """校验标准分页骨架和关键章节，防止封面溢出或目录丢失。"""
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore

    reader = PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    texts = [page.extract_text() or "" for page in reader.pages]
    compact = [_normalize_pdf_text(text) for text in texts]
    errors: list[str] = []

    if not 10 <= page_count <= 30:
        errors.append(f"页数必须在 10~30 页，实际为 {page_count} 页")
    if page_count < 2 or "目录" not in compact[1]:
        errors.append("第 2 页必须是目录页")
    if page_count >= 2 and "生成日期" in compact[1]:
        errors.append("封面内容溢出到第 2 页")

    all_text = "".join(compact)
    required_terms = (
        "战略与治理分析报告",
        "执行摘要",
        "时间骨架",
        "言行比对",
        "关键节点反事实推演",
        "治理结构影响机制",
        "战略摇摆点诊断",
        "建议方案",
        "战略隔离带",
        "治理韧性",
        "关键人事",
        "本报告由 AI 基于上市银行公开披露信息生成，仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐",
    )
    missing_terms = [term for term in required_terms if _normalize_pdf_text(term) not in all_text]
    if missing_terms:
        errors.append("PDF 缺少标准章节/文案：" + "、".join(missing_terms))

    result = {"passed": not errors, "page_count": page_count, "errors": errors}
    if errors:
        raise RuntimeError("Skill 5 PDF 终验失败：\n- " + "\n- ".join(errors))
    return result


def ordered_banks(keys: Any, base_bank: str) -> list[str]:
    available = list(keys)
    result = [base_bank] if base_bank in available else []
    result.extend(bank for bank in BANK_ORDER if bank in available and bank not in result)
    result.extend(bank for bank in available if bank not in result)
    return result


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def grade(total: float) -> str:
    if total >= 90:
        return "A（战略定力突出）"
    if total >= 75:
        return "B（战略定力良好）"
    if total >= 60:
        return "C（战略定力中等）"
    return "D（战略定力偏弱）"


def build_leader_timeline_html(profiles: dict[str, list[dict[str, Any]]], base_bank: str) -> str:
    rows: list[str] = []
    for bank in ordered_banks(profiles, base_bank):
        leaders = profiles.get(bank) or []
        leaders = sorted(leaders, key=lambda x: (str(x.get("tenure_start", "")), str(x.get("role", ""))))
        for leader in leaders:
            signature = "、".join(str(x) for x in leader.get("strategic_signature", []) if x)
            rows.append(
                "<tr>"
                f"<td class='bank-label'>{esc(bank)}</td>"
                f"<td>{esc(leader.get('role'))}</td>"
                f"<td><span class='tenure-bar {esc(leader.get('background', 'external'))}'>{esc(leader.get('name'))}</span></td>"
                f"<td>{esc(leader.get('tenure_start'))} – {esc(leader.get('tenure_end'))}</td>"
                f"<td>{esc(BACKGROUND_LABELS.get(leader.get('background'), leader.get('background')))}</td>"
                f"<td>{esc(signature)}</td>"
                "</tr>"
            )
    legend = "".join(
        f"<span class='legend-item'><span class='legend-swatch {key}'></span>{label}</span>"
        for key, label in BACKGROUND_LABELS.items()
    )
    return (
        "<table><thead><tr><th>银行</th><th>角色</th><th>领导</th><th>任期</th><th>背景</th><th>战略标签</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table><div class='timeline-legend'>{legend}</div>"
    )


def normalize_heatmap(raw: dict[str, Any]) -> dict[str, dict[str, dict[str, int]]]:
    result: dict[str, dict[str, dict[str, int]]] = {}
    for bank, bank_data in raw.items():
        result[bank] = {"零售": {}, "科技": {}, "风险": {}}
        if not isinstance(bank_data, dict):
            continue
        if any(key in bank_data for key in ("零售", "科技", "风险")):
            for line in result[bank]:
                values = bank_data.get(line) or {}
                result[bank][line] = {str(y): int(v or 0) for y, v in values.items()}
        else:
            for year, line_values in bank_data.items():
                if not isinstance(line_values, dict):
                    continue
                for line in result[bank]:
                    result[bank][line][str(year)] = int(line_values.get(line, 0) or 0)
    return result


def build_org_heatmap_html(raw: dict[str, Any], base_bank: str) -> str:
    heatmap = normalize_heatmap(raw)
    years = sorted({year for bank in heatmap.values() for line in bank.values() for year in line})
    if not years:
        return ""
    rows: list[str] = []
    for bank in ordered_banks(heatmap, base_bank):
        for line in ("零售", "科技", "风险"):
            cells = []
            for year in years:
                value = heatmap[bank].get(line, {}).get(year, 0)
                heat_class = min(max(int(value), 0), 3)
                cells.append(f"<td class='heat-{heat_class}'>{value}</td>")
            rows.append(
                f"<tr><td class='bank-label'>{esc(bank)}</td><td class='line-label'>{line}</td>{''.join(cells)}</tr>"
            )
    headers = "".join(f"<th>{esc(year)}</th>" for year in years)
    return (
        f"<table><thead><tr><th>银行</th><th>条线</th>{headers}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _consistency_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "rho": item.get("rho", item.get("ρ")),
        "verdict": item.get("verdict", item.get("判定", "")),
        "note": item.get("note") or item.get("reason") or item.get("资源证据") or "",
    }


def normalize_consistency(raw: Any) -> dict[str, dict[str, dict[str, Any]]]:
    normalized: dict[str, dict[str, dict[str, Any]]] = {}
    if isinstance(raw, list):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            bank = str(item.get("bank") or item.get("银行") or "").strip()
            if bank:
                grouped.setdefault(bank, []).append(item)
        raw = grouped
    if not isinstance(raw, dict):
        return normalized

    for bank, value in raw.items():
        records: list[dict[str, Any]] = []
        if isinstance(value, list):
            records = [item for item in value if isinstance(item, dict)]
        elif isinstance(value, dict) and any(key in value for key in ("rho", "ρ", "verdict", "判定")):
            records = [value]
        elif isinstance(value, dict):
            topics: dict[str, dict[str, Any]] = {}
            for topic, item in value.items():
                if topic == "avg_rho" or not isinstance(item, dict):
                    continue
                topics[str(topic)] = _consistency_item(item)
            if "avg_rho" in value:
                topics["__avg__"] = {"rho": value.get("avg_rho")}
            normalized[str(bank)] = topics
            continue

        topics = {}
        rho_values: list[float] = []
        for index, item in enumerate(records, start=1):
            topic = str(item.get("keyword_group") or item.get("战略关键词") or f"综合战略口径{index}")
            canonical = _consistency_item(item)
            topics[topic] = canonical
            if isinstance(canonical.get("rho"), (int, float)):
                rho_values.append(float(canonical["rho"]))
        if topics:
            topics["__avg__"] = {"rho": sum(rho_values) / len(rho_values) if rho_values else None}
            normalized[str(bank)] = topics
    return normalized


def build_consistency_table_html(raw: dict[str, Any], base_bank: str) -> str:
    consistency = normalize_consistency(raw)
    rows: list[str] = []
    for bank in ordered_banks(consistency, base_bank):
        topics = consistency[bank]
        for topic, item in topics.items():
            if topic == "__avg__":
                continue
            rho = item.get("rho")
            rows.append(
                "<tr>"
                f"<td class='strong-col'>{esc(bank)}</td><td>{esc(topic)}</td>"
                f"<td>{esc(f'{rho:.2f}' if isinstance(rho, (int, float)) else rho)}</td>"
                f"<td>{esc(item.get('verdict'))}</td><td>{esc(item.get('note') or item.get('reason'))}</td>"
                "</tr>"
            )
    return (
        "<table class='landscape-table'><thead><tr><th>银行</th><th>战略主题</th><th>ρ</th><th>判定</th><th>资源证据</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def consistency_extremes(raw: dict[str, Any]) -> tuple[list[str], list[str]]:
    values: list[tuple[float, str]] = []
    for bank, topics in normalize_consistency(raw).items():
        for topic, item in topics.items():
            rho = item.get("rho")
            if topic == "__avg__" or not isinstance(rho, (int, float)):
                continue
            values.append((float(rho), f"{bank} · {topic}：ρ={rho:.2f}，{item.get('verdict', '')}；{item.get('note') or item.get('reason') or ''}"))
    wins = [text for _, text in sorted(values, reverse=True)[:5]]
    gaps = [text for _, text in sorted(values)[:5]]
    return wins, gaps


def verdict_class(verdict: str) -> str:
    if "进化" in verdict:
        return "evolution"
    if "渐进" in verdict:
        return "incremental"
    return "rupture"


def build_continuity_items(raw: Any, profiles: dict[str, Any], base_bank: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(raw, list):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            bank = str(item.get("bank") or item.get("银行") or "").strip()
            if bank:
                grouped.setdefault(bank, []).append(item)
        raw = grouped
    if not isinstance(raw, dict):
        return items

    for bank in ordered_banks(raw, base_bank):
        leader_profiles = profiles.get(bank) or []
        bank_value = raw.get(bank) or []
        if isinstance(bank_value, dict):
            bank_records = [
                {"tenure": tenure, **record}
                for tenure, record in bank_value.items()
                if isinstance(record, dict)
            ]
        elif isinstance(bank_value, list):
            bank_records = [record for record in bank_value if isinstance(record, dict)]
        else:
            bank_records = []
        for item in bank_records:
            result = dict(item)
            result["bank"] = bank
            leader_label = str(result.get("leader", ""))
            matched = next((p for p in leader_profiles if str(p.get("name", "")) in leader_label), None)
            if matched:
                result["tenure"] = str(matched.get("tenure_start", result.get("tenure", "")))[:7]
            else:
                result.setdefault("tenure", "")
            result["verdict_class"] = result.get("verdict_class") or verdict_class(str(result.get("verdict", "")))
            drift = result.get("drift_rate")
            result["drift_rate"] = f"{float(drift) * 100:.0f}%" if isinstance(drift, (int, float)) else drift
            items.append(result)
    return items


def merge_key_nodes(result: dict[str, Any]) -> list[dict[str, Any]]:
    phase3 = result.get("phase3_counterfactual") or {}
    nodes = {str(item.get("id")): dict(item) for item in phase3.get("key_nodes", []) if item.get("id")}
    contexts = {str(item.get("id")): item for item in partial("scenario_context").get("scenario_context", [])}
    decisions = {str(item.get("id")): item for item in partial("decision_logic").get("decision_logic", [])}
    counterfactual = {str(item.get("id")): item for item in partial("counterfactual").get("counterfactual", [])}
    order = ["2013_qianhuang", "2016_mpa", "2018_asset_new_rules", "2020_covid", "2022_real_estate"]
    merged: list[dict[str, Any]] = []
    for node_id in order + [x for x in nodes if x not in order]:
        if node_id not in nodes and node_id not in contexts:
            continue
        item = dict(nodes.get(node_id, {}))
        item.update({k: v for k, v in contexts.get(node_id, {}).items() if v not in (None, "", [], {})})
        logic = decisions.get(node_id, {})
        item["decisions"] = logic.get("decisions") or item.get("decisions") or {}
        item["logic"] = logic.get("logic") or item.get("logic") or {}
        cf = counterfactual.get(node_id, {})
        item["what_if"] = cf.get("what_if") or item.get("what_if") or []
        item["overall_confidence"] = cf.get("overall_confidence") or item.get("overall_confidence") or "低"
        merged.append(item)
    return merged


def build_board_activity_html(raw: dict[str, Any], base_bank: str) -> str:
    rows: list[str] = []
    for bank in ordered_banks(raw, base_bank):
        item = raw.get(bank) or {}
        rows.append(
            "<tr>"
            f"<td class='strong-col'>{esc(bank)}</td>"
            f"<td>{esc(item.get('strategy_committee_density', '未披露'))}</td>"
            f"<td>{esc(item.get('risk_committee_density', '未披露'))}</td>"
            f"<td>{esc(item.get('roe_stability', '未披露'))}</td>"
            f"<td>{esc(item.get('correlation_qualitative', '未计算'))}</td>"
            f"<td>{esc(item.get('note', ''))}</td>"
            "</tr>"
        )
    return (
        "<table class='evidence-table'><thead><tr><th>银行</th><th>战略委密度</th><th>风险委密度</th><th>ROE稳定性</th><th>定性相关性</th><th>证据限制</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def normalize_resilience(result: dict[str, Any]) -> list[dict[str, Any]]:
    raw = (result.get("phase4_governance") or {}).get("resilience_score") or {}
    if not raw:
        raw = partial("resilience_score").get("resilience_score") or {}
    rows: list[dict[str, Any]] = []
    for bank, value in raw.items():
        if isinstance(value, dict):
            item = dict(value)
            item["bank"] = bank
            item.setdefault("grade", grade(float(item.get("total", 0))))
        else:
            item = {"bank": bank, "total": value, "grade": grade(float(value or 0))}
        rows.append(item)
    return sorted(rows, key=lambda x: float(x.get("total", 0)), reverse=True)


def normalize_recommendations(raw: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for category in ("strategy_insulation", "governance_resilience", "key_personnel"):
        result[category] = []
        for item in raw.get(category) or []:
            normalized = dict(item)
            normalized["rationale"] = item.get("rationale") or item.get("reason") or ""
            normalized["data_evidence"] = item.get("data_evidence") or item.get("data_basis") or item.get("evidence") or ""
            normalized["responsible_role"] = item.get("responsible_role") or item.get("owner") or ""
            normalized["time_window"] = item.get("time_window") or ""
            result[category].append(normalized)
    return result


def swing_points(result: dict[str, Any], base_short: str) -> list[dict[str, Any]]:
    candidates = [
        f"{base_short.lower()}_swing_points",
        "pufa_swing_points" if base_short == "浦发" else "",
        "base_bank_swing_points",
        "citic_swing_points",
    ]
    raw: list[dict[str, Any]] = []
    for key in candidates:
        if key and isinstance(result.get(key), list):
            raw = result[key]
            break
    normalized = []
    for item in raw:
        row = dict(item)
        evidence = item.get("evidence") or []
        if isinstance(evidence, dict):
            row["evidence"] = [str(value) for value in evidence.values() if value]
        elif isinstance(evidence, list):
            row["evidence"] = [str(value) for value in evidence if value]
        else:
            row["evidence"] = [str(evidence)] if evidence else []
        cost = item.get("cost_assessment") or item.get("cost_estimate") or item.get("cost") or ""
        if isinstance(cost, dict):
            cost = "；".join(f"{key}：{value}" for key, value in cost.items() if value)
        row["cost_assessment"] = str(cost)
        normalized.append(row)
    return normalized


def build_summary(result: dict[str, Any], ranking: list[dict[str, Any]], consistency: dict[str, Any], swings: list[dict[str, Any]]) -> dict[str, Any]:
    base_bank = str((result.get("meta") or {}).get("base_bank", ""))
    base_score = next((x for x in ranking if x.get("bank") == base_bank), {})
    rank = next((idx for idx, item in enumerate(ranking, start=1) if item.get("bank") == base_bank), None)
    normalized = normalize_consistency(consistency)
    base_topics = normalized.get(base_bank) or {}
    avg_rho = (base_topics.get("__avg__") or {}).get("rho")
    if avg_rho is None:
        values = [x.get("rho") for k, x in base_topics.items() if k != "__avg__" and isinstance(x.get("rho"), (int, float))]
        avg_rho = sum(values) / len(values) if values else None
    findings = [
        f"{base_bank}战略韧性得分 {base_score.get('total', '未披露')}，在可比银行中排名第 {rank or '未计算'}；短板集中在政策适配度与言行一致度。",
        f"言行一致度均值 ρ={avg_rho:.2f}，反映战略口径与资源投向的联动强度。" if isinstance(avg_rho, (int, float)) else "言行一致度样本不足，需结合年报原文继续补录。",
        f"识别 {len(swings)} 个战略摇摆点，均已按时点、诱因、证据、代价和教训展开。",
        "五个关键压力节点均恢复环境、同业决策逻辑和反事实区间；推演结论统一标注为模型推演，非事实。",
        "治理修复方案覆盖战略隔离带、治理韧性与关键人事三类，并明确责任方和时间窗。",
    ]
    return {
        "core_findings": findings,
        "kpis": [
            {"label": "战略韧性", "value": base_score.get("total", "—"), "note": f"同业第 {rank or '—'}"},
            {"label": "言行一致度", "value": f"ρ={avg_rho:.2f}" if isinstance(avg_rho, (int, float)) else "—", "note": "战略口径 × 资源投向"},
            {"label": "战略摇摆点", "value": len(swings), "note": "均含证据与代价评估"},
            {"label": "反事实节点", "value": 5, "note": "模型推演，非事实"},
        ],
        "resilience_ranking": ranking,
    }


def enrich_result(result: dict[str, Any]) -> dict[str, Any]:
    enriched = json.loads(json.dumps(result, ensure_ascii=False))
    phase1 = enriched.setdefault("phase1_timeline", {})
    partial_heatmap = partial("org_heatmap").get("org_heatmap") or {}
    if partial_heatmap:
        phase1["org_heatmap"] = partial_heatmap
    phase4 = enriched.setdefault("phase4_governance", {})
    board = partial("board_activity").get("board_activity") or {}
    shareholder = partial("shareholder_impact").get("shareholder_impact") or {}
    if board:
        phase4["board_activity"] = board
    if shareholder:
        phase4["shareholder_impact"] = shareholder
    return enriched


def build_report_ctx(result: dict[str, Any]) -> dict[str, Any]:
    meta = dict(result.get("meta") or {})
    base_bank = str(meta.get("base_bank") or "")
    if not base_bank:
        raise ValueError("result.meta 中未指定 base_bank。请先由用户指定基准银行。")
    base_short = short_name(base_bank)
    meta.update({
        "title": "战略与治理分析报告",
        "subtitle": "财务数据 × 管理层行为 × 组织演进的穿透式分析",
        "kicker": "SKILL 5 · STRATEGY & GOVERNANCE",
        "base_bank": base_bank,
        "base_bank_short": base_short,
        "base_bank_full": base_bank,
        "cover_meta": [
            {"label": "基准行", "value": base_bank},
            {"label": "对标范围", "value": "、".join(meta.get("peer_banks") or [])},
            {"label": "分析窗口", "value": meta.get("analysis_window", "2004-至今")},
            {"label": "数据窗口", "value": meta.get("data_window", "2015-最新期")},
        ],
    })
    phase1_src = result.get("phase1_timeline") or {}
    profiles = phase1_src.get("leader_profiles") or partial("leader_profiles").get("leader_profiles") or {}
    heatmap = phase1_src.get("org_heatmap") or partial("org_heatmap").get("org_heatmap") or {}

    consistency = partial("consistency_matrix").get("consistency_score") or (result.get("phase2_narrative") or {}).get("consistency_score") or {}
    continuity = partial("continuity_score").get("continuity_score") or (result.get("phase2_narrative") or {}).get("continuity_score") or {}
    wins, gaps = consistency_extremes(consistency)

    board = (result.get("phase4_governance") or {}).get("board_activity") or partial("board_activity").get("board_activity") or {}
    shareholders = (result.get("phase4_governance") or {}).get("shareholder_impact") or partial("shareholder_impact").get("shareholder_impact") or {}
    ranking = normalize_resilience(result)
    swings = swing_points(result, base_short)

    shareholder_events = []
    for bank in ordered_banks(shareholders, base_bank):
        item = shareholders.get(bank) or {}
        changes = "；".join(str(x) for x in item.get("changes_2015_plus", []) if x)
        impact = " → ".join(x for x in [
            str(item.get("controlling", "")), changes,
            str(item.get("risk_boundary_shift", "")), str(item.get("dividend_policy", "")),
        ] if x)
        shareholder_events.append({"bank": bank, "event": item.get("narrative") or changes, "impact_chain": impact})

    return {
        "meta": meta,
        "toc_items": [
            ("01", "执行摘要", ""),
            ("02", "时间骨架：周期、领导与组织", ""),
            ("03", "穿透式言行比对", ""),
            ("04", "五个关键节点反事实", ""),
            ("05", "治理结构影响机制", ""),
            ("06", f"{base_short}战略摇摆点诊断", ""),
            ("07", "建议方案", ""),
            ("08", "数据窗口与免责声明", ""),
        ],
        "summary": build_summary(result, ranking, consistency, swings),
        "phase1": {
            "cycles": phase1_src.get("cycles") or partial("cycle_timeline").get("cycles") or [],
            "leader_timeline_html": build_leader_timeline_html(profiles, base_bank),
            "org_heatmap_html": build_org_heatmap_html(heatmap, base_bank),
        },
        "phase2": {
            "consistency_table_html": build_consistency_table_html(consistency, base_bank),
            "col_wins": wins,
            "col_gaps": gaps,
            "continuity_items": build_continuity_items(continuity, profiles, base_bank),
        },
        "phase3": {"key_nodes": merge_key_nodes(result)},
        "phase4": {
            "board_activity_html": build_board_activity_html(board, base_bank),
            "shareholder_events": shareholder_events,
            "resilience_scores": ranking,
        },
        "swing_points": swings,
        "recommendations": normalize_recommendations(result.get("recommendations") or {}),
        "risk_disclosure": result.get("risk_disclosure") or [],
    }


def build_markdown(ctx: dict[str, Any]) -> str:
    meta = ctx["meta"]
    lines = [
        "# 战略与治理分析报告", "", f"基准行：{meta['base_bank']}", "",
        "## 执行摘要", "",
    ]
    lines.extend(f"- {item}" for item in ctx["summary"]["core_findings"])
    lines.extend(["", "## 01 时间骨架：周期划分、领导画像与组织演进", ""])
    lines.extend(f"- {c.get('name')}（{c.get('start')}–{c.get('end')}）：{c.get('macro', '')}" for c in ctx["phase1"]["cycles"])
    lines.extend(["", "## 02 穿透式‘言行比对’", ""])
    lines.extend(f"- 真战略：{item}" for item in ctx["phase2"]["col_wins"])
    lines.extend(f"- 待纠偏：{item}" for item in ctx["phase2"]["col_gaps"])
    lines.extend(["", "## 03 关键节点反事实推演", ""])
    for node in ctx["phase3"]["key_nodes"]:
        lines.append(f"### {node.get('name')}（{node.get('date', '')}）")
        lines.append(str(node.get("context", "")))
        for wf in node.get("what_if", []):
            lines.append(f"- {wf.get('scenario')}：{wf.get('impact_summary')}（模型推演，非事实；置信度 {wf.get('confidence', node.get('overall_confidence', '低'))}）")
    lines.extend(["", "## 04 治理结构影响机制", "", "董事会活动、股东意志与战略韧性评分详见报告表格。", "", f"## 05 【风险点】{meta['base_bank']}战略摇摆点诊断", ""])
    for item in ctx["swing_points"]:
        lines.extend([f"### {item.get('year')} · {item.get('event')}", f"- 诱因：{item.get('root_cause')}"])
        lines.extend(f"- 证据：{e}" for e in item.get("evidence", []))
        lines.extend([f"- 代价：{item.get('cost_assessment')}", f"- 教训：{item.get('lesson')}", ""])
    lines.extend(["## 06 【建议】战略隔离带与治理韧性提升方案", ""])
    for key, title in (("strategy_insulation", "战略隔离带"), ("governance_resilience", "治理韧性"), ("key_personnel", "关键人事安排")):
        lines.append(f"### {title}")
        for rec in ctx["recommendations"][key]:
            lines.append(f"- **动作**：{rec.get('action')}；**理由**：{rec.get('rationale')}；**数据依据**：{rec.get('data_evidence')}；**预期效果**：{rec.get('expected_effect')}；**责任方**：{rec.get('responsible_role')}；**时间窗**：{rec.get('time_window')}")
    lines.extend(["", "## 07 数据窗口与降级说明", ""])
    lines.extend(f"- {item}" for item in ctx["risk_disclosure"])
    lines.extend(["", "## 08 免责声明", "", "本报告由 AI 基于上市银行公开披露信息生成，仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐。", ""])
    return "\n".join(lines)


def resolve_result_path(base_short: str, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    customer = OUTPUT_DIR / base_short / "strategy_governance_result.json"
    return customer if customer.is_file() else DATA_DIR / "strategy_governance_result.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染完整 Skill 5 战略与治理报告")
    parser.add_argument("--base-bank", default=os.environ.get("RETAIL_ANALYSIS_BASE_BANK"), required=False,
                        help="基准银行短名/全称/别名（如 光大 / 光大银行 / CEB）。未指定时从 result.json 的 meta.base_bank 读取；若仍为空则报错。")
    parser.add_argument("--result-json", help="结构化主结果；默认优先读取 output/<bank>/，其次 data/")
    parser.add_argument("--html-only", action="store_true", help="只生成 JSON/Markdown/HTML，不导出 PDF")
    parser.add_argument("--write-enriched-result", action="store_true", help="把 partial 中缺失的治理模块回写结构化主结果")
    args = parser.parse_args()

    vendor_scripts = SKILL_DIR / "_vendor" / "pdf_report_builder_runtime" / "scripts"
    if str(vendor_scripts) not in sys.path:
        sys.path.insert(0, str(vendor_scripts))
    # 当前脚本已加载业务 Skill 的 paths；PDF Runtime 也有同名模块，导入前必须隔离。
    sys.modules.pop("paths", None)
    from bank_context import resolve as resolve_bank
    from html_to_pdf import build_report, render_html
    from pdf_validator import validate_pdf

    bank_ctx = resolve_bank(base_bank=args.base_bank)
    result_path = resolve_result_path(bank_ctx.short_name, args.result_json)
    source = load_json(result_path)
    validate_standard_inputs(source, expected_bank=bank_ctx.full_name)
    result = enrich_result(source)
    ctx = build_report_ctx(result)
    validate_report_context(ctx)

    customer_dir = bank_ctx.output_dir
    customer_dir.mkdir(parents=True, exist_ok=True)
    lock_dir = customer_dir / ".strategy_governance_render.lock"
    try:
        lock_dir.mkdir()
    except FileExistsError as exc:
        raise RuntimeError(f"同一银行已有报告渲染任务运行中：{lock_dir}") from exc

    run_id = f"{os.getpid()}-{uuid.uuid4().hex}"
    context_path = customer_dir / "strategy_governance_report_context.json"
    markdown_path = customer_dir / "strategy_governance_report.md"
    html_path = bank_ctx.output_path("strategy_governance_report.html")
    pdf_path = bank_ctx.output_path("战略与治理分析报告.pdf")
    validation_path = customer_dir / "strategy_governance_pdf_validation.json"
    temporary_context = customer_dir / f".strategy_governance_report_context.{run_id}.tmp.json"
    temporary_markdown = customer_dir / f".strategy_governance_report.{run_id}.tmp.md"
    temporary_html = customer_dir / f".strategy_governance_report.{run_id}.tmp.html"
    temporary_pdf = customer_dir / f".战略与治理分析报告.{run_id}.tmp.pdf"
    temporary_validation = customer_dir / f".strategy_governance_pdf_validation.{run_id}.tmp.json"
    temporary_paths = (
        temporary_context,
        temporary_markdown,
        temporary_html,
        temporary_pdf,
        temporary_validation,
    )

    try:
        temporary_context.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary_markdown.write_text(build_markdown(ctx), encoding="utf-8")
        render_kwargs = dict(
            ctx=ctx,
            template_path=str(STANDARD_TEMPLATE),
            output_html=str(temporary_html),
            style_overrides_path=str(SKILL_DIR / "assets" / "style_overrides.css"),
            bank_ctx=bank_ctx,
        )
        if args.html_only:
            render_html(**render_kwargs)
        else:
            generated_pdf = Path(build_report(
                **render_kwargs,
                output_pdf=str(temporary_pdf),
                base_bank=bank_ctx.short_name,
                margin_top="22mm",
                margin_bottom="15mm",
                header_text=f"战略与治理分析报告 · {bank_ctx.short_name}银行视角",
                runtime_acknowledged=True,
            ))
            structural_validation = validate_generated_pdf(generated_pdf)
            visual_validation = validate_pdf(str(generated_pdf), min_pages=10, max_pages=30)
            if not visual_validation.get("passed"):
                failed = [
                    check.get("detail", check.get("name", "未知错误"))
                    for check in visual_validation.get("checks", [])
                    if not check.get("passed")
                ]
                raise RuntimeError("Skill 5 PDF 五项视觉校验失败：\n- " + "\n- ".join(failed))
            validation = {
                "passed": True,
                "structural": structural_validation,
                "visual": visual_validation,
            }
            temporary_validation.write_text(
                json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8",
            )

        temporary_context.replace(context_path)
        temporary_markdown.replace(markdown_path)
        temporary_html.replace(html_path)
        if not args.html_only:
            temporary_pdf.replace(pdf_path)
            temporary_validation.replace(validation_path)
        if args.write_enriched_result:
            result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            customer_result = bank_ctx.output_path("strategy_governance_result.json")
            customer_result.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        for temporary_path in temporary_paths:
            temporary_path.unlink(missing_ok=True)
        lock_dir.rmdir()

    print(f"result={result_path}")
    print(f"context={context_path}")
    print(f"html={html_path}")
    if not args.html_only:
        print(f"validation={validation_path}")
        print(f"pdf={pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
