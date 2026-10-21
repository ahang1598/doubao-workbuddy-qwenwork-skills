#!/usr/bin/env python3
"""Guard the HTML production order and natural-language Brief boundary."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HtmlProductionSequenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        start = cls.skill.index("#### HTML 路线唯一生产顺序")
        end = cls.skill.index("#### 开工前上下文收集", start)
        cls.sequence = cls.skill[start:end]
        cls.kv = (ROOT / "references/workflow/visual-kv-clarification.md").read_text(encoding="utf-8")
        cls.ai = (ROOT / "references/workflow/creation/ai-coding.md").read_text(encoding="utf-8")
        cls.pure_image = (ROOT / "references/workflow/creation/pure-image.md").read_text(encoding="utf-8")
        cls.clarification = (ROOT / "references/workflow/clarification-strategy.md").read_text(encoding="utf-8")
        cls.carousel = (ROOT / "references/style/coding/scenarios/social-carousel-spec.md").read_text(encoding="utf-8")
        cls.announcement = (ROOT / "references/style/coding/scenarios/announcement-poster-spec.md").read_text(encoding="utf-8")
        cls.announcement_visual = (ROOT / "references/style/coding/systems/announcement-poster-visual-system.md").read_text(encoding="utf-8")
        cls.asset_prompt = (ROOT / "references/style/coding/ai-coding/asset-prompt-guide.md").read_text(encoding="utf-8")
        cls.composition = (ROOT / "references/style/shared/composition-principles.md").read_text(encoding="utf-8")
        cls.poster = (ROOT / "references/style/pure-image/media/media-poster.md").read_text(encoding="utf-8")
        cls.menu_visual = (ROOT / "references/style/coding/systems/menu-visual-system.md").read_text(encoding="utf-8")
        cls.ecommerce_spec = (ROOT / "references/style/coding/scenarios/ecommerce-detail-page-spec.md").read_text(encoding="utf-8")
        cls.ecommerce_visual = (ROOT / "references/style/coding/systems/ecommerce-visual-system.md").read_text(encoding="utf-8")
        cls.ref_bindings = json.loads((ROOT / "assets/templates/ref-bindings.json").read_text(encoding="utf-8"))
        cls.css_catalog = json.loads((ROOT / "assets/templates/css/catalog.json").read_text(encoding="utf-8"))
        cls.brief = (ROOT / "example/brief.md").read_text(encoding="utf-8")
        cls.manifest = (ROOT / "example/asset-manifest.md").read_text(encoding="utf-8")
        cls.html = (ROOT / "references/html/coding-rendering.md").read_text(encoding="utf-8")
        cls.html_item = (ROOT / "references/items/HTML.md").read_text(encoding="utf-8")
        cls.preview = (ROOT / "references/workflow/html-preview.md").read_text(encoding="utf-8")
        cls.validation = (ROOT / "references/workflow/validation.md").read_text(encoding="utf-8")
        cls.fonts = (ROOT / "references/rendering/font-family-library.md").read_text(encoding="utf-8")
        cls.css = (ROOT / "assets/templates/css/README.md").read_text(encoding="utf-8")

    def test_unique_order(self) -> None:
        terms = (
            "获取需求并路由",
            "创建 Brief",
            "按需澄清",
            "应用品类 Ref、完成视觉草案并校验 CSS 能力",
            "执行适用品类的 KV 展示确认并冻结最终 Brief",
            "按路线准备实现输入",
            "AI + Coding 生产并准出正式图片",
            "编译完整 HTML",
            "页面自检",
            "修正与交付闭环",
        )
        positions = [self.sequence.index(term) for term in terms]
        self.assertEqual(positions, sorted(positions))

    def test_ref_reading_does_not_depend_on_brief_creation(self) -> None:
        for doc in (self.skill, self.ai, self.pure_image):
            for obsolete in ("读取任何品类 Spec、Visual System 或 media ref 前",
                             "不得读取品类 Ref", "不得等待品类 Ref 读完才创建",
                             "在读取品类 Ref 前明确主题和商品"):
                self.assertNotIn(obsolete, doc)
        self.assertIn("完整读取已命中的任务策略 Ref", self.sequence)
        self.assertIn("路由尚未确定时", self.skill)

    def test_ecommerce_keeps_css_adoption_record_in_brief(self) -> None:
        self.assertNotIn("Brief 只写自然语言关系，不写 ID", self.ecommerce_visual)
        self.assertNotIn("不输出 ID、路径、类名或参数", self.ecommerce_visual)
        self.assertIn("Brief 记录选中 ID、源路径与版本、范围和映射", self.ecommerce_visual)
        self.assertIn("既有短采用记录", self.ecommerce_visual)

    def test_logo_transparency_and_monochrome_have_separate_steps(self) -> None:
        logo = (ROOT / "references/style/pure-image/scenarios/brand-logo-system.md").read_text(encoding="utf-8")
        self.assertNotIn("所有单色、反白、透明底", logo)
        self.assertNotIn("再进入品牌色和 Mockup", logo)
        self.assertNotIn("Logo 仍先通过黑白结构验证", logo)
        self.assertIn("透明通道和边缘", logo)
        self.assertIn("已有合格透明资产直接复用", logo)
        self.assertIn("不通过重新生图或 `image_edit` 模拟透明底", logo)
        start = logo.index("### 默认交付依赖顺序")
        end = logo.index("### 一致性与多样性", start)
        production = logo[start:end]
        steps = ("生成平面彩色主标", "生成黑色单色版", "生成白色反白版", "专门去底", "应用预览")
        positions = [production.index(step) for step in steps]
        self.assertEqual(positions, sorted(positions))

    def test_kv_is_retained_before_asset_manifest(self) -> None:
        self.assertTrue(self.kv.startswith("# 视觉 KV 澄清"))
        self.assertIn("完整候选 Brief 之后、最终 Brief 冻结和 正式素材清单之前", self.kv)
        self.assertIn("视觉澄清", self.ai)
        self.assertIn("KV 是唯一允许早于正式素材清单的图像生成例外", self.sequence)
        self.assertNotIn("# 完整 Brief／素材清单 后的视觉 KV 验证", self.kv)

    def test_target_categories_require_explicit_kv_approval(self) -> None:
        self.assertIn(
            "由品类和操作类型触发，不以 Agent 判断方向是否存在分歧为条件",
            self.sequence,
        )
        self.assertIn(
            "“直接开始”“其他你决定”以及普通参考图或已有素材都不构成确认依据",
            self.skill,
        )
        self.assertIn("前置文字澄清只处理", self.skill)
        self.assertIn("不替代适用品类的 KV 展示确认", self.skill)
        self.assertNotIn("按需执行 KV 视觉澄清并冻结最终 Brief", self.sequence)
        self.assertIn("当前 KV 版本已取得可核验的用户明确批准", self.ai)
        self.assertIn("否则不得进入阶段 4", self.ai)
        self.assertNotIn("它只澄清候选 Brief 中尚有分歧的视觉方向", self.ai)
        self.assertNotIn("| 3. 按需 KV 视觉澄清与最终 Brief 冻结 |", self.ai)

    def test_brief_manifest_and_html_have_single_responsibilities(self) -> None:
        self.assertIn("纯 Coding 由冻结 Brief 直接进入 HTML", self.brief)
        self.assertIn("AI + Coding 先建立", self.brief)
        self.assertIn("不保存 DOM 坐标、字号、颜色、CSS 参数、模板绑定或页面几何", self.manifest)
        self.assertIn("HTML 是坐标、层级、字体、样式和资产消费位置的唯一实现事实源", self.sequence)
        self.assertNotIn("Design IR", "\n".join((self.skill, self.ai, self.kv, self.manifest)))
        self.assertNotIn("planned 最终 HTML", "\n".join((self.skill, self.ai, self.kv, self.manifest)))
        self.assertNotIn("ready HTML", "\n".join((self.skill, self.ai, self.kv, self.manifest)))

    def test_brief_is_not_a_parameter_contract(self) -> None:
        self.assertIn("Brief 始终使用自然语言", self.skill)
        self.assertNotIn("在 Brief 指出组合 ID", self.css)
        self.assertNotIn("在素材清单 指出组合 ID", self.css)
        self.assertIn("直接落实到源码", self.css)
        self.assertIn("最终 Brief 写适配后的可见关系及短 CSS 采用记录，不复制技术参数", self.skill)
        terminology = "\n".join((self.skill, self.ai, self.kv, self.manifest))
        self.assertNotIn("编译 最终 HTML", terminology)
        self.assertNotIn("最终 HTML 编译", terminology)
        self.assertIn("不自动转换成另一份全量参数文件", self.brief)

    def test_css_capability_check_precedes_html_implementation_read(self) -> None:
        visual = self.sequence.index("完成视觉草案并校验 CSS 能力")
        frozen = self.sequence.index("冻结最终 Brief")
        implementation = self.sequence.index("编译完整 HTML")
        self.assertLess(visual, frozen)
        self.assertLess(frozen, implementation)
        self.assertIn("query-css-library.py search", self.css)
        self.assertIn("query-css-library.py describe", self.css)
        self.assertIn("get <ID> --dependencies", self.css)

    def test_coding_text_stays_editable_html(self) -> None:
        for term in ("真实 HTML 文本节点", "可编辑", "text-shadow", "-webkit-text-stroke", "background-clip"):
            self.assertIn(term, self.html)
        self.assertIn("普通 `<style>`", self.html)
        self.assertIn("Web 字体契约", self.fonts)
        self.assertIn("可加载的外部样式表", self.fonts)

    def test_social_carousel_route_and_reference_boundaries(self) -> None:
        carousel_rows = [line for line in self.skill.splitlines()
                         if line.startswith("| 社媒套图／轮播图")]
        self.assertTrue(carousel_rows)
        routes = "\n".join(carousel_rows)
        self.assertIn("pure-image", routes)
        self.assertIn("ai-coding", routes)
        self.assertIn("可编辑", routes)
        self.assertIn("pure-image-sequence.md", self.pure_image)
        self.assertIn("media-xiaohongshu.md", self.pure_image)
        for doc in (self.skill, self.ai, self.carousel):
            self.assertNotIn("cover_final_image", doc)
            self.assertNotIn("套图首页完整终图指导", doc)
        self.assertIn("HTML 原生文字", self.carousel)

    def test_runtime_capability_preflight_precedes_workspace_and_production(self) -> None:
        preflight = self.skill.index("### 0. 正式生产能力预检")
        workspace = self.skill.index("### 1. 绑定 Workspace")
        self.assertLess(preflight, workspace)
        for term in ("design-cli", "present_files", "FileBatchUpload", "shot.py", "RUNTIME_CAPABILITY_MISSING"):
            self.assertIn(term, self.skill[preflight:workspace])

    def test_announcement_remains_ai_coding_exception(self) -> None:
        family = "通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图"
        self.assertIn(family, self.skill)
        self.assertIn("ai-coding（可编辑设计）", next(line for line in self.skill.splitlines() if line.startswith(f"| {family}")))
        self.assertIn("底图已有不改变 ai-coding 路线", self.skill)
        self.assertIn("announcement-poster-visual-system.md", next(line for line in self.ai.splitlines() if line.startswith(f"| {family} |")))
        self.assertIn("传播型成果海报、销售喜报、成交捷报", self.skill)
        self.assertIn("以图表分析为主体的销售／赛事数据战报 | pure-coding", self.skill)
        self.assertNotIn("所有海报和单张社媒封面走纯生图", self.clarification)
        self.assertIn("单张传播型成果战报属于公告海报", self.clarification)
        self.assertIn('<a id="announcement-hybrid"></a>', self.announcement)

    def test_announcement_backgrounds_do_not_infer_radiating_light(self) -> None:
        self.assertIn("放射构图不等于放射性光线", self.composition)
        self.assertIn("放射构图不等于放射性光线", self.announcement_visual)
        self.assertIn("庆典、隆重、红金、金色、丝绸／绸缎", self.asset_prompt)
        self.assertIn("通知／公告／喜报／捷报／成果战报／邀请函／节庆贺图的显式纯生图覆盖例外", self.poster)
        overrides = self.ref_bindings["css"]["entry_overrides"]
        for ref_id in (
            "combination.clear-light",
            "surface.diffuse-field",
            "palette.neon-cyan",
            "surface.screen-grain",
            "surface.neon-edge",
            "shape.sparkle",
            "combination.urban-pink-cinema",
            "combination.urban-blue-concert",
            "combination.osmanthus-poetic-light",
        ):
            self.assertNotIn("announcement-poster", overrides[ref_id])

    def test_menu_visual_defines_image_composition_by_menu_type(self) -> None:
        self.assertIn("## 各类型菜单的图文组合与配图手段", self.menu_visual)
        for term in (
            "一级主图",
            "主图、分类图与条目图按实际职责选用",
            "不设统一面积比例或数量配额",
            "整盘／整杯去底图",
            "矩形摄影窗",
            "圆形／椭圆蒙版",
            "透明渐隐／羽化",
            "菜品与背景的联动",
            "共享台面／场景",
            "色块承托／跨栏出画",
            "自然餐桌与轻食",
            "墙面与灯箱",
            "每页必须写入 Brief 的配图编排",
        ):
            self.assertIn(term, self.menu_visual)
        self.assertIn("三个等宽分类顶图＋下方纯文字三栏＋大量微小圆形菜图", self.menu_visual)
        self.assertNotIn("至少一张大图带动两到四张辅图", self.menu_visual)
        self.assertNotIn("主图约占页面 25%–40%", self.menu_visual)

    def test_every_category_visual_writes_complete_brief_dimensions(self) -> None:
        visual_paths = {
            value["visual"]
            for value in self.ref_bindings["category_refs"].values()
        }
        for relative_path in visual_paths:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            with self.subTest(visual=relative_path):
                self.assertIn("决策优先级", content)
                self.assertIn("视觉命题", content)
                self.assertIn("素材生产意图", content)
                self.assertIn("验收", content)
                self.assertIn("视觉效果生产规范", content)
                self.assertIn("视觉效果验收规范", content)

    def test_every_category_spec_writes_content_production_and_acceptance(self) -> None:
        spec_paths = {
            value["spec"]
            for value in self.ref_bindings["category_refs"].values()
        }
        for relative_path in spec_paths:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            with self.subTest(spec=relative_path):
                self.assertIn("内容结构生产规范", content)
                self.assertIn("内容结构验收规范", content)

    def test_brief_and_manifest_have_distinct_asset_responsibilities(self) -> None:
        brief = (ROOT / "example/brief.md").read_text(encoding="utf-8")
        self.assertIn("素材生产意图／使用说明", brief)
        self.assertIn("Prompt 只在 manifest 维护", brief)
        self.assertIn("Brief 不随生产过程复制这些事实", brief)

    def test_category_visuals_do_not_default_to_rounded_card_walls(self) -> None:
        visual_paths = {
            value["visual"]
            for value in self.ref_bindings["category_refs"].values()
        }
        for relative_path in visual_paths:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            with self.subTest(visual=relative_path):
                self.assertIn("## 容器与开放排版视觉决策", content)
                self.assertTrue("中性圆角容器（非默认）" in content or "分组、网格对齐和内容分段都不自动意味着加底板" in content)
                self.assertNotIn("## 逐屏卡片容器视觉效果", content)

    def test_css_catalog_contains_planar_skeuomorphic_container_atoms(self) -> None:
        ids = {entry["id"] for entry in self.css_catalog["entries"]}
        self.assertIn("shape.scroll-sheet", ids)
        self.assertIn("shape.archival-sheet", ids)
        composition = (ROOT / "references/style/coding/composition-layout.md").read_text(encoding="utf-8")
        self.assertIn("### 容器视觉语法：开放排版优先，语义容器按需", composition)
        self.assertIn("不因缺少现成模板退化为默认圆角卡", composition)

    def test_ecommerce_requires_visual_evidence_rhythm_and_separate_text_default(self) -> None:
        self.assertIn("### 详情页视觉证据节奏合同", self.ecommerce_spec)
        for term in (
            "Hero 视觉主场",
            "图片层级依据",
            "证据形态轮换",
            "构图与辅图依据",
            "参数／规格的决策职责",
            "无字主图＋",
        ):
            self.assertIn(term, self.ecommerce_spec)
        self.assertIn("## 详情页反模板构图门禁", self.ecommerce_visual)
        self.assertNotIn("默认纯 DIT", self.ecommerce_spec)
        self.assertNotIn("默认 DIT", self.ecommerce_visual)
        self.assertIn("无字主图＋", self.ecommerce_visual)
        self.assertIn("### Hero 冲击力构图：主体与场景方案", self.ecommerce_visual)
        self.assertIn("按需一体生成", self.ecommerce_visual)
        self.assertIn("首屏遵循 Spec 的模式选择", self.ecommerce_visual)
        for content in (self.ecommerce_spec, self.ecommerce_visual):
            self.assertNotIn("整页至少两处", content)
            self.assertTrue(
                "不继承 Hero 或整图背景高度" in content
                or "不继承 Hero 比例" in content
            )

    def test_ecommerce_text_size_uses_final_reading_width(self) -> None:
        html_validation = (ROOT / "references/workflow/html-validation.md").read_text(encoding="utf-8")
        section = self.ecommerce_spec.split("### 阅读尺寸与字号门槛", 1)[1].split("### 2. 正式 Hero", 1)[0]
        self.assertIn("仅适用于电商详情页（含作为详情页交付的连续长图）", section)
        for term in ("390px", "13px", "12px", "源 CSS 字号 × 实际显示宽度 ÷ 源 CSS 画布宽度", "嵌入图片", "未验证"):
            self.assertTrue(term in section, term)
        self.assertIn("仅电商详情页", html_validation)
        self.assertIn("图内文字", html_validation)
        self.assertIn("任何内容文字低于 13px", html_validation)

    def test_ecommerce_narrative_derives_optional_breathers(self) -> None:
        for term in (
            "透气屏是可选屏型",
            "删除、合并或拆分",
            "购买问题、结论、证据、入口和出口",
        ):
            self.assertIn(term, self.ecommerce_spec)
        self.assertIn("背景组可以跨越多个内容屏", self.ecommerce_visual)
        for term in (
            "节奏映射：",
            "开场屏+共情屏+换气屏+解决屏+收束屏",
            "面料细节→换气",
        ):
            self.assertNotIn(term, self.ecommerce_spec)
        self.assertNotIn("中间穿插商品大图或透气图", self.ecommerce_visual)
        self.assertNotIn("屏数、换气位置", self.ai)

    def test_ecommerce_brief_has_background_transition_writeback(self) -> None:
        field = "背景连续性与衔接"
        self.assertIn(field, self.ecommerce_spec)
        self.assertIn(f"Brief 的“{field}”", self.ecommerce_visual)
        for term in ("起止屏", "连续或硬切", "渐隐对象", "安全空场"):
            self.assertIn(term, self.ecommerce_spec)
        self.assertIn("具体长度、色标、透明度和 CSS 参数", self.ecommerce_spec)

    def test_main_route_stable_anchors_exist(self) -> None:
        self.assertIn('<a id="asset-responsibility"></a>', self.ai)
        self.assertIn('<a id="background-visual-responsibility"></a>', self.ai)
        self.assertIn('<a id="html-fixed-canvas-delivery"></a>', self.html)
        for anchor in ("#asset-responsibility", "#announcement-hybrid", "#html-fixed-canvas-delivery", "#background-visual-responsibility"):
            self.assertIn(anchor, self.skill)

    def test_html_preview_and_workspace_card_delivery_contract(self) -> None:
        for text in (self.skill, self.html, self.html_item, self.preview, self.validation, self.ai):
            if text == self.preview:
                self.assertIn("workspace_id?item_id=xxx 卡片", text)
            else:
                self.assertIn("画布卡片", text)
        self.assertIn("不使用 present_files、不创建 IMAGE Item", self.preview)
        self.assertIn("CDN", self.html_item)
        self.assertIn("Markdown", self.html_item)
        self.assertIn("?item_id=", self.html_item)
        self.assertNotIn("预览截图只是内部视觉验收证据", self.preview)


if __name__ == "__main__":
    unittest.main()
