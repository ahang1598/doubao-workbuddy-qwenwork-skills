"""
Excel Formula Verification & Recalculation
Validates all formulas in an Excel workbook via LibreOffice headless mode.
Also flags derived values that were written as static numbers instead of formulas.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Set, Tuple

_SHARED_SCRIPTS = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "shared-assets", "scripts")
)
if _SHARED_SCRIPTS not in sys.path:
    sys.path.insert(0, _SHARED_SCRIPTS)

from excel_lo_runtime import get_soffice_env
from _checkpoints import (emit_checkpoint_hint, emit_checkpoint_skip_hint,
                          load_checkpoints, verify_checkpoints)

try:
    from openpyxl import load_workbook
    from openpyxl.utils.cell import range_boundaries
except ModuleNotFoundError as _missing:  # 本机没装 openpyxl：报错现场直接给出两条出路
    sys.stderr.write(
        f"\n[excel_formula_verify] 本机 Python 缺少 {_missing.name}，脚本无法在本地解析 Excel。\n"
        "  装一次即可长期复用：python3 -m pip install --user openpyxl\n"
        "  不装依赖也能做：把文件导入飞书在线表格，用飞书引擎读（服务端解析，无需本地库）——\n"
        "     lark-cli sheets +workbook-import --file ./<文件名>.xlsx\n"
    )
    raise SystemExit(1) from _missing

# 表头命中这些词 = 该行/列是「由其他单元格推导出来的量」，本就该写公式。
# 中文按子串匹配（字符级无误伤）；英文必须整词匹配（\b）——rate/sum/rank 等短串
# 会误命中 Corporate/Summary/Frank 这类普通列名，误报会硬阻断正确交付，比漏报更贵。
# index/share 因歧义过大（Index Number / Share Class 常为原始数据）不入词表。
DERIVED_HEADER_CN = re.compile(
    r"率|比例|占比|占%|合计|总计|小计|总和|增长|增速|同比|环比|排名|排序|名次"
    r"|平均|均值|累计|累积|差额|净额|毛利|利润|周转|复合|贡献|权重|方差|标准差|相关"
    r"|回报|收益|折旧|摊销|敞口|估值|倍数|系数|得分|评分|指数|客单价|人效"
)
DERIVED_HEADER_EN = re.compile(
    r"\b(rate|ratio|growth|rank|avg|average|total|sum|margin|cagr|yoy|mom|qoq"
    r"|pct|percent|contribution|weight|variance|stdev|std_?dev|correl"
    r"|return|score|npv|irr|ebitda|eps|arpu|arppu|ltv|roi|roe|roa|wacc)\b",
    re.IGNORECASE,
)


def _is_derived_header(text: str) -> bool:
    return bool(DERIVED_HEADER_CN.search(text) or DERIVED_HEADER_EN.search(text))


# 纯记录型表头，即使命中上面的词也不算派生（避免误报原始数据列）
RAW_HEADER = re.compile(r"^(日期|时间|date|time|id|编号|名称|name|备注|remark)", re.IGNORECASE)


def is_libreoffice_available() -> bool:
    return shutil.which("soffice") is not None


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _formula_text(v) -> str:
    """普通公式、ArrayFormula、DataTableFormula 统一提取公式串；非公式返回空串。

    openpyxl 3.1 把数组公式 / 数据表公式读成对象（不是 "=" 开头的字符串），
    只认字符串会让这些格整体漏出公式计数、错误扫描与不变量扫描。
    """
    if isinstance(v, str):
        return v if v.startswith("=") else ""
    if type(v).__name__ in ("ArrayFormula", "DataTableFormula"):
        text = getattr(v, "text", None)
        if isinstance(text, str) and text:
            return text if text.startswith("=") else "=" + text
        return "="  # 无文本的公式对象：至少按「存在公式」处理
    return ""


def _is_formula(v) -> bool:
    return bool(_formula_text(v))


def _normalize_sheet_names(raw: Optional[str]) -> Tuple[Set[str], List[str]]:
    names = []
    if raw:
        names = [s.strip() for s in raw.split(",") if s.strip()]
    seen = set()
    uniq = []
    for name in names:
        if name not in seen:
            seen.add(name)
            uniq.append(name)
    return set(uniq), uniq


def _sheet_has_formula(ws, cap_cells: int = 500000) -> Tuple[bool, bool]:
    """全表短路扫描公式是否存在。返回 (found, complete)。

    找到第一个公式立即返回；扫满 cap_cells 仍未找到则 complete=False——
    抽样式的「未见公式」不允许升级为 high（会对大表误判整表无公式并阻断）。
    """
    seen = 0
    for row in ws.iter_rows():
        for cell in row:
            if _is_formula(cell.value):
                return True, True
            seen += 1
            if seen >= cap_cells:
                return False, False
    return False, True


def detect_hardcode_suspects(filename: str, max_report: int = 12, static_source_sheets: Optional[Set[str]] = None) -> dict:
    """扫描「表头表明是派生量、但整行/整列没有一个公式」的区域。

    只报告有足够证据的区域（≥3 个静态数值且 0 个公式），避免噪声。
    分两级：sheet 内完全无公式 = high；sheet 有公式但个别派生区域没有 = low。
    被显式声明为历史/外部静态来源的 sheet 不参与 high_confidence 计数，降为 low。
    """
    static_source_sheets = set(static_source_sheets or ())
    try:
        wb = load_workbook(filename, data_only=False)
    except Exception as e:
        return {"status": "skipped", "reason": str(e)}

    suspects = []
    sheets_scanned = 0
    unknown_static_source_sheets = []
    try:
        workbook_sheets = set(wb.sheetnames)
        unknown_static_source_sheets = sorted(static_source_sheets - workbook_sheets)
        declared_static_source_sheets = workbook_sheets & static_source_sheets
        for name in wb.sheetnames:
            ws = wb[name]
            if ws.max_row < 2 or ws.max_column < 1:
                continue
            sheets_scanned += 1
            rows = list(ws.iter_rows(max_row=min(ws.max_row, 2000)))
            # 公式存在性单独全表短路扫描——前 2000 行的截断样本只用于表头/列画像，
            # 不允许决定「整表无公式」这种会升 high 并阻断退出码的判定
            has_formula, scan_complete = _sheet_has_formula(ws)
            is_declared_static_source = name in declared_static_source_sheets
            level = "high" if (not has_formula and scan_complete and not is_declared_static_source) else "low"

            # 表头行：前 5 行里字符串最多的那行
            header_idx, best = 0, -1
            for i, r in enumerate(rows[:5]):
                cnt = sum(1 for c in r if isinstance(c.value, str) and c.value.strip())
                if cnt > best:
                    header_idx, best = i, cnt
            header = rows[header_idx]

            # 列方向：表头命中派生词，列内全是静态数值
            for c in header:
                text = str(c.value).strip() if c.value is not None else ""
                if not text or RAW_HEADER.match(text) or not _is_derived_header(text):
                    continue
                col = c.column
                vals = [r[col - 1].value for r in rows[header_idx + 1:] if len(r) >= col]
                nums = sum(1 for v in vals if _is_number(v))
                fmls = sum(1 for v in vals if _is_formula(v))
                if nums >= 3 and fmls == 0:
                    suspects.append({
                        "level": level, "sheet": name, "axis": "column",
                        "header": text[:40], "static_cells": nums,
                        "declared_static_source": is_declared_static_source,
                    })

            # 行方向（横向年份布局）：首列行头命中派生词，行内全是静态数值
            for r in rows[header_idx + 1:]:
                if not r:
                    continue
                text = str(r[0].value).strip() if r[0].value is not None else ""
                if not text or not _is_derived_header(text):
                    continue
                vals = [c.value for c in r[1:]]
                nums = sum(1 for v in vals if _is_number(v))
                fmls = sum(1 for v in vals if _is_formula(v))
                if nums >= 3 and fmls == 0:
                    suspects.append({
                        "level": level, "sheet": name, "axis": "row",
                        "header": text[:40], "static_cells": nums,
                        "declared_static_source": is_declared_static_source,
                    })
    finally:
        wb.close()

    high = [s for s in suspects if s["level"] == "high"]
    return {
        "status": "suspected" if suspects else "clean",
        "total_suspects": len(suspects),
        "high_confidence": len(high),
        "sheets_scanned": sheets_scanned,
        "details": suspects[:max_report],
        "static_source_sheets": sorted(static_source_sheets),
        "unknown_static_source_sheets": unknown_static_source_sheets,
    }


HARDCODE_HINT = """\
[hardcode] 检出 {n} 处「表头表明是推导值、但整行/整列没有一个公式」的区域{extra}：
{lines}
这些格子应写成引用其他单元格的 Excel 公式，而不是先算好数值再写入。
结果对 != 合规：写死的表没有联动能力，用户改一个输入，全表不会更新。
处置：把上列区域改写为公式（假设 / 输入项集中放一处，由公式引用），改完重跑本脚本。
唯一可写静态值的情况：历史真实数据、供人修改的输入假设、标注了来源的外部取数。
若确属这三类，无需改写。"""


INVALID_INPUT_HINT = """\
[input] 产物读不出来（status={status}）：{error}
本脚本只吃 .xlsx / .xlsm / .xltx / .xltm；错误值扫描、前缀与形状、硬编码嫌疑一项都没跑，
这不是「没发现问题」，是没有判据。
退出码 3 是确定性错误，先把输入换成能读的工作簿再重跑：`.csv` 产物不适用本门禁，
`.xls` 先另存为 `.xlsx`，本地库打不开的文件用 `+workbook-import` 导入飞书表格再处理。"""


RECALC_UNVERIFIED_HINT = """\
[recalc] 公式未完成重算（status={status}）：{warning}
只读诊断（错误值扫描、前缀与形状、硬编码嫌疑）已经跑过，缺的只是执行验证。
退出码 4 不是让你反复重跑，也不是让你换 Python 复算冒充验证：
交付说明写明「公式未重算」并提示在 Excel 中刷新（Ctrl+Alt+F9），不得写「公式已验证无错误」。"""


def _emit_hardcode_hint(hc: dict) -> bool:
    """在 stderr 打印处置指引。返回是否存在高置信嫌疑。"""
    details = hc.get("details") or []
    if not details:
        return False
    lines = "\n".join(
        f"  - {d['sheet']} {'列' if d['axis'] == 'column' else '行'}「{d['header']}」"
        f"（{d['static_cells']} 个静态数值，0 公式）"
        + (" [declared static source → WARN only]" if d.get("declared_static_source") else "")
        for d in details
    )
    extra = ""
    if hc["total_suspects"] > len(details):
        extra = f"（仅列出前 {len(details)} 处，共 {hc['total_suspects']} 处）"
    print(HARDCODE_HINT.format(n=hc["total_suspects"], extra=extra, lines=lines), file=sys.stderr)
    return hc.get("high_confidence", 0) > 0


# ────────────────────── 静态风险扫描（不依赖 LibreOffice）──────────────────────
#
# 重算不可用时这些事实仍然拿得到，因此放在只读路径里，两条路径都输出。
# 两类判据都要求「不重算也能确定会算错」，宁可漏报：误报会硬阻断正确的产物。

# Excel 2010 起新增的函数在 xlsx 里以 `_xlfn.` 前缀存储。写文件的库不会替你补这个
# 前缀，直接写 `=STDEV.S(...)` 存进去的公式，Excel 与多数重算引擎打开后都是 #NAME?，
# 而缓存值扫描看不到它——文件里根本没有缓存值。
XLFN_FUNCTIONS = {
    # 统计（.S/.P/.DIST/.INV 这一代）
    "STDEV.S", "STDEV.P", "VAR.S", "VAR.P", "COVARIANCE.S", "COVARIANCE.P",
    "NORM.DIST", "NORM.INV", "NORM.S.DIST", "NORM.S.INV", "LOGNORM.DIST", "LOGNORM.INV",
    "T.DIST", "T.DIST.2T", "T.DIST.RT", "T.INV", "T.INV.2T", "T.TEST",
    "CHISQ.DIST", "CHISQ.DIST.RT", "CHISQ.INV", "CHISQ.INV.RT", "CHISQ.TEST",
    "F.DIST", "F.DIST.RT", "F.INV", "F.INV.RT", "F.TEST", "Z.TEST",
    "BINOM.DIST", "BINOM.INV", "NEGBINOM.DIST", "POISSON.DIST", "EXPON.DIST",
    "GAMMA.DIST", "GAMMA.INV", "GAMMALN.PRECISE", "BETA.DIST", "BETA.INV",
    "WEIBULL.DIST", "HYPGEOM.DIST", "CONFIDENCE.NORM", "CONFIDENCE.T",
    "PERCENTILE.INC", "PERCENTILE.EXC", "QUARTILE.INC", "QUARTILE.EXC",
    "PERCENTRANK.INC", "PERCENTRANK.EXC", "RANK.EQ", "RANK.AVG",
    "MODE.SNGL", "MODE.MULT", "ERF.PRECISE", "ERFC.PRECISE",
    "CEILING.PRECISE", "FLOOR.PRECISE", "ISO.CEILING",
    # 2013 / 2016 / 365
    "IFNA", "XOR", "ISFORMULA", "FORMULATEXT", "DAYS", "PDURATION", "RRI",
    "ARABIC", "BASE", "DECIMAL", "COMBINA", "PERMUTATIONA", "SHEET", "SHEETS",
    "TEXTJOIN", "CONCAT", "IFS", "SWITCH", "MAXIFS", "MINIFS",
    "XLOOKUP", "XMATCH", "LET", "LAMBDA", "SEQUENCE", "RANDARRAY",
    "TEXTSPLIT", "TEXTBEFORE", "TEXTAFTER", "VSTACK", "HSTACK", "TOROW", "TOCOL",
    "WRAPROWS", "WRAPCOLS", "TAKE", "DROP", "CHOOSECOLS", "CHOOSEROWS", "EXPAND",
    "ARRAYTOTEXT", "VALUETOTEXT",
}
# 这几个还要再套一层工作表级前缀：`_xlfn._xlws.FILTER`
XLWS_FUNCTIONS = {"FILTER", "SORT", "SORTBY", "UNIQUE"}

_STRING_LITERAL_RE = re.compile(r'"[^"]*"')
# Excel 公式大小写不敏感，openpyxl 会原样保留用户写的小写。两个正则都按
# 大小写不敏感匹配，函数名与列标在解析处统一大写，后续比较只认大写形态。
_CALL_NAME_RE = re.compile(r"(?<![A-Za-z0-9_.])([A-Z][A-Z0-9]*(?:\.[A-Z0-9]+)*)\s*\(",
                           re.IGNORECASE)
# 纯范围引用：可带表名与 $，形如 `明细!$B$2:$B$50`、`A1:C10`
_PLAIN_RANGE_RE = re.compile(
    r"^(?:'[^']+'!|[A-Za-z0-9_一-鿿]+!)?\$?([A-Z]{1,3})\$?([0-9]{1,7})"
    r":\$?([A-Z]{1,3})\$?([0-9]{1,7})$",
    re.IGNORECASE
)
# 条件区必须与求和区同形的函数：值是「跳过前几个参数」的数量
SHAPE_PAIRED_FUNCTIONS = {"SUMIFS": 1, "AVERAGEIFS": 1, "MAXIFS": 1, "MINIFS": 1, "COUNTIFS": 0}


def _strip_string_literals(formula: str) -> str:
    return _STRING_LITERAL_RE.sub('""', formula)


def _col_index(letters: str) -> int:
    idx = 0
    for ch in letters.upper():
        idx = idx * 26 + (ord(ch) - 64)
    return idx


def _range_dims(token: str) -> Optional[Tuple[int, int]]:
    """纯范围引用 → (行数, 列数)；不是纯范围（含函数、常量、单格）时返回 None。"""
    m = _PLAIN_RANGE_RE.match(token.strip())
    if not m:
        return None
    start_col, start_row = m.group(1).upper(), int(m.group(2))
    end_col, end_row = m.group(3).upper(), int(m.group(4))
    rows = abs(end_row - start_row) + 1
    cols = abs(_col_index(end_col) - _col_index(start_col)) + 1
    return rows, cols


def _split_args(arg_text: str) -> List[str]:
    """按顶层逗号拆参数，括号与引号内的逗号不算分隔符。"""
    args, depth, quoted, buf = [], 0, False, []
    for ch in arg_text:
        if ch == '"':
            quoted = not quoted
        if not quoted:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 0:
                args.append("".join(buf))
                buf = []
                continue
        buf.append(ch)
    args.append("".join(buf))
    return args


def _iter_calls(formula: str):
    """遍历公式里的函数调用，产出 (函数名, 参数原文)。括号不配对时跳过该调用。"""
    for m in _CALL_NAME_RE.finditer(formula):
        start = m.end()
        depth, quoted, end = 1, False, None
        for i in range(start, len(formula)):
            ch = formula[i]
            if ch == '"':
                quoted = not quoted
                continue
            if quoted:
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            continue
        yield m.group(1).upper(), formula[start:end]


def _compat_hits(formula: str) -> List[str]:
    """公式里缺 `_xlfn.` 前缀的新函数名。"""
    text = _strip_string_literals(formula)
    hits = []
    for name, _args in _iter_calls(text):
        if name in XLFN_FUNCTIONS or name in XLWS_FUNCTIONS:
            hits.append(name)
    return sorted(set(hits))


def _shape_hits(formula: str) -> List[str]:
    """条件区与求和区不同形的调用；只在参数全是纯范围引用时判定。"""
    text = _strip_string_literals(formula)
    problems = []
    for name, arg_text in _iter_calls(text):
        upper = name.upper()
        args = _split_args(arg_text)
        if upper in SHAPE_PAIRED_FUNCTIONS:
            skip = SHAPE_PAIRED_FUNCTIONS[upper]
            ranges = [args[0]] if skip else []
            ranges += args[skip::2]
            dims = [_range_dims(a) for a in ranges]
            if len(dims) < 2 or any(d is None for d in dims):
                continue
            if len({d for d in dims}) > 1:
                shown = "、".join(f"{d[0]}×{d[1]}" for d in dims)
                problems.append(f"{upper} 的区域大小不一致（{shown}）")
        elif upper == "SUMPRODUCT":
            dims = [_range_dims(a) for a in args]
            if len(dims) < 2 or any(d is None for d in dims):
                continue
            if len({d for d in dims}) > 1:
                shown = "、".join(f"{d[0]}×{d[1]}" for d in dims)
                problems.append(f"SUMPRODUCT 的数组形状不一致（{shown}）")
    return problems


def scan_static_risks(filename: str, max_report: int = 10) -> dict:
    """不依赖重算的公式事实：函数兼容前缀、数组形状、公式覆盖率。"""
    try:
        wb = load_workbook(filename, data_only=False)
    except Exception as exc:
        return {"status": "skipped", "reason": str(exc)}

    compat, shape = [], []
    formula_cells = static_numeric_cells = 0
    try:
        for name in wb.sheetnames:
            ws = wb[name]
            for row in ws.iter_rows():
                for cell in row:
                    text = _formula_text(cell.value)
                    if not text:
                        if _is_number(cell.value):
                            static_numeric_cells += 1
                        continue
                    formula_cells += 1
                    for func in _compat_hits(text):
                        compat.append({
                            "sheet": name, "cell": cell.coordinate,
                            "function": func, "formula": text[:120],
                        })
                    for problem in _shape_hits(text):
                        shape.append({
                            "sheet": name, "cell": cell.coordinate,
                            "problem": problem, "formula": text[:120],
                        })
    finally:
        wb.close()

    computed = formula_cells + static_numeric_cells
    return {
        "status": "issues_found" if (compat or shape) else "clean",
        "compat": {"count": len(compat), "details": compat[:max_report]},
        "shape": {"count": len(shape), "details": shape[:max_report]},
        "coverage": {
            "formula_cells": formula_cells,
            "static_numeric_cells": static_numeric_cells,
            "formula_share": round(formula_cells / computed, 4) if computed else 0.0,
        },
    }


STATIC_RISK_HINT = """\
[static] 检出不必重算就能确定会算错的公式{extra}：
{lines}
{advice}"""

COMPAT_ADVICE = (
    "缺前缀这类：Excel 2010 起的新函数在 xlsx 文件里必须写成 `_xlfn.<函数名>`"
    "（`FILTER` / `SORT` / `SORTBY` / `UNIQUE` 再多一层，写成 `_xlfn._xlws.<函数名>`）。"
    "直接写函数名存进文件，Excel 与重算引擎打开都是 #NAME?，而文件里没有缓存值、扫不出来。"
    "两条出路：写入时补上前缀，或改用同语义的经典函数（如 STDEV.S → STDEV、"
    "PERCENTILE.INC → PERCENTILE、CONCAT → CONCATENATE）。"
)
SHAPE_ADVICE = (
    "形状这类：条件区与求和区行列数必须一致，SUMPRODUCT 的各数组也必须同形，"
    "否则求值返回 #VALUE!。按目标区域重新框定引用范围，别只改其中一个参数。"
)


def _emit_static_risk_hint(sr: dict) -> bool:
    """在 stderr 打印处置指引。返回是否检出确定性问题。"""
    compat = sr.get("compat") or {}
    shape = sr.get("shape") or {}
    total = compat.get("count", 0) + shape.get("count", 0)
    if not total:
        return False
    lines = []
    for d in compat.get("details", []):
        lines.append(f"  - {d['sheet']}!{d['cell']} 函数 {d['function']} 缺 _xlfn 前缀：{d['formula']}")
    for d in shape.get("details", []):
        lines.append(f"  - {d['sheet']}!{d['cell']} {d['problem']}：{d['formula']}")
    shown = len(lines)
    extra = f"（仅列出前 {shown} 处，共 {total} 处）" if total > shown else ""
    advice = "\n".join(
        part for part, hit in ((COMPAT_ADVICE, compat.get("count")), (SHAPE_ADVICE, shape.get("count"))) if hit
    )
    print(STATIC_RISK_HINT.format(extra=extra, lines="\n".join(lines), advice=advice), file=sys.stderr)
    return True


def run_checkpoints(filename: str, items: List[dict]) -> dict:
    """按检查点回读产物：值取缓存值，公式取公式串。"""
    try:
        wb_f = load_workbook(filename, data_only=False)
        wb_v = load_workbook(filename, data_only=True)
    except Exception as exc:
        # 读不到产物 = 检查点这条门禁根本没跑成。与 baseline 的同类 I/O 失败
        # 同档处理：标 blocking 走确定性错误，不能按「降级」放行。
        return {"status": "skipped", "blocking": True,
                "reason": f"cannot read workbook: {exc}"}
    try:
        def lookup(sheet: str, coord: str):
            if sheet not in wb_f.sheetnames:
                return None, ""
            raw = wb_f[sheet][coord].value
            formula = _formula_text(raw)
            if formula:
                value = wb_v[sheet][coord].value if sheet in wb_v.sheetnames else None
            else:
                value = raw
            return value, formula

        return verify_checkpoints(items, lookup, list(wb_f.sheetnames))
    finally:
        wb_f.close()
        wb_v.close()


# ────────────────────── 基线对照（--baseline / --scope）──────────────────────
#
# 产物的终态永远是自洽的：没有改前基准，回读多少遍也判不出哪些格本不该长这样，
# 更判不出原表被整张换掉。传入源文件后这条才有判据——逐格比源与产物，
# 把「原值被改写」「原公式退化成静态值」「源 sheet 不见了」摆到台面上。
# 只比值、公式、sheet 结构；样式与行高列宽的差异噪声太大，不在这里判。

BASELINE_MAX_CELLS = 200000
SCOPE_ALL = "ALL"


def _norm_cell_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return f"{float(value):.10g}"
    return str(value).strip()


def _norm_formula(text: str) -> str:
    body = text[1:] if text.startswith("=") else text
    body = re.sub(r"'([^']+)'(?=!)", r"\1", body)
    return re.sub(r"\s+", "", body).upper()


def _read_workbook_cells(path: str) -> Tuple[dict, List[str]]:
    """({sheet: {坐标: (公式串, 归一化值)}}, 读到上限被截断的 sheet 名)。

    公式格的值取缓存值，没有就是空串。超过 BASELINE_MAX_CELLS 的 sheet 会停读，
    这时必须把 sheet 名带出去：源与产物在同一位置截断，尾部的改写两边都读不到，
    差异会归零，不带截断状态就会被判成 clean。
    """
    wb_f = load_workbook(path, data_only=False)
    wb_v = load_workbook(path, data_only=True)
    sheets = {}
    truncated: List[str] = []
    try:
        for name in wb_f.sheetnames:
            ws_f = wb_f[name]
            ws_v = wb_v[name] if name in wb_v.sheetnames else None
            cells = {}
            seen = 0
            for row in ws_f.iter_rows():
                for cell in row:
                    seen += 1
                    if seen > BASELINE_MAX_CELLS:
                        break
                    formula = _formula_text(cell.value)
                    if formula:
                        cached = ws_v[cell.coordinate].value if ws_v is not None else None
                        cells[cell.coordinate] = (_norm_formula(formula), _norm_cell_value(cached))
                    elif cell.value is not None and str(cell.value).strip() != "":
                        cells[cell.coordinate] = ("", _norm_cell_value(cell.value))
                if seen > BASELINE_MAX_CELLS:
                    break
            if seen > BASELINE_MAX_CELLS:
                truncated.append(name)
            sheets[name] = cells
    finally:
        wb_f.close()
        wb_v.close()
    return sheets, truncated


def split_scope_items(items):
    """按引号状态拆逗号：Excel 的 sheet 名允许逗号，`'Sales,2026'!A1:A2` 是合法写法。

    直接 split(",") 会把它拆成两段，其中 `'Sales` 去掉引号后没有 `!`，会被当成
    「整表放行」——目标表反而不在范围内，另一张真名 Sales 的表却被整张授权。
    """
    parts = []
    for raw in items or []:
        parts += _split_one_scope_item(str(raw))
    return [p.strip() for p in parts if p.strip()]


def split_sheet_and_range(part: str):
    """在引号外的第一个 `!` 处切开 sheet 名与范围；没有分隔符时返回 (part, None)。

    Excel 的 sheet 名允许 `!`，`'Sales!2026'!A1:A2` 是合法引用。直接 partition("!")
    会在名字内部切开，整条范围就此作废。
    """
    quoted = False
    for i, ch in enumerate(part):
        if ch == "'":
            quoted = not quoted
        elif ch == "!" and not quoted:
            return part[:i], part[i + 1:]
    return part, None


def _split_one_scope_item(text: str):
    parts, buf, quoted = [], [], False
    for ch in text:
        if ch == "'":
            quoted = not quoted
        elif ch == "," and not quoted:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return parts


def unquote_sheet_name(name: str) -> str:
    """去掉包裹的单引号并反转义内部的 ''。"""
    name = name.strip()
    if len(name) >= 2 and name.startswith("'") and name.endswith("'"):
        name = name[1:-1]
    return name.replace("''", "'")


class ScopeError(ValueError):
    """--scope 写法不合法。范围认不出时必须报错，不能退化成整表。"""


def parse_scope(items: List[str]) -> dict:
    """'明细!G:I' / '汇总' / '明细!A2:C10' → {sheet: SCOPE_ALL | [(r1,c1,r2,c2)]}。

    --scope 划的是「本轮允许改动」的边界，认不出的范围必须 fail closed：
    若退化成整表，范围外的改写就会被判成允许，baseline 门禁形同虚设。
    """
    scope: dict = {}
    for part in split_scope_items(items):
        raw_name, rng = split_sheet_and_range(part)
        if rng is None:
            scope[unquote_sheet_name(raw_name)] = SCOPE_ALL
            continue
        name = unquote_sheet_name(raw_name)
        box = _parse_scope_range(rng.strip())
        if box is None:
            raise ScopeError(
                f"--scope 里的范围认不出：{part!r}。"
                "写成 '子表名!A2:C10' / '子表名!G:I' / '子表名!2:5'，整表只写子表名。")
        if scope.get(name) == SCOPE_ALL:
            continue
        scope.setdefault(name, [])
        scope[name].append(box)
    return scope


MAX_EXCEL_ROW = 1048576
MAX_EXCEL_COL = 16384          # XFD


def _within_excel_bounds(box) -> bool:
    """行列必须落在 Excel 的真实边界内。

    只校验形状会让 `A0:XFD9999999` 这类非法输入被接受：行 0 起、行号上不封顶，
    结果所有合法坐标都算 in-scope，等于把一个写错的范围放大成整表授权。
    越界一律判非法，不 clamp——clamp 同样是在替调用方扩大授权。
    """
    start_row, start_col, end_row, end_col = box
    # 起点必须不晚于终点：`Z:A` / `9:2` 这类反序范围本地会匹配 0 格、在线会被
    # 悄悄当成 A:Z，两种都不是调用方写下的意思。与 iter_range 拒绝 B2:A1 同档，
    # 一律判非法，让调用方自己改对。
    if start_row > end_row or start_col > end_col:
        return False
    return (1 <= start_row <= MAX_EXCEL_ROW and 1 <= end_row <= MAX_EXCEL_ROW
            and 1 <= start_col <= MAX_EXCEL_COL and 1 <= end_col <= MAX_EXCEL_COL)


def _parse_scope_range(rng: str):
    """'G:I' / '3:20' / 'A2:C10' / 'B7' → (r1,c1,r2,c2)；认不出或越界返回 None。"""
    box = _parse_scope_shape(rng.replace("$", "").upper())
    if box is None or not _within_excel_bounds(box):
        return None
    return box


def _parse_scope_shape(rng: str):
    m = re.fullmatch(r"([A-Z]{1,3}):([A-Z]{1,3})", rng)
    if m:
        return 1, _col_index(m.group(1)), MAX_EXCEL_ROW, _col_index(m.group(2))
    m = re.fullmatch(r"([0-9]{1,7}):([0-9]{1,7})", rng)
    if m:
        return int(m.group(1)), 1, int(m.group(2)), MAX_EXCEL_COL
    m = re.fullmatch(r"([A-Z]{1,3})([0-9]{1,7})(?::([A-Z]{1,3})([0-9]{1,7}))?", rng)
    if m:
        start_col, start_row = _col_index(m.group(1)), int(m.group(2))
        end_col = _col_index(m.group(3)) if m.group(3) else start_col
        end_row = int(m.group(4)) if m.group(4) else start_row
        # 单元格范围沿用原有的 min/max 归一：`C10:A2` 与 `A2:C10` 等价，
        # 这是本条评审之前就有的行为，不在「反序 fail-closed」的范围内。
        return (
            min(start_row, end_row), min(start_col, end_col),
            max(start_row, end_row), max(start_col, end_col),
        )
    return None


def _in_scope(scope: dict, sheet: str, coord: str) -> bool:
    entry = scope.get(sheet)
    if entry is None:
        return False
    if entry == SCOPE_ALL:
        return True
    m = re.fullmatch(r"([A-Z]{1,3})([0-9]{1,7})", coord)
    if not m:
        return False
    col, row = _col_index(m.group(1)), int(m.group(2))
    return any(r1 <= row <= r2 and c1 <= col <= c2 for r1, c1, r2, c2 in entry)


class _BaselineReadError(Exception):
    """源工作簿读不到。"""


def _merge_baselines(baseline_paths: List[str]):
    """把多份 --baseline 并成一份联合快照。

    返回 (cells, truncated, conflicts, sources)。同名 sheet 的非重叠坐标取并集；
    同一坐标在两份源里值不同时记 conflict 并保留先出现的那份——按文件顺序静默
    覆盖会让「哪份才是改前基准」变得不可知。
    """
    merged: dict = {}
    truncated: List[str] = []
    conflicts: List[dict] = []
    sources: List[str] = []
    origin: dict = {}
    for src_path in baseline_paths:
        try:
            base, base_truncated = _read_workbook_cells(src_path)
        except Exception as exc:
            raise _BaselineReadError(f"cannot read baseline {src_path}: {exc}") from exc
        truncated += base_truncated
        sources.append(src_path)
        for sheet, cells in base.items():
            target = merged.setdefault(sheet, {})
            for coord, payload in cells.items():
                if coord not in target:
                    target[coord] = payload
                    origin[(sheet, coord)] = src_path
                elif target[coord] != payload:
                    conflicts.append({
                        "sheet": sheet, "cell": coord,
                        "kept": origin[(sheet, coord)], "conflicting": src_path,
                    })
    return merged, truncated, conflicts, sources


def _collect_additions(sheet: str, out_cells: dict, base_cells: dict,
                       scope: dict, scoped: bool) -> List[dict]:
    """产物里有、源里没有的非空格。scope 内算允许新增，scope 外要定性。"""
    added = []
    for coord, (formula, value) in out_cells.items():
        if coord in base_cells or not (formula or value):
            continue
        added.append({
            "sheet": sheet, "cell": coord, "kind": "added",
            "baseline": "", "produced": (formula or value)[:40],
            "in_scope": scoped and _in_scope(scope, sheet, coord),
        })
    return added


def _collect_added_sheets(produced: dict, base: dict, scope: dict,
                          scoped: bool) -> List[dict]:
    """产物里有、源里没有的整张 sheet。

    一律记录：没传 --scope 时它是改动事实（不定性），传了才判定。判定按格来，
    不按整张表——scope 精确写成 `New!A1:A1` 时那一格已获准，不该因为该 sheet
    不是整表放行就把整张表判成越界。
    """
    added = []
    for sheet, cells in produced.items():
        if sheet in base or not cells:
            continue
        outside = [coord for coord, (formula, value) in cells.items()
                   if (formula or value) and not (scoped and _in_scope(scope, sheet, coord))]
        added.append({
            "sheet": sheet, "cells": len(cells),
            "out_of_scope_cells": len(outside),
            "in_scope": scoped and not outside,
        })
    return added


def diff_baseline(output_path: str, baseline_paths: List[str], scope_items: List[str],
                  max_report: int = 12) -> dict:
    """比源工作簿与产物：丢失的 sheet、被改写的原值、退化成静态值的原公式。"""
    scope = parse_scope(scope_items)
    scoped = bool(scope)
    try:
        produced, produced_truncated = _read_workbook_cells(output_path)
    except Exception as exc:
        # 读不到就是这条门禁根本没跑成，不能按「没发现差异」放行。
        return {"status": "skipped", "blocking": True,
                "reason": f"cannot read output workbook: {exc}"}

    # 多份 --baseline 必须先并成一份联合快照再比：逐份独立比较时，另一份
    # baseline 合法提供的 sheet / 格会相对当前这份被误判成「产物新增」。
    try:
        base, base_truncated, conflicts, sources = _merge_baselines(baseline_paths)
    except _BaselineReadError as exc:
        return {"status": "skipped", "blocking": True, "reason": str(exc)}
    truncated = sorted(set(produced_truncated) | set(base_truncated))
    if conflicts:
        # 基准不唯一时不做逐格对照：结论会建立在「碰巧先读到的那份」上，和
        # 「先确认该传哪一份」的提示自相矛盾，还会被当成确定性错误摆出来。
        return {
            "status": "conflicted_baseline",
            "blocking": True,
            "scoped": scoped,
            "sources": sources,
            "baseline_conflicts": conflicts[:max_report],
            "truncated_sheets": truncated,
            "reason": ("多份 --baseline 在这些格上取值不同，改前基准不唯一；"
                       "本次跳过逐格对照，先确认该传哪一份再跑"),
        }

    missing_sheets, changes, formula_lost = [], [], []
    for sheet, cells in base.items():
        if sheet not in produced:
            missing_sheets.append({"baseline": ", ".join(sources), "sheet": sheet})
            continue
        out_cells = produced[sheet]
        for coord, (formula, value) in cells.items():
            out_formula, out_value = out_cells.get(coord, ("", ""))
            in_scope = scoped and _in_scope(scope, sheet, coord)
            if formula:
                if not out_formula:
                    formula_lost.append({
                        "sheet": sheet, "cell": coord, "baseline_formula": formula[:80],
                        "produced_value": out_value[:40], "in_scope": in_scope,
                    })
                elif out_formula != formula:
                    changes.append({
                        "sheet": sheet, "cell": coord, "kind": "formula",
                        "baseline": formula[:80], "produced": out_formula[:80], "in_scope": in_scope,
                    })
            elif value and out_value != value:
                changes.append({
                    "sheet": sheet, "cell": coord, "kind": "value",
                    "baseline": value[:40], "produced": out_value[:40], "in_scope": in_scope,
                })

    # 只比源里已有的格，会漏掉「范围外从空白变成有值」——scope 声明的是
    # 其余一格不动，新增同样是动。新增一律相对联合快照判定。
    additions = [a for sheet, out_cells in produced.items() if sheet in base
                 for a in _collect_additions(sheet, out_cells, base[sheet], scope, scoped)]
    added_sheets = _collect_added_sheets(produced, base, scope, scoped)

    out_of_scope = [c for c in changes if not c["in_scope"]] if scoped else []
    lost_out_of_scope = [c for c in formula_lost if not c["in_scope"]] if scoped else []
    added_out_of_scope = [c for c in additions if not c["in_scope"]] if scoped else []
    # 新增 sheet 只有在「存在范围外的格」时才阻断；没传 scope 时一律只陈述事实。
    added_sheets_blocking = [d for d in added_sheets if d["out_of_scope_cells"]] if scoped else []
    blocking = bool(missing_sheets or out_of_scope or lost_out_of_scope
                    or added_out_of_scope or added_sheets_blocking or conflicts)
    differed = bool(missing_sheets or changes or formula_lost or additions or added_sheets)
    # 状态要能单独回答「这次比得准不准」，因为下游可能只看 status：
    # 基准本身冲突时连「改前长什么样」都不唯一，比 differences_found 更靠前；
    # 截断过也不能报 clean——没读到的那部分没有判据，"没发现差异" 不等于 "没有差异"。
    if conflicts:
        status = "conflicted_baseline"
    elif differed:
        status = "differences_found"
    else:
        status = "partial" if truncated else "clean"
    result = {
        "status": status,
        "truncated_sheets": truncated,
        "blocking": blocking,
        "scoped": scoped,
        "sources": sources,
        "missing_sheets": missing_sheets[:max_report],
        "missing_sheet_count": len(missing_sheets),
        "changed_cells": len(changes),
        "formula_lost_cells": len(formula_lost),
        "added_cells": len(additions),
        "added_sheets": added_sheets[:max_report],
        "baseline_conflicts": conflicts[:max_report],
        "out_of_scope_changes": (len(out_of_scope) + len(lost_out_of_scope)
                                 + len(added_out_of_scope)),
        "details": (missing_sheets + lost_out_of_scope + out_of_scope + added_out_of_scope
                    if scoped else formula_lost + changes + additions)[:max_report],
        "sources_merged": len(sources),
    }
    if not scoped:
        result["note"] = ("未传 --scope，工具不知道哪些格该动，上面只是改动清单，不作判定；"
                          "动手前把允许改动的范围写成 --scope '子表名!G:I' 再跑一次，"
                          "范围外的改写才会被定性。")
    return result


BASELINE_HINT = """\
[baseline] 产物与源工作簿的差异触发阻断：
{lines}
源数据默认必须保留：编辑已有工作簿要在源工作簿上改，不要新建空工作簿再把结果写进去——
那样源表会整张消失。范围外被改写的格恢复原值，退化成静态值的格恢复公式，改完重跑本脚本。"""


def _emit_baseline_hint(bl: dict) -> bool:
    if not bl.get("blocking"):
        return False
    if bl.get("status") == "skipped":
        print(f"[baseline] 原表保护没跑成：{bl.get('reason')}。"
              "这不是「没发现差异」，是没有判据——换一份能读的源文件再跑。",
              file=sys.stderr)
        return True
    if bl.get("status") == "conflicted_baseline":
        lines = [f"  - {d['sheet']}!{d['cell']}：采用 {d['kept']}，与 {d['conflicting']} 不一致"
                 for d in bl.get("baseline_conflicts", [])]
        print(f"[baseline] {bl.get('reason')}：\n" + "\n".join(lines), file=sys.stderr)
        return True
    lines = []
    for d in bl.get("missing_sheets", []):
        lines.append(f"  - 源工作簿的 sheet「{d['sheet']}」在产物里不存在")
    for d in bl.get("added_sheets", []):
        if not d.get("out_of_scope_cells"):
            continue
        lines.append(f"  - 产物多出 sheet「{d['sheet']}」，其中 {d['out_of_scope_cells']} "
                     "个非空格不在 --scope 允许范围内")
    for d in bl.get("baseline_conflicts", []):
        lines.append(f"  - {d['sheet']}!{d['cell']} 在多份 --baseline 里取值不同"
                     f"（采用 {d['kept']}，与 {d['conflicting']} 冲突）：改前基准不唯一，"
                     "先确认该传哪一份")
    for d in bl.get("details", []):
        if "cell" not in d:
            continue
        if "baseline_formula" in d:
            lines.append(f"  - {d['sheet']}!{d['cell']} 原公式 {d['baseline_formula']} 变成了静态值")
        elif d.get("kind") == "added":
            lines.append(f"  - {d['sheet']}!{d['cell']} 范围外新增内容：{d['produced']}")
        else:
            lines.append(f"  - {d['sheet']}!{d['cell']} 范围外改写：{d['baseline']} → {d['produced']}")
    print(BASELINE_HINT.format(lines="\n".join(lines)), file=sys.stderr)
    return True


EXCEL_ERROR_VALUES = {"#VALUE!", "#DIV/0!", "#REF!", "#NAME?", "#NULL!", "#NUM!", "#N/A"}


def _scan_formula_error_values(filename: str) -> Tuple[int, dict]:
    """只统计公式格重算后的精确错误值；备注文本里的错误码不算公式错误。"""
    formula_wb = load_workbook(filename, data_only=False)
    value_wb = load_workbook(filename, data_only=True)
    error_details = {err: [] for err in EXCEL_ERROR_VALUES}
    total_errors = 0
    try:
        for sheet_name in formula_wb.sheetnames:
            if sheet_name not in value_wb.sheetnames:
                continue
            formula_ws = formula_wb[sheet_name]
            value_ws = value_wb[sheet_name]
            for row in formula_ws.iter_rows():
                for formula_cell in row:
                    if not _is_formula(formula_cell.value):
                        continue
                    value = value_ws[formula_cell.coordinate].value
                    if isinstance(value, str) and value.strip() in EXCEL_ERROR_VALUES:
                        error = value.strip()
                        error_details[error].append(f"{sheet_name}!{formula_cell.coordinate}")
                        total_errors += 1
    finally:
        formula_wb.close()
        value_wb.close()
    return total_errors, error_details


def scan_errors_only(filename: str, static_source_sheets: Optional[Set[str]] = None,
                     status: str = "skipped_no_libreoffice",
                     warning: str = "LibreOffice 未安装，公式未重算，仅扫描已有错误值") -> dict:
    """只扫描文件中已有的公式错误（不触发重算）。

    两种降级都走这里：LibreOffice 不可用，或副本建不出来。status / warning 由调用方
    指定，好让 JSON 里写的是真实原因。
    """
    try:
        total_errors, error_details = _scan_formula_error_values(filename)
        result = {
            "status": status,
            "formula_execution_verified": False,
            "warning": warning,
            "total_errors": total_errors,
            "error_summary": {k: {"count": len(v), "locations": v[:20]} for k, v in error_details.items() if v},
            "hardcode": detect_hardcode_suspects(filename, static_source_sheets=static_source_sheets),
            "static_risks": scan_static_risks(filename),
            "invariants": evaluate_formula_invariants(filename),
        }
        return result
    except Exception as e:
        # 解析失败不是「未重算」这种可降级状态：损坏 / 非 xlsx 文件必须以 error
        # 进入退出码，否则坏文件会打印异常后 exit 0 被当成通过
        return {"status": "invalid_input",
                "formula_execution_verified": False,
                "error": f"cannot parse workbook: {e}",
                "static_risks": {"status": "skipped", "reason": str(e)},
                "invariants": {"status": "skipped", "reason": str(e), "categories": {}}}


# 每次重算都使用独立 LibreOffice profile；宏位于 profile 内的固定相对目录。
# 共享默认 profile 在并发任务下会争用初始化锁，`--terminate_after_init` 因此可能挂死。
PROFILE_MACRO_DIR = Path("user/basic/Standard")
MACRO_FILENAME = "Module1.xba"

RECALCULATE_MACRO = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" script:language="StarBasic">
    Sub RecalculateAndSave()
      ThisComponent.calculateAll()
      ThisComponent.store()
      ThisComponent.close(True)
    End Sub
</script:module>"""


def _profile_arg(profile_dir: Path) -> str:
    """LibreOffice 的 UserInstallation 只接受 file URL。"""
    return f"-env:UserInstallation={profile_dir.resolve().as_uri()}"


def _run_managed_process(cmd: List[str], timeout: int, env: dict) -> subprocess.CompletedProcess:
    """运行并回收整棵进程树，避免超时后残留 soffice.bin 继续写文件。"""
    popen_kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "env": env,
    }
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True
    elif os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    process = subprocess.Popen(cmd, **popen_kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.05)
            # 组长退出不代表 soffice.bin 已退出；对仍存在的整个组补发 SIGKILL。
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif os.name == "nt":
            # terminate() 只杀 soffice.exe，taskkill /T 才能回收派生的 soffice.bin。
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                process.kill()
        else:
            process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)


def setup_libreoffice_macro(profile_dir: Path, timeout: int) -> Tuple[bool, str]:
    """初始化独立 profile 并安装重算宏；失败时返回可展示原因，不抛裸异常。"""
    init_timeout = max(30, timeout)
    try:
        result = _run_managed_process(
            [
                "soffice",
                _profile_arg(profile_dir),
                "--headless",
                "--norestore",
                "--terminate_after_init",
            ],
            timeout=init_timeout,
            env=get_soffice_env(),
        )
    except subprocess.TimeoutExpired:
        return False, f"LibreOffice profile initialization timed out after {init_timeout}s"
    except (FileNotFoundError, OSError) as exc:
        return False, f"LibreOffice profile initialization failed: {exc}"
    except Exception as exc:
        # get_soffice_env() 可能因 shim 准备失败抛 RuntimeError/CalledProcessError；
        # 这里同样要转成未验证状态，不能让 traceback 穿出。
        return False, f"LibreOffice environment setup failed: {exc}"

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        return False, f"LibreOffice profile initialization failed: {detail}"

    macro_dir = profile_dir / PROFILE_MACRO_DIR
    macro_file = macro_dir / MACRO_FILENAME
    try:
        macro_dir.mkdir(parents=True, exist_ok=True)
        macro_file.write_text(RECALCULATE_MACRO, encoding="utf-8")
    except OSError as exc:
        return False, f"LibreOffice macro installation failed: {exc}"
    return True, ""


def _safe_number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


CELL_REF_RE = re.compile(r"(?<![A-Z0-9_])(?:'([^']+)'!)?(\$?[A-Z]{1,3}\$?\d+)")
RANGE_FUNC_RE = re.compile(r"^=(SUM|AVERAGE)\((.+)\)$", re.IGNORECASE)
ARITH_ALLOWED_RE = re.compile(r"^[=0-9A-Z_+$\-*/().,: '\t]+$", re.IGNORECASE)
SENSITIVITY_RE = re.compile(r"sensitivity|敏感性|scenario", re.IGNORECASE)
TIEOUT_ROW_RE = re.compile(r"assets?|liabilit(?:y|ies)|equity|cash|net change|total", re.IGNORECASE)


def _split_sheet_and_ref(expr: str, current_sheet: str) -> Tuple[str, str]:
    if "!" in expr:
        sheet, ref = expr.split("!", 1)
        sheet = sheet.strip().strip("'")
        return sheet, ref
    return current_sheet, expr


def _cell_value(ws_map, sheet_name: str, coord: str):
    ws = ws_map.get(sheet_name)
    if ws is None:
        raise KeyError(sheet_name)
    return ws[coord.replace("$", "")].value


def _iter_range_values(ws_map, sheet_name: str, range_expr: str):
    start_col, start_row, end_col, end_row = range_boundaries(range_expr.replace("$", ""))
    ws = ws_map[sheet_name]
    values = []
    for row in range(start_row, end_row + 1):
        for col in range(start_col, end_col + 1):
            values.append(ws.cell(row=row, column=col).value)
    return values


def _normalize_formula_expr(expr: str, current_sheet: str):
    refs = []
    placeholder_map = {}
    counter = 0

    def repl(match):
        nonlocal counter
        sheet = match.group(1) or current_sheet
        ref = match.group(2)
        key = f"__REF_{counter}__"
        placeholder_map[key] = (sheet, ref)
        refs.append((sheet, ref))
        counter += 1
        return key

    replaced = CELL_REF_RE.sub(repl, expr)
    return replaced, placeholder_map, refs


def _eval_arithmetic_formula(expr: str, current_sheet: str, ws_map):
    body = expr.strip()
    if not body.startswith("="):
        return None
    inner = body[1:]
    if not ARITH_ALLOWED_RE.match(body):
        return None
    norm, placeholder_map, refs = _normalize_formula_expr(inner, current_sheet)
    values = {}
    for key, (sheet, ref) in placeholder_map.items():
        if ":" in ref:
            return None
        value = _safe_number(_cell_value(ws_map, sheet, ref))
        if value is None:
            return None
        values[key] = value
    try:
        import ast
        node = ast.parse(norm, mode="eval")
    except SyntaxError:
        return None

    def walk(n):
        if isinstance(n, ast.Expression):
            return walk(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = walk(n.operand)
            return v if isinstance(n.op, ast.UAdd) else -v
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left = walk(n.left)
            right = walk(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return left * right
            return left / right
        if isinstance(n, ast.Name) and n.id in values:
            return values[n.id]
        raise ValueError("unsupported arithmetic")

    try:
        return {"value": walk(node), "refs": [f"{s}!{r}" if s != current_sheet else r for s, r in refs]}
    except Exception:
        return None


def _eval_range_formula(expr: str, current_sheet: str, ws_map):
    match = RANGE_FUNC_RE.match(expr.strip())
    if not match:
        return None
    func = match.group(1).upper()
    target = match.group(2).strip()
    sheet_name, range_expr = _split_sheet_and_ref(target, current_sheet)
    if ":" not in range_expr:
        return None
    try:
        values = [_safe_number(v) for v in _iter_range_values(ws_map, sheet_name, range_expr)]
    except Exception:
        return None
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    if func == "SUM":
        out = sum(nums)
    else:
        out = sum(nums) / len(nums)
    ref = f"{sheet_name}!{range_expr}" if sheet_name != current_sheet else range_expr
    return {"value": out, "refs": [ref]}


def evaluate_formula_invariants(filename: str, max_samples: int = 8) -> dict:
    try:
        wb_formula = load_workbook(filename, data_only=False)
        wb_values = load_workbook(filename, data_only=True)
    except Exception as exc:
        return {"status": "skipped", "reason": str(exc), "categories": {}}

    ws_formula = {ws.title: ws for ws in wb_formula.worksheets}
    ws_values = {ws.title: ws for ws in wb_values.worksheets}
    categories = {
        "arithmetic": {"supported": 0, "matched": 0, "mismatched": 0, "skipped": 0, "samples": []},
        "tieout": {"supported": 0, "matched": 0, "mismatched": 0, "skipped": 0, "samples": []},
        "sensitivity": {"supported": 0, "matched": 0, "mismatched": 0, "skipped": 0, "samples": []},
    }

    def add_sample(kind: str, sample: dict):
        if len(categories[kind]["samples"]) < max_samples:
            categories[kind]["samples"].append(sample)

    try:
        for sheet_name, ws in ws_formula.items():
            values_ws = ws_values.get(sheet_name)
            if values_ws is None:
                continue
            rows = list(ws.iter_rows())
            for row in rows:
                for cell in row:
                    if not _is_formula(cell.value):
                        continue
                    formula_text = _formula_text(cell.value)
                    result = _eval_range_formula(formula_text, sheet_name, ws_values) or _eval_arithmetic_formula(formula_text, sheet_name, ws_values)
                    if result is None:
                        categories["arithmetic"]["skipped"] += 1
                        continue
                    actual = _safe_number(values_ws[cell.coordinate].value)
                    if actual is None:
                        categories["arithmetic"]["skipped"] += 1
                        continue
                    expected = result["value"]
                    categories["arithmetic"]["supported"] += 1
                    tolerance = max(1e-6, abs(expected) * 1e-6)
                    if abs(actual - expected) <= tolerance:
                        categories["arithmetic"]["matched"] += 1
                    else:
                        categories["arithmetic"]["mismatched"] += 1
                        add_sample("arithmetic", {
                            "sheet": sheet_name,
                            "cell": cell.coordinate,
                            "formula": cell.value,
                            "expected": expected,
                            "actual": actual,
                            "refs": result["refs"],
                        })

            header = {c.column: str(c.value).strip() if c.value is not None else "" for c in ws[1]}
            label_col = 1 if ws.max_column >= 1 else None
            value_col = None
            for col, title in header.items():
                low = title.lower()
                if TIEOUT_ROW_RE.search(low):
                    label_col = col
                if value_col is None and low in {"value", "amount", "金额", "数值"}:
                    value_col = col
            if value_col is None and ws.max_column >= 2:
                value_col = 2
            if label_col and value_col:
                labels = {}
                for r in range(2, min(ws.max_row, 200) + 1):
                    label = ws.cell(row=r, column=label_col).value
                    value = _safe_number(values_ws.cell(row=r, column=value_col).value)
                    if isinstance(label, str) and value is not None:
                        labels[label.strip().lower()] = value
                def _pick(keywords, exclude=()):
                    # 只认「类别词 + 总计词」同现的标签：普通 KPI（Return on Assets /
                    # Liability Ratio）没有总计词，不再被当成资产负债表勾稽项误报；
                    # 明细行（Current Assets）也不再顶替总计行。exclude 做类别互斥——
                    # 「负债和所有者权益总计 / total liabilities and equity」是合计行
                    # （数值 = 资产总计），单类命中会让勾稽整体错位。
                    total_keys = ("total", "总计", "合计", "总额")
                    def ok(k):
                        return (any(w in k for w in keywords)
                                and any(t in k for t in total_keys)
                                and not any(x in k for x in exclude))
                    return next((v for k, v in labels.items() if ok(k)), None)

                assets = _pick(("asset", "资产"), exclude=("liabilit", "负债", "equity", "权益"))
                liabilities = _pick(("liabilit", "负债"), exclude=("equity", "权益"))
                equity = _pick(("equity", "权益"), exclude=("liabilit", "负债"))
                if assets is not None and liabilities is not None and equity is not None:
                    categories["tieout"]["supported"] += 1
                    expected = liabilities + equity
                    tolerance = max(1e-6, abs(expected) * 1e-6)
                    if abs(assets - expected) <= tolerance:
                        categories["tieout"]["matched"] += 1
                    else:
                        categories["tieout"]["mismatched"] += 1
                        add_sample("tieout", {
                            "sheet": sheet_name,
                            "rule": "assets_equals_liabilities_plus_equity",
                            "expected": expected,
                            "actual": assets,
                        })
                else:
                    categories["tieout"]["skipped"] += 1
            else:
                categories["tieout"]["skipped"] += 1

            # 首版 sensitivity invariant 只在能唯一定位 main output + baseline intersection 时才可信；
            # 当前没有稳定结构证据时一律 skipped，避免把「baseline != scenario」误当可靠自洽性。
            categories["sensitivity"]["skipped"] += 1
    finally:
        wb_formula.close()
        wb_values.close()

    mismatch_total = sum(categories[k]["mismatched"] for k in categories)
    return {
        "status": "warn" if mismatch_total else "clean",
        "categories": categories,
        "supported": sum(categories[k]["supported"] for k in categories),
        "mismatched": mismatch_total,
    }


def _quiet_unlink(path: Path):
    """删除文件，不存在就算了。Python 3.7 的 unlink() 没有 missing_ok 形参。"""
    try:
        path.unlink()
    except OSError:
        pass


class _WorkspaceError(Exception):
    """副本创建失败。独立异常类型，避免把重算阶段的 OSError 误报成「创建副本失败」。"""


@contextlib.contextmanager
def _recalc_workspace(filename: str):
    """把待校验文件复制成临时副本；重算只作用于副本，原文件全程只读。

    LibreOffice 的 store() 会重写整个工作簿——工作簿默认字体被换成它自己的默认
    字体，列宽账面值随之按新字体的字符宽度基准重算，图案填充与会计式括号负数
    格式也会被改写。诊断不该以改动交付物为代价，所以重算跑在副本上。
    副本优先落在原文件同目录：LibreOffice 解析跨工作簿的相对路径外部引用要靠它。
    """
    src = Path(filename).absolute()
    last_error = None
    for parent in (src.parent, Path(tempfile.gettempdir())):
        try:
            fd, name = tempfile.mkstemp(
                dir=str(parent), prefix=f".{src.stem}.verify-", suffix=src.suffix
            )
        except OSError as exc:  # 原目录只读时退到系统临时目录
            last_error = exc
            continue
        tmp = Path(name)
        os.close(fd)
        try:
            shutil.copyfile(src, tmp)
        except OSError as exc:  # 磁盘满 / 写入受限：同样换下一个候选目录
            last_error = exc
            _quiet_unlink(tmp)
            continue
        try:
            yield tmp
            return
        finally:
            _quiet_unlink(tmp)
            # soffice 被超时杀掉时锁文件不会自己消失
            _quiet_unlink(tmp.parent / f".~lock.{tmp.name}#")
    raise _WorkspaceError(f"cannot create verification copy for {src}: {last_error}")


def _append_warning(result: dict, message: str) -> None:
    current = result.get("warning")
    result["warning"] = f"{current}；{message}" if current else message


def _unverified_result(reason: str, scan_path: Optional[Path] = None,
                       preflight: Optional[dict] = None,
                       static_source_sheets: Optional[Set[str]] = None,
                       recalculation_completed: bool = False,
                       in_place: bool = False) -> dict:
    """从未被 LibreOffice 写过的路径/快照诊断，避免解析可能半写坏的 target。"""
    if preflight is not None:
        result = dict(preflight)
    elif scan_path is not None:
        result = scan_errors_only(
            str(scan_path), static_source_sheets=static_source_sheets,
            status="inconclusive", warning="formula recalculation was not completed",
        )
    else:
        result = {
            "status": "inconclusive",
            "formula_execution_verified": False,
            "total_errors": 0,
            "error_summary": {},
            "hardcode": {"status": "skipped", "reason": "no safe workbook snapshot"},
            "static_risks": {"status": "skipped", "reason": "no safe workbook snapshot"},
            "invariants": {"status": "skipped", "reason": "no safe workbook snapshot", "categories": {}},
        }

    invalid_input = result.get("status") == "invalid_input"
    if not invalid_input:
        result["status"] = "inconclusive"
        result.pop("error", None)
    result["formula_execution_verified"] = False
    result["recalculation_completed"] = recalculation_completed
    if in_place and recalculation_completed:
        result["in_place_modified"] = True
        reason += "；--in-place 原文件已由 LibreOffice 保存"
    suffix = "后续扫描未完成" if recalculation_completed else "公式未重算"
    _append_warning(result, f"{reason}；{suffix}，不得声称已验证无错误")
    return result


def _recalc_with_profile(target: Path, profile_dir: Path, timeout: int,
                         safe_scan_path: Optional[Path], preflight: Optional[dict],
                         static_source_sheets: Optional[Set[str]], in_place: bool) -> dict:
    abs_path = str(target)
    ready, reason = setup_libreoffice_macro(profile_dir, timeout)
    if not ready:
        return _unverified_result(
            reason, scan_path=safe_scan_path, preflight=preflight,
            static_source_sheets=static_source_sheets, in_place=in_place,
        )

    cmd = [
        "soffice",
        _profile_arg(profile_dir),
        "--headless",
        "--norestore",
        "vnd.sun.star.script:Standard.Module1.RecalculateAndSave?language=Basic&location=application",
        abs_path,
    ]

    # 超时由 _run_managed_process 统一处理并清理进程树；不再套外部 timeout，
    # 否则进程组只包含 timeout 包装器，无法可靠回收它派生的 soffice.bin。
    try:
        process_result = _run_managed_process(cmd, timeout + 30, get_soffice_env())
    except subprocess.TimeoutExpired:
        return _unverified_result(
            f"LibreOffice recalculation timed out after {timeout + 30}s",
            scan_path=safe_scan_path, preflight=preflight,
            static_source_sheets=static_source_sheets, in_place=in_place,
        )
    except (FileNotFoundError, OSError) as exc:
        return _unverified_result(
            f"LibreOffice recalculation failed: {exc}", scan_path=safe_scan_path, preflight=preflight,
            static_source_sheets=static_source_sheets, in_place=in_place
        )
    except Exception as exc:
        return _unverified_result(
            f"LibreOffice environment setup failed: {exc}", scan_path=safe_scan_path, preflight=preflight,
            static_source_sheets=static_source_sheets, in_place=in_place
        )

    if process_result.returncode == 124:
        return _unverified_result(
            f"LibreOffice recalculation timed out after {timeout}s; cached formula values are not authoritative",
            scan_path=safe_scan_path, preflight=preflight,
            static_source_sheets=static_source_sheets, in_place=in_place,
        )
    if process_result.returncode != 0:
        error_msg = (process_result.stderr or process_result.stdout or "Unknown error during recalculation").strip()
        if "Module1" in error_msg and "RecalculateAndSave" in error_msg:
            error_msg = "LibreOffice macro not configured properly"
        return _unverified_result(
            error_msg, scan_path=safe_scan_path, preflight=preflight,
            static_source_sheets=static_source_sheets, in_place=in_place,
        )

    try:
        total_errors, error_details = _scan_formula_error_values(abs_path)

        result = {
            "status": "success" if total_errors == 0 else "errors_found",
            "formula_execution_verified": True,
            "recalculation_completed": True,
            "in_place_modified": bool(in_place),
            "total_errors": total_errors,
            "error_summary": {},
        }

        for err_type, locations in error_details.items():
            if locations:
                result["error_summary"][err_type] = {
                    "count": len(locations),
                    "locations": locations[:20],
                }

        wb_formulas = load_workbook(abs_path, data_only=False)
        try:
            formula_count = sum(
                1
                for ws in wb_formulas.worksheets
                for row in ws.iter_rows()
                for cell in row
                if _is_formula(cell.value)
            )
        finally:
            wb_formulas.close()

        result["total_formulas"] = formula_count
        result["hardcode"] = detect_hardcode_suspects(abs_path, static_source_sheets=static_source_sheets)
        # 静态风险扫源文件：LibreOffice 存回副本时会顺手补上 _xlfn 前缀，
        # 扫重算后的副本会把「Excel 打开就 #NAME?」的公式洗白。
        result["static_risks"] = scan_static_risks(str(safe_scan_path or abs_path))
        result["invariants"] = evaluate_formula_invariants(abs_path)
        return result

    except Exception as exc:
        return _unverified_result(
            f"LibreOffice recalculation finished but result scanning failed: {exc}",
            scan_path=safe_scan_path, preflight=preflight,
            static_source_sheets=static_source_sheets,
            recalculation_completed=True, in_place=in_place,
        )


def _recalc_target(target: Path, timeout: int, static_source_sheets: Optional[Set[str]] = None,
                   in_place: bool = False, safe_scan_path: Optional[Path] = None):
    """在 target 上重算；失败诊断只读取未被 LibreOffice 写过的安全快照。"""
    preflight = None
    if in_place:
        # --in-place 会改原文件，必须在启动 LibreOffice 前留住只读诊断结果。
        preflight = scan_errors_only(
            str(target), static_source_sheets=static_source_sheets,
            status="inconclusive", warning="formula recalculation has not started",
        )
        if preflight.get("status") == "invalid_input":
            return preflight
    elif safe_scan_path is None:
        # 内部调用方未提供源文件时，先留快照，避免失败后读取可能半写坏的 target。
        preflight = scan_errors_only(
            str(target), static_source_sheets=static_source_sheets,
            status="inconclusive", warning="formula recalculation has not started",
        )
        if preflight.get("status") == "invalid_input":
            return preflight

    try:
        profile_dir = Path(tempfile.mkdtemp(prefix="excel-formula-profile-"))
    except OSError as exc:
        return _unverified_result(
            f"cannot create LibreOffice profile: {exc}", scan_path=safe_scan_path,
            preflight=preflight, static_source_sheets=static_source_sheets,
            in_place=in_place,
        )

    result = None
    cleanup_warning = None
    try:
        result = _recalc_with_profile(
            target, profile_dir, timeout, safe_scan_path, preflight,
            static_source_sheets, in_place,
        )
    except Exception as exc:
        result = _unverified_result(
            f"unexpected LibreOffice verification failure: {exc}",
            scan_path=safe_scan_path, preflight=preflight,
            static_source_sheets=static_source_sheets, in_place=in_place,
        )
    finally:
        try:
            shutil.rmtree(profile_dir)
        except OSError as exc:
            cleanup_warning = f"cannot remove LibreOffice profile {profile_dir}: {exc}"
    if cleanup_warning:
        _append_warning(result, cleanup_warning)
    return result


def recalc(filename, timeout=30, static_source_sheets: Optional[Set[str]] = None,
           in_place: bool = False):
    if not Path(filename).exists():
        return {"error": f"File {filename} does not exist"}

    if not is_libreoffice_available():
        return scan_errors_only(filename, static_source_sheets=static_source_sheets)

    if in_place:
        return _recalc_target(
            Path(filename).absolute(), timeout, static_source_sheets, in_place=True
        )

    src = Path(filename).absolute()
    src_dir = src.parent
    try:
        with _recalc_workspace(filename) as target:
            result = _recalc_target(
                target, timeout, static_source_sheets, safe_scan_path=src
            )
            if target.parent != src_dir:
                # 退到系统临时目录后，工作簿里相对路径的跨文件引用解析不到，
                # 重算会吐出 #REF!。调用方必须能分辨这种 #REF! 不可信。
                result["recalc_copy_dir"] = str(target.parent)
                _append_warning(
                    result,
                    f"产物目录不可写，副本落在 {target.parent}；若工作簿含相对路径的跨文件引用，"
                    "重算出的 #REF! 可能是解析失败而非真实公式错误",
                )
            return result
    except _WorkspaceError as exc:
        # 两个候选目录都建不出副本：退回只读扫描，仍然不碰原文件
        return scan_errors_only(
            filename,
            static_source_sheets=static_source_sheets,
            status="skipped_no_workspace",
            warning=f"无法创建副本（{exc}），公式未重算，仅扫描已有错误值；需要重算可加 --in-place",
        )


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Excel 交付门禁：重算并校验公式错误，静态扫描新函数前缀与数组形状，"
            "扫描推导列/行的静态值硬编码嫌疑；传 --baseline 时另比对源工作簿。"
            "全部通过退出 0；确定性错误退出 3（必须修复后重跑）；"
            "重算未完成或仅命中诊断信号退出 4（按 stderr 提示处置，不反复重跑）。"
        )
    )
    ap.add_argument("excel_file")
    ap.add_argument(
        "timeout_seconds",
        nargs="?",
        type=int,
        default=30,
        help="重算超时秒数（保留旧 positional timeout 兼容）",
    )
    ap.add_argument(
        "--static-source-sheets",
        help="显式声明允许保留静态历史/外部数据的 sheet 名，逗号分隔、精确匹配；这些 sheet 的 hardcode suspect 降为 low/WARN",
    )
    ap.add_argument(
        "--baseline",
        action="append",
        default=None,
        metavar="SRC.xlsx",
        help="源工作簿（编辑已有文件时的改前基准，可重复）。逐格比对值与公式，报出被改写的原值、退化成静态值的原公式和丢失的 sheet",
    )
    ap.add_argument(
        "--scope",
        action="append",
        default=None,
        metavar="RANGE",
        help="本轮允许改动的范围，如 '明细!G:I' / '汇总' / '明细!A2:C10'，逗号分隔或重复本参数；与 --baseline 同用时范围外的改写判为错误，不传则只列改动清单",
    )
    ap.add_argument(
        "--checkpoints",
        metavar="@FILE",
        help="任务检查点 JSON（`@./checkpoints.json` 或内联）：逐条回读产物，判期望值、必须是公式的区域、必须存在的子表",
    )
    ap.add_argument(
        "--in-place",
        action="store_true",
        help="在原文件上公式求值并保存。但注意：使用 excel_formula_verify.py --in-place 会出现预期之外的写入、例如行高、列宽、符号、数字格式、颜色、底纹等被 LibreOffice 重置。若不想改动原文件，请不要加 --in-place，脚本会在临时副本上重算。",
    )
    args = ap.parse_args()

    # --scope 先验：范围写错就当场报错退出，绝不带着一个被悄悄放大成整表的
    # 边界继续跑——那样范围外的改写会被判成允许。
    try:
        parse_scope(args.scope or [])
    except ScopeError as exc:
        print(f"[scope] {exc}", file=sys.stderr)
        sys.exit(3)

    static_source_sheets, static_source_sheet_list = _normalize_sheet_names(args.static_source_sheets)
    result = recalc(args.excel_file, args.timeout_seconds, static_source_sheets=static_source_sheets,
                    in_place=args.in_place)
    checkpoints, checkpoint_error = load_checkpoints(args.checkpoints)
    if checkpoint_error:
        result["checkpoints"] = {"status": "invalid", "reason": checkpoint_error}
    elif checkpoints:
        result["checkpoints"] = run_checkpoints(args.excel_file, checkpoints)

    if args.baseline:
        result["baseline"] = diff_baseline(args.excel_file, args.baseline, args.scope or [])
    elif args.scope:
        result["baseline"] = {
            "status": "skipped",
            "degraded": True,
            "reason": "给了 --scope 但没给 --baseline；没有改前基准就比不出范围外的改写",
        }

    hc = result.get("hardcode") or {}
    unknown_static_source_sheets = hc.get("unknown_static_source_sheets") or []
    if unknown_static_source_sheets:
        # 参数写错不是「产物读不出来」：工作簿读开了、只读诊断也跑过了，走独立字段，
        # 别复用 error 通道把 INVALID_INPUT_HINT 的「一项都没跑」误扣到这里。
        result["param_error"] = f"Unknown --static-source-sheets: {', '.join(unknown_static_source_sheets)}"
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 副本降级只在 JSON 里带字段容易被忽略；stderr 再喊一次，免得 #REF! 被误当真错误
    if result.get("recalc_copy_dir") or result.get("status") == "skipped_no_workspace":
        print(f"[recalc] {result.get('warning')}", file=sys.stderr)

    if static_source_sheet_list:
        print(
            "[hardcode] 已声明静态来源 sheet：" + "、".join(static_source_sheet_list)
            + "——仅这些 sheet 的 hardcode suspect 会降为 WARN，其它 sheet 仍按原规则判定。",
            file=sys.stderr,
        )
    if unknown_static_source_sheets:
        print(
            "[hardcode] 未知的 --static-source-sheets：" + "、".join(unknown_static_source_sheets)
            + "——sheet 名必须精确匹配工作簿里的现有 sheet；修正参数后重跑。",
            file=sys.stderr,
        )

    if result.get("error"):
        # 读不出来的输入走退出码 3，别套用退出码 4 的「不要重跑」文案，
        # 也不能说只读诊断跑过了——它们全被 skip 了。
        print(INVALID_INPUT_HINT.format(
            status=result.get("status"), error=result.get("error")),
            file=sys.stderr)
    elif result.get("formula_execution_verified") is False:
        print(RECALC_UNVERIFIED_HINT.format(
            status=result.get("status"),
            warning=result.get("warning") or "未给出原因"),
            file=sys.stderr)

    has_high = _emit_hardcode_hint(hc) if hc.get("status") == "suspected" else False
    cp = result.get("checkpoints") or {}
    if cp.get("status") == "invalid":
        print(f"[checkpoints] {cp.get('reason')}", file=sys.stderr)
        has_checkpoint_break = True
        has_checkpoint_skip = False
    else:
        has_checkpoint_break = emit_checkpoint_hint(
            cp, lambda text: print(text, file=sys.stderr))
        # 判不了的检查点走降级档：不是「产物做错了」，而是「还没判到」。
        has_checkpoint_skip = emit_checkpoint_skip_hint(
            cp, lambda text: print(text, file=sys.stderr))
        # 汇总状态兜底：只认 pass 为跑过了。任何别的状态（含没有任何 detail 的
        # skipped）都不能靠「details 里没有 fail」推出通过。
        cp_status = cp.get("status")
        if cp.get("blocking"):
            # I/O 失败：门禁没跑成，按确定性错误处置。
            print(f"[checkpoints] 检查点没跑成：{cp.get('reason')}。"
                  "这不是「没发现问题」，是没有判据。", file=sys.stderr)
            has_checkpoint_break = True
        elif cp_status is not None and cp_status not in {"pass", "failed"}:
            has_checkpoint_skip = True
            if cp_status == "skipped":
                print("[checkpoints] 一条判据都没执行（status=skipped）：检查点没起到作用，"
                      "确认契约里写了 expect / non_empty / formula / all_formula。",
                      file=sys.stderr)
    bl = result.get("baseline") or {}
    has_baseline_break = _emit_baseline_hint(bl)
    # 截断说明尾部没比到，属"判不了"而不是"判过了"，走降级档。
    baseline_not_run = bool(bl.get("degraded"))
    if baseline_not_run:
        print(f"[baseline] {bl.get('reason')}。原表保护这条没有判据，"
              "把源文件用 --baseline 一并传进来才判得了。", file=sys.stderr)
    baseline_truncated = bl.get("truncated_sheets") or []
    if baseline_truncated:
        print(f"[baseline] 这些 sheet 超过 {BASELINE_MAX_CELLS} 格上限，只比对了前半部分："
              f"{'、'.join(baseline_truncated[:6])}。"
              "未读到的区域没有判据，不能据此认为原表没被改写；"
              "缩小表体或拆表后重跑才能覆盖尾部。", file=sys.stderr)
    sr = result.get("static_risks") or {}
    has_static_risk = _emit_static_risk_hint(sr) if sr.get("status") == "issues_found" else False
    has_formula_errors = bool(result.get("total_errors")) or result.get("status") == "errors_found"
    has_unverified = (
        result.get("formula_execution_verified") is False
        or result.get("status") in {"inconclusive", "skipped_no_libreoffice", "skipped_no_workspace"}
    )
    has_runtime_error = bool(result.get("error")) or bool(result.get("param_error"))
    # 退出码分两档，因为这两类的处置相反，混成一个码就没法照着做：
    # 3 = 确定性错误（公式错误 / 缺前缀或形状错 / 检查点不符 / 源表被改写或丢失 /
    #     文件读不了或静态来源点名错误），必须修复后重跑；
    # 4 = 重算未完成，或只命中诊断信号（高置信硬编码嫌疑）——按提示处置并在交付说明写明，
    #     不反复重跑；0 = 确定性判定全过且重算完成。
    blocking = (has_formula_errors or has_runtime_error or has_static_risk
                or has_baseline_break or has_checkpoint_break)
    degraded = (has_unverified or has_high or has_checkpoint_skip
                or bool(baseline_truncated) or baseline_not_run)
    sys.exit(3 if blocking else (4 if degraded else 0))


if __name__ == "__main__":
    main()
