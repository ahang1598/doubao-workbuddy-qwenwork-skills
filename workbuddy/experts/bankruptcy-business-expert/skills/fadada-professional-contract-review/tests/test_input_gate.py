#!/usr/bin/env python3
"""输入格式门禁与审查对象一致性回归。

覆盖真机故障（rpt_20260806T065933Z）：
  - 旧版 .doc 直接进 review_docx.py 撞 zipfile 裸崩，redline 被放弃；
  - 模型拿不到原文件路径，改把读到的正文重打成节选当审查对象。

运行：python3 tests/test_input_gate.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import review_intake  # noqa: E402
import validate_review_outputs as validator  # noqa: E402

OLE2_HEADER = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 512


def write_fake_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")


def write_legacy_doc(path: Path, embed_zip: bool = False) -> None:
    """构造 OLE2 文件；embed_zip 复刻真机样本内嵌 OOXML 主题片段的情况。"""
    payload = bytearray(OLE2_HEADER)
    if embed_zip:
        buffer = path.with_suffix(".embedded.zip")
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("theme/theme1.xml", "<theme/>")
        payload += buffer.read_bytes()
        buffer.unlink()
    path.write_bytes(bytes(payload))


class DetectFormatTest(unittest.TestCase):
    def test_real_docx(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "合同.docx"
            write_fake_docx(target)
            self.assertEqual(review_intake.detect_format(target), "docx")

    def test_legacy_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "合同.doc"
            write_legacy_doc(target)
            self.assertEqual(review_intake.detect_format(target), "ole2")

    def test_legacy_doc_with_embedded_zip_is_not_docx(self) -> None:
        """真机样本：.DOC 内嵌 OOXML 主题，zipfile.is_zipfile() 会误判为 True。"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "合同.doc"
            write_legacy_doc(target, embed_zip=True)
            self.assertTrue(zipfile.is_zipfile(target), "前提：zip 探测确实会误判")
            self.assertEqual(review_intake.detect_format(target), "ole2")

    def test_docx_suffix_but_legacy_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "改名的.docx"
            write_legacy_doc(target)
            self.assertEqual(review_intake.detect_format(target), "ole2")

    def test_unknown_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "合同.pdf"
            target.write_bytes(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
            self.assertEqual(review_intake.detect_format(target), "unknown")


class NormalizeInputTest(unittest.TestCase):
    def test_docx_passes_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "合同.docx"
            write_fake_docx(target)
            contract, converted, error = review_intake.normalize_contract_input(
                target, Path(tmp))
            self.assertIsNone(error)
            self.assertIsNone(converted)
            self.assertEqual(contract, target)

    def test_unsupported_returns_actionable_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "合同.pdf"
            target.write_bytes(b"%PDF-1.7\n")
            contract, _, error = review_intake.normalize_contract_input(
                target, Path(tmp))
            self.assertIsNone(contract)
            # 输入格式属「只有用户能修」，预算 0：直接升级，不给重试余地
            self.assertEqual(error["status"], "escalate")
            self.assertEqual(error["stage"], "input_format")
            self.assertEqual(error["budget"], 0)
            self.assertFalse(error["retryAllowed"])
            # PDF 走平台正规链路，不应笼统建议「另存为 .docx」（对 PDF 无效）
            self.assertIn("fadada-special-ocr", error["userMessage"])
            self.assertIn(".docx", error["userMessage"])
            # 能力缺口必须显式声明，供上层按「缺件不得静默」交付
            self.assertFalse(error["capabilities"]["redline"])


class LegacyDocGuidanceTest(unittest.TestCase):
    """.doc 转换失败时仍应给「另存为 .docx / 装 LibreOffice」指引。

    PDF 分支改用平台 OCR 链路后，这条容易被一起改坏——两类输入的补救办法不同。
    """

    def test_doc_conversion_failure_keeps_resave_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "合同.doc"
            write_legacy_doc(target)
            with unittest.mock.patch.object(review_intake, "find_soffice",
                                            return_value=None):
                _, _, error = review_intake.normalize_contract_input(
                    target, Path(tmp))
            self.assertEqual(error["stage"], "input_format")
            self.assertIn("另存为 .docx", error["userMessage"])
            self.assertIn("LibreOffice", error["userMessage"])


class CliGateTest(unittest.TestCase):
    """端到端：脚本层面不得再吐 traceback。"""

    def test_review_docx_extract_on_legacy_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "合同.doc"
            write_legacy_doc(target, embed_zip=True)
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "review_docx.py"), "extract",
                 str(target), "--out", str(Path(tmp) / "out.json")],
                capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            combined = proc.stdout + proc.stderr
            self.assertNotIn("Traceback", combined)
            self.assertIn("另存为 .docx", combined)

    def test_review_docx_bad_subcommand_shows_usage(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "review_docx.py"), "review_docx.py"],
            capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        combined = proc.stdout + proc.stderr
        self.assertIn("extract", combined)
        self.assertIn("review_intake.py", combined)

    def test_review_intake_rejects_unsupported_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "合同.pdf"
            target.write_bytes(b"%PDF-1.7\n")
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "review_intake.py"), str(target),
                 "--business-type", "采购合同", "--position", "甲方"],
                capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn("Traceback", proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["stage"], "input_format")


class ReviewSubjectGateTest(unittest.TestCase):
    """审查对象一致性：堵「用节选冒充全文」。"""

    def _bundle(self, tmp: Path, contract: Path) -> Path:
        bundle = tmp / "intake.json"
        bundle.write_text(json.dumps({
            "sourceSha256": review_intake.file_digest(contract),
            "paragraphCount": 487,
        }, ensure_ascii=False), encoding="utf-8")
        return bundle

    def test_matching_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            contract = tmp / "合同.docx"
            write_fake_docx(contract)
            errors: list[str] = []
            validator.check_review_subject(self._bundle(tmp, contract), contract, errors)
            self.assertEqual(errors, [])

    def test_substituted_contract_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            contract = tmp / "合同.docx"
            write_fake_docx(contract)
            bundle = self._bundle(tmp, contract)

            excerpt = tmp / "节选.docx"          # 模型重打的节选
            with zipfile.ZipFile(excerpt, "w") as archive:
                archive.writestr("word/document.xml", "<w:document>节选</w:document>")

            errors: list[str] = []
            validator.check_review_subject(bundle, excerpt, errors)
            self.assertEqual(len(errors), 1)
            self.assertIn("不一致", errors[0])

    def test_missing_args_skip_check(self) -> None:
        errors: list[str] = []
        validator.check_review_subject(None, None, errors)
        self.assertEqual(errors, [])

    def test_legacy_bundle_without_digest_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            contract = tmp / "合同.docx"
            write_fake_docx(contract)
            bundle = tmp / "intake.json"
            bundle.write_text("{}", encoding="utf-8")
            errors: list[str] = []
            validator.check_review_subject(bundle, contract, errors)
            self.assertEqual(len(errors), 1)
            self.assertIn("sourceSha256", errors[0])


class InheritedLayoutTest(unittest.TestCase):
    """红线/清洁版继承原合同版式，不得因原文件的表宽/页面尺寸判技能不合格。

    真机样本 7 个表格宽 9155–9511 DXA（均 >9026），且合同外观必须保留——
    若对红线跑版式闸门，调用方无论怎么改 report-json 都修不好，交付被永久阻断。

    豁免是**逐项比对**的（做法回灌自 multilingual-contract-review）：只有确实
    与原合同一致的超宽表/页面尺寸才降级为 warning，技能自己新加的超宽表仍判错。
    """

    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    def _docx(self, path: Path, widths: list[list[int]],
              page: tuple[int, int] = (11906, 16838)) -> None:
        tables = "".join(
            "<w:tbl><w:tblGrid>"
            + "".join(f'<w:gridCol w:w="{w}"/>' for w in cols)
            + "</w:tblGrid></w:tbl>"
            for cols in widths
        )
        document = (
            f'<w:document xmlns:w="{self.W}"><w:body>{tables}'
            f'<w:sectPr><w:pgSz w:w="{page[0]}" w:h="{page[1]}"/></w:sectPr>'
            '</w:body></w:document>'
        )
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document)
            archive.writestr("word/styles.xml", f'<w:styles xmlns:w="{self.W}"/>')

    def test_report_still_blocked_by_wide_table(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "report.docx"
            self._docx(target, [[4000, 5511]])
            errors: list[str] = []
            validator.common_checks(target, errors)
            self.assertTrue(any("exceeds content width" in e for e in errors),
                            "报告仍须受表宽闸门约束")

    def test_inherited_wide_table_downgraded(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "合同.docx"
            redline = Path(raw) / "红线.docx"
            self._docx(source, [[4000, 5511]])          # 原合同自带超宽表
            self._docx(redline, [[4000, 5511]])         # 红线原样保留
            errors: list[str] = []
            validator.common_checks(redline, errors,
                                    validator.source_layout(source))
            self.assertEqual(errors, [], "继承自原合同的超宽表只应 warning")

    def test_skill_added_wide_table_still_fails(self) -> None:
        """关键回归：整体豁免会放过这种情况，逐项豁免不会。"""
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "合同.docx"
            redline = Path(raw) / "红线.docx"
            self._docx(source, [[4000, 5511]])                  # 原件一个超宽表
            self._docx(redline, [[4000, 5511], [5000, 5000]])   # 红线另加一个
            errors: list[str] = []
            validator.common_checks(redline, errors,
                                    validator.source_layout(source))
            self.assertEqual(len(errors), 1, "新增的超宽表必须判错")
            self.assertIn("table 2", errors[0])

    def test_inherited_non_a4_page_downgraded(self) -> None:
        letter = (12240, 15840)
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "合同.docx"
            redline = Path(raw) / "红线.docx"
            self._docx(source, [], page=letter)
            self._docx(redline, [], page=letter)
            errors: list[str] = []
            validator.common_checks(redline, errors,
                                    validator.source_layout(source))
            self.assertEqual(errors, [], "原合同就是 Letter 时红线不应被判非 A4")

    def test_redline_page_differing_from_source_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "合同.docx"
            redline = Path(raw) / "红线.docx"
            self._docx(source, [], page=(11906, 16838))     # 原件是 A4
            self._docx(redline, [], page=(12240, 15840))    # 红线却变成 Letter
            errors: list[str] = []
            validator.common_checks(redline, errors,
                                    validator.source_layout(source))
            self.assertTrue(any("not A4" in e for e in errors),
                            "红线擅自改了页面尺寸，不属继承，必须判错")


if __name__ == "__main__":
    unittest.main(verbosity=2)
