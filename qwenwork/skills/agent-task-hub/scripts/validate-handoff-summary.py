#!/usr/bin/env python3
"""Validate a handoff summary before writing it to the team ledger.

Reads the summary text from --file or stdin and checks the required structure
from templates/handoff-summary.md. For development tasks pass --dev to also
require repo / branch / commit, deliverable list, and validation evidence.
Exits non-zero and prints the missing items when the summary is incomplete.

Usage:
    python3 scripts/validate-handoff-summary.py --file <path> [--dev]
    python3 scripts/validate-handoff-summary.py [--dev] < summary.md
"""

from __future__ import annotations

import argparse
import sys

# marker -> human readable label. Markers are copied from the template and must
# stay in sync with templates/handoff-summary.md so the check is deterministic.
ALWAYS_REQUIRED: dict[str, str] = {
    "【交接元信息】": "交接元信息",
    "任务ID：": "任务ID",
    "【目标】": "目标",
    "【当前状态】": "当前状态",
    "【已完成/已产出】": "已完成/已产出",
    "【下一步】": "下一步",
    "【关键决策/约束】": "关键决策/约束",
    "【风险/阻塞】": "风险/阻塞",
    "交付物清单": "交付物清单",
    "先读材料": "先读材料",
    "【接手方式】": "接手方式",
}

DEV_REQUIRED: dict[str, str] = {
    "仓库：": "仓库",
    "分支：": "分支",
    "基线 commit：": "基线 commit",
    "验证：": "验证",
}


def check_summary(text: str, is_dev: bool) -> list[str]:
    """Return the human-readable labels of missing required items."""
    required = dict(ALWAYS_REQUIRED)
    if is_dev:
        required.update(DEV_REQUIRED)
    return [label for marker, label in required.items() if marker not in text]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        "-f",
        help="summary file path; defaults to reading stdin",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="development task: also require repo/branch/commit, deliverables and validation",
    )
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    missing = check_summary(text, args.dev)
    if missing:
        print("FAIL: 交接摘要缺少以下必填项：")
        for label in missing:
            print(f"  - {label}")
        return 1

    scope = "（开发任务：已含仓库/分支/commit、交付物清单、验证）" if args.dev else ""
    print(f"PASS: 交接摘要结构校验通过{scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())