#!/usr/bin/env python3
"""根据完整输入复算 RICE、ICE 或加权优先级，不补默认值。"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


METHOD_COLUMNS = {
    "rice": ("item", "reach", "impact", "confidence", "effort"),
    "ice": ("item", "impact", "confidence", "ease"),
}


def parse_number(raw: str, row_number: int, column: str) -> Decimal:
    try:
        value = Decimal(raw.strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"第 {row_number} 行的 {column} 不是有效数字：{raw!r}") from None
    if not value.is_finite():
        raise ValueError(f"第 {row_number} 行的 {column} 必须是有限数字")
    return value


def parse_weights(raw: str | None) -> dict[str, Decimal]:
    if not raw:
        raise ValueError("weighted 方法必须显式提供 --weights，例如 value=0.5,confidence=0.3,ease=0.2")
    weights: dict[str, Decimal] = {}
    for part in raw.split(","):
        if "=" not in part:
            raise ValueError(f"权重格式错误：{part!r}")
        name, value_raw = (piece.strip() for piece in part.split("=", 1))
        if not name or name == "item" or name == "score" or name in weights:
            raise ValueError(f"权重字段无效或重复：{name!r}")
        value = parse_number(value_raw, 0, f"weight:{name}")
        if value <= 0:
            raise ValueError(f"权重必须大于 0：{name}={value}")
        weights[name] = value
    if not math.isclose(float(sum(weights.values())), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"权重之和必须等于 1，当前为 {sum(weights.values())}")
    return weights


def validate_headers(fieldnames: list[str] | None, required: tuple[str, ...]) -> None:
    if not fieldnames:
        raise ValueError("CSV 缺少表头")
    missing = [name for name in required if name not in fieldnames]
    if missing:
        raise ValueError(f"CSV 缺少必要列：{', '.join(missing)}")
    if "score" in fieldnames or "rank" in fieldnames:
        raise ValueError("输入 CSV 不得包含保留列 score 或 rank")


def compute(method: str, row: dict[str, str], row_number: int, weights: dict[str, Decimal]) -> Decimal:
    if not row.get("item", "").strip():
        raise ValueError(f"第 {row_number} 行 item 为空")

    if method == "rice":
        reach = parse_number(row["reach"], row_number, "reach")
        impact = parse_number(row["impact"], row_number, "impact")
        confidence = parse_number(row["confidence"], row_number, "confidence")
        effort = parse_number(row["effort"], row_number, "effort")
        if reach < 0 or impact < 0:
            raise ValueError(f"第 {row_number} 行 reach 与 impact 不能为负")
        if not Decimal("0") <= confidence <= Decimal("1"):
            raise ValueError(f"第 {row_number} 行 confidence 必须在 0 到 1 之间，不接受百分数写法")
        if effort <= 0:
            raise ValueError(f"第 {row_number} 行 effort 必须大于 0")
        return reach * impact * confidence / effort

    if method == "ice":
        impact = parse_number(row["impact"], row_number, "impact")
        confidence = parse_number(row["confidence"], row_number, "confidence")
        ease = parse_number(row["ease"], row_number, "ease")
        if impact < 0 or ease < 0:
            raise ValueError(f"第 {row_number} 行 impact 与 ease 不能为负")
        if not Decimal("0") <= confidence <= Decimal("1"):
            raise ValueError(f"第 {row_number} 行 confidence 必须在 0 到 1 之间，不接受百分数写法")
        return impact * confidence * ease

    score = Decimal("0")
    for column, weight in weights.items():
        score += parse_number(row[column], row_number, column) * weight
    return score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按完整输入复算优先级；不补默认值，也不判断输入证据是否可靠")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--method", required=True, choices=("rice", "ice", "weighted"))
    parser.add_argument("--weights", help="weighted 方法的字段与权重，权重之和必须为 1")
    parser.add_argument("--output", type=Path, help="输出 CSV；不提供时写到标准输出")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的输出文件；不能覆盖输入文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.csv_file.is_file():
        print(f"ERROR: 输入 CSV 不存在：{args.csv_file}", file=sys.stderr)
        return 2

    try:
        if args.output:
            if args.output.resolve() == args.csv_file.resolve():
                raise ValueError("输出文件不能与输入文件相同")
            if args.output.exists() and not args.force:
                raise ValueError(f"输出文件已存在：{args.output}；如需覆盖请显式提供 --force")
        weights = parse_weights(args.weights) if args.method == "weighted" else {}
        with args.csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = ("item", *weights.keys()) if args.method == "weighted" else METHOD_COLUMNS[args.method]
            validate_headers(reader.fieldnames, required)
            rows = list(reader)
        if not rows:
            raise ValueError("CSV 没有数据行")

        scored: list[tuple[Decimal, int, dict[str, str]]] = []
        for row_number, row in enumerate(rows, start=2):
            score = compute(args.method, row, row_number, weights)
            scored.append((score, row_number, row))
        scored.sort(key=lambda item: (-item[0], item[1]))

        fieldnames = list(reader.fieldnames or []) + ["score", "rank"]
        output_mode = "w" if args.force else "x"
        output_handle = args.output.open(output_mode, encoding="utf-8", newline="") if args.output else sys.stdout
        try:
            writer = csv.DictWriter(output_handle, fieldnames=fieldnames)
            writer.writeheader()
            for rank, (score, _row_number, row) in enumerate(scored, start=1):
                writer.writerow({**row, "score": format(score.normalize(), "f"), "rank": rank})
        finally:
            if args.output:
                output_handle.close()
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
