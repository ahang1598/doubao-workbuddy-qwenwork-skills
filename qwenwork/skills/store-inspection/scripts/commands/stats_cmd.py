"""``stats`` 命令族：模板使用 / 任务完成 / 门店表现 / 时间趋势统计。

子命令：``template / task / store / trend``

通用时间范围参数：
- ``--days N``：最近 N 天（与 ``--from/--to`` 互斥；默认 7）
- ``--from YYYY-MM-DD --to YYYY-MM-DD``：指定日期范围（含起含止）
- ``--template-id``：可选，按单个模板钻取

输出：
- 标题 + 纯文本表格（可读性优先，便于人工查看）
- 退出码：0 正常；2 参数冲突
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import Optional, Tuple

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.utils.output import err, print_table

DEFAULT_DAYS = 7
_DATE_FMT = "%Y-%m-%d"


def _add_range_args(parser: argparse.ArgumentParser) -> None:
    """给子命令统一加 ``--days / --from / --to / --template-id``。"""
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help=f"最近 N 天（与 --from/--to 互斥，默认 {DEFAULT_DAYS}）",
    )
    parser.add_argument(
        "--from",
        dest="date_from",
        default=None,
        help="起始日期 YYYY-MM-DD（含）",
    )
    parser.add_argument(
        "--to",
        dest="date_to",
        default=None,
        help="截止日期 YYYY-MM-DD（含），默认今天",
    )
    parser.add_argument(
        "--template-id",
        default=None,
        help="可选，按单个模板钻取",
    )


def _resolve_range(args, *, now: Optional[datetime] = None) -> Tuple[datetime, datetime, str]:
    """把 ``--days / --from / --to`` 解析成 ``(since, until, label)``。

    Args:
        args: argparse Namespace（必须含 ``days / date_from / date_to``）
        now:  当前时间（测试用，默认 ``datetime.now()``）

    Returns:
        ``since``: 起始时间（含），``until``: 截止时间（不含；按"截止日期 +1 天"算）
        ``label``: ``"YYYY-MM-DD 至 YYYY-MM-DD"`` 形式，用于表格标题
    """
    now = now or datetime.now()

    has_days = args.days is not None
    has_from = bool(args.date_from)
    has_to = bool(args.date_to)

    if has_days and (has_from or has_to):
        raise ValueError("--days 与 --from/--to 互斥，请只用一种方式指定时间范围")

    if has_from or has_to:
        # 显式日期模式
        try:
            until_date = (
                datetime.strptime(args.date_to, _DATE_FMT)
                if has_to
                else datetime(now.year, now.month, now.day)
            )
        except ValueError:
            raise ValueError(f"--to 日期格式应为 YYYY-MM-DD，收到: {args.date_to!r}")
        if has_from:
            try:
                since = datetime.strptime(args.date_from, _DATE_FMT)
            except ValueError:
                raise ValueError(
                    f"--from 日期格式应为 YYYY-MM-DD，收到: {args.date_from!r}"
                )
        else:
            # 只给了 --to：默认起点为 7 天前
            since = until_date - timedelta(days=DEFAULT_DAYS - 1)
        until = until_date + timedelta(days=1)  # exclusive
        label = f"{since.strftime(_DATE_FMT)} 至 {until_date.strftime(_DATE_FMT)}"
        if since >= until:
            raise ValueError(
                f"起始日期必须早于截止日期：since={since.date()}, until={until_date.date()}"
            )
        return since, until, label

    days = args.days if has_days else DEFAULT_DAYS
    if days <= 0:
        raise ValueError(f"--days 必须 > 0，收到: {days}")
    until_date = datetime(now.year, now.month, now.day)
    since = until_date - timedelta(days=days - 1)
    until = until_date + timedelta(days=1)
    label = f"{since.strftime(_DATE_FMT)} 至 {until_date.strftime(_DATE_FMT)}（最近 {days} 天）"
    return since, until, label


def _fmt_rate(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _fmt_duration(seconds) -> str:
    if seconds is None:
        return "-"
    s = int(seconds)
    if s < 60:
        return f"{s}秒"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}分{s}秒"
    h, m = divmod(m, 60)
    return f"{h}时{m}分"


@register_command
class StatsCommand(BaseCommand):
    name = "stats"
    help = "统计：模板使用 / 任务完成 / 门店表现 / 时间趋势"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.description = (
            "统计 4 个子命令对应的典型业务问题：\n"
            "  template — 哪些模板用得最多？哪些模板沉睡了？\n"
            "  task     — 整体任务完成率？哪些模板拖后腿？平均填写耗时？\n"
            "  store    — 哪家门店最积极？哪家垫底？\n"
            "  trend    — 派发量 / 完成率随时间怎么变？\n"
            "通用时间窗：--days N 或 --from/--to（互斥）；可选 --template-id 钻取。"
        )
        sub = parser.add_subparsers(dest="subcommand", required=True)

        st = sub.add_parser(
            "template",
            help="模板使用排行 + 活跃率",
            description="回答「哪个模板用得多 / 哪些模板沉睡了」；按 dispatch_count 倒序。",
        )
        _add_range_args(st)
        st.add_argument("--limit", type=int, default=20)
        st.set_defaults(func=_template)

        sk = sub.add_parser(
            "task",
            help="任务完成率与平均耗时",
            description=(
                "回答「整体完成率怎么样 / 哪些模板拖后腿 / 平均填写要多久」；"
                "末尾附『全局完成率』汇总。"
            ),
        )
        _add_range_args(sk)
        sk.set_defaults(func=_task)

        ss = sub.add_parser(
            "store",
            help="门店表现排行",
            description="回答「哪家门店最积极 / 哪家垫底」；默认按完成率倒序，可改 --sort-by avg_duration。",
        )
        _add_range_args(ss)
        ss.add_argument("--limit", type=int, default=20)
        ss.add_argument(
            "--sort-by",
            choices=["completion_rate", "avg_duration"],
            default="completion_rate",
        )
        ss.set_defaults(func=_store)

        tr = sub.add_parser(
            "trend",
            help="时间趋势",
            description="回答「派发量 / 完成率最近怎么变」；按天或按周分桶（--granularity）。",
        )
        _add_range_args(tr)
        tr.add_argument(
            "--granularity",
            choices=["day", "week"],
            default="day",
        )
        tr.set_defaults(func=_trend)


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------

def _template(args, ctx: AppContext) -> int:
    try:
        since, until, label = _resolve_range(args)
    except ValueError as exc:
        err(str(exc))
        return 2

    rows_data = ctx.stats_service.template_usage_ranking(
        since=since, until=until, template_id=args.template_id, limit=args.limit
    )
    rows = [
        [
            r.template_id,
            r.template_name,
            r.status,
            r.dispatch_count,
            r.last_dispatch_at or "-",
        ]
        for r in rows_data
    ]
    print_table(
        ["template_id", "name", "status", "dispatch", "last_dispatch_at"],
        rows,
        title=f"模板使用排行（{label}）",
    )

    rate = ctx.stats_service.template_active_rate(since=since, until=until)
    print()
    print(
        f"模板活跃率：启用 {rate.enabled}/{rate.total} = {_fmt_rate(rate.enabled_rate)}；"
        f"窗口内有派发 {rate.active_in_range}/{rate.total} = {_fmt_rate(rate.active_rate)}"
    )
    return 0


def _task(args, ctx: AppContext) -> int:
    try:
        since, until, label = _resolve_range(args)
    except ValueError as exc:
        err(str(exc))
        return 2

    metrics = ctx.stats_service.task_completion_metrics(
        since=since, until=until, template_id=args.template_id
    )
    rows = [
        [
            m.template_id,
            m.template_name,
            m.dispatch_count,
            m.total_targets,
            m.submitted,
            m.pending,
            _fmt_rate(m.completion_rate),
            _fmt_duration(m.avg_duration_seconds),
        ]
        for m in metrics
    ]
    print_table(
        [
            "template_id",
            "name",
            "dispatch",
            "targets",
            "submitted",
            "pending",
            "completion",
            "avg_duration",
        ],
        rows,
        title=f"任务完成率与平均耗时（{label}）",
    )

    if metrics:
        total_targets = sum(m.total_targets for m in metrics)
        total_submitted = sum(m.submitted for m in metrics)
        total_rate = total_submitted / total_targets if total_targets else 0.0
        print()
        print(
            f"全局完成率：{total_submitted}/{total_targets} = {_fmt_rate(total_rate)}"
        )
    return 0


def _store(args, ctx: AppContext) -> int:
    try:
        since, until, label = _resolve_range(args)
    except ValueError as exc:
        err(str(exc))
        return 2

    metrics = ctx.stats_service.store_ranking(
        since=since,
        until=until,
        template_id=args.template_id,
        limit=args.limit,
        sort_by=args.sort_by,
    )
    rows = [
        [
            m.store_id,
            m.store_name,
            m.total_assigned,
            m.submitted,
            _fmt_rate(m.completion_rate),
            _fmt_duration(m.avg_duration_seconds),
        ]
        for m in metrics
    ]
    print_table(
        ["store_id", "store_name", "assigned", "submitted", "completion", "avg_duration"],
        rows,
        title=f"门店表现排行（{label}，按 {args.sort_by}）",
    )
    return 0


def _trend(args, ctx: AppContext) -> int:
    try:
        since, until, label = _resolve_range(args)
    except ValueError as exc:
        err(str(exc))
        return 2

    points = ctx.stats_service.trend(
        since=since,
        until=until,
        template_id=args.template_id,
        granularity=args.granularity,
    )
    rows = [
        [
            p.bucket,
            p.dispatch_count,
            p.total_targets,
            p.submitted,
            _fmt_rate(p.completion_rate),
        ]
        for p in points
    ]
    print_table(
        ["bucket", "dispatch", "targets", "submitted", "completion"],
        rows,
        title=f"时间趋势（{label}，按 {args.granularity}）",
    )
    return 0
