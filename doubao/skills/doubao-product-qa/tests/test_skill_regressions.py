from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gate_policy  # noqa: E402
import report_shape  # noqa: E402
from qa_publish import validate_local_file  # noqa: E402
from qa_gate import stage_findings  # noqa: E402
from qa_run_common import SEVERITIES, coverage_snapshot, semantic_findings  # noqa: E402
from render_qa_artifacts import render_markdown_bundle  # noqa: E402
from run_web_session import update_qa_run  # noqa: E402


def request_hash(summary: str) -> str:
    return f"sha256:{hashlib.sha256(summary.encode('utf-8')).hexdigest()}"


def base_run() -> dict:
    summary = "复核已有证据并按请求交付"
    return {
        "schema_version": 2,
        "run_id": "regression",
        "revision": 1,
        "profile": "bug",
        "test_intent": "non_ui_validation",
        "execution_level": "blocked",
        "selected_path": "evidence_review",
        "target": {"type": "document", "name": "回归样例", "source": ""},
        "request_contract": {
            "request_summary": summary,
            "request_hash": request_hash(summary),
            "task_mode": "execution_review",
            "scope": {
                "included_source_ids": [],
                "excluded_source_ids": [],
                "included_rounds": [],
                "excluded_rounds": [],
            },
            "evidence_policy": {
                "allow_new_execution": False,
                "allow_precheck_bug_promotion": False,
                "required_bug_evidence_level": "L2_observation",
            },
            "delivery": {
                "artifact_required": False,
                "format": "inline_markdown",
                "carrier": "inline",
                "filenames": [],
                "artifacts": [],
                "required_sections": [],
                "section_order": [],
                "must_surface_to_user": True,
            },
        },
        "phase_receipts": [],
        "input": {"summary": summary, "sources": [], "assumptions": [], "conflicts": [], "artifacts": []},
        "environment": {},
        "requirements": [],
        "risk_mechanisms": [],
        "open_questions": [],
        "change_ledger": [{
            "id": "CHG-001", "revision": 1, "action": "ADD", "object_type": "run",
            "added_ids": ["regression"], "removed_ids": [], "modified_ids": [],
            "before_count": 0, "after_count": 1, "delta_count": 1,
            "source": "test", "summary": "初始化",
        }],
        "observed_surfaces": [],
        "cases": [],
        "acceptance_checks": [],
        "executions": [],
        "evidence": [],
        "bugs": [],
        "bug_candidates": [],
        "risks": [],
        "coverage": {
            "requirement_total": 0, "requirement_linked": 0, "requirement_unlinked": 0,
            "p0_requirement_total": 0, "p0_requirement_linked": 0,
            "case_total": 0, "case_status_counts": {},
            "acceptance_total": 0, "acceptance_status_counts": {},
        },
        "release_decision": {"decision": "undetermined", "rationale": "没有正式执行证据。", "conditions": []},
        "delivery_manifest": {"source_revision": 1, "outputs": []},
        "test_data": {
            "writes_allowed": False, "accounts": [], "created_records": [],
            "cleanup": {"required": False, "status": "completed", "command": "none", "residuals": []},
        },
        "blockers": [],
        "manual_handoff": {
            "required": False, "status": "not_required", "reason": "", "target_platform": "",
            "operator": "", "prerequisites": [], "case_ids": [],
            "evidence_requirements": [], "result_submission": [],
        },
        "unverified": [],
    }


def status_run(statuses: list[str]) -> dict:
    run = base_run()
    run["cases"] = [{"id": f"TC-CASE-{index:03d}", "title": f"记录 {index}"} for index in range(1, len(statuses) + 1)]
    run["executions"] = [
        {
            "id": f"EXE-CASE-{index:03d}",
            "case_id": f"TC-CASE-{index:03d}",
            "status": status,
        }
        for index, status in enumerate(statuses, start=1)
    ]
    return run


def valid_bug(severity: str = "S2") -> dict:
    return {
        "id": "BUG-CASE-001",
        "title": "可复现缺陷",
        "module": "核心流程",
        "status": "open",
        "severity": severity,
        "severity_basis": "正式观察显示核心流程失败",
        "priority": "P1",
        "category": "other",
        "environment": "test",
        "preconditions": ["已登录"],
        "steps": ["执行核心动作"],
        "actual_result": "动作失败",
        "expected_result": "动作成功",
        "reproducibility": "always",
        "repro_attempts": 2,
        "first_failure_preserved": True,
        "evidence_grade": "L2_observation",
        "evidence_ids": ["EVD-CASE-001"],
        "impact": "核心流程受影响",
        "analysis": {
            "classification": "产品缺陷",
            "trigger_hypothesis": "固定输入触发",
            "change_correlation": "待核对",
            "blast_radius": "同一入口",
            "confidence": "medium",
        },
        "workaround": "暂无",
        "related_ids": ["RISK-CASE"],
    }


def formal_failed_execution(run: dict, execution_id: str = "EXE-CASE-001") -> None:
    run["cases"] = [{
        "id": "TC-CASE-001", "module": "核心", "title": "核心动作",
        "priority": "P2", "type": "功能", "steps": ["执行核心动作"], "test_data": "fixture=case-001",
        "expected_result": "动作成功", "requirement_ids": ["RISK-CASE"],
        "risk_mechanism_ids": [], "execution_mode": "automated",
    }]
    run["evidence"] = [{
        "id": "EVD-CASE-001", "type": "manual_observation", "description": "正式观察失败",
        "level": "L2_observation", "validation_scope": "formal",
    }]
    run["executions"] = [{
        "id": execution_id, "case_id": "TC-CASE-001", "status": "failed",
        "execution_level": "partial_validation", "validation_scope": "formal",
        "execution_method": "automated", "actual_result": "动作失败",
        "evidence_ids": ["EVD-CASE-001"],
    }]
    append_count_change(run, "case", 1)
    append_count_change(run, "evidence", 1)
    append_count_change(run, "execution", 1)


def append_count_change(run: dict, object_type: str, after: int) -> None:
    before = 0
    for item in run["change_ledger"]:
        if item.get("object_type") == object_type:
            before = item["after_count"]
    number = len(run["change_ledger"]) + 1
    run["change_ledger"].append({
        "id": f"CHG-{number:03d}",
        "revision": run["revision"],
        "action": "ADD",
        "object_type": object_type,
        "added_ids": [f"{object_type}-{after}"],
        "removed_ids": [],
        "modified_ids": [],
        "before_count": before,
        "after_count": after,
        "delta_count": after - before,
        "source": "test",
        "summary": f"增加 {object_type}",
    })


class SkillRegressionTests(unittest.TestCase):
    # 已删除 test_formal_qa_bootstrap_precedes_attachment_work。
    # 它用 assertIn 断言 SKILL.md 里存在“禁止 Bash/Glob 枚举业务附件”等措辞，
    # 长期全绿；而真实 trace 显示，三次加载过本 Skill 的运行 100% 违反了那条规则——
    # 因为不先看目录就填不出 bootstrap 需要的 --source。查措辞的测试为一条不可执行的
    # 规则提供了“有回归保护”的假象，是负债不是资产。规则已删除，测试一并作废。

    def test_delivery_is_single_entry_and_never_deadlocks(self) -> None:
        """交付口唯一、且除“没有产物”外不会把执行者卡死。

        取证：旧流程 publish 返回 OPEN 后，模型直接绕开控制器连发 5 次宿主工具，
        产出两张重复卡片。所以这里查行为不查措辞：
        产物齐全 → 必须放行并给出唯一一条上屏调用；产物缺失 → 才允许阻断。
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            qa_run = root / "qa-run.json"
            subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap", str(qa_run),
                "--request", "输出 Markdown 收口报告", "--target", "退款审核",
                "--output", "报告.md",
            ], text=True, capture_output=True, check=False)

            missing = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_deliver.py"), str(qa_run),
            ], text=True, capture_output=True, check=False)
            self.assertIn("DELIVERY_LOCK=OPEN", missing.stdout)
            self.assertIn("DELIVER_BLOCKED", missing.stdout)

            # 章节不全属于“产物不够好”，必须放行 + 披露，不得阻断
            (root / "报告.md").write_text("# 报告\n\n## 结论\n\nno_go。\n", encoding="utf-8")
            partial = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_deliver.py"), str(qa_run),
            ], text=True, capture_output=True, check=False)
            self.assertEqual(partial.returncode, 0, partial.stdout + partial.stderr)
            self.assertIn("DELIVERY_LOCK=CLOSED", partial.stdout)
            self.assertIn("本轮披露", partial.stdout)
            self.assertIn("缺少用户约定的章节", partial.stdout)

            (root / "报告.md").write_text(
                "# 报告\n\n## 测试报告\n\nno_go。\n\n## 详细用例\n\nTC-1\n\n## Bug 单\n\nBUG-1\n",
                encoding="utf-8",
            )
            ready = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_deliver.py"), str(qa_run),
            ], text=True, capture_output=True, check=False)
            self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)
            self.assertIn("DELIVERY_LOCK=CLOSED", ready.stdout)
            # 唯一一条上屏调用，且只出现一次 —— 重复卡片在结构上不可能发生
            calls = [line for line in ready.stdout.splitlines() if line.strip().startswith("NotifyHuman")]
            self.assertEqual(len(calls), 1, ready.stdout)
            self.assertEqual(calls[0].count("attachment_source"), 1, calls[0])
            self.assertIn("不要重复", ready.stdout)

    def test_gate_blocks_only_wrong_output_not_incomplete_canonical(self) -> None:
        """门只拦“会让用户拿到错东西”的问题；canonical 完整度不阻断。

        阳性对照：把 P0 与阻塞项集合弄成不相等，门必须抓到。
        """
        run = status_run(["passed"] * 3)
        run["bugs"] = [{
            "id": "BUG-REF-001", "title": "金额上限被绕过", "module": "退款", "status": "open",
            "severity": "S1", "priority": "P0", "severity_basis": "资损", "category": "产品缺陷",
            "environment": "staging", "preconditions": ["订单已支付"], "steps": ["提交"],
            "actual_result": "写入超额", "expected_result": "拒绝", "reproducibility": "always",
            "repro_attempts": 1, "first_failure_preserved": True, "evidence_grade": "L2_observation",
            "evidence_ids": [], "impact": "资金", "workaround": "无", "related_ids": [],
            "analysis": {
                "classification": "后端", "trigger_hypothesis": "上限校验缺失",
                "change_correlation": "待查发布记录", "blast_radius": "共用退款服务", "confidence": "high",
            },
        }]
        run["release_decision"] = {
            "decision": "no_go", "rationale": "存在资损缺陷", "blocking_bug_ids": [],
        }
        findings = semantic_findings(run, None)
        blocking = gate_policy.blocking(findings)
        paths = {item["path"] for item in blocking}
        self.assertIn("release_decision.blocking_bug_ids", paths)

        # 反向：集合相等时不得阻断
        run["release_decision"]["blocking_bug_ids"] = ["BUG-REF-001"]
        again = gate_policy.blocking(semantic_findings(run, None))
        self.assertNotIn(
            "release_decision.blocking_bug_ids", {item["path"] for item in again}
        )

    def test_report_shape_matches_gold_families(self) -> None:
        """体裁判据用金标准反标定：判错就是判据错了。"""
        plan_run = {"executions": [], "cases": [{"id": "TC-1"}], "bugs": [],
                    "coverage": {}, "input": {}, "open_questions": [],
                    "request_contract": {"task_mode": "plan"}, "revision": 1, "target": {}}
        self.assertEqual(report_shape.select(plan_run, {}), "plan-only")
        self.assertNotIn("发布结论", report_shape.resolve_sections("plan-only", plan_run, {}))

        gate_run = dict(plan_run, executions=[{"id": "EXE-1"}])
        self.assertEqual(report_shape.select(gate_run, {"has_timeseries": False}), "release-gate")
        self.assertEqual(report_shape.select(gate_run, {"has_timeseries": True}), "rule-model")

        # 空章节不占位：没有 Bug 时不出现「已确认缺陷」
        sections = report_shape.resolve_sections("release-gate", gate_run, {})
        self.assertNotIn("已确认缺陷", sections)
        self.assertIn("结论", sections)

    def test_bootstrap_infers_defaults_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            qa_run = Path(directory) / "qa-run.json"
            command = [
                sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap", str(qa_run),
                "--request", "基于 PRD 输出测试范围和测试用例",
                "--target", "退款审核",
                "--source", "/tmp/退款审核.docx",
            ]
            first = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            self.assertIn("QA_FLOW_STATE=STARTED", first.stdout)
            self.assertIn("SKILL_LOADED=doubao-qa", first.stdout)
            self.assertIn("DELIVERY_LOCK=CLOSED", first.stdout)

            run = json.loads(qa_run.read_text(encoding="utf-8"))
            self.assertEqual(run["profile"], "plan")
            self.assertEqual(run["request_contract"]["task_mode"], "plan")
            self.assertEqual(run["test_intent"], "non_ui_validation")
            self.assertEqual(run["request_contract"]["delivery"]["format"], "multi")
            self.assertEqual(
                run["request_contract"]["delivery"]["filenames"],
                ["退款审核-QA测试方案与报告", "退款审核-QA测试用例与追踪"],
            )
            self.assertEqual(
                [
                    (item["format"], item["carrier"])
                    for item in run["request_contract"]["delivery"]["artifacts"]
                ],
                [("lark_doc", "lark_doc"), ("lark_sheets", "lark_sheets")],
            )

            second = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
            self.assertIn('"reused": true', second.stdout)
            self.assertIn("QA_FLOW_STATE=STARTED", second.stdout)

    def test_bootstrap_infers_evidence_review_and_exact_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            qa_run = Path(directory) / "qa-run.json"
            result = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap", str(qa_run),
                "--request", "读取现有日志、执行记录和供应商回执，给出 go/no-go 收口结论并用 Markdown 输出",
                "--target", "冷链告警引擎",
                "--source", "/tmp/cold-chain-evidence",
                "--output", "冷链告警_QA收口报告.md",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            run = json.loads(qa_run.read_text(encoding="utf-8"))
            self.assertEqual(run["profile"], "full")
            self.assertEqual(run["request_contract"]["task_mode"], "execution_review")
            self.assertFalse(run["request_contract"]["evidence_policy"]["allow_new_execution"])
            self.assertEqual(run["request_contract"]["delivery"]["format"], "markdown")
            self.assertEqual(
                run["request_contract"]["delivery"]["filenames"],
                ["冷链告警_QA收口报告.md"],
            )

    def test_bootstrap_routes_default_doubao_carriers_and_explicit_markdown(self) -> None:
        scenarios = (
            ("输出 QA 复核与收口报告", "lark_doc", "lark_doc", "QA测试方案与报告"),
            ("输出需求追踪和测试用例表格", "lark_sheets", "lark_sheets", "QA测试用例与追踪"),
            ("准备 go/no-go 评审会材料", "lark_ppt", "lark_ppt", "QA评审汇报"),
            ("输出 Markdown 报告", "markdown", "local", "QA收口报告.md"),
        )
        for request, output_format, carrier, filename_suffix in scenarios:
            with self.subTest(request=request), tempfile.TemporaryDirectory() as directory:
                qa_run = Path(directory) / "qa-run.json"
                result = subprocess.run([
                    sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap", str(qa_run),
                    "--request", request,
                    "--target", "组合优惠订单",
                ], text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                delivery = json.loads(qa_run.read_text(encoding="utf-8"))["request_contract"]["delivery"]
                self.assertEqual(delivery["format"], output_format)
                self.assertEqual(delivery["carrier"], carrier)
                self.assertEqual(delivery["artifacts"][0]["format"], output_format)
                self.assertTrue(delivery["filenames"][0].endswith(filename_suffix))

    def test_bootstrap_explicit_office_and_doubao_formats_override_semantic_default(self) -> None:
        scenarios = (
            ("输出测试用例 xlsx", "xlsx", "office_file"),
            ("输出测试报告 docx", "docx", "office_file"),
            ("输出 QA 汇报 pptx", "pptx", "office_file"),
            ("输出到豆包文档", "lark_doc", "lark_doc"),
            ("输出到豆包表格", "lark_sheets", "lark_sheets"),
            ("输出到豆包 PPT", "lark_ppt", "lark_ppt"),
        )
        for request, output_format, carrier in scenarios:
            with self.subTest(request=request), tempfile.TemporaryDirectory() as directory:
                qa_run = Path(directory) / "qa-run.json"
                result = subprocess.run([
                    sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap", str(qa_run),
                    "--request", request,
                    "--target", "退款审核",
                ], text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                delivery = json.loads(qa_run.read_text(encoding="utf-8"))["request_contract"]["delivery"]
                self.assertEqual(delivery["format"], output_format)
                self.assertEqual(delivery["carrier"], carrier)

        with tempfile.TemporaryDirectory() as directory:
            qa_run = Path(directory) / "qa-run.json"
            result = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap", str(qa_run),
                "--request", "输出测试方案 docx 和用例 xlsx",
                "--target", "退款审核",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            delivery = json.loads(qa_run.read_text(encoding="utf-8"))["request_contract"]["delivery"]
            self.assertEqual(delivery["format"], "multi")
            self.assertEqual(
                [(item["format"], item["filename"]) for item in delivery["artifacts"]],
                [
                    ("docx", "退款审核-QA测试方案与报告.docx"),
                    ("xlsx", "退款审核-QA测试用例与追踪.xlsx"),
                ],
            )

    def test_bootstrap_bad_output_is_self_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap",
                str(Path(directory) / "qa-run.json"),
                "--request", "输出测试用例",
                "--target", "示例",
                "--output", "没有扩展名",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            combined = result.stdout + result.stderr
            self.assertIn("FIX:", combined)
            self.assertIn("QA_FLOW_STATE=BLOCKED", combined)
            self.assertIn("NEXT=", combined)

    def test_normalize_repairs_only_mechanical_schema_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            qa_run = Path(directory) / "qa-run.json"
            started = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap", str(qa_run),
                "--request", "基于 PRD 输出测试用例",
                "--target", "退款审核",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(started.returncode, 0, started.stderr or started.stdout)
            run = json.loads(qa_run.read_text(encoding="utf-8"))
            run["input"] = {
                "summary": "退款审核",
                "sources": [],
                "assumptions": [],
                "conflicts": [],
                "artifacts": [{
                    "id": "SRC-001", "type": "document", "locator": "PRD.md",
                    "access_status": "read", "completeness_checked": True,
                    "coverage_note": "全文",
                }],
            }
            run["requirements"] = [{
                "id": "REQ-REF-001", "title": "退款边界", "source": "SRC-001", "risk": "P0",
                "actor": "学员", "precondition": "订单可退款", "trigger": "提交退款",
                "rule": "边界规则生效", "state_change": "进入审核",
                "expected_result": "结果可观察", "failure_behavior": "拒绝并提示",
                "impact_scope": ["退款主链路"],
            }]
            run["risk_mechanisms"] = [{
                "id": "RM-REF-001", "title": "边界错误", "failure_mode": "错误放行",
                "business_impact": "金额错误", "oracle": ["结果符合规则"],
                "requirement_ids": ["REQ-REF-001"], "case_ids": [],
                "priority": "P0", "status": "designed",
            }]
            run["cases"] = [{
                "id": "TC-REF-001", "module": "退款", "title": "边界值",
                "priority": "P0", "type": "功能", "steps": ["提交"],
                "test_data": "学习比例=30.00%", "expected_result": "进入约定审核分支",
                "requirement_ids": ["REQ-REF-001"], "risk_mechanism_ids": ["RM-REF-001"],
                "execution_mode": "manual", "release_blocking_reason": "金额错误阻断发布",
                "status": "未执行",
            }]
            run["open_questions"] = [{
                "id": "Q-REF-001", "question": "30% 是否包含边界",
                "impact": "影响分流", "status": "待确认", "next_action": "产品确认",
            }]
            run["coverage"] = {}
            qa_run.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            normalized = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "normalize", str(qa_run),
            ], text=True, capture_output=True, check=False)
            self.assertEqual(normalized.returncode, 0, normalized.stderr or normalized.stdout)
            self.assertIn("QA_FLOW_STATE=NORMALIZED", normalized.stdout)
            updated = json.loads(qa_run.read_text(encoding="utf-8"))
            self.assertEqual(updated["requirements"][0]["summary"], "退款边界")
            self.assertEqual(updated["requirements"][0]["behavior"]["actor"], "学员")
            self.assertNotIn("status", updated["cases"][0])
            self.assertEqual(updated["open_questions"][0]["status"], "open")
            self.assertEqual(updated["risk_mechanisms"][0]["case_ids"], ["TC-REF-001"])
            self.assertEqual(updated["input"]["sources"], ["PRD.md"])
            self.assertEqual(updated["coverage"], coverage_snapshot(updated))
            self.assertEqual(updated["change_ledger"][-1]["after_count"], 1)

    def test_case1_gold_counts_and_real_markdown_order(self) -> None:
        run = status_run(["passed"] * 10 + ["failed"] * 3 + ["pending_confirmation"] * 2)
        run["target"]["name"] = "外链分享灰度测试"
        run["request_contract"]["delivery"].update({
            "artifact_required": True,
            "format": "markdown",
            "carrier": "local",
            "filenames": ["外链分享灰度测试收口报告.md"],
            "artifacts": [{
                "format": "markdown", "carrier": "local", "filename": "外链分享灰度测试收口报告.md",
            }],
            "required_sections": ["测试报告", "详细用例", "Bug 单"],
            "section_order": ["测试报告", "详细用例", "Bug 单"],
        })
        run["bugs"] = [
            {"id": f"BUG-CASE-{index:03d}", "title": f"合格 Bug {index}"}
            for index in range(1, 4)
        ]
        counts = coverage_snapshot(run)["case_status_counts"]
        self.assertEqual(counts, {"失败": 3, "待确认": 2, "通过": 10})
        content = render_markdown_bundle(run)
        self.assertLess(content.index("## 测试报告"), content.index("## 详细用例"))
        self.assertLess(content.index("## 详细用例"), content.index("## Bug 单"))
        self.assertEqual(content.count("## BUG-CASE-"), 3)
        release_findings = stage_findings(run, "release")
        self.assertTrue(any(
            item["path"] == "delivery_manifest.outputs" for item in release_findings
        ))

    def test_case2_gold_counts_and_s0_is_rejected(self) -> None:
        counts = coverage_snapshot(
            status_run(["passed"] * 9 + ["failed"] * 3 + ["pending_confirmation"] * 2)
        )["case_status_counts"]
        self.assertEqual(counts, {"失败": 3, "待确认": 2, "通过": 9})
        self.assertNotIn("S0", SEVERITIES)

        run = base_run()
        run["evidence"] = [{
            "id": "EVD-CASE-001", "type": "manual_observation", "description": "正式观察",
            "level": "L2_observation", "validation_scope": "formal",
        }]
        run["bugs"] = [valid_bug("S0")]
        append_count_change(run, "evidence", 1)
        append_count_change(run, "bug", 1)
        findings = semantic_findings(run)
        self.assertTrue(any(item["path"] == "bugs[0].severity" for item in findings))

    def test_open_boundary_cannot_be_unconditional_oracle(self) -> None:
        run = base_run()
        run["open_questions"] = [{
            "id": "Q-REF-001", "question": "学习比例 30% 是否包含边界",
            "impact": "影响退款审核分流", "status": "open", "next_action": "产品确认口径",
        }]
        run["cases"] = [{
            "id": "TC-REF-030", "module": "退款", "title": "30% 边界",
            "priority": "P2", "type": "边界", "steps": ["提交退款"],
            "test_data": "学习比例=30.00%", "expected_result": "30.00% 均转人工审核",
            "requirement_ids": ["RISK-REF"], "risk_mechanism_ids": [],
            "execution_mode": "automated",
        }]
        append_count_change(run, "case", 1)
        run["coverage"] = coverage_snapshot(run)
        findings = semantic_findings(run)
        self.assertTrue(any(
            item["path"] == "cases[0].expected_result" and "双轨/条件预期" in item["message"]
            for item in findings
        ))

        run["cases"][0]["expected_result"] = (
            "按两种口径分别验证：若含边界则进入人工审核，否则保持自动路径"
        )
        self.assertFalse(any(
            item["path"] == "cases[0].expected_result"
            for item in semantic_findings(run)
        ))

    def test_one_execution_requires_one_bug_or_unique_signatures(self) -> None:
        run = base_run()
        formal_failed_execution(run)
        first = valid_bug()
        first["related_ids"] = ["EXE-CASE-001"]
        second = copy.deepcopy(first)
        second["id"] = "BUG-CASE-002"
        second["title"] = "同次执行的第二个表象"
        run["bugs"] = [first, second]
        append_count_change(run, "bug", 2)
        run["coverage"] = coverage_snapshot(run)
        findings = semantic_findings(run)
        self.assertTrue(any("被拆成 2 个开放 Bug" in item["message"] for item in findings))

        run["bugs"][0]["independent_failure_signature"] = "权限判定错误"
        run["bugs"][1]["independent_failure_signature"] = "审计事件缺失"
        self.assertFalse(any(
            "被拆成 2 个开放 Bug" in item["message"] for item in semantic_findings(run)
        ))

    def test_publish_open_creates_no_artifact_and_keeps_delivery_locked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            qa_run = root / "qa-run.json"
            output_name = "不应生成.md"
            run = base_run()
            run["request_contract"]["delivery"].update({
                "artifact_required": True,
                "format": "markdown",
                "carrier": "local",
                "filenames": [output_name],
                "artifacts": [{
                    "format": "markdown", "carrier": "local", "filename": output_name,
                }],
            })
            run["evidence"] = [{
                "id": "EVD-CASE-001", "type": "manual_observation", "description": "正式观察",
                "level": "L2_observation", "validation_scope": "formal",
            }]
            run["bugs"] = [valid_bug("S0")]
            append_count_change(run, "evidence", 1)
            append_count_change(run, "bug", 1)
            run["phase_receipts"] = [{
                "stage": stage, "revision": 1, "state": "CLOSED",
                "source_fingerprint": "",
            } for stage in ("baseline", "design", "execution")]
            qa_run.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            from qa_run_common import canonical_fingerprint
            fingerprint = canonical_fingerprint(run)
            for receipt in run["phase_receipts"]:
                receipt["source_fingerprint"] = fingerprint
            qa_run.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            published = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "publish", str(qa_run),
            ], text=True, capture_output=True, check=False)
            self.assertEqual(published.returncode, 1, published.stderr or published.stdout)
            self.assertIn('"publish_state": "OPEN"', published.stdout)
            self.assertIn('"delivery_allowed": false', published.stdout)
            self.assertIn('"artifacts_created": false', published.stdout)
            self.assertIn("DELIVERY_LOCK=OPEN", published.stdout)
            self.assertFalse((root / output_name).exists())

    def test_case3_pending_records_stay_pending_and_precheck_cannot_be_bug(self) -> None:
        counts = coverage_snapshot(
            status_run(["passed"] * 11 + ["failed"] * 4 + ["pending_confirmation"] * 2)
        )["case_status_counts"]
        self.assertEqual(counts, {"失败": 4, "待确认": 2, "通过": 11})

        run = base_run()
        run["cases"] = [{
            "id": "TC-PERF-001", "module": "性能", "title": "小样本性能预跑",
            "priority": "P2", "type": "性能", "steps": ["请求三次"], "test_data": "3 次",
            "expected_result": "仅记录 baseline", "requirement_ids": ["RISK-PERF"],
            "risk_mechanism_ids": [], "execution_mode": "automated",
        }]
        run["evidence"] = [{
            "id": "EVD-CASE-001", "type": "manual_observation", "description": "三次预跑偏慢",
            "level": "L2_observation", "validation_scope": "precheck",
        }]
        run["executions"] = [{
            "id": "EXE-PERF-001", "case_id": "TC-PERF-001", "status": "failed",
            "execution_level": "exploratory", "validation_scope": "precheck",
            "execution_method": "automated", "actual_result": "三次预跑偏慢",
            "evidence_ids": ["EVD-CASE-001"],
        }]
        bug = valid_bug()
        bug["related_ids"] = ["EXE-PERF-001"]
        run["bugs"] = [bug]
        append_count_change(run, "case", 1)
        append_count_change(run, "execution", 1)
        append_count_change(run, "evidence", 1)
        append_count_change(run, "bug", 1)
        findings = semantic_findings(run)
        messages = "\n".join(item["message"] for item in findings)
        self.assertIn("预跑执行不能直接提升", messages)
        self.assertIn("仅由预跑证据支持", messages)

    def test_case4_round_scope_state_semantics_and_mixed_office_contract(self) -> None:
        run = base_run()
        run["request_contract"]["scope"]["included_rounds"] = ["round-1"]
        run["input"]["sources"] = ["第一轮需求"]
        run["input"]["artifacts"] = [{
            "id": "SRC-002", "type": "document", "locator": "round-2.docx",
            "round": "round-2", "access_status": "read", "completeness_checked": True,
            "coverage_note": "读取第二轮",
        }]
        findings = semantic_findings(run)
        self.assertTrue(any("轮次" in item["message"] for item in findings))

        run["input"]["artifacts"] = []
        run["request_contract"]["scope"]["included_rounds"] = []
        run["cases"] = [{
            "id": "TC-STATE-001", "module": "退款", "title": "自动审核状态",
            "priority": "P2", "type": "状态", "steps": ["提交退款"], "test_data": "订单 O-001",
            "expected_result": "状态和技术结果分别可观察", "requirement_ids": ["RISK-STATE"],
            "risk_mechanism_ids": [], "execution_mode": "automated",
            "state_oracle": {
                "intermediate": "AUTO_APPROVED",
                "terminal": "REFUND_ACCEPTED",
                "technical_outcome": "SUCCESS",
                "side_effect": "退款任务仅创建一次",
            },
        }]
        append_count_change(run, "case", 1)
        self.assertFalse(any(
            item["path"] == "cases[0].state_oracle" for item in semantic_findings(run)
        ))
        conflated = copy.deepcopy(run)
        conflated["cases"][0]["state_oracle"]["technical_outcome"] = "AUTO_APPROVED"
        self.assertTrue(any(
            item["path"] == "cases[0].state_oracle" for item in semantic_findings(conflated)
        ))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            qa_run = root / "qa-run.json"
            start = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap", str(qa_run),
                "--request", "输出测试方案 docx 和用例 xlsx",
                "--target", "退款审核",
                "--output", "docx:退款审核测试方案.docx",
                "--output", "xlsx:退款审核测试用例.xlsx",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(start.returncode, 0, start.stderr or start.stdout)
            contract = json.loads(qa_run.read_text(encoding="utf-8"))["request_contract"]["delivery"]
            self.assertEqual(contract["format"], "multi")
            self.assertEqual(
                [(item["format"], item["carrier"]) for item in contract["artifacts"]],
                [("docx", "office_file"), ("xlsx", "office_file")],
            )

            docx = root / "退款审核测试方案.docx"
            xlsx = root / "退款审核测试用例.xlsx"
            with zipfile.ZipFile(docx, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types/>")
                archive.writestr("word/document.xml", "<document/>")
            with zipfile.ZipFile(xlsx, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types/>")
                archive.writestr("xl/workbook.xml", "<workbook/>")
            self.assertTrue(validate_local_file(docx, "docx").startswith("sha256:"))
            self.assertTrue(validate_local_file(xlsx, "xlsx").startswith("sha256:"))

    def test_unique_publish_generates_and_registers_real_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            qa_run = root / "qa-run.json"
            output_name = "方案收口.md"
            start = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "bootstrap", str(qa_run),
                "--request", "输出 Markdown，报告在前",
                "--target", "方案",
                "--output", output_name,
            ], text=True, capture_output=True, check=False)
            self.assertEqual(start.returncode, 0, start.stderr or start.stdout)
            run = json.loads(qa_run.read_text(encoding="utf-8"))
            run["input"] = {
                "summary": "方案",
                "sources": ["需求.md"],
                "assumptions": [],
                "conflicts": [],
                "artifacts": [{
                    "id": "SRC-001", "type": "document", "locator": "需求.md",
                    "access_status": "read", "completeness_checked": True,
                    "coverage_note": "全文读取",
                }],
            }
            run["requirements"] = [{
                "id": "REQ-PLAN-001", "summary": "输出方案", "source": "SRC-001", "risk": "P2",
            }]
            run["risk_mechanisms"] = [{
                "id": "RM-PLAN-001", "title": "方案遗漏", "failure_mode": "关键步骤缺失",
                "business_impact": "无法执行", "oracle": ["章节和步骤可执行"],
                "requirement_ids": ["REQ-PLAN-001"], "case_ids": ["TC-PLAN-001"],
                "priority": "P2", "status": "designed",
            }]
            run["cases"] = [{
                "id": "TC-PLAN-001", "module": "方案", "title": "核对方案结构",
                "priority": "P2", "type": "功能", "steps": ["核对章节"], "test_data": "revision=1",
                "expected_result": "报告、用例和 Bug 单章节均存在",
                "requirement_ids": ["REQ-PLAN-001"], "risk_mechanism_ids": ["RM-PLAN-001"],
                "execution_mode": "automated",
            }]
            append_count_change(run, "requirement", 1)
            append_count_change(run, "risk_mechanism", 1)
            append_count_change(run, "case", 1)
            # 纯方案交付同样要单列已知未覆盖范围（金标准在只有 PRD 的题目里也这么做）
            run["unverified"] = ["下游支付渠道真实打款依赖未联调接口，本轮不覆盖"]
            run["coverage"] = coverage_snapshot(run)
            qa_run.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            for stage in ("baseline", "design"):
                completed = subprocess.run([
                    sys.executable, str(SCRIPTS / "qa_flow.py"), "complete", str(qa_run),
                    "--stage", stage,
                ], text=True, capture_output=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            published = subprocess.run([
                sys.executable, str(SCRIPTS / "qa_flow.py"), "publish", str(qa_run),
            ], text=True, capture_output=True, check=False)
            self.assertEqual(published.returncode, 0, published.stderr or published.stdout)
            self.assertIn('"delivery_allowed": true', published.stdout)
            self.assertIn("DELIVERY_LOCK=CLOSED", published.stdout)
            artifact = root / output_name
            self.assertTrue(artifact.is_file())
            self.assertGreater(artifact.stat().st_size, 0)
            content = artifact.read_text(encoding="utf-8")
            self.assertLess(content.index("## 测试报告"), content.index("## 详细用例"))
            self.assertLess(content.index("## 详细用例"), content.index("## Bug 单"))
            updated = json.loads(qa_run.read_text(encoding="utf-8"))
            self.assertEqual(updated["delivery_manifest"]["outputs"][0]["status"], "validated")
            self.assertEqual(
                Path(updated["delivery_manifest"]["outputs"][0]["locator"]).resolve(),
                artifact.resolve(),
            )
            self.assertEqual(updated["phase_receipts"][-1]["stage"], "release")

    def test_web_session_writes_revisioned_evidence_and_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            qa_run = root / "qa-run.json"
            out = root / "web-evidence"
            out.mkdir()
            for name in ("test-stdout.log", "test-stderr.log", "web-session-summary.json"):
                (out / name).write_text("{}\n", encoding="utf-8")
            run = base_run()
            run["cases"] = [{
                "id": "TC-WEB-001", "module": "Web", "title": "核心页面",
                "priority": "P2", "type": "冒烟", "steps": ["打开页面"], "test_data": "URL=/",
                "expected_result": "页面业务断言通过", "requirement_ids": ["RISK-WEB"],
                "risk_mechanism_ids": [], "execution_mode": "automated",
            }]
            append_count_change(run, "case", 1)
            run["coverage"] = coverage_snapshot(run)
            qa_run.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            update_qa_run(
                qa_run,
                {
                    "case_id": "TC-WEB-001",
                    "execution_id": "EXE-WEB-001",
                    "runner_kind": "playwright",
                },
                {
                    "status": "passed",
                    "message": "核心页面断言通过",
                    "readiness": {"ok": True},
                    "runner_exit_code": 0,
                },
                out,
            )
            updated = json.loads(qa_run.read_text(encoding="utf-8"))
            self.assertEqual(updated["revision"], 2)
            self.assertEqual(updated["executions"][0]["validation_scope"], "formal")
            self.assertEqual(updated["evidence"][0]["level"], "L3_reproducible")
            self.assertTrue(all(item["id"].startswith("EVD-") for item in updated["evidence"]))
            self.assertEqual(updated["change_ledger"][-2]["object_type"], "evidence")
            self.assertEqual(updated["change_ledger"][-1]["object_type"], "execution")


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# 门禁标定：四份金标准的数值指纹
#
# 来源是用户提供的四份专家金标准输出。它们是"正确答案"的定义，
# 因此必须能通过包内每一道 BLOCK 门。
# 金标准不过门 = 阈值/判据错了，不是金标准错了（doubao-skill-builder/gate-design §1 问 5）。
# 改任何一道 BLOCK 门之前，先跑这个测试。
# ---------------------------------------------------------------------------
GOLD_FIXTURES = {
    "组合优惠订单部分取消": {
        "statuses": ["passed"] * 9 + ["failed"] * 3 + ["pending_confirmation"] * 2,
        "bugs": [("BUG-ORDER-001", "S1", "P0"), ("BUG-ORDER-002", "S2", "P1"), ("BUG-ORDER-003", "S2", "P1")],
        "blocking": ["BUG-ORDER-001"],
        "decision": "no_go",
        "unverified": ["低版本兼容、正式性能、三行商品尾差、取消与加锁并发、退款失败转人工、回调乱序和依赖超时未覆盖"],
    },
    "知识库外链分享": {
        "statuses": ["passed"] * 10 + ["failed"] * 3 + ["pending_confirmation"] * 2,
        "bugs": [("BUG-SHARE-001", "S1", "P0"), ("BUG-SHARE-002", "S1", "P0"), ("BUG-SHARE-003", "S2", "P1")],
        "blocking": ["BUG-SHARE-001", "BUG-SHARE-002"],
        "decision": "no_go",
        "unverified": ["同 visit_id 的 30 分钟边界、部分角色直调 API 组合未覆盖"],
    },
    "冷链事件时间告警": {
        "statuses": ["passed"] * 11 + ["failed"] * 4 + ["pending_confirmation"] * 2,
        "bugs": [
            ("BUG-COLD-004", "S1", "P0"), ("BUG-COLD-005", "S2", "P1"),
            ("BUG-COLD-008", "S1", "P0"), ("BUG-COLD-011", "S1", "P0"),
        ],
        "blocking": ["BUG-COLD-004", "BUG-COLD-008", "BUG-COLD-011"],
        "decision": "no_go",
        "unverified": ["历史补传样本离线重放、跨批连续与并发重复未执行"],
    },
    "知贝退款申请与审核": {
        "statuses": [],
        "bugs": [],
        "blocking": [],
        "decision": "undetermined",
        "unverified": ["平台券真实到账依赖未联调的下游接口，本轮已知未覆盖"],
    },
}


def gold_run(spec: dict) -> dict:
    run = status_run(spec["statuses"]) if spec["statuses"] else base_run()
    if not spec["statuses"]:
        run["cases"] = [{"id": f"TC-PLAN-{i:03d}", "title": f"用例 {i}"} for i in range(1, 15)]
    run["bugs"] = []
    for bug_id, severity, priority in spec["bugs"]:
        bug = valid_bug(severity)
        bug["id"] = bug_id
        bug["priority"] = priority
        run["bugs"].append(bug)
    run["release_decision"] = {
        "decision": spec["decision"],
        "rationale": "金标准结论",
        "blocking_bug_ids": spec["blocking"],
        "conditions": [],
    }
    run["unverified"] = spec["unverified"]
    run["coverage"] = coverage_snapshot(run)
    return run


class GoldCalibrationTests(unittest.TestCase):
    def test_every_gold_standard_passes_all_block_gates(self) -> None:
        for name, spec in GOLD_FIXTURES.items():
            with self.subTest(gold=name):
                blocking = gate_policy.blocking(semantic_findings(gold_run(spec), None))
                self.assertEqual(
                    [], [f"{i['path']}: {i['message']}" for i in blocking],
                    f"金标准《{name}》被自己的门拦住了——先改门，不要改金标准",
                )

    def test_known_bad_outputs_are_blocked(self) -> None:
        """方向一（灵敏度）：评测里实际发生过的四类错误必须被拦住。"""
        # 1) P0 膨胀：把金标的 P1 抬成 P0（组合优化实际发生）
        inflated = copy.deepcopy(GOLD_FIXTURES["组合优惠订单部分取消"])
        inflated["bugs"] = [(bid, sev, "P0") for bid, sev, _ in inflated["bugs"]]
        paths = {i["path"] for i in gate_policy.blocking(semantic_findings(gold_run(inflated), None))}
        self.assertIn("release_decision.blocking_bug_ids", paths)

        # 2) 非法枚举 S0（企业知识库实际发生）
        bad_enum = gold_run(GOLD_FIXTURES["知识库外链分享"])
        bad_enum["bugs"][0]["severity"] = "S0"
        paths = {i["path"] for i in gate_policy.blocking(semantic_findings(bad_enum, None))}
        self.assertTrue(any(p.endswith(".severity") for p in paths), paths)

        # 3) 未执行 > 0 却声称未验证范围为无（组合优化实际发生）
        contradictory = gold_run(GOLD_FIXTURES["组合优惠订单部分取消"])
        contradictory["cases"].extend({"id": f"TC-EXTRA-{i:03d}", "title": "未执行"} for i in range(1, 22))
        contradictory["unverified"] = []
        contradictory["coverage"] = coverage_snapshot(contradictory)
        paths = {i["path"] for i in gate_policy.blocking(semantic_findings(contradictory, None))}
        self.assertIn("unverified", paths)

        # 4) 零执行证据却下终审（金标准明确禁止）
        overreach = gold_run(GOLD_FIXTURES["知贝退款申请与审核"])
        overreach["release_decision"]["decision"] = "no_go"
        paths = {i["path"] for i in gate_policy.blocking(semantic_findings(overreach, None))}
        self.assertIn("release_decision.decision", paths)

    def test_light_path_is_not_crushed(self) -> None:
        """轻路径回归：单点问答/无产物契约的任务不被新下限约束。"""
        light = base_run()
        light["request_contract"]["delivery"]["artifact_required"] = False
        self.assertEqual([], gate_policy.blocking(semantic_findings(light, None)))
