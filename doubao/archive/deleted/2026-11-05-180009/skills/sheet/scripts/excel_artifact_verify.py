#!/usr/bin/env python3
"""Deterministic checks for exported xlsx artifacts.

Default run takes just the xlsx path: it reopens the workbook, flags cached
Excel error values, missing `_xlfn.` prefixes and foreground-only solid
conditional fills that can render differently across Excel and previews.
Use --require-formulas/charts/pivots/format for explicit task requirements.
A successful static scan does not verify calculation results or unstated needs.

`--contract` is optional and hand-written; there is no generator for it. The
file must be `{"status": "success", "contract": {"artifact": {"kind": "xlsx",
"path": "<same path as the argument>", "xlsx_verification": "local_working_file"},
...}}` — anything else is rejected as invalid. Checks only observable workbook
facts; it does not infer whether a chart or formula is semantically correct
beyond explicit contract fields.
"""
from __future__ import annotations

import argparse
import json
import math
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

import sys as _sys

# 同级脚本随 skill 一起分发。按自身位置补一次 sys.path，这样无论调用方是直接
# 执行、还是用 spec_from_file_location 加载本模块，兼容性判据都取得到。
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from excel_conditional_format_verify import check_file  # noqa: E402

try:
    from _xlsx_text import load_workbook
    from openpyxl.utils.cell import range_boundaries
except ModuleNotFoundError as _missing:  # 缺少 Python 库时先安装，再重跑原操作
    import sys

    sys.stderr.write(
        f"\n[excel_artifact_verify] 本机 Python 缺少 {_missing.name}，本脚本未执行，本地文件未修改。\n"
        "  请在运行本脚本的同一 Python 环境安装：python3 -m pip install openpyxl\n"
        "  安装成功后重跑原命令；安装失败再说明未完成，不能声明本次处理 / 校验已通过。\n"
    )
    raise SystemExit(1) from _missing

from excel_formula_verify import (  # noqa: E402
    EXCEL_ERROR_VALUES, _compat_hits, _formula_regions, _region_anchor, _regression_padding_regions,
)

# 经典 7 类 + 动态数组时代新增的错误值；缓存值就是这些字面量，漏一个就是漏报。
ERROR_VALUES = EXCEL_ERROR_VALUES


def formula_text(value) -> str:
    """普通公式、ArrayFormula、DataTableFormula 统一提取公式串；非公式返回空串。

    openpyxl 3.1 把数组公式读成对象而不是 "=" 开头的字符串，只认字符串会让这些
    格绕过 _xlfn. 兼容性扫描。
    """
    if isinstance(value, str):
        return value if value.startswith("=") else ""
    if type(value).__name__ in ("ArrayFormula", "DataTableFormula"):
        text = getattr(value, "text", None)
        if isinstance(text, str) and text:
            return text if text.startswith("=") else "=" + text
        return "="  # 无文本的公式对象：至少按「存在公式」处理
    return ""


def ref_contains(ref, needle: str) -> bool:
    """片段匹配但不跨引用边界：`$A$2:$A$3` 不能命中 `$A$2:$A$30`。"""
    if not needle:
        return False
    text = str(ref)
    start = text.find(needle)
    while start != -1:
        before = text[start - 1:start]
        after = text[start + len(needle):start + len(needle) + 1]
        if not (before.isalnum() or before == "$") and not (after.isalnum() or after == "$"):
            return True
        start = text.find(needle, start + 1)
    return False


def load_contract(path: str | None, artifact_path: str) -> dict:
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict) or value.get("status") != "success" or not isinstance(value.get("contract"), dict):
        raise ValueError("checked contract status must be success")
    artifact = value["contract"].get("artifact")
    if not isinstance(artifact, dict):
        raise ValueError("contract.artifact must be an object")
    if artifact.get("kind") != "xlsx":
        raise ValueError("artifact verifier only accepts local xlsx artifacts")
    if artifact.get("xlsx_verification") not in {"local_working_file", "user_requested_local_output"}:
        raise ValueError("xlsx verification trigger is not allowed")
    declared_path = artifact.get("path")
    if not isinstance(declared_path, str) or not declared_path:
        raise ValueError("contract.artifact.path must be a non-empty string")
    if Path(declared_path).resolve() != Path(artifact_path).resolve():
        raise ValueError("artifact path does not match checked contract")
    return value["contract"]


def iter_range(ws, cell_range: str):
    if not isinstance(cell_range, str):
        raise ValueError("range must be a string")
    min_col, min_row, max_col, max_row = range_boundaries(cell_range)
    if any(v is None for v in (min_col, min_row, max_col, max_row)):
        raise ValueError("range must include explicit row and column bounds")
    if min_col > max_col or min_row > max_row:
        raise ValueError("range start must not come after its end")
    if min_row < 1 or min_col < 1 or max_row > 1048576 or max_col > 16384:
        raise ValueError("range is outside Excel bounds")
    for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        yield from row


def chart_type(chart) -> str:
    """归一到 CLI 的 chart_type 词表：纵向柱状是 column，横向条形才是 bar。

    openpyxl 用同一个 BarChart 承载两种方向（`.type` 为 "col" / "bar"），只取类名
    会让 column 契约永远失败、bar 契约无条件通过。
    """
    name = chart.__class__.__name__.replace("Chart", "").lower()
    if name.startswith("bar"):
        orientation = "bar" if getattr(chart, "type", "col") == "bar" else "column"
        return orientation + name[len("bar"):]
    return name


def series_ref(series, attr: str):
    value = getattr(series, attr, None)
    if value is None:
        return None
    num_ref = getattr(value, "numRef", None)
    str_ref = getattr(value, "strRef", None)
    ref = num_ref or str_ref
    return getattr(ref, "f", None) if ref else None


def chart_title_text(chart, wb_values):
    """图表标题的显示文本，取不到时返回 None。

    不能用 `str(chart.title.tx)`——那是 openpyxl 的对象 repr：标题走 strRef
    引用单元格时文本根本不在里面，合法契约会稳定误报；反过来 repr 里的字段名
    （rich / Parameters 之类）又会让短标题意外命中。这里按两种承载分别取真文本。
    """
    tx = getattr(getattr(chart, "title", None), "tx", None)
    if tx is None:
        return None

    rich_text = _rich_text_runs(getattr(tx, "rich", None))
    if rich_text:
        return rich_text

    str_ref = getattr(tx, "strRef", None)
    if str_ref is None:
        return None
    cached = _str_cache_value(getattr(str_ref, "strCache", None))
    if cached is not None:
        return cached
    return _read_ref_value(getattr(str_ref, "f", None), wb_values)


def _rich_text_runs(rich) -> str:
    """把富文本段落里的所有 run 文本拼起来。"""
    if rich is None:
        return ""
    runs = [str(getattr(run, "t", "") or "")
            for para in (getattr(rich, "p", []) or [])
            for run in (getattr(para, "r", []) or [])]
    return "".join(runs)


def _str_cache_value(cache):
    """strRef 自带的缓存文本，没有就返回 None。"""
    values = [getattr(point, "v", None) for point in (getattr(cache, "pt", []) or [])]
    hits = [str(v) for v in values if v]
    return hits[0] if hits else None


def _read_ref_value(ref: str, wb_values):
    """把 `'子表'!$D$1` 这类单格引用读成文本；读不到返回 None。"""
    if not ref or "!" not in str(ref):
        return None
    sheet, _, coord = str(ref).rpartition("!")
    sheet = sheet.strip().strip("'").replace("''", "'")
    coord = coord.replace("$", "").strip()
    if sheet not in wb_values.sheetnames:
        return None
    try:
        value = wb_values[sheet][coord].value
    except (ValueError, IndexError, AttributeError, TypeError):
        return None
    return None if value is None else str(value)


def _verify_one_chart(chart, ref: str, obj: dict, expected_type: str, wb_values, add) -> None:
    """逐图核对契约：类型、标题、系列数、x 轴与必需引用。"""
    actual_type = chart_type(chart)
    if expected_type and expected_type not in actual_type:
        add("chart_type", ref, "chart type mismatch", expected_type, actual_type)

    expected_title = obj.get("title")
    if isinstance(expected_title, str) and expected_title:
        title_text = chart_title_text(chart, wb_values)
        reason = ("chart title mismatch" if title_text
                  else "chart title is missing or unreadable")
        if expected_title not in (title_text or ""):
            add("chart_title", ref, reason, expected_title, title_text)

    series = list(getattr(chart, "ser", []) or [])
    if obj.get("series_count") is not None and len(series) != obj["series_count"]:
        add("chart_series_count", ref, "series count mismatch", obj["series_count"], len(series))

    refs = [series_ref(s, "val") or series_ref(s, "yVal") for s in series]
    cat_refs = [series_ref(s, "cat") or series_ref(s, "xVal") for s in series]
    raw_x_axis = obj.get("x_axis")
    expected_x_axis = raw_x_axis if isinstance(raw_x_axis, str) else ""
    if expected_x_axis and not any(ref_contains(r, expected_x_axis) for r in cat_refs):
        add("chart_x_axis", ref, "x-axis reference mismatch", expected_x_axis, cat_refs)

    for required in _as_list(obj.get("series")):
        if not any(ref_contains(r, str(required)) for r in refs):
            add("chart_series", ref, "required series reference missing", required, refs)
    for required in _as_list(obj.get("required_ref_contains")):
        if not any(ref_contains(r, str(required)) for r in refs):
            add("chart_ref", ref, "required data reference missing", required, refs)


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def missing_xlfn_prefix(formula: str) -> list:
    """公式里缺 `_xlfn.` 前缀的新函数名。

    复用 excel_formula_verify 的同一份函数清单与解析：两个门禁必须同源，否则
    现代函数无论带不带前缀都至少踩中一个。同级脚本随 skill 一起分发，这里按
    自身位置补 sys.path，不依赖调用方怎么加载本模块。
    """
    return _compat_hits(formula)


def _scan_sheet_formulas(ws, formula_ws, add) -> None:
    """逐格扫两件事：缓存值里的 Excel 错误，以及缺 `_xlfn.` 前缀的新函数。"""
    padding = _regression_padding_regions(formula_ws)
    for coord in sorted(set(ws._cells) | set(formula_ws._cells)):
        cell, source = ws.cell(*coord), formula_ws.cell(*coord)
        _scan_one_cell(ws.title, cell, source.value if source.data_type == "f" else None, add,
                       expected_na=_region_anchor(padding, *coord) is not None)


def _scan_one_cell(sheet: str, cell, raw_formula, add, *, expected_na=False) -> None:
    formula = formula_text(raw_formula)
    is_formula_cell = bool(formula)
    if ((cell.data_type == "e" or is_formula_cell)
            and isinstance(cell.value, str) and cell.value.upper() in ERROR_VALUES
            and not (expected_na and cell.value.upper() == "#N/A")):
        add("formula_error", f"{sheet}!{cell.coordinate}",
            "cached formula value is an Excel error", actual=cell.value)
    if not is_formula_cell:
        return
    # 判据与 excel_formula_verify 同源：xlsx 存储层里新函数必须带 `_xlfn.` 前缀，
    # 缺前缀才会在 Excel 里变 #NAME?。把「带了前缀」当成违规，会让现代函数
    # 无论怎么写都过不了两个门禁。
    for name in missing_xlfn_prefix(formula):
        add("formula_compatibility", f"{sheet}!{cell.coordinate}",
            f"function {name} needs the _xlfn. storage prefix or it becomes #NAME? in Excel",
            expected=f"_xlfn.{name}", actual=formula)


def _valid_tolerance(tolerance) -> bool:
    """容差必须是非 bool、有限、非负的数字。"""
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        return False
    # JSON 整数没有位数上限：10**400 转 float 会抛 OverflowError，让校验自己崩掉。
    try:
        value = float(tolerance)
    except (OverflowError, ValueError):
        return False
    return math.isfinite(value) and value >= 0


def get_contract_list(contract: dict, key: str, violations: list) -> list:
    value = contract.get(key, [])
    if not isinstance(value, list):
        violations.append({"kind": "invalid_contract", "location": key, "message": "must be a list", "expected": "list", "actual": type(value).__name__})
        return []
    return value


def values_equal(actual, expected, tolerance=1e-9):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        try:
            left, right = Decimal(str(actual)), Decimal(str(expected))
            return (left.is_finite() and right.is_finite()
                    and abs(left - right) <= Decimal(str(tolerance)))
        except InvalidOperation:
            return False
    return actual == expected


def verify(path: str, contract: dict, formula_ranges=None) -> dict:
    violations = []
    checks_performed = 0

    def add(kind: str, location: str, message: str, expected=None, actual=None):
        violations.append({"kind": kind, "location": location, "message": message, "expected": expected, "actual": actual})

    conditional_report = check_file(path)
    if conditional_report["status"] == "error":
        return conditional_report
    for violation in conditional_report["violations"]:
        add(violation["kind"], violation["location"], violation["message"],
            expected="solid conditional fill with bgColor", actual=violation["actual"])

    wb_formula = load_workbook(path, data_only=False)
    wb_values = load_workbook(path, data_only=True)
    regions_by_sheet = {ws.title: _formula_regions(ws) for ws in wb_formula.worksheets}

    # Scan cached values for deterministic Excel errors and formulas for xlfn.
    for ws in wb_values.worksheets:
        _scan_sheet_formulas(ws, wb_formula[ws.title], add)

    for sheet, cell_range in formula_ranges or []:
        checks_performed += 1
        if sheet not in wb_formula.sheetnames:
            add("missing_sheet", sheet, "required formula sheet missing")
            continue
        missing, count = [], 0
        ws = wb_formula[sheet]
        regions = regions_by_sheet[sheet]
        try:
            for cell in iter_range(ws, cell_range):
                if cell.data_type != "f" and _region_anchor(regions, cell.row, cell.column) is None:
                    count += 1
                    if len(missing) < 30:
                        missing.append(cell.coordinate)
        except ValueError as exc:
            add("invalid_range", f"{sheet}!{cell_range}", str(exc))
            continue
        if count:
            add("formula_coverage", f"{sheet}!{cell_range}",
                "declared range contains cells not driven by a formula or an array/data-table formula",
                "formula-driven value in every declared cell", {"missing_count": count, "cells": missing})

    for req in get_contract_list(contract, "requirements", violations):
        if not isinstance(req, dict):
            add("invalid_contract", "requirements", "entries must be objects", actual=type(req).__name__)
            continue
        evidence_list = req.get("evidence", [])
        if not isinstance(evidence_list, list):
            add("invalid_contract", "requirements.evidence", "evidence must be a list", expected="list", actual=type(evidence_list).__name__)
            continue
        for evidence in evidence_list:
            if not isinstance(evidence, dict):
                add("invalid_contract", "requirements.evidence", "evidence entry must be an object", actual=type(evidence).__name__)
                continue
            sheet = evidence.get("sheet")
            cell_range = evidence.get("range")
            if sheet:
                checks_performed += 1
            if sheet and sheet not in wb_formula.sheetnames:
                add("missing_sheet", sheet, f"requirement {req.get('id')} evidence sheet missing")
            elif sheet and cell_range:
                try:
                    values = [c.value for c in iter_range(wb_values[sheet], cell_range)]
                except ValueError as exc:
                    add("invalid_range", f"{sheet}!{cell_range}", str(exc))
                    continue
                if evidence.get("non_empty") and not any(v not in (None, "") for v in values):
                    add("empty_range", f"{sheet}!{cell_range}", f"requirement {req.get('id')} evidence is empty")

    for formula_contract in get_contract_list(contract, "formula_contracts", violations):
        if not isinstance(formula_contract, dict):
            add("invalid_contract", "formula_contracts", "entries must be objects", actual=type(formula_contract).__name__)
            continue
        sentinels = formula_contract.get("sentinels", [])
        if not isinstance(sentinels, list):
            add("invalid_contract", "formula_contracts.sentinels", "must be a list",
                expected="list", actual=type(sentinels).__name__)
            sentinels = []
        for sentinel in sentinels:
            if not isinstance(sentinel, dict):
                add("invalid_contract", "formula_contracts.sentinels", "sentinel must be an object")
                continue
            sheet, cell = sentinel.get("sheet"), sentinel.get("cell")
            if not sheet or not cell or "expected" not in sentinel:
                add("invalid_contract", "formula_contracts.sentinels", "sheet/cell/expected are required")
                continue
            checks_performed += 1
            if sheet not in wb_formula.sheetnames:
                add("missing_sheet", sheet, "formula sentinel sheet missing")
                continue
            # 坐标来自手写契约。写错了要报 invalid_contract，不能让 openpyxl 的异常
            # 掀掉整次校验——那样契约写错会伪装成工具故障（status=error）。
            try:
                formula_cell = wb_formula[sheet][cell]
                formula = formula_cell.value if formula_cell.data_type == "f" else None
                if formula is None:
                    anchor = _region_anchor(regions_by_sheet[sheet], formula_cell.row, formula_cell.column)
                    if anchor is not None:
                        formula = wb_formula[sheet][anchor].value
                actual = wb_values[sheet][cell].value
            except (ValueError, IndexError, AttributeError, TypeError) as exc:
                add("invalid_contract", f"{sheet}!{cell}", f"cell is not a valid coordinate: {exc}",
                    expected="A1 形态的单格坐标", actual=cell)
                continue
            tolerance = sentinel.get("tolerance", 1e-9)
            # 与 _checkpoints.py 同一套判据：非 bool、有限、非负。
            # bool 是 int 子类，写成 true 会被当成 1；JSON 里 1e309 解析成 inf，
            # 它会让任何有限差值都算相等，等于把数值断言整个关掉。
            if not _valid_tolerance(tolerance):
                add("invalid_contract", f"{sheet}!{cell}",
                    "tolerance must be a finite, non-negative number",
                    expected="number >= 0", actual=repr(tolerance))
                tolerance = 1e-9
            # 数组公式在 openpyxl 里是对象不是字符串，只认字符串会把合法的
            # ArrayFormula / DataTableFormula 判成「没有公式」。
            if not formula_text(formula):
                add("formula_missing", f"{sheet}!{cell}", "sentinel cell must contain a formula", expected="formula", actual=str(formula))
            if not values_equal(actual, sentinel["expected"], tolerance):
                add("formula_sentinel", f"{sheet}!{cell}", "formula sentinel result mismatch", sentinel["expected"], actual)

    for rep in get_contract_list(contract, "replacement_contracts", violations):
        if not isinstance(rep, dict):
            add("invalid_contract", "replacement_contracts", "entries must be objects", actual=type(rep).__name__)
            continue
        sheet = rep.get("sheet")
        cell_range = rep.get("range")
        if not sheet or not cell_range:
            add("invalid_contract", "replacement_contracts", "sheet and range are required")
            continue
        if sheet not in wb_values.sheetnames:
            add("missing_sheet", sheet, "replacement target sheet missing")
            continue
        try:
            cells = list(iter_range(wb_values[sheet], cell_range))
        except ValueError as exc:
            add("invalid_range", f"{sheet}!{cell_range}", str(exc))
            continue
        for old in rep.get("old_values", []):
            checks_performed += 1
            hits = [c.coordinate for c in cells if c.value == old]
            if hits:
                add("replacement_residual", f"{sheet}!{cell_range}", f"old value {old!r} still exists", expected=0, actual=hits[:20])

    for sem in get_contract_list(contract, "semantic_contracts", violations):
        if not isinstance(sem, dict):
            add("invalid_contract", "semantic_contracts", "entries must be objects", actual=type(sem).__name__)
            continue
        sheet = sem.get("sheet")
        source_col = sem.get("source_col")
        output_col = sem.get("output_col")
        start_row = sem.get("start_row", 2)
        end_row = sem.get("end_row")
        if not sheet or not source_col or not output_col:
            add("invalid_contract", "semantic_contracts", "sheet/source_col/output_col are required")
            continue
        if sheet not in wb_values.sheetnames:
            add("missing_sheet", sheet, "semantic source sheet missing")
            continue
        ws = wb_values[sheet]
        end = end_row or ws.max_row
        minimum = sem.get("min_length", 0)
        if type(minimum) is not int or minimum < 0:
            add("invalid_contract", "semantic_contracts.min_length", "must be a non-negative integer")
            continue
        checks_performed += 1
        for row in range(start_row, end + 1):
            source_value = ws[f"{source_col}{row}"].value
            output_value = ws[f"{output_col}{row}"].value
            source = "" if source_value is None else str(source_value)
            output = "" if output_value is None else str(output_value)
            if output and output not in source:
                add("semantic_not_source_substring", f"{sheet}!{output_col}{row}", "output is not a continuous substring of source", actual=output)
            if output and len(output) < minimum:
                add("semantic_too_short", f"{sheet}!{output_col}{row}",
                    "output is shorter than the explicitly required minimum", expected=minimum, actual=len(output))

    pivot_parts = 0
    try:
        with zipfile.ZipFile(path) as archive:
            pivot_parts = sum(name.startswith("xl/pivotTables/pivotTable") and name.endswith(".xml") for name in archive.namelist())
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid xlsx container") from exc

    for obj in get_contract_list(contract, "object_contracts", violations):
        if not isinstance(obj, dict):
            add("invalid_contract", "object_contracts", "entries must be objects", actual=type(obj).__name__)
            continue
        sheet = obj.get("sheet")
        if not sheet:
            add("invalid_contract", "object_contracts", "sheet is required")
            continue
        if sheet not in wb_formula.sheetnames:
            add("missing_sheet", sheet, "object target sheet missing")
            continue
        ws = wb_formula[sheet]
        if obj.get("type") == "chart":
            checks_performed += 1
            charts = ws._charts
            if len(charts) != obj.get("count"):
                add("chart_count", sheet, "chart count mismatch", obj.get("count"), len(charts))
            raw_type = obj.get("chart_type")
            expected_type = raw_type.lower() if isinstance(raw_type, str) else ""
            for i, chart in enumerate(charts):
                _verify_one_chart(chart, f"{sheet}#chart{i+1}", obj, expected_type,
                                  wb_values, add)
        elif obj.get("type") == "pivot":
            checks_performed += 1
            in_memory = len(getattr(ws, "_pivots", []) or [])
            expected = obj.get("count", 1)
            wrong_count = (in_memory != expected if obj.get("exact_count") else in_memory < expected)
            if wrong_count or pivot_parts < expected:
                add("pivot_count", sheet, "native pivot definition missing from exported workbook", expected, {"sheet_objects": in_memory, "package_parts": pivot_parts})
        else:
            add("invalid_contract", "object_contracts", "type must be 'chart' or 'pivot'", expected="chart|pivot", actual=obj.get("type"))

    for style in get_contract_list(contract, "style_contracts", violations):
        if not isinstance(style, dict):
            add("invalid_contract", "style_contracts", "entries must be objects", actual=type(style).__name__)
            continue
        sheet = style.get("sheet")
        cell_range = style.get("range")
        if not sheet or not cell_range:
            add("invalid_contract", "style_contracts", "sheet and range are required")
            continue
        if sheet not in wb_formula.sheetnames:
            add("missing_sheet", sheet, "style target sheet missing")
            continue
        try:
            cells = list(iter_range(wb_formula[sheet], cell_range))
        except ValueError as exc:
            add("invalid_range", f"{sheet}!{cell_range}", str(exc))
            continue
        if style.get("all_borders"):
            checks_performed += 1
            missing = []
            for c in cells:
                sides = (c.border.left, c.border.right, c.border.top, c.border.bottom)
                if any(not isinstance(getattr(side, "style", None), str) or not side.style for side in sides):
                    missing.append(c.coordinate)
            if missing:
                add("border_missing", f"{sheet}!{cell_range}", "cells missing one or more border sides", expected=0, actual=missing[:30])
        fmt = style.get("number_format")
        if fmt:
            checks_performed += 1
            bad = [c.coordinate for c in cells if c.number_format != fmt]
            if bad:
                add("number_format", f"{sheet}!{cell_range}", "number format mismatch", fmt, bad[:30])

    inventory = [{"sheet": ws.title,
                  "formula_cells": sum(c.data_type == "f" for c in ws._cells.values()),
                  "charts": len(ws._charts), "pivots": len(ws._pivots),
                  "conditional_formats": len(ws.conditional_formatting),
                  "freeze_panes": str(ws.freeze_panes) if ws.freeze_panes else None}
                 for ws in wb_formula]
    result = {"status": "success" if not violations else "violations_found",
              "violations": violations, "inventory": inventory,
              "declared_requirements_verified": bool(checks_performed and not violations),
              "calculation_verified": False,
              "summary": {"violations": len(violations), "sheets": len(wb_formula.sheetnames),
                          "requirement_checks": checks_performed}}
    wb_formula.close()
    wb_values.close()
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify deterministic properties of an exported xlsx artifact")
    ap.add_argument("xlsx")
    ap.add_argument("--contract")
    ap.add_argument("--require-formulas", nargs=2, action="append", metavar=("SHEET", "RANGE"),
                    help="要求每格由公式驱动（包括数组/数据表公式的结果格）；排除不适用行，可重复")
    ap.add_argument("--require-charts", nargs=2, action="append", metavar=("SHEET", "COUNT"),
                    help="要求指定子表中原生图表数量精确相等，可重复")
    ap.add_argument("--require-pivots", nargs=2, action="append", metavar=("SHEET", "COUNT"),
                    help="要求指定子表中原生透视表数量精确相等，可重复")
    ap.add_argument("--require-format", nargs=3, action="append", metavar=("SHEET", "RANGE", "FORMAT"),
                    help="核对指定区域数字格式原文，如0.0000，可重复")
    args = ap.parse_args()
    if not Path(args.xlsx).is_file():
        print(json.dumps({"status": "error", "error": "xlsx not found"}, ensure_ascii=False))
        return 2
    try:
        contract = load_contract(args.contract, args.xlsx)
        for kind, entries in (("chart", args.require_charts), ("pivot", args.require_pivots)):
            for sheet, raw_count in entries or []:
                count = int(raw_count)
                if count < 0:
                    raise ValueError("object count must be non-negative")
                contract.setdefault("object_contracts", []).append(
                    {"type": kind, "sheet": sheet, "count": count, "exact_count": True})
        for sheet, cell_range, fmt in args.require_format or []:
            if not fmt:
                raise ValueError("number format must not be empty")
            contract.setdefault("style_contracts", []).append(
                {"sheet": sheet, "range": cell_range, "number_format": fmt})
        result = verify(args.xlsx, contract, args.require_formulas)
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "error", "error_type": exc.__class__.__name__, "error": "artifact or contract is invalid"}, ensure_ascii=False))
        print("检查未执行完整：{}。修正文件、子表名、带行列边界的范围或非负整数数量后重试。".format(exc), file=_sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "error":
        return 2
    if result["status"] != "success":
        print("按报告定位缺少的公式、原生对象或格式并修复；普通汇总区、图片和文本公式不能冒充对应对象。不能放宽原需求来让检查通过。", file=_sys.stderr)
    else:
        print("仅完成静态扫描及已声明要求；未声明的用户要求、业务口径与公式重算结果不在此成功结论内。", file=_sys.stderr)
    return 0 if result["status"] == "success" else 3


if __name__ == "__main__":
    raise SystemExit(main())
