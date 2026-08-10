#!/usr/bin/env python3
"""豆包 QA 阶段控制器：请求契约、上下文卡、体裁卡与阶段门禁。

交付与上屏不在这里，走 qa_deliver.py（唯一交付口）。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gate_policy
import report_shape
from qa_gate import REQUIRED_PHASES
from qa_run_common import DELIVERY_FORMATS, canonical_fingerprint, coverage_snapshot


STAGES = ("baseline", "design", "execution", "change")
OUTPUT_SUFFIX_FORMATS = {
    ".md": "markdown",
    ".csv": "csv",
    ".json": "json",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
    ".pdf": "pdf",
}
BOOTSTRAP_MODES = {
    "plan": ("plan", "plan", "non_ui_validation"),
    "review": ("full", "execution_review", "non_ui_validation"),
    "bug": ("bug", "bug", "non_ui_validation"),
    "hotfix": ("hotfix", "hotfix", "non_ui_validation"),
    "web": ("full", "web_execution", "repeatable_ui"),
    "api": ("full", "api_execution", "non_ui_validation"),
}
LEDGER_OBJECTS = {
    "run": lambda run: [str(run.get("run_id", "run"))],
    "requirement": lambda run: [str(item.get("id", "")) for item in run.get("requirements", [])],
    "risk_mechanism": lambda run: [str(item.get("id", "")) for item in run.get("risk_mechanisms", [])],
    "case": lambda run: [str(item.get("id", "")) for item in run.get("cases", [])],
    "acceptance": lambda run: [str(item.get("id", "")) for item in run.get("acceptance_checks", [])],
    "execution": lambda run: [str(item.get("id", "")) for item in run.get("executions", [])],
    "evidence": lambda run: [str(item.get("id", "")) for item in run.get("evidence", [])],
    "bug": lambda run: [str(item.get("id", "")) for item in run.get("bugs", [])],
    "delivery": lambda run: [
        str(item.get("filename", "")) for item in run.get("delivery_manifest", {}).get("outputs", [])
    ],
}


def emit_footer(state: str, *, next_command: str = "", delivery_lock: str = "CLOSED") -> None:
    """把关键状态印在每次控制器调用的必经输出末尾。"""
    print(f"QA_FLOW_STATE={state}")
    print("SKILL_LOADED=doubao-qa")
    print(f"DELIVERY_LOCK={delivery_lock}")
    if next_command:
        print(f"NEXT={next_command}")


def infer_mode(request: str, allow_new_execution: bool) -> str:
    text = request.lower()
    if any(token in text for token in ("热修复", "hotfix", "修复回归")):
        return "hotfix"
    if allow_new_execution and any(token in text for token in ("接口", "api", "openapi", "swagger")):
        return "api"
    if allow_new_execution and any(token in text for token in ("网页", "页面", "web", "浏览器", "url")):
        return "web"
    if allow_new_execution:
        return "review"
    evidence_tokens = (
        "执行记录", "测试记录", "日志", "回执", "遥测", "复核", "收口",
        "go/no-go", "go no-go", "是否上线", "是否试点", "发布结论",
    )
    if any(token in text for token in evidence_tokens):
        return "review"
    if any(token in text for token in ("bug 单", "bug单", "缺陷复核", "bug 复核")):
        return "bug"
    return "plan"


def infer_target_type(source: str) -> str:
    lowered = source.lower()
    if lowered.startswith(("http://", "https://")):
        return "url"
    suffix = Path(source).suffix.lower()
    if suffix in {".md", ".doc", ".docx", ".pdf", ".rtf", ".txt"}:
        return "document"
    if suffix in {".csv", ".xls", ".xlsx"}:
        return "spreadsheet"
    if suffix in {".yaml", ".yml", ".json"}:
        return "api_or_data"
    if source:
        return "attachment_or_directory"
    return "unknown"


def output_format(value: str) -> tuple[str, str]:
    explicit, separator, filename = value.partition(":")
    if separator and explicit in DELIVERY_FORMATS - {"inline_markdown", "multi"} and filename:
        return explicit, filename
    inferred = OUTPUT_SUFFIX_FORMATS.get(Path(value).suffix.lower())
    if not inferred:
        legal = ", ".join(sorted(OUTPUT_SUFFIX_FORMATS))
        raise ValueError(
            f"无法从 --output 推断格式：{value}。FIX: 使用带扩展名的文件（{legal}），"
            "或使用 FORMAT:FILENAME，例如 xlsx:测试用例.xlsx"
        )
    return inferred, value


def requested_delivery_formats(request: str) -> list[str]:
    """识别用户明确点名的载体；泛称“文档/表格/汇报”留给默认在线载体路由。"""
    text = request.lower()
    explicit_rules = (
        (("markdown", ".md", " md 文件", "md格式", "md 格式"), "markdown"),
        ((".xlsx", "xlsx", "excel"), "xlsx"),
        ((".docx", "docx", "word"), "docx"),
        ((".pptx", "pptx"), "pptx"),
        ((".pdf", "pdf"), "pdf"),
        ((".csv", "csv"), "csv"),
        ((".json", "json 文件", "json格式", "json 格式"), "json"),
        (("豆包文档", "飞书文档"), "lark_doc"),
        (("豆包表格", "飞书表格"), "lark_sheets"),
        (("豆包多维表格", "飞书多维表格", "lark base"), "lark_base"),
        (("豆包 ppt", "豆包ppt", "飞书 ppt", "飞书ppt", "飞书演示"), "lark_ppt"),
    )
    matches: list[tuple[int, int, str]] = []
    for rule_index, (tokens, output) in enumerate(explicit_rules):
        positions = [text.find(token) for token in tokens if token in text]
        if positions:
            matches.append((min(positions), rule_index, output))
    formats: list[str] = []
    for _, _, output in sorted(matches):
        if output not in formats:
            formats.append(output)
    return formats


def default_delivery_formats(request: str) -> list[str]:
    """用户未指定载体时，按 QA 交付语义路由到豆包在线文档、表格或 PPT。"""
    explicit = requested_delivery_formats(request)
    if explicit:
        return explicit

    text = request.lower()
    presentation_intent = any(token in text for token in (
        "ppt", "演示文稿", "幻灯片", "汇报材料", "汇报演示", "评审会材料",
        "评审会议", "go/no-go 会议", "go no-go 会议",
    ))
    sheet_intent = any(token in text for token in (
        "测试用例", "用例设计", "用例表", "需求追踪", "追踪矩阵", "覆盖矩阵",
        "设备矩阵", "兼容矩阵", "执行清单", "验收清单", "测试数据表", "表格",
    ))
    document_intent = any(token in text for token in (
        "测试方案", "测试计划", "测试范围", "测试报告", "复核报告", "收口报告",
        "qa 报告", "qa报告", "复核", "收口", "bug 单", "bug单", "缺陷报告",
        "发布结论", "上线结论", "风险分析", "总结",
    ))

    if presentation_intent:
        return ["lark_ppt"]
    if sheet_intent and document_intent:
        return ["lark_doc", "lark_sheets"]
    if sheet_intent:
        return ["lark_sheets"]
    return ["lark_doc"]


def default_output_title(target: str, output_format: str) -> str:
    safe_name = re.sub(r"[/\\:\x00-\x1f]+", "-", target).strip(" .-") or "QA"
    suffix = {
        "markdown": "QA收口报告.md",
        "csv": "QA测试用例.csv",
        "json": "QA结构化结果.json",
        "docx": "QA测试方案与报告.docx",
        "xlsx": "QA测试用例与追踪.xlsx",
        "pptx": "QA评审汇报.pptx",
        "pdf": "QA测试方案与报告.pdf",
        "lark_doc": "QA测试方案与报告",
        "lark_sheets": "QA测试用例与追踪",
        "lark_base": "QA协作台账",
        "lark_ppt": "QA评审汇报",
    }.get(output_format, "QA交付物")
    return f"{safe_name}-{suffix}"


def add_bootstrap_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("out", type=Path)
    parser.add_argument("--request", "--request-summary", dest="request", required=True)
    parser.add_argument("--target", "--target-name", dest="target", required=True)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--output", action="append", default=[])
    parser.add_argument("--mode", choices=("auto", *BOOTSTRAP_MODES), default="auto")
    parser.add_argument("--execute", action="store_true", help="用户已授权本轮新执行")
    parser.add_argument("--run-id")
    parser.add_argument("--target-type")


def next_change_id(ledger: list[dict[str, Any]]) -> str:
    numbers = []
    for item in ledger:
        value = str(item.get("id", ""))
        if value.startswith("CHG-") and value[4:].isdigit():
            numbers.append(int(value[4:]))
    return f"CHG-{max(numbers, default=0) + 1:03d}"


def ledger_is_consistent(run: dict[str, Any]) -> bool:
    ledger = run.get("change_ledger")
    if not isinstance(ledger, list) or not ledger:
        return False
    last_counts: dict[str, int] = {}
    last_revision = 0
    seen: set[str] = set()
    for item in ledger:
        change_id = str(item.get("id", ""))
        revision = item.get("revision")
        object_type = str(item.get("object_type", ""))
        before = item.get("before_count")
        after = item.get("after_count")
        delta = item.get("delta_count")
        if (
            not re.fullmatch(r"CHG-\d{3,}", change_id)
            or change_id in seen
            or not isinstance(revision, int)
            or revision < last_revision
            or object_type not in LEDGER_OBJECTS
            or not isinstance(before, int)
            or not isinstance(after, int)
            or before < 0
            or after < 0
            or not isinstance(delta, int)
            or after - before != delta
            or before != last_counts.get(object_type, 0)
        ):
            return False
        seen.add(change_id)
        last_revision = revision
        last_counts[object_type] = after
    if last_revision != run.get("revision"):
        return False
    for object_type, getter in LEDGER_OBJECTS.items():
        count = len([value for value in getter(run) if value])
        if count and last_counts.get(object_type) != count:
            return False
    return True


def rebuild_ledger(run: dict[str, Any], revision: int) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = []
    for object_type, getter in LEDGER_OBJECTS.items():
        object_ids = [value for value in getter(run) if value]
        if not object_ids:
            continue
        ledger.append({
            "id": f"CHG-{len(ledger) + 1:03d}",
            "revision": revision,
            "action": "ADD",
            "object_type": object_type,
            "added_ids": object_ids,
            "removed_ids": [],
            "modified_ids": [],
            "before_count": 0,
            "after_count": len(object_ids),
            "delta_count": len(object_ids),
            "source": "qa_flow.py normalize",
            "summary": "根据当前 canonical 重建机械计数台账",
        })
    return ledger


def normalize_mechanical_fields(run: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """只修答案唯一的派生字段；不补写业务事实、证据或测试结论。"""
    working = json.loads(json.dumps(run, ensure_ascii=False))
    changes: list[str] = []

    for requirement in working.get("requirements", []):
        if not requirement.get("summary"):
            for alias in ("title", "name", "description", "requirement"):
                if requirement.get(alias):
                    requirement["summary"] = requirement[alias]
                    changes.append("requirements.summary<-alias")
                    break
        if requirement.get("risk") in {"P0", "P1"} and not isinstance(requirement.get("behavior"), dict):
            aliases = {
                "actor": ("actor", "role"),
                "precondition": ("precondition", "preconditions"),
                "trigger": ("trigger", "action"),
                "rule": ("rule", "business_rule"),
                "state_change": ("state_change", "status_change"),
                "observable_result": ("observable_result", "expected_result"),
                "failure_behavior": ("failure_behavior", "failure_result"),
            }
            behavior = {}
            for field, candidates in aliases.items():
                value = next((requirement.get(name) for name in candidates if requirement.get(name)), None)
                if value:
                    behavior[field] = value
            if len(behavior) == len(aliases):
                requirement["behavior"] = behavior
                changes.append("requirements.behavior<-flat-fields")

    status_aliases = {
        "pending": "open",
        "pending_confirmation": "open",
        "待确认": "open",
        "confirmed": "resolved",
        "已确认": "resolved",
    }
    for question in working.get("open_questions", []):
        status = str(question.get("status", ""))
        if status in status_aliases:
            question["status"] = status_aliases[status]
            changes.append("open_questions.status")

    for case in working.get("cases", []):
        if "status" in case:
            case.pop("status", None)
            changes.append("cases.status removed")
    for check in working.get("acceptance_checks", []):
        if "status" in check:
            check.pop("status", None)
            changes.append("acceptance_checks.status removed")

    mechanism_index = {
        str(item.get("id", "")): item
        for item in working.get("risk_mechanisms", [])
        if item.get("id")
    }
    for case in working.get("cases", []):
        case_id = str(case.get("id", ""))
        for mechanism_id in case.get("risk_mechanism_ids", []):
            mechanism = mechanism_index.get(str(mechanism_id))
            if mechanism is None or not case_id:
                continue
            case_ids = [str(value) for value in mechanism.get("case_ids", [])]
            if case_id not in case_ids:
                mechanism["case_ids"] = case_ids + [case_id]
                changes.append("risk_mechanisms.case_ids synchronized")

    input_info = working.get("input", {})
    if isinstance(input_info, dict) and not input_info.get("sources"):
        locators = [
            str(item.get("locator", ""))
            for item in input_info.get("artifacts", [])
            if item.get("locator")
        ]
        if locators:
            input_info["sources"] = list(dict.fromkeys(locators))
            changes.append("input.sources<-artifacts")

    if not changes:
        expected_coverage = coverage_snapshot(working)
        if working.get("coverage") != expected_coverage:
            working["coverage"] = expected_coverage
            changes.append("coverage recomputed")
        manifest = working.get("delivery_manifest")
        if isinstance(manifest, dict) and manifest.get("source_revision") != working.get("revision"):
            changes.append("delivery_manifest.source_revision")

    if not changes:
        return run, []

    previous_revision = int(working.get("revision", 1))
    new_revision = previous_revision + 1
    working["revision"] = new_revision
    working["coverage"] = coverage_snapshot(working)
    working.setdefault("delivery_manifest", {})["source_revision"] = new_revision
    if ledger_is_consistent(run):
        ledger = working.setdefault("change_ledger", [])
        ledger.append({
            "id": next_change_id(ledger),
            "revision": new_revision,
            "action": "MODIFY",
            "object_type": "run",
            "added_ids": [],
            "removed_ids": [],
            "modified_ids": [str(working.get("run_id", "run"))],
            "before_count": 1,
            "after_count": 1,
            "delta_count": 0,
            "source": "qa_flow.py normalize",
            "summary": "自动同步答案唯一的派生字段",
        })
    else:
        working["change_ledger"] = rebuild_ledger(working, new_revision)
        changes.append("change_ledger rebuilt")
    return working, list(dict.fromkeys(changes))


def normalize_and_persist(path: Path) -> tuple[Path, dict[str, Any], list[str]]:
    resolved, run = load_run(path)
    normalized, changes = normalize_mechanical_fields(run)
    if changes:
        atomic_write(resolved, normalized)
    return resolved, normalized, changes


def add_start_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("out", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--test-intent", required=True)
    parser.add_argument("--target-name", required=True)
    parser.add_argument("--target-type", default="unknown")
    parser.add_argument("--target-source", default="")
    parser.add_argument("--request-summary", required=True)
    parser.add_argument("--task-mode", required=True)
    parser.add_argument("--delivery-format", required=True)
    parser.add_argument("--delivery-carrier")
    parser.add_argument("--output-file", action="append", default=[])
    parser.add_argument("--output-spec", action="append", default=[])
    parser.add_argument("--required-section", action="append", default=[])
    parser.add_argument("--section-order", action="append", default=[])
    parser.add_argument("--scope-source", action="append", default=[])
    parser.add_argument("--exclude-source", action="append", default=[])
    parser.add_argument("--scope-round", action="append", default=[])
    parser.add_argument("--exclude-round", action="append", default=[])
    parser.add_argument("--allow-new-execution", action="store_true")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="管理 qa-run 的受控阶段与最终交付")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help="推荐入口：只接收用户语义，自动选择合法 profile、intent、mode 与交付格式",
    )
    add_bootstrap_args(bootstrap)

    start = subparsers.add_parser("start", help="从用户请求创建带 request_contract 的 qa-run")
    add_start_args(start)

    status = subparsers.add_parser("status", help="显示可续跑上下文卡")
    status.add_argument("qa_run", type=Path)

    anchor = subparsers.add_parser("anchor", help="阶段开始前显示上下文卡")
    anchor.add_argument("qa_run", type=Path)
    anchor.add_argument("--stage", choices=("baseline", "design", "execution", "change", "release"), required=True)

    complete = subparsers.add_parser("complete", help="运行门禁并写入不可伪造的阶段回执")
    complete.add_argument("qa_run", type=Path)
    complete.add_argument("--stage", choices=STAGES, required=True)

    normalize = subparsers.add_parser("normalize", help="自动修复答案唯一的派生字段，不补写业务事实")
    normalize.add_argument("qa_run", type=Path)

    publish = subparsers.add_parser("publish", help="[从属] 生成/校验 Markdown 产物；交付与上屏请用 qa_deliver.py")
    publish.add_argument("qa_run", type=Path)
    publish.add_argument("--locator", action="append", default=[])
    publish.add_argument("--readback-receipt", action="append", default=[])

    inspect_web = subparsers.add_parser("inspect-web", help="复用项目上下文并执行 Web 工程勘察")
    inspect_web.add_argument("qa_run", type=Path)
    inspect_web.add_argument("--project", type=Path, required=True)
    return parser.parse_args()


def load_run(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = path.expanduser().resolve()
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 qa-run.json：{exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("qa-run.json 根节点必须是对象")
    return resolved, payload


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def current_receipts(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fingerprint = canonical_fingerprint(run)
    return {
        str(item.get("stage")): item
        for item in run.get("phase_receipts", [])
        if item.get("revision") == run.get("revision")
        and item.get("source_fingerprint") == fingerprint
        and item.get("state") in {"CLOSED", "DISCLOSE"}
    }


def context_card(path: Path, run: dict[str, Any], stage: str | None = None) -> dict[str, Any]:
    contract = run.get("request_contract", {})
    delivery = contract.get("delivery", {}) if isinstance(contract, dict) else {}
    receipts = current_receipts(run)
    required = list(REQUIRED_PHASES.get(str(run.get("profile")), ("baseline", "design", "execution")))
    unresolved = {
        "open_questions": sum(item.get("status") == "open" for item in run.get("open_questions", [])),
        "pending_confirmation": sum(
            item.get("status") == "pending_confirmation" for item in run.get("executions", [])
        ),
        "blockers": len(run.get("blockers", [])),
        "bug_candidates": len(run.get("bug_candidates", [])),
    }
    return {
        "qa_run": str(path),
        "run_id": run.get("run_id"),
        "revision": run.get("revision"),
        "profile": run.get("profile"),
        "requested_stage": stage,
        "task_mode": contract.get("task_mode") if isinstance(contract, dict) else None,
        "request_hash": contract.get("request_hash") if isinstance(contract, dict) else None,
        "scope": contract.get("scope") if isinstance(contract, dict) else None,
        "delivery": delivery,
        "selected_path": run.get("selected_path"),
        "known_runtime": {
            key: run.get("environment", {}).get(key)
            for key in ("project_path", "start_command", "url", "port", "login_state")
            if run.get("environment", {}).get(key) not in (None, "")
        },
        "required_pre_publish_receipts": required,
        "valid_receipts": sorted(receipts),
        "missing_receipts": [name for name in required if name not in receipts],
        "unresolved": unresolved,
    }


def start_command(args: argparse.Namespace) -> int:
    script = Path(__file__).with_name("init_qa_run.py")
    command = [
        sys.executable,
        str(script),
        str(args.out),
        "--run-id", args.run_id,
        "--profile", args.profile,
        "--test-intent", args.test_intent,
        "--target-name", args.target_name,
        "--target-type", args.target_type,
        "--target-source", args.target_source,
        "--request-summary", args.request_summary,
        "--task-mode", args.task_mode,
        "--delivery-format", args.delivery_format,
    ]
    if args.delivery_carrier:
        command.extend(["--delivery-carrier", args.delivery_carrier])
    for option, values in (
        ("--output-file", args.output_file),
        ("--output-spec", args.output_spec),
        ("--required-section", args.required_section),
        ("--section-order", args.section_order),
        ("--scope-source", args.scope_source),
        ("--exclude-source", args.exclude_source),
        ("--scope-round", args.scope_round),
        ("--exclude-round", args.exclude_round),
    ):
        for value in values:
            command.extend([option, value])
    if args.allow_new_execution:
        command.append("--allow-new-execution")
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        emit_footer(
            "BLOCKED",
            next_command="按上方 FIX 修正后重跑同一条 qa_flow.py 命令",
        )
        return result.returncode
    path, run = load_run(args.out)
    print(json.dumps({"state": "STARTED", "context_card": context_card(path, run)}, ensure_ascii=False, indent=2))
    emit_footer(
        "STARTED",
        next_command=f"读取用户允许的输入后运行 qa_flow.py anchor {path} --stage baseline",
    )
    return 0


def bootstrap_command(args: argparse.Namespace) -> int:
    path = args.out.expanduser().resolve()
    normalized_request = " ".join(args.request.split())
    request_hash = f"sha256:{hashlib.sha256(normalized_request.encode('utf-8')).hexdigest()}"
    if path.exists():
        try:
            _, existing = load_run(path)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            emit_footer("BLOCKED", next_command=f"修复或更换 qa-run 路径：{path}")
            return 2
        contract = existing.get("request_contract", {})
        if (
            contract.get("request_hash") == request_hash
            and existing.get("target", {}).get("name") == args.target
        ):
            print(json.dumps({
                "state": "STARTED",
                "reused": True,
                "context_card": context_card(path, existing),
            }, ensure_ascii=False, indent=2))
            emit_footer(
                "STARTED",
                next_command=f"继续当前任务：qa_flow.py status {path}",
            )
            return 0
        print(json.dumps({
            "state": "BLOCKED",
            "error": "现有 qa-run 属于不同请求，拒绝覆盖。",
            "fix": f"为新请求使用新的 qa-run 路径；现有路径：{path}",
        }, ensure_ascii=False, indent=2))
        emit_footer("BLOCKED", next_command="更换 qa-results/<feature>/qa-run.json 后重跑")
        return 2

    mode = infer_mode(normalized_request, args.execute) if args.mode == "auto" else args.mode
    profile, task_mode, test_intent = BOOTSTRAP_MODES[mode]
    source = " | ".join(dict.fromkeys(args.source))
    parsed_outputs: list[tuple[str, str]] = []
    try:
        parsed_outputs = [output_format(value) for value in args.output]
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        emit_footer("BLOCKED", next_command="修正 --output 后重跑同一条 bootstrap 命令")
        return 2
    if parsed_outputs:
        formats = {item[0] for item in parsed_outputs}
        delivery_format = next(iter(formats)) if len(formats) == 1 else "multi"
        output_specs = (
            [f"{item[0]}:{item[1]}" for item in parsed_outputs]
            if len(parsed_outputs) > 1 else []
        )
        output_files = [item[1] for item in parsed_outputs] if len(parsed_outputs) == 1 else []
    else:
        default_formats = default_delivery_formats(normalized_request)
        delivery_format = default_formats[0] if len(default_formats) == 1 else "multi"
        output_specs = (
            [f"{item}:{default_output_title(args.target, item)}" for item in default_formats]
            if len(default_formats) > 1 else []
        )
        output_files = []
    run_id = args.run_id or f"qa-{hashlib.sha256((args.target + normalized_request).encode('utf-8')).hexdigest()[:12]}"
    start_args = argparse.Namespace(
        out=path,
        run_id=run_id,
        profile=profile,
        test_intent=test_intent,
        target_name=args.target,
        target_type=args.target_type or infer_target_type(source),
        target_source=source,
        request_summary=normalized_request,
        task_mode=task_mode,
        delivery_format=delivery_format,
        delivery_carrier=None,
        output_file=output_files,
        output_spec=output_specs,
        required_section=[],
        section_order=[],
        scope_source=[],
        exclude_source=[],
        scope_round=[],
        exclude_round=[],
        allow_new_execution=args.execute,
    )
    return start_command(start_args)


def source_paths(run: dict[str, Any]) -> list[Path]:
    """把 canonical 里登记的来源展开成真实文件路径，供体裁探测使用。"""
    candidates: list[Path] = []
    seen: set[str] = set()
    raw: list[str] = []
    raw.extend(str(value) for value in run.get("input", {}).get("sources", []) or [])
    raw.extend(
        str(item.get("locator", ""))
        for item in run.get("input", {}).get("artifacts", []) or []
        if isinstance(item, dict)
    )
    raw.append(str(run.get("target", {}).get("source", "")))
    for entry in raw:
        entry = entry.strip()
        if not entry or entry.startswith(("http://", "https://")) or entry in seen:
            continue
        seen.add(entry)
        path = Path(entry).expanduser()
        if not path.exists():
            continue
        candidates.extend(sorted(item for item in path.rglob("*") if item.is_file())[:60] if path.is_dir() else [path])
    return candidates[:80]


def restamp_receipts(run: dict[str, Any], fingerprint_before: str) -> int:
    """规范化改写了 canonical 之后，把仍然有效的前序回执重新盖章。

    旧行为是一处确定性缺陷：`complete --stage design` 先跑 normalize，
    normalize 改了 revision/change_ledger → 指纹变化 → baseline 回执立刻失效 →
    报"缺少前置阶段回执：baseline" → 执行者回去重跑一次 baseline（什么都没改也会过）。
    实测两条 trace 各多付一次往返。规范化不是内容变更，不应使前序验证作废。
    """
    fingerprint_after = canonical_fingerprint(run)
    if fingerprint_before == fingerprint_after:
        return 0
    restamped = 0
    for receipt in run.get("phase_receipts", []) or []:
        if not isinstance(receipt, dict):
            continue
        if receipt.get("source_fingerprint") == fingerprint_before:
            receipt["source_fingerprint"] = fingerprint_after
            receipt["revision"] = run.get("revision")
            restamped += 1
    return restamped


def complete_command(path: Path, stage: str) -> int:
    resolved, run = load_run(path)
    fingerprint_before = canonical_fingerprint(run)
    slug = resolved.parent.name

    # autofix 必须先于 normalize：normalize 会把当前全部 ID 写进 change_ledger，
    # 之后它们就被视为"已发布、不得改名"，改名窗口就永久关闭了。
    changes = gate_policy.autofix(run, slug)
    normalized_run, normalize_changes = normalize_mechanical_fields(run)
    run = normalized_run
    changes = changes + list(normalize_changes)
    restamped = restamp_receipts(run, fingerprint_before)
    if changes or restamped:
        atomic_write(resolved, run)

    receipts = current_receipts(run)
    prerequisites = {
        "design": ("baseline",),
        "execution": ("baseline",) if run.get("profile") == "smoke" else ("baseline", "design"),
        "change": ("baseline",),
    }.get(stage, ())
    missing = [name for name in prerequisites if name not in receipts]
    if missing:
        print(f"GATE: 缺少前置阶段回执：{', '.join(missing)}")
        for name in missing:
            print(f"          修法：qa_flow.py complete {resolved} --stage {name}")
        emit_footer("OPEN", next_command=f"qa_flow.py complete {resolved} --stage {missing[0]}")
        return 1

    gate = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("qa_gate.py")), str(resolved), "--stage", stage, "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(gate.stdout)
    except json.JSONDecodeError:
        print(gate.stderr or gate.stdout or "阶段门禁没有返回合法 JSON", file=sys.stderr)
        emit_footer("BLOCKED", next_command="保留原始错误并停止；不要手工绕过控制器")
        return 2

    buckets = gate_policy.partition(result.get("findings", []))
    for line in gate_policy.render_lines(buckets, fixed=changes):
        print(line)

    if buckets[gate_policy.BLOCK]:
        first = buckets[gate_policy.BLOCK][0]
        emit_footer(
            "OPEN",
            next_command=str(first.get("fix") or "修完上面的 BLOCK 条目后重跑同一条命令"),
        )
        return 1

    _, latest = load_run(resolved)
    disclosures = gate_policy.disclosure_notes(buckets)
    state = "DISCLOSE" if disclosures else "CLOSED"
    receipt = {
        "stage": stage,
        "revision": latest.get("revision"),
        "state": state,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_fingerprint": canonical_fingerprint(latest),
        "warnings": len(disclosures),
    }
    existing = [
        item for item in latest.get("phase_receipts", [])
        if not (item.get("stage") == stage and item.get("revision") == latest.get("revision"))
    ]
    latest["phase_receipts"] = existing + [receipt]
    if disclosures:
        latest.setdefault("disclosures", [])
        for note in disclosures:
            if note not in latest["disclosures"]:
                latest["disclosures"].append(note)
    atomic_write(resolved, latest)
    print(f"STAGE {stage} = {state}（revision {latest.get('revision')}）")
    result = {"gate_state": state}
    emit_footer(
        str(result.get("gate_state")),
        next_command=f"qa_flow.py anchor {resolved} --stage release",
    )
    return 3 if result.get("gate_state") == "DISCLOSE" else 0


def publish_command(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(Path(__file__).with_name("qa_publish.py")),
        str(args.qa_run),
    ]
    for locator in args.locator:
        command.extend(["--locator", locator])
    for receipt in args.readback_receipt:
        command.extend(["--readback-receipt", receipt])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    # publish 只保证"文件对不对"。用户能不能看到，由唯一交付口决定。
    deliver = Path(__file__).with_name("qa_deliver.py")
    print(f"NEXT=python3 {deliver} {args.qa_run}  # 交付与上屏的唯一入口")
    publish_state = "OPEN"
    try:
        publish_state = str(json.loads(result.stdout).get("publish_state", "OPEN"))
    except (json.JSONDecodeError, AttributeError):
        pass
    emit_footer(
        f"PUBLISHED_{publish_state}",
        next_command=(
            "逐项返回 publish 回执中的 outputs[].locator"
            if publish_state in {"CLOSED", "DISCLOSE"}
            else "按 publish 输出的 FIX 修复后重跑同一条 publish 命令"
        ),
        delivery_lock="OPEN" if publish_state not in {"CLOSED", "DISCLOSE"} else "CLOSED",
    )
    return result.returncode


def inspect_web_command(path: Path, project: Path) -> int:
    resolved, run = load_run(path)
    card = context_card(resolved, run, "execution")
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("inspect_web_project.py")),
            "--project",
            str(project.expanduser().resolve()),
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    print(json.dumps({
        "context_card": card,
        "inspection_returncode": result.returncode,
        "inspection": json.loads(result.stdout) if result.stdout.strip().startswith("{") else result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }, ensure_ascii=False, indent=2))
    return result.returncode


def main() -> int:
    args = parse_args()
    try:
        if args.command == "bootstrap":
            return bootstrap_command(args)
        if args.command == "start":
            return start_command(args)
        if args.command in {"status", "anchor"}:
            path, run = load_run(args.qa_run)
            stage = args.stage if args.command == "anchor" else None
            print(json.dumps(context_card(path, run, stage), ensure_ascii=False, indent=2))
            # 体裁卡印在每次 anchor 的必经输出里：报告形状由本次任务与材料决定，
            # 不是由 renderer 常量决定。执行者读到什么形状就写什么形状。
            print()
            for line in report_shape.render_card(report_shape.describe(run, source_paths(run))):
                print(line)
            emit_footer(
                "ANCHORED" if args.command == "anchor" else "STARTED",
                next_command=(
                    f"qa_flow.py complete {path} --stage {stage}"
                    if stage and stage in STAGES
                    else f"继续当前 canonical：{path}"
                ),
            )
            return 0
        if args.command == "complete":
            return complete_command(args.qa_run, args.stage)
        if args.command == "normalize":
            path, run, changes = normalize_and_persist(args.qa_run)
            print(json.dumps({
                "state": "NORMALIZED" if changes else "UNCHANGED",
                "qa_run": str(path),
                "revision": run.get("revision"),
                "changes": changes,
            }, ensure_ascii=False, indent=2))
            emit_footer(
                "NORMALIZED" if changes else "UNCHANGED",
                next_command=f"qa_flow.py complete {path} --stage baseline",
            )
            return 0
        if args.command == "publish":
            return publish_command(args)
        if args.command == "inspect-web":
            return inspect_web_command(args.qa_run, args.project)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        emit_footer("BLOCKED", next_command="按原始错误修复后重跑同一条命令")
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
