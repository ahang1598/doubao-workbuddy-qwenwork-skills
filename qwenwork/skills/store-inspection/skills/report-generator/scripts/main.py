#!/usr/bin/env python3
"""report-generator 命令路由入口。"""

import argparse
import sys
from pathlib import Path

# 确保模块路径正确（Windows 兼容：无需外部设置 PYTHONPATH）
# generate_report.py 使用 "from scripts.template_store import ..." 格式导入，
# 因此需要 scripts 的父目录（即 report-generator/）在 sys.path 中。
_SCRIPTS_DIR = Path(__file__).resolve().parent
_SKILL_ROOT = str(_SCRIPTS_DIR.parent)  # report-generator/
_SCRIPTS_STR = str(_SCRIPTS_DIR)

for _path in (_SKILL_ROOT, _SCRIPTS_STR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from commands import generate_report, embed_images


def main():
    parser = argparse.ArgumentParser(description="门店督导报告工具")
    subparsers = parser.add_subparsers(dest="command")

    generate_report.register(subparsers)
    embed_images.register(subparsers)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.handler(args)


if __name__ == "__main__":
    main()
