"""按正文首次出现顺序重排引用编号，并同步重排文末参考文献。

设计目标：编号是机械问题，不是模型的认知任务。
模型在写作阶段可以用任何稳定编号（例如台账序号），只要满足两点：
  1) 同一来源全文用同一个编号（1:1 映射）；
  2) 文末参考文献含全部被引编号，格式为行首 `[n] `。
本脚本在拼接后运行，做三件事：
  a) 抽取正文引用的首次出现顺序，构造 旧编号 -> 新编号 映射；
  b) 重写正文所有 [n]，并把同句相邻多引 [14][8] 排成 [8][14]；
  c) 按新编号重排参考文献条目。

用法：
  python3 scripts/renumber_references.py --file output/report.md
  python3 scripts/renumber_references.py --file output/report.md --check   # 只检查不改写
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from report_pipeline_common import (
    CITATION_PATTERN,
    DEFAULT_OUTPUT_PATH,
    REFERENCE_HEADING,
    ValidationError,
    read_utf8,
    require,
    split_reference_section,
)

# 参考文献条目：行首 [n] 空格
REFERENCE_LINE_PATTERN = re.compile(r"^\s*\[(\d+)\]\s+(.*)$")
# 同句相邻多引：[14][8][2] 这样的连续串
ADJACENT_RUN_PATTERN = re.compile(r"(?:(?<!\!)\[\d+\](?!\()){2,}")


def extract_unique_citations_in_order(body: str) -> list[int]:
    seen: list[int] = []
    for match in CITATION_PATTERN.finditer(body):
        number = int(match.group(1))
        if number not in seen:
            seen.append(number)
    return seen


def build_number_mapping(ordered_old_numbers: list[int]) -> dict[int, int]:
    return {old: new for new, old in enumerate(ordered_old_numbers, start=1)}


def renumber_body(body: str, mapping: dict[int, int]) -> str:
    def replace_match(match: re.Match[str]) -> str:
        old = int(match.group(1))
        require(old in mapping, f"正文引用 [{old}] 在映射中不存在（正文/参考文献不一致？）")
        return f"[{mapping[old]}]"

    renumbered = CITATION_PATTERN.sub(replace_match, body)

    # 相邻多引按新编号升序排列并去重，避免出现 [9][2] 或 [8][8] 这类观感问题
    def sort_run(match: re.Match[str]) -> str:
        numbers = sorted({int(n) for n in re.findall(r"\[(\d+)\]", match.group(0))})
        return "".join(f"[{n}]" for n in numbers)

    return ADJACENT_RUN_PATTERN.sub(sort_run, renumbered)


def parse_reference_entries(reference_block: str) -> dict[int, str]:
    entries: dict[int, str] = {}
    current: int | None = None
    for line in reference_block.splitlines():
        match = REFERENCE_LINE_PATTERN.match(line)
        if match:
            current = int(match.group(1))
            require(current not in entries, f"参考文献编号 [{current}] 重复")
            entries[current] = match.group(2).strip()
        elif line.strip() and current is not None:
            if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", line.strip()):
                current = None  # 水平分割线，不属于任何条目
                continue
            # 续行（条目换行书写）
            entries[current] += " " + line.strip()
    return entries


def renumber_reference_block(reference_block: str, mapping: dict[int, int]) -> str:
    entries = parse_reference_entries(reference_block)
    cited = set(mapping)
    listed = set(entries)
    require(cited.issubset(listed), f"正文引用了参考文献中不存在的编号: {sorted(cited - listed)}")
    require(listed.issubset(cited), f"参考文献存在未被正文引用的条目: {sorted(listed - cited)}")

    lines = [""]
    for old, new in sorted(mapping.items(), key=lambda item: item[1]):
        lines.append(f"[{new}] {entries[old]}")
        lines.append("")
    return "\n".join(lines)


def renumber_report(report_path: Path, check_only: bool = False) -> tuple[bool, int]:
    """按首现顺序重排编号。返回 (重排前是否已有序, 来源总数)。"""
    text = read_utf8(report_path)
    body, reference_block, disclaimer_block = split_reference_section(text)

    ordered = extract_unique_citations_in_order(body)
    require(ordered, "正文未检测到任何引用编号")
    mapping = build_number_mapping(ordered)

    already_ordered = all(old == new for old, new in mapping.items())
    if check_only or already_ordered:
        # 即使已有序，也顺手核对正文与参考文献的勾稽
        renumber_reference_block(reference_block, mapping)
        return already_ordered, len(mapping)

    new_body = renumber_body(body, mapping)
    new_reference_block = renumber_reference_block(reference_block, mapping)

    new_text = new_body + REFERENCE_HEADING + "\n" + new_reference_block
    if disclaimer_block.strip():
        new_text = new_text.rstrip() + "\n\n---\n\n" + disclaimer_block.lstrip()
    report_path.write_text(new_text.rstrip() + "\n", encoding="utf-8")
    return already_ordered, len(mapping)


def main() -> int:
    parser = argparse.ArgumentParser(description="按正文首次出现顺序重排引用编号与参考文献。")
    parser.add_argument("--file", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--check", action="store_true", help="只检查是否已按首现顺序编号，不改写文件")
    args = parser.parse_args()

    try:
        already_ordered, count = renumber_report(args.file, check_only=args.check)
    except ValidationError as exc:
        print(f"[renumber_references] 失败: {exc}", file=sys.stderr)
        return 1

    if args.check:
        if already_ordered:
            print(f"[renumber_references] 检查通过：{count} 个来源已按首现顺序编号")
            return 0
        print("[renumber_references] 检查未通过：正文首现顺序不是 [1][2][3]… 递增", file=sys.stderr)
        return 1

    if already_ordered:
        print(f"[renumber_references] 编号已符合首现顺序（{count} 个来源），未改动: {args.file}")
    else:
        print(f"[renumber_references] 已按首现顺序重排 {count} 个来源的编号与参考文献: {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
