#!/usr/bin/env python3
"""
PandaAI CLI 封装脚本 — 为 factor-mining skill 提供程序化调用接口。

用法:
    python pandaai_cli_wrapper.py <action> [options]

Actions:
    login       登录（交互式，不接受凭据参数）
    create      创建因子分析
    run         执行因子分析
    list        列出所有因子
    balance     查询算力余额
    result      查询运行结果
    info        查看因子详情
    update      修改因子参数
    delete      删除因子分析
"""

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

CLI_CMD = "pandaai-cli"

# 需要尝试的解码顺序：UTF-8 优先，其次 GB18030（Windows 中文环境常见），
# 最后用 errors="replace" 兜底保证不抛异常。
_DECODE_ENCODINGS = ("utf-8", "gb18030")


def _decode_bytes(raw: bytes) -> str:
    """按 UTF-8 → GB18030 → 兜底 的顺序解码 CLI 原始字节输出。"""
    for enc in _DECODE_ENCODINGS:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def run_cli(args: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """执行 pandaai-cli 命令。二进制捕获，编码统一交给 _decode_bytes。"""
    cmd = [CLI_CMD, "--json"] + args
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=False,
    )
    return result


def parse_json_output(result: subprocess.CompletedProcess) -> dict:
    """从 CompletedProcess 解析 JSON 输出，stderr 错误优先返回。"""
    stdout = _decode_bytes(result.stdout or b"")
    stderr = _decode_bytes(result.stderr or b"")

    # 非零退出且有 stderr 时，优先返回错误信息
    if result.returncode != 0 and stderr.strip():
        # 尝试从 stderr 解析 JSON（部分版本错误也用 JSON 格式）
        for line in reversed(stderr.strip().splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return {"success": False, "error": stderr.strip()}

    # 从 stdout 后往前找第一个以 { 或 [ 开头的可解析 JSON 行
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if not line or line[0] not in ("{", "["):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    # 尝试整体解析
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass

    # 有 stderr 但退出码为 0（不常见），也附上
    extra = {"stderr": stderr.strip()} if stderr.strip() else {}
    return {"success": False, "raw_output": stdout, "error": "无法解析 JSON", **extra}


def action_login() -> dict:
    """交互式登录 PandaAI。不接受凭据参数，由用户在终端输入。"""
    # 不传 --json，让交互式提示正常显示；不捕获输出，让终端直连
    cmd = [CLI_CMD, "login"]
    result = subprocess.run(cmd, text=False)
    return {"success": result.returncode == 0}


def action_create(
    formula: str | None = None,
    code: str | None = None,
    file: str | None = None,
    name: str = "新建因子分析",
    start_date: str | None = None,
    end_date: str | None = None,
    adjustment_cycle: int = 1,
    factor_direction: int = 1,
) -> dict:
    """创建因子分析。"""
    args = ["factor_create"]

    if formula:
        args.extend(["--formula", formula])
    elif code:
        args.extend(["--code", code])
    elif file:
        args.extend(["--file", file])
    else:
        return {"success": False, "error": "必须提供 --formula、--code 或 --file 之一"}

    args.extend(["--name", name])
    if start_date:
        args.extend(["--start-date", start_date])
    if end_date:
        args.extend(["--end-date", end_date])
    args.extend(["--adjustment-cycle", str(adjustment_cycle)])
    args.extend(["--factor-direction", str(factor_direction)])

    result = run_cli(args)
    return parse_json_output(result)


def action_run(
    factor_id: str,
    download_path: str | None = None,
    download_default: bool = False,
    poll_interval: int = 2,
    timeout: int = 600,
) -> dict:
    """执行因子分析。

    download_path: 指定下载路径；download_default: 下载到默认路径（~/Downloads/）。
    两者均为 False/None 则不下载。
    """
    args = ["factor_run", factor_id]
    if download_path:
        args.extend(["--download", download_path])
    elif download_default:
        args.append("--download")
    args.extend(["--poll-interval", str(poll_interval)])
    args.extend(["--timeout", str(timeout)])

    result = run_cli(args)
    return parse_json_output(result)


def action_list(limit: int = 100, offset: int = 0, no_detail: bool = False) -> dict:
    """列出所有因子分析。"""
    args = ["factor_list", "--limit", str(limit), "--offset", str(offset)]
    if no_detail:
        args.append("--no-detail")
    result = run_cli(args)
    return parse_json_output(result)


def action_balance() -> dict:
    """查询算力余额。"""
    result = run_cli(["balance"])
    return parse_json_output(result)


def action_result(run_id: str, download_path: str | None = None, download_default: bool = False) -> dict:
    """查询运行结果。"""
    args = ["factor_result", run_id]
    if download_path:
        args.extend(["--download", download_path])
    elif download_default:
        args.append("--download")
    result = run_cli(args)
    return parse_json_output(result)


def action_info(factor_id: str) -> dict:
    """查看因子详情。"""
    result = run_cli(["factor_info", factor_id])
    return parse_json_output(result)


def action_update(
    factor_id: str,
    name: str | None = None,
    formula: str | None = None,
    code: str | None = None,
    file: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    adjustment_cycle: int | None = None,
    factor_direction: int | None = None,
) -> dict:
    """修改因子参数。"""
    args = ["factor_update", factor_id]
    if name:
        args.extend(["--name", name])
    if formula:
        args.extend(["--formula", formula])
    elif code:
        args.extend(["--code", code])
    elif file:
        args.extend(["--file", file])
    if start_date:
        args.extend(["--start-date", start_date])
    if end_date:
        args.extend(["--end-date", end_date])
    if adjustment_cycle is not None:
        args.extend(["--adjustment-cycle", str(adjustment_cycle)])
    if factor_direction is not None:
        args.extend(["--factor-direction", str(factor_direction)])
    result = run_cli(args)
    return parse_json_output(result)


def action_delete(
    factor_ids: list[str] | None = None,
    pattern: str | None = None,
    yes: bool = False,
) -> dict:
    """删除因子分析。"""
    args = ["factor_delete"]
    if factor_ids:
        args.extend(factor_ids)
    if pattern:
        args.extend(["--pattern", pattern])
    if yes:
        args.append("--yes")
    result = run_cli(args)
    return parse_json_output(result)


def main():
    parser = argparse.ArgumentParser(description="PandaAI CLI Wrapper")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # login — 不暴露 phone/password，凭据只能在终端交互输入
    subparsers.add_parser("login", help="交互式登录（不接受凭据参数）")

    # create
    p_create = subparsers.add_parser("create", help="创建因子分析")
    p_create.add_argument("--formula", default=None)
    p_create.add_argument("--code", default=None)
    p_create.add_argument("--file", default=None)
    p_create.add_argument("--name", default="新建因子分析")
    p_create.add_argument("--start-date", default=None)
    p_create.add_argument("--end-date", default=None)
    p_create.add_argument("--adjustment-cycle", type=int, default=1)
    p_create.add_argument("--factor-direction", type=int, default=1)

    # run
    p_run = subparsers.add_parser("run", help="执行因子分析")
    p_run.add_argument("factor_id")
    dl_group = p_run.add_mutually_exclusive_group()
    dl_group.add_argument("--download-path", default=None,
                          help="下载结果到指定路径")
    dl_group.add_argument("--download", action="store_true",
                          help="下载结果到默认路径（~/Downloads/）")
    p_run.add_argument("--poll-interval", type=int, default=2)
    p_run.add_argument("--timeout", type=int, default=600)

    # list
    p_list = subparsers.add_parser("list", help="列出因子")
    p_list.add_argument("--limit", type=int, default=100)
    p_list.add_argument("--offset", type=int, default=0)
    p_list.add_argument("--no-detail", action="store_true")

    # balance
    subparsers.add_parser("balance", help="查询余额")

    # result
    p_result = subparsers.add_parser("result", help="查询结果")
    p_result.add_argument("run_id")
    dl_group2 = p_result.add_mutually_exclusive_group()
    dl_group2.add_argument("--download-path", default=None,
                           help="下载结果到指定路径")
    dl_group2.add_argument("--download", action="store_true",
                           help="下载结果到默认路径（~/Downloads/）")

    # info
    p_info = subparsers.add_parser("info", help="因子详情")
    p_info.add_argument("factor_id")

    # update
    p_update = subparsers.add_parser("update", help="修改因子")
    p_update.add_argument("factor_id")
    p_update.add_argument("--name", default=None)
    p_update.add_argument("--formula", default=None)
    p_update.add_argument("--code", default=None)
    p_update.add_argument("--file", default=None)
    p_update.add_argument("--start-date", default=None)
    p_update.add_argument("--end-date", default=None)
    p_update.add_argument("--adjustment-cycle", type=int, default=None)
    p_update.add_argument("--factor-direction", type=int, default=None)

    # delete
    p_delete = subparsers.add_parser("delete", help="删除因子")
    p_delete.add_argument("factor_ids", nargs="*")
    p_delete.add_argument("--pattern", default=None)
    p_delete.add_argument("--yes", action="store_true")

    args = parser.parse_args()
    action = args.action

    if action == "login":
        result = action_login()
    elif action == "create":
        result = action_create(
            formula=args.formula,
            code=args.code,
            file=args.file,
            name=args.name,
            start_date=args.start_date,
            end_date=args.end_date,
            adjustment_cycle=args.adjustment_cycle,
            factor_direction=args.factor_direction,
        )
    elif action == "run":
        result = action_run(
            factor_id=args.factor_id,
            download_path=args.download_path,
            download_default=args.download,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
    elif action == "list":
        result = action_list(limit=args.limit, offset=args.offset, no_detail=args.no_detail)
    elif action == "balance":
        result = action_balance()
    elif action == "result":
        result = action_result(
            run_id=args.run_id,
            download_path=args.download_path,
            download_default=args.download,
        )
    elif action == "info":
        result = action_info(args.factor_id)
    elif action == "update":
        result = action_update(
            factor_id=args.factor_id,
            name=args.name,
            formula=args.formula,
            code=args.code,
            file=args.file,
            start_date=args.start_date,
            end_date=args.end_date,
            adjustment_cycle=args.adjustment_cycle,
            factor_direction=args.factor_direction,
        )
    elif action == "delete":
        result = action_delete(
            factor_ids=args.factor_ids or None,
            pattern=args.pattern,
            yes=args.yes,
        )
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # Windows 控制台默认 GBK 时，stdout 强制用 UTF-8，保证中文 JSON 正常显示
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
