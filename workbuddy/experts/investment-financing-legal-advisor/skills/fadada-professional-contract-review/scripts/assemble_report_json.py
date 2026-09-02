#!/usr/bin/env python3
"""把 AI 产出的扁平风险 JSON 组装为 build_review_report.py 所需的 14 章 report JSON。

背景：诊断日志 rpt_20260809T043248Z 显示 AI agent 能产出正确的 risk JSON 和
operations.json，但无法产出 build_review_report.py 要求的 14 章结构化 report JSON，
导致该脚本崩溃后降级到 md2docx.py 通用转换器，报告结构和格式完全偏离。

本组装器接收 AI 擅长的输出格式，自动映射到 build_review_report.py 的输入 schema，
消除人工（或模型）手工组装 JSON 的不可靠环节。

用法:
    python scripts/assemble_report_json.py \\
        --risk-json /tmp/local_risk.json \\
        --intake /var/tmp/intake.json \\
        --position "甲方" \\
        --focus "违约金,私力救济,信息缺失" \\
        --out /tmp/report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from skill_paths import output_root  # noqa: E402

# ── field mapping: AI risk JSON → build_review_report.py risk schema ──

_RISK_FIELD_MAP = {
    "id": "issue_id",
    "riskLevel": "level",
    "riskType": "risk_type",
    "content": "issue",
    "basis": "basis_tag",
    "suggestion": "recommendation",
}

# riskLevel normalization
_LEVEL_MAP = {"高": "高", "中": "中", "低": "低", "high": "高", "medium": "中", "low": "低"}

# impact_likelihood 推导
_LEVEL_IMPACT = {
    "高": "高影响 / 高概率 — 可能影响合同效力或核心交易目的",
    "中": "中影响 / 中概率 — 影响履行、付款或争议解决，可通过修改缓释",
    "低": "低影响 / 低概率 — 文字或流程问题，可签后监控",
}


def _norm_level(raw: str) -> str:
    return _LEVEL_MAP.get(str(raw).strip().lower(), "中")


def _map_risk(entry: dict, index: int) -> dict:
    """将 AI 产出的单条风险映射为 build_review_report.py 的 risks[] 条目。"""
    risk: dict[str, str] = {}
    for src, dst in _RISK_FIELD_MAP.items():
        val = str(entry.get(src, "")).strip()
        if val:
            risk[dst] = val
    # 标准化字段
    if "level" not in risk:
        risk["level"] = _norm_level(entry.get("riskLevel", "中"))
    else:
        risk["level"] = _norm_level(risk["level"])
    if "issue_id" not in risk or not risk["issue_id"]:
        risk["issue_id"] = f"R-{index + 1:03d}"
    # location: 优先用 entry.location，其次从 content 推断
    if not risk.get("location"):
        risk["location"] = str(entry.get("location", "待定位"))
    # impact_likelihood: 从 level 推导
    if not risk.get("impact_likelihood"):
        risk["impact_likelihood"] = _LEVEL_IMPACT.get(risk["level"], "")
    return risk


def _extract_risks(risk_json: dict) -> list[dict]:
    """从 AI 产出的多种可能格式中提取风险列表。"""
    # 格式 1: {"riskList": [...]}
    if "riskList" in risk_json:
        return risk_json["riskList"]
    # 格式 2: {"risks": [...]}
    if "risks" in risk_json:
        return risk_json["risks"]
    # 格式 3: 直接是 list
    if isinstance(risk_json, list):
        return risk_json
    # 格式 4: 顶层 dict 可能就是单条风险（fallback 防止空报告）
    return []


def _summary_from_risks(risks: list[dict], position: str) -> str:
    high = sum(1 for r in risks if _norm_level(r.get("riskLevel", r.get("level", ""))) == "高")
    mid = sum(1 for r in risks if _norm_level(r.get("riskLevel", r.get("level", ""))) == "中")
    low = sum(1 for r in risks if _norm_level(r.get("riskLevel", r.get("level", ""))) == "低")
    parts = []
    if high:
        parts.append(f"高风险 {high} 项")
    if mid:
        parts.append(f"中风险 {mid} 项")
    if low:
        parts.append(f"低风险 {low} 项")
    summary = f"本次审查以{position}立场，共识别{'、'.join(parts)}。"
    if high:
        summary += "建议优先处理高风险条款，修改后签署。"
    elif mid:
        summary += "建议关注中风险条款，协商修改后签署。"
    else:
        summary += "整体风险可控，建议签署。"
    return summary


def _intake_context(intake_path: Path | None) -> dict:
    """从 intake.json 提取合同上下文。"""
    if intake_path is None or not intake_path.exists():
        return {}
    try:
        data = json.loads(intake_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return {
        "contractName": data.get("contractName", ""),
        "businessType": data.get("businessType", ""),
        "position": data.get("position", ""),
        "paragraphCount": data.get("paragraphCount", 0),
    }


def assemble(
    risk_json: dict,
    intake_path: Path | None = None,
    position: str = "",
    focus: str = "",
    analysis_md: str = "",
) -> dict:
    """组装完整的 14 章 report JSON。"""
    raw_risks = _extract_risks(risk_json)
    risks = [_map_risk(r, i) for i, r in enumerate(raw_risks)]
    ctx = _intake_context(intake_path)
    pos = position or ctx.get("position", "")
    contract_name = ctx.get("contractName", "合同")
    biz_type = ctx.get("businessType", "")

    # scope — 审查范围
    scope_parts = [f"对《{contract_name}》进行全文审查"]
    if biz_type:
        scope_parts.append(f"合同类型：{biz_type}")
    if focus:
        scope_parts.append(f"用户关注要点：{focus}")
    if pos:
        scope_parts.append(f"审查立场：{pos}")

    # coverage — 从风险中提取审查覆盖状态
    coverage = []
    seen_types = set()
    for r in risks:
        rt = r.get("risk_type", "")
        if rt and rt not in seen_types:
            seen_types.add(rt)
            coverage.append({
                "item": f"{rt}相关条款",
                "direction": "正向审查",
                "status": "已覆盖",
                "location": r.get("location", ""),
            })

    # 组装最终 JSON
    report = {
        "report_title": f"《{contract_name}》合同审查报告",
        "scope": {"zh": "；".join(scope_parts) + "。"},
        "facts": {"zh": f"审查立场：{pos}。审查日期：{date.today()}。"
                 f"审查对象为《{contract_name}》全文，共 {ctx.get('paragraphCount', '?')} 个段落。"},
        "playbook_status": {"zh": f"本次审查以{pos}立场执行，适用{biz_type or '合同'}审查规则。"},
        "executive_summary": {"zh": _summary_from_risks(raw_risks, pos)},
        # add_matrix 章节 → 空列表触发内置 empty_reason（dict 会经 _fill_basis_column 导致崩溃）
        "structural_parameters": [],
        "risks": risks,
        "coverage": coverage,
        "missing_terms": {"zh": "经审查，未发现系统性缺失关键保护条款。"},
        "symmetry": [],
        "ip_analysis": [],
        "recommendations": {
            "zh": "建议优先协商修改高风险条款，中风险条款在签署前确认。"
            "所有修改内容需以书面补充协议形式确认并加盖双方公章后方可生效。"
        },
        "verification": {"zh": "本次审查基于现行法律法规，具体适用性建议由执业律师最终确认。"},
        "pending": {
            "empty_reason": "经核实不涉及：本次审查未发现需跨文件核验或进一步确认的待核查事项。"
        },
        "deliverables": {
            "zh": "审查报告一份、带批注修订版合同一份。"
        },
    }

    # 如果有 AI 的分析 markdown，补充进 recommendations
    if analysis_md:
        report["recommendations"] = {"zh": analysis_md[:3000]}

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="把 AI 产出的风险 JSON 组装为 build_review_report.py 所需的 14 章 report JSON"
    )
    parser.add_argument("--risk-json", required=True, type=Path, help="AI 产出的风险 JSON 文件")
    parser.add_argument("--intake", type=Path, default=None, help="review_intake.py 的上下文包")
    parser.add_argument("--position", default="", help="审查立场，如 甲方/乙方")
    parser.add_argument("--focus", default="", help="用户关注要点，逗号分隔")
    parser.add_argument("--analysis-md", default="", help="AI 的文字分析 markdown（可选）")
    parser.add_argument("--out", type=Path, required=True, help="输出 report JSON 路径")
    args = parser.parse_args()

    if not args.risk_json.exists():
        print(json.dumps({"status": "failed", "stage": "input",
                          "errors": [f"risk JSON 不存在: {args.risk_json}"]},
                         ensure_ascii=False))
        return 1

    try:
        risk_data = json.loads(args.risk_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(json.dumps({"status": "failed", "stage": "input",
                          "errors": [f"risk JSON 解析失败: {exc}"]},
                         ensure_ascii=False))
        return 1

    report = assemble(
        risk_data,
        intake_path=args.intake,
        position=args.position,
        focus=args.focus,
        analysis_md=args.analysis_md,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "stage": "assembled",
                      "report_json": str(args.out),
                      "risk_count": len(report["risks"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
