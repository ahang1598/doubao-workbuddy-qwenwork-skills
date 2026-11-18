from __future__ import annotations

import argparse
import sys
from pathlib import Path

from report_pipeline_common import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PARTS_DIR,
    ValidationError,
    ensure_parent,
    normalize_trailing_newline,
    read_utf8,
    require,
)
from renumber_references import renumber_report


def assemble(parts_dir: Path, output_path: Path) -> Path:
    part_paths = sorted(parts_dir.glob("*.md"))
    require(part_paths, f"未找到 Markdown 分片: {parts_dir}")
    require(output_path.resolve() not in {path.resolve() for path in part_paths}, "输出文件不能与输入分片重合")
    assembled_parts: list[str] = []
    for part_path in part_paths:
        text = read_utf8(part_path)
        assembled_parts.append(normalize_trailing_newline(text))

    final_text = "\n\n".join(part.rstrip() for part in assembled_parts) + "\n"
    ensure_parent(output_path)
    output_path.write_text(final_text, encoding="utf-8")

    # 引用信息完整时自动重排；信息不足时保留原稿，不阻止交付。
    already_ordered, source_count = renumber_report(output_path)
    if source_count == 0:
        print("[assemble_report] 引用未调整；已保留报告原文")
    elif already_ordered:
        print(f"[assemble_report] 引用编号已符合首现顺序（{source_count} 个来源），未改动")
    else:
        print(f"[assemble_report] 检测到首现乱序，已自动重排 {source_count} 个来源的引用编号与参考文献")

    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="按文件名顺序拼接任意数量的 Markdown 分片为完整行业研究报告。")
    parser.add_argument("--parts-dir", type=Path, default=DEFAULT_PARTS_DIR, help=f"分片目录，默认: {DEFAULT_PARTS_DIR}")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help=f"输出文件，默认: {DEFAULT_OUTPUT_PATH}")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        output_path = assemble(args.parts_dir, args.output)
    except ValidationError as exc:
        print(f"[assemble_report] 失败: {exc}", file=sys.stderr)
        return 1

    print(f"[assemble_report] 成功生成: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
