#!/usr/bin/env python3
"""页码映射计算器：PPT 增/删/移页后，旧页码 -> 新页码 与 insert_before 目标。

约定（与 SKILL.md 第 2 节一致）：
- 页码从 1 起、含封面；
- "N 页后面插入" = 新页落在第 N+1 位，编辑器 insert_before 目标
  = 操作前当前第 N+1 页的 slide_id（N+1 超过当前页数时即追加到末尾）；
- 每个操作的页码都指"操作那一刻用户看到的当前页码"（与逐轮对话口径一致）。

用法:
    python3 page_map.py 17 insert:11
    python3 page_map.py 17 insert:11 delete:5 move:9-3
    python3 page_map.py 20 delete:4,7 insert:2
"""
import sys


def apply_ops(n, ops):
    pages = list(range(1, n + 1))  # 元素 = 原始页码，新增页用字符串标记
    log = []
    for op in ops:
        kind, _, arg = op.partition(":")
        if kind == "insert":
            after = int(arg)
            if not 0 <= after <= len(pages):
                raise SystemExit(f"insert:{after} 越界（当前 {len(pages)} 页）")
            pages.insert(after, f"new-after-{after}")
            target = after + 1
            advice = (f"insert_before = 当前第 {target} 页的 slide_id（操作前读取）"
                      if after < len(pages) - 1 else "追加到末尾，无需 insert_before")
            log.append(f"insert: 新页落在第 {target} 位；{advice}")
        elif kind == "delete":
            for x in sorted((int(v) for v in arg.split(",")), reverse=True):
                if not 1 <= x <= len(pages):
                    raise SystemExit(f"delete:{x} 越界（当前 {len(pages)} 页）")
                pages.pop(x - 1)
            log.append(f"delete: 删除当前第 {arg} 页")
        elif kind == "move":
            src, dst = (int(x) for x in arg.split("-"))
            if not (1 <= src <= len(pages) and 1 <= dst <= len(pages)):
                raise SystemExit(f"move:{arg} 越界（当前 {len(pages)} 页）")
            pages.insert(dst - 1, pages.pop(src - 1))
            log.append(f"move: 当前第 {src} 位移到第 {dst} 位")
        else:
            raise SystemExit(f"未知操作: {op}（支持 insert:N / delete:a,b / move:a-b）")
    mapping = {p: i + 1 for i, p in enumerate(pages) if isinstance(p, int)}
    return pages, mapping, log


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    n = int(sys.argv[1])
    pages, mapping, log = apply_ops(n, sys.argv[2:])
    for line in log:
        print(line)
    print(f"最终页数: {len(pages)}（原 {n} 页）")
    print("旧页码->新页码: " + ", ".join(f"{o}->{m}" for o, m in sorted(mapping.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
