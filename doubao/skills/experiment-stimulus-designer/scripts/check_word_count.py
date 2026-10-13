#!/usr/bin/env python3
"""
字数差异检查脚本
用途：检查实验刺激不同条件版本的字数差异是否在5%以内（最小差异原则门禁）
用法：
  python3 check_word_count.py file1.txt file2.txt [file3.txt ...]
  python3 check_word_count.py --text "版本A文本" "版本B文本"
  python3 check_word_count.py --threshold 0.03 file1.txt file2.txt
"""

import argparse
import re
import sys
from pathlib import Path


def count_chars(text):
    """统计字数：中文字符按字算，英文按单词算，数字按整体算"""
    # 移除空白字符
    text = re.sub(r'\s+', '', text)
    # 统计中文字符数
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 统计英文单词数
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    # 统计数字串
    numbers = len(re.findall(r'\d+', text))
    return chinese_chars + english_words + numbers


def main():
    parser = argparse.ArgumentParser(description='实验刺激字数差异检查')
    parser.add_argument('files', nargs='*', help='要检查的文本文件路径')
    parser.add_argument('--text', nargs='+', help='直接输入多个版本的文本')
    parser.add_argument('--threshold', type=float, default=0.05,
                        help='字数差异阈值，默认0.05（5%%）')
    parser.add_argument('--names', nargs='+', help='各版本的名称（可选）')
    args = parser.parse_args()

    versions = []
    names = []

    if args.text:
        for i, t in enumerate(args.text):
            versions.append(t)
            names.append(args.names[i] if args.names and i < len(args.names) else f'版本{i+1}')
    elif args.files:
        for i, f in enumerate(args.files):
            p = Path(f)
            if not p.exists():
                print(f'❌ 文件不存在: {f}', file=sys.stderr)
                sys.exit(1)
            versions.append(p.read_text(encoding='utf-8'))
            names.append(args.names[i] if args.names and i < len(args.names) else p.stem)
    else:
        parser.print_help()
        sys.exit(1)

    if len(versions) < 2:
        print('❌ 至少需要2个版本进行对比', file=sys.stderr)
        sys.exit(1)

    # 统计字数
    counts = [count_chars(v) for v in versions]
    max_count = max(counts)
    min_count = min(counts)
    max_diff_ratio = (max_count - min_count) / min_count if min_count > 0 else float('inf')

    # 输出报告
    print('=' * 50)
    print('字数差异检查报告')
    print('=' * 50)
    for name, count in zip(names, counts):
        print(f'  {name}: {count} 字')
    print('-' * 50)
    print(f'  最大字数: {max_count}')
    print(f'  最小字数: {min_count}')
    print(f'  最大差异: {max_count - min_count} 字 ({max_diff_ratio:.2%})')
    print(f'  阈值: {args.threshold:.0%}')
    print('=' * 50)

    if max_diff_ratio <= args.threshold:
        print(f'✅ 通过：字数差异在 {args.threshold:.0%} 以内')
        sys.exit(0)
    else:
        print(f'❌ 未通过：字数差异超过 {args.threshold:.0%}，需要修改')
        print(f'   建议：将较长版本缩短约 {max_count - int(min_count * (1 + args.threshold))} 字，')
        print(f'   或将较短版本扩充约 {int(max_count * (1 - args.threshold)) - min_count} 字')
        sys.exit(1)


if __name__ == '__main__':
    main()
