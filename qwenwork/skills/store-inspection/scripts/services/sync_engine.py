"""同步引擎（新架构）。

新架构下，店长直接通过表单更新动态任务表，不再需要「巡店上报」中间表。
本模块职责简化为：
- 定期扫描通知明细表，对「已发送但超时未提交」的门店发送提醒
- 提供手动触发提醒的接口

如需统计分析，由 summary 模块负责查询动态任务表。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from scripts.domain import schema as S
from scripts.domain.exceptions import DwsError, StoreTaskDispatcherError
from scripts.domain.records import extract_records, values_by_name
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache
from scripts.services.messenger import Messenger

logger = logging.getLogger(__name__)


@dataclass
class RemindSummary:
    """提醒汇总结果。"""

    scanned: int = 0
    reminded: int = 0
    skipped: int = 0
    failed: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scanned": self.scanned,
            "reminded": self.reminded,
            "skipped": self.skipped,
            "failed": self.failed,
            "details": self.details,
        }


class SyncEngine:
    """同步引擎：负责提醒超时未提交的门店。"""

    def __init__(
        self,
        client: Optional[DwsClient] = None,
        cache: Optional[MappingCache] = None,
        base_id: Optional[str] = None,
        messenger: Optional[Messenger] = None,
    ) -> None:
        self.client = client or DwsClient()
        self.cache = cache or MappingCache(client=self.client)
        self._base_id = base_id
        self.messenger = messenger or Messenger(client=self.client)

    @property
    def base_id(self) -> str:
        bid = self._base_id or get_base_id()
        if not bid:
            raise StoreTaskDispatcherError("未初始化：config.json 中无 base_id")
        return bid

    def _notification_table_id(self) -> str:
        return self.cache.get_table_id(self.base_id, S.NOTIFICATION_TABLE)

    def remind_pending(
        self,
        task_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> RemindSummary:
        """对通知明细表中 notify_status=sent 且 remind_status=pending 的记录发送提醒。

        Args:
            task_id: 指定任务 ID，为空则扫描所有待提醒记录。
            now: 当前时间，默认 datetime.now()。
        """
        now = now or datetime.now()
        summary = RemindSummary()

        try:
            result = self.client.aitable_record_query(
                self.base_id, self._notification_table_id(), filters=None
            )
        except DwsError:
            raise
        except Exception as exc:
            logger.error("查询通知明细失败: %s", exc)
            return summary

        records = extract_records(result)
        for record in records:
            row = values_by_name(
                self.cache, self.base_id, S.NOTIFICATION_TABLE, record
            )
            summary.scanned += 1

            if task_id and row.get("task_id") != task_id:
                summary.skipped += 1
                continue
            if row.get("notify_status") != "sent":
                summary.skipped += 1
                continue
            if row.get("remind_status") not in ("pending", None, ""):
                summary.skipped += 1
                continue

            manager_user_id = row.get("manager_user_id")
            if not manager_user_id:
                summary.skipped += 1
                continue

            try:
                self.messenger.send_remind_message(row)
                summary.reminded += 1
                summary.details.append({
                    "store_id": row.get("store_id"),
                    "store_name": row.get("store_name"),
                    "result": "reminded",
                })
            except Exception as exc:
                logger.warning("发送提醒失败 store=%s: %s", row.get("store_id"), exc)
                summary.failed += 1
                summary.details.append({
                    "store_id": row.get("store_id"),
                    "store_name": row.get("store_name"),
                    "result": "failed",
                    "reason": str(exc),
                })

        return summary


__all__ = ["SyncEngine", "RemindSummary"]
