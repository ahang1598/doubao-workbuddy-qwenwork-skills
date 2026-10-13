#!/usr/bin/env python3
"""Pre-handoff local check + record-create cells builder — never calls dws.

Before creating a 交接/待认领 sub-record, run this ONCE. It:
  1. validates the handoff summary structure (development tasks add --dev),
  2. renders the 通知文案 (richText markdown) deterministically,
  3. when --cells-out is given, assembles the COMPLETE record-create cells JSON
     with the notice already embedded, and writes it to a file.

The agent then runs `dws aitable record create ... --records-file <cells-out>`.
The notice is born together with the create payload in one atomic file, so it
cannot be forgotten or added later.

Usage:
    python3 scripts/check-handoff-ready.py handoff \
        --title "【交接】<父任务标题>" \
        --summary "<一句话摘要>" \
        --handoff-summary-file <交接摘要文本文件> \
        [--dev] \
        --group "<父任务标题>|<任务ID后6位>" \
        --parent-record-id <父recordId> \
        --creator '{"userId":"...","corpId":"..."}' \
        --assignee '{"userId":"...","corpId":"..."}' \
        --fields '<字段名→fieldId 映射 JSON>' \
        [--outputs-file-tokens "f1,f2"] \
        [--workfiles-file-tokens "f3"] \
        --cells-out <create-cells.json>

    python3 scripts/check-handoff-ready.py claim ...    # 无 --assignee
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_render_notice = _load_module("render_notice", SCRIPTS_DIR / "render-notice.py")
_validate = _load_module("validate_handoff_summary", SCRIPTS_DIR / "validate-handoff-summary.py")

# 字段名固定（来自团队 Schema）；fieldId 运行时映射。产出物/工作文件可选（无附件时省略）。
REQUIRED_FIELD_NAMES = [
    "任务标题",
    "任务组",
    "交接状态",
    "任务交接对象",
    "创建人",
    "一句话摘要",
    "交接摘要",
    "通知文案",
    "父记录",
]
OPTIONAL_FIELD_NAMES = ["产出物", "工作文件"]


def _parse_user(raw: str) -> dict:
    obj = json.loads(raw)
    if not isinstance(obj, dict) or "userId" not in obj or "corpId" not in obj:
        raise ValueError('creator/assignee 必须是 {"userId":"...","corpId":"..."}')
    return obj


def _parse_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def check_ready(
    kind: str,
    title: str,
    summary: str,
    handoff_summary_text: str,
    is_dev: bool,
) -> tuple[list[str], dict | None]:
    """Return (blocking_errors, notice_dict). notice is None if not ready."""
    errors: list[str] = []
    if not title.strip():
        errors.append("任务标题为空")
    if not summary.strip():
        errors.append("一句话摘要为空")

    missing = _validate.check_summary(handoff_summary_text, is_dev)
    errors.extend(f"交接摘要缺少「{label}」" for label in missing)

    notice = None
    if not errors:
        notice = _render_notice.render_notice(kind, title, summary)
    return errors, notice


def build_cells(
    kind: str,
    title: str,
    summary: str,
    handoff_summary_text: str,
    notice: dict,
    fields: dict[str, str],
    group: str,
    parent_record_id: str,
    creator: dict,
    assignee: dict | None,
    output_file_tokens: list[str],
    workfile_file_tokens: list[str],
) -> dict:
    """Assemble the record-create cells with 通知文案 embedded. keys are fieldIds."""
    missing = [n for n in REQUIRED_FIELD_NAMES if n not in fields]
    if missing:
        raise ValueError("字段映射缺少：" + "、".join(missing))

    for name, tokens in (("产出物", output_file_tokens), ("工作文件", workfile_file_tokens)):
        if tokens and name not in fields:
            raise ValueError(f"字段映射缺少：{name}")

    cells: dict = {}
    cells[fields["任务标题"]] = title
    cells[fields["任务组"]] = group
    cells[fields["交接状态"]] = "交接中" if kind == "handoff" else "待认领"
    cells[fields["创建人"]] = [creator]
    cells[fields["一句话摘要"]] = summary
    cells[fields["交接摘要"]] = handoff_summary_text
    cells[fields["通知文案"]] = notice
    cells[fields["父记录"]] = {"linkedRecordIds": [parent_record_id]}
    if assignee is not None:
        cells[fields["任务交接对象"]] = [assignee]
    if output_file_tokens:
        cells[fields["产出物"]] = [{"fileToken": t} for t in output_file_tokens]
    if workfile_file_tokens:
        cells[fields["工作文件"]] = [{"fileToken": t} for t in workfile_file_tokens]
    return cells


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["handoff", "claim"], help="指定人交接或待认领")
    parser.add_argument("--title", required=True, help="交接子记录任务标题")
    parser.add_argument("--summary", required=True, help="一句话摘要（180 字以内）")
    parser.add_argument("--handoff-summary-file", "-s", required=True, help="交接摘要文本文件路径")
    parser.add_argument("--dev", action="store_true", help="开发任务：额外要求仓库/验证/交付物")
    parser.add_argument("--notice-out", help="可选：把通知文案 JSON 单独写入指定文件")
    parser.add_argument("--group", help="任务组值：<父任务标题>|<任务ID后6位>")
    parser.add_argument("--parent-record-id", help="父 recordId")
    parser.add_argument("--creator", help='创建人 user 对象 JSON：{"userId":"...","corpId":"..."}')
    parser.add_argument("--assignee", help='任务交接对象 user 对象 JSON（仅 handoff）')
    parser.add_argument("--fields", help="字段名→fieldId 映射 JSON 字符串")
    parser.add_argument("--outputs-file-tokens", help="产出物 fileToken，逗号分隔")
    parser.add_argument("--workfiles-file-tokens", help="工作文件 fileToken，逗号分隔")
    parser.add_argument("--cells-out", help="生成完整 record-create cells JSON 到该文件")
    args = parser.parse_args()

    try:
        handoff_summary_text = Path(args.handoff_summary_file).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL: 无法读取交接摘要文件：{exc}", file=sys.stderr)
        return 1

    errors, notice = check_ready(args.kind, args.title, args.summary, handoff_summary_text, args.dev)
    if errors:
        print("FAIL: 交接未就绪，禁止创建子记录：", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    notice_json = json.dumps(notice, ensure_ascii=False)
    if args.notice_out:
        Path(args.notice_out).write_text(notice_json, encoding="utf-8")

    if args.cells_out:
        for flag, label in (
            ("fields", "--fields"),
            ("group", "--group"),
            ("parent_record_id", "--parent-record-id"),
            ("creator", "--creator"),
        ):
            if not getattr(args, flag):
                print(f"FAIL: --cells-out 需要 {label}", file=sys.stderr)
                return 1
        if args.kind == "handoff" and not args.assignee:
            print("FAIL: handoff 需要 --assignee", file=sys.stderr)
            return 1
        if args.kind == "claim" and args.assignee:
            print("FAIL: claim 不需要 --assignee（待认领无交接对象）", file=sys.stderr)
            return 1
        try:
            fields = json.loads(args.fields)
            creator = _parse_user(args.creator)
            assignee = _parse_user(args.assignee) if args.assignee else None
            output_tokens = _parse_tokens(args.outputs_file_tokens)
            workfile_tokens = _parse_tokens(args.workfiles_file_tokens)
            cells = build_cells(
                args.kind,
                args.title,
                args.summary,
                handoff_summary_text,
                notice,
                fields,
                args.group,
                args.parent_record_id,
                creator,
                assignee,
                output_tokens,
                workfile_tokens,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"FAIL: cells 组装失败：{exc}", file=sys.stderr)
            return 1

        payload = [{"cells": cells}]
        Path(args.cells_out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("PASS: 交接就绪")
        print(f"已生成完整 record-create cells：{args.cells_out}（通知文案已内嵌，可直接 --records-file 使用）")
        return 0

    print("PASS: 交接就绪")
    print("通知文案 cell 值（原样嵌入 <通知文案fieldId>）：")
    print(notice_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())