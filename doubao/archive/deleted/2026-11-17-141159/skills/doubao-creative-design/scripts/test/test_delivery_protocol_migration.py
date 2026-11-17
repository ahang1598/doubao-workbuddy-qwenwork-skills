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
        self.assertIn("html-preview.md#交付与失败", self.html_validation)
        for name, content in (("validation.md", self.validation),):
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

    def test_media_direct_delivery_and_post_archive(self) -> None:
        for name, content in (("SKILL.md", self.skill), ("delivery_gate", self.delivery_gate)):
            with self.subTest(file=name):
                self.assertIn('<RichMediaCard>{"refs":[', content)
                self.assertIn("Workspace ID", content)
                self.assertIn("产后", content)
                self.assertIn("+get", content)
                self.assertIn("+update", content)
        self.assertIn("HTML_ASSEMBLY_BEFORE_MEDIA_BARRIER", self.validation)
        self.assertIn("不作为组装前提", self.validation)
        self.assertIn("工具返回失败", self.delivery_gate)
        self.assertIn("Mobile", self.delivery_gate)

    def test_no_legacy_media_gate_in_active_references(self) -> None:
        paths = [ROOT / "SKILL.md", *sorted((ROOT / "references").rglob("*.md"))]
        legacy = (
            "双通道", "双分支", "sync_group_id",
            "同步启动 CLI 写入", "同步完成持久化",
            "完成 CLI 写入／回读和以 RichMediaCard",
            "同步完成 RichMediaCard 单项直接交付及产后归档",
            "MEDIA_DELIVERY_NOT_SYNCHRONIZED",
        )
        for path in paths:
            content = path.read_text(encoding="utf-8")
            for term in legacy:
                with self.subTest(file=str(path.relative_to(ROOT)), term=term):
                    self.assertNotIn(term, content, f"Legacy media gate: {path}:{term}")

    def test_storage_exceptions_and_html_archive_order(self) -> None:
        image = (ROOT / "references/items/image.md").read_text(encoding="utf-8")
        archive = (ROOT / "references/workflow/canvas-asset-organization.md").read_text(encoding="utf-8")
        self.assertIn("手工登记", image)
        self.assertIn("平台已关联对象", image)
        self.assertIn("用户上传", archive)
        self.assertIn("HTML Item 回读成功并完成产后目录整理后", self.validation)
        self.assertIn("不为不存在的结果", self.delivery_gate)

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
            "Web 字体契约",
            "屏间过渡路由验收",
            "mix-blend-mode: multiply",
            "ART_TITLE_ALPHA_INVALID",
            "KV 展示确认",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)


if __name__ == "__main__":
    unittest.main()
