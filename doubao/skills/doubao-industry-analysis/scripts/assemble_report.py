from __future__ import annotations

import argparse
import sys
from pathlib import Path

from report_pipeline_common import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PARTS_DIR,
    DISCLAIMER_MARKER,
    PART_SPECS,
    RECAP_HEADING,
    REFERENCE_HEADING,
    TITLE_PATTERN,
    ValidationError,
    ensure_parent,
    normalize_trailing_newline,
    read_utf8,
    require,
)
from renumber_references import renumber_report


def validate_part_for_assembly(text: str, filename: str) -> None:
    require(text.strip(), f"{filename} 为空，无法拼接")
    spec = next(spec for spec in PART_SPECS if spec.filename == filename)

    if spec.requires_title:
        require(TITLE_PATTERN.search(text) is not None, f"{filename} 缺少 Markdown H1 主标题")
    else:
        require(TITLE_PATTERN.search(text) is None, f"{filename} 不应包含 Markdown H1 主标题")

    for heading in spec.required_sections:
        require(heading in text, f"{filename} 缺少必需章节 `{heading}`")

    if spec.requires_recap:
        require(RECAP_HEADING in text, f"{filename} 缺少 `{RECAP_HEADING}` 小节")

    if spec.allows_references:
        require(REFERENCE_HEADING in text, f"{filename} 缺少 `{REFERENCE_HEADING}`")
    else:
        require(REFERENCE_HEADING not in text, f"{filename} 不应提前出现 `{REFERENCE_HEADING}`")

    if spec.requires_disclaimer:
        require(DISCLAIMER_MARKER in text, f"{filename} 缺少免责声明标记 `{DISCLAIMER_MARKER}`")
    else:
        require(DISCLAIMER_MARKER not in text, f"{filename} 不应提前出现免责声明")


def assemble(parts_dir: Path, output_path: Path) -> Path:
    assembled_parts: list[str] = []
    for spec in PART_SPECS:
        part_path = parts_dir / spec.filename
        require(part_path.exists(), f"缺少分片文件: {part_path}")
        text = read_utf8(part_path)
        validate_part_for_assembly(text, spec.filename)
        assembled_parts.append(normalize_trailing_newline(text))

    final_text = "\n\n".join(part.rstrip() for part in assembled_parts) + "\n"
    require(len(TITLE_PATTERN.findall(final_text)) == 1, "整篇报告只允许出现一个 Markdown H1 主标题")
    require(final_text.count(REFERENCE_HEADING) == 1, "整篇报告只允许出现一个 `## 参考文献` 标题")
    require(final_text.count(DISCLAIMER_MARKER) == 1, "整篇报告只允许出现一份免责声明")

    ensure_parent(output_path)
    output_path.write_text(final_text, encoding="utf-8")

    # 兜底机制：写作规则仍是"按正文首次出现顺序递增编号"（见 SKILL.md 第 4 步），
    # 这里在拼接后机械校正一次，保证最终交付一定满足 [1][2][3] 首现递增、
    # 参考文献同步重排。编号正确时为无操作。
    already_ordered, source_count = renumber_report(output_path)
    if already_ordered:
        print(f"[assemble_report] 引用编号已符合首现顺序（{source_count} 个来源），未改动")
    else:
        print(f"[assemble_report] 检测到首现乱序，已自动重排 {source_count} 个来源的引用编号与参考文献")

    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="按固定顺序拼接 Markdown 分片为完整行业研究报告。")
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
