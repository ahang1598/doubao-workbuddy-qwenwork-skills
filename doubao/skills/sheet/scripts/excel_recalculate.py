#!/usr/bin/env python3
"""Recalculate a workbook copy with LibreOffice and save it for reading values.

Uses calculateAll(), including workbooks with manual calculation and stale caches.
The source is read-only; the output copy may have LibreOffice formatting changes.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import date, time as datetime_time, timedelta
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Tuple
from _lo_reuse import OutputReuse, digest_file, publish_new_output, reuse_result

from excel_lo_runtime import (LO_START_FAILURE_MARKERS, get_soffice_env, profile_arg,
                              run_managed_process, soffice_detail, sweep_stale_profiles)

PROFILE_MACRO_DIR = Path("user/basic/Standard")
MACRO_FILENAME = "Module1.xba"

# 未完成重算时写进 failure_kind，调用方据此选处置：启动失败已自动换新 profile 重试过一次，
# 超时说明 soffice 挂在等待上——两者都不该再重跑或加长超时。
FAILURE_START = "lo_start_failed"
FAILURE_TIMEOUT = "timeout"
FAILURE_MACRO = "macro_setup_failed"
FAILURE_UNKNOWN = "recalc_failed"
PROFILE_PREFIX = "excel-recalculate-profile-"

RECALCULATE_MACRO = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" script:language="StarBasic">
    Sub RecalculateAndSave()
      ThisComponent.calculateAll()
      ThisComponent.store()
      ThisComponent.close(True)
    End Sub
</script:module>"""


# 进程管理与 profile 参数放在 excel_lo_runtime，供本脚本与 excel_lo_convert 共用；
# 共用进程启动与清理实现。
_profile_arg = profile_arg
_run_managed_process = run_managed_process


def _profile_is_initialized(profile_dir: Path) -> bool:
    """LibreOffice 自己完成初始化后，宏库登记文件里会列出 Module1。

    只有 Module1.xba、没有这份登记的目录是半成品：宏不会被加载，soffice 会在
    无界面状态下一直等到超时。只看返回码判不出来，所以单独核对。
    """
    script_xlb = profile_dir / PROFILE_MACRO_DIR / "script.xlb"
    try:
        return 'library:name="Module1"' in script_xlb.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):  # 写到一半被杀的截断文件同样算半成品
        return False


def setup_libreoffice_macro(profile_dir: Path, timeout: int) -> Tuple[bool, str]:
    """初始化独立 profile 并安装重算宏；失败时返回可展示原因，不抛裸异常。"""
    ok, reason, _kind = _setup_profile(profile_dir, timeout)
    return ok, reason


def _setup_profile(profile_dir: Path, timeout: int) -> Tuple[bool, str, str]:
    """同 setup_libreoffice_macro，另返回 failure_kind：在出错分支直接定类，不靠事后匹配原因字符串。"""
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
        return False, f"LibreOffice profile initialization timed out after {init_timeout}s", FAILURE_TIMEOUT
    except (FileNotFoundError, OSError) as exc:
        return False, f"LibreOffice profile initialization failed: {exc}", FAILURE_START
    except Exception as exc:
        # get_soffice_env() 可能因 shim 准备失败抛 RuntimeError/CalledProcessError；
        # 这里同样要报告执行失败，不能让 traceback 穿出。换 profile 也修不好环境，不重试。
        return False, f"LibreOffice environment setup failed: {exc}", FAILURE_UNKNOWN

    if result.returncode != 0:
        detail = soffice_detail(result.stderr, result.stdout) or f"soffice exited {result.returncode}"
        return False, f"LibreOffice profile initialization failed: {detail}", FAILURE_START
    if not _profile_is_initialized(profile_dir):
        # 不替 LibreOffice 补建目录：补出来的半成品会让后面的重算挂到超时。
        return (False, "LibreOffice profile initialization incomplete: macro library was not registered",
                FAILURE_START)

    macro_file = profile_dir / PROFILE_MACRO_DIR / MACRO_FILENAME
    try:
        macro_file.write_text(RECALCULATE_MACRO, encoding="utf-8")
    except OSError as exc:
        return False, f"LibreOffice macro installation failed: {exc}", FAILURE_MACRO
    return True, "", ""


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
    """把源文件复制成临时副本；重算只作用于副本，原文件全程只读。

    LibreOffice 的 store() 会重写整个工作簿——工作簿默认字体被换成它自己的默认
    字体，列宽账面值随之按新字体的字符宽度基准重算，图案填充与会计式括号负数
    格式也会被改写。取值不该以改动交付物为代价，所以重算跑在副本上。
    副本优先落在原文件同目录：LibreOffice 解析跨工作簿的相对路径外部引用要靠它。
    """
    src = Path(filename).absolute()
    last_error = None
    for parent in (src.parent, Path(tempfile.gettempdir())):
        try:
            fd, name = tempfile.mkstemp(
                dir=str(parent), prefix=f".{src.stem}.recalc-", suffix=src.suffix
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
    raise _WorkspaceError(f"cannot create recalculation copy for {src}: {last_error}")


def _run_recalculation(target: Path, timeout: int) -> dict:
    sweep_stale_profiles(PROFILE_PREFIX)
    for attempt in (1, 2):
        with tempfile.TemporaryDirectory(prefix=PROFILE_PREFIX) as directory:
            profile = Path(directory)
            ready, reason, kind = _setup_profile(profile, timeout)
            if ready:
                try:
                    result = _run_managed_process([
                        "soffice", _profile_arg(profile), "--headless", "--norestore",
                        "vnd.sun.star.script:Standard.Module1.RecalculateAndSave?language=Basic&location=application",
                        str(target),
                    ], timeout + 30, get_soffice_env())
                    if result.returncode == 0:
                        return {"status": "recalculated", "attempts": attempt}
                    reason = soffice_detail(result.stderr, result.stdout) or "LibreOffice exited {}".format(result.returncode)
                    kind = (FAILURE_TIMEOUT if result.returncode == 124 else
                            FAILURE_START if any(m in reason for m in LO_START_FAILURE_MARKERS)
                            else FAILURE_UNKNOWN)
                except subprocess.TimeoutExpired:
                    reason, kind = "LibreOffice recalculation timed out", FAILURE_TIMEOUT
                except (FileNotFoundError, OSError) as exc:
                    reason, kind = str(exc), FAILURE_START
                except (RuntimeError, ValueError, subprocess.SubprocessError) as exc:
                    reason, kind = str(exc), FAILURE_UNKNOWN
            if kind != FAILURE_START or attempt == 2:
                return {"status": "failed", "failure_kind": kind, "error": reason, "attempts": attempt}


def _parse_read_ranges(items):
    if items is None:
        return []
    if not isinstance(items, (list, tuple)) or not 1 <= len(items) <= 16:
        raise ValueError('read_ranges must contain 1 to 16 explicit sheet!A1:B2 ranges')
    from openpyxl.utils.cell import range_boundaries
    selections, count = [], 0
    pattern = r"('(?:[^']|'')+'|[^'!]+)!(\$?[A-Za-z]{1,3}\$?[1-9][0-9]*(?::\$?[A-Za-z]{1,3}\$?[1-9][0-9]*)?)"
    for item in items:
        match = re.fullmatch(pattern, item) if isinstance(item, str) else None
        if not match:
            raise ValueError('read range must include a sheet and bounded A1 cells: {!r}'.format(item))
        sheet, address = match.groups()
        sheet = sheet[1:-1].replace("''", "'") if sheet.startswith("'") else sheet
        address = address.replace('$', '').upper()
        first_column, first_row, last_column, last_row = range_boundaries(address)
        if not (1 <= first_column <= last_column <= 16384 and 1 <= first_row <= last_row <= 1048576):
            raise ValueError('read range is reversed or exceeds Excel bounds: ' + item)
        count += (last_column - first_column + 1) * (last_row - first_row + 1)
        if count > 1000:
            raise ValueError('read ranges exceed 1000 cells; request only the values needed next')
        selections.append((sheet, address, (first_column, first_row, last_column, last_row)))
    return selections


def _range_read_groups(selections):
    groups = []
    for index, (sheet, _, bounds) in enumerate(selections):
        for group in groups:
            if group['sheet'] != sheet:
                continue
            previous = group['bounds']
            merged = (min(previous[0], bounds[0]), min(previous[1], bounds[1]),
                      max(previous[2], bounds[2]), max(previous[3], bounds[3]))
            if (merged[2] - merged[0] + 1) * (merged[3] - merged[1] + 1) <= 1000:
                group['bounds'] = merged
                group['indices'].append(index)
                break
        else:
            groups.append(dict(sheet=sheet, bounds=bounds, indices=[index]))
    return groups


def _load_calculated_workbook(output):
    """Load cached values lazily without modifying shared-string text."""
    from openpyxl.cell.text import Text
    from openpyxl.reader.excel import ExcelReader
    from openpyxl.xml.constants import SHARED_STRINGS, SHEET_MAIN_NS
    from openpyxl.xml.functions import iterparse

    class CachedTextReader(ExcelReader):
        def read_strings(self):
            """Keep the serialized text for one-pass decoding when a cell is read."""
            part = self.package.find(SHARED_STRINGS)
            if part is None:
                return
            with self.archive.open(part.PartName.lstrip('/')) as source:
                for _, node in iterparse(source):
                    if node.tag == '{' + SHEET_MAIN_NS + '}si':
                        self.shared_strings.append(Text.from_tree(node).content)
                        node.clear()

    reader = CachedTextReader(output, read_only=True, data_only=True, keep_links=False)
    try:
        reader.read()
    except Exception:
        reader.archive.close()
        raise
    return reader.wb


def _decode_cached_text(value):
    """Decode OOXML escapes once, preserving escaped literals and surrogate pairs."""
    decoded = re.sub(r'_x([0-9A-Fa-f]{4})_', lambda match: chr(int(match.group(1), 16)), value)
    return decoded.encode('utf-16-le', errors='surrogatepass').decode('utf-16-le')


def _read_calculated_ranges(output, selections):
    workbook = _load_calculated_workbook(output)
    try:
        missing = [sheet for sheet, _, _ in selections if sheet not in workbook.sheetnames]
        if missing:
            raise ValueError('requested sheet not found: ' + ', '.join(missing))
        result = []
        for sheet, address, bounds in selections:
            first_column, first_row, last_column, last_row = bounds
            result.append(dict(sheet=sheet, range=address, error_cells=[],
                               values=[[None] * (last_column - first_column + 1)
                                       for _ in range(last_row - first_row + 1)]))
        for group in _range_read_groups(selections):
            worksheet = workbook[group['sheet']]
            worksheet.reset_dimensions()
            first_column, first_row, last_column, last_row = group['bounds']
            rows = worksheet.iter_rows(min_row=first_row, max_row=last_row,
                                       min_col=first_column, max_col=last_column)
            for row_number, row in enumerate(rows, first_row):
                row_values = []
                for cell in row:
                    value = cell.value
                    if isinstance(value, (date, datetime_time)):
                        value = value.isoformat()
                    elif isinstance(value, timedelta):
                        value = dict(type='duration', seconds=value.total_seconds())
                    elif isinstance(value, str) and cell.data_type == 's':
                        value = _decode_cached_text(value)
                    row_values.append(value)
                for index in group['indices']:
                    left, top, right, bottom = selections[index][2]
                    if top <= row_number <= bottom:
                        start, stop = left - first_column, right - first_column + 1
                        result[index]['values'][row_number - top] = row_values[start:stop]
                        result[index]['error_cells'].extend(
                            dict(cell=cell.coordinate, value=cell.value)
                            for cell in row[start:stop] if cell.data_type == 'e')
        return result
    finally:
        workbook.close()


def recalculate(filename, output=None, timeout=30, reuse=True, read_ranges=None):
    started = time.monotonic()
    try:
        selections = _parse_read_ranges(read_ranges)
    except (ValueError, ImportError) as exc:
        return reuse_result(dict(status='invalid_input', error=str(exc), output=None), reason='invalid_request')
    result = _recalculate(filename, output, timeout, reuse)
    if result.get('status') == 'recalculated':
        result.update(source=str(Path(filename).resolve()), output_role='values_only')
        if selections:
            read_started = time.monotonic()
            try:
                result['ranges'] = _read_calculated_ranges(result['output'], selections)
                result['read_status'] = 'read'
            except Exception as exc:
                result.update(read_status='failed', read_error=str(exc))
            result['values_read_ms'] = round((time.monotonic() - read_started) * 1000, 3)
    result['elapsed_ms'] = round((time.monotonic() - started) * 1000, 3)
    return result


def _recalculate(filename, output, timeout, reuse):
    managed = output is None
    if managed:
        source = Path(filename).resolve()
        directory = source.parent / '.sheet-calculated'
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            return reuse_result({'status': 'invalid_input', 'error': 'managed output directory must be a real directory; use a new --output path'}, reason='unsafe_output')
        output = directory / source.name
    source, destination = Path(filename).resolve(), Path(output).resolve()
    if timeout <= 0 or not source.is_file():
        return reuse_result({"status": "invalid_input", "error": "input must exist and timeout must be positive"}, reason="invalid_request")
    engine = shutil.which("soffice")
    reason = 'disabled' if not reuse else 'engine_unavailable' if engine is None else 'invalid_request'
    cache = (OutputReuse(source, destination, {"operation": "recalculate"}, engine, managed=managed)
             if reuse and engine and source != destination else None)
    if managed:
        destination = cache.output if cache and cache.key else destination.with_name(uuid.uuid4().hex + source.suffix)
        if cache is not None:
            cache.retarget(destination)
    replacement_prefix = ''
    if cache is not None:
        cached = cache.lookup()
        if cached is not None:
            return cached
        if managed and cache.key is not None:
            replacement_prefix = destination.stem + '-'
            initial_miss_reason = cache.reason
            try:
                for candidate in destination.parent.glob(replacement_prefix + '*' + source.suffix):
                    cache.retarget(candidate)
                    cached = cache.lookup()
                    if cached is not None:
                        return cached
            except OSError:
                pass  # Reuse is optional even when the directory cannot be listed.
            cache.retarget(destination)
            cache.reason = initial_miss_reason
    if managed and (destination.exists() or destination.is_symlink()):
        destination = destination.with_name(replacement_prefix + uuid.uuid4().hex + source.suffix)
        if cache is not None:
            cache.retarget(destination)
    if source == destination or destination.exists():
        return reuse_result({"status": "invalid_input", "error": "output must be new and distinct from source unless an unchanged output receipt matches; choose a new --output path, do not delete or overwrite the existing file"}, cache, reason)
    if destination.suffix.lower() != source.suffix.lower():
        return reuse_result({"status": "invalid_input", "error": "output must have the same extension as source"}, reason="invalid_request")
    if engine is None:
        return reuse_result({"status": "skipped_no_libreoffice", "output": None}, reason=reason)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with _recalc_workspace(str(source)) as target:
            engine_started = time.monotonic()
            result = reuse_result(_run_recalculation(target, timeout), cache, reason)
            result['engine_elapsed_ms'] = round((time.monotonic() - engine_started) * 1000, 3)
            if result["status"] != "recalculated":
                result["output"] = None
                return result
            produced_hash = digest_file(target) if cache is not None and cache.key is not None else None
            try:
                publish_new_output(target, destination)
            except OSError as exc:
                return reuse_result({"status": "failed", "error": str(exc), "output": None}, cache, reason)
            result["output"] = str(destination)
            if target.parent != source.parent:
                result["warning"] = "Temporary copy is outside source directory; relative workbook links may not resolve."
            if cache is not None:
                cache.remember(result, produced_hash)
            return result
    except (OSError, RuntimeError, _WorkspaceError) as exc:
        return reuse_result({"status": "failed", "error": str(exc), "output": None}, cache, reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--output", help="Explicit new values-only copy; omit to manage reusable copies beside the source")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--read-range", action="append", dest="read_ranges",
                        help=("Return needed values from the calculated copy in this response: 'Sheet!A1:B2'; "
                              "repeat up to 16 ranges / 1000 cells"))
    reuse_options = parser.add_mutually_exclusive_group()
    reuse_options.add_argument("--reuse", dest="reuse", action="store_true",
                               help=("Default: reuse only a matching unchanged receipt; "
                                     "first calls and changed inputs recalculate automatically."))
    reuse_options.add_argument("--fresh", dest="reuse", action="store_false",
                               help=("Explicitly bypass reuse, e.g. to diagnose a prior receipt; "
                                     "not needed for first calls or changed inputs. --output is optional; "
                                     "if supplied, it must be new and distinct from source."))
    parser.set_defaults(reuse=True)
    args = parser.parse_args()
    result = recalculate(args.file, args.output, args.timeout, reuse=args.reuse, read_ranges=args.read_ranges)
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] == "skipped_no_libreoffice":
        print("本机缺少 LibreOffice，本次公式重算未执行，源文件未修改。\n"
              "缺少 LibreOffice 只限制本地重算与格式转换，保存、导入和交付仍按原契约执行。\n"
              "后续步骤依赖计算值时，先用已有可用引擎取得可靠结果，否则说明该部分未完成；"
              "不把未重算的缓存值当作新结果，也不得声称已完成重算。\n"
              "不反复重跑，不因缺少引擎改用 HTML / 图片替代表格交付。", file=sys.stderr)
        return 4
    if result["status"] != "recalculated":
        print("重算未完成，源文件未修改。按返回原因处理；没有可用引擎时说明无法取得计算值。", file=sys.stderr)
        return 3
    if result.get('read_status') == 'failed':
        print('重算已完成，但指定范围读取失败。保留并读取回执output副本，不重复重算。', file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
