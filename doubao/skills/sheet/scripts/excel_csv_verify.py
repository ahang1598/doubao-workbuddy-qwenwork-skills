#!/usr/bin/env python3
"""
excel_csv_verify.py
本地 CSV 产物的交付门禁。CSV 没有公式、没有子表、没有样式，excel_formula_verify.py
那套判据一条都套不上，所以单独走这个入口。

判的是 CSV 真正会翻车的地方：编码与 BOM、能不能被原样重新解析、表头与列数、
逐行字段数、行数、长数字被转成科学计数或前导零被吃掉，以及用户点名的检查点。

退出码与 excel_formula_verify.py 同一套分档：
  0 = 确定性判据全过；
  3 = 确定性错误（读不出 / 解析失败 / 字段数不齐 / 表头或行数不符 / 检查点不符 /
      与基准比对失败），必须修完重跑；
  4 = 诊断信号（编码易乱码、疑似前导零丢失或科学计数、检查点判不了），
      按提示处置并写进交付说明，不反复重跑。
"""
from __future__ import annotations

import argparse
import codecs
import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from _checkpoints import (col_index, emit_checkpoint_hint,
                          emit_checkpoint_skip_hint, load_checkpoints,
                          verify_checkpoints)

MAX_LISTED = 20

# UTF-32 的 BOM 前两字节与 UTF-16 相同，必须先试更长的那个，否则会误判成 UTF-16。
BOM_CODECS = [
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
]

SCIENTIFIC = re.compile(r"^-?\d+(\.\d+)?[Ee][+-]?\d+$")
LEADING_ZERO = re.compile(r"^0\d+$")
PLAIN_DIGITS = re.compile(r"^\d+$")


def detect_encoding(raw: bytes) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """返回 (codec, bom 名称, 失败原因)。没有 BOM 时按 utf-8 → gb18030 试。"""
    for bom, name in BOM_CODECS:
        if raw.startswith(bom):
            return name, name, None
    for name in ("utf-8", "gb18030"):
        try:
            raw.decode(name)
        except UnicodeDecodeError:
            continue
        return name, None, None
    return None, None, "既不是 UTF-8 也不是 GB18030，无法确定编码"


def read_matrix(path: Path, delimiter: str) -> Dict[str, Any]:
    """读成二维矩阵。失败时 status=invalid_input，由调用方按退出码 3 处置。"""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return {"status": "invalid_input", "error": f"读不到文件：{exc}"}
    if not raw.strip():
        return {"status": "invalid_input", "error": "文件是空的，没有可校验的内容"}

    codec, bom, why = detect_encoding(raw)
    if codec is None:
        return {"status": "invalid_input", "error": why}
    text = raw.decode(codec)

    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
    except csv.Error as exc:
        return {"status": "invalid_input", "error": f"CSV 解析失败：{exc}"}
    rows = [r for r in rows if r != []]
    if not rows:
        return {"status": "invalid_input", "error": "解析后一行都没有"}
    return {"status": "ok", "rows": rows, "codec": codec, "bom": bom,
            "has_non_ascii": any(ord(ch) > 127 for ch in text)}


def check_encoding(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """编码本身能解码不代表在 Excel 里打得开。这两条都只降级，不阻断。"""
    notes: List[str] = []
    codec, bom = parsed["codec"], parsed["bom"]
    if codec == "gb18030":
        notes.append("文件是 GB18030 而不是 UTF-8，换平台或换工具读容易乱码；"
                     "建议改存 UTF-8 BOM（Python 里用 encoding='utf-8-sig'）")
    elif codec == "utf-8" and parsed["has_non_ascii"]:
        notes.append("UTF-8 但没有 BOM，含非 ASCII 字符时 Excel 双击打开会乱码；"
                     "建议改存 UTF-8 BOM（Python 里用 encoding='utf-8-sig'）")
    return {"status": "issues_found" if notes else "clean",
            "codec": codec, "bom": bom, "notes": notes}


def check_structure(rows: List[List[str]], expect_rows: Optional[int],
                    expect_headers: Optional[List[str]]) -> Dict[str, Any]:
    """表头、列数、逐行字段数、行数。这一组全是确定性判据。"""
    header = rows[0]
    width = len(header)
    problems: List[str] = []

    ragged = [(i + 1, len(r)) for i, r in enumerate(rows) if len(r) != width]
    if ragged:
        shown = "、".join(f"第 {n} 行 {c} 个" for n, c in ragged[:MAX_LISTED])
        problems.append(f"{len(ragged)} 行的字段数与表头（{width} 个）不一致：{shown}。"
                        "多半是值里含逗号 / 换行没被引号包起来")

    blank_cols = [i + 1 for i, h in enumerate(header) if not h.strip()]
    if expect_headers is not None and header != expect_headers:
        problems.append(f"表头与 --expect-headers 不一致：实际 {header}，期望 {expect_headers}")

    data_rows = len(rows) - 1
    if expect_rows is not None and data_rows != expect_rows:
        problems.append(f"数据行数 {data_rows}，期望 {expect_rows}")

    return {"status": "issues_found" if problems else "clean",
            "columns": width, "data_rows": data_rows, "header": header,
            "blank_header_cols": blank_cols, "problems": problems}


def check_value_risks(rows: List[List[str]]) -> Dict[str, Any]:
    """长数字被转成科学计数、前导零在同一列里时有时无——都是写出去时被吃掉的痕迹。"""
    header = rows[0]
    body = rows[1:]
    scientific: List[str] = []
    mixed_zero: List[str] = []

    for c in range(len(header)):
        column = [r[c] for r in body if c < len(r)]
        sci = [(i, v) for i, v in enumerate(column) if SCIENTIFIC.match(v.strip())]
        if sci:
            name = header[c] or f"第 {c + 1} 列"
            scientific.append(f"「{name}」{len(sci)} 个值形如 {sci[0][1].strip()}"
                              f"（首个在第 {sci[0][0] + 2} 行）")
        zeros = [v for v in column if LEADING_ZERO.match(v.strip())]
        plain = [v for v in column if PLAIN_DIGITS.match(v.strip())
                 and not LEADING_ZERO.match(v.strip())]
        if zeros and plain:
            # 定宽的零填充编号列里，短于该宽度的纯数字就是被当成数字后掉了前导零。
            pad_width = max(len(v.strip()) for v in zeros)
            stripped = [v for v in plain if len(v.strip()) < pad_width]
            if stripped:
                name = header[c] or f"第 {c + 1} 列"
                mixed_zero.append(f"「{name}」同列既有 {zeros[0].strip()}（{pad_width} 位定宽），"
                                  f"也有 {stripped[0].strip()} 这种更短的纯数字，"
                                  f"共 {len(stripped)} 个疑似掉了前导零")

    notes = scientific + mixed_zero
    return {"status": "issues_found" if notes else "clean",
            "scientific": scientific, "mixed_leading_zero": mixed_zero}


def compare_baseline(rows: List[List[str]], base_rows: List[List[str]]) -> Dict[str, Any]:
    """与改前快照比。只比不依赖行序的三件事，免得排序类任务被误判。"""
    problems: List[str] = []
    header, base_header = rows[0], base_rows[0]
    if header != base_header:
        problems.append(f"表头与基准不一致：实际 {header}，基准 {base_header}")

    data, base_data = len(rows) - 1, len(base_rows) - 1
    if data < base_data:
        problems.append(f"数据行数从 {base_data} 减到 {data}；"
                        "用户没要求删行就是丢数据，要求删了就把基准换成删后的快照")

    # 行数没少时才比前导零：真删了行，计数本来就会跟着降，上面那条已经在报了。
    if data >= base_data:
        def zero_count(matrix: List[List[str]], col: int) -> int:
            return sum(1 for r in matrix[1:]
                       if col < len(r) and LEADING_ZERO.match(r[col].strip()))

        lost: List[str] = []
        for c in range(min(len(header), len(base_header))):
            before, after = zero_count(base_rows, c), zero_count(rows, c)
            if after < before:
                lost.append("「{}」{} → {}".format(
                    base_header[c] or "第 {} 列".format(c + 1), before, after))
        if lost:
            problems.append("带前导零的值比基准少了：" + "、".join(lost[:MAX_LISTED])
                            + "。写出去时被当成数字了，把该列改成文本再重写")

    return {"status": "differences_found" if problems else "clean",
            "blocking": bool(problems), "problems": problems}


def run_checkpoints(rows: List[List[str]], sheet: str, items: List[dict]) -> Dict[str, Any]:
    """CSV 当成一张名为文件名的表。公式类与子表类条目在这里没有判据，标 invalid。"""
    extra: List[dict] = []
    usable: List[dict] = []
    for item in items:
        if "sheets" in item:
            extra.append({"result": "invalid", "ref": "子表集合",
                          "message": "CSV 只有一张表，没有子表可校验；这条改到 xlsx 或在线表上判"})
            continue
        if item.get("formula") or item.get("all_formula"):
            extra.append({"result": "invalid", "ref": str(item.get("cell") or item.get("range")),
                          "message": "CSV 存不了公式，公式覆盖判不了；要判公式就别交 CSV"})
            continue
        if "!" not in str(item.get("cell") or item.get("range") or ""):
            item = dict(item)
            key = "cell" if "cell" in item else "range"
            item[key] = "{}!{}".format(sheet, item[key])
        usable.append(item)

    def lookup(_sheet: str, coord: str) -> Tuple[Any, str]:
        match = re.match(r"^([A-Za-z]+)(\d+)$", coord)
        if not match:
            return None, ""
        col = col_index(match.group(1)) - 1
        row = int(match.group(2)) - 1
        if row < 0 or row >= len(rows) or col < 0 or col >= len(rows[row]):
            return None, ""
        return rows[row][col], ""

    result = verify_checkpoints(usable, lookup, [sheet]) if usable else {
        "status": "skipped", "total": 0, "passed": 0, "failed": 0,
        "skipped": 0, "details": []}
    if extra:
        result = dict(result)
        result["details"] = list(result.get("details") or []) + extra
        result["total"] = result.get("total", 0) + len(extra)
        result["failed"] = result.get("failed", 0) + len(extra)
        result["status"] = "failed"
    return result


INVALID_INPUT_HINT = """\
[input] CSV 读不出来：{error}
一条判据都没跑，这不是「没发现问题」，是没有判据。
退出码 3 是确定性错误：确认路径与分隔符（非逗号用 --delimiter），修完重跑。"""

STRUCTURE_HINT = """\
[structure] {count} 项确定性错误：
{lines}
表头 / 列数 / 行数是 CSV 唯一的结构契约，不符就是产物做错了。改完重跑本命令。"""

BASELINE_HINT = """\
[baseline] 与改前快照比出 {count} 处差异：
{lines}
源数据默认必须保留。范围外被改写的恢复原值，被当成数字的列改回文本，改完重跑。"""

ENCODING_HINT = """\
[encoding] {count} 条编码提示：
{lines}
退出码 4 不是让你反复重跑：改存法就改，改不了就把「编码 + 打开方式」写进交付说明。"""

VALUE_RISK_HINT = """\
[values] {count} 条取值嫌疑：
{lines}
这类值多半在写出时被当成数字处理过。确属原始数据就在交付说明写明，
否则把该列改成文本再重写，改完重跑。"""


def emit(hint: str, items: List[str], **kw) -> None:
    print(hint.format(count=len(items),
                      lines="\n".join("  - " + s for s in items[:MAX_LISTED]), **kw),
          file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="excel_csv_verify.py",
        description="本地 CSV 产物的交付门禁：编码、结构、取值嫌疑与检查点。")
    ap.add_argument("csv_file", help="待校验的 .csv 产物")
    ap.add_argument("--baseline", help="改前快照 CSV；编辑已有文件时给它")
    ap.add_argument("--delimiter", default=",", help="字段分隔符，默认逗号")
    ap.add_argument("--expect-rows", type=int, help="期望的数据行数（不含表头）")
    ap.add_argument("--expect-headers", help="期望表头，JSON 数组，逐字比对")
    ap.add_argument("--checkpoints", help="检查点 JSON，协议同 excel_formula_verify.py")
    args = ap.parse_args()

    parsed = read_matrix(Path(args.csv_file), args.delimiter)
    if parsed["status"] != "ok":
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        print(INVALID_INPUT_HINT.format(error=parsed["error"]), file=sys.stderr)
        return 3

    expect_headers = None
    if args.expect_headers:
        try:
            expect_headers = json.loads(args.expect_headers)
        except ValueError as exc:
            print(json.dumps({"status": "invalid_input",
                              "error": f"--expect-headers 不是合法 JSON：{exc}"},
                             ensure_ascii=False, indent=2))
            return 3
        if not isinstance(expect_headers, list) or \
                not all(isinstance(h, str) for h in expect_headers):
            print(json.dumps({"status": "invalid_input",
                              "error": "--expect-headers 要是字符串数组"},
                             ensure_ascii=False, indent=2))
            return 3

    rows = parsed["rows"]
    result: Dict[str, Any] = {
        "status": "success",
        "encoding": check_encoding(parsed),
        "structure": check_structure(rows, args.expect_rows, expect_headers),
        "value_risks": check_value_risks(rows),
    }

    if args.baseline:
        base = read_matrix(Path(args.baseline), args.delimiter)
        if base["status"] != "ok":
            result["baseline"] = {"status": "skipped", "blocking": True,
                                  "problems": [f"基准读不出来：{base['error']}"]}
        else:
            result["baseline"] = compare_baseline(rows, base["rows"])

    checkpoint_error = None
    if args.checkpoints:
        items, checkpoint_error = load_checkpoints(args.checkpoints)
        if checkpoint_error:
            result["checkpoints"] = {"status": "invalid", "reason": checkpoint_error}
        else:
            stem = Path(args.csv_file).stem
            result["checkpoints"] = run_checkpoints(
                rows, stem if "!" not in stem else "CSV", items)

    structure = result["structure"]
    baseline = result.get("baseline") or {}
    checkpoints = result.get("checkpoints") or {}

    if structure["problems"]:
        emit(STRUCTURE_HINT, structure["problems"])
    if baseline.get("problems"):
        emit(BASELINE_HINT, baseline["problems"])
    if result["encoding"]["notes"]:
        emit(ENCODING_HINT, result["encoding"]["notes"])
    risks = result["value_risks"]
    value_notes = risks["scientific"] + risks["mixed_leading_zero"]
    if value_notes:
        emit(VALUE_RISK_HINT, value_notes)
    if checkpoints.get("status") == "invalid":
        print(f"[checkpoints] {checkpoints.get('reason')}", file=sys.stderr)
    has_checkpoint_break = (checkpoints.get("status") == "invalid"
                            or emit_checkpoint_hint(checkpoints, lambda t: print(t, file=sys.stderr)))
    has_checkpoint_skip = emit_checkpoint_skip_hint(
        checkpoints, lambda t: print(t, file=sys.stderr))

    blocking = bool(structure["problems"]) or bool(baseline.get("blocking")) \
        or has_checkpoint_break
    degraded = bool(result["encoding"]["notes"]) or bool(value_notes) \
        or has_checkpoint_skip or bool(structure["blank_header_cols"])
    if structure["blank_header_cols"]:
        print("[structure] 表头有空列名：第 "
              + "、".join(str(i) for i in structure["blank_header_cols"][:MAX_LISTED])
              + " 列。下游按列名取数会错位；确属无名索引列就在交付说明写明。",
              file=sys.stderr)

    result["status"] = "errors_found" if blocking else (
        "issues_found" if degraded else "success")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 3 if blocking else (4 if degraded else 0)


if __name__ == "__main__":
    raise SystemExit(main())
