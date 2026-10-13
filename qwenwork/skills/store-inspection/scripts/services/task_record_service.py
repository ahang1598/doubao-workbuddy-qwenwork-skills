"""任务记录服务（TaskRecordService）。

从 Dispatcher 中提取任务记录相关的 CRUD 方法，封装为独立的服务类。
负责任务记录表的 upsert、查询和更新操作。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from scripts.domain import filters as F
from scripts.domain import schema as S
from scripts.domain.records import build_cell_value, cells_by_name, extract_cell_value as _extract_cell_value, extract_records, extract_url_value as _extract_url_value, get_record_id, values_by_name
from scripts.domain.exceptions import DwsError, StoreTaskDispatcherError
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache
from scripts.utils.datetime_format import fmt_date, fmt_datetime
from scripts.services.dispatch_helpers import (
    DispatchSummary,
    _extract_records,
    _find_table_id_by_name,
    _extract_record_id,
    _resolve_task_record_status,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TaskRecordService
# ---------------------------------------------------------------------------

class TaskRecordService:
    """任务记录服务，提供任务记录表的 CRUD 操作。

    职责：
    - 向任务记录固定表 upsert 记录
    - 查询当天同一模版的任务列表
    - 通用任务查询（支持多维度过滤）
    - 更新任务记录字段
    """

    def __init__(
        self,
        client: DwsClient,
        cache: MappingCache,
        base_id: Optional[str] = None,
        table_manager=None,
    ):
        """初始化任务记录服务。

        Args:
            client: DWS 客户端。
            cache: 字段映射缓存。
            base_id: Base ID，不传则从配置读取。
            table_manager: 表管理器，用于获取任务记录表 ID 和字段映射。
        """
        self.client = client
        self.cache = cache
        self._base_id = base_id
        self.table_manager = table_manager

    @property
    def base_id(self) -> str:
        """获取 AI表格 ID。"""
        if self._base_id:
            return self._base_id
        return get_base_id()

    # -----------------------------------------------------------------------
    # 核心方法
    # -----------------------------------------------------------------------

    def upsert_task_record(
        self,
        *,
        task_id: str,
        template: Dict[str, Any],
        instance_table_name: str,
        instance_table_id: str,
        notification_table_name: str,
        notification_table_id: str,
        summary: DispatchSummary,
        now: datetime,
        form_url: str = "",
        form_view_id: str = "",
        deadline_value: Optional[str] = None,
        status_override: Optional[str] = None,
        extra_info: Optional[str] = None,
        reminder_round: Optional[int] = None,
    ) -> None:
        """向「任务记录」固定表 upsert 一条派发元数据记录。

        策略：按 ``task_id`` 查询；存在则 update，不存在则 create。
        这样支持「先建占位记录，后续多次回填表 ID / form_url / 统计」的流水。

        Args:
            task_id: 任务唯一 ID，作为 upsert 的判断依据。
            template: 模版 dict。
            instance_table_name / instance_table_id: 巡检表元信息（可能为空，后续回填）。
            notification_table_name / notification_table_id: 通知表元信息（可能为空）。
            summary: 派发汇总（占位写入时 total/success/failed 都是 0）。
            now: 时间戳。
            form_url: 表单分享链接（首次派发会持久化到任务记录，复用时直接读取）。
            form_view_id: 表单视图 ID（用于复用时拼接引导链接）。
            status_override: 显式指定 status；不传时按 summary 推断。
            extra_info: 额外信息（写入 ``extra_info`` 字段）。``None`` 表示
                本次 upsert 不更新该字段（避免占位 upsert 把已写入的值覆盖为空）。
            reminder_round: 已发送的提醒次数（写入 ``reminder_round`` 字段）。
                ``None`` 表示本次 upsert 不更新该字段。

        失败时记录 error 日志，不阻断主流程；但 ``DwsError`` 例外——
        dws CLI 返回的错误（含权限错误）必须向上抛，由上层统一处理。
        """
        tpl_id = template.get("template_id", "")
        tpl_name = template.get("name", "")
        status = status_override or _resolve_task_record_status(summary)

        field_values: Dict[str, Any] = {
            "task_id": task_id,
            "template_id": tpl_id,
            "template_name": tpl_name,
            "instance_table_name": instance_table_name,
            "instance_table_id": instance_table_id,
            "notification_table_name": notification_table_name,
            "notification_table_id": notification_table_id,
            "form_url": (
                {"text": "填写链接", "link": form_url} if form_url else ""
            ),
            "form_view_id": form_view_id,
            "task_date": now.strftime("%Y-%m-%d"),
            "target_store_count": summary.total,
            "success_count": summary.success,
            "failed_count": summary.failed,
            "status": status,
        }
        if deadline_value is not None:
            field_values["deadline"] = deadline_value
        # 仅在调用方显式传入时才写入 extra_info / reminder_round，避免
        # 占位 upsert 把任务记录里已经持久化的值覆盖为空。
        if extra_info is not None:
            field_values["extra_info"] = extra_info
        if reminder_round is not None:
            field_values["reminder_round"] = reminder_round

        try:
            task_record_table_id = self.table_manager._get_task_record_table_id()
            if not task_record_table_id:
                logger.error(
                    "upsert 任务记录失败：在 AI表格 %s 中未找到表 %r，"
                    "任务 %s 的派发汇总记录将丢失，请运行 check --repair 补充缺失的表",
                    self.base_id,
                    S.TASK_RECORD_TABLE,
                    task_id,
                )
                return

            # 通过 cache 将 fieldName 转为 fieldId（写记录用）
            try:
                cells = cells_by_name(
                    self.cache, self.base_id, S.TASK_RECORD_TABLE, field_values
                )
            except Exception as map_exc:
                logger.warning("任务记录字段映射失败，降级用 fieldName 写入: %s", map_exc)
                cells = field_values

            # 按 task_id 查询是否已有记录（决定 update 还是 create）
            existing_record_id: Optional[str] = None
            try:
                task_id_field_id = self.cache.get_field_id(
                    self.base_id, S.TASK_RECORD_TABLE, "task_id"
                )
                payload = self.client.aitable_record_query(
                    self.base_id,
                    task_record_table_id,
                    # 必须用 F.and_ 包裹，否则 dws 会静默忽略 filter，
                    # 返回全表第一条导致 upsert 误判为已存在并覆盖历史记录。
                    F.and_(F.eq(task_id_field_id, task_id)),
                    limit=1,
                )
                existing = extract_records(payload)
                if existing:
                    existing_record_id = get_record_id(existing[0])
            except DwsError:
                raise
            except Exception as query_exc:
                logger.warning(
                    "查询任务记录是否已存在失败 task_id=%s: %s（跳过 upsert，避免误判为新建产生重复记录）",
                    task_id, query_exc,
                )
                return

            if existing_record_id:
                self.client.aitable_record_update(
                    self.base_id,
                    task_record_table_id,
                    [{"recordId": existing_record_id, "cells": cells}],
                )
                logger.debug("task record updated: %s", task_id)
            else:
                self.client.aitable_record_create(
                    self.base_id, task_record_table_id, [{"cells": cells}]
                )
                logger.debug("task record created: %s", task_id)
        except DwsError:
            raise
        except Exception as exc:
            logger.error(
                "upsert 任务记录失败 task_id=%s: %s", task_id, exc, exc_info=True
            )

    # 兼容老调用名，保留为别名（直接走 upsert 语义）
    write_task_record = upsert_task_record

    def query_today_tasks(
        self, template_id: str, today: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """查询任务记录表中当天同一模版的任务列表（按发起时间倒序）。

        Args:
            template_id: 模版 ID。
            today: 日期字符串 ``"YYYY-MM-DD"``，默认当天。

        Returns:
            任务记录列表（每项为 fields dict），最新的在前。空列表表示当天未派发。
        """
        limit = min(limit, 100)
        today = today or fmt_date()
        try:
            base_payload = self.client.aitable_base_get(self.base_id)
            task_record_table_id = _find_table_id_by_name(
                base_payload, S.TASK_RECORD_TABLE
            )
            if not task_record_table_id:
                logger.warning("query_today_tasks: 未找到任务记录表")
                return []

            # 在服务端按 template_id 精确过滤，避免随任务记录积累全表拉取
            # 触发 aitable TIMEOUT_ERROR（曾导致下游 _find_task_by_id /
            # query_today_tasks 全部失败，最终用户看到"未找到任务记录"误报）。
            # filter 必须用 F.and_ 包裹，否则 dws 静默忽略等同于全表查询。
            try:
                template_id_field_id = self.cache.get_field_id(
                    self.base_id, S.TASK_RECORD_TABLE, "template_id"
                )
                payload = self.client.aitable_record_query(
                    self.base_id,
                    task_record_table_id,
                    F.and_(F.eq(template_id_field_id, template_id)),
                    limit=limit,
                )
            except DwsError:
                raise
            except Exception as filter_exc:
                # filter 构造失败（如字段不存在），降级为全表查询保证可用性
                logger.warning(
                    "query_today_tasks: 按 template_id filter 查询失败，"
                    "降级为全表扫描: %s", filter_exc,
                )
                payload = self.client.aitable_record_query(
                    self.base_id, task_record_table_id, limit=limit
                )

            records = _extract_records(payload)
            results = []
            for r in records:
                # cells 以 fieldId 为 key，需翻译回 fieldName 才能按名称过滤
                fields = values_by_name(
                    self.cache, self.base_id, S.TASK_RECORD_TABLE, r
                )
                # 服务端已 filter，但保留 Python 端二次校验以兼容降级路径
                if fields.get("template_id") != template_id:
                    continue
                task_date = fields.get("task_date", "")
                if not task_date.startswith(today):
                    continue
                # url 类型字段读出来是 dict，统一解包为字符串
                for url_field in S.TASK_RECORD_URL_FIELD_NAMES:
                    if url_field in fields:
                        fields[url_field] = _extract_url_value(fields[url_field])
                results.append({
                    "record_id": r.get("recordId") or r.get("id", ""),
                    **fields,
                })
            # 按 task_date 倒序（最新在前）
            results.sort(key=lambda x: x.get("task_date", ""), reverse=True)
            return results
        except DwsError:
            raise
        except Exception as exc:
            logger.error(
                "query_today_tasks 失败 template_id=%s today=%s: %s，"
                "返回空列表可能导致重复派发检测失效",
                template_id, today, exc,
            )
            return []

    def query_tasks(
        self,
        template_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """通用任务查询，支持多维度过滤。

        Args:
            template_id: 按模版 ID 过滤（精确匹配）。
            status: 按状态过滤（"进行中" / "已完成" / "部分失败" / "已禁用"）。
            date_from: 按发起日期过滤，格式 "YYYY-MM-DD"（含）。
            date_to: 按发起日期过滤，格式 "YYYY-MM-DD"（含）。
            limit: 最多返回 N 条（按 task_date 倒序后截断）。

        Returns:
            任务记录列表，按 task_date 倒序排列。
        """
        try:
            task_record_table_id = self.table_manager._get_task_record_table_id()
            if not task_record_table_id:
                logger.warning("query_tasks: 未找到任务记录表")
                return []

            # 尝试在服务端按 template_id 过滤，减少全表拉取
            if template_id:
                try:
                    template_id_field_id = self.cache.get_field_id(
                        self.base_id, S.TASK_RECORD_TABLE, "template_id"
                    )
                    payload = self.client.aitable_record_query(
                        self.base_id,
                        task_record_table_id,
                        F.and_(F.eq(template_id_field_id, template_id)),
                    )
                except Exception as filter_exc:
                    logger.warning(
                        "query_tasks: 按 template_id filter 查询失败，降级为全表扫描: %s",
                        filter_exc,
                    )
                    payload = self.client.aitable_record_query(
                        self.base_id, task_record_table_id
                    )
            else:
                payload = self.client.aitable_record_query(
                    self.base_id, task_record_table_id
                )

            records = _extract_records(payload)
            results: List[Dict[str, Any]] = []
            for r in records:
                fields = values_by_name(
                    self.cache, self.base_id, S.TASK_RECORD_TABLE, r
                )
                # Python 端二次过滤（兼容降级路径）
                if template_id and fields.get("template_id") != template_id:
                    continue
                if status and fields.get("status") != status:
                    continue
                task_date = fields.get("task_date", "")
                if date_from and task_date and task_date[:10] < date_from:
                    continue
                if date_to and task_date and task_date[:10] > date_to:
                    continue
                # url 类型字段读出来是 dict，统一解包为字符串
                for url_field in S.TASK_RECORD_URL_FIELD_NAMES:
                    if url_field in fields:
                        fields[url_field] = _extract_url_value(fields[url_field])
                results.append({
                    "record_id": r.get("recordId") or r.get("id", ""),
                    **fields,
                })

            # 按 task_date 倒序（最新在前）
            results.sort(key=lambda x: x.get("task_date", ""), reverse=True)
            if limit is not None and limit > 0:
                results = results[:limit]
            return results
        except Exception as exc:
            logger.warning("query_tasks 失败: %s", exc)
            return []

    def update_task(
        self,
        task_id: str,
        *,
        form_url: Optional[str] = None,
        status: Optional[str] = None,
        scope_desc: Optional[str] = None,
        store_count: int = 0,
        success_count: int = 0,
        now: Optional[datetime] = None,
    ) -> bool:
        """更新任务记录的字段。

        Args:
            task_id: 任务 ID（必须已存在）。
            form_url: 更新表单链接（传 None 则不更新）。
            status: 更新任务状态（传 None 则不更新）。
            scope_desc: 派发范围描述，不为空时追加到 dispatch_log JSON 数组。
            store_count: 本次派发门店数（配合 scope_desc 使用）。
            success_count: 本次派发成功数（配合 scope_desc 使用）。
            now: 时间戳，默认当前时间。

        Returns:
            True 表示更新成功，False 表示失败（任务不存在或写入异常）。
        """
        now = now or datetime.now()
        try:
            task_record_table_id = self.table_manager._get_task_record_table_id()
            if not task_record_table_id:
                logger.warning("update_task: 未找到任务记录表")
                return False

            # 查找任务记录
            task_id_field_id = self.cache.get_field_id(
                self.base_id, S.TASK_RECORD_TABLE, "task_id"
            )
            payload = self.client.aitable_record_query(
                self.base_id,
                task_record_table_id,
                F.and_(F.eq(task_id_field_id, task_id)),
                limit=1,
            )
            records = extract_records(payload)
            if not records:
                logger.warning("update_task: 未找到任务记录 task_id=%s", task_id)
                return False

            record = records[0]
            record_id = get_record_id(record)
            if not record_id:
                logger.warning("update_task: 任务记录缺少 recordId task_id=%s", task_id)
                return False

            existing_fields = values_by_name(
                self.cache, self.base_id, S.TASK_RECORD_TABLE, record
            )

            field_values: Dict[str, Any] = {}

            # 更新 form_url
            if form_url is not None:
                field_values["form_url"] = (
                    {"text": "填写链接", "link": form_url} if form_url else ""
                )

            # 更新 status
            if status is not None:
                field_values["status"] = status

            # 追加 dispatch_log
            if scope_desc:
                existing_log_raw = existing_fields.get("dispatch_log") or ""
                # dispatch_log 是 richText，值可能是 str 或 dict
                if isinstance(existing_log_raw, dict):
                    existing_log_raw = existing_log_raw.get("text") or ""
                try:
                    log_list = json.loads(existing_log_raw) if existing_log_raw.strip() else []
                    if not isinstance(log_list, list):
                        log_list = []
                except (json.JSONDecodeError, AttributeError):
                    log_list = []
                log_list.append({
                    "time": fmt_datetime(now),
                    "scope_desc": scope_desc,
                    "store_count": store_count,
                    "success_count": success_count,
                })
                field_values["dispatch_log"] = build_cell_value(
                    "richText", json.dumps(log_list, ensure_ascii=False)
                )

            if not field_values:
                logger.debug("update_task: 无需更新任何字段 task_id=%s", task_id)
                return True

            try:
                cells = cells_by_name(
                    self.cache, self.base_id, S.TASK_RECORD_TABLE, field_values
                )
            except Exception as map_exc:
                logger.warning("update_task: 字段映射失败，降级用 fieldName 写入: %s", map_exc)
                cells = field_values

            self.client.aitable_record_update(
                self.base_id,
                task_record_table_id,
                [{"recordId": record_id, "cells": cells}],
            )
            logger.debug(
                "update_task: 任务记录已更新 task_id=%s fields=%s",
                task_id, list(field_values),
            )
            return True
        except DwsError:
            raise
        except Exception as exc:
            logger.error("update_task 失败 task_id=%s: %s", task_id, exc, exc_info=True)
            return False
