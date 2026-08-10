#!/usr/bin/env python3
"""Mechanically audit activity subtotals and net rows in cash-flow XLSX files."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from time_window_audit import _xlsx_rows, xlsx_sheet_names


SECTION = re.compile(r"(经营|投资|筹资).{0,12}活动.*现金流量")
INFLOW = re.compile(r"现金流入小计|cash\s+inflow\s+subtotal", re.I)
OUTFLOW = re.compile(r"现金流出小计|cash\s+outflow\s+subtotal", re.I)
NET = re.compile(r"活动产生的现金流量净额|net\s+cash\s+flow", re.I)
PERIOD = re.compile(r"(?:年度\s*[:：]?\s*)?(\d{4})")


def _number(value: object) -> float:
    if value in {"", None}:
        return 0.0
    if isinstance(value, bool):
        raise ValueError("布尔值不能作为金额")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"无法解析金额 {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError("金额不是有限数")
    return result


def _find_columns(rows: list[dict[int, object]]) -> tuple[int, int]:
    for row in rows[:12]:
        labels = {str(value or "").strip(): col for col, value in row.items()}
        label_col = next(
            (col for text, col in labels.items() if text in {"项目", "Item", "ITEM"}),
            None,
        )
        value_col = next(
            (
                col
                for text, col in labels.items()
                if text in {"本期金额", "本期数", "Current period", "Current Period"}
            ),
            None,
        )
        if label_col and value_col:
            return label_col, value_col
    raise ValueError("找不到“项目/本期金额”表头")


def _period(rows: list[dict[int, object]]) -> str:
    for row in rows[:8]:
        for value in row.values():
            match = PERIOD.search(str(value or ""))
            if match:
                return match.group(1)
    return ""


def audit_cashflow(path: Path, tolerance: float = 0.01) -> dict:
    if path.suffix.lower() != ".xlsx":
        raise ValueError("cashflow_audit 仅直接支持 .xlsx")
    checks: list[dict] = []
    anomalies: list[dict] = []

    for sheet in xlsx_sheet_names(path):
        rows = _xlsx_rows(path, sheet)
        label_col, value_col = _find_columns(rows)
        period = _period(rows)
        labels = [str(row.get(label_col, "") or "").strip() for row in rows]

        section_starts: list[tuple[int, str]] = []
        for idx, label in enumerate(labels):
            match = SECTION.search(label)
            if match and ("：" in label or ":" in label or label.startswith(("一、", "二、", "三、"))):
                section_starts.append((idx, match.group(1)))
        for pos, (start, section) in enumerate(section_starts):
            end = (
                section_starts[pos + 1][0]
                if pos + 1 < len(section_starts)
                else len(rows)
            )
            inflow_idx = next(
                (idx for idx in range(start + 1, end) if INFLOW.search(labels[idx])),
                None,
            )
            outflow_idx = next(
                (idx for idx in range(start + 1, end) if OUTFLOW.search(labels[idx])),
                None,
            )
            net_idx = next(
                (idx for idx in range(start + 1, end) if NET.search(labels[idx])),
                None,
            )

            inflow_value = None
            outflow_value = None
            if inflow_idx is not None:
                components = [
                    _number(rows[idx].get(value_col))
                    for idx in range(start + 1, inflow_idx)
                    if labels[idx]
                ]
                recomputed = sum(components)
                source = _number(rows[inflow_idx].get(value_col))
                check = _check(
                    sheet, period, section, "现金流入小计", inflow_idx + 1,
                    source, recomputed, tolerance
                )
                checks.append(check)
                if check["status"] == "FAIL":
                    anomalies.append(check)
                inflow_value = recomputed

            if outflow_idx is not None and inflow_idx is not None:
                components = [
                    _number(rows[idx].get(value_col))
                    for idx in range(inflow_idx + 1, outflow_idx)
                    if labels[idx]
                ]
                recomputed = sum(components)
                source = _number(rows[outflow_idx].get(value_col))
                check = _check(
                    sheet, period, section, "现金流出小计", outflow_idx + 1,
                    source, recomputed, tolerance
                )
                checks.append(check)
                if check["status"] == "FAIL":
                    anomalies.append(check)
                outflow_value = recomputed

            if net_idx is not None and inflow_value is not None and outflow_value is not None:
                recomputed = inflow_value - outflow_value
                source = _number(rows[net_idx].get(value_col))
                check = _check(
                    sheet, period, section, "活动现金流量净额", net_idx + 1,
                    source, recomputed, tolerance
                )
                checks.append(check)
                if check["status"] == "FAIL":
                    anomalies.append(check)

    return {
        "generated_by": "cashflow_audit.py",
        "source_path": str(path.resolve()),
        "checks": checks,
        "anomalies": anomalies,
        "check_count": len(checks),
        "anomaly_count": len(anomalies),
        "anomaly_markdown": _anomaly_markdown(anomalies),
    }


def _format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"
    return f"{value:,.2f}"


def _anomaly_markdown(anomalies: list[dict]) -> str:
    lines = [
        "| 期间 | 活动 | 恒等式 | 源表值 | 重算值 | 差异 |",
        "|---|---|---|---:|---:|---:|",
    ]
    for item in anomalies:
        lines.append(
            "| {period} | {section} | {relation} | {source} | {recomputed} | {difference} |".format(
                period=item["period"] or item["sheet"],
                section=item["section"],
                relation=item["relation"],
                source=_format_number(item["source_value"]),
                recomputed=_format_number(item["recomputed_value"]),
                difference=_format_number(item["difference"]),
            )
        )
    return "\n".join(lines)


def _check(
    sheet: str,
    period: str,
    section: str,
    relation: str,
    row: int,
    source: float,
    recomputed: float,
    tolerance: float,
) -> dict:
    difference = recomputed - source
    return {
        "sheet": sheet,
        "period": period,
        "section": section,
        "relation": relation,
        "row": row,
        "source_value": source,
        "recomputed_value": recomputed,
        "difference": difference,
        "status": "PASS" if abs(difference) <= tolerance else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--output")
    parser.add_argument("--markdown-output")
    parser.add_argument("--tolerance", type=float, default=0.01)
    args = parser.parse_args()
    try:
        result = audit_cashflow(Path(args.source), args.tolerance)
    except Exception as exc:
        print(f"FAIL\n- {exc}")
        return 1
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    if args.markdown_output:
        Path(args.markdown_output).write_text(
            result["anomaly_markdown"] + "\n", encoding="utf-8"
        )
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
