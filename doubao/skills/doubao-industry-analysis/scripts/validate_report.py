from __future__ import annotations

import argparse
import sys
from pathlib import Path

from report_pipeline_common import DEFAULT_OUTPUT_PATH, DEFAULT_PARTS_DIR, read_utf8, require, ValidationError


def validate_part_file(file_path: Path) -> None:
    """仅读取文件，不执行内容、格式或数量校验。"""
    read_utf8(file_path)


def validate_stage(parts_dir: Path) -> None:
    """读取分片文件，不检查分片数量、结构或引用。"""
    for file_path in sorted(parts_dir.glob("*.md")):
        read_utf8(file_path)


def validate_final_report(file_path: Path) -> None:
    """仅读取文件，不执行报告内容校验。"""
    read_utf8(file_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="读取报告文件，不校验报告内容、格式或数量。")
    parser.add_argument("--stage", choices=("part", "stage", "final"), required=True, help="校验阶段")
    parser.add_argument("--file", type=Path, help="`--stage part` 或 `--stage final` 时要校验的文件路径")
    parser.add_argument("--parts-dir", type=Path, default=DEFAULT_PARTS_DIR, help=f"分片目录，默认: {DEFAULT_PARTS_DIR}")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help=f"`--stage final` 默认校验文件: {DEFAULT_OUTPUT_PATH}")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.stage == "part":
            require(args.file is not None, "`--stage part` 时必须提供 `--file`")
            validate_part_file(args.file)
        elif args.stage == "stage":
            validate_stage(args.parts_dir)
        else:
            validate_final_report(args.file or args.output)
    except (ValidationError, OSError, UnicodeError) as exc:
        print(f"[validate_report] 文件读取失败: {exc}", file=sys.stderr)
        return 1

    print("[validate_report] 文件读取成功；未执行报告内容、格式及数量核验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
