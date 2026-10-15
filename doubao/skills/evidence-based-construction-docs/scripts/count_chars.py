#!/usr/bin/env python3
"""按块统计字符数并对照上限，核验"特征分析80字 / 措施5点各100字 /
测量控制网3点各约400字"这类字数与点数限制。

用法:
  python3 count_chars.py <文本文件> [上限1 上限2 ...]
  文本按空行分块；只给 1 个上限时对所有块套用同一上限。
字符口径: 去掉所有空白后的字符数（中文按 1 字符计）。
退出码: 有超限或缺块时为 1，全部达标为 0。
"""
import re
import sys


def main(path, limits):
    text = open(path, encoding="utf-8").read()
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(limits) == 1 and len(blocks) > 1:
        limits = limits * len(blocks)
    bad = 0
    for i, b in enumerate(blocks):
        n = len(re.sub(r"\s", "", b))
        limit = limits[i] if i < len(limits) else None
        flag = ""
        if limit is not None and n > limit:
            flag = f"  <-- 超 {n - limit} 字，需压缩"
            bad += 1
        line = f"块 {i + 1}: {n} 字"
        if limit is not None:
            line += f" / 上限 {limit}"
        print(line + flag)
    if len(blocks) < len(limits):
        print(f"只有 {len(blocks)} 块，但要求 {len(limits)} 点：缺 "
              f"{len(limits) - len(blocks)} 点，需补足")
        bad += 1
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("用法: python3 count_chars.py <文本文件> [上限1 上限2 ...]")
    main(sys.argv[1], [int(x) for x in sys.argv[2:]])
