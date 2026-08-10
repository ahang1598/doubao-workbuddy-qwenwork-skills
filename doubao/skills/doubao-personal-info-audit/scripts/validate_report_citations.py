#!/usr/bin/env python3
"""Validate citation IDs and output form in an audit-report Markdown file."""

import re
import sys
from pathlib import Path


CITATION_BLOCK_RE = re.compile(r"〔([^〕]+)〕")
SOURCE_ID_RE = re.compile(r"\b((?:AR|[LRSJPEFC])\d{3})(?:-\d+)?\b")
LEGAL_ID_RE = re.compile(r"\b((?:AR|[LRS])\d{3})\b")
TABLE_ID_RE = re.compile(r"^\|\s*((?:AR|[LRSJPEFC])\d{3})(?:-\d+)?\b", re.MULTILINE)
HEADING_ID_RE = re.compile(r"^#{3,5}\s+((?:AR|[LRSJPEFC])\d{3})(?:-\d+)?\b", re.MULTILINE)
ARTICLE_RE = re.compile(r"第[一二三四五六七八九十百千〇零两0-9]+条")


def markdown_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def validate_legal_rule_tables(text: str) -> tuple[list[str], int]:
    """Require every L/AR/R/S table row to carry a concrete rule-content cell."""
    errors: list[str] = []
    legal_rows = 0
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        headers = markdown_cells(line)
        if not any("法源编号" in header for header in headers) or "具体规则内容" not in headers:
            continue
        rule_index = headers.index("具体规则内容")
        row_index = index + 2
        table_rows: list[tuple[str, list[str]]] = []
        while row_index < len(lines) and lines[row_index].lstrip().startswith("|"):
            cells = markdown_cells(lines[row_index])
            row_index += 1
            source_match = re.match(r"((?:AR|[LRS])\d{3})(?:-\d+)?\b", cells[0]) if cells else None
            if not source_match:
                continue
            source_id = source_match.group(1)
            table_rows.append((source_id, cells))
            legal_rows += 1
            content = cells[rule_index].strip() if rule_index < len(cells) else ""
            compact = re.sub(r"[【】*`\s]", "", content)
            if len(compact) < 12:
                errors.append(f"法条表{cells[0]}未展示足够具体的规则内容")
            if compact in {"相关规定", "详见附件", "见附件", "第X条"}:
                errors.append(f"法条表{cells[0]}以笼统文字代替具体规则内容")
        detail_rows = [
            (source_id, cells)
            for source_id, cells in table_rows
            if any("下位法细化补充" in cell or "配套规范实施补充" in cell for cell in cells)
        ]
        if detail_rows:
            has_upper = any(any("上位法基础依据" in cell for cell in cells) for _, cells in table_rows)
            if not has_upper:
                errors.append("法条表引用下位法或配套规范，但未同时列示上位法基础依据")
            for source_id, cells in detail_rows:
                joined = " ".join(cells)
                if source_id.startswith("S") and "下位法细化补充" in joined:
                    errors.append(f"法条表{source_id}为标准/指南，不得标注为下位法")
                if "触发" not in joined or "适用" not in joined:
                    errors.append(f"法条表{source_id}未说明细化规范的触发事实和适用结论")
                if "不适用" in joined:
                    errors.append(f"法条表{source_id}标记为不适用，不应作为正文法源列示")
    if "〔" in text and not legal_rows:
        errors.append("报告存在引文，但未发现含“具体规则内容”的L/AR/R/S法条表行")
    return errors, legal_rows


def validate(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    table_errors, legal_row_count = validate_legal_rule_tables(text)
    errors.extend(table_errors)

    blocks = CITATION_BLOCK_RE.findall(text)
    cited = {item for block in blocks for item in SOURCE_ID_RE.findall(block)}
    defined_list = TABLE_ID_RE.findall(text) + HEADING_ID_RE.findall(text)
    defined = set(defined_list)

    # 同一法源会在不同问题的法条表和附件中重复展示具体规则；重复出现是
    # 交叉引用，不属于同号异源。来源唯一性由法规数据库主键另行校验。

    undefined = sorted(cited - defined)
    if undefined:
        errors.append("正文引用但附件未定义：" + "、".join(undefined))

    unused = sorted(item for item in defined - cited if item.startswith(("L", "AR", "R", "S", "J", "P", "E")))
    if unused:
        warnings.append("附件定义但正文未引用：" + "、".join(unused))

    appendix_pos = text.find("## 附件二")
    body = text if appendix_pos < 0 else text[:appendix_pos]
    for line_no, line in enumerate(body.splitlines(), 1):
        if "http://" in line or "https://" in line or re.search(r"\[[^]]+\]\(https?://", line):
            errors.append(f"第{line_no}行正文含网址或Markdown链接，应移入附件二")
        legal_table_row = re.match(r"^\|\s*(?:AR|[LRS])\d{3}(?:-\d+)?\b", line)
        if ARTICLE_RE.search(line) and not legal_table_row and not any(LEGAL_ID_RE.search(block) for block in CITATION_BLOCK_RE.findall(line)):
            warnings.append(f"第{line_no}行含具体法条但没有L/AR/R/S来源编号")
        if "相关法律法规" in line and not ARTICLE_RE.search(line):
            warnings.append(f"第{line_no}行使用笼统的“相关法律法规”，应写明规范和条款")

    opinion_count = len(re.findall(r"^\|\s*(?:审计观点|⑨审计结论)\s*\|", text, re.MULTILINE))
    if opinion_count and legal_row_count < opinion_count:
        errors.append(f"审计观点共{opinion_count}项，但含具体规则内容的法条表行仅{legal_row_count}项")

    return errors, warnings


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python validate_report_citations.py <审计报告.md>")
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"错误：文件不存在：{path}")
        return 2
    errors, warnings = validate(path)
    for item in errors:
        print("错误：" + item)
    for item in warnings:
        print("警告：" + item)
    if errors:
        print(f"引注校验未通过：{len(errors)}项错误，{len(warnings)}项警告")
        return 1
    print(f"引注校验通过：0项错误，{len(warnings)}项警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
