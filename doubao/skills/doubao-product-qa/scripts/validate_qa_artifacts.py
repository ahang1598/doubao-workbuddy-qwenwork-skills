#!/usr/bin/env python3
"""校验 qa-product-testing 生成的结构化交付物。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import gate_policy
from qa_run_common import PROFILE_FILES, case_status, coverage_snapshot, semantic_findings

PROFILES = {name: set(files) | {"qa-run.json"} for name, files in PROFILE_FILES.items()}

TRACE_HEADERS = [
    "requirement_id",
    "requirement",
    "source",
    "risk",
    "actor",
    "trigger",
    "rule",
    "observable_result",
    "impact_scope",
    "risk_mechanism_ids",
    "test_case_ids",
    "status",
    "notes",
]

CASE_HEADERS = [
    "case_id",
    "module",
    "title",
    "priority",
    "type",
    "preconditions",
    "steps",
    "test_data",
    "expected_result",
    "requirement_ids",
    "risk_mechanism_ids",
    "release_blocking_reason",
    "automation_candidate",
    "execution_mode",
    "assigned_to",
    "manual_reason",
    "evidence_expected",
    "status",
    "notes",
]
CASE_OPTIONAL_HEADERS = {
    "execution_mode", "assigned_to", "manual_reason", "evidence_expected",
    "release_blocking_reason",
}
CASE_REQUIRED_HEADERS = [name for name in CASE_HEADERS if name not in CASE_OPTIONAL_HEADERS]
MANUAL_CASE_HEADERS = [
    "case_id", "module", "title", "priority", "preconditions", "steps", "test_data",
    "expected_result", "assigned_to", "evidence_expected", "previous_status", "attempt",
    "status", "operator", "actual_result", "started_at", "finished_at", "evidence_paths",
    "tester_notes", "retest_of",
]

PRIORITIES = {"P0", "P1", "P2", "P3"}
TRACE_STATUSES = {"已覆盖", "部分覆盖", "未覆盖", "阻塞", "不适用"}
CASE_STATUSES = {"未执行", "通过", "失败", "待确认", "阻塞", "不适用"}
CASE_TYPES = {
    "功能",
    "边界",
    "异常",
    "状态",
    "权限",
    "兼容",
    "接口",
    "回归",
    "冒烟",
    "可访问性",
    "性能",
    "安全",
    "探索",
}
AUTOMATION_VALUES = {"是", "否", "部分"}


@dataclass
class Finding:
    level: str
    file: str
    message: str
    row: int | None = None


class Validator:
    def __init__(self, root: Path, profile: str) -> None:
        self.root = root
        self.profile = profile
        self.findings: list[Finding] = []
        self.requirements: dict[str, dict[str, str]] = {}
        self.cases: dict[str, dict[str, str]] = {}
        self.qa_run: dict[str, object] | None = None

    def add(self, level: str, file: str, message: str, row: int | None = None) -> None:
        self.findings.append(Finding(level, file, message, row))

    def error(self, file: str, message: str, row: int | None = None) -> None:
        self.add("error", file, message, row)

    def warning(self, file: str, message: str, row: int | None = None) -> None:
        self.add("warning", file, message, row)

    def validate(self) -> None:
        if not self.root.is_dir():
            self.error(str(self.root), "目标目录不存在或不是目录")
            return

        for filename in sorted(PROFILES[self.profile]):
            if not (self.root / filename).is_file():
                self.error(filename, f"{self.profile} profile 缺少必需文件")

        self._validate_qa_run()
        self._validate_markdown_if_present(
            "01-test-plan.md",
            ["目标与范围", "不在范围", "风险", "环境", "准入", "准出", "回归"],
        )
        self._validate_checklist()
        self._validate_bug_report()
        self._validate_markdown_if_present(
            "07-test-report.md",
            ["执行摘要", "覆盖情况", "执行结果", "缺陷", "验收摘要", "风险机制", "发布结论", "未验证"],
        )
        self._validate_traceability()
        self._validate_cases()
        self._validate_manual_guide()
        self._validate_manual_bundle()
        self._validate_cross_references()
        self._validate_device_matrix()
        self._validate_automation_summary()
        self._validate_test_data_manifest()
        self._validate_canonical_consistency()

    def _validate_qa_run(self) -> None:
        filename = "qa-run.json"
        payload = self._read_json(filename)
        if payload is None:
            return
        if not isinstance(payload, dict):
            self.error(filename, "根节点必须是 JSON 对象")
            return
        self.qa_run = payload
        declared_profile = payload.get("profile")
        if declared_profile != self.profile:
            self.error(filename, f"profile={declared_profile!r} 与校验参数 {self.profile!r} 不一致")
        blocking = {id(item) for item in gate_policy.blocking(semantic_findings(payload, self.root))}
        for finding in semantic_findings(payload, self.root):
            message = f"{finding['path']} - {finding['message']}"
            if gate_policy.classify(finding) == gate_policy.BLOCK:
                self.error(filename, message)
            else:
                self.warning(filename, message)

    def _read_text(self, filename: str) -> str | None:
        path = self.root / filename
        if not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            self.error(filename, "文件不是有效 UTF-8")
            return None

    def _validate_markdown_if_present(self, filename: str, terms: Iterable[str]) -> None:
        content = self._read_text(filename)
        if content is None:
            return
        if not content.strip():
            self.error(filename, "文件为空")
            return
        headings = "\n".join(
            line.strip() for line in content.splitlines() if line.lstrip().startswith("#")
        )
        for term in terms:
            if term not in headings:
                self.warning(filename, f"缺少包含“{term}”的章节标题")
        if "{{" in content or "}}" in content:
            self.error(filename, "仍包含未替换的模板变量")

    def _validate_checklist(self) -> None:
        filename = "04-acceptance-checklist.md"
        content = self._read_text(filename)
        if content is None:
            return
        if not re.search(r"^- \[[ xX]\] ", content, flags=re.MULTILINE):
            self.error(filename, "未找到 Markdown 复选项")
        summary = re.search(
            r"总数：(\d+)；通过：(\d+)；未通过：(\d+)；阻塞：(\d+)；待验证：(\d+)；不适用：(\d+)",
            content,
        )
        if not summary:
            self.error(filename, "缺少可复算的验收状态汇总")
        else:
            total, passed, failed, blocked, pending, na = map(int, summary.groups())
            if passed + failed + blocked + pending + na != total:
                self.error(filename, "验收状态计数之和不等于总数")
        if "{{" in content or "}}" in content:
            self.error(filename, "仍包含未替换的模板变量")

    def _validate_bug_report(self) -> None:
        filename = "06-bugs.md"
        content = self._read_text(filename)
        if content is None:
            return
        if (
            "无缺陷" in content
            or "本轮未发现缺陷" in content
            or "本轮执行未发现缺陷" in content
            or "尚未执行，无法判断是否存在产品缺陷" in content
            or "待分析的人工失败（缺陷候选）" in content
        ):
            return
        bug_ids = re.findall(
            r"^##\s+(BUG-[A-Z0-9_-]+-\d{3})\b",
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not bug_ids:
            self.warning(filename, "未找到 BUG-<模块>-NNN 格式的缺陷 ID；若无缺陷请明确写“本轮未发现缺陷”")
            return
        if len(bug_ids) != len(set(bug_ids)):
            self.warning(filename, "存在重复出现的 Bug ID，请确认每个缺陷标题唯一")
        required_terms = [
            "所属模块", "严重程度", "严重程度依据", "优先级", "复现步骤",
            "实际结果", "期望结果", "影响范围", "证据", "初步分析",
            "近期改动关联", "波及范围",
        ]
        for term in required_terms:
            if term not in content:
                self.error(filename, f"Bug 报告缺少“{term}”字段或章节")
        if "{{" in content or "}}" in content:
            self.error(filename, "仍包含未替换的模板变量")

    def _read_csv(
        self,
        filename: str,
        required_headers: list[str],
        optional_headers: set[str] | None = None,
    ) -> list[dict[str, str]]:
        path = self.root / filename
        if not path.is_file():
            return []
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                headers = reader.fieldnames or []
                missing = [name for name in required_headers if name not in headers]
                allowed = set(required_headers) | set(optional_headers or set())
                extra = [name for name in headers if name not in allowed]
                if missing:
                    self.error(filename, f"缺少 CSV 字段：{', '.join(missing)}")
                if extra:
                    self.warning(filename, f"存在扩展 CSV 字段：{', '.join(extra)}")
                return [
                    {key: (value or "").strip() for key, value in row.items() if key is not None}
                    for row in reader
                ]
        except UnicodeDecodeError:
            self.error(filename, "文件不是有效 UTF-8")
        except csv.Error as exc:
            self.error(filename, f"CSV 解析失败：{exc}")
        return []

    def _validate_traceability(self) -> None:
        filename = "02-traceability.csv"
        rows = self._read_csv(filename, TRACE_HEADERS)
        if (self.root / filename).is_file() and not rows:
            self.error(filename, "追踪矩阵没有数据行")
        for row_number, row in enumerate(rows, start=2):
            req_id = row.get("requirement_id", "")
            if not re.fullmatch(r"REQ-[A-Z0-9_-]+-\d{3}", req_id, flags=re.IGNORECASE):
                self.error(filename, "requirement_id 应为 REQ-<模块>-NNN", row_number)
            elif req_id in self.requirements:
                self.error(filename, f"重复 requirement_id：{req_id}", row_number)
            else:
                self.requirements[req_id] = row
            for field in ("requirement", "source", "risk", "status"):
                if not row.get(field):
                    self.error(filename, f"{field} 不能为空", row_number)
            if row.get("risk") and row["risk"] not in PRIORITIES:
                self.error(filename, f"risk 非法：{row['risk']}", row_number)
            if row.get("status") and row["status"] not in TRACE_STATUSES:
                self.error(filename, f"status 非法：{row['status']}", row_number)
            if row.get("status") in {"部分覆盖", "未覆盖", "阻塞"} and not row.get("notes"):
                self.warning(filename, f"{row['status']} 需求应在 notes 解释", row_number)

    def _validate_cases(self) -> None:
        filename = "03-test-cases.csv"
        rows = self._read_csv(filename, CASE_REQUIRED_HEADERS, CASE_OPTIONAL_HEADERS)
        if (self.root / filename).is_file() and not rows:
            self.error(filename, "测试用例表没有数据行")
        for row_number, row in enumerate(rows, start=2):
            case_id = row.get("case_id", "")
            if not re.fullmatch(r"TC-[A-Z0-9_-]+-\d{3}", case_id, flags=re.IGNORECASE):
                self.error(filename, "case_id 应为 TC-<模块>-NNN", row_number)
            elif case_id in self.cases:
                self.error(filename, f"重复 case_id：{case_id}", row_number)
            else:
                self.cases[case_id] = row

            for field in (
                "module",
                "title",
                "priority",
                "type",
                "steps",
                "test_data",
                "expected_result",
                "requirement_ids",
                "risk_mechanism_ids",
                "automation_candidate",
                "status",
            ):
                if not row.get(field):
                    self.error(filename, f"{field} 不能为空", row_number)

            if row.get("priority") and row["priority"] not in PRIORITIES:
                self.error(filename, f"priority 非法：{row['priority']}", row_number)
            if row.get("priority") == "P0" and not row.get("release_blocking_reason"):
                self.error(filename, "P0 缺少 release_blocking_reason", row_number)
            if row.get("type") and row["type"] not in CASE_TYPES:
                self.error(filename, f"type 非法：{row['type']}", row_number)
            if row.get("automation_candidate") and row["automation_candidate"] not in AUTOMATION_VALUES:
                self.error(
                    filename,
                    f"automation_candidate 非法：{row['automation_candidate']}",
                    row_number,
                )
            if row.get("execution_mode") and row["execution_mode"] not in {"automated", "manual", "hybrid"}:
                self.error(filename, f"execution_mode 非法：{row['execution_mode']}", row_number)
            if row.get("execution_mode") in {"manual", "hybrid"}:
                if not row.get("assigned_to"):
                    self.error(filename, "人工用例缺少 assigned_to", row_number)
                if not row.get("manual_reason"):
                    self.error(filename, "人工用例缺少 manual_reason", row_number)
                if not row.get("evidence_expected"):
                    self.error(filename, "人工用例缺少 evidence_expected", row_number)
            if row.get("status") and row["status"] not in CASE_STATUSES:
                self.error(filename, f"status 非法：{row['status']}", row_number)
            if row.get("status") == "通过" and not row.get("notes"):
                self.warning(filename, "通过用例建议在 notes 记录执行证据或结果位置", row_number)

    def _validate_manual_guide(self) -> None:
        if not self.qa_run or not self.qa_run.get("manual_handoff", {}).get("required"):
            return
        filename = "10-manual-test-guide.md"
        if not (self.root / filename).is_file():
            self.error(filename, "自动化不可用且已声明人工交接，但缺少人工测试执行指南")
            return
        self._validate_markdown_if_present(
            filename,
            ["降级原因", "执行前准备", "人工操作用例", "结果回传", "结论限制"],
        )

    def _validate_manual_bundle(self) -> None:
        if not self.qa_run or not self.qa_run.get("manual_handoff", {}).get("required"):
            return
        required = {
            "manual-handoff/01-manual-test-plan.md": ["测试范围", "执行前准备", "准出条件", "结果处理"],
            "manual-handoff/03-manual-acceptance-checklist.md": ["发布门禁"],
            "manual-handoff/04-evidence-guide.md": ["截图策略", "按问题类型取证", "路径填写"],
            "manual-handoff/05-risks-and-blockers.md": ["自动化阻塞", "产品与发布风险", "当前限制"],
        }
        for filename, headings in required.items():
            if not (self.root / filename).is_file():
                self.error(filename, "人工交接包缺少必需文件")
            else:
                self._validate_markdown_if_present(filename, headings)
        filename = "manual-handoff/02-manual-test-cases.csv"
        rows = self._read_csv(filename, MANUAL_CASE_HEADERS)
        if not rows:
            self.error(filename, "人工测试用例表没有数据行")
            return
        expected_ids = {str(value) for value in self.qa_run.get("manual_handoff", {}).get("case_ids", [])}
        actual_ids = {row.get("case_id", "") for row in rows}
        if actual_ids != expected_ids:
            self.error(filename, f"人工用例 ID 与 manual_handoff.case_ids 不一致：{sorted(actual_ids ^ expected_ids)}")
        canonical = {str(item.get("id", "")): item for item in self.qa_run.get("cases", [])}
        for row_number, row in enumerate(rows, start=2):
            case = canonical.get(row.get("case_id", ""), {})
            if row.get("title") != str(case.get("title", "")):
                self.error(filename, "title 与 qa-run.json 不一致", row_number)
            if row.get("priority") != str(case.get("priority", "")):
                self.error(filename, "priority 与 qa-run.json 不一致", row_number)
            if row.get("previous_status") != case_status(self.qa_run, row.get("case_id", "")):
                self.error(filename, "previous_status 与 qa-run.json 派生状态不一致", row_number)
            if row.get("status") != "未执行":
                self.warning(filename, "生成态 status 应为未执行；若这是人工填写结果，请先运行 import_manual_results.py", row_number)
            try:
                if int(row.get("attempt", "0")) < 1:
                    raise ValueError
            except ValueError:
                self.error(filename, "attempt 必须是大于等于 1 的整数", row_number)

    @staticmethod
    def _split_ids(value: str) -> list[str]:
        return [item.strip() for item in re.split(r"[;；]", value) if item.strip()]

    def _validate_cross_references(self) -> None:
        if not self.requirements or not self.cases:
            return
        filename = "02-traceability.csv"
        for req_id, requirement in self.requirements.items():
            linked_cases = self._split_ids(requirement.get("test_case_ids", ""))
            if requirement.get("status") == "已覆盖" and not linked_cases:
                self.error(filename, f"{req_id} 标为已覆盖但没有 test_case_ids")
            for case_id in linked_cases:
                if case_id not in self.cases:
                    self.error(filename, f"{req_id} 引用了不存在的用例 {case_id}")
                elif req_id not in self._split_ids(self.cases[case_id].get("requirement_ids", "")):
                    self.error(filename, f"{req_id} → {case_id} 缺少反向引用")

        case_file = "03-test-cases.csv"
        for case_id, case in self.cases.items():
            for req_id in self._split_ids(case.get("requirement_ids", "")):
                if req_id.upper().startswith("RISK-"):
                    continue
                if req_id not in self.requirements:
                    self.error(case_file, f"{case_id} 引用了不存在的需求 {req_id}")
                elif case_id not in self._split_ids(self.requirements[req_id].get("test_case_ids", "")):
                    self.error(case_file, f"{case_id} → {req_id} 缺少反向引用")

    def _read_json(self, filename: str) -> object | None:
        path = self.root / filename
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except UnicodeDecodeError:
            self.error(filename, "文件不是有效 UTF-8")
        except json.JSONDecodeError as exc:
            self.error(filename, f"JSON 解析失败：{exc}")
        return None

    def _validate_device_matrix(self) -> None:
        filename = "08-device-matrix.json"
        payload = self._read_json(filename)
        if payload is None:
            return
        if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
            self.error(filename, "必须是包含 runs 数组的 JSON 对象")
            return
        runs = payload["runs"]
        if not runs:
            self.error(filename, "设备矩阵没有 run")
            return
        seen = set()
        for index, item in enumerate(runs, start=1):
            if not isinstance(item, dict):
                self.error(filename, f"runs[{index}] 必须是对象")
                continue
            for field in ("id", "platform", "target", "command"):
                if not item.get(field):
                    self.error(filename, f"runs[{index}] 缺少字段 {field}")
            run_id = item.get("id")
            if run_id in seen:
                self.error(filename, f"重复 run id：{run_id}")
            seen.add(run_id)
            command = item.get("command")
            if command is not None and (
                not isinstance(command, list)
                or not command
                or not all(isinstance(arg, str) and arg for arg in command)
            ):
                self.error(filename, f"runs[{index}].command 必须是非空字符串数组")

    def _validate_automation_summary(self) -> None:
        filename = "09-automation-summary.json"
        payload = self._read_json(filename)
        if payload is None:
            return
        if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
            self.error(filename, "必须是包含 runs 数组的 JSON 对象")
            return
        allowed = {"passed", "failed", "timeout", "infra_error", "skipped"}
        for index, item in enumerate(payload["runs"], start=1):
            if not isinstance(item, dict):
                self.error(filename, f"runs[{index}] 必须是对象")
                continue
            for field in ("id", "platform", "target", "status"):
                if item.get(field) in (None, ""):
                    self.error(filename, f"runs[{index}] 缺少字段 {field}")
            status = item.get("status")
            if status and status not in allowed:
                self.error(filename, f"runs[{index}].status 非法：{status}")

    def _validate_test_data_manifest(self) -> None:
        filename = "test-data-manifest.json"
        path = self.root / filename
        if not path.is_file():
            return
        payload = self._read_json(filename)
        if not isinstance(payload, dict):
            self.error(filename, "根节点必须是 JSON 对象")
            return
        if self.qa_run is None:
            return
        expected = self.qa_run.get("test_data", {})
        for key in ("writes_allowed", "accounts", "created_records", "cleanup"):
            if payload.get(key) != expected.get(key):
                self.error(filename, f"{key} 与 qa-run.json 不一致；请重新渲染产物")

    def _validate_canonical_consistency(self) -> None:
        if self.qa_run is None:
            return
        canonical_cases = {
            str(item.get("id", "")): item
            for item in self.qa_run.get("cases", [])
            if isinstance(item, dict) and item.get("id")
        }
        if self.cases and set(self.cases) != set(canonical_cases):
            self.error("03-test-cases.csv", "用例 ID 与 qa-run.json 不一致；请重新渲染产物")
        for case_id, row in self.cases.items():
            expected = case_status(self.qa_run, case_id)
            if row.get("status") != expected:
                self.error(
                    "03-test-cases.csv",
                    f"{case_id} 状态为 {row.get('status')}，qa-run.json 派生状态为 {expected}",
                )
        canonical_requirements = {
            str(item.get("id", ""))
            for item in self.qa_run.get("requirements", [])
            if isinstance(item, dict) and item.get("id")
        }
        if self.requirements and set(self.requirements) != canonical_requirements:
            self.error("02-traceability.csv", "需求 ID 与 qa-run.json 不一致；请重新渲染产物")
        snapshot = coverage_snapshot(self.qa_run)
        report = self._read_text("07-test-report.md")
        if report is not None and f"总用例：{snapshot['case_total']}" not in report:
            self.warning("07-test-report.md", "用例总数可能与 qa-run.json 不一致；请重新渲染产物")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 QA 测试交付物的结构与追踪关系")
    parser.add_argument("artifact_dir", type=Path, help="qa-results 下的功能目录")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="full",
        help="按交付阶段选择必需文件，默认 full",
    )
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validator = Validator(args.artifact_dir.resolve(), args.profile)
    validator.validate()

    errors = sum(item.level == "error" for item in validator.findings)
    warnings = sum(item.level == "warning" for item in validator.findings)
    requirement_count = len(validator.requirements)
    case_count = len(validator.cases)
    if validator.qa_run is not None:
        requirement_count = max(requirement_count, len(validator.qa_run.get("requirements", [])))
        case_count = max(case_count, len(validator.qa_run.get("cases", [])))
    result = {
        "ok": errors == 0,
        "profile": args.profile,
        "artifact_dir": str(args.artifact_dir.resolve()),
        "errors": errors,
        "warnings": warnings,
        "requirements": requirement_count,
        "test_cases": case_count,
        "findings": [asdict(item) for item in validator.findings],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in validator.findings:
            location = item.file if item.row is None else f"{item.file}:{item.row}"
            print(f"[{item.level.upper()}] {location} - {item.message}")
        print(
            f"校验完成：errors={errors}, warnings={warnings}, "
            f"requirements={requirement_count}, test_cases={case_count}"
        )

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
