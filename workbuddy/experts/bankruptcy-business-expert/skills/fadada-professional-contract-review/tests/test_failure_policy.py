#!/usr/bin/env python3
"""失败分级、重试预算、降级交付与升级话术回归。

覆盖真机痛点：无法读取的文档与红线生成失败时反复重试、不及时升级给用户，
三次诊断分别烧掉 751 秒 / 190 秒 / 20 分钟且无交付物。

运行：python3 tests/test_failure_policy.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import failure_policy as fp  # noqa: E402


class ClassifyTest(unittest.TestCase):
    """用户才能修的错必须预算 0——这是不浪费时间的前提。"""

    def test_user_stages(self) -> None:
        for stage in ("input_format", "extract", "input", "deliver"):
            self.assertEqual(fp.classify(stage, []), fp.CLASS_USER, stage)
            self.assertEqual(fp.BUDGETS[fp.classify(stage, [])], 0)

    def test_review_subject_is_user_fixable(self) -> None:
        cls = fp.classify("delivery_gate", ["review subject: 交付所用合同与…不一致"])
        self.assertEqual(cls, fp.CLASS_USER)

    def test_non_ooxml_is_user_fixable(self) -> None:
        self.assertEqual(
            fp.classify("apply_redline", ["BadZipFile: not a zip"]), fp.CLASS_USER)

    def test_gate_content_is_model_fixable(self) -> None:
        cls = fp.classify("delivery_gate", ["report: 章节 「待核查」 为裸占位"])
        self.assertEqual(cls, fp.CLASS_MODEL)
        self.assertEqual(fp.BUDGETS[cls], 2)

    def test_user_class_exceeds_on_first_attempt(self) -> None:
        self.assertTrue(fp.exceeded(fp.CLASS_USER, 1))
        self.assertFalse(fp.exceeded(fp.CLASS_MODEL, 2))
        self.assertTrue(fp.exceeded(fp.CLASS_MODEL, 3))


class LedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.key = "unittest_ledger"
        fp.clear(self.key)

    def tearDown(self) -> None:
        fp.clear(self.key)

    def test_attempts_accumulate_across_calls(self) -> None:
        self.assertEqual(fp.record_attempt(self.key, "delivery_gate"), 1)
        self.assertEqual(fp.record_attempt(self.key, "delivery_gate"), 2)
        self.assertEqual(fp.attempts_so_far(self.key, "delivery_gate"), 2)

    def test_stages_counted_separately(self) -> None:
        fp.record_attempt(self.key, "apply_redline")
        self.assertEqual(fp.attempts_so_far(self.key, "delivery_gate"), 0)

    def test_clear_resets(self) -> None:
        fp.record_attempt(self.key, "delivery_gate")
        fp.clear(self.key)
        self.assertEqual(fp.attempts_so_far(self.key, "delivery_gate"), 0)

    def test_scope_key_tracks_contract_content(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            a, b = Path(raw) / "a.docx", Path(raw) / "b.docx"
            a.write_bytes(b"AAA")
            b.write_bytes(b"BBB")
            self.assertNotEqual(fp.scope_key(a), fp.scope_key(b),
                                "换了合同应当获得独立的重试预算")


class EscalationPayloadTest(unittest.TestCase):
    def test_payload_forbids_retry_and_carries_user_message(self) -> None:
        payload = fp.escalation(
            "input_format", fp.CLASS_USER, ["无法识别的二进制格式"],
            fp.user_message_for("input_format", ["无法识别的二进制格式"]), 1)
        self.assertEqual(payload["status"], "escalate")
        self.assertFalse(payload["retryAllowed"])
        self.assertEqual(payload["nextAction"], "ask_user")
        # 话术必须是可直接发给用户的成品，含具体可执行动作
        self.assertIn("另存为 .docx", payload["userMessage"])
        self.assertIn("不要重跑本命令", payload["hint"])


def write_docx(path: Path, text: str = "合同正文") -> None:
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml",
                         f'<w:document xmlns:w="{W}"><w:body>'
                         f'<w:p><w:r><w:t>{text}</w:t></w:r></w:p>'
                         f'</w:body></w:document>')


class IntakeEscalationTest(unittest.TestCase):
    """无法读取的文档：第一次就升级，绝不重试。"""

    def test_unreadable_input_escalates_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "合同.pdf"
            target.write_bytes(b"%PDF-1.7\n")
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "review_intake.py"), str(target),
                 "--business-type", "采购合同", "--position", "甲方"],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2, "退出码 2 = 已升级，不得再重跑")
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "escalate")
            self.assertEqual(payload["budget"], 0)
            self.assertFalse(payload["retryAllowed"])
            self.assertFalse(payload["capabilities"]["redline"])
            # PDF 指向平台链路（内置读取工具 / fadada-special-ocr），非「另存为 .docx」
            self.assertIn("fadada-special-ocr", payload["userMessage"])

    def test_missing_file_escalates(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "review_intake.py"),
             "/nonexistent/合同.docx", "--business-type", "采购合同",
             "--position", "甲方"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)["status"], "escalate")


class OperationsPreflightTest(unittest.TestCase):
    """红线预检必须一次报全，而不是每轮只暴露一个错。"""

    def _contract(self, directory: Path) -> Path:
        target = directory / "合同.docx"
        W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        paragraphs = "".join(
            f'<w:p><w:r><w:t>第{i}条 这是第{i}段的正文内容。</w:t></w:r></w:p>'
            for i in range(1, 4))
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("word/document.xml",
                             f'<w:document xmlns:w="{W}"><w:body>{paragraphs}'
                             f'<w:sectPr/></w:body></w:document>')
            archive.writestr("word/settings.xml", f'<w:settings xmlns:w="{W}"/>')
        return target

    def test_all_errors_reported_in_one_pass(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            contract = self._contract(directory)
            ops = directory / "ops.json"
            ops.write_text(json.dumps({"operations": [
                {"target": "p0001", "action": "replace_text",
                 "old_text": "根本不存在的原文", "new_text": "X",
                 "risk": "high", "basis_tag": "[法规]", "comment": "c"},
                {"target": "p9999", "action": "comment",
                 "risk": "low", "basis_tag": "[惯例]", "comment": "c"},
                {"target": "p0002", "action": "不存在的动作",
                 "risk": "low", "basis_tag": "[惯例]", "comment": "c"},
            ]}, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "review_docx.py"), "apply",
                 str(contract), str(ops),
                 "--redline", str(directory / "rl.docx"),
                 "--clean", str(directory / "cl.docx")],
                capture_output=True, text=True,
                env={**os.environ, "RICHEE_OUTPUT_DIR": str(directory)})
            combined = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn("Traceback", combined, "应给可读错误而非 traceback")
            # 三类问题必须同时出现，否则就是「改一次试一次」的 N 次往返
            self.assertIn("old_text 在 p0001 中不存在", combined)
            self.assertIn("p9999", combined)
            self.assertIn("不存在的动作", combined)
            self.assertIn("未对文档做任何修改", combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
