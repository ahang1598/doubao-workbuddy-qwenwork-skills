#!/usr/bin/env python3
"""
实验条件组合对照表生成脚本
用途：根据自变量及其水平，自动生成所有实验条件组合
用法：
  python3 generate_conditions.py "自我披露:有,无" "AI谄媚:有,无"
  python3 generate_conditions.py "自我披露:有,无" "推理披露:有,无" "AI谄媚:有,无"
  python3 generate_conditions.py --json "IV1:高,低" "IV2:A,B"
  python3 generate_conditions.py --flow "自我披露:有,无" "AI谄媚:有,无"
"""

import argparse
import json
import sys
from itertools import product


def parse_iv(iv_str):
    """解析自变量字符串，格式为 '名称:水平1,水平2,...'"""
    if ':' not in iv_str:
        print(f'❌ 自变量格式错误: "{iv_str}"，应为 "名称:水平1,水平2"', file=sys.stderr)
        sys.exit(1)
    name, levels_str = iv_str.split(':', 1)
    levels = [l.strip() for l in levels_str.split(',') if l.strip()]
    if len(levels) < 2:
        print(f'❌ 自变量 "{name}" 至少需要2个水平', file=sys.stderr)
        sys.exit(1)
    return name.strip(), levels


def main():
    parser = argparse.ArgumentParser(description='实验条件组合对照表生成')
    parser.add_argument('ivs', nargs='+', help='自变量列表，格式: "名称:水平1,水平2,..."')
    parser.add_argument('--json', action='store_true', help='同时输出JSON格式')
    parser.add_argument('--flow', action='store_true', help='生成对话/刺激流程列')
    args = parser.parse_args()

    # 解析所有自变量
    ivs = [parse_iv(iv) for iv in args.ivs]
    iv_names = [name for name, _ in ivs]
    iv_levels = [levels for _, levels in ivs]

    # 生成所有组合
    all_combinations = list(product(*iv_levels))
    n_conditions = len(all_combinations)

    # 输出Markdown表格
    print('# 实验条件对照表\n')
    print(f'共 {len(ivs)} 个自变量，{n_conditions} 个实验条件。\n')

    # 表头
    header = '| 条件编号 | ' + ' | '.join(iv_names) + ' |'
    if args.flow:
        header = '| 条件编号 | ' + ' | '.join(iv_names) + ' | 刺激流程 |'
    separator = '|' + '---|' * (len(ivs) + 2 + (1 if args.flow else 0))

    print(header)
    print(separator)

    conditions_json = []
    for i, combo in enumerate(all_combinations, 1):
        row = f'| {i} | ' + ' | '.join(combo) + ' |'
        if args.flow:
            flow_parts = []
            for name, level in zip(iv_names, combo):
                flow_parts.append(f'{name}={level}')
            row = f'| {i} | ' + ' | '.join(combo) + f' | {" → ".join(flow_parts)} |'
        print(row)

        conditions_json.append({
            'condition_id': i,
            **{name: level for name, level in zip(iv_names, combo)}
        })

    print(f'\n*共 {n_conditions} 个条件*')

    # 检查是否有遗漏
    expected = 1
    for _, levels in ivs:
        expected *= len(levels)
    if n_conditions != expected:
        print(f'⚠️ 警告：条件数({n_conditions})与预期({expected})不符！', file=sys.stderr)
        sys.exit(1)

    # JSON输出
    if args.json:
        print('\n```json')
        print(json.dumps(conditions_json, ensure_ascii=False, indent=2))
        print('```')

    sys.exit(0)


if __name__ == '__main__':
    main()
