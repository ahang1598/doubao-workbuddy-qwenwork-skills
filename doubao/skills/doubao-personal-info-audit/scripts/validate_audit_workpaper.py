#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""校验107项审计底稿的完整性和最低证据门槛。"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path


VALID_CONCLUSIONS = {"合规", "部分合规", "不合规", "无法判断", "不涉及"}
REQUIRED_HEADERS = {
    "子项编号",
    "模块",
    "审计结论",
    "关联事实",
    "审计证据",
    "直接法源",
    "法律要求",
    "差异或判断理由",
    "待补材料",
    "分析链编号",
    "不确定性编号",
    "数据分类编号",
    "处理活动编号",
    "法律角色编号",
    "处理情形编号",
    "适用规则编号",
    "风险编号",
    "整改编号",
    "对应正文问题",
}

CHAIN_REFERENCE_FIELDS = (
    "分析链编号", "审计证据", "关联事实", "不确定性编号", "数据分类编号",
    "处理活动编号", "法律角色编号", "处理情形编号", "适用规则编号",
    "对应正文问题", "风险编号", "整改编号",
)


def expected_items(checklist_path: Path) -> dict[str, str]:
    pattern = re.compile(r"^-\s+(\d+)\.(\d+)\s+(.+?)\s*$")
    expected: dict[str, str] = {}
    for line in checklist_path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        module_number = int(match.group(1))
        item_number = int(match.group(2))
        item_id = f"M{module_number:02d}-{item_number:02d}"
        expected[item_id] = match.group(3)
    if len(expected) != 107:
        raise ValueError(f"完整清单应包含107项，实际解析到{len(expected)}项")
    return expected


def normalize_item_id(value: str) -> str:
    text = value.strip().upper().replace("—", "-").replace("_", "-")
    patterns = [
        r"^M?(\d{1,2})[-.](\d{1,2})$",
        r"^M(\d{2})(\d{2})$",
    ]
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            return f"M{int(match.group(1)):02d}-{int(match.group(2)):02d}"
    return text


def read_rows(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames or []
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    return headers, rows


def require_fields(
    errors: list[str],
    item_id: str,
    row: dict[str, str],
    fields: tuple[str, ...],
    reason: str,
) -> None:
    missing = [field for field in fields if not row.get(field, "")]
    if missing:
        errors.append(f"{item_id}：{reason}，缺少“{'、'.join(missing)}”")


def validate(csv_path: Path, checklist_path: Path) -> tuple[list[str], Counter]:
    expected = expected_items(checklist_path)
    headers, rows = read_rows(csv_path)
    errors: list[str] = []

    missing_headers = sorted(REQUIRED_HEADERS - set(headers))
    if missing_headers:
        errors.append("缺少表头：" + "、".join(missing_headers))
        return errors, Counter()

    normalized_ids = [normalize_item_id(row.get("子项编号", "")) for row in rows]
    counts = Counter(normalized_ids)
    duplicates = sorted(item_id for item_id, count in counts.items() if item_id and count > 1)
    unknown = sorted(item_id for item_id in counts if item_id and item_id not in expected)
    missing = sorted(set(expected) - set(normalized_ids))

    if len(rows) != 107:
        errors.append(f"底稿应包含107条有效记录，实际为{len(rows)}条")
    if duplicates:
        errors.append("重复子项：" + "、".join(duplicates))
    if unknown:
        errors.append("未知子项：" + "、".join(unknown))
    if missing:
        errors.append("缺失子项：" + "、".join(missing))

    conclusion_counts: Counter = Counter()
    for index, row in enumerate(rows, start=2):
        item_id = normalize_item_id(row.get("子项编号", ""))
        if not item_id:
            errors.append(f"第{index}行：子项编号为空")
            continue
        if item_id not in expected:
            continue

        expected_module = item_id.split("-")[0]
        module = row.get("模块", "").upper()
        if module != expected_module:
            errors.append(f"{item_id}：模块应为{expected_module}，实际为{module or '空'}")

        conclusion = row.get("审计结论", "")
        if conclusion not in VALID_CONCLUSIONS:
            errors.append(
                f"{item_id}：审计结论应为五档之一，实际为“{conclusion or '空'}”"
            )
            continue
        conclusion_counts[conclusion] += 1

        if row.get("对应正文问题", ""):
            require_fields(
                errors,
                item_id,
                row,
                CHAIN_REFERENCE_FIELDS,
                "对应正文审计发现的子项必须完整引用11环节分析链",
            )

        if conclusion == "合规":
            require_fields(
                errors,
                item_id,
                row,
                ("关联事实", "审计证据", "直接法源", "法律要求", "差异或判断理由"),
                "合规结论必须具有事实、履行证据、直接法源、规则和要件对照",
            )
        elif conclusion in {"部分合规", "不合规"}:
            require_fields(
                errors,
                item_id,
                row,
                ("关联事实", "审计证据", "直接法源", "法律要求", "差异或判断理由"),
                f"{conclusion}结论必须具有事实、证据、直接法源、规则和差异分析",
            )
        elif conclusion == "无法判断":
            require_fields(
                errors,
                item_id,
                row,
                ("直接法源", "法律要求", "差异或判断理由", "待补材料"),
                "无法判断必须说明候选直接法源、适用要求、判断障碍和待补材料",
            )
        elif conclusion == "不涉及":
            if not row.get("关联事实") and not row.get("差异或判断理由"):
                errors.append(f"{item_id}：不涉及必须记录积极排除事实")

    return errors, conclusion_counts


def main() -> None:
    parser = argparse.ArgumentParser(description="校验26模块107项审计底稿")
    parser.add_argument("csv", help="107项点检.csv路径")
    parser.add_argument(
        "--checklist",
        help="完整清单Markdown路径；默认使用Skill内置清单",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    csv_path = Path(args.csv)
    checklist_path = (
        Path(args.checklist)
        if args.checklist
        else skill_dir / "references" / "2、审计报告各模块审计点完整清单.md"
    )

    if not csv_path.exists():
        raise SystemExit(f"底稿CSV不存在：{csv_path}")
    if not checklist_path.exists():
        raise SystemExit(f"完整清单不存在：{checklist_path}")

    try:
        errors, counts = validate(csv_path, checklist_path)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error

    if errors:
        print("校验未通过：")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("【评估完成确认】")
    print("已完成全部26个模块、107个子项的合规评估。")
    for conclusion in ("合规", "部分合规", "不合规", "无法判断", "不涉及"):
        print(f"- {conclusion}子项：{counts[conclusion]}项")
    print("完整性校验：26个模块、107个子项，无缺号、无重复、无空结论。")
    print("审计底稿校验通过，可以进入报告组装和成果输出阶段。")


if __name__ == "__main__":
    main()
