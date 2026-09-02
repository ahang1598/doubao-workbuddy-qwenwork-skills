#!/usr/bin/env python3
"""
Step 2 门禁检查 — 翻译质量检查

Usage:
    python check_step2_translation.py /home/coder/project/replication/report-replication/{report_id}

检查项：
    1. full_translation.md 是否存在
    2. 是否为中文翻译（不是英文原文提取）
    3. 是否保留了原文结构（页码/章节锚点）
    4. 文件大小是否合理（不能太短）

Exit codes:
    0 — 通过
    1 — 存在错误
"""

import sys
import os
import re
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def check_translation(project_dir):
    errors = []
    warnings = []
    infos = []

    trans_path = Path(project_dir) / "01_translation" / "full_translation.md"

    print("=" * 70)
    print("Step 2 门禁检查 — 翻译质量")
    print("=" * 70)

    # 1. 文件存在性
    if not trans_path.exists():
        errors.append("[FAIL] 01_translation/full_translation.md 不存在")
        print_summary(errors, warnings, infos)
        return 1
    print("[PASS] 翻译文件存在")

    with open(trans_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    total_chars = len(content)
    total_lines = len(lines)

    # 2. 文件大小检查
    if total_chars < 5000:
        errors.append(f"[FAIL] 翻译文件过短 ({total_chars} 字符)，疑似未完整翻译")
    else:
        print(f"[PASS] 翻译文件长度: {total_chars} 字符, {total_lines} 行")

    # 3. 中文比例检查（核心门禁）
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    total_text_chars = len(re.findall(r'[a-zA-Z\u4e00-\u9fff]', content))

    if total_text_chars == 0:
        chinese_ratio = 0
    else:
        chinese_ratio = chinese_chars / total_text_chars

    print(f"[INFO] 中文字符: {chinese_chars}, 中英文字符总计: {total_text_chars}")
    print(f"[INFO] 中文占比: {chinese_ratio:.1%}")

    if chinese_ratio < 0.3:
        errors.append(
            f"[FAIL] 中文占比仅 {chinese_ratio:.1%}，疑似未翻译（要求是中文翻译，"
            f"不是英文原文提取！）。翻译文件中必须有大量中文字符。"
        )
    elif chinese_ratio < 0.5:
        warnings.append(
            f"[WARN] 中文占比 {chinese_ratio:.1%}，可能翻译不完整或保留了大量英文"
        )
    else:
        print(f"[PASS] 中文占比 {chinese_ratio:.1%}，确认为中文翻译")

    # 4. 检查是否有"待核验"标记（诚实性）
    uncertain_count = content.count("待核验") + content.count("[待核验]")
    if uncertain_count > 0:
        print(f"[INFO] 发现 {uncertain_count} 处「待核验」标记（诚实性良好）")
    else:
        infos.append("未找到「待核验」标记，建议对低置信度区域进行标注")

    # 5. 检查是否包含常见论文结构关键词（中文）
    chinese_structure_keywords = [
        "摘要", "引言", "文献综述", "数据", "方法", "模型",
        "实证", "结果", "结论", "参考文献", "附录", "表格", "图"
    ]
    found_keywords = [kw for kw in chinese_structure_keywords if kw in content]
    if len(found_keywords) >= 3:
        print(f"[PASS] 发现 {len(found_keywords)} 个中文论文结构关键词: {found_keywords}")
    else:
        warnings.append(
            f"[WARN] 仅发现 {len(found_keywords)} 个中文结构关键词，"
            f"可能未保留原文结构"
        )

    # 6. 检查是否有页码或章节锚点
    has_pages = bool(re.search(r'---\s*Page\s*\d+\s*---', content)) or \
                bool(re.search(r'#+\s+\d+', content))
    if has_pages:
        print("[PASS] 发现页码/章节锚点，原文结构已保留")
    else:
        warnings.append("[WARN] 未发现页码或章节锚点，建议保留原文结构")

    print_summary(errors, warnings, infos)
    return 1 if errors else 0


def print_summary(errors, warnings, infos):
    print("\n" + "=" * 70)
    print("检查汇总")
    print("=" * 70)
    for e in errors:
        print(e)
    for w in warnings:
        print(w)
    for i in infos:
        print(i)

    print(f"\n错误: {len(errors)}, 警告: {len(warnings)}, 信息: {len(infos)}")
    if errors:
        print("【结果】未通过 — 翻译不符合要求。必须修复后重新检查。")
    elif warnings:
        print("【结果】有条件通过 — 建议修复警告项。")
    else:
        print("【结果】通过 — 翻译质量合格。")


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_step2_translation.py /home/coder/project/replication/report-replication/{report_id}")
        sys.exit(1)

    project_dir = sys.argv[1]
    if not os.path.exists(project_dir):
        print(f"错误: 目录不存在: {project_dir}")
        sys.exit(1)

    exit_code = check_translation(project_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
