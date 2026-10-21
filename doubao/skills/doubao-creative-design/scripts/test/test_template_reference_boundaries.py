"""Contract tests for natural-language reference Briefs and the HTML protocol."""
from __future__ import annotations

import json
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ReferenceBriefAndHtmlProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "references/workflow/template-rewrite.md").read_text(encoding="utf-8")
        cls.analysis = (ROOT / "references/style/coding/ai-coding/reference-analysis.md").read_text(encoding="utf-8")
        cls.creation = (ROOT / "references/workflow/creation/ai-coding.md").read_text(encoding="utf-8")
        cls.validation = (ROOT / "references/workflow/validation.md").read_text(encoding="utf-8")
        cls.protocol = (ROOT / "references/html/coding-rendering.md").read_text(encoding="utf-8")
        cls.asset_prompt_guide = (
            ROOT / "references/style/coding/ai-coding/asset-prompt-guide.md"
        ).read_text(encoding="utf-8")
        cls.bindings = json.loads((ROOT / "assets/templates/ref-bindings.json").read_text(encoding="utf-8"))
        cls.css = json.loads((ROOT / "assets/templates/css/catalog.json").read_text(encoding="utf-8"))
        cls.svg = json.loads((ROOT / "assets/svg/catalog.json").read_text(encoding="utf-8"))

    def test_template_authorization_remains_separate(self):
        self.assertIn("模板授权边界", self.template)
        self.assertIn("唯一事实源", self.template)
        self.assertIn("本文件不授予编辑权限", self.analysis)

    def test_reference_filter_and_eleven_dimensions(self):
        for term in ("水印", "截图 UI", "平台按钮", "黑边", "账号名", "AI 角标"):
            self.assertIn(term, self.analysis)
        for term in ("版式", "构图", "关系", "文案", "色彩", "光影材质", "字体", "信息", "风格", "人像", "商业与可迁移规律"):
            self.assertIn(term, self.analysis)
        self.assertIn("禁止使用 K、RGB、HEX 或光比数字", self.analysis)
        self.assertIn("具体胶片型号", self.analysis)

    def test_multiblock_and_same_source_mechanisms(self):
        for term in ("分栏", "四宫格", "时间轴", "步骤图", "对比卡", "卡片流", "不得写“其余同理”"):
            self.assertIn(term, self.analysis)
        for term in ("构图公式", "配色思路", "文字层数与字号相对比例", "文案语气与修辞", "主体与其他元素的关联强弱", "美术成像手法"):
            self.assertIn(term, self.analysis)

    def test_rebuild_order_and_natural_brief(self):
        self.assertIn("默认换掉所有具体色相", self.analysis)
        self.assertIn("不做“圆换圆、方换方”的换皮", self.analysis)
        self.assertIn("至少重建三项", self.analysis)
        self.assertIn("一个主亮点和一至两个辅助亮点", self.analysis)
        self.assertIn("不新建参考分析 JSON、参数表、机器合同或平行 Brief", self.analysis)
        self.assertIn("阶段 6 才把实现参数直接写入 HTML", self.creation)
        self.assertIn("禁止因没有模板 ID", self.validation)

    def test_category_template_name_mapping_is_resolvable(self):
        refs = set(self.bindings["category_refs"])
        self.assertEqual(
            set(self.bindings["naming_contract"]),
            {"category_ref_key", "template_id", "display_name", "resolution", "binding_meaning"},
        )
        self.assertEqual(self.css["ref_bindings"], "assets/templates/ref-bindings.json")
        self.assertEqual(self.svg["ref_bindings"], "assets/templates/ref-bindings.json")
        self.assertEqual(set(self.bindings["css"]["default_ref_keys"]), refs)
        css_ids = {entry["id"] for entry in self.css["entries"]}
        svg_ids = {entry["id"] for entry in self.svg["entries"]}
        self.assertTrue(css_ids)
        self.assertTrue(svg_ids)
        self.assertTrue(all(entry.get("name") for entry in self.css["entries"]))
        self.assertEqual(len({entry["name"] for entry in self.css["entries"]}), len(self.css["entries"]))
        self.assertTrue(all(entry.get("name") for entry in self.svg["entries"]))
        self.assertEqual(len({entry["name"] for entry in self.svg["entries"]}), len(self.svg["entries"]))
        self.assertTrue(set(self.bindings["css"]["entry_overrides"]).issubset(css_ids))
        for entry in self.svg["entries"]:
            self.assertTrue(entry["name"])
            self.assertTrue(set(entry["ref_keys"]).issubset(refs))

    def test_fixed_canvas_top_level_html_item_protocol(self):
        for term in ("data-canvas-width", "data-canvas-height", "固定 `px` 值", "可加载的外部样式表", "`FileBatchUpload`", "顶层 `<item type=\"HTML\">`", "禁止 `<frame type=\"HTML\">`"):
            self.assertIn(term, self.protocol)
        self.assertIn("`+update`／`+update-batch` 只允许修正顶层对象的 `brief`／`path`", self.protocol)

    def test_all_category_refs_require_background_quality_and_prompt_routing(self):
        self.assertIn("## 5. 背景图 Prompt", self.asset_prompt_guide)
        category_refs = self.bindings["category_refs"]
        spec_paths = {entry["spec"] for entry in category_refs.values()}
        visual_paths = {entry["visual"] for entry in category_refs.values()}

        for relative in spec_paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("纹理、肌理或渐变", text, relative)
            self.assertIn("不得以无变化纯色铺满", text, relative)

        for relative in visual_paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("纹理、肌理或渐变", text, relative)
            self.assertIn("不得以无变化纯色铺满", text, relative)
            self.assertIn(
                "../ai-coding/asset-prompt-guide.md#5-背景图-prompt",
                text,
                relative,
            )

    def test_background_assets_follow_visible_responsibility(self):
        contracts = {
            "creation": self.creation,
            "asset": self.asset_prompt_guide,
            "carousel": (ROOT / "references/style/coding/scenarios/social-carousel-spec.md").read_text(encoding="utf-8"),
            "long": (ROOT / "references/style/coding/scenarios/social-long-image-spec.md").read_text(encoding="utf-8"),
            "brief": (ROOT / "example/brief.md").read_text(encoding="utf-8"),
        }
        self.assertIn("CSS、图片或二者组合", contracts["creation"])
        self.assertIn("连续内容组", contracts["creation"])
        self.assertIn("完全被遮挡且无其他职责", contracts["asset"])
        self.assertIn("不得重复生产", contracts["asset"])
        self.assertIn("背景生产单元", contracts["carousel"])
        self.assertIn("背景生产单元", contracts["long"])
        self.assertIn("Visual 决定使用 CSS、图片或组合", contracts["long"])
        self.assertIn("只为实际可见、露底或跨段连续职责生产背景", contracts["long"])
        self.assertIn("背景系统", contracts["brief"])
        forbidden = (
            "连续长图先生成与完整画布等比例的底图",
            "不能因上层遮挡而省略完整底图",
            "先做完整底图，再做按本页内容需要的背景",
            "封面与内页均先准备完整底图",
            "底图必须有纹理、肌理或渐变至少一项",
            "先规划一张从画布顶部连续到底部的完整长底图",
            "先生产完整底图",
            "完整底图仍覆盖被遮挡区域",
        )
        for name, text in contracts.items():
            for phrase in forbidden:
                self.assertNotIn(phrase, text, name)

    def test_social_spec_keeps_content_before_visual_and_css_routing(self):
        social = (ROOT / "references/style/coding/scenarios/social-long-image-spec.md").read_text(encoding="utf-8")
        headings = [line for line in social.splitlines() if line.startswith("## ")]
        self.assertEqual(headings[-1], "## 下一步路由")
        self.assertNotIn("transition_out", social)
        self.assertNotIn("### 前期规划就匹配视觉与 CSS", social)
        self.assertNotIn("### 摄影分章候选", social)
        self.assertIn("CSS ID、源路径与版本", social)
        self.assertIn("Brief 短采用记录", social)

    def test_social_continuous_content_groups_have_decision_boundaries(self):
        social = (ROOT / "references/style/coding/scenarios/social-long-image-spec.md").read_text(encoding="utf-8")
        for term in (
            "连续内容组是",
            "合组条件",
            "拆组条件",
            "默认延续当前组",
            "标题、屏边界、段高或配图变化不自动拆组",
            "不设固定组数",
            "连续内容组不等于背景生产单元",
            "验收",
        ):
            self.assertIn(term, social)

    def test_social_background_uses_conditional_continuity(self):
        social = (ROOT / "references/style/coding/scenarios/social-long-image-spec.md").read_text(encoding="utf-8")
        visual = (ROOT / "references/style/coding/systems/social-visual-system.md").read_text(encoding="utf-8")
        self.assertIn("有明确视觉与内容换挡依据时可拆分", social)
        self.assertIn("同一内容组可包含多个背景生产单元", social)
        self.assertNotIn("只有视觉条件无法兼容且局部图窗或覆盖层不能解决时才拆分", social)
        self.assertNotIn("连续内容组成员共享同一底面或背景组", visual)

    def test_css_candidate_record_is_distinct_from_implementation(self):
        visual = (ROOT / "references/style/coding/systems/social-visual-system.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("选中候选的 ID、源路径与版本仅写入短采用记录", visual)
        self.assertIn("不表示已完成实现采用", skill)
        self.assertNotIn("名称用于能力对应，不输出 ID、路径、类名或参数", visual)

    def test_asset_admission_follows_delivery_environment(self):
        mobile = (ROOT / "references/workflow/mobile-app-direct-delivery.md").read_text(encoding="utf-8")
        image_gate = (ROOT / "references/workflow/image-generation-delivery-gate.md").read_text(encoding="utf-8")
        self.assertIn("默认 Canvas", self.asset_prompt_guide)
        self.assertIn("Mobile", self.asset_prompt_guide)
        self.assertIn("present_files", self.asset_prompt_guide)
        self.assertIn("delivery_environment=mobile_direct", self.asset_prompt_guide)
        self.assertNotIn("只采用已完成画布回读、交付且检查通过的版本", self.asset_prompt_guide)
        self.assertIn("不为回读素材调用 Canvas CLI", mobile)
        self.assertIn("delivery_environment=mobile_direct", mobile)
        self.assertIn("不包含 `Device platfrom: Mobile`", image_gate)

    def test_stable_solid_background_is_scoped_to_local_information_areas(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for source in (skill, self.asset_prompt_guide):
            self.assertIn("连续背景组", source)
            self.assertIn("局部信息区", source)
        self.assertIn("整页", skill)
        self.assertIn("无变化纯色", skill)
        self.assertIn("削弱主体或版式", self.asset_prompt_guide)

    def test_editable_single_social_cover_uses_generic_ai_coding_fallback(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        clarification = (ROOT / "references/workflow/clarification-strategy.md").read_text(encoding="utf-8")
        for source in (skill, clarification):
            self.assertIn("单张社媒封面", source)
            self.assertIn("明确要求文字或设计可编辑", source)
            self.assertIn("ai-coding", source)
        self.assertIn("未命中专用品类", skill)
        self.assertIn("generic-visual-fallback.md", self.creation)
        self.assertNotIn("| 单张社媒封面（明确要求文字或设计可编辑） |", self.creation)

    def test_social_visual_limits_background_scope_without_losing_other_duties(self):
        visual = (ROOT / "references/style/coding/systems/social-visual-system.md").read_text(encoding="utf-8")
        self.assertIn("Visual 在同一字段补充背景生产单元、复用范围和换挡理由", visual)
        self.assertIn("背景变化不得改变 Spec 已确定的内容顺序和职责", visual)
        self.assertNotIn("Visual 只细化背景实现", visual)

    def test_shot_issue_and_execution_failure_have_distinct_gates(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        preview = (ROOT / "references/workflow/html-preview.md").read_text(encoding="utf-8")
        validation = (ROOT / "references/workflow/html-validation.md").read_text(encoding="utf-8")
        item_protocol = (ROOT / "references/items/HTML.md").read_text(encoding="utf-8")
        rendering = (ROOT / "references/html/coding-rendering.md").read_text(encoding="utf-8")
        joined = "\n".join((skill, preview, validation, item_protocol, rendering))
        self.assertIn("退出码 `1`", joined)
        self.assertIn("必须修正并重跑", joined)
        self.assertIn("退出码 `3`", joined)
        self.assertIn("预览未验证", joined)
        self.assertNotIn("脚本执行失败可跳过", skill)
        for source in (item_protocol, rendering):
            self.assertNotIn("预览问题不阻断", source)

    def test_all_visuals_have_visual_only_category_container_tables(self):
        visual_paths = {
            entry["visual"] for entry in self.bindings["category_refs"].values()
        }

        for relative in visual_paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            if relative.endswith('ecommerce-visual-system.md'):
                marker = '### 按内容关系选择组织方式\n'
                self.assertIn(marker, text, relative)
                section = re.split(r"\n#{1,3} ", text.split(marker, 1)[1], maxsplit=1)[0]
                self.assertIn('| 内容关系 | 先考虑的组织方式 | 何时需要可见容器 |', section)
                self.assertIn('不默认一项一卡', section)
                self.assertGreaterEqual(section.count('\n|'), 6)
                continue
            marker = "### 常用局部容器\n" if relative.endswith("resume-visual-system.md") else "### 品类常用容器表\n"
            self.assertIn(marker, text, relative)
            section = re.split(r"\n#{1,3} ", text.split(marker, 1)[1], maxsplit=1)[0]
            if relative.endswith('tri-fold-visual-system.md'):
                self.assertIn('| 容器类型 | 常见用途 | 候选入口与边界 |', section)
                self.assertIn('稳定分组成立才使用', section)
                self.assertGreaterEqual(section.count('\n|'), 6)
                continue
            self.assertIn("| 常用容器类型 | 常见用途 | 视觉选择与边界 |", section, relative)
            self.assertTrue(
                any(term in section for term in ("候选", "不是默认", "非默认")),
                relative,
            )
            self.assertGreaterEqual(section.count("\n|"), 6, relative)
            for forbidden in (
                "assets/templates/css",
                "catalog",
                "`shape.",
                "`recipe.",
                "`material.",
                "`surface.",
                "读取对应正文",
                "读取 CSS",
            ):
                self.assertNotIn(forbidden, "\n".join(line for line in section.splitlines() if line.startswith("|")), relative)

    def test_all_visuals_expose_natural_language_css_capabilities(self):
        visual_paths = {
            entry["visual"] for entry in self.bindings["category_refs"].values()
        }
        required = (
            "布局",
            "字形",
            "形状",
            "表面",
            "配色与背景",
            "作用对象与边界",
            "引用",
            "依赖",
            "参数",
            "消费者",
            "最终 HTML",
        )

        for relative in visual_paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            if relative == "references/style/coding/systems/vi-visual-system.md":
                section = text.split("## CSS 组合选择与局部补充", 1)[1].split("\n## ", 1)[0]
                for term in ("#brief-combination-match", "原子能力补足局部", "#css-recipe-binding", "最终 HTML"):
                    self.assertIn(term, section)
                self.assertLess(section.index("比较与适配组合"), section.index("原子能力补足局部"))
                continue
            marker = "### CSS 原子能力校验\n"
            self.assertIn(marker, text, relative)
            section = re.split(r"\n#{1,3} ", text.split(marker, 1)[1], maxsplit=1)[0]
            for term in required:
                self.assertIn(term, section, relative)
            for forbidden in (
                "assets/templates/css",
                "catalog",
                "`shape.",
                "`recipe.",
                ".md#",
            ):
                self.assertNotIn(forbidden, "\n".join(line for line in section.splitlines() if line.startswith("|")), relative)

    def test_all_visuals_cover_every_catalogued_layout_capability(self):
        layout_names = {
            entry["name"]
            for entry in self.css["entries"]
            if entry["id"].startswith("layout.")
        }
        self.assertTrue(
            layout_names.issuperset(
            {
                "紧凑内容",
                "宽松内容",
                "规整对齐",
                "疏朗留白",
                "错落平衡",
                "聚焦主场",
                "连续流动",
                "叠层拼贴",
                "S 形导览线",
                "横向卡片列",
                "章节眉线",
                "带引导线的图像标注",
            },
        ))
        layouts = {
            entry["id"]: entry for entry in self.css["entries"]
            if entry["id"].startswith("layout.")
        }
        self.assertIn("方格排版", layouts["layout.evidence-grid"]["tags"])
        self.assertIn("网格排版", layouts["layout.evidence-grid"]["tags"])
        self.assertIn("串页排版", layouts["layout.chapter-flow"]["tags"])
        visual_paths = {
            entry["visual"] for entry in self.bindings["category_refs"].values()
        }

        for relative in visual_paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            if relative == "references/style/coding/systems/resume-visual-system.md":
                # Resume routes to the catalog; associations live there, not in a second Visual table.
                resume_layouts = [entry for key, entry in layouts.items()
                                  if key.startswith("layout.resume-")]
                self.assertEqual(len(resume_layouts), 13)
                css_ids = {entry['id'] for entry in self.css['entries']}
                for entry in resume_layouts:
                    self.assertTrue(entry['style_affinities'])
                    self.assertTrue(entry['related_combinations'])
                    self.assertTrue(set(entry['related_combinations']) <= css_ids)
                    document = ROOT / self.css['documents'][entry['document']]['path']
                    self.assertIn('id="' + entry['anchor'] + '"', document.read_text())
                self.assertIn('../../../../assets/templates/css/catalog.json', text)
                self.assertIn('related_combinations', text)
                self.assertIn("--kind layout --artifact 简历 --layout-scope 整张单屏", text)
                self.assertNotIn("resume-visual-presets.md", text)
                continue
            if relative == "references/style/coding/systems/vi-visual-system.md":
                # VI delegates capability discovery to the public catalog; it must not duplicate all layout names.
                self.assertIn("../../../../assets/templates/css/README.md#brief-combination-match", text)
                self.assertIn("模型提出的配色、容器和构图草案可调整", text)
                self.assertIn("组件命中只代表对应范围适用", text)
                continue
            marker = "### 已有布局 CSS 能力表\n"
            self.assertIn(marker, text, relative)
            section = text.split(marker, 1)[1].split(
                "\n### CSS 原子能力校验", 1
            )[0]
            for name in {"紧凑内容", "宽松内容", "规整对齐", "疏朗留白", "错落平衡", "聚焦主场", "方格／网格排版", "串页／长页排版"}:
                self.assertIn(name, section, relative)
            self.assertIn("方格／网格排版", section, relative)
            self.assertIn("串页／长页排版", section, relative)
            for forbidden in (
                "assets/templates/css",
                "`layout.",
                ".md#",
            ):
                self.assertNotIn(forbidden, "\n".join(line for line in section.splitlines() if line.startswith("|")), relative)


if __name__ == "__main__":
    unittest.main()
