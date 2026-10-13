"""``check`` 命令：固定表结构自检与修复。

用法：
    uv run python scripts/cli.py check [--repair] [--json]

- 无参数：只读自检，输出人类可读报告
- --repair：自检后自动补充缺失的表和字段（禁止删除任何内容）
- --json：输出原始 JSON（供脚本解析）

退出码：
    0  校验通过（或修复后通过）
    1  校验未通过（有缺失表/字段或类型不匹配）
    2  配置错误（未初始化、AI表格 不可访问等）
"""

from __future__ import annotations

import argparse
import sys
from typing import List

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.domain import schema as S
from scripts.infrastructure import config as cfg
from scripts.services.initializer import ValidationReport
from scripts.utils.output import err, print_json

# ANSI 颜色（终端不支持时降级为纯文本）
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_RESET = "\033[0m"
_BOLD = "\033[1m"

def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def _c(text: str, color: str) -> str:
    if _supports_color():
        return f"{color}{text}{_RESET}"
    return text

@register_command
class CheckCommand(BaseCommand):
    name = "check"
    help = "自检固定表结构，可选 --repair 补充缺失表/字段（禁止删除）"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--repair",
            action="store_true",
            help="自检后自动补充缺失的表和字段（不会删除或修改已有内容）",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="output_json",
            help="以 JSON 格式输出校验报告（供脚本解析）",
        )
        parser.set_defaults(func=_check)

# ---------------------------------------------------------------------------
# handler
# ---------------------------------------------------------------------------

def _check(args: argparse.Namespace, ctx: AppContext) -> int:
    bid = cfg.get_base_id()
    if not bid:
        err("未初始化，无 base_id。请先运行 init create/url。")
        return 2

    # ── 第一次校验 ──────────────────────────────────────────────────────────
    report = ctx.initializer.validate(bid)

    if args.output_json:
        print_json(report.to_dict())
        return 0 if report.is_passed else 1

    _print_report(report, title="CHECK")

    if report.is_passed:
        print(_c("\n[结果] 通过 ✓", _GREEN + _BOLD))
        return 0

    # 统计问题数
    issues = _count_issues(report)
    print(_c(f"\n[结果] 未通过（{issues} 项问题）", _RED + _BOLD))

    if not args.repair:
        print(
            _c(
                "提示：运行 check --repair 可自动补齐缺失的表和字段（不会删除任何内容）",
                _YELLOW,
            )
        )
        return 1

    # ── 修复 ────────────────────────────────────────────────────────────────
    print(_c("\n[REPAIR] 正在修复...", _CYAN + _BOLD))
    _do_repair(ctx, bid, report)

    # ── 修复后重新校验 ────────────────────────────────────────────────────────
    print(_c("\n[结果] 修复完成，重新校验...", _CYAN))
    report2 = ctx.initializer.validate(bid)
    _print_report(report2, title="CHECK")

    if report2.is_passed:
        print(_c("\n[结果] 通过 ✓", _GREEN + _BOLD))
        return 0

    remaining = _count_issues(report2)
    print(_c(f"\n[结果] 仍有 {remaining} 项问题无法自动修复（字段类型不匹配需手工处理）", _RED + _BOLD))
    return 1

# ---------------------------------------------------------------------------
# 人类可读报告输出
# ---------------------------------------------------------------------------

def _print_report(report: ValidationReport, title: str = "CHECK") -> None:
    print(f"\n[{title}] AI表格: {_c(report.base_id, _CYAN)}")

    if not report.base_accessible:
        print(f"  {_c('✗', _RED)} AI表格 不可访问: {report.error_message}")
        return

    for table_name in S.ALL_TABLE_NAMES:
        item = report.tables.get(table_name)
        if item is None:
            # 未校验到（不应出现）
            print(f"  {_c('?', _YELLOW)} {table_name:<12} 未校验")
            continue

        expected_count = len(S.get_required_field_names(table_name))

        if not item.exists:
            print(
                f"  {_c('✗', _RED)} {table_name:<12} "
                f"{_c('缺失 → 需要创建', _RED)}"
            )
            continue

        missing = item.missing_fields
        mismatched = item.type_mismatched
        tid_display = _c(f"({item.table_id})", _CYAN) if item.table_id else ""

        if not missing and not mismatched:
            print(
                f"  {_c('✓', _GREEN)} {table_name:<12} {tid_display}  "
                f"{_c(f'{expected_count}/{expected_count} 字段完整', _GREEN)}"
            )
        else:
            actual_ok = expected_count - len(missing) - len(mismatched)
            print(
                f"  {_c('✗', _RED)} {table_name:<12} {tid_display}  "
                f"{_c(f'{actual_ok}/{expected_count} 字段', _YELLOW)}"
            )
            if missing:
                names = ", ".join(f["name"] for f in missing)
                print(f"    {_c('✗ 字段缺失:', _RED)} {names}")
            if mismatched:
                for m in mismatched:
                    print(
                        f"    {_c('⚠ 类型不匹配:', _YELLOW)} "
                        f"{m['name']} "
                        f"(期望 {m['expected']}，实际 {m['actual']}，需手工修复)"
                    )

# ---------------------------------------------------------------------------
# 修复执行（仅补充，禁止删除）
# ---------------------------------------------------------------------------

def _do_repair(ctx: AppContext, base_id: str, report: ValidationReport) -> None:
    """根据校验报告补充缺失的表和字段，不删除任何已有内容。"""
    initializer = ctx.initializer

    for table_name, item in report.tables.items():
        if not item.exists:
            print(f"  {_c('+', _GREEN)} 创建表: {table_name}")
            try:
                initializer._create_table_with_phases(base_id, table_name)
            except Exception as exc:
                print(
                    f"  {_c('✗', _RED)} 创建表 {table_name!r} 失败: {exc}",
                    file=sys.stderr,
                )
            continue

        if item.missing_fields:
            schema = S.get_table_schema(table_name)
            spec_by_name = {f["name"]: f for f in schema["fields"]}
            fields_to_create = [
                spec_by_name[m["name"]]
                for m in item.missing_fields
                if m["name"] in spec_by_name
            ]
            if fields_to_create:
                names_str = ", ".join(f["name"] for f in fields_to_create)
                print(f"  {_c('+', _GREEN)} 补充字段: {names_str} ({table_name})")
                try:
                    initializer._create_fields_in_chunks(
                        base_id, item.table_id, fields_to_create
                    )
                except Exception as exc:
                    print(
                        f"  {_c('✗', _RED)} 补充字段失败 ({table_name}): {exc}",
                        file=sys.stderr,
                    )

        # 类型不匹配：不做任何操作，仅提示
        if item.type_mismatched:
            for m in item.type_mismatched:
                print(
                    f"  {_c('⚠', _YELLOW)} 跳过: {m['name']} ({table_name}) "
                    f"类型不匹配，需手工修复"
                )

# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _count_issues(report: ValidationReport) -> int:
    """统计报告中的问题总数（缺失表 + 缺失字段 + 类型不匹配）。"""
    count = 0
    for item in report.tables.values():
        if not item.exists:
            count += 1
        else:
            count += len(item.missing_fields)
            count += len(item.type_mismatched)
    return count
