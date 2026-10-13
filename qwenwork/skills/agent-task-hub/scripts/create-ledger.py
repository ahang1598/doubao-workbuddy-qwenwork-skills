#!/usr/bin/env python3
"""Prepare agent-task-hub team ledger artifacts.

This helper is local-only. It never calls dws, because dws authentication is
injected only for foreground agent commands whose first word is `dws`.

Use it to generate deterministic JSON artifacts and the foreground dws command
plan. The agent then runs each dws command directly in the foreground.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEAM_BASE_NAME = "千问办公团队接续台账"
TASK_TABLE_NAME = "任务台账"
ALIDOCS_PREFIX = "https://alidocs.dingtalk.com/i/nodes/"
PLACEHOLDER_RE = re.compile(r"<[^>]+>")


TEAM_FIELDS = [
    {"fieldName": "任务标题", "type": "text"},
    {"fieldName": "任务组", "type": "text"},
    {
        "fieldName": "交接状态",
        "type": "singleSelect",
        "config": {"options": [{"name": v} for v in ["未交接", "待认领", "交接中", "已接手", "已完成"]]},
    },
    {"fieldName": "任务交接对象", "type": "user", "config": {"multiple": False}},
    {
        "fieldName": "状态",
        "type": "singleSelect",
        "config": {"options": [{"name": v} for v in ["进行中", "等待确认", "已完成", "已取消", "失败", "中断", "暂停"]]},
    },
    {"fieldName": "一句话摘要", "type": "text"},
    {"fieldName": "交接摘要", "type": "text"},
    {"fieldName": "产出物", "type": "attachment"},
    {"fieldName": "工作文件", "type": "attachment"},
    {
        "fieldName": "Agent类型",
        "type": "singleSelect",
        "config": {"options": [{"name": v} for v in ["qwenwork", "codex", "qoder", "claudecode", "qoderwork", "其他"]]},
    },
    {"fieldName": "任务ID", "type": "text"},
    {"fieldName": "通知文案", "type": "richText"},
    {"fieldName": "创建人", "type": "user", "config": {"multiple": False}},
]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def base_url(base_id: str) -> str:
    return f"{ALIDOCS_PREFIX}{base_id}"


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def unwrap(data: Any) -> Any:
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


def first_value(data: Any, *keys: str) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if key in data:
                return data[key]
        for value in data.values():
            found = first_value(value, *keys)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = first_value(item, *keys)
            if found is not None:
                return found
    return None


def extract_fields(table_get_response: Any) -> dict[str, dict[str, Any]]:
    data = unwrap(table_get_response)
    fields = first_value(data, "fields") or []
    if not isinstance(fields, list):
        raise SystemExit("cannot find fields list in table get response")

    mapping: dict[str, dict[str, Any]] = {}
    duplicates: dict[str, int] = {}
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = field.get("fieldName") or field.get("name")
        field_id = field.get("fieldId") or field.get("id")
        if not name or not field_id:
            continue
        duplicates[name] = duplicates.get(name, 0) + 1
        mapping[name] = field

    dup_names = [name for name, count in duplicates.items() if count > 1]
    if dup_names:
        raise SystemExit(f"duplicate field names found: {', '.join(dup_names)}")
    return mapping


def field_id(fields: dict[str, dict[str, Any]], name: str) -> str:
    field = fields.get(name)
    if not field:
        raise SystemExit(f"missing field: {name}")
    value = field.get("fieldId") or field.get("id")
    if not value:
        raise SystemExit(f"missing fieldId for field: {name}")
    return str(value)


def option_id(fields: dict[str, dict[str, Any]], field_name: str, option_name: str) -> str:
    field = fields.get(field_name)
    if not field:
        raise SystemExit(f"missing field: {field_name}")
    options = (field.get("config") or {}).get("options") or field.get("options") or []
    for option in options:
        if option.get("name") == option_name:
            option_value = option.get("id") or option.get("optionId")
            if option_value:
                return str(option_value)
    raise SystemExit(f"missing option id: {field_name}={option_name}")


def render_template(template_name: str, replacements: dict[str, str], out: Path) -> None:
    template = (ROOT / "templates" / template_name).read_text(encoding="utf-8")
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    leftovers = PLACEHOLDER_RE.findall(rendered)
    if leftovers:
        raise SystemExit(f"unreplaced placeholders in {template_name}: {', '.join(sorted(set(leftovers)))}")
    write_json(out, json.loads(rendered))


def extract_grid_view_id(table_get_response: Any) -> str:
    # table get 返回自带 views（键名是 type，不是 viewType），无需额外 view get 往返
    data = unwrap(table_get_response)
    views = first_value(data, "views") or []
    if not isinstance(views, list):
        raise SystemExit("cannot find views list in table get response")
    for view in views:
        if isinstance(view, dict) and (view.get("viewType") or view.get("type")) == "Grid":
            view_id = view.get("viewId") or view.get("id")
            if view_id:
                return str(view_id)
    raise SystemExit("cannot find Grid view in table get response")


def group_json(field_id_value: str) -> str:
    return "'" + json.dumps([{"fieldId": field_id_value, "direction": "asc"}], separators=(",", ":")) + "'"


def write_views_plan(path: Path, commands: list[str]) -> None:
    body = [
        "# agent-task-hub views foreground command plan",
        "",
        "所有 `dws` 命令必须由 agent 前台直接执行，不能放进 Python subprocess、nohup、后台或脚本批跑。",
        "执行顺序即下文编号顺序；`<看板viewId>` 取上一步 view create 返回的 viewId。",
        "",
    ]
    for index, command in enumerate(commands, start=1):
        body.extend([f"## {index}.", "", "```bash", command, "```", ""])
    path.write_text("\n".join(body), encoding="utf-8")


def delete_default_table_command(base_id: str, default_table_id: str) -> str:
    reason = shell_quote("删除建 Base 时自动生成的默认空数据表，避免打开台账先看到空表")
    return f"dws aitable table delete --base-id {base_id} --table-id {default_table_id} --yes --reason {reason} --format json"


def team_views(args: argparse.Namespace) -> None:
    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="agent-task-hub-views-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = extract_fields(read_json(args.table_get_json))
    grid_view_id = extract_grid_view_id(read_json(args.table_get_json))

    grid_visible_names = [
        "任务标题", "交接状态", "任务交接对象", "状态", "一句话摘要", "交接摘要",
        "产出物", "工作文件", "Agent类型", "任务ID", "通知文案", "创建人", "父记录",
    ]
    grid_config = {
        "visibleFieldIds": [field_id(fields, name) for name in grid_visible_names],
        "group": [{"fieldId": field_id(fields, "任务组"), "direction": "asc"}],
    }
    grid_config_arg = shell_quote(json.dumps(grid_config, ensure_ascii=False, separators=(",", ":")))

    commands = [
        (
            f"dws aitable view update --base-id {args.base_id} --table-id {args.table_id} "
            f"--view-id {grid_view_id} --config {grid_config_arg} --format json"
        ),
        (
            f"dws aitable view create --base-id {args.base_id} --table-id {args.table_id} "
            f"--view-type Kanban --name {shell_quote('交接看板')} --format json"
        ),
        (
            f"dws aitable view update group --base-id {args.base_id} --table-id {args.table_id} "
            f"--view-id <看板viewId> --json {group_json(field_id(fields, '交接状态'))} --format json"
        ),
    ]
    if args.default_table_id:
        commands.append(delete_default_table_command(args.base_id, args.default_table_id))

    plan_path = out_dir / "views-plan.md"
    write_views_plan(plan_path, commands)
    print(json.dumps(
        {
            "mode": "team-views",
            "outDir": str(out_dir),
            "viewsPlan": str(plan_path),
            "gridViewId": grid_view_id,
            "note": "本脚本只生成视图命令计划；执行仍由 agent 前台逐条跑 dws。",
        },
        ensure_ascii=False,
        indent=2,
    ))


def personal_views(args: argparse.Namespace) -> None:
    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="agent-task-hub-views-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = extract_fields(read_json(args.table_get_json))

    commands = [
        (
            f"dws aitable view create --base-id {args.base_id} --table-id {args.table_id} "
            f"--view-type Kanban --name {shell_quote('状态看板')} --format json"
        ),
        (
            f"dws aitable view update group --base-id {args.base_id} --table-id {args.table_id} "
            f"--view-id <看板viewId> --json {group_json(field_id(fields, '状态'))} --format json"
        ),
    ]
    if args.default_table_id:
        commands.append(delete_default_table_command(args.base_id, args.default_table_id))

    plan_path = out_dir / "views-plan.md"
    write_views_plan(plan_path, commands)
    print(json.dumps(
        {
            "mode": "personal-views",
            "outDir": str(out_dir),
            "viewsPlan": str(plan_path),
            "note": "本脚本只生成视图命令计划；执行仍由 agent 前台逐条跑 dws。",
        },
        ensure_ascii=False,
        indent=2,
    ))


def write_plan_markdown(path: Path, args: argparse.Namespace, fields_path: Path, parent_config_path: Path | None) -> None:
    fields_inline = shell_quote(json.dumps(TEAM_FIELDS, ensure_ascii=False, separators=(",", ":")))
    if args.table_id:
        parent_config = json.dumps({"linkedTableId": args.table_id, "multiple": False}, ensure_ascii=False, separators=(",", ":"))
    else:
        parent_config = '{"linkedTableId":"<TABLE_ID>","multiple":false}'
    parent_config_arg = f" --config {shell_quote(parent_config)}"
    commands = [
        f"dws aitable base create --name {shell_quote(args.name)} --format json",
        "dws aitable base get --base-id <BASE_ID> --format json",
        f"dws aitable table create --base-id <BASE_ID> --name {shell_quote(TASK_TABLE_NAME)} --fields {fields_inline} --format json",
        "# 复用已有表时：先 dws aitable table get 检查「父记录」是否已存在，已存在则跳过下一条 field create",
        "dws aitable field create --base-id <BASE_ID> --table-id <TABLE_ID> --name '父记录' --type unidirectionalLink" + parent_config_arg + " --format json",
        "dws aitable table get --base-id <BASE_ID> --table-id <TABLE_ID> --format json > <TABLE_GET_JSON>",
        f"python3 scripts/create-ledger.py team workflows --base-id <BASE_ID> --table-id <TABLE_ID> --table-get-json <TABLE_GET_JSON>{' --group-cid ' + shell_quote(args.group_cid) if args.group_cid else ''}",
        "dws aitable workflow list --base-id <BASE_ID> --format json",
        "dws aitable workflow create --base-id <BASE_ID> --dsl @<HANDOFF_DSL_JSON> --locale zh-CN --format json",
    ]
    if args.group_cid:
        commands.append("dws aitable workflow create --base-id <BASE_ID> --dsl @<CLAIM_DSL_JSON> --locale zh-CN --format json")
    commands.append(
        "python3 scripts/create-ledger.py team views --base-id <BASE_ID> --table-id <TABLE_ID>"
        " --table-get-json <TABLE_GET_JSON> --default-table-id <DEFAULT_TABLE_ID>"
    )
    commands.append(
        "# 逐条执行上一步生成的 views-plan.md：Grid 按任务组分组并重排列序 → 建交接看板 → 看板按交接状态分组 → 删默认空数据表"
    )
    if args.share_users:
        commands.append(f"dws drive permission add --node <BASE_ID> --users {shell_quote(args.share_users)} --role EDITOR --format json")
    commands.extend(
        [
            "dws aitable workflow list --base-id <BASE_ID> --format json",
            "dws aitable record query --base-id <BASE_ID> --table-id <TABLE_ID> --limit 1 --format json",
        ]
    )

    body = [
        "# agent-task-hub team ledger foreground command plan",
        "",
        "所有 `dws` 命令必须由 agent 前台直接执行，不能放进 Python subprocess、nohup、后台或脚本批跑。",
        "本文件只是确定性命令清单；执行时把 `<BASE_ID>`、`<TABLE_ID>`、`<TABLE_GET_JSON>` 和 DSL 路径替换为真实值。",
        "`<DEFAULT_TABLE_ID>` = base get 返回里名为「数据表」的默认空表 tableId；若 base 下没有名为「数据表」的表（例如复用已有 Base），team views 不传 `--default-table-id`。",
        "",
    ]
    for index, command in enumerate(commands, start=1):
        body.extend([f"## {index}.", "", "```bash", command, "```", ""])
    path.write_text("\n".join(body), encoding="utf-8")


def team_plan(args: argparse.Namespace) -> None:
    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="agent-task-hub-create-ledger-"))
    out_dir.mkdir(parents=True, exist_ok=True)

    fields_path = out_dir / "team-fields.json"
    write_json(fields_path, TEAM_FIELDS)

    parent_config_path: Path | None = None
    if args.table_id:
        parent_config_path = out_dir / "parent-field-config.json"
        write_json(parent_config_path, {"linkedTableId": args.table_id, "multiple": False})

    plan_path = out_dir / "foreground-dws-plan.md"
    write_plan_markdown(plan_path, args, fields_path, parent_config_path)

    print(json.dumps(
        {
            "mode": "team-plan",
            "outDir": str(out_dir),
            "baseName": args.name,
            "baseId": args.base_id or "",
            "tableId": args.table_id or "",
            "shareUsers": args.share_users or "",
            "groupCid": args.group_cid or "",
            "teamFieldsJson": str(fields_path),
            "parentFieldConfigJson": str(parent_config_path) if parent_config_path else "",
            "foregroundDwsPlan": str(plan_path),
            "note": "本脚本未调用 dws；请由 agent 按 plan.md 前台逐条执行 dws 命令。",
        },
        ensure_ascii=False,
        indent=2,
    ))


def team_workflows(args: argparse.Namespace) -> None:
    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="agent-task-hub-workflows-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = extract_fields(read_json(args.table_get_json))

    handoff_path = out_dir / "handoff-notify-workflow.json"
    render_template(
        "handoff-notify-workflow.json",
        {
            "<任务台账tableId>": args.table_id,
            "<任务交接对象fieldId>": field_id(fields, "任务交接对象"),
            "<通知文案fieldId>": field_id(fields, "通知文案"),
        },
        handoff_path,
    )

    claim_path = ""
    if args.group_cid:
        target = out_dir / "claim-notify-workflow.json"
        render_template(
            "claim-notify-workflow.json",
            {
                "<任务台账tableId>": args.table_id,
                "<通知文案fieldId>": field_id(fields, "通知文案"),
                "<交接状态fieldId>": field_id(fields, "交接状态"),
                "<待认领optionId>": option_id(fields, "交接状态", "待认领"),
                "<团队群cid>": args.group_cid,
            },
            target,
        )
        claim_path = str(target)

    print(json.dumps(
        {
            "mode": "team-workflows",
            "outDir": str(out_dir),
            "handoffDslJson": str(handoff_path),
            "claimDslJson": claim_path,
            "handoffCreateCommand": f"dws aitable workflow create --base-id {args.base_id} --dsl @{handoff_path} --locale zh-CN --format json",
            "claimCreateCommand": f"dws aitable workflow create --base-id {args.base_id} --dsl @{claim_path} --locale zh-CN --format json" if claim_path else "",
            "note": "本脚本只生成 DSL；workflow create 仍需 agent 前台直接执行 dws。",
        },
        ensure_ascii=False,
        indent=2,
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare agent-task-hub team ledger artifacts without calling dws")
    root = parser.add_subparsers(dest="mode", required=True)

    team = root.add_parser("team", help="Prepare team ledger creation artifacts")
    team_sub = team.add_subparsers(dest="team_mode", required=True)

    plan = team_sub.add_parser("plan", help="Generate fields JSON and foreground dws command plan")
    plan.add_argument("--name", default=DEFAULT_TEAM_BASE_NAME)
    plan.add_argument("--base-id", help="Existing baseId, if known")
    plan.add_argument("--table-id", help="Existing tableId, if known")
    plan.add_argument("--share-users", help="Comma-separated userIds to grant EDITOR")
    plan.add_argument("--group-cid", help="Optional group cid for pending-claim notification")
    plan.add_argument("--out-dir", type=Path)
    plan.set_defaults(func=team_plan)

    workflows = team_sub.add_parser("workflows", help="Generate workflow DSL from a table-get JSON response")
    workflows.add_argument("--base-id", required=True)
    workflows.add_argument("--table-id", required=True)
    workflows.add_argument("--table-get-json", required=True, type=Path)
    workflows.add_argument("--group-cid", help="Optional group cid for pending-claim notification")
    workflows.add_argument("--out-dir", type=Path)
    workflows.set_defaults(func=team_workflows)

    views = team_sub.add_parser("views", help="Generate view commands plan (grid group / handoff kanban / delete default table)")
    views.add_argument("--base-id", required=True)
    views.add_argument("--table-id", required=True)
    views.add_argument("--table-get-json", required=True, type=Path)
    views.add_argument("--default-table-id", help="Default empty 数据表 tableId from base get; omit to skip deletion")
    views.add_argument("--out-dir", type=Path)
    views.set_defaults(func=team_views)

    personal = root.add_parser("personal", help="Prepare personal ledger artifacts")
    personal_sub = personal.add_subparsers(dest="personal_mode", required=True)
    pviews = personal_sub.add_parser("views", help="Generate personal view commands plan (status kanban / delete default table)")
    pviews.add_argument("--base-id", required=True)
    pviews.add_argument("--table-id", required=True)
    pviews.add_argument("--table-get-json", required=True, type=Path)
    pviews.add_argument("--default-table-id", help="Default empty 数据表 tableId from base get; omit to skip deletion")
    pviews.add_argument("--out-dir", type=Path)
    pviews.set_defaults(func=personal_views)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
