#!/usr/bin/env python3
"""用独立 LibreOffice profile 转换文件格式（xlsx → pdf / xlsx / csv 等）。

直接写 `soffice --convert-to` 会落到共享的默认 profile：一次被杀或初始化中断留下的
锁与半成品目录，会让之后每次启动都失败。本脚本每次新建临时 profile，转换结束即删，
超时回收整棵进程树，调用方无需 pkill。

用法：
  python3 excel_lo_convert.py <输入文件> <目标格式> [--outdir 目录] [--timeout 秒]
  python3 excel_lo_convert.py report.xlsx pdf --outdir ./preview

stdout 输出一行 JSON。退出码：
  0 = 成功，output 为产物路径；
  3 = 转换失败（invalid_input / lo_start_failed / timeout / convert_failed），stderr 给处置；
  4 = 本机没有 LibreOffice（skipped_no_libreoffice），转换不可用。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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


def convert(src: Path, fmt: str, outdir: Path, timeout: int) -> dict:
    """使用隔离 profile 转换文件，并返回结构化执行结果。"""
    if shutil.which("soffice") is None:
        return {"status": "skipped_no_libreoffice", "error": "soffice not found"}
    try:
        if not src.is_file():
            return {"status": "invalid_input", "error": f"input not found: {src}"}
    except OSError as exc:
        return {"status": "invalid_input", "error": f"cannot access input {src}: {exc}"}
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

    sweep_stale_profiles(PROFILE_PREFIX)
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
            if proc.returncode == 0 and expected.is_file():
                return {"status": "success", "output": str(expected), "attempts": attempt}
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
    "convert_failed": "确认输入文件能被打开、目标格式写法正确（如 pdf / xlsx / csv）后再试。",
    "invalid_input": "检查输入路径与 --outdir。",
    "skipped_no_libreoffice": "本机没有 LibreOffice，转换不可用。",
}


def main() -> None:
    """解析命令行参数，执行转换并映射退出码。"""
    ap = argparse.ArgumentParser(description="用独立 LibreOffice profile 转换文件格式")
    ap.add_argument("input")
    ap.add_argument("format", help="soffice --convert-to 的目标格式，如 pdf / xlsx / csv")
    ap.add_argument("--outdir", default=".", help="输出目录，默认当前目录")
    ap.add_argument("--timeout", type=int, default=120, help="单次转换超时秒数，默认 120")
    args = ap.parse_args()

    result = convert(Path(args.input).absolute(), args.format, Path(args.outdir).absolute(), args.timeout)
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] == "success":
        sys.exit(0)
    print(f"[convert] {result.get('error')}\n{HINTS.get(result['status'], '')}", file=sys.stderr)
    sys.exit(4 if result["status"] == "skipped_no_libreoffice" else 3)


if __name__ == "__main__":
    main()
