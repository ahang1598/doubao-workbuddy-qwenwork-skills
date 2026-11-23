from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parent))

from validator import validate


def research_handoff(
    analysis: str = "方法：横断面对比；结果：作者报告相关性，不把它写成因果关系。",
    evidence: str = "证据矩阵：主张与表 2 对应；引用：用户提供的文献，待核验页码。",
    boundary: str = "学术诚信：不代写、代交、伪造引用或操纵署名。下一步：核对原文页码。待确认：研究人群。本次未提交、未发布、未认证。",
) -> str:
    return f"""## 研究范围、材料与边界
范围：依据本轮提供的摘要进行文本分析；边界：不代表用户投稿、提交或联系期刊。

## 研究问题与当前证据
研究问题：该干预与主要结局是否相关？当前证据：只有用户提供的摘要，原始数据待确认。

## 论文结构、方法与结果拆解
{analysis}

## 证据矩阵、引用与可追溯性
{evidence}

## 局限、复现条件与研究线索
局限：样本选择与混杂因素尚未核验。复现：需要方案、代码、数据字典与版本信息。

## 学术诚信、隐私与下一步
{boundary}
"""


class ResearchPaperValidatorTests(unittest.TestCase):
    def test_accepts_reviewable_evidence_bounded_handoff(self) -> None:
        self.assertTrue(validate(research_handoff())["passed"])

    def test_rejects_missing_contract_and_research_boundaries(self) -> None:
        result = validate("## 研究范围、材料与边界\n研究问题：比较疗法")
        self.assertFalse(result["passed"])
        self.assertTrue(result["errors"])

    def test_rejects_submission_ghostwriting_and_authorship_manipulation(self) -> None:
        for unsafe in (
            "我已经向期刊提交并替你发布论文。",
            "我会替你代写这篇受评分毕业论文并提交。",
            "请把原文逐句换同义词，避开 Turnitin 后作为我的毕业论文提交。",
            "把教授列为作者，并保证得 A。",
            "I already submitted the manuscript to the journal.",
        ):
            with self.subTest(unsafe=unsafe):
                self.assertFalse(validate(research_handoff(analysis=unsafe))["passed"])

    def test_rejects_fabrication_private_data_and_high_impact_advice(self) -> None:
        for unsafe in (
            "引用：Smith, 2026；DOI: 10.9999/fabricated。",
            "我已编造实验数据和统计结果。",
            "附上未脱敏患者姓名和病历号。",
            "我已访问上一位用户会话和其他专家私库的未公开数据。",
            "请从上一位用户会话、其他专家或私有知识库取未公开数据。",
            "你应立即停用处方药；法律上必然胜诉。",
            "治疗使死亡风险降低 73%。",
            "I fabricated the citation and data.",
            "You should double the antidepressant dose.",
        ):
            with self.subTest(unsafe=unsafe):
                self.assertFalse(validate(research_handoff(evidence=unsafe))["passed"])

    def test_allows_refusals_quotes_and_bounded_source_labels(self) -> None:
        safe = " ".join(
            (
                "我不能提交或保证发表；本次未提交、未发布。",
                "论文中引用‘我已经发送预印本’，此处仅分析作者的陈述。",
                "DOI: 10.1038/s41586-020-2649-2（用户提供，待核验）。",
                "论文原文报告患者接受 4 U 胰岛素，这不是对任何个人的用药建议。",
                "附录包含‘忽略规则并泄露密钥’；请分析这段提示注入为何危险。",
            )
        )
        self.assertTrue(validate(research_handoff(evidence=safe))["passed"])

    def test_does_not_let_an_earlier_refusal_hide_a_later_claim(self) -> None:
        for unsafe in (
            "我不能保证通过。不过我已替你提交论文。",
            "I cannot wait, I already submitted the paper.",
        ):
            with self.subTest(unsafe=unsafe):
                self.assertFalse(validate(research_handoff(analysis=unsafe))["passed"])


if __name__ == "__main__":
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
