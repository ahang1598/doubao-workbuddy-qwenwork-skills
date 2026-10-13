#!/usr/bin/env python3
"""Build the selected will-planning deliverables without case-management artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_will_docx import build_will_docx
from evaluate_rules import evaluate_rules
from intake_runtime import AI_DELIVERY_NOTICE, AI_FILE_NOTICE
from validate_case import OUTPUT_GATE_STATUSES, validate_case


ALWAYS_PACKET_FILES = (
    "validation-report.json",
    "02-legal-rule-evaluation.md",
    "03-execution-guide.md",
)
LEGACY_PACKET_FILES = ("04-education-links.md", "05-ai-judgment-notice.md")
OPTIONAL_PACKET_FILES = {
    "legal_research_report": "01-legal-research-report.md",
    "relationship_diagram": "06-relationship-diagram.svg",
    "asset_inventory": "07-asset-inventory.md",
}
BASE_PACKET_FILES = ALWAYS_PACKET_FILES + tuple(OPTIONAL_PACKET_FILES.values())
WILL_FILE = "08-will.docx"

WILL_FORM_LABELS = {
    "holographic": "自书遗嘱",
    "dictated": "代书遗嘱",
    "printed": "打印遗嘱",
    "audio_video": "录音录像遗嘱",
    "oral": "口头遗嘱",
    "notarized": "公证遗嘱",
    "undecided": "遗嘱形式待确定",
}
FORM_CHECKLISTS = {
    "holographic": ["由遗嘱人亲笔书写全文", "由遗嘱人本人签名", "写明年、月、日"],
    "dictated": ["安排两名以上合格见证人全程在场", "由其中一名见证人代书", "遗嘱人、代书人和其他见证人签名并写明年、月、日"],
    "printed": ["安排两名以上合格见证人全程在场", "遗嘱人和见证人在每一页签名", "写明年、月、日"],
    "audio_video": ["安排两名以上合格见证人全程在场", "在录音录像中记录遗嘱人和见证人的姓名或肖像", "在录音录像中记录年、月、日"],
    "oral": ["只在危急情况下采用", "安排两名以上合格见证人在场见证", "危急情况消除后能够改用书面或录音录像形式的，立即另行办理"],
    "notarized": ["联系公证机构确认受理材料", "按照公证机构要求完成身份、财产和意思表示核验", "按通知到场办理并领取、妥善保管公证遗嘱"],
    "undecided": ["先确定遗嘱形式", "按所选形式重新核对签名、日期和见证要求", "形式未确定前不要签署"],
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("work data root must be an object")
    return value


def _write_text(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _md(value: Any) -> str:
    if value is None or value == "":
        return "未提供"
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _names(data: dict[str, Any]) -> dict[str, str]:
    return {item.get("id", ""): item.get("display_name", item.get("id", "未知人物")) for item in data.get("people", [])}


def _header(data: dict[str, Any], title: str) -> list[str]:
    audience = data.get("audience_profile", {})
    rules = data.get("rule_context", {})
    return [
        f"# {title}", "",
        f"> **⚠️ {AI_FILE_NOTICE}**", "",
        f"> 工作数据：`{_md(data.get('work_id'))}`  ",
        f"> 数据基准：{_md(data.get('baseline_at'))}  ",
        f"> 用户类型：`{_md(audience.get('audience_type'))}` / 语言档位：`{_md(audience.get('language_profile'))}`  ",
        f"> 规则包：`{_md(rules.get('rule_pack_id'))}@{_md(rules.get('rule_pack_version'))}` / `{_md(rules.get('status'))}`", "",
    ]


def _research_report(data: dict[str, Any]) -> str:
    research = data.get("legal_research", {})
    lines = _header(data, "法律法规与案例检索报告")
    lines.extend([
        "## 检索基准", "",
        f"- 状态：{_md(research.get('status'))}",
        f"- 法域：{_md(research.get('jurisdiction'))}",
        f"- 近年案例窗口：{_md(research.get('recent_case_years'))} 年",
        f"- 检索时间：{_md(research.get('retrieved_at'))}",
        f"- 摘要：{_md(research.get('research_summary'))}", "", "## 法律依据", "",
    ])
    for item in research.get("authorities", []):
        lines.extend([
            f"### {_md(item.get('title'))}", "",
            f"- 发布机关：{_md(item.get('issuing_body'))}", f"- 文号：{_md(item.get('document_number'))}",
            f"- 效力状态：{_md(item.get('effective_status'))}", f"- 原文：<{_md(item.get('source_url'))}>",
            f"- 检索时间：{_md(item.get('retrieved_at'))}", f"- 本次用途：{_md(item.get('relevance'))}",
            f"- 局限：{_md(item.get('limitations'))}", "",
        ])
    if not research.get("authorities"):
        lines.extend(["尚无已核验法律依据。", ""])
    lines.extend(["## 相关案例", ""])
    for item in research.get("cases", []):
        lines.extend([
            f"### {_md(item.get('title'))}", "",
            f"- 法院/发布者：{_md(item.get('court_or_publisher'))}",
            f"- 案号/入库编号：{_md(item.get('case_number_or_library_id'))}",
            f"- 类型：{_md(item.get('source_kind'))}", f"- 日期：{_md(item.get('decision_or_publication_date'))}",
            f"- 原文：<{_md(item.get('source_url'))}>", f"- 本次用途：{_md(item.get('relevance'))}",
            f"- 差异和局限：{_md(item.get('differences'))}", "",
        ])
    if not research.get("cases"):
        lines.extend(["尚无已核验相关案例。", ""])
    lines.extend(["## 检索局限", ""])
    lines.extend(f"- {_md(item)}" for item in research.get("limitations", []))
    return "\n".join(lines)


def _rule_report(data: dict[str, Any], report: dict[str, Any]) -> str:
    lines = _header(data, "遗嘱法律规则检查报告")
    lines.extend([
        "> 本报告仅列示规则包的确定性检查结果。无阻断、检查通过或全部 PASS 均不代表文书可以签署，也不代表遗嘱有效；仍须由律师结合原始材料人工复核。", "",
        "## 汇总", "",
        f"- BLOCKED：{report['counts']['BLOCKED']}", f"- REVIEW_REQUIRED：{report['counts']['REVIEW_REQUIRED']}",
        f"- WARN：{report['counts']['WARN']}", f"- PASS：{report['counts']['PASS']}", "",
    ])
    for item in report["results"]:
        lines.extend([
            f"## [{item['level']}] {_md(item['title'])}", "",
            f"- 规则：`{_md(item['rule_id'])}` / `{_md(item['code'])}`",
            f"- 说明：{_md(item['message'])}",
            f"- 法源引用：{_md('、'.join(item['authority_refs']))}",
            f"- 相关对象：{_md('、'.join(item['related_ids']))}", "",
        ])
    return "\n".join(lines)


def _execution_guide(data: dict[str, Any], rules: dict[str, Any]) -> str:
    plain = data.get("audience_profile", {}).get("language_profile") == "plain"
    plan = data.get("will_execution_plan", {})
    form = str(plan.get("form") or "undecided")
    form_label = WILL_FORM_LABELS.get(form, _md(form))
    pending: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add_pending(title: Any, action: Any) -> None:
        item_title = _md(title)
        if item_title in seen:
            return
        seen.add(item_title)
        pending.append((item_title, _md(action)))

    for item in rules.get("results", []):
        if item.get("level") in {"BLOCKED", "REVIEW_REQUIRED", "WARN"}:
            add_pending(item.get("title"), "补充相关事实或材料，并交由律师复核。")
    for item in (data.get("deliverables") or {}).get("ai_judgment_items", []):
        add_pending(item.get("title"), item.get("next_action") or "交由律师复核。")

    lines = [
        f"# {'遗嘱怎么签、怎么保管、以后怎么办' if plain else '遗嘱执行操作指引'}",
        "",
        f"> **⚠️ {AI_FILE_NOTICE}**",
        "",
        f"> 当前拟采用：**{form_label}**。本指引仅用于律师复核和签署准备。",
    ]
    lines.extend([
        "",
        "## 🧭 一页行动路线",
        "",
        "| 顺序 | 节点 | 必须做什么 |",
        "|---:|---|---|",
    ])
    for index, item in enumerate((data.get("deliverables") or {}).get("execution_guide", []), start=1):
        lines.append(f"| {index} | {_md(item.get('phase'))} | **{_md(item.get('action'))}** |")
    lines.extend(["", "## 还需要判断的事项", ""])
    if pending:
        for title, action in pending:
            lines.append(f"- **{title}**：{action}")
    else:
        lines.append("- 当前没有单独列出的补充事项；仍应由律师结合原始材料整体复核。")
    lines.extend(["", "## ✍️ 签署当天", ""])
    for index, action in enumerate(FORM_CHECKLISTS.get(form, FORM_CHECKLISTS["undecided"]), start=1):
        lines.append(f"{index}. **{action}**。")
    lines.extend([
        "",
        "> **注意：** 不要留空后补。签署前完成最终核对；签署后不要替换单页或继续修改正文。",
        "",
        "## 📦 签署后",
        "",
        "- **扫描或拍照留档**，记录签署时间、地点和在场人员。",
        "- **妥善保管遗嘱原件**，记录保管人和保管位置。",
        "- 婚姻、家庭、财产或意愿发生重大变化时，**重新进行专业复核**。",
    ])
    return "\n".join(lines)


def _conversation_education_links(data: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "name": str(item.get("title") or "未命名普法内容"),
            "main_content": str(item.get("relevance") or "请打开链接查看主要内容。"),
            "link": str(item.get("url") or ""),
        }
        for item in data.get("legal_research", {}).get("education_links", [])
        if isinstance(item, dict) and item.get("verified_access") is True and item.get("url")
    ]


def _person_markers(person: dict[str, Any]) -> str:
    roles = set(person.get("roles", []))
    markers = []
    if roles & {"subject", "testator"}: markers.append("遗嘱人")
    if roles & {"legal_heir", "possible_heir", "potential_heir", "heir"}: markers.append("已知/可能继承人")
    if roles & {"intended_beneficiary", "beneficiary"}: markers.append("拟受益人")
    if "witness" in roles: markers.append("拟任见证人")
    return "、".join(markers or ["已知关系人"])


def _node(prefix: str, value: Any) -> str:
    return prefix + str(value or "unknown").replace("-", "_")


ASSET_TYPE_LABELS = {
    "real_estate": "房产", "financial_assets": "存款或理财", "equity": "股权或合伙份额",
    "vehicles": "车辆", "insurance_rights": "保险相关权利", "claims": "债权",
    "digital_assets": "数字资产", "other": "其他",
}
RELATIONSHIP_LABELS = {
    "spouse": "配偶", "father": "父亲", "mother": "母亲", "son": "儿子", "daughter": "女儿",
    "child": "子女", "sibling": "兄弟姐妹", "grandparent": "祖父母/外祖父母", "other": "其他关系",
    "important_person": "重要关系人", "subject": "遗嘱人", "heir": "继承人",
    "intended_beneficiary": "拟受益人", "beneficiary": "受益人", "witness": "拟任见证人",
    "friend": "友人", "creditor": "债权人",
}
STATUS_LABELS = {
    "uploaded": "已上传", "held": "持有", "missing": "未提供", "need_collect": "需调取",
    "covered": "已安排", "partial": "部分安排", "uncovered": "未安排",
    "confirmed": "已确认", "pending_confirmation": "待确认", "unknown": "未知",
    "not_applicable": "不适用", "complete": "已安排", "incomplete": "待完善",
}


def _label(value: Any, table: dict[str, str]) -> str:
    text = str(value or "")
    return table.get(text, text or "未知")


def _money(value: Any, currency: Any) -> str:
    if value in (None, ""):
        return "未填写"
    try:
        number = f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)
    unit = "元" if str(currency or "CNY").upper() in {"CNY", "RMB"} else str(currency)
    return f"{number}{unit}"


_SVG_PALETTE = {
    "testator": ("#F9D7E4", "#E39BBE", "#8A4A68"),
    "person": ("#DDEBF7", "#A8C8E8", "#3E5C76"),
    "witness": ("#EAE3F7", "#C3B1E1", "#5D4A7A"),
    "asset": ("#FDF3D8", "#E4CD9A", "#7A6234"),
}


def _svg_esc(value: Any) -> str:
    return (str(value or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _clip(value: Any, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _relationship_diagram(data: dict[str, Any]) -> str:
    """关系人与拟继承财产示意图：SVG 图片，中文标签 + 马卡龙配色，零依赖确定性生成。"""
    people = data.get("people", [])
    assets = data.get("assets", [])
    relationships = data.get("relationships", [])
    intentions = data.get("intentions", [])
    node_w, node_h, gap, top = 260, 64, 96, 170
    left_x, right_x, width = 70, 710, 1040
    rows = max(len(people), len(assets), 1)
    height = top + rows * gap + 40
    person_y = {item.get("id"): top + index * gap for index, item in enumerate(people)}
    asset_y = {item.get("id"): top + index * gap for index, item in enumerate(assets)}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'font-family="PingFang SC, Hiragino Sans GB, Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#FFFDFA"/>',
        '<text x="40" y="52" font-size="24" font-weight="700" fill="#5B4A5A">关系人与拟继承财产示意图</text>',
        f'<text x="40" y="80" font-size="12" fill="#9A8C98">{_svg_esc(AI_FILE_NOTICE)}</text>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#E39BBE"/></marker></defs>',
    ]
    legend = [("遗嘱人", "testator"), ("关系人", "person"), ("拟任见证人", "witness"), ("财产", "asset")]
    lx = 40
    for label, key in legend:
        fill, stroke, _ = _SVG_PALETTE[key]
        parts.append(f'<rect x="{lx}" y="100" width="18" height="18" rx="6" fill="{fill}" stroke="{stroke}"/>')
        parts.append(f'<text x="{lx + 24}" y="114" font-size="13" fill="#6B5A6A">{label}</text>')
        lx += 24 + 13 * len(label) + 36
    parts.append(f'<text x="{left_x}" y="{top - 18}" font-size="15" font-weight="600" fill="#6B5A6A">人物</text>')
    parts.append(f'<text x="{right_x}" y="{top - 18}" font-size="15" font-weight="600" fill="#6B5A6A">财产</text>')
    for relation in relationships:
        y1 = person_y.get(relation.get("from_person_id"))
        y2 = person_y.get(relation.get("to_person_id"))
        if y1 is None or y2 is None:
            continue
        cx = left_x + node_w / 2
        parts.append(f'<line x1="{cx}" y1="{y1 + node_h}" x2="{cx}" y2="{y2}" stroke="#C9B8C6" stroke-width="1.6"/>')
        mid = (y1 + node_h + y2) / 2
        rel = str(relation.get("relationship_type") or "")
        rel_label = RELATIONSHIP_LABELS.get(rel, rel if any("\u4e00" <= ch <= "\u9fff" for ch in rel) else "其他关系")
        parts.append(f'<text x="{cx + 10}" y="{mid + 4}" font-size="12" fill="#8A7888">{_svg_esc(rel_label)}</text>')
    for intention in intentions:
        for person_id in intention.get("related_person_ids", []):
            for asset_id in intention.get("related_asset_ids", []):
                y1 = person_y.get(person_id)
                y2 = asset_y.get(asset_id)
                if y1 is None or y2 is None:
                    continue
                x1, x2 = left_x + node_w, right_x
                cy1, cy2 = y1 + node_h / 2, y2 + node_h / 2
                parts.append(
                    f'<path d="M {x1} {cy1} C {(x1 + x2) / 2} {cy1}, {(x1 + x2) / 2} {cy2}, {x2 - 6} {cy2}" '
                    'stroke="#E39BBE" stroke-width="2" fill="none" marker-end="url(#arrow)"/>'
                )
                parts.append(
                    f'<text x="{(x1 + x2) / 2 - 34}" y="{(cy1 + cy2) / 2 - 8}" font-size="12" fill="#B06A8E">拟继承/受益</text>'
                )
    for person in people:
        markers = _person_markers(person)
        key = "testator" if "遗嘱人" in markers else ("witness" if "见证人" in markers else "person")
        fill, stroke, color = _SVG_PALETTE[key]
        y = person_y[person.get("id")]
        parts.append(f'<rect x="{left_x}" y="{y}" width="{node_w}" height="{node_h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        parts.append(f'<text x="{left_x + 16}" y="{y + 27}" font-size="15" font-weight="600" fill="{color}">{_svg_esc(_clip(person.get("display_name"), 14))}</text>')
        parts.append(f'<text x="{left_x + 16}" y="{y + 48}" font-size="12" fill="{color}">{_svg_esc(_clip(markers, 16))}</text>')
    for asset in assets:
        fill, stroke, color = _SVG_PALETTE["asset"]
        y = asset_y[asset.get("id")]
        parts.append(f'<rect x="{right_x}" y="{y}" width="{node_w}" height="{node_h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        parts.append(f'<text x="{right_x + 16}" y="{y + 27}" font-size="15" font-weight="600" fill="{color}">{_svg_esc(_clip(asset.get("description"), 14))}</text>')
        parts.append(f'<text x="{right_x + 16}" y="{y + 48}" font-size="12" fill="{color}">{_svg_esc(_label(asset.get("asset_type"), ASSET_TYPE_LABELS))}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _asset_inventory_md(data: dict[str, Any]) -> str:
    """适于阅读的资产与债务一览表（中文、美观）。"""
    names = _names(data)
    lines = _header(data, "资产与债务清单")
    lines += ["", "## 一、资产", "", "| 编号 | 资产 | 类型 | 权利人与份额 | 估计价值 | 证明材料 | 安排情况 | 确认状态 | 备注 |",
              "|---|---|---|---|---|---|---|---|---|"]
    for asset in data.get("assets", []):
        owners = "；".join(
            f"{names.get(item.get('person_id'), item.get('person_id'))}（{item.get('share_percent') if item.get('share_percent') is not None else '份额未知'}）"
            for item in asset.get("owners", [])
        ) or "未填写"
        lines.append("| " + " | ".join([
            _md(asset.get("id")), _md(asset.get("description")),
            _md(_label(asset.get("asset_type"), ASSET_TYPE_LABELS)), _md(owners),
            _md(_money(asset.get("estimated_value"), asset.get("currency"))),
            _md(_label(asset.get("evidence_status"), STATUS_LABELS)),
            _md(_label(asset.get("arrangement_status"), STATUS_LABELS)),
            _md(_label((asset.get("provenance") or {}).get("confirmation_status"), STATUS_LABELS)),
            _md(asset.get("notes")),
        ]) + " |")
    if not data.get("assets"):
        lines.append("| — | 未申报资产 | — | — | — | — | — | — | — |")
    lines += ["", "## 二、债务与其他义务", "", "| 编号 | 类型 | 描述 | 债权人 | 金额 | 状态 | 备注 |",
              "|---|---|---|---|---|---|---|"]
    for item in data.get("liabilities", []):
        lines.append("| " + " | ".join([
            _md(item.get("id")), _md(item.get("liability_type")), _md(item.get("description")),
            _md(item.get("creditor_masked")), _md(_money(item.get("amount"), item.get("currency"))),
            _md(_label(item.get("status"), STATUS_LABELS)), _md(item.get("notes")),
        ]) + " |")
    if not data.get("liabilities"):
        lines.append("| — | 未申报债务或义务 | — | — | — | — | — |")
    return "\n".join(lines) + "\n"


def build_packet(data: dict[str, Any], output_dir: Path, allow_incomplete: bool = False, force: bool = False) -> dict[str, Any]:
    validation = validate_case(data)
    rules = evaluate_rules(data)
    output_dir.mkdir(parents=True, exist_ok=True)
    known = tuple(dict.fromkeys(BASE_PACKET_FILES + (WILL_FILE,) + LEGACY_PACKET_FILES))
    existing = [output_dir / name for name in known if (output_dir / name).exists()]
    if existing and not force:
        raise FileExistsError(f"deliverable files already exist in {output_dir}; use --force")
    if force:
        for path in existing:
            path.unlink()
    requested = set(data.get("output_preferences", {}).get("requested_deliverables", []))
    draft_allowed = validation["valid"] and data.get("legal_research", {}).get("status") == "verified" and data.get("status") in OUTPUT_GATE_STATUSES and rules["counts"]["BLOCKED"] == 0
    preparation_only = True
    metadata = {
        "builder": "lawd-estate-planning.build_packet",
        "builder_version": "0.5.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preparation_only": True,
        "signature_ready": False,
        "signature_ready_reason": "本 Skill 仅生成待律师人工复核的 AI 草案，不作可直接签署认定。",
        "draft_generation_allowed": draft_allowed,
        "requested_deliverables": sorted(requested),
        "rule_evaluation": rules["counts"],
        "ai_notice": AI_FILE_NOTICE,
        "delivery_notice": AI_DELIVERY_NOTICE,
    }
    validation = {"ai_notice": AI_FILE_NOTICE, **validation, "rule_evaluation": rules, "packet_metadata": metadata}
    _write_json(output_dir / "validation-report.json", validation)
    files = [output_dir / name for name in ALWAYS_PACKET_FILES]
    if "legal_research_report" in requested:
        path = output_dir / OPTIONAL_PACKET_FILES["legal_research_report"]
        _write_text(path, _research_report(data)); files.append(path)
    _write_text(output_dir / "02-legal-rule-evaluation.md", _rule_report(data, rules))
    _write_text(output_dir / "03-execution-guide.md", _execution_guide(data, rules))
    if "relationship_diagram" in requested:
        path = output_dir / OPTIONAL_PACKET_FILES["relationship_diagram"]
        _write_text(path, _relationship_diagram(data)); files.append(path)
    if "asset_inventory" in requested:
        path = output_dir / OPTIONAL_PACKET_FILES["asset_inventory"]
        _write_text(path, _asset_inventory_md(data)); files.append(path)
    if draft_allowed and "will_docx" in requested:
        path = output_dir / WILL_FILE
        build_will_docx(data, path, force=force); files.append(path)
    return {
        "output_dir": str(output_dir),
        "files": [str(path) for path in sorted(files)],
        "validation": validation["counts"],
        "rule_evaluation": rules["counts"],
        "preparation_only": preparation_only,
        "signature_ready": False,
        "draft_docx_generated": draft_allowed and "will_docx" in requested,
        "ai_notice": AI_FILE_NOTICE,
        "delivery_notice": AI_DELIVERY_NOTICE,
        "conversation_education_links": _conversation_education_links(data) if "education_content" in requested else [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_data", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_packet(_load_json(args.work_data), args.output_dir, args.allow_incomplete, args.force)
    except (OSError, json.JSONDecodeError, ValueError, FileExistsError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
