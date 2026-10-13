"""通知服务 - 封装通知相关的核心逻辑。

从 Dispatcher 中提取的通知相关方法，负责：
- 单门店派发 (_dispatch_one)
- 通知记录的查询、写入、更新
- 通知明细的多维度查询
- 目标门店的通知派发 (notify_targets)
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

from scripts.services.dispatch_helpers import (
    DispatchSummary,
    _extract_records,
    _extract_record_id,
    _is_valid_share_link,
    _parse_notified_at,
    _prompt_resend_for_store,
    make_notification_id,
)
from scripts.domain import filters as F
from scripts.domain import schema as S
from scripts.domain.records import build_cell_value, extract_cell_value as _extract_cell_value, extract_url_value, extract_user_id, get_record_id, values_by_name
from scripts.domain.exceptions import DispatchError, DwsError
from scripts.domain.form_link_builder import build as build_form_link
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache
from scripts.utils.datetime_format import fmt_datetime

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务 - 封装通知相关的核心逻辑。

    从 Dispatcher 中提取的通知相关方法，负责：
    - 单门店派发 (_dispatch_one)
    - 通知记录的查询、写入、更新
    - 通知明细的多维度查询
    - 目标门店的通知派发 (notify_targets)
    """

    def __init__(
        self,
        client: DwsClient,
        cache: MappingCache,
        base_id: Optional[str] = None,
        table_manager=None,
        messenger=None,
        store_manager=None,
        task_record_service=None,
    ):
        self.client = client
        self.cache = cache
        self._base_id = base_id
        self.table_manager = table_manager
        self.messenger = messenger
        self.store_manager = store_manager
        self.task_record_service = task_record_service
        self._query_filled_store_ids_fn = None  # 由 Dispatcher Facade 注入

    @property
    def base_id(self) -> str:
        if self._base_id:
            return self._base_id
        return get_base_id()

    def query_filled_store_ids(self, instance_table_id: str) -> set:
        """由外部注入（通常由 Dispatcher Facade 设置）。"""
        if self._query_filled_store_ids_fn:
            return self._query_filled_store_ids_fn(instance_table_id)
        return set()

    def _resolve_targets(
        self,
        template: Dict[str, Any],
        *,
        target_store_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """解析目标门店列表（全量拉取）。

        派发通知必须拿到完整门店清单，因此走 list_all_stores（DWS --all
        自动翻页，内置 200ms 防抖）。若指定了 target_store_ids 则按 ID
        精确查询，不走分页。

        Args:
            template: 模板 dict。
            target_store_ids: 指定的门店 ID 列表（优先级高于 tags）。
            tags: 标签过滤条件。

        Returns:
            目标门店列表。
        """
        if target_store_ids:
            return self.store_manager.list_stores_by_ids(target_store_ids)
        return self.store_manager.list_all_stores(only_active=True, tags_any_of=tags)

    def _dispatch_one(
        self,
        template: Dict[str, Any],
        store: Dict[str, Any],
        task_id: str,
        instance_table_name: str,
        instance_table_id: str,
        notification_table_id: str,
        notif_field_map: Optional[Dict[str, str]] = None,
        form_base_link: str = "",
        now: Optional[datetime] = None,
        deadline_str: str = "",
        extra_info: str = "",
        message_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = now or datetime.now()
        tpl_id = template["template_id"]
        store_id = store.get("store_id")
        if not store_id:
            return {"store_id": None, "result": "failed", "reason": "门店缺少 store_id"}

        # user 类型：统一提取 userId（兼容 list/dict/str 等多种格式）
        manager_user_id = extract_user_id(store.get("manager"))
        # user 类型不含 name，通过通讯录反查姓名
        manager_name = ""
        if manager_user_id:
            manager_name = self.client.get_user_name(manager_user_id) or ""
        store_name = store.get("store_name", "")

        # 1. 生成通知 ID
        notification_id = make_notification_id(task_id, store_id)

        # 2. 生成 inspection_id（每行唯一主键）
        inspection_id = f"INSP_{task_id}_{store_id}"

        # 3. 为该门店生成带 prefill 参数的个性化表单链接
        personal_form_link = ""
        if form_base_link:
            try:
                personal_form_link = build_form_link(
                    form_base_link,
                    inspection_id=inspection_id,
                    task_id=task_id,
                    template_id=tpl_id,
                    store_id=store_id,
                    notification_id=notification_id,
                    extra={
                        "store_name": store_name,
                        S.FIELD_DISPLAY_DISPATCH_DATE: now.strftime("%Y-%m-%d"),
                    },
                )
            except Exception as exc:
                logger.warning(
                    "生成 prefill 表单链接失败 store=%s: %s", store_id, exc
                )
                personal_form_link = form_base_link  # 降级：使用无 prefill 的原始链接

        # 4. 预写通知明细（pending），记录派发开始
        pending_record_id = self._write_notification(
            notification_id=notification_id,
            task_id=task_id,
            instance_table_name=instance_table_name,
            template_id=tpl_id,
            store=store,
            notify_status="pending",
            form_link=personal_form_link,
            notification_table_id=notification_table_id,
            notif_field_map=notif_field_map,
            now=now,
        )

        # 5. 校验 userId（用于反查 openDingTalkId，发消息用 --open-dingtalk-id）
        if not manager_user_id:
            fail_reason = (
                f"门店 {store_id!r} 的 manager 字段缺少 userId，"
                f"请确认 manager 字段已正确关联钉钉用户"
            )
            if pending_record_id:
                self._update_notification_status(
                    record_id=pending_record_id,
                    notification_table_id=notification_table_id,
                    notif_field_map=notif_field_map,
                    notify_status="failed",
                    fail_reason=fail_reason,
                )
            else:
                self._write_notification(
                    notification_id=notification_id,
                    task_id=task_id,
                    instance_table_name=instance_table_name,
                    template_id=tpl_id,
                    store=store,
                    notify_status="failed",
                    fail_reason=fail_reason,
                    form_link=personal_form_link,
                    notification_table_id=notification_table_id,
                    notif_field_map=notif_field_map,
                    now=now,
                )
            return {
                "store_id": store_id,
                "result": "failed",
                "reason": fail_reason,
            }

        # 6. 发送钉钉单聊通知
        message_context = {
            "store_name": store_name,
            "manager": store.get("manager"),  # 传递完整 user 对象（含 userId）
            "manager_user_id": manager_user_id,
            "manager_name": manager_name,
            "task_id": task_id,
            "instance_table_name": instance_table_name,
            "task_date": now.strftime("%Y-%m-%d"),
            "dispatch_time": fmt_datetime(now),
            "form_link": personal_form_link,
            "deadline_str": deadline_str,
            # 透传额外信息：messenger 在渲染 {额外信息}/{extra_info} 占位符时使用，
            # 模板未含占位符且非空时会作为正文末尾的兜底信息追加。
            "task_table_name": instance_table_name,
            "extra_info": extra_info or "",
        }
        try:
            message_id = self.messenger.send_dispatch_message(
                message_context, template,
                message_override=message_override,
            )
        except (DwsError, ValueError) as exc:
            fail_reason = str(exc)
            if pending_record_id:
                self._update_notification_status(
                    record_id=pending_record_id,
                    notification_table_id=notification_table_id,
                    notif_field_map=notif_field_map,
                    notify_status="failed",
                    fail_reason=fail_reason,
                )
            else:
                self._write_notification(
                    notification_id=notification_id,
                    task_id=task_id,
                    instance_table_name=instance_table_name,
                    template_id=tpl_id,
                    store=store,
                    notify_status="failed",
                    fail_reason=fail_reason,
                    form_link=personal_form_link,
                    notification_table_id=notification_table_id,
                    notif_field_map=notif_field_map,
                    now=now,
                )
            return {
                "store_id": store_id,
                "result": "failed",
                "reason": fail_reason,
            }

        # 7. 更新通知明细为 sent（派发完成）
        if pending_record_id:
            self._update_notification_status(
                record_id=pending_record_id,
                notification_table_id=notification_table_id,
                notif_field_map=notif_field_map,
                notify_status="sent",
                message_id=message_id,
            )
        else:
            self._write_notification(
                notification_id=notification_id,
                task_id=task_id,
                instance_table_name=instance_table_name,
                template_id=tpl_id,
                store=store,
                notify_status="sent",
                message_id=message_id,
                form_link=personal_form_link,
                notification_table_id=notification_table_id,
                notif_field_map=notif_field_map,
                now=now,
            )
        return {
            "store_id": store_id,
            "task_id": task_id,
            "result": "success",
            "message_id": message_id,
            "form_link": personal_form_link,
        }

    # ------------------------------------------------------------------
    # 写入通知明细（动态通知明细表）
    # ------------------------------------------------------------------

    def _find_notification_record_by_id(
        self,
        notification_table_id: str,
        notif_field_map: Optional[Dict[str, str]],
        notification_id: str,
    ) -> Optional[tuple]:
        """按 ``notification_id`` 在通知表中查找已有记录。

        Returns:
            ``(record_id, send_count)`` 元组（``send_count`` 找不到字段时为 0）；
            未找到或查询失败返回 ``None``。

        设计目的：
            通知 ID 形如 ``NOTIF_{task_id}_{store_id}``，是「同一个人 + 同一个
            巡检任务」的天然唯一键。重发同一通知时，应原地 update + send_count++，
            而不是新建记录，避免一个人一个任务在通知明细表中出现多条记录。
        """
        if not notification_table_id or not notification_id:
            return None
        # 优先用传入的 fieldName→fieldId 映射，缺失时降级查表
        field_map = notif_field_map or self.table_manager._load_field_map(notification_table_id)
        notif_id_field = field_map.get("notification_id")
        send_count_field = field_map.get("send_count")
        if not notif_id_field:
            logger.warning(
                "_find_notification_record_by_id: 通知表 %s 缺少 notification_id 字段，"
                "无法去重",
                notification_table_id,
            )
            return None
        try:
            payload = self.client.aitable_record_query(
                self.base_id,
                notification_table_id,
                # 必须用 F.and_ 包裹，否则 dws 会静默忽略 filter，
                # 返回全表第一条导致通知去重失效并覆盖历史通知记录。
                F.and_(F.eq(notif_id_field, notification_id)),
                limit=1,
            )
        except DwsError as exc:
            logger.warning(
                "查询已有通知记录失败 notification_id=%s: %s",
                notification_id, exc,
            )
            return None
        records = _extract_records(payload)
        if not records:
            return None
        record = records[0]
        record_id = record.get("recordId") or record.get("id")
        if not record_id:
            return None
        # 提取当前 send_count（兼容 cells / fields 两种返回结构）
        current_count = 0
        cells = record.get("cells") or record.get("fields") or {}
        if send_count_field:
            value = _extract_cell_value(cells.get(send_count_field))
            try:
                current_count = int(value) if value not in (None, "") else 0
            except (TypeError, ValueError):
                current_count = 0
        return record_id, current_count

    def _write_notification(
        self,
        *,
        notification_id: str,
        task_id: str,
        instance_table_name: str,
        template_id: str,
        store: Dict[str, Any],
        notify_status: str,
        fail_reason: str = "",
        message_id: str = "",
        form_link: str = "",
        notification_table_id: str,
        notif_field_map: Optional[Dict[str, str]] = None,
        now: datetime,
    ) -> Optional[str]:
        """写入或更新通知明细，返回 recordId（失败返回 None）。

        去重策略（一个人 + 一个巡检任务只保留一条记录）：
        - 先按 ``notification_id`` 查询已有记录；
        - 若已存在 → 原地 update，``send_count`` 在原值上 +1；
        - 若不存在 → create 新记录，``send_count`` = 1。
        """
        # 1) 去重查询：按 notification_id 找已有记录
        existing = self._find_notification_record_by_id(
            notification_table_id, notif_field_map, notification_id
        )

        field_values: Dict[str, Any] = {
            "notification_id": notification_id,
            "task_id": task_id,
            "task_table_name": instance_table_name,  # 通知表字段名保持 task_table_name
            "template_id": template_id,
            "store_id": store.get("store_id", ""),
            "store_name": store.get("store_name", ""),
            "manager": store.get("manager"),
            "notify_status": notify_status,
            "notify_fail_reason": fail_reason,
            "message_id": message_id or "",
            "form_link": build_cell_value("url", form_link) if form_link else "",
            "dispatched_at": fmt_datetime(now),
            "last_contacted_at": fmt_datetime(now),
        }

        if existing:
            existing_record_id, current_count = existing
            field_values["send_count"] = (current_count or 0) + 1
            cells = self._build_notif_cells(
                field_values, notif_field_map, keep_empty=False
            )
            try:
                self.client.aitable_record_update(
                    self.base_id,
                    notification_table_id,
                    [{"recordId": existing_record_id, "cells": cells}],
                )
                logger.debug(
                    "通知记录原地更新 notification_id=%s send_count=%s status=%s",
                    notification_id, field_values["send_count"], notify_status,
                )
                return existing_record_id
            except DwsError as exc:
                logger.warning("更新已有通知明细失败: %s", exc)
                return None

        # 不存在 → 新建记录，send_count=1
        field_values["send_count"] = 1
        cells = self._build_notif_cells(
            field_values, notif_field_map, keep_empty=False
        )
        record = {"cells": cells}
        try:
            payload = self.client.aitable_record_create(
                self.base_id, notification_table_id, [record]
            )
            record_id = _extract_record_id(payload)
            if not record_id:
                logger.warning("写入通知明细成功但未返回 recordId，notification_id=%s", notification_id)
            return record_id
        except DwsError as exc:
            logger.warning("写入通知明细失败: %s", exc)
            return None

    @staticmethod
    def _build_notif_cells(
        field_values: Dict[str, Any],
        notif_field_map: Optional[Dict[str, str]],
        *,
        keep_empty: bool = False,
    ) -> Dict[str, Any]:
        """把 fieldName→value 字典转成 fieldId→value（用于通知表写入）。

        Args:
            field_values: fieldName -> value 字典。
            notif_field_map: fieldName -> fieldId 映射（建表时查出）。
            keep_empty: True 时保留空值（用于 update 显式清空字段）；
                False 时跳过空值（用于 create 避免传无意义字段）。
        """
        if notif_field_map:
            return {
                notif_field_map[k]: v
                for k, v in field_values.items()
                if (keep_empty or v != "") and k in notif_field_map
            }
        return {k: v for k, v in field_values.items() if keep_empty or v != ""}

    def _update_notification_status(
        self,
        *,
        record_id: str,
        notification_table_id: str,
        notif_field_map: Optional[Dict[str, str]] = None,
        notify_status: str,
        fail_reason: str = "",
        message_id: str = "",
    ) -> None:
        """更新通知明细记录的派发状态（pending → sent/failed）。

        Args:
            record_id: 通知明细记录的 recordId（由 _write_notification 返回）。
            notification_table_id: 动态通知明细表的 tableId。
            notif_field_map: fieldName->fieldId 映射（建表时查出）。
            notify_status: 新状态，``"sent"`` 或 ``"failed"``。
            fail_reason: 失败原因（仅 failed 时填写）。
            message_id: 消息 ID（仅 sent 时填写）。
        """
        field_values: Dict[str, Any] = {"notify_status": notify_status}
        if fail_reason:
            field_values["notify_fail_reason"] = fail_reason
        if message_id:
            field_values["message_id"] = message_id
        # 用传入的 fieldName->fieldId 映射
        if notif_field_map:
            cells = {
                notif_field_map[k]: v
                for k, v in field_values.items()
                if k in notif_field_map
            }
        else:
            cells = field_values
        try:
            self.client.aitable_record_update(
                self.base_id,
                notification_table_id,
                [{"recordId": record_id, "cells": cells}],
            )
        except DwsError as exc:
            logger.warning(
                "更新通知明细状态失败 record_id=%s status=%s: %s",
                record_id, notify_status, exc,
            )

    def query_notification_details(
        self,
        notification_table_id: str,
        instance_table_id: str,
        *,
        status_filter: Optional[str] = None,
        notified_from: Optional[str] = None,
        notified_to: Optional[str] = None,
        stayed_over_minutes: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """通知明细查询，支持多维度过滤（完全覆盖原 query_pending_notifications 能力）。

        Args:
            notification_table_id: 动态通知明细表的 tableId。
            instance_table_id: 动态任务表的 tableId（用于查"已填写"集合）。
            status_filter: 状态过滤：
                - "sent"：已派发（notify_status=sent，不论是否填写）
                - "filled"：已派发已填写（notify_status=sent 且 store_id 在已填写集合中）
                - "unfilled"：已派发未填写（等价于原 query_pending_notifications）
                - "failed"：失败（notify_status=failed）
                - None：不过滤状态
            notified_from: 通知时间下限，格式 "YYYY-MM-DD HH:mm"（含）。
            notified_to: 通知时间上限，格式 "YYYY-MM-DD HH:mm"（含）。
            stayed_over_minutes: 通知发出后超过 N 分钟仍未填写的记录（催办场景）。
                仅当 status_filter 为 None 或 "unfilled" 时生效。
            limit: 最多返回 N 条。

        Returns:
            通知明细列表，每项含 store_id / store_name / manager_name /
            notified_at / send_count / notification_id / notify_status 等字段。
        """
        if not notification_table_id:
            return []

        now_dt = datetime.now()

        # 1. 查"已填写"集合（sent/filled/unfilled 场景需要）
        filled_store_ids: set = set()
        if status_filter in (None, "sent", "filled", "unfilled"):
            filled_store_ids = self.query_filled_store_ids(instance_table_id)

        # 2. 加载通知表字段映射
        try:
            field_map = self.table_manager._load_field_map(notification_table_id)
        except DwsError:
            raise
        except Exception as exc:
            logger.warning("query_notification_details: 加载通知表字段映射失败: %s", exc)
            return []

        required_fields = ["store_id", "notify_status"]
        missing = [f for f in required_fields if not field_map.get(f)]
        if missing:
            logger.warning(
                "query_notification_details: 通知表 %s 缺少必需字段 %s",
                notification_table_id, missing,
            )
            return []

        # 3. 拉取通知表所有记录
        try:
            payload = self.client.aitable_record_query(
                self.base_id, notification_table_id
            )
        except DwsError:
            raise
        except Exception as exc:
            logger.warning("query_notification_details: 查询通知表失败: %s", exc)
            return []

        records = _extract_records(payload)
        results: List[Dict[str, Any]] = []

        for r in records:
            cells = r.get("cells") or r.get("fields") or {}

            def _val(name: str, _cells: dict = cells, _fmap: dict = field_map) -> Any:
                fid = _fmap.get(name)
                if not fid:
                    return None
                return _extract_cell_value(_cells.get(fid))

            notify_status = _val("notify_status") or ""
            store_id = _val("store_id")
            dispatched_at = _val("dispatched_at") or ""

            if not store_id:
                continue

            is_filled = str(store_id) in filled_store_ids

            # 状态过滤
            if status_filter == "sent":
                if notify_status != "sent":
                    continue
            elif status_filter == "filled":
                if notify_status != "sent" or not is_filled:
                    continue
            elif status_filter == "unfilled":
                if notify_status != "sent" or is_filled:
                    continue
            elif status_filter == "failed":
                if notify_status != "failed":
                    continue
            # None：不过滤

            # 通知时间范围过滤
            if notified_from and dispatched_at and dispatched_at[:16] < notified_from[:16]:
                continue
            if notified_to and dispatched_at and dispatched_at[:16] > notified_to[:16]:
                continue

            # stayed_over_minutes：通知发出后超过 N 分钟仍未填写
            if stayed_over_minutes is not None and stayed_over_minutes > 0:
                if notify_status != "sent" or is_filled:
                    continue
                if dispatched_at:
                    ts = _parse_notified_at(dispatched_at)
                    if ts is not None:
                        elapsed_minutes = (now_dt - ts).total_seconds() / 60
                        if elapsed_minutes < stayed_over_minutes:
                            continue
                    else:
                        continue
                else:
                    continue

            results.append({
                "store_id": str(store_id),
                "store_name": _val("store_name") or "",
                "manager": _val("manager"),
                "dispatched_at": dispatched_at,
                "send_count": _val("send_count") or 1,
                "notification_id": _val("notification_id") or "",
                "notify_status": notify_status,
                "notify_fail_reason": _val("notify_fail_reason") or "",
                "form_link": _val("form_link") or "",
                "is_filled": is_filled,
            })

        if limit is not None and limit > 0:
            results = results[:limit]
        return results

    def query_pending_notifications(
        self,
        task_id: str,
        notification_table_id: str,
        instance_table_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """查询某任务下『已通知未填写』的成员列表。

        Args:
            task_id: 任务 ID（用于过滤通知表中的记录）。
            notification_table_id: 动态通知明细表的 tableId。
            instance_table_id: 动态任务表的 tableId（用于查"已填写"集合）。

        Returns:
            未填写成员列表，每项含：store_id / store_name / manager_user_id /
            manager_name / notified_at / send_count / notification_id。
        """
        limit = min(limit, 100)
        if not notification_table_id:
            return []

        # 1. 查"已填写"集合
        filled_store_ids = self.query_filled_store_ids(instance_table_id)

        # 2. 加载通知表字段映射
        try:
            field_map = self.table_manager._load_field_map(notification_table_id)
        except Exception as exc:
            logger.warning(
                "query_pending_notifications: 加载通知表字段映射失败: %s", exc
            )
            return []

        required_fields = ["task_id", "store_id", "notify_status"]
        missing = [f for f in required_fields if not field_map.get(f)]
        if missing:
            logger.warning(
                "query_pending_notifications: 通知表 %s 缺少必需字段 %s",
                notification_table_id,
                missing,
            )
            return []

        # 3. 拉取通知表记录（带 limit 防护）
        try:
            payload = self.client.aitable_record_query(
                self.base_id, notification_table_id, limit=limit
            )
        except Exception as exc:
            logger.warning(
                "query_pending_notifications: 查询通知表失败: %s", exc
            )
            return []

        records = _extract_records(payload)
        pending: List[Dict[str, Any]] = []
        for r in records:
            cells = r.get("cells") or r.get("fields") or {}

            def _val(name: str) -> Any:
                fid = field_map.get(name)
                if not fid:
                    return None
                return _extract_cell_value(cells.get(fid))

            # 必须属于本任务
            if _val("task_id") != task_id:
                continue
            # 必须是已发送状态
            if _val("notify_status") != "sent":
                continue
            store_id = _val("store_id")
            if not store_id:
                continue
            # 已填写则跳过
            if str(store_id) in filled_store_ids:
                continue

            pending.append({
                "store_id": str(store_id),
                "store_name": _val("store_name") or "",
                "manager": _val("manager"),
                "dispatched_at": _val("dispatched_at") or "",
                "send_count": _val("send_count") or 1,
                "notification_id": _val("notification_id") or "",
            })
        return pending

    def query_recent_notified_store_ids(
        self,
        notification_table_id: str,
        cutoff_seconds: int,
        *,
        now: Optional[datetime] = None,
    ) -> set:
        """查询 notified_at 在 cutoff_seconds 秒内的 store_id 集合（用于冷却保护）。

        Args:
            notification_table_id: 动态通知明细表的 tableId。
            cutoff_seconds: 冷却窗口秒数；<=0 表示不启用冷却（直接返回空 set）。
            now: 当前时间，默认 datetime.now()。

        Returns:
            最近发过消息的门店 ID 集合，解析失败/查询失败时返回空 set。
        """
        if not notification_table_id or cutoff_seconds <= 0:
            return set()
        now = now or datetime.now()
        try:
            field_map = self.table_manager._load_field_map(notification_table_id)
            store_id_field = field_map.get("store_id")
            last_contacted_at_field = field_map.get("last_contacted_at")
            if not store_id_field or not last_contacted_at_field:
                logger.warning(
                    "query_recent_notified_store_ids: 通知表 %s 缺少 store_id / last_contacted_at 字段",
                    notification_table_id,
                )
                return set()

            payload = self.client.aitable_record_query(
                self.base_id, notification_table_id
            )
            records = _extract_records(payload)
            recent: set = set()
            for r in records:
                cells = r.get("cells") or r.get("fields") or {}
                store_val = _extract_cell_value(cells.get(store_id_field))
                notified_val = _extract_cell_value(cells.get(last_contacted_at_field))
                if not store_val or not notified_val:
                    continue
                # 兼容 ISO 字符串 / 时间戳 / 带毫秒等多种格式
                ts = _parse_notified_at(notified_val)
                if ts is None:
                    continue
                delta = (now - ts).total_seconds()
                if 0 <= delta <= cutoff_seconds:
                    recent.add(str(store_val))
            return recent
        except DwsError:
            raise
        except Exception as exc:
            logger.warning("query_recent_notified_store_ids 失败: %s", exc)
            return set()

    def query_dispatched_store_ids(
        self, notification_table_id: str, task_id: str = ""
    ) -> set:
        """查询某通知明细表中已成功派发（notify_status=sent）的门店 ID 集合。

        通知表可能被同一模版当天多个 task 复用，因此必须按 task_id 过滤，
        只返回当前 task 已通知的门店，避免跨 task 的通知状态污染。

        通过 ``_load_field_map`` 拿到 ``store_id`` 和 ``notify_status`` 的精确
        fieldId，再按 fieldId 读取每条记录的 cell 值，避免老版本"遍历 cells +
        startswith 字符串匹配"带来的脏匹配问题（任何 ``STORE_`` 开头的字符串都
        会被误判为 store_id）。

        Args:
            notification_table_id: 动态通知明细表的 tableId。
            task_id: 当前任务 ID，用于过滤只属于本次任务的通知记录。
                     为空时不过滤（兼容旧调用，但不推荐）。

        Returns:
            已派发门店 ID 的 set，查询失败或字段缺失返回空 set。
        """
        if not notification_table_id:
            return set()
        try:
            field_map = self.table_manager._load_field_map(notification_table_id)
            store_id_field = field_map.get("store_id")
            notify_status_field = field_map.get("notify_status")
            task_id_field = field_map.get("task_id")
            if not store_id_field or not notify_status_field:
                logger.warning(
                    "query_dispatched_store_ids: 通知表 %s 缺少 store_id / notify_status 字段",
                    notification_table_id,
                )
                return set()

            # 按 task_id 过滤，避免通知表被多个 task 复用时跨 task 污染
            filters = None
            if task_id and task_id_field:
                filters = F.and_(F.eq(task_id_field, task_id))
            elif task_id and not task_id_field:
                logger.warning(
                    "query_dispatched_store_ids: 通知表 %s 缺少 task_id 字段，"
                    "无法按 task_id 过滤，可能返回跨 task 的脏数据",
                    notification_table_id,
                )

            payload = self.client.aitable_record_query(
                self.base_id, notification_table_id, filters
            )
            records = _extract_records(payload)
            sent_store_ids = set()
            cross_task_skipped = 0
            for r in records:
                cells = r.get("cells") or r.get("fields") or {}
                # Python 端二次校验 task_id（防御 dws filter 被静默忽略导致
                # 返回跨 task 脏数据，参见 _find_task_by_id 的同类防御模式）
                if task_id and task_id_field:
                    record_task_id = _extract_cell_value(cells.get(task_id_field))
                    if record_task_id != task_id:
                        cross_task_skipped += 1
                        continue
                status_val = _extract_cell_value(cells.get(notify_status_field))
                store_val = _extract_cell_value(cells.get(store_id_field))
                if status_val == "sent" and store_val:
                    sent_store_ids.add(store_val)
            # 监控计数器：仅在 DWS Filter 返回与 Python 端过滤结果不一致时打印 warning
            if cross_task_skipped:
                logger.warning(
                    "query_dispatched_store_ids: dws filter 疑似失效，"
                    "Python 端二次过滤剔除了 %d 条不属于 task %s 的记录"
                    "（总返回 %d 条，有效 %d 条）",
                    cross_task_skipped, task_id,
                    len(records), len(sent_store_ids),
                )
            return sent_store_ids
        except DwsError:
            raise
        except Exception as exc:
            logger.warning("query_dispatched_store_ids 失败: %s", exc)
            return set()

    def notify_targets(
        self,
        template: Dict[str, Any],
        task_context: Dict[str, Any],
        *,
        duplicate_strategy: str = "ask",
        only_pending: bool = False,
        cooldown_seconds: Optional[int] = None,
        scope_desc: Optional[str] = None,
        target_store_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        now: Optional[datetime] = None,
        extra_info: Optional[str] = None,
        message_override: Optional[str] = None,
    ) -> DispatchSummary:
        """阶段 2：基于已有 task_context 向目标门店派发通知。

        本方法不会创建任何表，所有表 ID / form_url 都从 task_context 读取。
        如果 task_context 缺少 form_url（用户跳过了分享），会拒绝派发并把所有
        目标门店标记为 failed，避免发垃圾消息。

        Args:
            template: 模板 dict。
            task_context: 阶段 1 ``ensure_task`` 的返回值。
            duplicate_strategy: 已通知门店的处理策略：

                - ``"ask"``：逐店询问用户（y 重发 / N 跳过 / a 全部重发 /
                  s 全部跳过 / q 退出）。在批处理 / 无人值守场景请勿使用。
                - ``"resend"``：所有已通知门店都直接重发
                - ``"skip"``：所有已通知门店都跳过
            only_pending: 仅向"已通知未填写"的成员重发。启用时：
                - 自动用 query_pending_notifications 计算目标
                - 自动忽略 ``duplicate_strategy``（强制 resend，因为目标
                  本身就是已通知未填写）
            cooldown_seconds: 冷却保护窗口（秒）。``last_contacted_at`` 在该窗口
                内的门店将被标记为 ``skipped (reason=cooldown_active)``，
                避免短时间内重复骚扰。``None`` 或 ``<=0`` 表示不启用。
            scope_desc: 派发范围描述（如"华东大区"），派发完成后自动追加到
                任务记录的 dispatch_log 字段（JSON 数组）。传 None 则不追加。
            now: 派发时间，默认当前时间。

        Returns:
            DispatchSummary，包含 success / failed / skipped 统计。
        """
        now = now or datetime.now()
        tpl_id = template.get("template_id", "")
        task_id = task_context.get("task_id", "")
        instance_table_name = task_context.get("instance_table_name", "")
        instance_table_id = task_context.get("instance_table_id", "")
        notification_table_name = task_context.get("notification_table_name", "")
        notification_table_id = task_context.get("notification_table_id", "")
        notif_field_map = task_context.get("notif_field_map") or {}
        form_url = task_context.get("form_url", "")
        form_view_id = task_context.get("form_view_id", "")
        # extra_info：调用方显式传入则覆盖，否则沿用 task_context 中已经合并好的值
        effective_extra_info = (
            extra_info
            if extra_info is not None
            else (task_context.get("extra_info") or "")
        )

        # 1. 解析目标门店
        targets = self._resolve_targets(template, target_store_ids=target_store_ids, tags=tags)

        # 1.1 only_pending：仅向"已通知未填写"的成员重发
        # 该模式下强制 duplicate_strategy=resend（已通知是天然条件，无需再问）
        if only_pending:
            duplicate_strategy = "resend"
            pending_members = self.query_pending_notifications(
                task_id=task_id,
                notification_table_id=notification_table_id,
                instance_table_id=instance_table_id,
            )
            pending_ids = {m["store_id"] for m in pending_members}
            targets = [t for t in targets if t.get("store_id") in pending_ids]
            logger.info(
                "notify_targets only_pending: 任务 %s 共 %d 个已通知未填写成员，"
                "本次重发目标 %d 个",
                task_id,
                len(pending_ids),
                len(targets),
            )

        # 1.2 冷却保护：剔除 notified_at 在窗口内的门店
        cooldown_hits: set = set()
        if cooldown_seconds and cooldown_seconds > 0 and notification_table_id:
            cooldown_hits = self.query_recent_notified_store_ids(
                notification_table_id, cooldown_seconds, now=now
            )
            if cooldown_hits:
                logger.info(
                    "notify_targets 冷却保护：任务 %s 有 %d 个门店在 %ds 冷却窗口内",
                    task_id, len(cooldown_hits), cooldown_seconds,
                )

        summary = DispatchSummary(
            task_id=task_id,
            instance_table_name=instance_table_name,
            template_id=tpl_id,
            total=len(targets),
        )

        # 2. form_url 缺失 → 拒绝派发，全部标记为 failed
        if not _is_valid_share_link(form_url):
            logger.error(
                "notify_targets 拒绝派发 task_id=%s：缺少合法的 form_url，"
                "请先调用 ensure_task 完成分享链接配置",
                task_id,
            )
            for store in targets:
                summary.details.append({
                    "store_id": store.get("store_id"),
                    "result": "failed",
                    "reason": "form_url 未配置（请先到表单视图分享并粘贴合法链接）",
                })
                summary.failed += 1
            return summary

        # 3. 加载已通知集合（仅 ask / skip 策略需要）
        dispatched_ids: set = set()
        if duplicate_strategy in ("ask", "skip") and notification_table_id:
            dispatched_ids = self.query_dispatched_store_ids(notification_table_id, task_id)

        # 4. 逐店派发（含重复通知策略）
        current_strategy = duplicate_strategy  # 局部副本，ask 中可能升级为 a/s
        user_quit = False

        # 4.1 预处理：根据策略和冷却保护筛选需要派发的门店
        stores_to_dispatch: List[Dict[str, Any]] = []
        skipped_before_dispatch: List[Dict[str, Any]] = []

        for store in targets:
            if user_quit:
                skipped_before_dispatch.append({
                    "store": store,
                    "reason": "用户中止派发",
                })
                continue

            store_id = store.get("store_id")

            # 冷却保护：上次通知在 cooldown_seconds 窗口内 → 静默跳过
            if store_id in cooldown_hits:
                skipped_before_dispatch.append({
                    "store": store,
                    "reason": "cooldown_active",
                })
                continue

            already_sent = store_id in dispatched_ids

            # 决定本店是否要发
            should_send = True
            if already_sent:
                if current_strategy == "skip":
                    should_send = False
                elif current_strategy == "resend":
                    should_send = True
                else:  # ask - 需要用户交互，不能并发，单独处理
                    choice = _prompt_resend_for_store(store)
                    if choice == "y":
                        should_send = True
                    elif choice == "n":
                        should_send = False
                    elif choice == "a":
                        current_strategy = "resend"
                        should_send = True
                    elif choice == "s":
                        current_strategy = "skip"
                        should_send = False
                    elif choice == "q":
                        user_quit = True
                        should_send = False

            if not should_send:
                skipped_before_dispatch.append({
                    "store": store,
                    "reason": "已通知，按策略跳过",
                })
                continue

            stores_to_dispatch.append(store)

        # 4.2 记录预处理阶段的跳过结果
        for item in skipped_before_dispatch:
            summary.skipped += 1
            summary.details.append({
                "store_id": item["store"].get("store_id"),
                "result": "skipped",
                "reason": item["reason"],
            })

        # 4.3 并发派发（仅当 strategy != ask 时才能并发）
        # ask 策略已在上面逐店处理完毕，stores_to_dispatch 为空
        if stores_to_dispatch:
            def _dispatch_single_store(store: Dict[str, Any]) -> Dict[str, Any]:
                """单个门店的派发逻辑，用于并发执行。"""
                try:
                    detail = self._dispatch_one(
                        template=template,
                        store=store,
                        task_id=task_id,
                        instance_table_name=instance_table_name,
                        instance_table_id=instance_table_id,
                        notification_table_id=notification_table_id,
                        notif_field_map=notif_field_map,
                        form_base_link=form_url,
                        now=now,
                        deadline_str=task_context.get("deadline_str", ""),
                        extra_info=effective_extra_info,
                        message_override=message_override,
                    )
                    return detail
                except Exception as exc:
                    # 异常隔离：单个门店失败不影响其他门店
                    logger.error(
                        "notify_targets 并发派发异常 store=%s: %s",
                        store.get("store_id"), exc, exc_info=True,
                    )
                    return {
                        "store_id": store.get("store_id"),
                        "result": "failed",
                        "reason": f"并发派发异常: {str(exc)}",
                    }

            # 使用 ThreadPoolExecutor 并发发送，max_workers=3 避免钉钉限流
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_store = {
                    executor.submit(_dispatch_single_store, store): store
                    for store in stores_to_dispatch
                }
                for future in as_completed(future_to_store):
                    detail = future.result()
                    summary.details.append(detail)
                    status = detail.get("result")
                    if status == "success":
                        summary.success += 1
                    elif status == "skipped":
                        summary.skipped += 1
                    else:
                        summary.failed += 1

        # 5. 派发结束：回写任务记录的最终统计
        if instance_table_id and self.task_record_service:
            # 仅当调用方显式传入 extra_info 时才持久化（保留任务记录中已有值）
            self.task_record_service.upsert_task_record(
                task_id=task_id,
                template=template,
                instance_table_name=instance_table_name,
                instance_table_id=instance_table_id,
                notification_table_name=notification_table_name,
                notification_table_id=notification_table_id,
                summary=summary,
                now=now,
                form_url=form_url,
                form_view_id=form_view_id,
                extra_info=extra_info,
            )

        return summary
