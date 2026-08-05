from __future__ import annotations

import argparse
import sys
from pathlib import Path

from report_pipeline_common import (
    ALLOWED_PART_FILENAMES,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PARTS_DIR,
    DISCLAIMER_MARKER,
    FINAL_REQUIRED_SECTIONS,
    PART_SPEC_BY_NAME,
    PART_SPECS,
    RECAP_HEADING,
    REFERENCE_HEADING,
    TITLE_PATTERN,
    ValidationError,
    check_contiguous_numbers,
    check_first_appearance_order,
    extract_citations,
    extract_reference_numbers,
    first_non_empty_line,
    has_forbidden_markup,
    has_markdown_table,
    read_utf8,
    require,
    split_reference_section,
)


def validate_part_file(file_path: Path) -> None:
    require(file_path.exists(), f"文件不存在: {file_path}")
    require(file_path.name in ALLOWED_PART_FILENAMES, f"不是受支持的分片文件: {file_path.name}")
    spec = PART_SPEC_BY_NAME[file_path.name]
    text = read_utf8(file_path)

    require(text.strip(), f"{file_path.name} 内容为空")
    require(not has_forbidden_markup(text), f"{file_path.name} 含图片、html/xml 标签或旧写入链路残留")

    first_line = first_non_empty_line(text)
    if spec.requires_title:
        require(first_line.startswith("# "), f"{file_path.name} 首个非空行必须是主标题")
    else:
        require(TITLE_PATTERN.search(text) is None, f"{file_path.name} 不应包含 Markdown H1 主标题")

    for heading in spec.required_sections:
        require(heading in text, f"{file_path.name} 缺少必需章节 `{heading}`")

    if spec.requires_recap:
        require(RECAP_HEADING in text, f"{file_path.name} 缺少 `{RECAP_HEADING}` 小节")

    if spec.requires_table:
        require(has_markdown_table(text), f"{file_path.name} 至少应包含 1 张 Markdown 表格")

    if spec.allows_references:
        require(REFERENCE_HEADING in text, f"{file_path.name} 缺少 `{REFERENCE_HEADING}`")
    else:
        require(REFERENCE_HEADING not in text, f"{file_path.name} 不应出现 `{REFERENCE_HEADING}`")

    if spec.requires_disclaimer:
        require(DISCLAIMER_MARKER in text, f"{file_path.name} 缺少免责声明")
    else:
        require(DISCLAIMER_MARKER not in text, f"{file_path.name} 不应提前出现免责声明")


def validate_stage(parts_dir: Path) -> None:
    stage_texts: list[str] = []
    for spec in PART_SPECS[:3]:
        part_path = parts_dir / spec.filename
        validate_part_file(part_path)
        stage_texts.append(read_utf8(part_path))

    combined = "\n".join(stage_texts)
    citations = extract_citations(combined)
    require(citations, "阶段校验失败：前三片尚未出现任何引用编号")
    check_contiguous_numbers(citations, "阶段引用")
    # lark-doc-report-standard.md 阶段校验已声明的规则，此前未在代码中实现：
    check_first_appearance_order(
        combined,
        "阶段引用",
        hint="请按正文首次出现顺序修正前三片的引用编号后重试。",
    )


def validate_final_report(file_path: Path) -> None:
    require(file_path.exists(), f"文件不存在: {file_path}")
    text = read_utf8(file_path)
    require(text.strip(), f"{file_path.name} 内容为空")
    require(not has_forbidden_markup(text), f"{file_path.name} 含图片、html/xml 标签或旧写入链路残留")

    first_line = first_non_empty_line(text)
    require(first_line.startswith("# "), "整篇报告首个非空行必须是主标题")
    require(len(TITLE_PATTERN.findall(text)) == 1, "整篇报告只允许出现一个 Markdown H1 主标题")
    require(text.count(REFERENCE_HEADING) == 1, "整篇报告只允许出现一个 `## 参考文献` 标题")
    require(text.count(DISCLAIMER_MARKER) == 1, "整篇报告只允许出现一份免责声明")

    positions = []
    for heading in FINAL_REQUIRED_SECTIONS:
        position = text.find(heading)
        require(position != -1, f"整篇报告缺少必需章节 `{heading}`")
        positions.append(position)
    require(positions == sorted(positions), "整篇报告的一级章节顺序不正确")

    require(text.count(RECAP_HEADING) >= 5, "整篇报告应至少包含 5 个 `### 回扣主线` 小节")
    require(text.count("资料来源：") >= 5, "整篇报告至少应包含 5 处 `资料来源：`")
    require(has_markdown_table(text), "整篇报告至少应包含 1 张 Markdown 表格")

    body, reference_block, disclaimer_block = split_reference_section(text)
    require(reference_block.strip(), "`## 参考文献` 下缺少文献内容")
    require(disclaimer_block.strip(), "`## 参考文献` 后缺少免责声明内容")

    citations = extract_citations(body)
    require(citations, "正文未检测到任何引用编号")
    check_contiguous_numbers(citations, "正文引用")
    # SKILL.md 第 6 步已声明的规则（首现顺序 [1][2][3] 递增），此前未在代码中实现：
    check_first_appearance_order(
        body,
        "正文引用",
        hint="请运行 `python3 scripts/renumber_references.py --file output/report.md` 自动重排后重试。",
    )

    reference_numbers = extract_reference_numbers(reference_block)
    require(reference_numbers, "参考文献必须使用 `[n]` 格式")
    check_contiguous_numbers(reference_numbers, "参考文献")
    require(reference_numbers == sorted(reference_numbers), "参考文献条目未按编号升序排列")
    require(len(reference_numbers) >= 15, f"参考文献数量不足，当前仅 {len(reference_numbers)} 条")

    cited_set = set(citations)
    reference_set = set(reference_numbers)
    require(cited_set.issubset(reference_set), "正文引用编号与参考文献条目不一致，存在未定义引用")
    require(reference_set.issubset(cited_set), "存在未被正文引用的参考文献条目")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验行业研究 Markdown 分片、阶段内容或整篇报告。")
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
    except ValidationError as exc:
        print(f"[validate_report] 失败: {exc}", file=sys.stderr)
        return 1

    print(f"[validate_report] {args.stage} 校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
