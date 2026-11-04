#!/usr/bin/env python3
"""用独立 LibreOffice profile 转换文件格式（xlsx → pdf / png / xlsx / csv 等）。

直接写 `soffice --convert-to` 会落到共享的默认 profile：一次被杀或初始化中断留下的
锁与半成品目录，会让之后每次启动都失败。本脚本每次新建临时 profile，转换结束即删，
超时回收整棵进程树，调用方无需 pkill。

png 只渲染一个子表的第一页，csv 只导出一个子表：默认第一个可见子表。`--sheet` 指定别的子表
（仅 .xlsx / .xlsm 输入），脚本在临时副本里隐藏其余子表再转换，原文件不动，产物名带上子表名
（<原名>__<子表名>.<格式>；子表名含文件名非法字符时替换为 _ 并追加原名哈希前 6 位），逐个
子表转换不会互相覆盖，同一子表重导出名字不变。要看全貌用 pdf。

用法：
  python3 excel_lo_convert.py <输入文件> <目标格式> [--outdir 目录] [--timeout 秒] [--sheet 子表名]
  python3 excel_lo_convert.py report.xlsx pdf --outdir ./preview
  python3 excel_lo_convert.py report.xlsx png --sheet 图表 --outdir ./preview
  python3 excel_lo_convert.py report.xlsx csv --sheet 明细 --outdir ./out

stdout 输出一行 JSON。退出码：
  0 = 成功，output 为产物路径；
  3 = 转换失败（invalid_input / lo_start_failed / timeout / convert_failed），stderr 给处置；
  4 = 本机没有 LibreOffice（skipped_no_libreoffice），转换不可用。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path
from typing import List, Optional
from xml.parsers import expat

# 只依赖 LibreOffice 运行时模块，不依赖 openpyxl：转换本身用不到它。
from excel_lo_runtime import (
    LO_START_FAILURE_MARKERS,
    get_soffice_env,
    profile_arg,
    run_managed_process,
    soffice_detail,
    sweep_stale_profiles,
)

PROFILE_PREFIX = "excel-lo-convert-"
SHEET_COPY_PREFIX = "excel-lo-sheet-"

SHEET_FORMATS = ("png", "csv")
WORKBOOK_PART = "xl/workbook.xml"

# XML parser 定位真实元素，按原始字节补丁；属性值里的 '>' 不结束标签。
_ATTRS = r"""(?:"[^"]*"|'[^']*'|[^>"'])*"""
_OPEN_TAG_RE = re.compile((r"<" + _ATTRS + r">").encode("ascii"))
_XML_ATTR_RE = re.compile(r"""\s+([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
# 产物文件名里不能出现的字符
_UNSAFE_NAME_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _workbook_elements(workbook_xml: str):
    """按命名空间和层级识别元素，支持任意合法 XML 前缀并保留原始字节。"""
    raw = workbook_xml.encode("utf-8")
    parser = expat.ParserCreate(namespace_separator="}")
    elements = {name: [] for name in ("workbook", "sheets", "sheet", "bookViews", "workbookView")}
    stack = []
    ns = ""

    def start(name, attrs):
        nonlocal ns
        if not stack:
            uri, _, local = name.rpartition("}")
            if local != "workbook" or uri not in (
                    "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                    "http://purl.oclc.org/ooxml/spreadsheetml/main"):
                raise ValueError("workbook.xml has an unsupported root namespace")
            ns = uri + "}"
        local = name[len(ns):] if name.startswith(ns) else ""
        parents = {"workbook": [], "sheets": [ns + "workbook"], "bookViews": [ns + "workbook"],
                   "sheet": [ns + "workbook", ns + "sheets"],
                   "workbookView": [ns + "workbook", ns + "bookViews"]}
        if local in parents and stack == parents[local]:
            begin = parser.CurrentByteIndex
            match = _OPEN_TAG_RE.match(raw, begin)
            if match is None:
                raise ValueError("cannot locate workbook element opening tag")
            elements[local].append({"start": begin, "end": match.end(),
                                    "tag": match.group().decode("utf-8"), "attrs": attrs})
        stack.append(name)

    def end(_name):
        stack.pop()

    def reject_doctype(*_args):
        raise ValueError("workbook.xml must not contain a DTD")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = reject_doctype
    try:
        parser.Parse(raw, True)
    except expat.ExpatError as exc:
        raise ValueError("invalid workbook.xml: {}".format(exc)) from exc
    return raw, elements


def _without_attrs(tag: str, names) -> str:
    return _XML_ATTR_RE.sub(lambda m: "" if m.group(1) in names else m.group(0), tag)


def _sheet_names(workbook_xml: str) -> List[str]:
    _raw, elements = _workbook_elements(workbook_xml)
    return [element["attrs"].get("name", "") for element in elements["sheet"]]


def _sheet_index(workbook_xml: str, sheet: str) -> int:
    """子表在工作簿里的位置（0 起，含隐藏子表）；找不到时抛 ValueError。"""
    names = _sheet_names(workbook_xml)
    if sheet not in names:
        raise ValueError(f"sheet not found: {sheet}; available: {', '.join(names)}")
    return names.index(sheet)


def _show_only_sheet(workbook_xml: str, sheet: str) -> str:
    """把 sheet 设为唯一可见且活动的子表；找不到时抛 ValueError。"""
    raw, elements = _workbook_elements(workbook_xml)
    names = [element["attrs"].get("name", "") for element in elements["sheet"]]
    if sheet not in names:
        raise ValueError(f"sheet not found: {sheet}; available: {', '.join(names)}")
    target = names.index(sheet)

    def set_state(tag: str, state: str) -> str:
        tag = _without_attrs(tag, {"state"})
        if state == "visible":
            return tag
        end = -2 if tag.endswith("/>") else -1
        return f'{tag[:end].rstrip()} state="{state}"{tag[end:]}'

    replacements = []
    for i, element in enumerate(elements["sheet"]):
        tag = element["tag"]
        if i == target:
            updated = set_state(tag, "visible")
        elif element["attrs"].get("state") == "veryHidden":
            updated = tag
        else:
            updated = set_state(tag, "hidden")
        replacements.append((element["start"], element["end"], updated))

    if elements["workbookView"]:
        view = elements["workbookView"][0]
        tag = _without_attrs(view["tag"], {"activeTab", "firstSheet"})
        end = -2 if tag.endswith("/>") else -1
        updated = f'{tag[:end].rstrip()} activeTab="{target}" firstSheet="{target}"{tag[end:]}'
        replacements.append((view["start"], view["end"], updated))
    else:
        # 补建视图使用其父节点的前缀，不能依赖只在 sheets 上声明的命名空间。
        parent = (elements["bookViews"] or elements["workbook"])[0]
        qualified = re.match(r"<([^\s/>]+)", parent["tag"]).group(1)
        prefix = qualified.rsplit(":", 1)[0] + ":" if ":" in qualified else ""
        view = f'<{prefix}workbookView activeTab="{target}" firstSheet="{target}"/>'
        if elements["bookViews"]:
            if parent["tag"].endswith("/>"):
                updated = parent["tag"][:-2] + ">" + view + f"</{qualified}>"
                replacements.append((parent["start"], parent["end"], updated))
            else:
                replacements.append((parent["end"], parent["end"], view))
        else:
            at = elements["sheets"][0]["start"]
            replacements.append((at, at, f'<{prefix}bookViews>{view}</{prefix}bookViews>'))
    for begin, end, text in sorted(replacements, reverse=True):
        raw = raw[:begin] + text.encode("utf-8") + raw[end:]
    return raw.decode("utf-8")


def _first_visible_index(workbook_xml: str) -> int:
    _raw, elements = _workbook_elements(workbook_xml)
    for i, element in enumerate(elements["sheet"]):
        if element["attrs"].get("state", "visible") in ("", "visible"):
            return i
    return 0


def _read_workbook_xml(src: Path) -> str:
    with zipfile.ZipFile(src) as zin:
        if WORKBOOK_PART not in zin.namelist():
            raise ValueError(f"{WORKBOOK_PART} not found in the package")
        return zin.read(WORKBOOK_PART).decode("utf-8")


def _single_sheet_copy(src: Path, sheet: str, workdir: Path) -> Path:
    """在 workdir 里写一份只显示 sheet 的副本（png 渲染活动子表，靠它选子表）。"""
    copy = workdir / src.name
    rewritten = False
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(copy, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == WORKBOOK_PART:
                data = _show_only_sheet(data.decode("utf-8"), sheet).encode("utf-8")
                rewritten = True
            zout.writestr(info, data)
    if not rewritten:
        raise ValueError(f"{WORKBOOK_PART} not found in the package")
    return copy


# 与 `--convert-to csv` 默认输出一致（逗号分隔、双引号、UTF-8、存原始值），末位是子表序号（1 起）。
# csv 导出不看子表是否隐藏、哪张活动，只认这个序号。
_CSV_SHEET_FILTER = "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,{index}"

_PREPARE_ERRORS = (ValueError, KeyError, OSError, RuntimeError, UnicodeDecodeError,
                   EOFError, zlib.error, zipfile.BadZipFile, NotImplementedError)


def _sheet_file_part(sheet: str) -> str:
    """子表名在产物文件名里的写法：能直接当文件名的原样用；清洗过的追加原名哈希前 6 位。

    只由子表名本身决定——重导出、调子表顺序、增删其他子表，名字都不变。
    """
    safe = _UNSAFE_NAME_RE.sub("_", sheet).strip() or "sheet"
    if safe == sheet:
        return safe
    return f"{safe}_{hashlib.md5(sheet.encode('utf-8')).hexdigest()[:6]}"


def _file_part_clash(sheet: str, names: List[str]) -> Optional[str]:
    """与本子表产物名相同的其他子表（文件系统按不分大小写计）；没有返回 None。"""
    part = _sheet_file_part(sheet).casefold()
    return next((n for n in names if n != sheet and _sheet_file_part(n).casefold() == part), None)


def _convert_sheet(src: Path, fmt: str, outdir: Path, timeout: int, sheet: str,
                   final_name: Optional[str] = None) -> dict:
    """只转一个子表；产物名为 <原名>__<子表名>.<格式>（见 _sheet_file_part），
    与其他子表的产物名撞上时报 invalid_input，不静默覆盖。"""
    ext = fmt.split(":", 1)[0].lower()
    if ext not in SHEET_FORMATS:
        return {"status": "invalid_input", "error": "--sheet only applies to png / csv"}
    if ":" in fmt:
        return {"status": "invalid_input", "error": "--sheet cannot be combined with a custom filter in the format"}
    if src.suffix.lower() not in (".xlsx", ".xlsm"):
        return {"status": "invalid_input", "error": "--sheet only supports .xlsx / .xlsm input"}
    try:
        workdir = Path(tempfile.mkdtemp(prefix=SHEET_COPY_PREFIX))
    except OSError as exc:
        return {"status": "lo_start_failed", "error": f"cannot create working directory: {exc}"}
    try:
        try:
            workbook_xml = _read_workbook_xml(src)
            index = _sheet_index(workbook_xml, sheet)
            if final_name is None:
                clash = _file_part_clash(sheet, _sheet_names(workbook_xml))
                if clash is not None:
                    return {"status": "invalid_input",
                            "error": f"sheets {sheet!r} and {clash!r} map to the same output name "
                                     f"{_sheet_file_part(sheet)!r}; rename one of them before exporting"}
                final_name = f"{src.stem}__{_sheet_file_part(sheet)}.{ext}"
            final = outdir / final_name
            # 目标是目录（含指向目录的符号链接）时 shutil.move 会把产物移进去，output 就指错了
            if final.is_dir():
                return {"status": "invalid_input",
                        "error": f"output path {final} is a directory; choose another --outdir"}
            if ext == "csv":
                source, run_fmt = src, _CSV_SHEET_FILTER.format(index=index + 1)
            else:
                source, run_fmt = _single_sheet_copy(src, sheet, workdir), fmt
        except _PREPARE_ERRORS as exc:
            return {"status": "invalid_input", "error": f"cannot select sheet: {exc}"}
        staging = workdir / "out"
        result = _run_convert(source, run_fmt, staging, timeout, locate=lambda: _single_output(staging, ext))
        if result.get("status") != "success":
            return result
        try:
            outdir.mkdir(parents=True, exist_ok=True)
            if final.resolve() == src.resolve() or (final.exists() and final.samefile(src)):
                return {"status": "invalid_input", "error": "output would overwrite the input; choose another --outdir"}
            shutil.move(result["output"], str(final))
        except OSError as exc:
            return {"status": "convert_failed", "error": f"cannot write output: {exc}"}
        result["output"] = str(final)
        result["sheet"] = sheet
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _single_output(staging: Path, ext: str) -> Optional[Path]:
    found = [p for p in staging.glob(f"*.{ext}") if p.is_file()] if staging.is_dir() else []
    return found[0] if len(found) == 1 else None


def convert(src: Path, fmt: str, outdir: Path, timeout: int, sheet: Optional[str] = None) -> dict:
    """使用隔离 profile 转换文件，并返回结构化执行结果。"""
    if shutil.which("soffice") is None:
        return {"status": "skipped_no_libreoffice", "error": "soffice not found"}
    try:
        if not src.is_file():
            return {"status": "invalid_input", "error": f"input not found: {src}"}
    except OSError as exc:
        return {"status": "invalid_input", "error": f"cannot access input {src}: {exc}"}
    if sheet is not None:
        return _convert_sheet(src, fmt, outdir, timeout, sheet)
    if fmt.lower() == "csv" and src.suffix.lower() in (".xlsx", ".xlsm"):
        # LO 默认导出第 1 个子表，即使它是隐藏的；改成导出第一个可见子表，与 png 一致
        try:
            xml = _read_workbook_xml(src)
            index = _first_visible_index(xml)
        except _PREPARE_ERRORS:
            index = 0   # 读不了结构就交给 soffice 按默认处理，失败由它报
        if index > 0:
            result = _convert_sheet(src, "csv", outdir, timeout, _sheet_names(xml)[index],
                                    final_name=f"{src.stem}.csv")
            result.pop("sheet", None)
            return result
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        expected = outdir / f"{src.stem}.{fmt.split(':', 1)[0]}"
        # 路径文本不同也可能指向同一文件（大小写不敏感文件系统或硬链接）。
        if expected.resolve() == src.resolve() or (expected.exists() and expected.samefile(src)):
            return {"status": "invalid_input", "error": "output would overwrite the input; choose another --outdir"}
    except (FileExistsError, NotADirectoryError) as exc:
        return {"status": "invalid_input", "error": f"invalid output directory {outdir}: {exc}"}
    except OSError as exc:
        return {"status": "convert_failed", "error": f"cannot prepare output directory {outdir}: {exc}"}
    # 删掉同名旧产物：否则 soffice 静默没写文件时，会把上一次的产物误判成这次的成功。
    try:
        expected.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        return {"status": "convert_failed", "error": f"cannot remove previous output {expected}: {exc}"}
    return _run_convert(src, fmt, outdir, timeout, locate=lambda: expected if expected.is_file() else None)


def _run_convert(src: Path, fmt: str, outdir: Path, timeout: int, locate) -> dict:
    """跑 soffice --convert-to；locate() 返回产物路径或 None。启动失败换新 profile 重试一次。"""
    outdir.mkdir(parents=True, exist_ok=True)
    sweep_stale_profiles(PROFILE_PREFIX)
    sweep_stale_profiles(SHEET_COPY_PREFIX)
    last = {}
    for attempt in (1, 2):
        try:
            profile = Path(tempfile.mkdtemp(prefix=PROFILE_PREFIX))
        except OSError as exc:
            return {"status": "lo_start_failed", "error": f"cannot create LibreOffice profile: {exc}"}
        try:
            cmd = ["soffice", profile_arg(profile), "--headless", "--norestore",
                   "--convert-to", fmt, "--outdir", str(outdir), str(src)]
            try:
                proc = run_managed_process(cmd, timeout, get_soffice_env())
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "error": f"conversion timed out after {timeout}s"}
            except (FileNotFoundError, OSError) as exc:
                return {"status": "lo_start_failed", "error": str(exc)}
            except (RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                # shim 准备失败等环境问题，换 profile 修不好
                return {"status": "convert_failed", "error": f"LibreOffice environment setup failed: {exc}"}
            detail = soffice_detail(proc.stderr, proc.stdout)
            output = locate()
            if proc.returncode == 0 and output is not None:
                return {"status": "success", "output": str(output), "attempts": attempt}
            start_failed = any(m in detail for m in LO_START_FAILURE_MARKERS)
            last = {"status": "lo_start_failed" if start_failed else "convert_failed",
                    "error": detail[-800:] or f"soffice exited {proc.returncode} without output",
                    "attempts": attempt}
            if not start_failed:
                return last
        finally:
            shutil.rmtree(profile, ignore_errors=True)
    return last


HINTS = {
    "lo_start_failed": ("检查 LibreOffice 启动报错中的路径、权限与可用空间；"
                        "进程报告启动失败时最多换新 profile 重试一次，"
                        "不要 pkill soffice 或删 ~/.config/libreoffice。"),
    "timeout": "转换超时；不要加长超时反复重跑，也不要 pkill -f soffice（会杀掉执行这条命令的 shell）。",
    "convert_failed": "确认输入文件能被打开、目标格式写法正确（如 pdf / png / xlsx / csv）后再试。",
    "invalid_input": "检查输入路径、--outdir 与 --sheet（子表名要与工作簿里的完全一致）。",
    "skipped_no_libreoffice": "本机没有 LibreOffice，转换不可用。",
}


def main() -> None:
    """解析命令行参数，执行转换并映射退出码。"""
    ap = argparse.ArgumentParser(description="用独立 LibreOffice profile 转换文件格式")
    ap.add_argument("input")
    ap.add_argument("format", help="soffice --convert-to 的目标格式，如 pdf / png / xlsx / csv")
    ap.add_argument("--outdir", default=".", help="输出目录，默认当前目录")
    ap.add_argument("--timeout", type=int, default=120, help="单次转换超时秒数，默认 120")
    ap.add_argument("--sheet", help="仅 png / csv：要转换的子表名，默认第一个可见子表")
    args = ap.parse_args()

    result = convert(Path(args.input).absolute(), args.format, Path(args.outdir).absolute(), args.timeout,
                     sheet=args.sheet)
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] == "success":
        sys.exit(0)
    print(f"[convert] {result.get('error')}\n{HINTS.get(result['status'], '')}", file=sys.stderr)
    sys.exit(4 if result["status"] == "skipped_no_libreoffice" else 3)


if __name__ == "__main__":
    main()
