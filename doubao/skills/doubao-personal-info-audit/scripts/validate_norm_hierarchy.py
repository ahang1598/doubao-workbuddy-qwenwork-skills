#!/usr/bin/env python3
"""Validate upper-law and detailed-rule decisions in the applicable-norm matrix."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


REQUIRED_HEADERS = {
    "规则编号",
    "来源编号",
    "规范全称",
    "条款或章节",
    "具体规则内容",
    "本案对应事实",
    "上位依据编号及条款",
    "下位法或配套规范编号及条款",
    "衔接类型",
    "下位规范触发事实",
    "下位规范适用状态",
    "下位规范不适用理由",
    "层级权限冲突核验",
    "正文引用组合",
    "待补事实与核验程序",
}

VALID_STATUSES = {"适用", "不适用", "无下位配套", "待确认"}
RULE_ID_RE = re.compile(r"^NR\d{3}$")
DIRECT_LEGAL_ID_RE = re.compile(r"\b(?:L|AR|R)\d{3}\b")
DETAIL_ID_RE = re.compile(r"\b(?:L|AR|R|S)\d{3}\b")
FACT_ID_RE = re.compile(r"\b(?:F|D|A|RO|SC)\d{3}\b")


def source_ids(value: str, pattern: re.Pattern[str]) -> set[str]:
    return set(pattern.findall(value or ""))


def validate_row(row: dict[str, str], line_no: int) -> list[str]:
    errors: list[str] = []
    rule_id = row.get("规则编号", "").strip()
    label = f"第{line_no}行{f'（{rule_id}）' if rule_id else ''}"
    if not RULE_ID_RE.fullmatch(rule_id):
        errors.append(f"{label}规则编号应为NR###")

    upper_text = row.get("上位依据编号及条款", "").strip()
    detail_text = row.get("下位法或配套规范编号及条款", "").strip()
    status = row.get("下位规范适用状态", "").strip()
    relation = row.get("衔接类型", "").strip()
    trigger = row.get("下位规范触发事实", "").strip()
    exclusion = row.get("下位规范不适用理由", "").strip()
    conflict = row.get("层级权限冲突核验", "").strip()
    citation = row.get("正文引用组合", "").strip()
    pending = row.get("待补事实与核验程序", "").strip()

    upper_ids = source_ids(upper_text, DIRECT_LEGAL_ID_RE)
    detail_ids = source_ids(detail_text, DETAIL_ID_RE)
    citation_ids = source_ids(citation, DETAIL_ID_RE)

    if not upper_ids:
        errors.append(f"{label}缺少L/AR/R上位依据编号及具体条款")
    if status not in VALID_STATUSES:
        errors.append(f"{label}下位规范适用状态必须为：适用/不适用/无下位配套/待确认")
    if not conflict:
        errors.append(f"{label}未记录制定权限、效力和冲突核验")
    if upper_ids and not upper_ids.issubset(citation_ids):
        errors.append(f"{label}正文引用组合未完整包含上位依据：{'、'.join(sorted(upper_ids))}")

    if status == "适用":
        if not detail_ids:
            errors.append(f"{label}状态为适用但未列下位法或配套规范编号及条款")
        if not relation:
            errors.append(f"{label}状态为适用但未说明上下位或配套衔接类型")
        if not FACT_ID_RE.search(trigger):
            errors.append(f"{label}状态为适用但缺少F/D/A/RO/SC触发事实编号")
        if any(term in conflict for term in ("待确认", "待复核", "疑似冲突", "越权")):
            errors.append(f"{label}权限或冲突尚未排除，不得将细化规范标为适用")
        if detail_ids and not detail_ids.issubset(citation_ids):
            errors.append(f"{label}细化规范适用但正文未组合引用：{'、'.join(sorted(detail_ids))}")

    elif status == "不适用":
        if not detail_ids:
            errors.append(f"{label}状态为不适用但未登记被排除的候选细化规范")
        if not exclusion:
            errors.append(f"{label}状态为不适用但未写明排除理由")
        if not FACT_ID_RE.search(trigger):
            errors.append(f"{label}状态为不适用但缺少积极排除事实编号")
        overlap = detail_ids & citation_ids
        if overlap:
            errors.append(f"{label}细化规范不适用却进入正文引用组合：{'、'.join(sorted(overlap))}")

    elif status == "无下位配套":
        if detail_text:
            errors.append(f"{label}状态为无下位配套时，候选细化规范字段应留空")
        if not exclusion or "检索" not in exclusion:
            errors.append(f"{label}无下位配套时应在不适用理由中记录检索范围或检索过程")

    elif status == "待确认":
        if not detail_ids:
            errors.append(f"{label}状态为待确认但未登记候选细化规范")
        if not pending:
            errors.append(f"{label}状态为待确认但未列最小补证与核验程序")
        overlap = detail_ids & citation_ids
        if overlap:
            errors.append(f"{label}候选细化规范待确认，不得进入确定性正文引用组合：{'、'.join(sorted(overlap))}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验适用规范矩阵中的上下位法及配套规范衔接")
    parser.add_argument("matrix", help="适用规范矩阵CSV")
    parser.add_argument("--schema-only", action="store_true", help="仅校验表头")
    args = parser.parse_args()

    path = Path(args.matrix)
    if not path.is_file():
        print(f"错误：文件不存在：{path}")
        return 2

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_HEADERS - headers)
        if missing:
            print("错误：缺少表头：" + "、".join(missing))
            return 1
        if args.schema_only:
            print("上下位规范矩阵结构校验通过")
            return 0
        rows = list(reader)

    if not rows:
        print("错误：适用规范矩阵没有数据行")
        return 1

    errors: list[str] = []
    for line_no, row in enumerate(rows, 2):
        if not any((value or "").strip() for value in row.values()):
            continue
        errors.extend(validate_row(row, line_no))

    for error in errors:
        print("错误：" + error)
    if errors:
        print(f"上下位规范矩阵校验未通过：{len(errors)}项错误")
        return 1
    print(f"上下位规范矩阵校验通过：{len(rows)}条记录")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
