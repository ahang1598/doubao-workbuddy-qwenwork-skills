"""再次提醒模块（需求文档 §2.4.4）。

由 Agent 按业务节奏一次性调用 :meth:`Reminder.remind_template`：
- 查询当日 ``dispatch_status='dispatched'`` AND ``completion_status='pending'``
  AND ``remind_status='pending'`` 的实例。
- 逐条发送提醒消息。
- 成功则回写 ``remind_status='reminded'`` / ``remind_message_id`` /
  ``remind_time_actual``。

> 本模块不内置 daemon / cron 判断；周期触发由 Agent 自行安排。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from scripts.domain import filters as F
from scripts.domain.records import extract_url_value
from scripts.domain import schema as S
from scripts.domain.exceptions import DwsError, StoreTaskDispatcherError
from scripts.domain.records import (
    cells_by_name,
    extract_records,
    get_record_id,
    values_by_name,
)
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache
from scripts.services.messenger import Messenger
from scripts.services.template_service import TemplateManager
from scripts.utils.datetime_format import fmt_datetime

logger = logging.getLogger(__name__)


@dataclass
class RemindSummary:
    template_id: str
    total: int = 0
    success: int = 0
    failed: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "details": self.details,
        }


class Reminder:
    """再次提醒执行器。"""

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

    def _instance_table_id(self) -> str:
        return self.cache.get_table_id(self.base_id, S.TASK_RECORD_TABLE)

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------

    def remind_template(
        self,
        template: Dict[str, Any],
        *,
        now: Optional[datetime] = None,
    ) -> RemindSummary:
        """对一个模板执行一次提醒扫描。

        无条件执行；周期触发由 Agent 按业务节奏完成，本方法不感知调度器。
        """
        now = now or datetime.now()
        tpl_id = template.get("template_id")
        if not tpl_id:
            raise StoreTaskDispatcherError("模板缺少 template_id")

        summary = RemindSummary(template_id=tpl_id)
        instances = self._query_pending_instances(tpl_id, now)
        summary.total = len(instances)

        for inst_record in instances:
            detail = self._remind_one(template, inst_record, now)
            summary.details.append(detail)
            if detail.get("result") == "success":
                summary.success += 1
            else:
                summary.failed += 1
        return summary

    # ------------------------------------------------------------------
    # 实例查询 + 提醒
    # ------------------------------------------------------------------

    def _query_pending_instances(
        self, template_id: str, now: datetime
    ) -> List[Dict[str, Any]]:
        """查询当日待提醒的实例。"""
        # 当日 0 点（采用本地时区，与 dispatch_time 写入一致）
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tpl_field = self.cache.get_field_id(
            self.base_id, S.TASK_RECORD_TABLE, "template_id"
        )
        dispatch_field = self.cache.get_field_id(
            self.base_id, S.TASK_RECORD_TABLE, "dispatch_status"
        )
        completion_field = self.cache.get_field_id(
            self.base_id, S.TASK_RECORD_TABLE, "completion_status"
        )
        remind_field = self.cache.get_field_id(
            self.base_id, S.TASK_RECORD_TABLE, "remind_status"
        )
        dispatch_time_field = self.cache.get_field_id(
            self.base_id, S.TASK_RECORD_TABLE, "dispatch_time"
        )

        filters = F.and_(
            F.eq(tpl_field, template_id),
            F.eq(dispatch_field, "dispatched"),
            F.eq(completion_field, "pending"),
            F.eq(remind_field, "pending"),
            F.after(
                dispatch_time_field,
                day_start.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        try:
            result = self.client.aitable_record_query(
                self.base_id, self._instance_table_id(), filters
            )
        except DwsError as exc:
            # 查询失败不能静默返回空列表，否则调用方会误认为"无待提醒实例"
            # 而跳过整个提醒流程，导致所有提醒静默丢失。
            raise StoreTaskDispatcherError(
                f"查询待提醒实例失败，提醒流程已中止: {exc}"
            ) from exc
        return extract_records(result)

    def _remind_one(
        self,
        template: Dict[str, Any],
        inst_record: Dict[str, Any],
        now: datetime,
    ) -> Dict[str, Any]:
        record_id = get_record_id(inst_record)
        values = values_by_name(
            self.cache, self.base_id, S.TASK_RECORD_TABLE, inst_record
        )
        instance_id = values.get("instance_id")
        manager_user_id = values.get("manager_user_id")
        form_link = _extract_url_value(values.get("form_link"))
        # 额外信息：派发时通过 --extra-info 持久化在任务记录的 extra_info 字段，
        # 提醒消息复用同一份内容（确保派发与提醒展示一致）。
        extra_info = values.get("extra_info") or ""
        # 已发送的提醒次数：本次提醒后 +1 写回；标题在 ≥2 时加 `【第N次提醒】` 前缀
        try:
            previous_round = int(values.get("reminder_round") or 0)
        except (TypeError, ValueError):
            previous_round = 0
        current_round = previous_round + 1

        detail: Dict[str, Any] = {
            "instance_id": instance_id,
            "store_id": values.get("store_id"),
            "result": "failed",
            "reminder_round": current_round,
        }

        if not manager_user_id:
            detail["reason"] = "缺少 manager_user_id"
            return detail

        instance_for_msg = {
            "instance_id": instance_id,
            "manager_user_id": manager_user_id,
            "manager_name": values.get("manager_name", ""),
            "store_name": values.get("store_name", ""),
            "form_link": form_link,
            "extra_info": extra_info,
        }
        try:
            message_id = self.messenger.send_remind_message(
                instance_for_msg,
                template,
                reminder_round=current_round,
            )
        except (DwsError, ValueError) as exc:
            detail["reason"] = f"消息发送失败: {exc}"
            return detail

        # 回写 remind_status=reminded + 累加后的 reminder_round
        update_values = {
            "remind_status": "reminded",
            "remind_message_id": message_id or "",
            "remind_time_actual": fmt_datetime(now),
            "reminder_round": current_round,
        }
        cells = cells_by_name(
            self.cache, self.base_id, S.TASK_RECORD_TABLE, update_values
        )
        try:
            self.client.aitable_record_update(
                self.base_id,
                self._instance_table_id(),
                [{"recordId": record_id, "cells": cells}],
            )
        except DwsError as exc:
            detail["reason"] = f"实例回写失败: {exc}"
            return detail

        detail["result"] = "success"
        detail["message_id"] = message_id
        return detail


# extract_url_value 已迁移到 scripts.domain.records，此处保留别名以兼容内部调用
_extract_url_value = extract_url_value


__all__ = ["Reminder", "RemindSummary"]
