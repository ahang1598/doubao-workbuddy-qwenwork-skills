"""汇总报表（需求文档 §2.5.2）。

由 Agent 按业务节奏一次性调用 :meth:`Summarizer.summary_template`：

1. 统计当日该模板的总派发数、已完成数、未完成数、完成率、平均耗时、
   未完成门店清单。
2. 把渲染好的报表通过 :class:`Messenger` 发送给 ``summary_receivers``
   （逗号分隔的 UserID 列表）解析出的每个 UserID。

> 本模块不内置 daemon / cron 判断；周期触发由 Agent 自行安排。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from scripts.domain import filters as F
from scripts.domain import schema as S
from scripts.domain.exceptions import DwsError, StoreTaskDispatcherError
from scripts.domain.records import extract_records, values_by_name
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache
from scripts.services.messenger import Messenger
from scripts.services.template_service import TemplateManager

logger = logging.getLogger(__name__)


@dataclass
class TemplateStats:
    """单个模板当日统计。"""

    template_id: str
    template_name: str
    total: int = 0
    completed: int = 0
    pending: int = 0
    completion_rate: float = 0.0
    avg_duration_seconds: Optional[float] = None
    pending_stores: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "total": self.total,
            "completed": self.completed,
            "pending": self.pending,
            "completion_rate": self.completion_rate,
            "avg_duration_seconds": self.avg_duration_seconds,
            "pending_stores": list(self.pending_stores),
        }


@dataclass
class SummarySendResult:
    template_id: str
    receivers: List[str] = field(default_factory=list)
    success: int = 0
    failed: int = 0
    stats: Optional[TemplateStats] = None


class Summarizer:
    """汇总报表执行器。"""

    def __init__(
        self,
        client: Optional[DwsClient] = None,
        cache: Optional[MappingCache] = None,
        base_id: Optional[str] = None,
        template_manager: Optional[TemplateManager] = None,
        messenger: Optional[Messenger] = None,
    ) -> None:
        self.client = client or DwsClient()
        self.cache = cache or MappingCache(client=self.client)
        self._base_id = base_id
        self.template_manager = template_manager or TemplateManager(
            client=self.client, cache=self.cache, base_id=base_id
        )
        self.messenger = messenger or Messenger(client=self.client)

    @property
    def base_id(self) -> str:
        bid = self._base_id or get_base_id()
        if not bid:
            raise StoreTaskDispatcherError("未初始化：config.json 中无 base_id")
        return bid

    def summary_template(
        self,
        template: Dict[str, Any],
        *,
        now: Optional[datetime] = None,
        output_format: str = "text",
    ) -> SummarySendResult:
        """对一个模板执行一次汇总并推送。

        无条件执行；周期触发由 Agent 按业务节奏完成，本方法不感知调度器。

        Args:
            template: 模板配置字典。
            now: 当前时间，默认取系统时间。
            output_format: 输出格式，可选 "text"、"html"。
                html 格式时仅记录日志提示使用子技能生成。
        """
        now = now or datetime.now()

        if output_format == "html":
            logger.info(
                "HTML 报告请使用子技能 report-generator 生成：\n"
                "  python3 skills/report-generator/scripts/cli.py generate-report"
                " <data.json> --fields <fields.json>"
            )
        tpl_id = template.get("template_id")
        if not tpl_id:
            raise StoreTaskDispatcherError("模板缺少 template_id")

        stats = self._build_stats(template, now)
        receivers = parse_receivers(template.get("summary_receivers", ""))
        result = SummarySendResult(
            template_id=tpl_id, receivers=receivers, stats=stats
        )
        if not receivers:
            logger.warning(
                "template %s 无 summary_receivers，跳过推送", tpl_id
            )
            return result

        content = format_summary_report(stats, now=now)
        for uid in receivers:
            try:
                self.messenger.send_summary_message(uid, content)
                result.success += 1
            except (DwsError, ValueError) as exc:
                logger.warning("汇总推送给 %s 失败: %s", uid, exc)
                result.failed += 1
        return result

    def _build_stats(
        self, template: Dict[str, Any], now: datetime
    ) -> TemplateStats:
        """从任务记录表查询当日任务，再遍历任务实例表按 task_id 过滤聚合。

        数据源迁移说明：
        - 旧实现依赖废弃的 INSTANCE_TABLE 固定表，已移除。
        - 新实现：从「任务记录」表查当日该模版的任务记录，
          再通过 instance_table_id（兼容旧字段名 task_table_id）读取对应的
          任务实例表，按记录存在即已提交的逻辑聚合统计。
        - 兼容历史表字段名：旧字段 task_table_id / 新字段 instance_table_id。
        """
        import json as _json
        tpl_id = template["template_id"]
        today_str = now.strftime("%Y-%m-%d")

        # 1. 查询任务记录表，找当日该模版的任务记录
        task_records: List[Dict[str, Any]] = []
        try:
            task_record_table_id = self.cache.get_table_id(
                self.base_id, S.TASK_RECORD_TABLE
            )
            tpl_field = self.cache.get_field_id(
                self.base_id, S.TASK_RECORD_TABLE, "template_id"
            )
            filters = F.and_(F.eq(tpl_field, tpl_id))
            payload = self.client.aitable_record_query(
                self.base_id, task_record_table_id, filters
            )
            for r in extract_records(payload):
                d = values_by_name(self.cache, self.base_id, S.TASK_RECORD_TABLE, r)
                # 只保留当日任务
                task_date = str(d.get("task_date") or "")
                if today_str in task_date:
                    task_records.append(d)
        except DwsError as exc:
            logger.warning("汇总查询任务记录失败 %s: %s", tpl_id, exc)

        # 2. 遍历每条任务记录，读取对应的任务实例表，按 submit_status 聚合
        total = 0
        completed = 0
        pending_stores: List[Dict[str, str]] = []

        for task_rec in task_records:
            task_id = task_rec.get("task_id", "")
            # 兼容新旧字段名
            instance_table_id = (
                task_rec.get("instance_table_id")
                or task_rec.get("task_table_id")
                or ""
            )
            if not instance_table_id:
                continue
            try:
                # 按 task_id 过滤（共享表场景下避免重复计数）
                field_map = {}
                try:
                    tbl_payload = self.client.aitable_table_get(
                        self.base_id, instance_table_id
                    )
                    from scripts.infrastructure.mapping_cache import _extract_fields
                    for f in _extract_fields(tbl_payload):
                        name = f.get("name") or f.get("fieldName")
                        fid = f.get("fieldId") or f.get("id")
                        if name and fid:
                            field_map[name] = fid
                except DwsError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "加载任务实例表 %s 字段映射失败，task_id 过滤将被跳过: %s",
                        instance_table_id, exc,
                    )

                # 构建过滤条件（有 task_id 字段时按 task_id 过滤）
                task_id_field = field_map.get("task_id")
                if task_id_field and task_id:
                    row_filters = F.and_(F.eq(task_id_field, task_id))
                else:
                    row_filters = None

                row_payload = self.client.aitable_record_query(
                    self.base_id, instance_table_id, row_filters
                )
                rows = extract_records(row_payload)
                # 纯 prefill 模式下记录存在即视为已提交
                record_count = len(rows)
                total += record_count
                completed += record_count
            except DwsError as exc:
                logger.warning(
                    "汇总读取任务实例表失败 task_id=%s instance_table_id=%s: %s",
                    task_id, instance_table_id, exc,
                )

        pending = total - completed
        rate = round(completed / total, 4) if total else 0.0

        return TemplateStats(
            template_id=tpl_id,
            template_name=template.get("name", "") or "",
            total=total,
            completed=completed,
            pending=pending,
            completion_rate=rate,
            avg_duration_seconds=None,  # 任务实例表无耗时字段，暂不统计
            pending_stores=pending_stores,
        )


def parse_receivers(raw: str) -> List[str]:
    """把逗号分隔的 UserID 字符串拆成列表，去重保序。"""
    if not raw:
        return []
    seen = set()
    out = []
    for piece in raw.split(","):
        uid = piece.strip()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        out.append(uid)
    return out


def format_summary_report(
    stats: TemplateStats, *, now: Optional[datetime] = None
) -> str:
    """按文档 §2.5.2 的报表示例格式渲染。"""
    now = now or datetime.now()
    lines = [
        "【任务汇总报表】",
        f"任务名称：{stats.template_name or stats.template_id}",
        f"统计时间：{now.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- 总派发数：{stats.total}",
        f"- 已完成数：{stats.completed}",
        f"- 未完成数：{stats.pending}",
        f"- 完成率：{stats.completion_rate * 100:.1f}%",
    ]
    if stats.avg_duration_seconds is not None:
        lines.append(
            f"- 平均完成耗时：{_format_duration(stats.avg_duration_seconds)}"
        )

    if stats.pending_stores:
        lines.append("")
        lines.append("未完成门店：")
        for i, s in enumerate(stats.pending_stores, start=1):
            mname = s.get("manager_name") or "-"
            lines.append(f"{i}. {s.get('store_name', '')} - {mname}")
    elif stats.total > 0:
        lines.append("")
        lines.append("✅ 所有门店均已完成上报。")
    return "\n".join(lines)


def _format_duration(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}秒"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}分{s}秒"
    h, m = divmod(m, 60)
    return f"{h}小时{m}分{s}秒"


__all__ = [
    "Summarizer",
    "TemplateStats",
    "SummarySendResult",
    "parse_receivers",
    "format_summary_report",
]
