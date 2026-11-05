#!/usr/bin/env python3
"""Recalculate a workbook copy with LibreOffice and save it for reading values.

Uses calculateAll(), including workbooks with manual calculation and stale caches.
The source is read-only; the output copy may have LibreOffice formatting changes.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

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


def recalculate(filename, output, timeout=30):
    source, destination = Path(filename).resolve(), Path(output).resolve()
    if timeout <= 0 or not source.is_file():
        return {"status": "invalid_input", "error": "input must exist and timeout must be positive"}
    if source == destination or destination.exists():
        return {"status": "invalid_input", "error": "output must be a new file distinct from source"}
    if destination.suffix.lower() != source.suffix.lower():
        return {"status": "invalid_input", "error": "output must have the same extension as source"}
    if shutil.which("soffice") is None:
        return {"status": "skipped_no_libreoffice", "output": None}
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with _recalc_workspace(str(source)) as target:
            result = _run_recalculation(target, timeout)
            if result["status"] != "recalculated":
                result["output"] = None
                return result
            # Exclusive creation prevents replacing a concurrent caller's output.
            try:
                stream = destination.open("xb")
            except OSError as exc:
                return {"status": "failed", "error": str(exc), "output": None}
            try:
                with stream, target.open("rb") as data:
                    shutil.copyfileobj(data, stream)
            except OSError:
                _quiet_unlink(destination)
                raise
            result["output"] = str(destination)
            if target.parent != source.parent:
                result["warning"] = "Temporary copy is outside source directory; relative workbook links may not resolve."
            return result
    except (OSError, RuntimeError, _WorkspaceError) as exc:
        return {"status": "failed", "error": str(exc), "output": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--output", required=True, help="New copy for reading calculated values")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    result = recalculate(args.file, args.output, args.timeout)
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "recalculated":
        print("重算未完成，源文件未修改。按返回原因处理；没有可用引擎时说明无法取得计算值。", file=sys.stderr)
        return 4 if result["status"] == "skipped_no_libreoffice" else 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
