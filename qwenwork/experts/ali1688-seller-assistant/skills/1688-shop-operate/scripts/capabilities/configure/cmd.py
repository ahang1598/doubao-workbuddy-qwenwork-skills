#!/usr/bin/env python3
"""AK 配置命令 — CLI 入口"""

COMMAND_NAME = "configure"
COMMAND_DESC = "配置 AK"

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _output import make_output, print_output, print_error
from capabilities.configure.service import (
    validate_ak, configure_ak, remove_ak, check_existing_config,
)


def _clear_token_silently():
    """尝试吊销并清除 OAuth Token，失败时不中断主流程"""
    try:
        from token_manager import revoke_access, revoke_refresh, clear_token
        from _const import ENV_FILE
        revoke_access(ENV_FILE)
        revoke_refresh(ENV_FILE)
        clear_token(ENV_FILE)
    except Exception:
        pass


def main(args=None):
    """
    AK 配置命令入口。

    Args:
        args: 命令参数列表。为 None 时从 sys.argv[1:] 读取。
              通过 cli.py 路由时传入 sys.argv[2:]。

    支持的参数：
        <AK>            配置新的 AK（若已有旧 AK，会同时清除旧 Token）
        --reset <AK>    重置 AK（清除旧 Token + 配置新 AK）
        --clear         取消 AK 配置（同时清除 Token）
        --status        查看 AK 配置状态
    """
    if args is None:
        args = sys.argv[1:]

    # 无参数时自动查询本地 AK 状态
    if len(args) < 1:
        args = ["--status"]

    try:
        has_existing, existing_ak, existing_source = check_existing_config()

        # --status: 查看 AK 配置状态
        if "--status" in args:
            if has_existing:
                print_output(make_output(
                    success=True,
                    markdown=f"AK 已配置。\n\n**AK**: `{existing_ak}`",
                    data={"configured": True, "ak": existing_ak},
                ))
            else:
                print_output(make_output(
                    success=True,
                    markdown="AK 未配置。",
                    data={"configured": False, "ak": None},
                ))
            return

        # --clear: 取消 AK 并清除 Token
        if "--clear" in args:
            if not has_existing:
                print_output(make_output(
                    success=True,
                    markdown="当前未配置 AK，无需清除。",
                    data={"configured": False},
                ))
                return

            _clear_token_silently()
            remove_ok = remove_ak()
            if remove_ok:
                print_output(make_output(
                    success=True,
                    markdown="AK 已清除，关联的 1688 OAuth Token 也已同步清除。",
                    data={"configured": False},
                ))
            else:
                print_output(make_output(
                    success=False,
                    markdown="AK 清除失败，请检查文件权限。",
                    data={"configured": True},
                ))
            return

        # --reset <AK>: 重置 AK（清除旧 Token + 配置新 AK）
        if "--reset" in args:
            reset_idx = args.index("--reset")
            if reset_idx + 1 >= len(args):
                print_output(make_output(
                    success=False,
                    error_code="MISSING_PARAM",
                    markdown="缺少参数：`--reset` 后需要提供新的 AK",
                ))
                return

            ak = args[reset_idx + 1].strip()
            is_valid, error_msg = validate_ak(ak)
            if not is_valid:
                print_output(make_output(
                    success=False, markdown=f"❌ {error_msg}", data={"configured": False}
                ))
                return

            _clear_token_silently()

            write_ok, storage_location = configure_ak(ak)
            if not write_ok:
                print_output(make_output(
                    success=False,
                    markdown="❌ AK 写入失败，请检查文件权限",
                    data={"configured": False},
                ))
                return

            print_output(make_output(
                success=True,
                markdown="✅ AK 已重置\n\n旧的 1688 OAuth Token 已同步清除。",
                data={"configured": True},
            ))
            return

        # 直接传入 AK -> 配置（若已有旧 AK，同时清除旧 Token）
        ak = args[0].strip()
        is_valid, error_msg = validate_ak(ak)
        if not is_valid:
            print_output(make_output(
                success=False, markdown=f"❌ {error_msg}", data={"configured": False}
            ))
            return

        if has_existing and existing_ak != ak:
            _clear_token_silently()

        write_ok, storage_location = configure_ak(ak)
        if not write_ok:
            print_output(make_output(
                success=False,
                markdown="❌ AK 写入失败，请检查文件权限",
                data={"configured": False},
            ))
            return

        token_hint = "\n\n旧的 1688 OAuth Token 已同步清除" if has_existing and existing_ak != ak else ""
        print_output(make_output(
            success=True,
            markdown=f"✅ AK 设置成功{token_hint}",
            data={"configured": True},
        ))
    except Exception as e:
        print_error(e, {"configured": False})


if __name__ == "__main__":
    main()
