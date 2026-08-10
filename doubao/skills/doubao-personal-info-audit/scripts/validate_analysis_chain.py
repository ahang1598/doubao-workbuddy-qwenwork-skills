#!/usr/bin/env python3
"""Validate the mandatory 11-stage personal-information audit analysis chain."""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


STAGES = {
    1: ("证据", re.compile(r"^E\d{3}$")),
    2: ("事实", re.compile(r"^F\d{3}$")),
    3: ("不确定性", re.compile(r"^U\d{3}$")),
    4: ("数据分类", re.compile(r"^D\d{3}$")),
    5: ("处理活动", re.compile(r"^A\d{3}$")),
    6: ("法律角色", re.compile(r"^RO\d{3}$")),
    7: ("处理情形", re.compile(r"^SC\d{3}$")),
    8: ("适用规则", re.compile(r"^NR\d{3}$")),
    9: ("审计结论", re.compile(r"^C\d{3}$")),
    10: ("风险", re.compile(r"^RK\d{3}$")),
    11: ("整改", re.compile(r"^RM\d{3}$")),
}

REQUIRED_HEADERS = {
    "链条编号", "审计发现编号", "环节序号", "分析环节", "本环节编号",
    "分析内容", "直接上游编号", "证据或法源定位", "状态或结论", "待补数据与核验程序",
}


def split_ids(value: str) -> set[str]:
    return set(re.findall(r"(?:RO|SC|NR|RK|RM|[EFUDAC])\d{3}", value or ""))


def validate(path: Path, schema_only: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_HEADERS - headers)
        if missing:
            return ["缺少表头：" + "、".join(missing)], warnings
        rows = list(reader)

    if schema_only:
        return errors, warnings
    if not rows:
        return ["审计分析链没有有效数据行"], warnings

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    used_ids: set[str] = set()
    for line_no, row in enumerate(rows, 2):
        finding = row["审计发现编号"].strip()
        if not re.fullmatch(r"C\d{3}", finding):
            errors.append(f"第{line_no}行审计发现编号无效：{finding or '空'}")
        groups[finding].append(row)
        current = row["本环节编号"].strip()
        if current in used_ids:
            errors.append(f"本环节编号重复：{current}")
        used_ids.add(current)

    for finding, group in groups.items():
        parsed: list[tuple[int, dict[str, str]]] = []
        for row in group:
            try:
                sequence = int(row["环节序号"].strip())
            except ValueError:
                errors.append(f"{finding}存在非数字环节序号：{row['环节序号']}")
                continue
            parsed.append((sequence, row))
        parsed.sort(key=lambda item: item[0])
        sequences = [item[0] for item in parsed]
        if sequences != list(range(1, 12)):
            errors.append(f"{finding}环节必须且只能按1—11完整排列，当前为：{sequences}")
            continue

        previous_id = ""
        for sequence, row in parsed:
            expected_name, id_pattern = STAGES[sequence]
            stage_name = row["分析环节"].strip()
            current_id = row["本环节编号"].strip()
            if stage_name != expected_name:
                errors.append(f"{finding}第{sequence}环节应为“{expected_name}”，实际为“{stage_name}”")
            if not id_pattern.fullmatch(current_id):
                errors.append(f"{finding}第{sequence}环节编号无效：{current_id or '空'}")
            if len(re.sub(r"\s+", "", row["分析内容"])) < 8:
                errors.append(f"{finding}{current_id}分析内容过短或为空")
            if sequence > 1 and previous_id not in split_ids(row["直接上游编号"]):
                errors.append(f"{finding}{current_id}未直接引用上一环节{previous_id}")
            if sequence in {1, 8} and len(row["证据或法源定位"].strip()) < 4:
                errors.append(f"{finding}{current_id}缺少证据或法源精确定位")
            if sequence == 3 and not row["待补数据与核验程序"].strip():
                errors.append(f"{finding}{current_id}未说明待补数据/核验程序或积极排除证据")
            if sequence in {9, 10, 11} and not row["状态或结论"].strip():
                errors.append(f"{finding}{current_id}缺少结论、风险或整改状态")
            previous_id = current_id

        if parsed[8][1]["本环节编号"].strip() != finding:
            errors.append(f"{finding}第9环节本环节编号必须与审计发现编号一致")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验证据—事实—不确定性至整改的11环节审计分析链")
    parser.add_argument("csv_file")
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args()
    path = Path(args.csv_file)
    if not path.is_file():
        print(f"错误：文件不存在：{path}")
        return 2
    errors, warnings = validate(path, args.schema_only)
    for item in errors:
        print("错误：" + item)
    for item in warnings:
        print("警告：" + item)
    if errors:
        print(f"11环节分析链校验未通过：{len(errors)}项错误，{len(warnings)}项警告")
        return 1
    print(f"11环节分析链校验通过：0项错误，{len(warnings)}项警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
