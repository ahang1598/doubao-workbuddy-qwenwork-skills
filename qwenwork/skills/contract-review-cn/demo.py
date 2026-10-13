#!/usr/bin/env python3
"""
中文合同审查技能 - 演示脚本
无需API密钥即可演示功能
"""

import sys
from pathlib import Path

# 添加scripts目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from scripts.pdf_parser import PDFParser
from scripts.word_parser import WordParser


def demo_parser(file_path, file_type):
    """演示文件解析功能"""
    print(f"\n{'=' * 60}")
    print(f"演示：解析 {file_type} 文件")
    print(f"文件路径: {file_path}")
    print(f"{'=' * 60}\n")

    try:
        if file_type == 'pdf':
            parser = PDFParser()
            text = parser.extract_text_from_pdf(Path(file_path), output_text=True)
            sections = parser.extract_sections(text)
        elif file_type == 'word':
            parser = WordParser()
            text = parser.extract_text_from_word(Path(file_path), output_text=True)
            sections = parser.extract_sections(text)
        elif file_type == 'txt':
            text = Path(file_path).read_text(encoding='utf-8')
            print(f"成功读取TXT文件，字符数: {len(text)}")

            # 简单解析
            sections = {
                'title': text.split('\n')[0] if text else '未知合同',
                'parties': '从文档中提取',
                'obligations': text[:200] + '...' if len(text) > 200 else text,
                'payment_terms': '付款方式未明确',
                'liabilities': '违约责任未明确',
                'termination': '终止条款未明确',
                'dispute_resolution': '争议解决方式未明确'
            }

        print("\n提取的合同条款:")
        print("-" * 60)
        for section_name, section_text in sections.items():
            if section_text:
                print(f"\n【{section_name}】")
                preview = section_text[:200] + '...' if len(str(section_text)) > 200 else section_text
                print(preview)

        return True

    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_analyzer_structure():
    """演示分析器结构"""
    print(f"\n{'=' * 60}")
    print(f"演示：分析器架构")
    print(f"{'=' * 60}\n")

    print("分析器主要功能:")
    print("1. 文件解析 - 支持PDF、Word、TXT")
    print("2. 风险识别 - 调用AI模型分析")
    print("3. 修订建议 - 提供具体修改建议")
    print("4. 三栏对照表 - 生成原文/建议/原因对照")
    print("5. 报告生成 - 输出Markdown格式报告")

    print("\n核心模块:")
    print("- contract_analyzer.py - 主分析器")
    print("- pdf_parser.py - PDF解析器")
    print("- word_parser.py - Word解析器")

    return True


def main():
    """主函数"""
    print("=" * 60)
    print("中文合同审查技能 - 功能演示")
    print("=" * 60)

    # 1. 演示分析器结构
    demo_analyzer_structure()

    # 2. 选择要演示的文件
    print("\n请选择要演示的文件类型:")
    print("1. TXT样本文件 (test_sample.txt)")
    print("2. PDF样本文件 (sample_contract.pdf)")
    print("3. 退出")

    try:
        choice = input("\n请输入选择 (1-3): ").strip()

        if choice == '1':
            file_path = Path(__file__).parent / 'examples' / 'test_sample.txt'
            if file_path.exists():
                demo_parser(str(file_path), 'txt')
            else:
                print(f"错误: 文件不存在 - {file_path}")

        elif choice == '2':
            file_path = Path(__file__).parent / 'examples' / 'sample_contract.pdf'
            if file_path.exists():
                demo_parser(str(file_path), 'pdf')
            else:
                print(f"错误: 文件不存在 - {file_path}")

        elif choice == '3':
            print("\n演示结束")
            return

        else:
            print("无效选择")

    except KeyboardInterrupt:
        print("\n\n演示结束")
    except Exception as e:
        print(f"\n错误: {str(e)}")


if __name__ == '__main__':
    main()
