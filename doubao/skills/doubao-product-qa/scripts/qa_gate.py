#!/usr/bin/env python3
"""豆包 QA 单一阶段门禁：结构、语义、阶段完成度与派生产物。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from qa_run_common import (
    acceptance_status,
    canonical_fingerprint,
    case_status,
    requested_delivery,
    resolve_local_locator,
    semantic_findings,
)


STAGES = ("baseline", "design", "execution", "change", "release")
REQUIRED_PHASES = {
    "smoke": ("baseline", "execution"),
    "plan": ("baseline", "design"),
    "execution": ("baseline", "design", "execution"),
    "full": ("baseline", "design", "execution"),
    "mobile": ("baseline", "design", "execution"),
    "hotfix": ("baseline", "design", "execution"),
    "bug": ("baseline",),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 QA 阶段门禁；OPEN=必须修复，DISCLOSE=可交付但需披露 warning"
    )
    parser.add_argument("qa_run", type=Path)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--render", action="store_true", help="生成并校验本地派生产物")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args()


def stage_findings(
    run: dict[str, Any],
    stage: str,
    artifact_root: Path | None = None,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def add(level: str, path: str, message: str, fix: str) -> None:
        findings.append({"level": level, "path": path, "message": message, "fix": fix})

    profile = str(run.get("profile", ""))
    if stage == "baseline":
        if not run.get("input", {}).get("sources"):
            add("error", "input.sources", "没有输入来源", "登记文件/URL/页面/执行记录及其版本")
        artifacts = run.get("input", {}).get("artifacts", [])
        if not artifacts:
            add("error", "input.artifacts", "没有逐项建立输入材料清单", "为每个材料建立 SRC-* 并记录读取状态与完整性")
        elif not any(item.get("access_status") == "read" for item in artifacts):
            add("error", "input.artifacts", "没有任何已实际读取的输入", "获取权限或提供可读副本后再建立需求基线")
        if profile != "bug" and not run.get("requirements"):
            add("error", "requirements", "尚未建立原子需求基线", "创建 REQ-* 并写明 source 与 risk")

    if stage == "design":
        if profile != "bug" and not run.get("cases"):
            add("error", "cases", "没有可执行用例", "为需求和风险机制创建 TC-*")
        if run.get("requirements") and not run.get("risk_mechanisms"):
            add("error", "risk_mechanisms", "尚未建立风险机制", "创建 RM-*，填写 failure_mode、impact 与 oracle")
        linked_requirements = {
            str(req_id)
            for case in run.get("cases", [])
            for req_id in case.get("requirement_ids", [])
        }
        for requirement in run.get("requirements", []):
            if requirement.get("risk") in {"P0", "P1"} and requirement.get("id") not in linked_requirements:
                add(
                    "error",
                    f"requirements[{requirement.get('id')}]",
                    "P0/P1 需求没有关联用例",
                    "创建独立用例并双向登记 requirement_ids",
                )
        for mechanism in run.get("risk_mechanisms", []):
            if mechanism.get("priority") in {"P0", "P1"} and mechanism.get("status") == "identified":
                add(
                    "error",
                    f"risk_mechanisms[{mechanism.get('id')}]",
                    "P0/P1 风险机制仍停留在 identified",
                    "补充独立用例、具体数据与 oracle，并改为 designed",
                )
        if profile in {"full", "hotfix", "mobile"} and run.get("cases") and not run.get("acceptance_checks"):
            add(
                "error",
                "acceptance_checks",
                "完整提测/热修复尚未建立决策级验收清单",
                "从 P0/P1 风险与发布门提炼 AC-*，关联用例但不要逐行复制",
            )

    if stage == "execution":
        if not run.get("executions"):
            add("error", "executions", "没有执行记录", "运行用例或切换 manual_handoff 后导入人工结果")
        for execution in run.get("executions", []):
            if execution.get("status") == "failed":
                if not execution.get("actual_result") and not execution.get("summary"):
                    add(
                        "error",
                        f"executions[{execution.get('id')}].actual_result",
                        "失败执行缺少真实观察",
                        "记录实际结果、时间、环境与复现上下文",
                    )
                if not execution.get("evidence_ids"):
                    add(
                        "warning",
                        f"executions[{execution.get('id')}].evidence_ids",
                        "失败执行没有关联证据",
                        "补充请求响应、日志、trace、结构化观察或截图策略允许的截图",
                    )

    if stage == "release":
        contract = run.get("request_contract")
        if not isinstance(contract, dict):
            add(
                "error",
                "request_contract",
                "缺少用户请求契约，无法证明交付载体、范围和证据政策符合请求",
                "FIX: 使用 qa_flow.py bootstrap <qa-run> --request <摘要> --target <名称> 建立 request_contract",
            )
            contract = {}
        receipts = {
            str(item.get("stage")): item
            for item in run.get("phase_receipts", [])
            if item.get("revision") == run.get("revision")
            and item.get("state") in {"CLOSED", "DISCLOSE"}
            and item.get("source_fingerprint") == canonical_fingerprint(run)
        }
        for required_stage in REQUIRED_PHASES.get(profile, ("baseline", "design", "execution")):
            if required_stage not in receipts:
                add(
                    "error",
                    f"phase_receipts.{required_stage}",
                    f"当前 revision 缺少 {required_stage} 阶段回执",
                    f"运行 qa_flow.py complete <qa-run> --stage {required_stage}",
                )
        decision = run.get("release_decision", {})
        if not decision.get("rationale"):
            add("error", "release_decision.rationale", "发布判断缺少依据", "引用覆盖、执行、Bug 和残余风险")
        outputs = run.get("delivery_manifest", {}).get("outputs", [])
        delivery = requested_delivery(run)
        artifact_required = delivery.get("artifact_required") is True
        requested_names = [str(value) for value in delivery.get("filenames", []) if str(value)]
        if artifact_required and not outputs:
            add(
                "error",
                "delivery_manifest.outputs",
                "请求要求实体交付，但交付清单为空",
                "使用 qa_flow.py publish 生成或登记真实产物；不得只在对话中粘贴内容",
            )
        validated_names = {
            str(output.get("filename") or Path(str(output.get("locator", ""))).name)
            for output in outputs
            if output.get("status") == "validated"
            and output.get("validated") is True
            and output.get("source_revision") == run.get("revision")
        }
        for filename in requested_names:
            if filename not in validated_names:
                add(
                    "error",
                    f"request_contract.delivery.filenames[{filename}]",
                    "请求中的文件没有匹配当前 revision 的 validated 交付回执",
                    "生成并回读该文件，再通过 qa_flow.py publish 登记",
                )
        for output in outputs:
            if output.get("status") in {"planned", "created", "stale"}:
                add(
                    "error",
                    f"delivery_manifest[{output.get('purpose', output.get('carrier'))}]",
                    f"外部产物状态仍为 {output.get('status')}",
                    "更新原对象并回读；成功后标 validated，失败则标 failed/local_fallback",
                )
            if output.get("status") in {"failed", "local_fallback"}:
                add(
                    "warning",
                    f"delivery_manifest[{output.get('purpose', output.get('carrier'))}]",
                    f"飞书交付降级为 {output.get('status')}",
                    "向用户披露未创建的对象与本地替代路径",
                )
        markdown_names = [
            str(item.get("filename"))
            for item in delivery.get("artifacts", [])
            if item.get("format") == "markdown"
        ]
        for markdown_name in markdown_names:
            matching = next(
                (
                    item for item in outputs
                    if item.get("status") == "validated"
                    and str(item.get("filename") or Path(str(item.get("locator", ""))).name)
                    == markdown_name
                ),
                None,
            )
            locator = str(matching.get("locator", "")) if matching else ""
            resolved = resolve_local_locator(locator, artifact_root)
            # semantic_findings 已验证存在性；此处只检查 Markdown 章节及顺序。
            if resolved:
                try:
                    content = resolved.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeDecodeError):
                    content = ""
                required_sections = [
                    str(value) for value in delivery.get("required_sections", []) if str(value)
                ]
                for section in required_sections:
                    if section not in content:
                        add(
                            "error",
                            f"delivery[{markdown_name}].sections",
                            f"Markdown 缺少必需章节：{section}",
                            "重新生成合并 Markdown，并保留请求指定的章节",
                        )
                ordered_sections = [
                    str(value) for value in delivery.get("section_order", []) if str(value)
                ]
                positions = [content.find(section) for section in ordered_sections]
                if any(position < 0 for position in positions) or positions != sorted(positions):
                    add(
                        "error",
                        f"delivery[{markdown_name}].section_order",
                        "Markdown 章节顺序不符合 request_contract",
                        "按 request_contract.section_order 重新排列后发布",
                    )
        if run.get("cases") and not any(
            case_status(run, str(case.get("id", ""))) != "未执行"
            for case in run.get("cases", [])
        ) and decision.get("decision") != "undetermined":
            add(
                "error",
                "release_decision.decision",
                "全部用例未执行却给出终审",
                "改为 undetermined，并列出获取决定性证据的最小动作",
            )
        acceptance_counts: dict[str, int] = {}
        for check in run.get("acceptance_checks", []):
            status = acceptance_status(run, check)
            acceptance_counts[status] = acceptance_counts.get(status, 0) + 1
        if sum(acceptance_counts.values()) != len(run.get("acceptance_checks", [])):
            add(
                "error",
                "acceptance_checks",
                "验收状态计数与总数不一致",
                "从关联 executions 重新派生验收状态并复算",
            )

    return findings


def render_and_validate(path: Path, profile: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    findings: list[dict[str, str]] = []
    scripts = Path(__file__).parent
    renderer = subprocess.run(
        [sys.executable, str(scripts / "render_qa_artifacts.py"), str(path), "--out", str(path.parent)],
        text=True,
        capture_output=True,
        check=False,
    )
    if renderer.returncode != 0:
        findings.append({
            "level": "error",
            "path": "render",
            "message": renderer.stderr.strip() or renderer.stdout.strip() or "renderer 失败",
            "fix": "按报错修复 qa-run.json 后重跑同一条 qa_gate 命令",
        })
        return findings, {}
    validator = subprocess.run(
        [
            sys.executable,
            str(scripts / "validate_qa_artifacts.py"),
            str(path.parent),
            "--profile",
            profile,
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(validator.stdout)
    except json.JSONDecodeError:
        result = {}
    if validator.returncode != 0:
        findings.append({
            "level": "error",
            "path": "artifacts",
            "message": validator.stderr.strip() or validator.stdout.strip() or "派生产物校验失败",
            "fix": "修复 canonical 数据或 renderer 后重跑；不要手改派生文件",
        })
    return findings, {"render": renderer.stdout.strip(), "validate": result}


def main() -> int:
    args = parse_args()
    path = args.qa_run.expanduser().resolve()
    try:
        run = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"GATE_STATE=OPEN\nERRORS=1\n① {exc}\nFIX: 提供合法 qa-run.json")
        return 1

    findings = semantic_findings(run, path.parent)
    for item in findings:
        item.setdefault("fix", "按字段错误修复 qa-run.json 后重跑同一条命令")
    findings.extend(stage_findings(run, args.stage, path.parent))
    render_result: dict[str, Any] = {}
    if args.render and not any(item["level"] == "error" for item in findings):
        extra, render_result = render_and_validate(path, str(run.get("profile", "full")))
        findings.extend(extra)

    errors = [item for item in findings if item["level"] == "error"]
    warnings = [item for item in findings if item["level"] == "warning"]
    state = "OPEN" if errors else ("DISCLOSE" if warnings else "CLOSED")
    result = {
        "gate_state": state,
        "stage": args.stage,
        "qa_run": str(path),
        "revision": run.get("revision"),
        "errors": len(errors),
        "warnings": len(warnings),
        "findings": findings,
        "artifacts": render_result,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"GATE_STATE={state}")
        print(f"STAGE={args.stage}")
        print(f"REVISION={run.get('revision')}")
        print(f"ERRORS={len(errors)}")
        print(f"WARNINGS={len(warnings)}")
        for number, item in enumerate(findings, start=1):
            print(f"{number}. [{item['level'].upper()}] {item['path']} - {item['message']}")
            print(f"FIX: {item['fix']}")
    return 1 if errors else (3 if warnings else 0)


if __name__ == "__main__":
    sys.exit(main())
