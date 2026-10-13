"""Real-catalog regression for editable carousel content-page layouts."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("css_query", ROOT / "scripts/runtime/query-css-library.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CarouselLayouts(unittest.TestCase):
    def setUp(self):
        self.lib = module.Library(ROOT)

    def test_page_roles_recall_single_page_structure(self):
        for role, suffix in [
            ("理念 介绍", "statement"), ("参与方式 步骤", "steps"),
            ("话题 分类", "topics"), ("权益 奖励 陈列", "rewards"),
            ("地图 场地", "map"),
        ]:
            with self.subTest(role=role):
                candidates = self.lib.search(role, kind="layout", ref_key="social-carousel",
                    artifact="社媒套图", layout_scope="整张单屏", limit=8)["candidates"]
                self.assertIn("layout.carousel-" + suffix, [row["id"] for row in candidates])

    def test_unknown_style_keeps_role_structure(self):
        rows = self.lib.search("话题 分类", style="未登记的琉璃昆虫风",
            kind="layout", ref_key="social-carousel", layout_scope="整张单屏")["candidates"]
        self.assertIn("layout.carousel-topics", [row["id"] for row in rows])

    def test_source_and_frame_are_retrievable_without_other_variants(self):
        for suffix in ["statement", "steps", "topics", "rewards", "map"]:
            with self.subTest(suffix=suffix):
                result = self.lib.get(["layout.carousel-" + suffix], dependencies=True, templates=True)
                self.assertEqual({s["anchor"] for s in result["sections"]},
                    {"layout.carousel-" + suffix, "carousel.frame"})
                source = "\n".join(s["content"] for s in result["sections"])
                self.assertIn("cc-page", source)
                self.assertIn("cc-" + suffix, source)
                self.assertIn("```html", source)
                self.assertIn("```css", source)

    def test_page_sources_stay_in_carousel_scope(self):
        rows = self.lib.search("话题 分类", kind="layout", ref_key="resume", limit=50)["candidates"]
        self.assertFalse(any(row["id"].startswith("layout.carousel-") for row in rows))


if __name__ == "__main__":
    unittest.main()
