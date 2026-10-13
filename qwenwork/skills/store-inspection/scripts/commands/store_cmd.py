"""``store`` 命令族：门店清单 CRUD。

子命令：``add / update / delete / get / list``
"""

from __future__ import annotations

import argparse

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.utils.output import apply_list_options, err, ok, print_json, split_csv, warn


@register_command
class StoreCommand(BaseCommand):
    name = "store"
    help = "门店清单维护"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="subcommand", required=True)

        sa = sub.add_parser("add", help="新增门店")
        sa.add_argument("--store-id", default=None, help="门店 ID，不传则自动生成 S_{yyyyMMddHHmmss}_{rand4}")
        sa.add_argument("--store-name", required=True)
        sa.add_argument("--manager", required=True, help="店长 userId（user 类型，AI 表格自动关联钉钉用户信息）")
        sa.add_argument("--tags", default=None, help="逗号分隔的标签")
        sa.add_argument(
            "--status", default="active", choices=["active", "inactive"]
        )
        sa.set_defaults(func=_add)

        su = sub.add_parser("update", help="按 store_id 更新门店字段")
        su.add_argument("--store-id", required=True)
        su.add_argument("--store-name", default=None)
        su.add_argument("--manager", default=None, help="店长 userId（user 类型）")
        su.add_argument("--tags", default=None)
        su.add_argument(
            "--status", default=None, choices=["active", "inactive"]
        )
        su.set_defaults(func=_update)

        sd = sub.add_parser("delete", help="按 store_id 删除门店")
        sd.add_argument("--store-id", required=True)
        self.add_yes_flag(sd, "二次确认（高危操作必填）")
        sd.set_defaults(func=_delete)

        sg = sub.add_parser("get", help="按 store_id 查询单门店")
        sg.add_argument("--store-id", required=True)
        sg.set_defaults(func=_get)

        sl = sub.add_parser("list", help="列出门店")
        sl.add_argument("--only-active", action="store_true", help="仅列 active")
        sl.add_argument("--tags", default=None, help="按标签过滤（逗号分隔，任一命中）")
        sl.add_argument(
            "--limit",
            type=int,
            default=10,
            metavar="N",
            help="最多返回 N 条记录（默认 10，上限 100），防止数据量过大",
        )
        sl.add_argument(
            "--sort-by",
            default="created_at",
            metavar="FIELD",
            help="排序字段名（默认 created_at）",
        )
        sl.add_argument(
            "--sort-order",
            default="desc",
            choices=["asc", "desc"],
            help="排序方向：asc 升序 / desc 降序（默认 desc，最新在前）",
        )
        sl.add_argument(
            "--fields",
            default=None,
            metavar="FIELD1,FIELD2,...",
            help="仅返回指定字段（逗号分隔），如 store_id,store_name,status",
        )
        sl.add_argument(
            "--count-only",
            action="store_true",
            help="仅返回符合条件的总数 {\"total\": N}，不返回数据体",
        )
        sl.set_defaults(func=_list)

        sb = sub.add_parser("batch-add", help="批量新增门店（支持 JSON 参数或文件导入）")
        sb_group = sb.add_mutually_exclusive_group(required=True)
        sb_group.add_argument(
            "--json",
            default=None,
            help='JSON 数组字符串，如 \'[{"store_name":"店1","manager":"userId1"}]\'',
        )
        sb_group.add_argument(
            "--file",
            default=None,
            help="JSON 文件路径（文件内容为门店数组）",
        )
        sb.set_defaults(func=_batch_add)

        su = sub.add_parser("url", help="输出门店清单表的 AI 表格链接，供用户直接在表格中管理门店")
        su.set_defaults(func=_url)


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------


def _add(args, ctx: AppContext) -> int:
    rid = ctx.store_manager.add_store(
        store_name=args.store_name,
        manager=args.manager,
        store_id=args.store_id,
        tags=split_csv(args.tags),
        status=args.status,
    )
    ok(f"门店已新增: {args.store_id or '(自动生成)'} (recordId={rid})")
    return 0


def _update(args, ctx: AppContext) -> int:
    fields = {}
    if args.store_name is not None:
        fields["store_name"] = args.store_name
    if args.manager is not None:
        fields["manager"] = args.manager
    if args.tags is not None:
        fields["tags"] = split_csv(args.tags) or []
    if args.status is not None:
        fields["status"] = args.status
    rid = ctx.store_manager.update_store(args.store_id, **fields)
    ok(f"门店已更新: {args.store_id} (recordId={rid})")
    return 0


def _delete(args, ctx: AppContext) -> int:
    if not args.yes:
        err("删除门店是高危操作，请追加 --yes 二次确认。")
        return 2
    deleted = ctx.store_manager.delete_store(args.store_id)
    if deleted:
        ok(f"门店已删除: {args.store_id}")
        return 0
    warn(f"门店不存在: {args.store_id}")
    return 1


def _get(args, ctx: AppContext) -> int:
    d = ctx.store_manager.get_store(args.store_id)
    if not d:
        err(f"门店不存在: {args.store_id}")
        return 1
    print_json(d)
    return 0


def _list(args, ctx: AppContext) -> int:
    stores = ctx.store_manager.list_stores(
        only_active=args.only_active,
        tags_any_of=split_csv(args.tags),
        limit=args.limit,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
    )
    result = apply_list_options(
        stores,
        fields=getattr(args, "fields", None),
        count_only=getattr(args, "count_only", False),
        limit=args.limit,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
    )
    print_json(result)
    return 0


def _batch_add(args, ctx: AppContext) -> int:
    import json
    from pathlib import Path

    if args.json:
        try:
            stores = json.loads(args.json)
        except json.JSONDecodeError as exc:
            err(f"--json 解析失败: {exc}")
            return 2
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            err(f"文件不存在: {args.file}")
            return 2
        try:
            stores = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            err(f"文件读取/解析失败: {exc}")
            return 2
    else:
        err("请指定 --json 或 --file")
        return 2

    if not isinstance(stores, list):
        err("输入数据必须是 JSON 数组")
        return 2

    result = ctx.store_manager.batch_add_stores(stores)
    ok(f"批量新增完成: 成功 {result['success']}，跳过 {result['skipped']}，失败 {result['failed']}")
    if result["errors"]:
        print_json({"errors": result["errors"]})
    return 0


def _url(args, ctx: AppContext) -> int:
    table_url = ctx.store_manager.get_store_table_url()
    ok("门店清单表格地址如下，可直接在 AI 表格中管理门店：")
    print(table_url)
    print(
        "\n⚠️ 注意事项：\n"
        "  1. 请确保必填字段完整：store_id、store_name、manager（member 类型，选择钉钉用户）\n"
        "  2. store_id 一旦填写禁止修改（主键约束）\n"
        "  3. status 仅允许 active / inactive 两个值\n"
        "  4. tags 为多选字段，可自由添加标签"
    )
    return 0
