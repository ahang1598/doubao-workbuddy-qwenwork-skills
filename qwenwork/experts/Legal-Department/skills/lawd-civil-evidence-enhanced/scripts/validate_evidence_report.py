#!/usr/bin/env python3
"""证据类报告交付门禁校验（单元 10「综合证据策略」）。

对模式 A/B/C 的报告草稿做结构完整性硬校验，拦截时以非零退出码阻断交付：

  1. 证据三性表格结构完整（模式 A/B）
     每份证据都必须有真实性 / 合法性 / 关联性三栏，且三栏均不为空。
  2. 证据链缺口标注完整（模式 A/C）
     缺口章节必须存在；每个已识别缺口必须给出补强 / 补救建议。
  3. 证据编号连续无重复（模式 A/B/C）
     证据编号不得重复，不得断号。
  4. 无悬空主张（模式 C）
     主张清单中的每个主张都必须出现在主张-证据映射中，
     且有支撑证据或被明确标注为缺口。

脚本只做结构门禁，不做法律实质判断。

用法：
  python3 validate_evidence_report.py report.md --mode A
  python3 validate_evidence_report.py report.md            # 自动识别模式
  python3 validate_evidence_report.py --help
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------

EMPTY_CELL_TOKENS = {
    "",
    "-",
    "—",
    "–",
    "/",
    "N/A",
    "n/a",
    "NA",
    "待填写",
    "待补充",
    "待定",
    "略",
    "TODO",
    "TBD",
    "...",
    "…",
    "[待补充]",
    "[待填写]",
}

THREE_CHARACTER_COLUMNS = ("真实性", "合法性", "关联性")

# 三性小节式写法（模式 B 逐份质证常用）
THREE_CHARACTER_SECTION_PATTERNS = {
    "真实性": re.compile(r"真实性(?:分析|审查|意见)?[：:】]"),
    "合法性": re.compile(r"合法性(?:分析|审查|意见)?[：:】]"),
    "关联性": re.compile(r"关联性(?:分析|审查|意见)?[：:】]"),
}

GAP_SECTION_PATTERNS = (
    re.compile(r"证据链缺口"),
    re.compile(r"证据缺口"),
    re.compile(r"缺口清单"),
    re.compile(r"缺漏与补强"),
    re.compile(r"【缺口\s*\d+"),
)

REMEDY_PATTERNS = (
    re.compile(r"补强(?:方案|建议|措施|难度)"),
    re.compile(r"补救(?:建议|方案|措施)"),
    re.compile(r"补证(?:计划|建议)"),
    re.compile(r"补充(?:取证|证据)"),
    re.compile(r"替代(?:方案|路径)"),
)

# 证据编号：证据1 / 证据 12 / 编号 3 / 原证1 / 被证2 / 被证1-2（复合编号）/ 表格首列纯数字
EVIDENCE_NO_PATTERNS = (
    re.compile(r"(?:证据|原证|被证|证\s*据\s*编号|编号)\s*[第]?\s*(\d{1,3}(?:-\d{1,3})?)\s*[号]?"),
)

CLAIM_LIST_HEADER_PATTERNS = (
    re.compile(r"主张清单"),
    re.compile(r"法律主张清单"),
)

CLAIM_MAPPING_PATTERNS = (
    re.compile(r"主张[-—–]?\s*证据映射"),
    re.compile(r"【主张\s*\d+"),
    re.compile(r"五层映射"),
    re.compile(r"举证要点映射"),
)

GAP_MARK_PATTERNS = (
    re.compile(r"缺失"),
    re.compile(r"缺口"),
    re.compile(r"无证据"),
    re.compile(r"待补"),
    re.compile(r"🔴"),
    re.compile(r"🟡"),
)

MODE_HINTS = {
    "A": (re.compile(r"证据专项分析报告"), re.compile(r"证明责任分配")),
    "B": (re.compile(r"质证意见"), re.compile(r"质证话术")),
    "C": (re.compile(r"证据链组织报告"), re.compile(r"主张[-—–]?\s*证据映射")),
}

# 块式条目（【缺口 N】/【主张 N】）的结束边界：遇到新章节即结束，
# 避免最后一个块吞掉后续章节内容导致漏判。
SECTION_BOUNDARY_PATTERNS = (
    re.compile(r"^\s*[一二三四五六七八九十]+、"),
    re.compile(r"^\s*={3,}"),
    re.compile(r"^\s*#{1,6}\s"),
    re.compile(r"^\s*【(?:证据缺口|缺口清单|证明力总评|证据目录|类案裁判规则摘要|本案证据分析法律依据|证据体系弱点识别|必须补充的证据|建议补充的证据|印证关系图谱)"),
)


# --------------------------------------------------------------------------
# 工具函数
# --------------------------------------------------------------------------


def is_empty_cell(value: str) -> bool:
    return value.strip() in EMPTY_CELL_TOKENS


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    cells = stripped.strip("|").split("|")
    return [cell.strip() for cell in cells]


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells)


def parse_tables(lines: list[str]) -> list[dict]:
    """提取所有 Markdown 管道表格：{'header':[...], 'rows':[(lineno, cells)], 'start':lineno}"""
    tables: list[dict] = []
    index = 0
    total = len(lines)
    while index < total:
        cells = split_table_row(lines[index])
        if len(cells) >= 2:
            header = cells
            start_lineno = index + 1
            body: list[tuple[int, list[str]]] = []
            cursor = index + 1
            saw_separator = False
            while cursor < total:
                row = split_table_row(lines[cursor])
                if len(row) < 2:
                    break
                if is_separator_row(row):
                    saw_separator = True
                else:
                    body.append((cursor + 1, row))
                cursor += 1
            if saw_separator:
                tables.append({"header": header, "rows": body, "start": start_lineno})
            index = cursor
        else:
            index += 1
    return tables


def find_column(header: list[str], keyword: str) -> int:
    for position, name in enumerate(header):
        if keyword in name:
            return position
    return -1


THREE_CHAR_SUFFIXES = ("", "意见", "审查", "认定")


def find_three_char_column(header: list[str], keyword: str) -> int:
    """三性列严格匹配：列名=关键词（可带 意见/审查/认定 后缀），或列名含"三性"且含该关键词。

    避免"真实性保障"等描述性列名被子串匹配误判为三性列（误判会导致合规表格被拦）。
    """
    stripped = [str(name).strip() for name in header]
    for position, name in enumerate(stripped):
        if name == keyword or any(name == keyword + suffix for suffix in THREE_CHAR_SUFFIXES):
            return position
    for position, name in enumerate(stripped):
        if "三性" in name and keyword in name:
            return position
    return -1


def block_end(lines: list[str], start: int, hard_limit: int) -> int:
    """返回块式条目的结束行号（不含）：遇到新章节即截断，否则取 hard_limit。"""
    for cursor in range(start + 1, hard_limit):
        line = lines[cursor]
        if any(pattern.search(line) for pattern in SECTION_BOUNDARY_PATTERNS):
            return cursor
    return hard_limit


def detect_mode(text: str) -> str | None:
    scores: dict[str, int] = {}
    for mode, patterns in MODE_HINTS.items():
        scores[mode] = sum(1 for pattern in patterns if pattern.search(text))
    best = max(scores, key=lambda key: scores[key])
    return best if scores[best] > 0 else None


# --------------------------------------------------------------------------
# 校验项
# --------------------------------------------------------------------------


def check_three_characters(
    text: str, lines: list[str], tables: list[dict]
) -> tuple[list[str], list[str]]:
    """校验项 1：证据三性表格结构完整。"""
    errors: list[str] = []
    notes: list[str] = []

    three_char_tables = []
    for table in tables:
        hits = [column for column in THREE_CHARACTER_COLUMNS if find_three_char_column(table["header"], column) >= 0]
        if hits:
            three_char_tables.append((table, hits))

    for table, hits in three_char_tables:
        missing_columns = [column for column in THREE_CHARACTER_COLUMNS if column not in hits]
        if missing_columns:
            errors.append(
                f"第 {table['start']} 行的证据三性表格缺少列：{'、'.join(missing_columns)}"
            )
            continue
        positions = {column: find_three_char_column(table["header"], column) for column in THREE_CHARACTER_COLUMNS}
        name_position = find_column(table["header"], "证据名称")
        label_position = name_position if name_position >= 0 else 0
        for lineno, row in table["rows"]:
            if label_position < len(row):
                label = row[label_position].strip()
            else:
                label = row[0].strip() if row else ""
            blanks = [
                column
                for column, position in positions.items()
                if position >= len(row) or is_empty_cell(row[position])
            ]
            if blanks:
                errors.append(
                    f"第 {lineno} 行证据「{label or '(未命名)'}」三性栏缺失或为空：{'、'.join(blanks)}"
                )

    # 小节式三性（模式 B 逐份质证）
    section_blocks = re.findall(r"【?(?:对方)?证据\s*\d{1,3}[】\)）]?[^\n]*", text)
    if not three_char_tables and section_blocks:
        found = {
            column: bool(pattern.search(text))
            for column, pattern in THREE_CHARACTER_SECTION_PATTERNS.items()
        }
        missing = [column for column, ok in found.items() if not ok]
        if missing:
            errors.append(
                "逐份质证部分缺少三性分析小节：" + "、".join(missing)
            )
        else:
            notes.append(f"三性以小节形式呈现，三项齐备（识别到 {len(section_blocks)} 处证据标题）")

    if three_char_tables:
        row_count = sum(len(table["rows"]) for table, _ in three_char_tables)
        notes.append(
            f"证据三性表格 {len(three_char_tables)} 张、共 {row_count} 份证据，三栏齐备无空缺"
        )
    elif not section_blocks:
        errors.append("未找到任何证据三性表格或三性分析小节（模式 A/B 必须包含）")

    return errors, notes


def check_gap_annotation(text: str, lines: list[str], tables: list[dict]) -> tuple[list[str], list[str]]:
    """校验项 2：证据链缺口标注完整。"""
    errors: list[str] = []
    notes: list[str] = []

    has_gap_section = any(pattern.search(text) for pattern in GAP_SECTION_PATTERNS)
    if not has_gap_section:
        errors.append("缺少证据链缺口章节（模式 A/C 必须包含缺口识别）")
        return errors, notes

    # 表格式缺口清单：逐行检查补救建议列
    gap_tables = [
        table
        for table in tables
        if find_column(table["header"], "缺口") >= 0
        or find_column(table["header"], "风险等级") >= 0
    ]
    checked_rows = 0
    for table in gap_tables:
        remedy_position = -1
        for keyword in ("补救", "补强", "补证", "建议", "方案"):
            remedy_position = find_column(table["header"], keyword)
            if remedy_position >= 0:
                break
        if remedy_position < 0:
            # 缺口类型定义表（表现/风险等级）不要求补救列，仅当含具体缺口条目时报错
            if find_column(table["header"], "对应主张") >= 0 or find_column(table["header"], "序号") >= 0:
                errors.append(
                    f"第 {table['start']} 行的缺口清单表格没有补强/补救建议列"
                )
            continue
        for lineno, row in table["rows"]:
            checked_rows += 1
            if remedy_position >= len(row) or is_empty_cell(row[remedy_position]):
                label = row[0] if row else ""
                errors.append(
                    f"第 {lineno} 行缺口「{label or '(未命名)'}」未填写补强/补救建议"
                )

    # 块式缺口：【缺口 N】…下一个缺口/章节之前必须出现补强字样
    block_starts = [
        (index, match.group(0))
        for index, line in enumerate(lines)
        for match in [re.search(r"【缺口\s*(\d{1,3})[】\s]", line)]
        if match
    ]
    for position, (index, label) in enumerate(block_starts):
        hard_limit = block_starts[position + 1][0] if position + 1 < len(block_starts) else len(lines)
        end = block_end(lines, index, hard_limit)
        block = "\n".join(lines[index:end])
        if not any(pattern.search(block) for pattern in REMEDY_PATTERNS):
            errors.append(f"第 {index + 1} 行 {label} 未给出补强/补救建议")
        else:
            checked_rows += 1

    # 空壳缺口章节拦截：章节存在但无任何缺口条目（无表格行、无【缺口 N】块），
    # 且章节实质内容只有占位文字（如"无。""N/A"）时，视为未做缺口分析
    if checked_rows == 0 and not block_starts and not gap_tables:
        section_started = False
        section_body = ""
        for line in lines:
            stripped = line.strip()
            if not section_started:
                if any(pattern.search(stripped) for pattern in GAP_SECTION_PATTERNS):
                    section_started = True
                continue
            if re.match(r"^#{1,3}\s", stripped):
                break
            section_body += stripped + "\n"
        body_compact = re.sub(r"\s+", "", section_body)
        if len(body_compact) < 20:
            errors.append(
                "证据链缺口章节为空壳（无任何缺口条目，仅有占位文字）。"
                "请列出已识别缺口及补强建议；若确实无缺口，须写明审查依据而非仅写'无'"
            )

    notes.append(f"缺口章节存在，已检查 {checked_rows} 条缺口条目的补强建议")
    return errors, notes


def check_evidence_numbering(text: str, tables: list[dict]) -> tuple[list[str], list[str]]:
    """校验项 3：证据编号连续无重复。"""
    errors: list[str] = []
    notes: list[str] = []

    numbers: list[int] = []
    for table in tables:
        name_position = find_column(table["header"], "证据名称")
        no_position = find_column(table["header"], "编号")
        if name_position < 0 or no_position < 0:
            continue
        for _, row in table["rows"]:
            if no_position < len(row):
                match = re.search(r"(\d{1,3})", row[no_position])
                if match:
                    numbers.append(int(match.group(1)))

    if not numbers:
        for pattern in EVIDENCE_NO_PATTERNS:
            numbers.extend(int(value) for value in pattern.findall(text))

    if not numbers:
        notes.append("未识别到证据编号，跳过编号连续性检查")
        return errors, notes

    unique_numbers = sorted(set(numbers))

    # 表格来源可判定重复；正文引用会天然重复，故仅对表格列做重复判定
    table_numbers: list[int] = []
    for table in tables:
        name_position = find_column(table["header"], "证据名称")
        no_position = find_column(table["header"], "编号")
        if name_position < 0 or no_position < 0:
            continue
        seen: set[int] = set()
        for lineno, row in table["rows"]:
            if no_position >= len(row):
                continue
            match = re.search(r"(\d{1,3})", row[no_position])
            if not match:
                continue
            value = int(match.group(1))
            table_numbers.append(value)
            if value in seen:
                errors.append(f"第 {lineno} 行证据编号重复：{value}")
            seen.add(value)

    expected = list(range(unique_numbers[0], unique_numbers[-1] + 1))
    gaps = [value for value in expected if value not in unique_numbers]
    if gaps:
        errors.append(
            "证据编号断号："
            + "、".join(str(value) for value in gaps)
            + f"（现有编号 {unique_numbers[0]}–{unique_numbers[-1]}）"
        )
    if unique_numbers[0] != 1:
        errors.append(f"证据编号未从 1 开始，最小编号为 {unique_numbers[0]}")

    if not errors:
        notes.append(f"证据编号 1–{unique_numbers[-1]} 连续且无重复（共 {len(unique_numbers)} 份）")
    return errors, notes


def check_dangling_claims(text: str, lines: list[str], tables: list[dict]) -> tuple[list[str], list[str]]:
    """校验项 4：模式 C 无悬空主张。"""
    errors: list[str] = []
    notes: list[str] = []

    if not any(pattern.search(text) for pattern in CLAIM_MAPPING_PATTERNS):
        errors.append("模式C 报告缺少主张-证据映射（五层映射表）")
        return errors, notes

    # 1) 提取主张清单条目
    claims: list[tuple[int, str]] = []
    in_claim_list = False
    for index, line in enumerate(lines):
        if any(pattern.search(line) for pattern in CLAIM_LIST_HEADER_PATTERNS):
            in_claim_list = True
            continue
        if in_claim_list:
            match = re.match(r"\s*(\d{1,2})[\.、\)]\s*(.+)", line)
            if match:
                claims.append((int(match.group(1)), match.group(2).strip()))
                continue
            if line.strip() == "":
                continue
            in_claim_list = False

    # 2) 提取映射中已覆盖的主张序号
    mapped: set[int] = set()
    for match in re.finditer(r"【主张\s*(\d{1,2})", text):
        mapped.add(int(match.group(1)))
    for table in tables:
        claim_position = find_column(table["header"], "主张")
        if claim_position < 0:
            continue
        for _, row in table["rows"]:
            if claim_position < len(row):
                found = re.search(r"主张\s*(\d{1,2})", row[claim_position])
                if found:
                    mapped.add(int(found.group(1)))

    for number, title in claims:
        if number not in mapped:
            errors.append(f"悬空主张：主张 {number}「{title}」未出现在主张-证据映射中")

    # 3) 映射块内必须有支撑证据或明确缺口标注
    block_starts = [
        (index, int(match.group(1)))
        for index, line in enumerate(lines)
        for match in [re.search(r"【主张\s*(\d{1,2})", line)]
        if match
    ]
    for position, (index, number) in enumerate(block_starts):
        hard_limit = block_starts[position + 1][0] if position + 1 < len(block_starts) else len(lines)
        end = block_end(lines, index, hard_limit)
        block = "\n".join(lines[index:end])
        has_evidence = re.search(r"证据\s*\d{1,3}", block) is not None
        has_gap_mark = any(pattern.search(block) for pattern in GAP_MARK_PATTERNS)
        if not has_evidence and not has_gap_mark:
            errors.append(
                f"第 {index + 1} 行主张 {number} 既无支撑证据也未标注缺口（悬空主张）"
            )

    if not errors:
        notes.append(
            f"主张清单 {len(claims)} 项、映射覆盖 {len(mapped)} 项，无悬空主张"
        )
    return errors, notes


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------


def run_checks(text: str, mode: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    tables = parse_tables(lines)

    errors: list[str] = []
    passed: list[str] = []

    if mode in ("A", "B"):
        item_errors, item_notes = check_three_characters(text, lines, tables)
        errors.extend(item_errors)
        if not item_errors:
            passed.append("① 证据三性表格结构完整：" + ("；".join(item_notes) or "通过"))

    if mode in ("A", "C"):
        item_errors, item_notes = check_gap_annotation(text, lines, tables)
        errors.extend(item_errors)
        if not item_errors:
            passed.append("② 证据链缺口标注完整：" + ("；".join(item_notes) or "通过"))

    item_errors, item_notes = check_evidence_numbering(text, tables)
    errors.extend(item_errors)
    if not item_errors:
        passed.append("③ 证据编号连续无重复：" + ("；".join(item_notes) or "通过"))

    if mode == "C":
        item_errors, item_notes = check_dangling_claims(text, lines, tables)
        errors.extend(item_errors)
        if not item_errors:
            passed.append("④ 主张-证据映射无悬空主张：" + ("；".join(item_notes) or "通过"))

    return errors, passed


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="validate_evidence_report.py",
        description=(
            "证据类报告交付门禁校验（单元10 综合证据策略）。"
            "校验三性表格结构、证据链缺口标注、证据编号连续性、模式C 悬空主张；"
            "未通过以退出码 1 阻断交付。"
        ),
        epilog=(
            "示例：\n"
            "  python3 validate_evidence_report.py report.md --mode A\n"
            "  python3 validate_evidence_report.py report.md   # 自动识别模式\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("report", type=Path, help="待校验的报告文件（.md / .txt，Markdown 结构）")
    parser.add_argument(
        "--mode",
        choices=["A", "B", "C", "a", "b", "c", "auto"],
        default="auto",
        help="报告模式：A=综合证据分析 / B=质证意见 / C=证据链构建；默认 auto 自动识别",
    )
    args = parser.parse_args()

    if not args.report.exists():
        print(f"校验失败：报告文件不存在：{args.report}", file=sys.stderr)
        return 1
    try:
        text = args.report.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"校验失败：无法读取报告文件：{exc}", file=sys.stderr)
        return 1
    if not text.strip():
        print("校验失败：报告文件为空", file=sys.stderr)
        return 1

    mode = args.mode.upper()
    if mode == "AUTO":
        detected = detect_mode(text)
        if detected is None:
            print(
                "校验失败：无法自动识别报告模式，请用 --mode A|B|C 显式指定",
                file=sys.stderr,
            )
            return 1
        mode = detected
        print(f"自动识别模式：{mode}", flush=True)

    errors, passed = run_checks(text, mode)

    if errors:
        print(f"\n证据报告门禁校验未通过（模式{mode}），共 {len(errors)} 项拦截：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print("\n禁止交付：请按上述清单修复报告后重新运行本脚本。", file=sys.stderr)
        return 1

    print(f"\n证据报告门禁校验通过（模式{mode}）：{args.report}")
    for item in passed:
        print(f"- {item}")
    print("可进入大纲确认与 docx 生成环节。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
