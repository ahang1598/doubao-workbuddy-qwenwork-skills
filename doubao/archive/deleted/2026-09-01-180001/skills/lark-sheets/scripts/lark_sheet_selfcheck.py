#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT


from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections import Counter, defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lark_sheet_read_cli import (  # noqa: E402
    LarkCliError,
    envelope_data,
    extract_sheets,
    run_sheets,
    sheet_title,
)

# ── 观测能力上限 ──────────────────────────────────────────────────
# 单 sheet 读取上限，防 row_count 数万时读上百页。
# 取 5100 而非 5000：实测有表恰好 5001 行，卡 5000 会让它
# 因为超出 1 行就降级成 CHECK_INCOMPLETE，属于无谓噪声。
MAX_ROWS = 5100
PAGE_ROWS = 400        # 分页窗口
MAX_LIST = 6           # 单条规则最多列几个坐标
MAX_FINDINGS = 10      # 高置信度发现总条数上限

# ── 高置信度规则的阈值（依据：46 个满分产物实测）────────────────────
ERROR_VALUES = ("#VALUE!", "#NAME?", "#REF!", "#DIV/0!", "#N/A", "#NUM!", "#NULL!")
ISLAND_MIN_CELLS = 20      # 列内至少这么多非空格才谈「孤岛」，小样本没有统计意义
ISLAND_MAJOR_RATIO = 0.90  # 多数模式占比下限
ISLAND_MAX_MINOR = 3       # 少数派最多这么多格 —— 再多就是两种合法分区，不是漏
PERCENT_LIMIT = 1000.0     # 显示值超过 1000% 才算量纲错。150%/200% 是合法增长率
REPEAT_MIN_BLOCKS = 3      # 至少这么多同构区块才做横向对照
RAGGED_MIN_CELLS = 20      # 「大块」数值列的门槛：不足这么多格不谈格式参差
RAGGED_MIN_SPREAD = 2      # 最大与最小小数位之差；差 1 位是数据自然精度，不算参差

NUMERIC_RE = re.compile(r"^-?[\d,]*\.?\d+$")
PERCENT_RE = re.compile(r"^(-?[\d,]*\.?\d+)\s*%$")
REF_RE = re.compile(r"^([A-Z]+)(\d+)$")
RANGE_RE = re.compile(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$")

# 飞书 AI 公式（AI_ASK / AI_CLASSIFY / AI_EXTRACT / AI_TRANSLATE / AI_SUMMARIZE 等）
# 实测两点：① 求值是异步的 —— 改动依赖后立刻回读，A2 会返回 "#ERROR" 字面串
# （飞书用它做占位），能持续数分钟；② 各产品线未来占位形态未必都是 "#ERROR"，
# 也有可能出成 "#N/A" 之类落入我们的 ERROR_VALUES 触发误报。
# 处理策略：**静默豁免** —— 所有规则跳过这类格，不报也不提示。
# 理由：目前模型基本不主动使用 AI 公式，误报的代价高于漏报；将来若模型开始
# 大量使用 AI 公式，可以把这里改成「计数出结构特征提醒」。
AI_FORMULA_RE = re.compile(r"\bAI[_.]\w+\s*\(", re.I)


def is_ai_formula_cell(rec) -> bool:
    return bool(rec and AI_FORMULA_RE.search(str(rec.get("f") or "")))


# ────────────────────────── 坐标与值（复用旧版）──────────────────────────


def col_letter(idx: int) -> str:
    out = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        out = chr(65 + rem) + out
    return out


def col_index(letter: str) -> int:
    n = 0
    for ch in letter:
        n = n * 26 + (ord(ch) - 64)
    return n


def split_ref(ref: str) -> tuple[int, int]:
    m = REF_RE.match(ref)
    if not m:
        raise ValueError(f"bad ref {ref!r}")
    return int(m.group(2)), col_index(m.group(1))


def as_display(value: Any) -> str:
    """cells-get 的 value 统一成显示值字符串。非公式格返回字符串，公式格返回数字。"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return repr(value)
    return str(value)


def as_number(text: str) -> float | None:
    t = text.strip().replace(",", "")
    if not t or not NUMERIC_RE.match(t):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def render_units(text: str) -> int:
    """渲染宽度：全角/CJK 记 2。"""
    return sum(2 if ord(ch) > 0x2E7F else 1 for ch in text)


def style_signature(cell: dict[str, Any]) -> str:
    """样式指纹：背景色 / 字重 / 字色 / 四边框 / 数字格式。

    注意它是**不透明**的：只能比较两格是否相同，无法反解出「是红色」或
    「是居中」。所以本工具只报「这几格与本列多数不同」，绝不断言颜色。
    """
    styles = cell.get("cell_styles") or {}
    borders = cell.get("border_styles") or {}
    edges = "".join(
        "1" if isinstance(borders.get(s), dict) and borders[s].get("style") else "0"
        for s in ("top", "bottom", "left", "right")
    )
    return "|".join([
        str(styles.get("back_color") or styles.get("background_color") or ""),
        str(styles.get("font_weight") or ""),
        str(styles.get("font_color") or ""),
        edges,
        str(styles.get("number_format") or ""),
    ])


def truncate(items: list[str], limit: int = MAX_LIST) -> tuple[list[str], int]:
    return (items, 0) if len(items) <= limit else (items[:limit], len(items) - limit)


# ────────────────────────── lark-cli 调用（新增重试）──────────────────────────

TRANSIENT = ("bad gateway", "502", "503", "504", "timed out", "was not JSON",
             "invalid_response", "connection reset", "temporarily",
             # 飞书 API 限流。实测批量跑时命中 code 99991400
             # "request trigger frequency limit"，老的重试列表漏了它 → 直接失败。
             # 生产上模型并发跑多个任务时同样会撞到。
             "frequency limit", "rate limit", "too many requests", "429", "99991400")
RATE_LIMIT_HINT = ("frequency limit", "rate limit", "too many requests", "429", "99991400")


def call(shortcut: str, *, tries: int = 3, backoff: float = 2.0, **kw) -> dict[str, Any]:
    """带退避重试的 run_sheets。

    为什么必须加这层：真实点测里第一次 validate 跑了 120 秒撞上限，
    原因是 lark-cli 返回 `bad gateway`（非 JSON），run_sheets 直接抛错、
    脚本 exit 1；模型的反应是放弃工具、改用自己的口头断言。
    而第二次重跑只用 5.5 秒就成功 —— 是瞬时故障。
    只重试**瞬时错误**：权限、参数、找不到 sheet 这类重试没有意义。
    """
    last: Exception | None = None
    for attempt in range(1, tries + 1):
        try:
            return run_sheets(shortcut, **kw)
        except LarkCliError as exc:
            last = exc
            msg = str(exc).lower()
            if not any(t in msg for t in TRANSIENT) or attempt == tries:
                raise
            # 限流要等得更久 —— 立刻重试只会继续撞同一个配额窗口
            wait = backoff * attempt
            if any(t in msg for t in RATE_LIMIT_HINT):
                wait = max(wait, 5.0 * attempt)
            time.sleep(wait)
    raise last  # pragma: no cover


# ────────────────────────── 读取层 ──────────────────────────


def locator(target: str) -> dict[str, str]:
    """URL 或裸 token 都接受。"""
    t = target.strip()
    return {"url": t} if t.startswith("http") else {"spreadsheet_token": t}


def read_cells(loc, sheet_id: str, rows: int, cols: int) -> dict[str, dict]:
    """整表读回，按行窗口分页。返回 {"A1": {v,f,nf,s}}"""
    cells: dict[str, dict] = {}
    if rows < 1 or cols < 1:
        return cells
    last_col, start = col_letter(cols), 1
    while start <= rows:
        end = min(start + PAGE_ROWS - 1, rows)
        before = len(cells)
        data = envelope_data(call(
            "+cells-get", sheet_id=sheet_id,
            flags={"range": f"A{start}:{last_col}{end}",
                   "include": "value,formula,style", "skip_hidden": False},
            timeout=180, **loc))
        for rng in data.get("ranges") or []:
            ridx = rng.get("row_indices") or list(range(start, end + 1))
            cidx = rng.get("col_indices") or [col_letter(i) for i in range(1, cols + 1)]
            for i, row in enumerate(rng.get("cells") or []):
                for j, cell in enumerate(row):
                    if not isinstance(cell, dict) or not cell:
                        continue
                    disp, formula = as_display(cell.get("value")), cell.get("formula")
                    if not disp and not formula:
                        continue
                    if i >= len(ridx) or j >= len(cidx):
                        continue
                    raw = cell.get("value")
                    rec: dict[str, Any] = {
                        "v": disp, "s": style_signature(cell),
                        # 原始类型。as_display 会把数字 1234 和文本 "1234" 都变成
                        # "1234"，不在这里记下来就再也分不开了，而「本该是数值的列
                        # 里混着文本数字」正是要查的形态。
                        "t": ("num" if isinstance(raw, (int, float))
                              and not isinstance(raw, bool) else "text"),
                    }
                    if formula:
                        rec["f"] = formula
                    nf = (cell.get("cell_styles") or {}).get("number_format")
                    if nf:
                        rec["nf"] = nf
                    cells[f"{cidx[j]}{ridx[i]}"] = rec
        if start > 1 and len(cells) == before:
            break   # 连续一页无非空格 → 数据到底了，不必把分配网格读完
        start = end + 1
    return cells


def read_sheet(loc, sheet: dict) -> dict[str, Any]:
    sid = str(sheet.get("sheet_id") or sheet.get("id") or "")
    rows = int(sheet.get("row_count") or 0)
    cols = int(sheet.get("column_count") or 0)
    notes: list[str] = []
    if rows > MAX_ROWS:
        notes.append(f"仅读取前 {MAX_ROWS} 行（实际 {rows} 行）")
        rows = MAX_ROWS
    info = envelope_data(call("+sheet-info", sheet_id=sid, timeout=120, **loc))
    return {
        "id": sid,
        # 复用 lark_sheet_read_cli.sheet_title()：`title → sheet_name → name`。
        # 契约（references/lark-sheets-workbook.md）写明「优先取 title、缺失再回退
        # sheet_name」，本文件原先写成 `sheet_name or title`，顺序正好相反。实测当前
        # 后端 title 恒为 None、sheet_name 才有值，两种写法结果相同，所以这不是在
        # 修一个现存的错坐标，是把顺序对齐契约 —— 哪天后端开始返回 title（重命名后
        # 旧字段残留是最可能的形态），错的那一版会让所有 `name!A1` 前缀指向错的 sheet，
        # 而坐标是本工具唯一的可核查入口。
        "name": sheet_title(sheet),
        "rows": rows, "cols": cols,
        "merged": sorted(str(m.get("range")) for m in (info.get("merged_cells") or [])
                         if isinstance(m, dict) and m.get("range")),
        "cells": read_cells(loc, sid, rows, cols),
        "notes": notes,
    }


def read_workbook(target: str) -> tuple[dict[str, Any], list[str]]:
    """返回 (workbook, unread)。unread 只装**真的读不到**的区域。

    不要往 unread 里塞「规则没跑成」或「发现没展示全」—— 那两类数据其实读到了，
    混进来会让结论句说出「部分数据没读全」，而 L853 的指引又会让调用方去回读一个
    根本不缺的区域。它们分别走 main 里的 unchecked / notices。
    """
    loc = locator(target)
    unread: list[str] = []
    wb = envelope_data(call("+workbook-info", timeout=120, **loc))
    sheets = []
    for sh in extract_sheets(wb):
        try:
            sheets.append(read_sheet(loc, sh))
        except LarkCliError as exc:
            unread.append(f"sheet「{sheet_title(sh)}」读取失败："
                          f"{str(exc)[:80]}")
    for s in sheets:
        unread.extend(f"{s['name']}: {n}" for n in s["notes"])
    return {"loc": loc, "revision": wb.get("revision"), "sheets": sheets}, unread


# ────────────────────────── 列切片（规则的公共输入）──────────────────────────


def merged_slaves(sheet: dict) -> set[tuple[int, int]]:
    """合并区里除左上角以外的格。

    这些格按 API 读回来一律是空值 —— 值只存在左上角。不排除它们的话，
    「列内空洞」会把每一个纵向合并表头都报成漏格。实测踩到过：
    U069 的 A2/C2/H2、U073 的 A4/C4/D4 全是 H1:H2 这类纵向合并表头的续格。
    """
    out: set[tuple[int, int]] = set()
    for rng in sheet.get("merged") or []:
        m = RANGE_RE.match(str(rng))
        if not m:
            continue
        col1, row1 = col_index(m.group(1)), int(m.group(2))
        col2, row2 = col_index(m.group(3)), int(m.group(4))
        rows = range(min(row1, row2), max(row1, row2) + 1)
        cols = range(min(col1, col2), max(col1, col2) + 1)
        out.update((r, c) for r in rows for c in cols if (r, c) != (row1, col1))
    return out


def columns_of(sheet: dict) -> dict[int, dict[int, dict]]:
    """按列聚拢：{列号: {行号: rec}}。规则大多是列内统计。

    合并区的从属格在这一层就排掉 —— 它们不是独立单元格，任何列内统计
    都不该把它们算成「有值」或「空洞」。
    """
    slaves = merged_slaves(sheet)
    cols: dict[int, dict[int, dict]] = defaultdict(dict)
    for ref, rec in sheet["cells"].items():
        try:
            r, c = split_ref(ref)
        except ValueError:
            continue
        if (r, c) in slaves:
            continue
        cols[c][r] = rec
    return cols


# 标识符列（编码/工号/SKU/单号…）里「多数格恰好只含数字」是常态，
# 少数含字母或下划线的编码同样合法。实测 U148 的 D 列「商品编码（自定义）」
# 里 09000016718 与 260308_XH1935DQ6ST6 并存 —— 那不是脏数据。
ID_COL_RE = re.compile(r"(编码|编号|代码|编号|工号|卡号|证号|单号|订单|批号|"
                       r"\bID\b|\bSKU\b|\bcode\b|\bno\.?\b)", re.I)
AGG_RE = re.compile(r"\b(SUM|SUMIF|SUMIFS|SUBTOTAL|AVERAGE|AVERAGEIF|COUNT|COUNTA|"
                    r"COUNTIF|COUNTIFS|MAX|MIN|AGGREGATE)\s*\(", re.I)
LABEL_RE = re.compile(r"(合计|小计|总计|累计|总数|平均|均值|总额|汇总|"
                      r"\btotal\b|\bsum\b|\bsubtotal\b|\baverage\b)", re.I)


def label_rows(sheet: dict) -> set[int]:
    """标签行（表头 / 小计 / 合计 / 平均）—— 列内统计必须先把它们剔掉。

    这是实测出来的第一大噪声源：46 个满分产物里 42 个存在同列样式混杂，
    根因就是「表头必然异于数据行、小计行必然异于明细行」。第一版没剔，
    结果在一张完全正常的表上报了「E 列 42 格中 41 格为公式，唯 E1 是常量」
    —— E1 是表头「金额」。

    两条启发式（都不需要知道任务要求）：
      · 含合计/小计/平均这类标签词的行
      · 首个非空行：若该行多为文本、而其下方同列多为数字或公式，判为表头
    """
    cols = columns_of(sheet)
    rows_with: dict[int, list[dict]] = defaultdict(list)
    for col in cols.values():
        for r, rec in col.items():
            rows_with[r].append(rec)
    out = {r for r, recs in rows_with.items()
           if any(LABEL_RE.search(rec["v"]) for rec in recs)}

    # 没有「合计」字样的总计行：整行只有聚合公式、其余列空着。
    # 实测 U161 的第 72 行 —— 加粗、=SUM(E4:E71)、A:D/F 全空，靠关键词认不出来。
    widths = [len(recs) for r, recs in rows_with.items()]
    typical = (sorted(widths)[len(widths) // 2] if widths else 0)
    for r, recs in rows_with.items():
        if len(recs) > max(1, typical // 2):
            continue                     # 非空格数接近数据行 → 是数据行，不是汇总行
        if any(AGG_RE.search(str(rec.get("f") or "")) for rec in recs):
            out.add(r)
        # 表顶元数据行：整行只有一个长文本格（其余是合并从属格）。
        # 实测 U037 的表顶是三层结构 —— A1:M1「假期统计报表」标题、
        # A2:M2 是「日期到:2026-02-24;部门:…」的筛选条件、A3 才是字段表头。
        # 只认首个非空行会把第 2 行的参数说明当成 A 列（工号列）的脏数据。
        if len(recs) == 1 and as_number(recs[0]["v"]) is None \
                and render_units(recs[0]["v"]) > 20:
            out.add(r)

    if rows_with:
        first = min(rows_with)
        head = rows_with[first]
        below = [rec for r, recs in rows_with.items() if r > first for rec in recs]
        if below:
            head_text = sum(1 for rec in head if rec["v"] and as_number(rec["v"]) is None)
            below_num = sum(1 for rec in below
                            if rec.get("f") or as_number(rec["v"]) is not None)
            if head_text >= max(1, len(head) // 2) and below_num >= len(below) // 2:
                out.add(first)
    return out


def data_cells(sheet: dict, col: dict[int, dict], skip: set[int]) -> list[tuple[int, dict]]:
    """列内的「数据格」：剔掉标签行，且值/公式至少有一个非空。

    AI 公式格（AI_ASK / AI_CLASSIFY / AI_EXTRACT 等）异步求值，中间态可能是
    "#ERROR"/"#N/A" 等字面串，形态与本列其余格差异极大，会误触发数值/类型类
    事实档规则。这里静默豁免 —— 让所有走 data_cells 的规则跳过它们。
    """
    return [(r, rec) for r, rec in sorted(col.items())
            if r not in skip and (rec["v"] or rec.get("f"))
            and not is_ai_formula_cell(rec)]


# ────────────────────────── 高置信度规则（逐条报坐标）──────────────────────────


def _addr_ref(addr: Any) -> str:
    """`'Sheet1'!C900` → `C900`。+formula-verify 的地址带 sheet 名前缀和单引号。"""
    return str(addr or "").rsplit("!", 1)[-1].strip().replace("$", "").strip("'")


def rule_formula_errors(wb: dict) -> list[tuple[str, str, list[str]]]:
    """R1 公式错误值。满分产物上几乎不出现，是最干净的信号。

    两路信号合并，都必须带坐标：
      · bad   —— 本地读回窗口里直接看到的错误值
      · extra —— +formula-verify 全表扫描报的、本地窗口没盖到的格

    为什么需要第二路：read_cells 有早停（连续一页全空即 break）和 MAX_ROWS 截断。
    实测造过这张表 —— 数据在 1–7 行、C900 有个 `=1/0`，read_cells 第二页全空就
    停了，C900 根本没进 cells，而 +formula-verify 的 `error_summary` 里明明白白
    写着 `'Sheet1'!C900`。旧版只取 `total_errors`，那一处就退化成
    「0 处（+formula-verify 扫全表报 1 处）」这种没有任何坐标的 ✗ 断言，还把结论
    抬成 CHECK_DEFECTS —— 调用方拿到「有错但不知道在哪」，只能忽略或瞎猜。

    AI 公式豁免：`samples[].formula` 是公式原文，直接拿 AI_FORMULA_RE 判；只出现在
    `locations[]` 里、没有对应 sample 的格回落到本地 cells 判定。实测当前后端并
    **不**把 AI 公式的异步中间态（value 是 "AI formula is calculating"，不是
    早先注释猜的 "#ERROR"）算进 total_errors，所以这层豁免是防后端行为变化的，
    不是当下的已知误报源。
    """
    out = []
    for s in wb["sheets"]:
        bad = [(ref, rec) for ref, rec in sorted(s["cells"].items())
               if any(e in rec["v"] for e in ERROR_VALUES)
               and not is_ai_formula_cell(rec)]
        local = {ref for ref, _ in bad}
        extra: list[tuple[str, str]] = []    # (错误类型, 坐标)
        unlocated = ai_skipped = 0
        try:
            d = envelope_data(call(
                "+formula-verify", sheet_id=s["id"],
                flags={"range": f"A1:{col_letter(s['cols'])}{s['rows']}",
                       # 默认 20：同一类错误超过 20 处时后面的拿不到坐标，
                       # 而没坐标的错误对调用方等于不可修。
                       "max_locations": 50},
                timeout=180, **wb["loc"]))
            # has_more / partial = 后端扫描撞上内部上限，剩余区域**没有检查过**。
            # 这不是「数据没读全」而是「检查没跑全」，交给 main 记进 unchecked。
            if d.get("has_more") or d.get("status") == "partial":
                wb.setdefault("scan_gaps", []).append(
                    f"{s['name']}: +formula-verify 扫描被后端上限截断，"
                    "未覆盖区域的公式错误这次没有检查")
            for kind, info in (d.get("error_summary") or {}).items():
                if not isinstance(info, dict):
                    continue
                ai_addrs = {_addr_ref(sm.get("address"))
                            for sm in (info.get("samples") or [])
                            if isinstance(sm, dict)
                            and AI_FORMULA_RE.search(str(sm.get("formula") or ""))}
                locs = [a for a in (info.get("locations") or []) if a]
                for addr in locs:
                    ref = _addr_ref(addr)
                    if ref in local:
                        continue            # 本地已带坐标报过，不重复
                    if ref in ai_addrs or is_ai_formula_cell(s["cells"].get(ref)):
                        ai_skipped += 1
                        continue
                    extra.append((str(kind), ref))
                # count 是全量，locations 受 max_locations 限制。
                unlocated += max(0, int(info.get("count") or 0) - len(locs))
        except LarkCliError:
            pass

        # 只在**拿得出坐标**时才断言。旧版判据是 `not bad and not total`，会放行
        # 「bad 空、total 非空」的组合并打出无坐标的 ✗。要么给得出坐标，要么不报。
        if not bad and not extra:
            continue
        # extra 排在前面：bad 那些格调用方自己读表就能看到，extra 只有这里能看到，
        # 而 truncate 的展示额度只有 MAX_LIST 条。
        lines = [f"{s['name']}!{ref}={kind}（本工具未读到该区域，坐标来自 +formula-verify）"
                 for kind, ref in extra]
        lines += [f"{s['name']}!{ref}={rec['v']}" for ref, rec in bad]
        shown, rest = truncate(lines)
        detail = f"{len(bad) + len(extra)} 处"
        if extra:
            detail += f"（其中 {len(extra)} 处在本工具未读到的区域）"
        if unlocated:
            detail += f"，另有 {unlocated} 处同类错误未给出坐标（--max-locations 可放宽）"
        if ai_skipped:
            detail += f"；已忽略 {ai_skipped} 处 AI 公式"
        out.append(("公式错误值", detail, shown + ([f"…另 {rest} 处"] if rest else [])))
    return out


# 「公式列里夹着常量」已删除。
# 语义上它做的是「整列公式占比检测」，没有识别表头边界，于是「一列几乎全是公式、
# 唯一的常量恰好在顶部」这种最典型的表头形态必然命中 —— 而那正是正常结构。
# 191 条编辑轨迹里该规则命中 41 次，逐条核验后真问题 0 条、误报 40 条、判不了 1 条
# （可判定样本误报率 100%）。典型命中：「4242 格中 4241 格为公式，唯一常量在 B1」
# 「2445 格中 2444 格为公式，唯一常量在 L1」—— B1/L1 都是字段名。
# 收紧阈值救不回来（真问题要求「公式块内部被写死」，而它查的是「列内占比」，
# 判据本身错了）。若将来要恢复，正确判据是：上下都是公式、当前格是常量，
# 即在连续公式块**内部**找断点，而不是按列统计占比。


# 「密集列中的空格」已从高置信度规则降级为 survey 里的样例。
# 实测 14 条命中 100% 误报，两类根因：
#   · 合并区从属格（已在 columns_of 里统一排掉）
#   · 源记录本身缺值 —— 血清肌酐没测、废品回收站没登记地址。
#     这类从表内无法区分「模型漏填」和「源数据本来就没有」，不该断言为缺陷。


# 「合并区未覆盖到最右列」已删除。
# 判据是拿全表数据最右列去要求每个局部合并都覆盖到那里，语义根本不成立：
# 真实表里合并有多种正当用途 —— 签字栏（A16:C16 编制人/负责人/主管副总）、
# 班组栏（B10:C10）、分组标题（A6:B6「法人联系方式」，C 列留空有层级语义）、
# 独立分区（U122 的 AB:AC「常州排名」与 D7:AA7 并列存在）。
# 实测 19 条命中里 17 条误报（89%），其中一个月报模板一张表就报 51 处。
# 收紧阈值救不回来，直接删。


def rule_number_text_mix(wb: dict) -> list[tuple[str, str, list[str]]]:
    """数值列里混着文本数字。

    典型来路：原表某列是文本型数字，模型把其中一部分转成了真数字（或反过来），
    剩下的没转。显示上两者几乎一样，但排序、求和、数字格式全会出问题，
    用户看到的是参差不齐的一列。

    只报「少数派 ≤3 格」的情况 —— 两边都占相当比例时更可能是两个合法分区
    （例如上半段是数值明细、下半段是文字说明），不该断言为缺陷。
    要求两侧显示值都能被解析成数字，避免把「数量列里写了'暂无'」这种正常
    占位当成类型不一致。
    """
    out = []
    for s in wb["sheets"]:
        skip = label_rows(s)
        for c, col in sorted(columns_of(s).items()):
            # 排除有公式的格：公式格的 value 是**求值结果**，真数字会以 JSON 数字
            # 返回（type=num），于是「一列文本型输入 + 一个派生/汇总公式」必然被
            # 判成类型不一致。实测 U095 的 B13（=B15+B16+B17+B22「企业增加值」）
            # 和 U161 的 E72（=SUM(E4:E71)）都是这么误报的。
            # 这条规则要查的是**输入类型**是否一致，公式的输出类型不该参与比较。
            cells = [(r, rec) for r, rec in data_cells(s, col, skip)
                     if not rec.get("f") and as_number(rec["v"]) is not None]
            if len(cells) < ISLAND_MIN_CELLS:
                continue
            nums = [r for r, rec in cells if rec.get("t") == "num"]
            texts = [r for r, rec in cells if rec.get("t") != "num"]
            if not nums or not texts:
                continue
            minor, label = ((texts, "文本") if len(texts) <= len(nums)
                            else (nums, "数值"))
            if len(minor) > ISLAND_MAX_MINOR:
                continue
            shown, rest = truncate([f"{s['name']}!{col_letter(c)}{r}" for r in sorted(minor)])
            out.append(("数值列里混着文本数字",
                        f"{col_letter(c)} 列 {len(cells)} 格里 {len(minor)} 格是{label}型，"
                        f"其余是{'数值' if label == '文本' else '文本'}型",
                        shown + ([f"…另 {rest} 格"] if rest else [])))
    return out


def rule_unit_in_numeric(wb: dict) -> list[tuple[str, str, list[str]]]:
    """本该是数值的列里，零星几格写成了带单位或表达式的文本。

    典型来路：抄写原始数据时没清理，于是一列 27 格里 25 格是 "3.5"，
    另外两格是 "2/kg"、"1+1"。它们看着像数值，却参与不了计算和排序，
    汇总时会被当成 0 或直接报错。

    dirty 的判据是「**含数字但解析不出纯数字**」，不是「非数字」——
    否则 "暂无" / "-" / "N/A" 这类合法缺失占位会被误报，它们不含数字。
    """
    out = []
    for s in wb["sheets"]:
        skip = label_rows(s)
        for c, col in sorted(columns_of(s).items()):
            cells = data_cells(s, col, skip)
            if len(cells) < ISLAND_MIN_CELLS:
                continue
            pure, dirty = [], []
            for r, rec in cells:
                v = rec["v"]
                if as_number(v) is not None:
                    pure.append(r)
                elif any(ch.isdigit() for ch in v):
                    dirty.append((r, v))
            if not dirty or len(dirty) > ISLAND_MAX_MINOR:
                continue
            # 排除标识符列：列名命中编码类关键词，或纯数字格全是「长整数」
            # （≥6 位且无小数点 —— 量值很少长这样，编码却几乎总是）。
            head = next((rec["v"] for r, rec in sorted(col.items())
                         if r in skip and rec["v"]), "")
            if ID_COL_RE.search(head):
                continue
            pure_vals = [rec["v"] for r, rec in cells if as_number(rec["v"]) is not None]
            if all("." not in v and len(v.lstrip("-")) >= 6 for v in pure_vals):
                continue
            # 用「纯数字格的绝对数量」而不是占比来判「大块」。
            # 「零星几格」的语义已经由 ISLAND_MAX_MINOR ≤ 3 表达，再叠一个 90%
            # 占比阈值是多余的，而且两者互相干扰：列越短，3 格脏就越容易把占比
            # 压到 90% 以下（实测 25 纯 + 2 脏 + 1 表头 = 0.893，差 0.007 漏判）。
            if len(pure) < ISLAND_MIN_CELLS:
                continue
            # 但要确认这确实是「数值列」：数字类内容（纯数字 + 脏格）得占绝大多数，
            # 否则可能是「20 格数字 + 3 格脏 + 50 行文字说明」这种非数值列。
            if (len(pure) + len(dirty)) / len(cells) < ISLAND_MAJOR_RATIO:
                continue
            shown, rest = truncate([f"{s['name']}!{col_letter(c)}{r}={v[:24]!r}"
                                    for r, v in sorted(dirty)])
            out.append(("数值列里混着带单位/表达式的格",
                        f"{col_letter(c)} 列 {len(cells)} 格中 {len(pure)} 格是纯数字，"
                        f"{len(dirty)} 格不是",
                        shown + ([f"…另 {rest} 格"] if rest else [])))
    return out


def rule_ragged_numbers(wb: dict) -> list[tuple[str, str, list[str]]]:
    """大块数值列用默认格式，且小数位数不统一 —— 用户看到的是参差不齐的一列。

    典型来路：原表是文本型数字，模型转成真数字后没设 number format；
    或者写入的是计算结果（=A/B 会产生一长串小数）。显示上就成了
        1234 / 1234.5 / 1234.56
    这三行在同一列里，右对齐但小数位不齐。

    为什么要「小数位不统一」这个限定：整列默认格式本身**判不了**——
    序号列、年份列、整数数量列、编号列本来就不需要数字格式。
    只有小数位数出现两种以上时，参差才是客观可见的，而且加一个统一的
    number format 就能修掉，修法明确。
    """
    out = []
    for s in wb["sheets"]:
        skip = label_rows(s)
        for c, col in sorted(columns_of(s).items()):
            nums = [(r, rec) for r, rec in data_cells(s, col, skip)
                    if rec.get("t") == "num" and as_number(rec["v"]) is not None]
            if len(nums) < RAGGED_MIN_CELLS:
                continue
            if any((rec.get("nf") or "").strip() not in ("", "General", "@")
                   for _, rec in nums):
                continue                      # 有人设过格式，交给它自己负责
            decimals = Counter(len(rec["v"].partition(".")[2]) for _, rec in nums)
            # 判据是**位数跨度**，不是「出现几种位数」。实测两个相反的例子：
            #   U032 绩效系数 1位/2位（跨度 1）—— 1.5 与 1.15 是档位本身的两种粒度，
            #        而且列是居中显示，小数点不会错位 → 核验判误报
            #   U073 面积计算 0~6 位（跨度 6）—— 1234 与 1234.567890 同列 → 判真问题
            # 跨度 ≥2 才谈参差；只差一位（1.5 / 1.15）属于数据自然精度。
            if max(decimals) - min(decimals) < RAGGED_MIN_SPREAD:
                continue
            samples = []
            seen: set[int] = set()
            for r, rec in nums:               # 每种位数取一个代表，便于直接看到参差
                d = len(rec["v"].partition(".")[2])
                if d not in seen:
                    seen.add(d)
                    samples.append(f"{s['name']}!{col_letter(c)}{r}={rec['v']}")
            shown, rest = truncate(samples)
            spread = "/".join(f"{d}位×{n}" for d, n in sorted(decimals.items()))
            out.append(("数值列未设格式且小数位参差",
                        f"{col_letter(c)} 列 {len(nums)} 格均为默认格式，小数位 {spread}",
                        shown + ([f"…另 {rest} 种"] if rest else [])))
    return out


def rule_percent_scale(wb: dict) -> list[tuple[str, str, list[str]]]:
    """R5 百分比量纲。显示值已渲染，>1000% 基本只能是「存了百分数又套了 % 格式」。"""
    out = []
    for s in wb["sheets"]:
        bad = []
        for ref, rec in sorted(s["cells"].items()):
            if is_ai_formula_cell(rec):
                continue
            m = PERCENT_RE.match(rec["v"])
            if not m:
                continue
            val = as_number(m.group(1))
            if val is not None and abs(val) > PERCENT_LIMIT:
                bad.append(f"{s['name']}!{ref} 显示 {rec['v']}（底层约 {val/100:g}）")
        if bad:
            shown, rest = truncate(bad)
            out.append(("百分比量纲可疑", f"{len(bad)} 处",
                        shown + ([f"…另 {rest} 处"] if rest else [])))
    return out


def rule_repeated_blocks(wb: dict) -> list[tuple[str, str, list[str]]]:
    """R6 同构区块横向对照 —— 本工具里证据最强的一条。

    多个同结构 sheet（12 个月份表、37 份成绩单、周报的各周）本身就是内部基准：
    「其他 11 块都一致，唯独这块不同」比「本列多数派 vs 少数派」有力得多，
    因为它不需要假设「多数即正确」，也不会把表头/小计的天然差异算成异常。
    """
    out = []
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for s in wb["sheets"]:
        cols = columns_of(s)
        header = tuple(sorted((c, rec["v"][:20]) for c, col in cols.items()
                              for r, rec in col.items() if r == min(col)))
        if header:
            groups[header].append(s)
    for header, sheets in groups.items():
        if len(sheets) < REPEAT_MIN_BLOCKS:
            continue
        # 每块取「哪些列含公式」作为结构指纹，找唯一的异类
        fp = {}
        for s in sheets:
            fp[s["name"]] = frozenset(c for c, col in columns_of(s).items()
                                      if any(rec.get("f") for rec in col.values()))
        tally = Counter(fp.values())
        if len(tally) < 2:
            continue
        major, n = tally.most_common(1)[0]
        if n < len(sheets) - ISLAND_MAX_MINOR:
            continue          # 没有明显的多数结构，不判
        odd = [name for name, f in fp.items() if f != major]
        lines = []
        for name in odd[:MAX_LIST]:
            miss = sorted(col_letter(c) for c in (major - fp[name]))
            extra = sorted(col_letter(c) for c in (fp[name] - major))
            lines.append(f"「{name}」" + (f" 缺公式列 {','.join(miss)}" if miss else "")
                         + (f" 多出公式列 {','.join(extra)}" if extra else ""))
        out.append(("同构区块中的异类",
                    f"{len(sheets)} 个同结构 sheet 里 {n} 个一致，{len(odd)} 个不同", lines))
    return out


# ── 两档：能确定性判定的才允许断言，需要语义才能判定的只报事实 ──────────
#
# 为什么要分档（191 条编辑轨迹 + 156 条单轮轨迹逐条核验的结果）
#   同一段扫描逻辑，输出成「断言」还是「事实」，误报率天差地别：
#     「✗ 合并区未覆盖到最右列」  —— 断言，83% 是错的（已删）
#     「A1:G1 止于 G，数据区到 H」—— 事实，永远不会错
#   检测逻辑本身是准的，错的是「这是缺陷」这个结论 —— 它需要语义才能下。
#   所以对需要语义的规则，只陈述观察到的结构，把判断交回调用方。
#
# 这么改的连带收益：「误报」这个概念在事实档里不存在了。调用方不必先判断
# 「工具说得对不对」再判断「要不要改」，只剩后一层。实测模型在前一层上会把
# 「原文件已有 / 不在任务范围」误当成「工具误报」，拆掉这一层正好绕开它。
ASSERT_RULES = (rule_formula_errors,)
FACT_RULES = (rule_number_text_mix, rule_unit_in_numeric, rule_ragged_numbers,
              rule_percent_scale, rule_repeated_blocks)

# 事实档每条附一句判断引导：说清「什么情况下它是问题、什么情况下是正常的」。
# 不给引导的话，事实和断言在调用方眼里没区别，等于白拆。
FACT_HINT = {
    "数值列里混着文本数字":
        "若整列是同一个量，文本型与数值型混排会让排序/求和/数字格式失效；"
        "若少数几格本就是占位或说明文字，则正常。",
    "数值列里混着带单位/表达式的格":
        "若整列应为纯数值，带单位或表达式的格无法参与计算；"
        "若该列本就是「规格/备注」这类文本列，则正常。",
    "数值列未设格式且小数位参差":
        "若这些格是同一个量，展示精度不一致用户看到的就是参差不齐；"
        "统一设置数字格式只改变展示、不改变底层值与公式。"
        "若各行本就是不同量纲（单价与总量同列），则正常。",
    "百分比量纲可疑":
        "显示值已渲染。>1000% 通常是「存了百分数又套了百分比格式」导致乘了两次 100；"
        "若业务上确实存在这么大的倍数，则正常。",
    "同构区块中的异类":
        "若这些区块是同一套结构的重复（多个月份/多个门店），异类那格大概率是漏改；"
        "若各区块本就承载不同内容，则正常。",
}
HIGH_RULES = ASSERT_RULES + FACT_RULES
# 排序权重：数字越小越先展示。断言档必须排在事实档之前。
RULE_ORDER = {"公式错误值": 0, "同构区块中的异类": 1,
              "数值列里混着带单位/表达式的格": 2, "数值列里混着文本数字": 3,
              "数值列未设格式且小数位参差": 4,
              "百分比量纲可疑": 5}
ASSERT_LABELS = {"公式错误值"}


# ────────────────────────── 低置信度：只报计数 ──────────────────────────


SURVEY_SAMPLES = 2      # 每类给几个样例坐标


def minority_group(vals: dict[int, dict], key: str) -> tuple[int, int] | None:
    """一列里按 key 分组，返回 (少数派格数, 少数派最小行号)。只有一组时返回 None。"""
    groups: dict[str, list[int]] = defaultdict(list)
    for r, rec in vals.items():
        groups[rec.get(key, "")].append(r)
    if len(groups) <= 1:
        return None
    minor = min(groups.values(), key=len)
    return len(minor), min(minor)


def gap_segments(rows: set[int], skip: set[int]) -> list[tuple[int, int]]:
    """一列里的空洞分段，返回 [(起始行, 段长)]。rows 必须非空。"""
    lo, hi = min(rows), max(rows)
    segs: list[tuple[int, int]] = []
    start = None
    for r in range(lo, hi + 1):
        if r not in rows and r not in skip:
            start = r if start is None else start
        elif start is not None:
            segs.append((start, r - start))
            start = None
    return segs


def survey_col(name: str, c: int, col: dict, skip: set[int],
               buckets: tuple[list, list, list]) -> tuple[int, int, int, int]:
    """统计一列，命中的样例塞进对应 bucket。

    buckets 是 (style_odd, fmt_odd, gap_odd) 三个样例桶。
    返回四个计数增量：(样式混杂, 数字格式多种, 有空洞, 空洞段数)。
    抽成独立函数是为了让 survey 的主循环和这里各自的 if/for 都不超过 3 层嵌套。
    """
    style_odd, fmt_odd, gap_odd = buckets
    vals = {r: rec for r, rec in col.items()
            if r not in skip and (rec["v"] or rec.get("f"))}
    n_style = n_fmt = 0
    if len(vals) >= 5:
        for key, bucket in (("s", style_odd), ("nf", fmt_odd)):
            hit = minority_group(vals, key)
            if hit is None:
                continue
            n_minor, first_row = hit
            if key == "s":
                n_style = 1
            else:
                n_fmt = 1
            bucket.append((n_minor, f"{name}!{col_letter(c)}{first_row}", len(vals)))

    rows = {r for r in col if r not in skip}
    if not rows:
        return n_style, n_fmt, 0, 0
    segs = gap_segments(rows, skip)
    if not segs:
        return n_style, n_fmt, 0, 0
    lo, hi = min(rows), max(rows)
    fill = len(rows) / (hi - lo + 1)
    seg_start, seg_len = min(segs, key=lambda x: x[1])
    gap_odd.append((seg_len, -round(fill, 3), f"{name}!{col_letter(c)}{seg_start}", fill))
    return n_style, n_fmt, 1, len(segs)


def survey(wb: dict) -> list[str]:
    """这几类在满分产物上几乎必然出现（42/46 有样式混杂、34/46 有空洞），
    列全部坐标会淹没真问题，所以只给计数。

    但纯计数「4 列 / 1 段」对模型没有可操作性 —— 它无法据此去核任何东西。
    所以每类附**最可疑的 1–2 个样例坐标**：按「少数派越少越可疑」排序
    （1 格异于其余 47 格，比 20 格异于 27 格可疑得多；单格空洞比连续 50 格空可疑）。
    既保住降噪，又给了可核查的入口。
    """
    style_cols = fmt_cols = gap_cols = gap_segs = 0
    style_odd: list[tuple[int, str, int]] = []   # (少数派格数, 坐标, 该列总格数)
    fmt_odd: list[tuple[int, str, int]] = []
    gap_odd: list[tuple[int, str, float]] = []   # (段长, 起始坐标, 该列填充率)

    for s in wb["sheets"]:
        skip = label_rows(s)                     # 表头/小计行不参与，它们天然不同
        for c, col in columns_of(s).items():
            d_style, d_fmt, d_gap, d_segs = survey_col(
                s["name"], c, col, skip, (style_odd, fmt_odd, gap_odd))
            style_cols += d_style
            fmt_cols += d_fmt
            gap_cols += d_gap
            gap_segs += d_segs

    def samples(bucket, fmt) -> str:
        if not bucket:
            return ""
        picks = sorted(bucket)[:SURVEY_SAMPLES]
        return "（最可疑：" + "；".join(fmt(*p) for p in picks) + "）"

    # 按计数决定要不要这一行。旧版是把三行都拼出来、再用
    # `not ln.endswith("0 列")` 过滤，只对前两行生效 —— 第三行结尾是「段」，
    # 0/0 时照样渲染；而说明行永远保留、counts 永不为空，于是干净表上必然剩下
    # 「列内空洞 0 列 / 0 段」+ 一句免责声明这两行纯噪声（实测确认）。
    # 顺带：前两行的过滤原本也只是「恰好」成立 —— 计数 >0 时 samples() 必然追加
    # 「（最可疑：…）」改掉了行尾，改一次文案就会失效。
    out = []
    if style_cols:
        out.append(f"同列样式混杂 {style_cols} 列" + samples(
            style_odd, lambda n, ref, tot: f"{ref} 等 {n} 格异于本列其余 {tot - n} 格"))
    if fmt_cols:
        out.append(f"同列数字格式多种 {fmt_cols} 列" + samples(
            fmt_odd, lambda n, ref, tot: f"{ref} 等 {n} 格格式异于其余 {tot - n} 格"))
    if gap_cols:
        out.append(f"列内空洞 {gap_cols} 列 / {gap_segs} 段" + samples(
            gap_odd, lambda n, _nf, ref, fill: f"{ref} 起 {n} 格空，该列填充率 {fill:.0%}"))
    if not out:
        return []          # 三类都是 0 → 整段不要，免得 render 打出一个空章节
    return out + ["（这三类在做对了的表上也普遍存在 —— 表头异于数据行、小计异于明细、"
                  "备注列稀疏都正常。只列最极端的样例供定位，不是断言它们有错。）"]


# ────────────────────────── 固定文本 ──────────────────────────

# 清单的取舍原则：只放「有确定性判据、做得完、做完能得出是/否」的动作。
# 得不出结论的项要么删掉，要么明说工具查不了 —— 否则调用方会做一遍无判据的
# 动作然后认为自己核过了。实测原第 2 条「原表有没有被动过？改完回读确认」
# 就是这样失效的：终态是自洽的，没有改前基准，回读了也判不出哪些格本不该长这样，
# 有 case 回读后把明显被覆盖的前几行判成了「正确」。所以第 2 条改成
# 「工具查不了 + 只核题面点名要保留的部分（这部分有判据）」。
CHECKLIST = """1. 汇总/合计/统计值/复杂业务计算 —— 必做，不是可选：
   先写下你采用的口径（含哪些行、单位、筛选阈值取 > 还是 >=、时区如何换算），
   再用 python 从明细独立算一遍，和表里的公式的「求值结果」逐项对账。
   如果结果对不上或者你写的 python 脚本报错了，看看是不是你的公式或脚本没有考虑到 Corner Case。
   如果单一公式无法覆盖整列，允许对特殊行单独写公式，不要把「无法解析」当理由。
   把对账结论写进交付说明。不要只看公式写得对不对，要看算出来的数对不对。
2. 原表保护：
   检查在编辑之前要保留的 sheet / 列 / 行 / 标题 / 单元格值是否还在、条数是否对得上，逐项回读断言。
   高危动作自己复查：
   - 「整列整块写入」前确认目标区域原本为空；
   - 「新增列」要落在原有效区右侧，不能覆盖已有字段；
   - 「追加」不能实现成重建或替换。
   - 「修改单元格值类型」，文本->数字/日期/百分比 等, Number Format 是否设置好？确保最终视觉效果与修改前相同？（使用 `+cells-get` 确认）
3. 题面点名的产出项：先把题面里点名的东西抄成一张清单
   （sheet 名称与数量、文件名、列名、指标项、必须包含的枚举值），
   再逐项对着产物打勾。是集合比对，不是凭印象扫一眼。
4. 处理范围：所有该处理的 sheet 和数据行都处理了吗？
   别只处理了第一个 sheet 或前几十行 —— 数据末尾、中间抽样都要看。
5. 条件标注（标红/高亮/筛选/去重）：既查漏标，也查误标。
6. 单位与口径：涉及单位换算（CM/MM、元/万元、秒/分钟）或特殊口径
   （是否含某类数据、是否排除某些行）的，逐行核对一次。"""


# ────────────────────────── 输出 ──────────────────────────


def hr(title: str, width: int = 46) -> str:
    return f"── {title} " + "─" * max(2, width - render_units(title))


def render(wb: dict, findings: list, counts: list[str],
           unread: list[str], unchecked: list[str], notices: list[str]) -> str:
    head = [f"交付前自检   {wb['loc'].get('url') or wb['loc'].get('spreadsheet_token')}",
            f"revision {wb['revision']}   " + "   ".join(
                f"{s['name']} ({s['rows']}×{s['cols']})" for s in wb["sheets"][:6]),
            # revision 约束。实测 191 条编辑轨迹里 39% 的 case 最后一次自检之后
            # 还在写表 —— 交付的产物从没被本工具看过，而调用方以为自己检查过了。
            # revision 本来就打印在上一行，只是没有约束力，补一句把它变成约束。
            f"⚠ 以上结论对应 revision {wb['revision']}。此后任何写入都会使它失效 —— "
            f"必须在最后一次写操作之后重跑本工具，再交付。"]
    out = list(head) + [""]

    asserts = [f for f in findings if f[0] in ASSERT_LABELS]
    facts = [f for f in findings if f[0] not in ASSERT_LABELS]

    if asserts:
        out.append(hr("确定性错误（工具能定性，必须处理）"))
        for label, detail, lines in asserts:
            out.append(f"✗ {label:<22} {detail}".rstrip())
            out.extend(f"    {ln}" for ln in lines)
        out.append("  → 在题面要求改的范围内：修根因，别用 IFERROR 之类把错误藏起来。")
        out.append("    范围外（题面没点到、且是原文件自带的）：不要改动，"
                   "但必须在交付说明里逐条列出，不能静默忽略。")
        out.append("")
    if facts:
        # 只陈述观察到的结构，不断言它是缺陷 —— 「这算不算问题」需要题面语义，
        # 工具没有那个信息。事实无法误报，判断权交回调用方。
        out.append(hr("结构特征（工具只能陈述事实，是否为问题由你判断）"))
        for label, detail, lines in facts:
            out.append(f"· {detail}".rstrip())
            out.extend(f"    {ln}" for ln in lines)
            if FACT_HINT.get(label):
                out.append(f"  → {FACT_HINT[label]}")
        out.append("  判为正常的，在交付说明里写一句理由；判为问题的，修完重跑本工具。")
        out.append("")
    if counts:
        out.append(hr("仅计数（正常表也常见，不逐条列）"))
        out.extend(f"! {c}" if i == 0 else f"  {c}" for i, c in enumerate(counts))
        out.append("")
    # 三类「没盖到」分开列：成因不同，调用方该做的动作也不同。
    #   unread    数据没读到 → 该区域自己抽样回读
    #   unchecked 数据读到了、检查没跑成 → 重跑或人工核，回读没有意义
    #   notices   都做了、只是没全显示 → 不需要任何动作，放宽参数即可
    if unread:
        out.append(hr("读取不完整"))
        out.extend(f"! {c}" for c in unread)
        out.append("  → 本工具读不到的部分它就是查不了，不要把「没报问题」当成「那部分没问题」。"
                   "该区域你自己抽样回读：末尾、中间各看几行。")
        out.append("")
    if unchecked:
        out.append(hr("检查未完成"))
        out.extend(f"! {c}" for c in unchecked)
        out.append("  → 数据读到了，但这些检查没跑成 —— 对应的问题类型这次等于没查。"
                   "重跑一次；仍失败就按自查清单人工核这几类。")
        out.append("")
    if notices:
        out.append(hr("提示（不影响结论）"))
        out.extend(f"  {c}" for c in notices)
        out.append("")

    out.append(hr("交付前自查（逐条回答，不要跳过）"))
    out.append(CHECKLIST)

    # 三态结论。语义收紧：只有**确定性错误**才算 DEFECTS，事实档不参与定性。
    # PASS 的措辞必须不含任何令人安心的成分 —— 实测有 case 拿到 PASS 后原话
    # 「self-check passed, let me just deliver it」，取消了它上一步已经决定要做的
    # 回读，而那张表的原有数据实际已被整体覆盖。旧措辞虽然也写了「无法判定」，
    # 但结论句先说了「没发现问题」，调用方只读了前半句。
    #
    # 分支顺序：asserts 必须排在 unread/unchecked 之前判。旧版是 `if incomplete:
    # ... elif asserts:`，于是「有确定性错误」这个最强信号会被「没读全」吃掉 ——
    # 一张 5101 行的表（MAX_ROWS 截断 → unread 非空）即使扫出公式错误，结论句也
    # 只说「部分数据没读全」，而 L861-864 已经论证了调用方只读结论句前半句。
    # 「没盖到」的信息不丢，改成挂在 DEFECTS 后面一起说。
    tail = ""
    if facts:
        tail = f" 另有「结构特征」{len(facts)} 条需你逐条判断，判完才算过。"

    blind = ([f"部分数据没读全（{len(unread)} 处）"] if unread else []) + \
            ([f"部分检查没跑成（{len(unchecked)} 处）"] if unchecked else [])
    blind_txt = "、".join(blind)

    if asserts:
        out.append(f"CHECK_DEFECTS：{len(asserts)} 类确定性错误，先处理再交付；"
                   "自查清单同样要过。"
                   + (f" 同时{blind_txt}，见上面对应小节 —— "
                      "那些区域没报问题不等于没问题。" if blind else "")
                   + tail)
    elif blind:
        out.append(f"CHECK_INCOMPLETE：{blind_txt}，上面的结论不完整，"
                   "不能据此认为产物没问题。" + tail)
    else:
        out.append("CHECK_PASS：规则扫描没有命中确定性错误。"
                   "这**不是**产物没问题的证明 —— 原表是否被改坏、计算口径是否正确、"
                   "题面要点是否覆盖，本工具都没有检查、也无法检查。"
                   "交付前必须自己走完上面的自查清单，"
                   "第 1、3 条要有实际的复算和逐项打勾动作，不能因为本工具通过就跳过。"
                   + tail)
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="交付前自检（无基准、不落盘）")
    ap.add_argument("target", help="表格 URL 或 spreadsheet token")
    ap.add_argument("--max-findings", type=int, default=MAX_FINDINGS,
                    help=f"高置信度发现的条数上限（默认 {MAX_FINDINGS}）")
    args = ap.parse_args()

    try:
        wb, unread = read_workbook(args.target)
    except LarkCliError as exc:
        # 注意 print 到 stdout：skill 文档教模型「只读 stdout」，
        # 若把这段落在 stderr，模型看不到「自检没跑成」，会当成「没问题」。
        print(f"交付前自检无法完成：{exc}\n\n"
              f"{hr('交付前自查（工具不可用，请逐条自己核）')}\n{CHECKLIST}\n\n"
              "CHECK_INCOMPLETE：读表失败，本次没有任何规则结论，"
              "不能据此认为产物没问题。请重试一次；仍失败就按上面的清单人工核并在交付说明写明。")
        print(f"[stderr] {exc}", file=sys.stderr)
        return 2

    findings: list = []
    unchecked: list[str] = []               # 数据读到了、检查没跑成
    notices: list[str] = []                 # 都做了、只是没全显示
    for rule in HIGH_RULES:
        try:
            findings.extend(rule(wb))
        except Exception as exc:            # 单条规则崩掉不该拖垮整次自检
            unchecked.append(f"规则 {rule.__name__} 执行失败：{str(exc)[:80]}")
    findings.sort(key=lambda f: RULE_ORDER.get(f[0], 99))
    # 规则内部记下的「扫描被截断」——数据读到了，是检查没跑全。
    unchecked.extend(wb.get("scan_gaps") or [])
    if len(findings) > args.max_findings:
        rest = len(findings) - args.max_findings
        findings = findings[:args.max_findings]
        # 展示截断不参与三态：数据读了、规则跑了，只是没全列出来。
        # 旧版把它塞进 incomplete，效果是「发现越多，DEFECTS 结论越会消失」。
        notices.append(f"另有 {rest} 类低优先发现未展示（--max-findings 可放宽）")

    # survey / render 也要兜底：整个工具的价值就是往 stdout 写出结论，
    # 这两步一旦抛异常，traceback 只到 stderr，模型读到的 stdout 是空的。
    try:
        counts = survey(wb)
    except Exception as exc:
        counts = []
        unchecked.append(f"低置信度普查（survey）执行失败：{str(exc)[:80]}")
    try:
        print(render(wb, findings, counts, unread, unchecked, notices))
    except Exception as exc:
        print(f"交付前自检的结果渲染失败：{str(exc)[:200]}\n\n"
              f"{hr('交付前自查（逐条回答，不要跳过）')}\n{CHECKLIST}\n\n"
              "CHECK_INCOMPLETE：规则跑完了但结论没能渲染出来，本次没有可用的规则结论，"
              "不能据此认为产物没问题。请重跑一次。")
        print(f"[stderr] render failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
