#!/usr/bin/env python3
"""
最小差异对比脚本
用途：对比两个实验刺激版本，找出所有不同的句子，验证最小差异原则
用法：
  python3 compare_versions.py version_a.txt version_b.txt
  python3 compare_versions.py --names "谄媚组" "非谄媚组" a.txt b.txt
  python3 compare_versions.py --char-by-char a.txt b.txt
"""

import argparse
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


def split_sentences(text):
    """将文本按中文/英文标点拆分为句子"""
    # 按句号、问号、感叹号、分号拆分，保留标点
    sentences = re.split(r'(?<=[。！？；\.\!\?;])\s*', text)
    # 过滤空句子和纯空白
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def normalize(text):
    """标准化文本用于对比：移除空白、统一标点"""
    text = re.sub(r'\s+', '', text)
    # 统一中英文标点
    text = text.replace(',', '，').replace('.', '。').replace('!', '！').replace('?', '？')
    return text


def main():
    parser = argparse.ArgumentParser(description='实验刺激最小差异对比')
    parser.add_argument('file_a', help='版本A文件路径')
    parser.add_argument('file_b', help='版本B文件路径')
    parser.add_argument('--names', nargs=2, default=['版本A', '版本B'],
                        help='两个版本的名称，如 --names "谄媚组" "非谄媚组"')
    parser.add_argument('--char-by-char', action='store_true',
                        help='逐字对比模式（更精细，适合检查核心段落）')
    args = parser.parse_args()

    # 读取文件
    text_a = Path(args.file_a).read_text(encoding='utf-8')
    text_b = Path(args.file_b).read_text(encoding='utf-8')
    name_a, name_b = args.names

    print('=' * 60)
    print(f'最小差异对比报告：{name_a} vs {name_b}')
    print('=' * 60)

    # 字数统计
    norm_a = normalize(text_a)
    norm_b = normalize(text_b)
    len_a, len_b = len(norm_a), len(norm_b)
    diff_ratio = abs(len_a - len_b) / min(len_a, len_b) if min(len_a, len_b) > 0 else 1

    print(f'\n【字数统计】')
    print(f'  {name_a}: {len_a} 字')
    print(f'  {name_b}: {len_b} 字')
    print(f'  差异: {abs(len_a - len_b)} 字 ({diff_ratio:.2%})')
    if diff_ratio <= 0.05:
        print(f'  ✅ 字数差异在5%以内')
    else:
        print(f'  ❌ 字数差异超过5%，违反最小差异原则')

    # 句子级对比
    sents_a = split_sentences(text_a)
    sents_b = split_sentences(text_b)

    print(f'\n【句子级对比】')
    print(f'  {name_a}: {len(sents_a)} 句')
    print(f'  {name_b}: {len(sents_b)} 句')

    # 使用SequenceMatcher找出匹配和差异的句子
    matcher = SequenceMatcher(None, sents_a, sents_b)
    same_count = 0
    diff_blocks = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            same_count += (i2 - i1)
        else:
            diff_blocks.append((tag, sents_a[i1:i2], sents_b[j1:j2]))

    print(f'  相同句子: {same_count} 句')
    print(f'  差异块数: {len(diff_blocks)} 处')

    # 输出差异详情
    if diff_blocks:
        print(f'\n【差异详情】')
        for i, (tag, a_block, b_block) in enumerate(diff_blocks, 1):
            print(f'\n  --- 差异 {i} ({tag}) ---')
            if a_block:
                print(f'  [{name_a}]:')
                for s in a_block:
                    print(f'    "{s}"')
            if b_block:
                print(f'  [{name_b}]:')
                for s in b_block:
                    print(f'    "{s}"')

    # 逐字对比模式
    if args.char_by_char:
        print(f'\n【逐字对比】')
        char_matcher = SequenceMatcher(None, norm_a, norm_b)
        changes = 0
        for tag, i1, i2, j1, j2 in char_matcher.get_opcodes():
            if tag != 'equal':
                changes += 1
                old = norm_a[i1:i2] if i1 < i2 else '(无)'
                new = norm_b[j1:j2] if j1 < j2 else '(无)'
                print(f'  {tag}: "{old}" → "{new}"')
        print(f'\n  共 {changes} 处文字差异')

    # 总结判断
    print(f'\n{"=" * 60}')
    print('【结论】')
    if diff_ratio <= 0.05 and len(diff_blocks) <= 3:
        print(f'✅ 通过：差异较小（{len(diff_blocks)}处，字数差{diff_ratio:.1%}），')
        print(f'   请确认差异处仅为目标操纵变量，无其他混淆。')
        sys.exit(0)
    elif diff_ratio > 0.05:
        print(f'❌ 未通过：字数差异过大（{diff_ratio:.1%}），需要修改。')
        sys.exit(1)
    else:
        print(f'⚠️  注意：差异处较多（{len(diff_blocks)}处），请逐一确认是否都是')
        print(f'   目标操纵的一部分，避免引入混淆变量。')
        sys.exit(0)


if __name__ == '__main__':
    main()
