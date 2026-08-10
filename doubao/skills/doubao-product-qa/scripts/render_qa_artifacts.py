#!/usr/bin/env python3
"""从唯一数据源 qa-run.json 确定性生成 Markdown、CSV 和设备摘要。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gate_policy
from qa_run_common import (
    PROFILE_FILES,
    acceptance_status,
    case_status,
    coverage_snapshot,
    requested_delivery,
    semantic_findings,
)


TRACE_HEADERS = [
    "requirement_id", "requirement", "source", "risk", "actor", "trigger", "rule",
    "observable_result", "impact_scope", "risk_mechanism_ids", "test_case_ids", "status", "notes",
]
CASE_HEADERS = [
    "case_id", "module", "title", "priority", "type", "preconditions", "steps",
    "test_data", "expected_result", "requirement_ids", "risk_mechanism_ids",
    "release_blocking_reason", "automation_candidate", "execution_mode", "assigned_to",
    "manual_reason", "evidence_expected", "status", "notes",
]
MANUAL_CASE_HEADERS = [
    "case_id", "module", "title", "priority", "preconditions", "steps", "test_data",
    "expected_result", "assigned_to", "evidence_expected", "previous_status", "attempt",
    "status", "operator", "actual_result", "started_at", "finished_at", "evidence_paths",
    "tester_notes", "retest_of",
]


def lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value)]


def bullets(items: Any, empty: str = "- 无") -> str:
    values = lines(items)
    return "\n".join(f"- {item}" for item in values) if values else empty


def numbered(items: Any) -> str:
    values = lines(items)
    return "\n".join(f"{index}. {item}" for index, item in enumerate(values, start=1))


def evidence_paths(run: dict[str, Any], evidence_ids: list[str]) -> list[str]:
    evidence = {str(item.get("id")): item for item in run.get("evidence", [])}
    result = []
    for evidence_id in evidence_ids:
        item = evidence.get(str(evidence_id), {})
        path = item.get("path")
        result.append(str(path or item.get("description") or evidence_id))
    return result


def latest_case_note(run: dict[str, Any], case_id: str) -> str:
    executions = [item for item in run.get("executions", []) if item.get("case_id") == case_id]
    if not executions:
        return ""
    latest = executions[-1]
    parts = [str(latest.get("summary", "")).strip()]
    assertions = lines(latest.get("assertions"))
    if assertions:
        parts.append("断言：" + "；".join(assertions))
    paths = evidence_paths(run, [str(value) for value in latest.get("evidence_ids", [])])
    if paths:
        parts.append("证据：" + "；".join(paths))
    return "；".join(part for part in parts if part)


def latest_execution(run: dict[str, Any], case_id: str) -> dict[str, Any] | None:
    executions = [item for item in run.get("executions", []) if item.get("case_id") == case_id]
    return executions[-1] if executions else None


def requirement_status(run: dict[str, Any], requirement: dict[str, Any]) -> tuple[str, list[str]]:
    req_id = str(requirement.get("id", ""))
    linked = [
        str(case.get("id", ""))
        for case in run.get("cases", [])
        if req_id in [str(value) for value in case.get("requirement_ids", [])]
    ]
    override = requirement.get("coverage_status")
    if override:
        return str(override), linked
    return ("已覆盖" if linked else "未覆盖"), linked


def environment_rows(env: Any) -> list[str]:
    """环境写成人读的行。原实现直接 json.dumps 出一坨字典塞进正文。"""
    if not isinstance(env, dict) or not env:
        return []
    return [f"{key}：{value}" for key, value in sorted(env.items())]


def environment_line(env: Any) -> str:
    rows = environment_rows(env)
    return "；".join(rows) if rows else "未记录"


def screenshot_line(run: dict[str, Any]) -> list[str]:
    """截图策略是内部状态；只有真的确认过策略才对读者有意义。"""
    policy = run.get("screenshot_policy")
    if policy in (None, "", "unconfirmed"):
        return []
    return [f"- 截图策略：{policy}"]


def unverified_line(run: dict[str, Any], counts: dict[str, int]) -> str:
    """存在未执行/阻塞时禁止输出"无"——那是自相矛盾的成品。"""
    declared = "；".join(lines(run.get("unverified")))
    if declared:
        return declared
    pending = int(counts.get("未执行", 0)) + int(counts.get("阻塞", 0))
    if pending:
        return f"{pending} 条用例本轮未执行，其覆盖的能力均未验证（明细见用例表）"
    return "无"


def render_input_notes(run: dict[str, Any]) -> str:
    input_info = run.get("input", {})
    env = run.get("environment", {})
    artifacts = []
    for item in input_info.get("artifacts", []):
        item_progress = ""
        if item.get("type") in {"spreadsheet", "archive"}:
            item_progress = (
                f"；核对 {item.get('reviewed_item_count', 0)}/{item.get('item_count', 0)}"
            )
        blocked = ""
        if item.get("access_status") == "blocked":
            blocked = (
                f"；原因：{item.get('blocked_reason', '未记录')}"
                f"；解锁：{item.get('minimal_unblock_action', '未记录')}"
            )
        artifacts.append(
            f"{item.get('id')}｜{item.get('type')}｜{item.get('access_status')}"
            f"｜{item.get('locator')}｜{item.get('coverage_note', '')}{item_progress}{blocked}"
        )
    return "\n".join([
        "# 输入记录", "",
        f"- 测试目标：{input_info.get('summary', run.get('target', {}).get('name', '未提供'))}",
        f"- 输入来源：{'；'.join(lines(input_info.get('sources'))) or '未记录'}",
        f"- 环境：{environment_line(env)}",
        *screenshot_line(run),
        "", "## 材料清点", "", bullets(artifacts), "",
        "", "## 假设", "", bullets(input_info.get("assumptions")), "",
        "## 待确认", "",
        bullets([
            f"{item.get('id')}：{item.get('question')}；影响：{item.get('impact')}；下一步：{item.get('next_action', '待指定')}"
            for item in run.get("open_questions", [])
            if item.get("status") == "open"
        ]), "",
    ])


def render_plan(run: dict[str, Any]) -> str:
    plan = run.get("plan", {})
    risks = [f"{item.get('id')}：{item.get('title')}（{item.get('priority')}）" for item in run.get("risks", [])]
    handoff = run.get("manual_handoff", {})
    execution_route = (
        f"自动化不可用，转人工执行：{handoff.get('reason')}；详见 `10-manual-test-guide.md`。"
        if handoff.get("required")
        else f"选择路径：{run.get('selected_path', '未确定')}"
    )
    return "\n".join([
        f"# {run.get('target', {}).get('name', run['run_id'])} 测试计划", "",
        "## 目标与范围", "", bullets(plan.get("scope") or plan.get("objectives")), "",
        "## 不在范围", "", bullets(plan.get("out_of_scope")), "",
        "## 执行方式与降级", "", execution_route, "",
        "## 风险", "", bullets(risks), "",
        "## 环境", "", bullets(environment_rows(run.get("environment", {})), "未记录"), "",
        "## 准入", "", bullets(plan.get("entry_criteria")), "",
        "## 准出", "", bullets(plan.get("exit_criteria")), "",
        "## 回归", "", bullets(plan.get("regression")), "",
    ])


def write_traceability(path: Path, run: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACE_HEADERS)
        writer.writeheader()
        for requirement in run.get("requirements", []):
            status, linked = requirement_status(run, requirement)
            behavior = requirement.get("behavior", {})
            mechanism_ids = [
                str(item.get("id"))
                for item in run.get("risk_mechanisms", [])
                if requirement.get("id") in item.get("requirement_ids", [])
            ]
            writer.writerow({
                "requirement_id": requirement.get("id", ""),
                "requirement": requirement.get("summary", ""),
                "source": requirement.get("source", ""),
                "risk": requirement.get("risk", ""),
                "actor": behavior.get("actor", ""),
                "trigger": behavior.get("trigger", ""),
                "rule": behavior.get("rule", ""),
                "observable_result": behavior.get("observable_result", ""),
                "impact_scope": ";".join(lines(requirement.get("impact_scope"))),
                "risk_mechanism_ids": ";".join(mechanism_ids),
                "test_case_ids": ";".join(linked),
                "status": status,
                "notes": requirement.get("notes", ""),
            })


def write_cases(path: Path, run: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_HEADERS)
        writer.writeheader()
        for case in run.get("cases", []):
            writer.writerow({
                "case_id": case.get("id", ""),
                "module": case.get("module", ""),
                "title": case.get("title", ""),
                "priority": case.get("priority", ""),
                "type": case.get("type", ""),
                "preconditions": "；".join(lines(case.get("preconditions"))),
                "steps": "\n".join(f"{index}. {item}" for index, item in enumerate(lines(case.get("steps")), start=1)),
                "test_data": case.get("test_data", ""),
                "expected_result": "；".join(lines(case.get("expected_result"))),
                "requirement_ids": ";".join(str(value) for value in case.get("requirement_ids", [])),
                "risk_mechanism_ids": ";".join(str(value) for value in case.get("risk_mechanism_ids", [])),
                "release_blocking_reason": case.get("release_blocking_reason", ""),
                "automation_candidate": case.get("automation_candidate", "否"),
                "execution_mode": case.get("execution_mode", "automated"),
                "assigned_to": case.get("assigned_to", ""),
                "manual_reason": case.get("manual_reason", ""),
                "evidence_expected": "；".join(lines(case.get("evidence_expected"))),
                "status": case_status(run, str(case.get("id", ""))),
                "notes": latest_case_note(run, str(case.get("id", ""))) or case.get("notes", ""),
            })


def render_manual_guide(run: dict[str, Any]) -> str:
    handoff = run.get("manual_handoff", {})
    selected_ids = {str(value) for value in handoff.get("case_ids", [])}
    manual_cases = [
        case for case in run.get("cases", [])
        if (str(case.get("id", "")) in selected_ids if selected_ids else case.get("execution_mode") in {"manual", "hybrid"})
    ]
    rows = [
        "# 人工测试执行指南", "",
        "> 自动化执行当前不可用。本文件是可直接交给用户或 QA 操作的降级测试方案；未实际操作前，所有结果均为“未执行”。", "",
        "## 降级原因", "",
        f"- 目标平台：{handoff.get('target_platform') or run.get('target', {}).get('type', '未记录')}",
        f"- 当前宿主：{run.get('environment', {}).get('host_os', '未记录')}",
        f"- 原因：{handoff.get('reason', '未记录')}",
        f"- 自动化执行等级：`{run.get('execution_level', 'blocked')}`",
        f"- 人工交接状态：`{handoff.get('status', 'pending')}`", "",
        "## 执行前准备", "", bullets(handoff.get("prerequisites")), "",
        "## 统一证据要求", "", bullets(handoff.get("evidence_requirements")), "",
        "## 人工操作用例", "",
    ]
    for case in manual_cases:
        case_id = str(case.get("id", ""))
        rows.extend([
            f"### 【人工操作】【{case.get('priority', 'P2')}】{case_id}：{case.get('title', '')}", "",
            f"- 模块：{case.get('module', '')}",
            f"- 执行方式：`{case.get('execution_mode', 'manual')}`",
            f"- 建议操作人：{case.get('assigned_to') or handoff.get('operator') or '用户或 QA'}",
            f"- 必须人工操作的原因：{case.get('manual_reason') or handoff.get('reason', '未记录')}",
            f"- 当前状态：**{case_status(run, case_id)}**", "",
            "#### 前置条件", "", bullets(case.get("preconditions")), "",
            "#### 测试数据", "", str(case.get("test_data", "无特殊数据")), "",
            "#### 操作步骤", "", numbered(case.get("steps")) or "未记录", "",
            "#### 预期结果", "", bullets(case.get("expected_result")), "",
            "#### 需要回传的证据", "", bullets(case.get("evidence_expected") or handoff.get("evidence_requirements")), "",
            "#### 结果填写", "",
            "- 实际结果：待填写",
            "- 状态：未执行（可改为通过/失败/阻塞/不适用）",
            "- 证据记录、文件或链接：待填写",
            "- 备注：待填写", "",
        ])
    rows.extend([
        "## 结果回传", "", bullets(handoff.get("result_submission")), "",
        "回传结果后，将人工执行记录写入 `qa-run.json.executions`，`execution_method` 使用 `manual`，并保留操作人、实际结果和证据引用；再重新生成测试报告。", "",
        "## 结论限制", "",
        "人工步骤完成并回传证据前，不得写“通过”“自动化通过”或给出建议上线结论。", "",
    ])
    return "\n".join(rows)


def manual_cases(run: dict[str, Any]) -> list[dict[str, Any]]:
    selected_ids = {str(value) for value in run.get("manual_handoff", {}).get("case_ids", [])}
    return [
        case for case in run.get("cases", [])
        if (str(case.get("id", "")) in selected_ids if selected_ids else case.get("execution_mode") in {"manual", "hybrid"})
    ]


def render_manual_plan(run: dict[str, Any]) -> str:
    handoff = run.get("manual_handoff", {})
    plan = run.get("plan", {})
    return "\n".join([
        "# 人工测试计划", "",
        f"- 测试目标：{run.get('target', {}).get('name', run['run_id'])}",
        f"- 目标平台：{handoff.get('target_platform') or run.get('target', {}).get('type', '未记录')}",
        f"- 建议执行人：{handoff.get('operator') or '人工 QA'}",
        f"- 人工交接状态：`{handoff.get('status', 'pending')}`",
        f"- 自动化不可用原因：{handoff.get('reason', '未记录')}", "",
        "## 测试范围", "", bullets(plan.get("scope") or plan.get("objectives")), "",
        "## 不在范围", "", bullets(plan.get("out_of_scope")), "",
        "## 执行前准备", "", bullets(handoff.get("prerequisites")), "",
        "## 准出条件", "", bullets(plan.get("exit_criteria") or ["P0/P1 人工用例已执行并回传结果", "失败和阻塞项已完成归因"]), "",
        "## 结果处理", "",
        "填写 `02-manual-test-cases.csv` 的结果列后交回 Skill；不要修改用例标题、步骤或预期结果。", "",
    ])


def write_manual_cases(path: Path, run: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handoff = run.get("manual_handoff", {})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANUAL_CASE_HEADERS)
        writer.writeheader()
        for case in manual_cases(run):
            case_id = str(case.get("id", ""))
            latest = latest_execution(run, case_id)
            previous_attempt = latest.get("attempt", 0) if latest else 0
            next_attempt = int(previous_attempt) + 1 if isinstance(previous_attempt, int) else 1
            writer.writerow({
                "case_id": case_id,
                "module": case.get("module", ""),
                "title": case.get("title", ""),
                "priority": case.get("priority", ""),
                "preconditions": "；".join(lines(case.get("preconditions"))),
                "steps": "\n".join(f"{index}. {item}" for index, item in enumerate(lines(case.get("steps")), start=1)),
                "test_data": case.get("test_data", ""),
                "expected_result": "；".join(lines(case.get("expected_result"))),
                "assigned_to": case.get("assigned_to") or handoff.get("operator") or "人工 QA",
                "evidence_expected": "；".join(lines(case.get("evidence_expected"))),
                "previous_status": case_status(run, case_id),
                "attempt": next_attempt,
                "status": "未执行",
                "operator": "",
                "actual_result": "",
                "started_at": "",
                "finished_at": "",
                "evidence_paths": "",
                "tester_notes": "",
                "retest_of": latest.get("id", "") if latest else "",
            })


def render_manual_acceptance(run: dict[str, Any]) -> str:
    rows = ["# 人工验收清单", "", "> 勾选状态由 qa-run.json 中的人工执行记录派生；不要仅修改本文档表示通过。", ""]
    for case in manual_cases(run):
        if str(case.get("priority", "")) not in {"P0", "P1"}:
            continue
        status = case_status(run, str(case.get("id", "")))
        rows.append(f"- [{'x' if status == '通过' else ' '}] 【人工操作】{case.get('id')} {case.get('title')} — {status}")
    rows.extend(["", "## 发布门禁", "", "- [ ] 所有 P0 人工用例有实际结果和证据记录", "- [ ] 所有失败、阻塞和缺陷候选已完成归因", "- [ ] 首次失败证据未被复测覆盖", ""])
    return "\n".join(rows)


def render_evidence_guide(run: dict[str, Any]) -> str:
    policy = str(run.get("screenshot_policy", "unconfirmed"))
    if policy == "off":
        screenshot_rule = "截图已关闭：不要要求截图或录屏；使用文字观察、版本号、时间点、日志、错误文案或请求信息。"
    elif policy in {"on", "all_steps", "failure_only"}:
        screenshot_rule = f"截图策略为 `{policy}`：仅按该策略采集，避免包含账号、通知或私人数据。"
    else:
        screenshot_rule = "截图策略尚未确认：先询问用户；确认前使用文字观察、版本号、时间点、日志或错误文案。"
    handoff = run.get("manual_handoff", {})
    return "\n".join([
        "# 人工证据指南", "",
        "## 截图策略", "", screenshot_rule, "",
        "## 本轮统一要求", "", bullets(handoff.get("evidence_requirements")), "",
        "## 按问题类型取证", "",
        "- 静态展示：记录页面、控件、文案、设备和版本；截图仅在策略允许时使用。",
        "- 交互或状态：记录完整步骤、发生时间、前后状态；策略允许时可录屏。",
        "- API：记录请求摘要、响应状态、错误码和 request ID，不粘贴密钥。",
        "- Crash：记录最后操作、时间、设备/版本和可获得的 crash/log 文件。",
        "- 偶现：保留第一次失败，再单独记录每次复测，不覆盖原始证据。", "",
        "## 路径填写", "",
        "在 CSV 的 `evidence_paths` 中使用英文分号分隔多个相对路径或 URL。没有文件时，详细填写 `actual_result` 和 `tester_notes`，Skill 会登记为人工观察证据。", "",
    ])


def render_manual_risks_and_blockers(run: dict[str, Any]) -> str:
    rows = ["# 人工测试风险与阻塞", "", "## 自动化阻塞", ""]
    blockers = run.get("blockers", [])
    if blockers:
        for item in blockers:
            rows.extend([
                f"### {item.get('id', 'BLOCKER')}：{item.get('reason', '未记录')}", "",
                f"- 影响用例：{'；'.join(lines(item.get('affected_case_ids'))) or '未记录'}",
                "- 恢复自动化的可选动作：",
                bullets(item.get("minimal_unblock_actions")), "",
            ])
    else:
        rows.extend(["- 无", ""])
    rows.extend(["## 产品与发布风险", ""])
    if run.get("risks"):
        for risk in run["risks"]:
            rows.extend([f"- {risk.get('id')}（{risk.get('priority')}）：{risk.get('title')} — {risk.get('description')}"])
    else:
        rows.append("- 暂无新增风险")
    rows.extend(["", "## 当前限制", "", "人工用例未完成或结果未导回前，发布结论保持“无法判断”。", ""])
    return "\n".join(rows)


def render_manual_bundle(out: Path, run: dict[str, Any]) -> list[str]:
    root = out / "manual-handoff"
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "01-manual-test-plan.md": render_manual_plan(run),
        "03-manual-acceptance-checklist.md": render_manual_acceptance(run),
        "04-evidence-guide.md": render_evidence_guide(run),
        "05-risks-and-blockers.md": render_manual_risks_and_blockers(run),
    }
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    write_manual_cases(root / "02-manual-test-cases.csv", run)
    return [f"manual-handoff/{name}" for name in [
        "01-manual-test-plan.md", "02-manual-test-cases.csv",
        "03-manual-acceptance-checklist.md", "04-evidence-guide.md", "05-risks-and-blockers.md",
    ]]


def render_acceptance(run: dict[str, Any]) -> str:
    values = run.get("acceptance_checks", [])
    if not values:
        values = [
            {
                "id": f"AC-AUTO-{index:03d}",
                "title": case.get("title"),
                "type": "core_flow",
                "case_ids": [case.get("id")],
                "blocking": case.get("priority") == "P0",
                "notes": "由 P0/P1 用例自动投影；正式完整提测应在 canonical 中提炼验收项。",
            }
            for index, case in enumerate(
                [
                    item
                    for item in run.get("cases", [])
                    if str(item.get("priority", "")) in {"P0", "P1"}
                ],
                start=1,
            )
        ]
    counts: dict[str, int] = {
        "通过": 0,
        "未通过": 0,
        "阻塞": 0,
        "待验证": 0,
        "不适用": 0,
    }
    rows = ["# 验收清单", ""]
    for item in values:
        status = acceptance_status(run, item)
        counts[status] = counts.get(status, 0) + 1
        checked = status == "通过"
        suffix = f" — {item.get('notes')}" if item.get("notes") else ""
        rows.append(
            f"- [{'x' if checked else ' '}] `{item.get('id', 'AC-UNSET')}`"
            f" [{item.get('type', 'core_flow')}] {item.get('title', '未命名检查')}"
            f" — **{status}**；blocking={str(bool(item.get('blocking'))).lower()}"
            f"；关联：{'；'.join(lines(item.get('case_ids'))) or '无'}{suffix}"
        )
    total = len(values)
    rows.extend([
        "",
        "## 汇总",
        "",
        (
            f"- 总数：{total}；通过：{counts['通过']}；未通过：{counts['未通过']}；"
            f"阻塞：{counts['阻塞']}；待验证：{counts['待验证']}；不适用：{counts['不适用']}"
        ),
        (
            f"- 复算：{counts['通过']} + {counts['未通过']} + {counts['阻塞']} + "
            f"{counts['待验证']} + {counts['不适用']} = {total}"
        ),
        "",
    ])
    return "\n".join(rows)


def render_risks(run: dict[str, Any]) -> str:
    rows = ["# 风险与测试机制", ""]
    mechanisms = run.get("risk_mechanisms", [])
    if mechanisms:
        rows.extend(["## 风险机制闭环", ""])
        for mechanism in mechanisms:
            rows.extend([
                f"### {mechanism.get('id')}：{mechanism.get('title')}（{mechanism.get('priority')} / {mechanism.get('status')}）",
                "",
                f"- 失效方式：{mechanism.get('failure_mode')}",
                f"- 业务影响：{mechanism.get('business_impact')}",
                f"- Oracle：{'；'.join(lines(mechanism.get('oracle'))) or '未记录'}",
                f"- 关联需求：{'；'.join(lines(mechanism.get('requirement_ids'))) or '未记录'}",
                f"- 关联用例：{'；'.join(lines(mechanism.get('case_ids'))) or '未记录'}",
                "",
            ])
    rows.extend(["## 其他风险与问题", ""])
    if not run.get("risks"):
        return "\n".join(rows + ["本轮未识别到新增风险。", ""])
    for risk in run["risks"]:
        rows.extend([
            f"## {risk.get('id')}：{risk.get('title')}（{risk.get('priority')}）",
            "", str(risk.get("description", "")), "",
            f"- 影响：{risk.get('impact', '未记录')}",
            f"- 缓解措施：{risk.get('mitigation', '未记录')}", "",
        ])
    return "\n".join(rows)


def render_bugs(run: dict[str, Any]) -> str:
    rows = ["# Bug 列表", ""]
    candidates = run.get("bug_candidates", [])
    if not run.get("bugs") and not candidates:
        message = "本轮执行未发现缺陷。" if run.get("executions") else "本轮尚未执行，无法判断是否存在产品缺陷。"
        return "\n".join(rows + [message, ""])
    if candidates:
        rows.extend(["## 待分析的人工失败（缺陷候选）", "", "以下失败尚未完成产品缺陷、环境、数据或需求问题归因，不能直接当作正式 Bug。", ""])
        for candidate in candidates:
            rows.extend([
                f"### {candidate.get('id')}：{candidate.get('title')}", "",
                f"- 关联用例：{candidate.get('case_id')}",
                f"- 状态：{candidate.get('status')}",
                f"- 首次失败执行：{candidate.get('first_execution_id')}",
                f"- 最近执行：{candidate.get('latest_execution_id', candidate.get('first_execution_id'))}",
                f"- 首次失败已保留：{str(bool(candidate.get('first_failure_preserved'))).lower()}",
                f"- 说明：{candidate.get('summary', '需要复现和分层归因后再生成正式 Bug。')}", "",
            ])
    evidence = {str(item.get("id")): item for item in run.get("evidence", [])}
    for bug in run["bugs"]:
        paths = [str(evidence.get(str(value), {}).get("path") or value) for value in bug.get("evidence_ids", [])]
        analysis = bug.get("analysis", {})
        if isinstance(analysis, dict):
            analysis_lines = [
                f"- 问题分类：{analysis.get('classification', '待补充')}",
                f"- 触发条件假设：{analysis.get('trigger_hypothesis', '待补充')}",
                f"- 近期改动关联：{analysis.get('change_correlation', '待补充')}",
                f"- 波及范围：{analysis.get('blast_radius', '待补充')}",
                f"- 置信度：{analysis.get('confidence', 'unknown')}",
            ]
        else:
            analysis_lines = [str(analysis or "待分析")]
        rows.extend([
            f"## {bug.get('id')}：{bug.get('title')}", "",
            f"- 所属模块：{bug.get('module')}",
            f"- 严重程度：{bug.get('severity')}",
            f"- 严重程度依据：{bug.get('severity_basis')}",
            f"- 优先级：{bug.get('priority')}",
            f"- 类型：{bug.get('type', '产品缺陷')}",
            f"- 证据类别：{bug.get('category', 'other')}",
            f"- 状态：{bug.get('status', 'open')}",
            f"- 环境：{bug.get('environment') or environment_line(run.get('environment', {}))}",
            f"- 关联：{'；'.join(lines(bug.get('related_ids'))) or '未记录'}",
            f"- reproducibility：{bug.get('reproducibility')}",
            f"- repro_attempts：{bug.get('repro_attempts')}",
            f"- first_failure_preserved：{str(bool(bug.get('first_failure_preserved'))).lower()}",
            f"- evidence_grade：{bug.get('evidence_grade')}", "",
            "### 前置条件", "", bullets(bug.get("preconditions")), "",
            "### 复现步骤", "", numbered(bug.get("steps")) or "未记录", "",
            "### 实际结果", "", str(bug.get("actual_result", "未记录")), "",
            "### 期望结果", "", str(bug.get("expected_result", "未记录")), "",
            "### 影响范围", "", str(bug.get("impact", "未记录")), "",
            "### 证据", "", bullets(paths), "",
            "### 初步分析", "", *analysis_lines, "",
            "### 临时规避与复测建议", "", str(bug.get("workaround", "无；修复后按关联用例复测。")), "",
        ])
    return "\n".join(rows)


def render_report(run: dict[str, Any]) -> str:
    coverage = coverage_snapshot(run)
    counts = coverage["case_status_counts"]
    acceptance_counts = coverage["acceptance_status_counts"]
    decision_map = {"go": "建议上线", "conditional_go": "有条件上线", "no_go": "不建议上线", "undetermined": "无法判断"}
    release = run.get("release_decision", {})
    bug_summary = [f"{item.get('id')}（{item.get('severity')}/{item.get('priority')}）：{item.get('title')}" for item in run.get("bugs", [])]
    candidate_summary = [f"{item.get('id')}（{item.get('status')}）：{item.get('title')}" for item in run.get("bug_candidates", [])]
    risk_summary = [f"{item.get('id')}（{item.get('priority')}）：{item.get('title')}" for item in run.get("risks", [])]
    mechanism_summary = [
        f"{item.get('id')}（{item.get('priority')}/{item.get('status')}）：{item.get('title')}"
        for item in run.get("risk_mechanisms", [])
    ]
    execution_rows = []
    for case in run.get("cases", []):
        execution_rows.append(
            f"- `{case.get('id')}` {case.get('title')}：**{case_status(run, str(case.get('id', '')))}**"
            + (f" — {latest_case_note(run, str(case.get('id', '')))}" if latest_case_note(run, str(case.get('id', ''))) else "")
        )
    blockers = [f"{item.get('id', 'BLOCKER')}：{item.get('reason')}；补齐：{'；'.join(lines(item.get('minimal_unblock_actions')))}" for item in run.get("blockers", [])]
    handoff = run.get("manual_handoff", {})
    manual_cases = [case for case in run.get("cases", []) if case.get("execution_mode") in {"manual", "hybrid"}]
    manual_summary = (
        [
            f"自动化不可用原因：{handoff.get('reason', '未记录')}",
            f"需人工执行用例：{len(manual_cases)} 个",
            f"交接状态：{handoff.get('status', 'pending')}",
            "操作指南：10-manual-test-guide.md",
        ]
        if handoff.get("required") else []
    )
    return "\n".join([
        f"# {run.get('target', {}).get('name', run['run_id'])} 测试报告", "",
        "## 执行摘要", "",
        f"- 环境：{environment_line(run.get('environment', {}))}",
        *screenshot_line(run), "",
        "## 覆盖情况", "",
        f"- 需求：{coverage['requirement_linked']}/{coverage['requirement_total']} 已关联用例",
        f"- P0 需求：{coverage['p0_requirement_linked']}/{coverage['p0_requirement_total']} 已关联用例",
        f"- 可观察界面项：{len(run.get('observed_surfaces', []))}",
        f"- 未验证范围：{unverified_line(run, counts)}", "",
        "## 执行结果", "",
        f"- 总用例：{coverage['case_total']}；通过：{counts.get('通过', 0)}；失败：{counts.get('失败', 0)}；待确认：{counts.get('待确认', 0)}；阻塞：{counts.get('阻塞', 0)}；未执行：{counts.get('未执行', 0)}；不适用：{counts.get('不适用', 0)}",
        *(execution_rows or ["- 本 profile 未维护独立用例；执行详情见 qa-run.json。"]), "",
        "## 缺陷", "", bullets(
            bug_summary + candidate_summary,
            "本轮执行未发现缺陷。" if run.get("executions") else "本轮尚未执行，无法判断是否存在产品缺陷。",
        ), "",
        "## 验收摘要", "",
        (
            f"- 总数：{coverage['acceptance_total']}；通过：{acceptance_counts.get('通过', 0)}；"
            f"未通过：{acceptance_counts.get('未通过', 0)}；阻塞：{acceptance_counts.get('阻塞', 0)}；"
            f"待验证：{acceptance_counts.get('待验证', 0)}；不适用：{acceptance_counts.get('不适用', 0)}"
        ),
        "- 详细决策项见 `04-acceptance-checklist.md`。", "",
        "## 风险机制", "", bullets(mechanism_summary), "",
        "## 其他风险", "", bullets(risk_summary), "",
        "## 发布结论", "",
        f"**{decision_map.get(str(release.get('decision')), '无法判断')}。** {release.get('rationale', '')}",
        bullets(release.get("conditions"), ""), "",
        "## 未验证", "", bullets(run.get("unverified")), "",
        "## 阻塞与后续动作", "", bullets(blockers), "",
        "## 人工交接", "", bullets(manual_summary), "",
        "## 环境恢复", "",
        f"- 写入授权：{str(bool(run.get('test_data', {}).get('writes_allowed', False))).lower()}",
        f"- 清理状态：{run.get('test_data', {}).get('cleanup', {}).get('status', 'not_required')}",
        f"- 未清理残留：{'；'.join(lines(run.get('test_data', {}).get('cleanup', {}).get('residuals'))) or '无'}", "",
    ])


def demote_headings(content: str, levels: int = 1) -> str:
    prefix = "#" * levels
    return "\n".join(
        f"{prefix}{line}" if line.startswith("#") else line
        for line in content.splitlines()
    )


def render_cases_markdown(run: dict[str, Any]) -> str:
    rows: list[str] = []
    if not run.get("cases"):
        return "本轮没有独立测试用例。\n"
    for case in run["cases"]:
        case_id = str(case.get("id", ""))
        rows.extend([
            f"### {case_id}：{case.get('title', '')}",
            "",
            f"- 模块：{case.get('module', '')}",
            f"- 优先级：{case.get('priority', '')}",
            f"- 类型：{case.get('type', '')}",
            f"- 状态：{case_status(run, case_id)}",
            f"- 关联需求：{'；'.join(lines(case.get('requirement_ids'))) or '无'}",
            f"- 风险机制：{'；'.join(lines(case.get('risk_mechanism_ids'))) or '无'}",
            "",
            "#### 前置条件",
            "",
            bullets(case.get("preconditions")),
            "",
            "#### 步骤",
            "",
            numbered(case.get("steps")) or "未记录",
            "",
            "#### 测试数据",
            "",
            str(case.get("test_data", "")),
            "",
            "#### 预期结果",
            "",
            bullets(case.get("expected_result")),
            "",
            "#### 实际结果与证据",
            "",
            latest_case_note(run, case_id) or "未执行或暂无证据。",
            "",
        ])
    return "\n".join(rows)


def render_markdown_bundle(run: dict[str, Any]) -> str:
    delivery = requested_delivery(run)
    requested_order = [
        str(value) for value in delivery.get("section_order", []) if str(value).strip()
    ] or ["测试报告", "详细用例", "Bug 单"]
    sections = {
        "report": demote_headings(render_report(run)),
        "cases": render_cases_markdown(run),
        "bugs": demote_headings(render_bugs(run)),
    }
    rendered: list[str] = [
        f"# {run.get('target', {}).get('name', run['run_id'])} QA 交付",
        "",
    ]
    used: set[str] = set()
    for title in requested_order:
        lowered = title.lower()
        if "用例" in title or "case" in lowered:
            key = "cases"
        elif "bug" in lowered or "缺陷" in title:
            key = "bugs"
        elif "报告" in title or "report" in lowered:
            key = "report"
        else:
            key = ""
        rendered.extend([f"## {title}", "", sections.get(key, "该自定义章节没有可投影的 canonical 内容。"), ""])
        if key:
            used.add(key)
    for key, title in (("report", "测试报告"), ("cases", "详细用例"), ("bugs", "Bug 单")):
        if key not in used:
            rendered.extend([f"## {title}", "", sections[key], ""])
    return "\n".join(rendered).rstrip() + "\n"


def write_markdown_bundle(path: Path, run: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_bundle(run), encoding="utf-8")


def render_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 qa-run.json 生成 QA 交付物")
    parser.add_argument("qa_run", type=Path)
    parser.add_argument("--out", type=Path, help="输出目录，默认 qa-run.json 所在目录")
    parser.add_argument("--profile", choices=sorted(PROFILE_FILES), help="覆盖 qa-run 中的 profile")
    parser.add_argument("--bundle", action="append", default=[], help="额外生成合并 Markdown 文件名")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.qa_run.expanduser().resolve()
    try:
        run = json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取 qa-run.json：{exc}", file=sys.stderr)
        return 2
    if args.profile:
        run["profile"] = args.profile
    run["coverage"] = coverage_snapshot(run)
    run["updated_at"] = datetime.now(timezone.utc).isoformat()
    findings = semantic_findings(run, source.parent)
    errors = gate_policy.blocking(findings)
    if errors:
        for item in errors:
            print(f"[BLOCK] {item['path']} - {item['message']}", file=sys.stderr)
        return 1

    source.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out = (args.out or source.parent).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    renderers = {
        "00-input-notes.md": lambda path: path.write_text(render_input_notes(run), encoding="utf-8"),
        "01-test-plan.md": lambda path: path.write_text(render_plan(run), encoding="utf-8"),
        "02-traceability.csv": lambda path: write_traceability(path, run),
        "03-test-cases.csv": lambda path: write_cases(path, run),
        "04-acceptance-checklist.md": lambda path: path.write_text(render_acceptance(run), encoding="utf-8"),
        "05-risks.md": lambda path: path.write_text(render_risks(run), encoding="utf-8"),
        "06-bugs.md": lambda path: path.write_text(render_bugs(run), encoding="utf-8"),
        "07-test-report.md": lambda path: path.write_text(render_report(run), encoding="utf-8"),
        "08-device-matrix.json": lambda path: render_json(path, {"schema_version": 1, "runs": run.get("devices", {}).get("planned_runs", [])}),
        "09-automation-summary.json": lambda path: render_json(path, {"schema_version": 1, "runs": run.get("devices", {}).get("automation_runs", [])}),
        "10-manual-test-guide.md": lambda path: path.write_text(render_manual_guide(run), encoding="utf-8"),
    }
    generated = []
    for filename in sorted(PROFILE_FILES[run["profile"]]):
        renderers[filename](out / filename)
        generated.append(filename)
    if run.get("manual_handoff", {}).get("required"):
        renderers["10-manual-test-guide.md"](out / "10-manual-test-guide.md")
        generated.append("10-manual-test-guide.md")
        generated.extend(render_manual_bundle(out, run))
    if any(item.get("execution_method") == "manual" for item in run.get("executions", [])):
        for filename in ("06-bugs.md", "07-test-report.md"):
            if filename not in generated:
                renderers[filename](out / filename)
                generated.append(filename)
    requested = requested_delivery(run)
    bundle_names = list(args.bundle)
    if requested.get("artifact_required"):
        bundle_names.extend(
            str(item.get("filename"))
            for item in requested.get("artifacts", [])
            if item.get("format") == "markdown" and str(item.get("filename", "")).lower().endswith(".md")
        )
    for filename in dict.fromkeys(bundle_names):
        candidate = Path(filename)
        if candidate.name != filename or candidate.suffix.lower() != ".md":
            print(f"非法 Markdown bundle 文件名：{filename}", file=sys.stderr)
            return 2
        write_markdown_bundle(out / candidate, run)
        generated.append(filename)
    test_data = run.get("test_data", {})
    if test_data.get("writes_allowed") or test_data.get("created_records") or test_data.get("cleanup", {}).get("required"):
        manifest = dict(test_data)
        manifest["schema_version"] = 1
        manifest["run_id"] = run["run_id"]
        manifest["environment_restored"] = test_data.get("cleanup", {}).get("status") in {"completed", "not_required"}
        render_json(out / "test-data-manifest.json", manifest)
        generated.append("test-data-manifest.json")
    print(json.dumps({"ok": True, "profile": run["profile"], "qa_run": str(source), "out": str(out), "generated": generated}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
