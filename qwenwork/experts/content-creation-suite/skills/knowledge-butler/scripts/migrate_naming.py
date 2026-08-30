#!/usr/bin/env python3
"""
migrate_naming.py · 知识管家旧格式文件迁移工具（可选 · P5）

═══════════════════════════════════════════════════════════════════
背景
═══════════════════════════════════════════════════════════════════

知识管家的命名规则在 2026-04-26 后统一为：
    YYYY-MM-DD：title.md  （全角冒号 ：U+FF1A 作分隔符）

但用户在此之前生成的旧文件可能是：
    YYYY-MM-DD_title.md   （下划线分隔）
    YYYY-MM-DD-title.md   （半角连字符）
    YYYY-MM-DD title.md   （空格）

这个脚本扫描旧格式 → dry-run 显示重命名计划 → 用户 confirm 后执行。

═══════════════════════════════════════════════════════════════════
安全设计
═══════════════════════════════════════════════════════════════════

1. **默认 dry-run**：不传 --apply 时只打印计划，不动文件
2. **冲突检测**：如果新文件名已存在 → 跳过该文件并打印警告（不覆盖）
3. **范围限定**：仅扫描 1-素材/录音/、1-素材/收藏/、1-素材/文稿/ 这三个用户原文目录
4. **不动 2-AI知识库/**：摘要/专题/洞察的命名是 LLM 写的，自带前缀（"摘要-"），不需要迁移
5. **保留旧文件**：执行重命名是 git mv 风格的 rename，不是 cp + rm

═══════════════════════════════════════════════════════════════════
用法
═══════════════════════════════════════════════════════════════════

    # 默认 dry-run，只看计划：
    .venv/bin/python scripts/migrate_naming.py

    # 确认 OK 后真正执行：
    .venv/bin/python scripts/migrate_naming.py --apply

    # 只扫某个子目录：
    .venv/bin/python scripts/migrate_naming.py --subdir 录音

    # 不同 KB_ROOT：
    KB_ROOT=~/Documents/我的知识库 .venv/bin/python scripts/migrate_naming.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# 旧格式文件名模式：YYYY-MM-DD 后跟 [_-空格] 然后 title.md
# 注意必须**不**匹配新格式（YYYY-MM-DD：）
OLD_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[_\- ](.+)\.md$"
)


def find_kb_root() -> Path:
    """优先环境变量，fallback 到默认桌面路径。"""
    env = os.environ.get("KB_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "Desktop" / "知识管家").resolve()


def plan_renames(target_dir: Path) -> list[tuple[Path, Path, str]]:
    """扫描 target_dir，返回 [(旧路径, 新路径, 状态), ...]。

    状态:
      "ok"        - 可以迁移
      "conflict"  - 新名已存在
      "skip"      - 已是新格式（含全角冒号）
    """
    plan: list[tuple[Path, Path, str]] = []
    if not target_dir.exists():
        return plan

    for old in sorted(target_dir.glob("*.md")):
        name = old.name
        # 已是新格式（含全角冒号 U+FF1A）→ 跳过
        if "：" in name:
            continue
        m = OLD_PATTERN.match(name)
        if not m:
            continue
        date_part, title_part = m.group(1), m.group(2)
        new_name = f"{date_part}：{title_part}.md"
        new_path = old.parent / new_name
        if new_path.exists():
            plan.append((old, new_path, "conflict"))
        else:
            plan.append((old, new_path, "ok"))
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="迁移知识管家旧格式文件名（YYYY-MM-DD_X.md → YYYY-MM-DD：X.md）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("用法")[0],
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真正执行重命名（默认 dry-run，只打印计划）",
    )
    parser.add_argument(
        "--subdir",
        choices=["录音", "收藏", "文稿"],
        help="只扫某个子目录（默认全部 3 个）",
    )
    args = parser.parse_args()

    kb_root = find_kb_root()
    if not kb_root.exists():
        print(f"❌ KB_ROOT 不存在：{kb_root}", file=sys.stderr)
        return 1

    print(f"🗝 KB_ROOT={kb_root}")
    print(f"模式：{'真实执行（--apply）' if args.apply else 'DRY-RUN（仅显示计划）'}")
    print()

    subdirs = [args.subdir] if args.subdir else ["录音", "收藏", "文稿"]

    total_ok = 0
    total_conflict = 0
    total_renamed = 0

    for sub in subdirs:
        target = kb_root / "1-素材" / sub
        plan = plan_renames(target)
        if not plan:
            print(f"📁 {sub}/  无旧格式文件需要迁移")
            continue
        print(f"📁 {sub}/  {len(plan)} 项")
        for old, new, status in plan:
            if status == "conflict":
                total_conflict += 1
                print(f"  ⚠️  {old.name}")
                print(f"      → {new.name}（新名已存在，跳过）")
            else:  # ok
                total_ok += 1
                print(f"  {'✓' if not args.apply else '→'} {old.name}")
                print(f"      → {new.name}")
                if args.apply:
                    try:
                        old.rename(new)
                        total_renamed += 1
                    except OSError as e:
                        print(f"      ❌ 重命名失败：{e}", file=sys.stderr)
        print()

    print("=" * 60)
    print(f"扫描结果：{total_ok} 项可迁移 · {total_conflict} 项冲突跳过")
    if args.apply:
        print(f"实际重命名：{total_renamed} 项")
    else:
        print("这是 DRY-RUN——确认 OK 后用 --apply 真正执行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
