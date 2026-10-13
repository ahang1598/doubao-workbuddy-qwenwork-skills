#!/usr/bin/env python3
"""
中文合同审查技能 - 合同分析器
支持PDF、Word、TXT等格式的合同审查
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import traceback

# 添加scripts目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from pdf_parser import PDFParser
from word_parser import WordParser


class ContractAnalyzer:
    """合同审查分析器"""

    def __init__(self, config: Dict):
        self.config = config
        self.pdf_parser = PDFParser()
        self.word_parser = WordParser()

    def parse_contract(self, file_path: str) -> str:
        """
        解析合同文件，提取文本内容

        Args:
            file_path: 合同文件路径

        Returns:
            合同文本内容
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"合同文件不存在: {file_path}")

        # 根据文件扩展名选择解析器
        if file_path.suffix.lower() in ['.pdf']:
            return self.pdf_parser.parse(file_path)
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            return self.word_parser.parse(file_path)
        elif file_path.suffix.lower() in ['.txt']:
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

    def _parse_txt(self, file_path: Path) -> str:
        """解析TXT文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()

    def analyze_contract(self, contract_text: str, file_path: Optional[str] = None) -> Dict:
        """
        分析合同内容，识别风险和提供修订建议

        Args:
            contract_text: 合同文本内容
            file_path: 原始文件路径（用于生成引用）

        Returns:
            包含审查结果的字典
        """
        focus_areas = self.config.get('focus_areas', [
            'payment_terms',
            'acceptance_standards',
            'breach_liability',
            'intellectual_property',
            'confidentiality',
            'dispute_resolution',
            'governing_courts'
        ])

        # 构建分析提示词
        prompt = self._build_prompt(contract_text, focus_areas)

        # 调用AI模型进行分析
        analysis_result = self._call_ai_model(prompt)

        # 提取风险点
        risks = self._extract_risks(analysis_result)

        # 生成修订建议和对照表
        revisions = self._generate_revisions(analysis_result, risks)

        return {
            'file_path': file_path,
            'analysis': analysis_result,
            'risks': risks,
            'revisions': revisions,
            'config': self.config
        }

    def _build_prompt(self, contract_text: str, focus_areas: List[str]) -> str:
        """构建分析提示词"""
        template_path = SCRIPT_DIR / self.config.get('contract_prompt_file', 'templates/review_prompt.txt')

        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        else:
            prompt_template = """你是一位专业的中国合同审查专家。请审查以下合同：

{contract_text}

重点审查以下领域：
{focus_areas}

请按以下格式输出：
1. 风险摘要
2. 修订建议
3. 三栏对照表（原文 | 建议修改 | 修改原因）"""

        focus_areas_text = '\n'.join(f'- {area}' for area in focus_areas)

        return prompt_template.format(
            contract_text=contract_text,
            focus_areas=focus_areas_text
        )

    def _call_ai_model(self, prompt: str) -> str:
        """
        调用AI模型进行分析

        Args:
            prompt: 分析提示词

        Returns:
            AI模型的回复
        """
        try:
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage

            llm = ChatOpenAI(
                model=self.config.get('model', 'zai/glm-4.7-flash'),
                temperature=self.config.get('temperature', 0.3),
                max_tokens=self.config.get('max_tokens', 4096)
            )

            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content

        except ImportError:
            raise ImportError("未安装langchain-openai，请先运行: pip install langchain-openai")
        except Exception as e:
            raise Exception(f"调用AI模型失败: {str(e)}")

    def _extract_risks(self, analysis: str) -> List[Dict]:
        """从分析结果中提取风险点"""
        # 这里可以使用更复杂的解析逻辑
        # 简化版：返回从分析结果中识别的段落
        lines = analysis.split('\n')
        risks = []

        for line in lines:
            if '风险' in line or 'Risk' in line:
                risks.append({
                    'level': '中',
                    'description': line.strip()
                })

        # 如果没有明确识别到风险，返回全部内容
        if not risks:
            return [{
                'level': '低',
                'description': '未发现明显风险，但建议仍进行详细审查'
            }]

        return risks

    def _generate_revisions(self, analysis: str, risks: List[Dict]) -> List[Dict]:
        """生成修订建议和对照表"""
        # 从分析结果中提取三栏对照表
        revisions = []

        # 简化版：基于风险点生成修订建议
        for risk in risks:
            revisions.append({
                'original_text': '合同原文待提取',
                'suggested_revision': '请根据AI分析的修订建议进行修改',
                'reason': risk.get('description', '风险点')
            })

        return revisions

    def generate_review_report(self, analysis: str, risks: List[Dict], revisions: List[Dict]) -> str:
        """
        生成审查报告（Markdown格式）

        Args:
            analysis: AI分析结果
            risks: 风险列表
            revisions: 修订建议列表

        Returns:
            审查报告的Markdown文本
        """
        report = f"""# 中文合同审查报告

## 风险摘要

{analysis.split('## 修订')[0] if '## 修订' in analysis else analysis}

## 修订建议

{analysis.split('## 三栏对照')[0] if '## 三栏对照' in analysis else '请查看下方的三栏对照表'}

## 三栏对照表

| 原文 | 建议修改 | 修改原因 |

"""

        for rev in revisions[:20]:  # 最多显示20条
            report += f"| {rev.get('original_text', 'N/A')}\n"
            report += f"| {rev.get('suggested_revision', 'N/A')}\n"
            report += f"| {rev.get('reason', 'N/A')}\n\n"

        return report

    def analyze_file(self, file_path: str) -> str:
        """
        分析合同文件，返回审查报告

        Args:
            file_path: 合同文件路径

        Returns:
            审查报告的Markdown文本
        """
        # 解析合同
        contract_text = self.parse_contract(file_path)

        # 分析合同
        result = self.analyze_contract(contract_text, file_path)

        # 生成报告
        report = self.generate_review_report(
            result['analysis'],
            result['risks'],
            result['revisions']
        )

        return report


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='中文合同审查工具')
    parser.add_argument('file', help='合同文件路径（支持PDF、Word、TXT）')
    parser.add_argument('--config', help='配置文件路径', default='config.example.json')
    parser.add_argument('--output', help='输出文件路径（默认：合同名_review.md）')
    parser.add_argument('--show-only', action='store_true', help='只显示报告，不保存文件')

    args = parser.parse_args()

    # 加载配置
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}

    # 创建分析器
    analyzer = ContractAnalyzer(config)

    # 分析合同
    try:
        print(f"正在分析合同文件: {args.file}")
        report = analyzer.analyze_file(args.file)

        # 输出报告
        if args.show_only:
            print("\n" + "=" * 50)
            print(report)
            print("=" * 50)
        else:
            output_path = args.output or Path(args.file).stem + '_review.md'
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n审查报告已保存至: {output_path}")

    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
