#!/usr/bin/env python3
"""校验并写入标准案件事件；只处理已经明确绑定的案件。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


STATUSES = {"草稿", "待核验稿", "门禁通过稿", "律师确认稿"}
REQUIRED = ("案件编号", "案件简称", "事件类型", "产出名称", "来源Skill", "成果状态", "完成日期", "摘要")


class EventError(Exception):
    pass


def load_event(raw: str | None, path: Path | None) -> dict:
    if bool(raw) == bool(path):
        raise EventError("必须且只能提供 --json 或 --file 之一")
    try:
        value = json.loads(raw) if raw else json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EventError(f"事件 JSON 无法读取：{exc}") from exc
    if not isinstance(value, dict):
        raise EventError("事件必须是 JSON 对象")
    return value


def validate(event: dict, cases_root: Path) -> Path:
    missing = [field for field in REQUIRED if not str(event.get(field, "")).strip()]
    if missing:
        raise EventError("缺少必填字段：" + "、".join(missing))
    if event["成果状态"] not in STATUSES:
        raise EventError("成果状态只允许：" + "、".join(sorted(STATUSES)))
    try:
        dt.date.fromisoformat(str(event["完成日期"]))
    except ValueError as exc:
        raise EventError("完成日期必须为 YYYY-MM-DD") from exc
    short_name = str(event["案件简称"]).strip()
    if short_name in {".", ".."} or "/" in short_name or "\\" in short_name:
        raise EventError("案件简称不能包含路径分隔符")
    matter_dir = cases_root / short_name
    if not (matter_dir / "案件画像.md").is_file():
        raise EventError(f"未找到已建档案件：{matter_dir / '案件画像.md'}；不得自动建档")
    output_path = str(event.get("产出路径", "")).strip()
    if output_path and not (output_path.startswith("http://") or output_path.startswith("https://")):
        if not Path(output_path).exists():
            raise EventError(f"产出路径不存在：{output_path}")
    return matter_dir


def append_history(event: dict, matter_dir: Path) -> None:
    history = matter_dir / "办案历程.md"
    if not history.exists():
        history.write_text("# 办案历程\n\n", encoding="utf-8")
    path_text = f"；产出：{event['产出路径']}" if event.get("产出路径") else ""
    line = (
        f"- {event['完成日期']} ｜ {event['事件类型']} ｜ {event['产出名称']}"
        f"（{event['成果状态']}）｜ 来源：{event['来源Skill']} ｜ {event['摘要']}{path_text}\n"
    )
    with history.open("a", encoding="utf-8") as handle:
        handle.write(line)


def update_local_ledger(event: dict, ledger: Path) -> tuple[bool, str]:
    if not ledger.exists():
        return False, "本地台账不存在，已只追加办案历程"
    script = Path(__file__).resolve().parent / "ledger_excel.py"
    patch = {"当前进展": f"{event['产出名称']}（{event['成果状态']}）：{event['摘要']}"}
    if str(event.get("下一步动作", "")).strip():
        patch["下一步动作"] = str(event["下一步动作"]).strip()
    result = subprocess.run(
        [sys.executable, str(script), "update", "--path", str(ledger), "--field", "案件编号",
         "--value", str(event["案件编号"]), "--json", json.dumps(patch, ensure_ascii=False)],
        text=True, capture_output=True, check=False,
    )
    if result.returncode:
        return False, (result.stderr or result.stdout).strip()
    return True, "本地台账已更新"


def main() -> int:
    parser = argparse.ArgumentParser(description="校验并写入标准案件事件")
    parser.add_argument("--json", help="案件事件 JSON 字符串")
    parser.add_argument("--file", type=Path, help="案件事件 JSON 文件")
    parser.add_argument("--cases-root", type=Path, default=Path("cases"))
    parser.add_argument("--ledger", type=Path, default=Path("cases/案件台账.xlsx"))
    parser.add_argument("--online-ledger", action="store_true", help="在线台账由案件管家另行写入，本脚本只追加历程")
    args = parser.parse_args()
    try:
        event = load_event(args.json, args.file)
        matter_dir = validate(event, args.cases_root)
        append_history(event, matter_dir)
    except EventError as exc:
        print(f"案件事件未写入：{exc}", file=sys.stderr)
        return 2

    if args.online_ledger:
        print(json.dumps({"status": "history_written", "event": event, "online_ledger_patch_required": True}, ensure_ascii=False))
        return 0
    updated, note = update_local_ledger(event, args.ledger)
    print(json.dumps({"status": "ok" if updated else "partial", "event": event, "note": note}, ensure_ascii=False))
    return 0 if updated else 1


if __name__ == "__main__":
    raise SystemExit(main())
