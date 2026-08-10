#!/usr/bin/env python3
"""Validate the ordered E→F→U→D→A→RO→SC fact-analysis workpapers."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


FILES = {
    "附件与证据目录.csv": {"证据编号", "真实附件名称", "具体定位", "证据状态", "支持事实"},
    "事实与不确定性.csv": {
        "事实编号", "评价单元编号", "事实来源类型", "主体", "产品或系统", "事实期间",
        "处理动作", "原子化事实", "证据编号及精确定位", "样本与外推边界",
        "不确定性编号", "竞争性假设", "最小补证", "核验程序", "事实状态",
    },
    "信息分类.csv": {
        "数据分类编号", "数据项目或组合", "关联事实编号", "不确定性编号",
        "是否个人信息", "是否敏感个人信息", "是否达到匿名化", "分类结论前提",
    },
    "处理活动与角色.csv": {
        "活动编号", "处理活动", "数据分类编号", "关联事实编号", "不确定性编号",
        "法律角色编号", "目的决定权", "核心方式决定权", "角色结论",
    },
    "处理情形与模块适用性.csv": {
        "处理情形编号", "处理活动编号", "法律角色编号", "情形类型", "情形状态",
        "触发事实编号", "排除事实编号", "关键数据分类编号", "不确定性编号",
        "关联模块", "核验程序",
    },
}

FACT_STATUSES = {"已确认", "材料未提及", "已有线索但证据不足", "证据相互冲突", "已有积极证据证明不存在"}
SCENARIO_STATUSES = {"已确认涉及", "有涉及迹象但待确认", "有积极证据证明不涉及"}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    return headers, rows


def ids(value: str, prefix: str) -> set[str]:
    return set(re.findall(rf"(?<![A-Z]){re.escape(prefix)}\d{{3}}(?!\d)", value or ""))


def require_reference(
    errors: list[str], record: str, field: str, value: str, prefix: str, known: set[str]
) -> None:
    found = ids(value, prefix)
    if not found:
        errors.append(f"{record}的{field}未引用{prefix}编号")
    for item in sorted(found - known):
        errors.append(f"{record}的{field}引用不存在的编号{item}")


def validate(root: Path, schema_only: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    data: dict[str, list[dict[str, str]]] = {}

    for filename, required in FILES.items():
        path = root / filename
        if not path.is_file():
            errors.append(f"缺少事实顺序底稿：{filename}")
            continue
        headers, rows = read_csv(path)
        missing = sorted(required - set(headers))
        if missing:
            errors.append(f"{filename}缺少表头：{'、'.join(missing)}")
        data[filename] = rows

    if errors or schema_only:
        return errors, warnings
    if any(not rows for rows in data.values()):
        return ["事实顺序校验要求五张底稿均至少有一条有效记录"], warnings

    evidence_rows = data["附件与证据目录.csv"]
    fact_rows = data["事实与不确定性.csv"]
    class_rows = data["信息分类.csv"]
    activity_rows = data["处理活动与角色.csv"]
    scenario_rows = data["处理情形与模块适用性.csv"]

    known_e = {row["证据编号"] for row in evidence_rows if re.fullmatch(r"E\d{3}", row["证据编号"])}
    known_f = {row["事实编号"] for row in fact_rows if re.fullmatch(r"F\d{3}", row["事实编号"])}
    known_u = set().union(*(ids(row["不确定性编号"], "U") for row in fact_rows))
    known_d = {row["数据分类编号"] for row in class_rows if re.fullmatch(r"D\d{3}", row["数据分类编号"])}
    known_a = {row["活动编号"] for row in activity_rows if re.fullmatch(r"A\d{3}", row["活动编号"])}
    known_ro = {row["法律角色编号"] for row in activity_rows if re.fullmatch(r"RO\d{3}", row["法律角色编号"])}

    for row in evidence_rows:
        record = row["证据编号"] or "证据空编号"
        if not re.fullmatch(r"E\d{3}", record):
            errors.append(f"证据编号无效：{record}")
        if not row["真实附件名称"] or not row["具体定位"]:
            errors.append(f"{record}缺少真实附件名称或具体定位")

    for row in fact_rows:
        record = row["事实编号"] or "事实空编号"
        if not re.fullmatch(r"F\d{3}", record):
            errors.append(f"事实编号无效：{record}")
        require_reference(errors, record, "证据编号及精确定位", row["证据编号及精确定位"], "E", known_e)
        for field in ("评价单元编号", "事实来源类型", "主体", "产品或系统", "事实期间", "处理动作", "原子化事实", "样本与外推边界", "事实状态"):
            if not row[field]:
                errors.append(f"{record}缺少{field}")
        status = row["事实状态"]
        if status not in FACT_STATUSES:
            errors.append(f"{record}事实状态无效：{status or '空'}")
        if status != "已确认":
            for field in ("不确定性编号", "竞争性假设", "最小补证", "核验程序"):
                if not row[field]:
                    errors.append(f"{record}为非确定事实但缺少{field}")

    for row in class_rows:
        record = row["数据分类编号"] or "分类空编号"
        if not re.fullmatch(r"D\d{3}", record):
            errors.append(f"数据分类编号无效：{record}")
        require_reference(errors, record, "关联事实编号", row["关联事实编号"], "F", known_f)
        for item in ids(row["不确定性编号"], "U") - known_u:
            errors.append(f"{record}引用不存在的不确定性编号{item}")

    for row in activity_rows:
        record = row["活动编号"] or "活动空编号"
        if not re.fullmatch(r"A\d{3}", record):
            errors.append(f"处理活动编号无效：{record}")
        if not re.fullmatch(r"RO\d{3}", row["法律角色编号"]):
            errors.append(f"{record}法律角色编号无效：{row['法律角色编号'] or '空'}")
        require_reference(errors, record, "数据分类编号", row["数据分类编号"], "D", known_d)
        require_reference(errors, record, "关联事实编号", row["关联事实编号"], "F", known_f)
        if not row["目的决定权"] or not row["核心方式决定权"] or not row["角色结论"]:
            errors.append(f"{record}缺少决定权分析或角色结论")

    for row in scenario_rows:
        record = row["处理情形编号"] or "情形空编号"
        if not re.fullmatch(r"SC\d{3}", record):
            errors.append(f"处理情形编号无效：{record}")
        require_reference(errors, record, "处理活动编号", row["处理活动编号"], "A", known_a)
        require_reference(errors, record, "法律角色编号", row["法律角色编号"], "RO", known_ro)
        require_reference(errors, record, "关键数据分类编号", row["关键数据分类编号"], "D", known_d)
        status = row["情形状态"]
        if status not in SCENARIO_STATUSES:
            errors.append(f"{record}情形状态无效：{status or '空'}")
        if status == "有积极证据证明不涉及":
            require_reference(errors, record, "排除事实编号", row["排除事实编号"], "F", known_f)
        else:
            require_reference(errors, record, "触发事实编号", row["触发事实编号"], "F", known_f)
        if status == "有涉及迹象但待确认" and not row["不确定性编号"]:
            errors.append(f"{record}待确认但未引用U编号")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验E→F→U→D→A→RO→SC事实顺序底稿")
    parser.add_argument("directory")
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args()
    root = Path(args.directory)
    if not root.is_dir():
        print(f"错误：目录不存在：{root}")
        return 2
    errors, warnings = validate(root, args.schema_only)
    for item in errors:
        print("错误：" + item)
    for item in warnings:
        print("警告：" + item)
    if errors:
        print(f"事实顺序校验未通过：{len(errors)}项错误，{len(warnings)}项警告")
        return 1
    print(f"事实顺序校验通过：0项错误，{len(warnings)}项警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
