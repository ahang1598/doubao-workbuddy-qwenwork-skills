from pathlib import Path
import re
import unittest

import yaml


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_ROOT / "SKILL.md"


class SkillPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = SKILL_MD.read_text(encoding="utf-8")
        frontmatter = re.match(
            r"^---\n(.*?)\n---",
            cls.content,
            re.DOTALL,
        ).group(1)
        cls.frontmatter = yaml.safe_load(frontmatter)

    def test_description_has_user_phrases_and_negative_boundaries(self):
        description = self.frontmatter["description"]
        for phrase in (
            "帮我核验",
            "比较欧盟法院与欧洲人权法院",
            "境外牌照需要什么条件",
            "不适用于合同审查",
            "不适用于纯翻译",
        ):
            self.assertIn(phrase, description)
        self.assertNotIn("等研究问题", description)

    def test_fixed_disclaimer_and_quick_answer_disclosure_are_inline(self):
        self.assertIn(
            "本文档由 AI 辅助生成，仅供参考，不构成正式法律意见",
            self.content,
        )
        self.assertIn("正式报告首部", self.content)
        self.assertIn("快速问答开头", self.content)

    def test_adversarial_and_illegal_requests_are_explicitly_refused(self):
        for phrase in (
            "不要免责声明",
            "假装律师",
            "100%确定",
            "伪造判例",
            "教唆违法",
        ):
            self.assertIn(phrase, self.content)

    def test_formal_output_is_text_only_and_has_table_width_rule(self):
        self.assertIn("正式输出禁止使用 emoji", self.content)
        self.assertIn("表格不得超出页面内容区", self.content)

    def test_risk_method_and_actionable_advice_are_required(self):
        self.assertIn("影响 × 发生可能性", self.content)
        self.assertIn("民事、行政、刑事", self.content)
        self.assertIn("责任人", self.content)
        self.assertIn("完成时限", self.content)

    def test_route_truth_file_is_mandatory(self):
        self.assertIn("references/research-routing-rules.md", self.content)
        self.assertIn("必须先读取", self.content)


if __name__ == "__main__":
    unittest.main()
