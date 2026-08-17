#!/usr/bin/env python3
"""
将裁判文书内容转换为结构化 Markdown 文件

用法：
    python convert_to_md.py --case-no "(2023) 京 01 民初 1234 号" \
                           --court "北京市第一中级人民法院" \
                           --date "2023-06-15" \
                           --parties "原告：张三；被告：李四" \
                           --cause "劳动争议" \
                           --content "完整文书内容..." \
                           --output-dir "/path/to/output"
"""

import argparse
import os
import re
import sys
from datetime import datetime


def sanitize_filename(case_no: str) -> str:
    """将案号转换为安全的文件名"""
    # 替换特殊字符为下划线
    # 含裁判文书网案号常用全角括号（），与半角 () 一并替换为下划线，保证跨平台文件名安全
    sanitized = re.sub(r'[\\/*?:"<>|()\s\uFF08\uFF09]', '_', case_no)
    # 移除连续的下划线
    sanitized = re.sub(r'_+', '_', sanitized)
    # 移除首尾下划线
    sanitized = sanitized.strip('_')
    return sanitized


def convert_to_markdown(
    case_no: str,
    court: str,
    date: str,
    parties: str,
    cause: str,
    content: str,
    judgment_result: str = "",
    dispute_focus: str = "",
    legal_basis: str = ""
) -> str:
    """
    将案例信息转换为 Markdown 格式

    Args:
        case_no: 案号
        court: 审理法院
        date: 判决日期
        parties: 当事人信息
        cause: 案由
        content: 完整文书内容
        judgment_result: 裁判结果
        dispute_focus: 争议焦点
        legal_basis: 援引法条

    Returns:
        Markdown 格式的字符串
    """
    md_lines = []

    # 标题
    md_lines.append(f"# 案例详情：{case_no}")
    md_lines.append("")

    # 基本信息表格
    md_lines.append("## 基本信息")
    md_lines.append("")
    md_lines.append("| 项目 | 内容 |")
    md_lines.append("|------|------|")
    md_lines.append(f"| **案号** | {case_no} |")
    md_lines.append(f"| **审理法院** | {court} |")
    md_lines.append(f"| **判决日期** | {date} |")
    md_lines.append(f"| **案由** | {cause} |")
    md_lines.append("")

    # 当事人信息
    if parties:
        md_lines.append("## 当事人信息")
        md_lines.append("")
        md_lines.append(parties)
        md_lines.append("")

    # 争议焦点
    if dispute_focus:
        md_lines.append("## 争议焦点")
        md_lines.append("")
        md_lines.append(dispute_focus)
        md_lines.append("")

    # 裁判结果
    if judgment_result:
        md_lines.append("## 裁判结果")
        md_lines.append("")
        md_lines.append(judgment_result)
        md_lines.append("")

    # 援引法条
    if legal_basis:
        md_lines.append("## 援引法条")
        md_lines.append("")
        md_lines.append(legal_basis)
        md_lines.append("")

    # 完整文书内容
    if content:
        md_lines.append("## 完整文书")
        md_lines.append("")
        md_lines.append(content)
        md_lines.append("")

    # 页脚
    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    md_lines.append("")
    md_lines.append("> **版权提示**：本文书内容来源于中国裁判文书网，仅限个人学习研究使用。")
    md_lines.append("")

    return "\n".join(md_lines)


def resolve_markdown_path(case_no: str, output_dir: str, on_collision: str) -> str:
    """
    解析最终 Markdown 路径；若 on_collision 为 abort 且默认名已存在，打印标记并退出。
    """
    os.makedirs(output_dir, exist_ok=True)
    safe_name = sanitize_filename(case_no)
    filename = f"{safe_name}_案例详情.md"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        return filepath
    if on_collision == "overwrite":
        return filepath
    if on_collision == "abort":
        print(f"FILE_EXISTS_ABORT:{filepath}", flush=True)
        sys.exit(2)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(output_dir, f"{safe_name}_案例详情_{ts}.md")


def dry_run_markdown_path(
    case_no: str, output_dir: str, on_collision: str
) -> str:
    """计算拟写入路径（不写入、不因 abort 退出）。"""
    os.makedirs(output_dir, exist_ok=True)
    safe_name = sanitize_filename(case_no)
    filename = f"{safe_name}_案例详情.md"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        return filepath
    if on_collision == "overwrite":
        return filepath
    if on_collision == "abort":
        return filepath
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(output_dir, f"{safe_name}_案例详情_{ts}.md")


def save_markdown(
    md_content: str,
    case_no: str,
    output_dir: str,
    on_collision: str = "timestamp",
) -> str:
    """
    保存 Markdown 内容到文件

    Args:
        md_content: Markdown 内容
        case_no: 案号（用于生成文件名）
        output_dir: 输出目录
        on_collision: abort | timestamp | overwrite

    Returns:
        生成的文件路径
    """
    filepath = resolve_markdown_path(case_no, output_dir, on_collision)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Markdown 文件已保存：{filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description='将裁判文书内容转换为 Markdown 文件')
    parser.add_argument('--case-no', required=True, help='案号')
    parser.add_argument('--court', required=True, help='审理法院')
    parser.add_argument('--date', required=True, help='判决日期')
    parser.add_argument('--parties', default='', help='当事人信息')
    parser.add_argument('--cause', required=True, help='案由')
    parser.add_argument('--content', required=True, help='完整文书内容')
    parser.add_argument('--judgment-result', default='', help='裁判结果')
    parser.add_argument('--dispute-focus', default='', help='争议焦点')
    parser.add_argument('--legal-basis', default='', help='援引法条')
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="输出目录",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="不写入文件，仅输出拟写入路径与内容摘要",
    )
    parser.add_argument(
        "--on-collision",
        choices=["abort", "timestamp", "overwrite"],
        default="timestamp",
        help="目标文件已存在时的策略（默认 timestamp 避免静默覆盖）",
    )

    args = parser.parse_args()

    md_content = convert_to_markdown(
        case_no=args.case_no,
        court=args.court,
        date=args.date,
        parties=args.parties,
        cause=args.cause,
        content=args.content,
        judgment_result=args.judgment_result,
        dispute_focus=args.dispute_focus,
        legal_basis=args.legal_basis,
    )

    if args.dry_run:
        safe_name = sanitize_filename(args.case_no)
        default_path = os.path.join(
            args.output_dir, f"{safe_name}_案例详情.md"
        )
        if args.on_collision == "abort" and os.path.exists(default_path):
            print(f"DRY_RUN_WOULD_ABORT:{default_path}", flush=True)
        path = dry_run_markdown_path(
            args.case_no, args.output_dir, args.on_collision
        )
        preview = md_content[:500].replace("\n", " ")
        print(f"DRY_RUN_PATH:{path}", flush=True)
        print(
            f"DRY_RUN_SUMMARY:chars={len(md_content)} preview={preview!r}",
            flush=True,
        )
        return

    filepath = save_markdown(
        md_content, args.case_no, args.output_dir, on_collision=args.on_collision
    )

    print(f"FILE_PATH:{filepath}")


if __name__ == '__main__':
    main()
