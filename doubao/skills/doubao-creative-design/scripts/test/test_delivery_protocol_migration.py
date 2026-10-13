#!/usr/bin/env python3
"""Guard the delivery protocol shared by the main route and HTML references."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class DeliveryProtocolMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.preview = (ROOT / "references/workflow/html-preview.md").read_text(encoding="utf-8")
        cls.html_validation = (ROOT / "references/workflow/html-validation.md").read_text(encoding="utf-8")
        cls.validation = (ROOT / "references/workflow/validation.md").read_text(encoding="utf-8")
        cls.delivery_gate = (
            ROOT / "references/workflow/image-generation-delivery-gate.md"
        ).read_text(encoding="utf-8")
        cls.coding_rendering = (ROOT / "references/html/coding-rendering.md").read_text(
            encoding="utf-8"
        )
        cls.html_item = (ROOT / "references/items/HTML.md").read_text(encoding="utf-8")

    def test_exit_one_requires_repair_without_blocking_canvas_persistence(self) -> None:
        required = "退出码 `1` 本身不阻断默认 Canvas 的 HTML 上传、Item 创建与回读"
        for name, content in (
            ("SKILL.md", self.skill),
            ("html-preview.md", self.preview),
            ("html-validation.md", self.html_validation),
        ):
            with self.subTest(file=name):
                self.assertIn(required, content)
                self.assertIn("修正并重跑", content)

        forbidden = (
            "退出码 `1` 或截图确认的真实页面问题会阻断 `FileBatchUpload`",
            "退出码 `1` 的问题版本不得上传或写入",
        )
        combined = "\n".join((self.skill, self.preview, self.html_validation))
        for wording in forbidden:
            self.assertNotIn(wording, combined)

    def test_preview_quality_and_persistence_are_separate_states(self) -> None:
        for name, content in (
            ("html-validation.md", self.html_validation),
            ("validation.md", self.validation),
        ):
            with self.subTest(file=name):
                self.assertIn("不合格截图不得展示", content)
                self.assertIn("不阻断 HTML 上传", content)
        self.assertIn("预览未验证", self.preview)
        self.assertIn("不能宣称", self.validation)

    def test_workspace_card_protocol_keeps_stable_failure_codes(self) -> None:
        self.assertIn("WORKSPACE_CARD_NOT_PRESENTED", self.validation)
        self.assertIn("WORKSPACE_CARD_DELIVERY_NOT_EXCLUSIVE", self.validation)
        self.assertNotIn("WORKSPACE_CONTEXT_NOT_INITIALIZED", self.validation)
        self.assertNotIn("WORKSPACE_ID_DELIVERY_NOT_EXCLUSIVE", self.validation)
        self.assertIn("原始 ID", self.validation)
        self.assertIn("主 Agent", self.validation)
        self.assertIn("画布卡片", self.validation)

    def test_media_results_keep_two_independent_delivery_channels(self) -> None:
        combined = "\n".join((self.skill, self.delivery_gate, self.validation))
        for term in (
            "design-cli",
            "+get",
            "present_files",
            "同步双分支",
            "候选",
            "未采用版本",
            "中间素材",
            "HTML_ASSEMBLY_BEFORE_MEDIA_BARRIER",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)

    def test_html_artifacts_keep_separate_delivery_channels(self) -> None:
        combined = "\n".join(
            (self.skill, self.preview, self.validation, self.coding_rendering, self.html_item)
        )
        for term in (
            "FileBatchUpload",
            "Markdown",
            "HTML Item",
            "workspace_id?item_id=xxx",
            "HTML_WORKSPACE_CARD_NOT_PRESENTED",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)
        self.assertIn("不使用 present_files、不创建 IMAGE Item", self.preview)
        self.assertIn("禁止通过 `present_files` 直接交付原 `.html`", self.validation)

    def test_current_non_delivery_capabilities_are_not_rolled_back(self) -> None:
        combined = "\n".join((self.skill, self.html_validation, self.validation))
        for term in (
            "data-web-fonts",
            "屏间过渡路由验收",
            "mix-blend-mode: multiply",
            "ART_TITLE_ALPHA_INVALID",
            "KV 展示确认",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)


if __name__ == "__main__":
    unittest.main()
