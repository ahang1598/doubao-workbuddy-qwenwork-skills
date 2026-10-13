"""任务进度监控（新架构）。

新架构下，任务数据存储在动态任务表（如「每日巡检-20260424」）中。
Monitor 提供两种查询方式：
1. 查询通知明细表：了解通知发送状态（sent/failed/pending）
2. 查询动态任务表：了解门店提交状态（待提交/已提交）
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from scripts.domain import schema as S
from scripts.domain.exceptions import DwsError, StoreTaskDispatcherError
from scripts.domain.records import extract_records, values_by_name
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache

logger = logging.getLogger(__name__)


class Monitor:
    """任务进度查询。"""

    def __init__(
        self,
        client: Optional[DwsClient] = None,
        cache: Optional[MappingCache] = None,
        base_id: Optional[str] = None,
    ) -> None:
        self.client = client or DwsClient()
        self.cache = cache or MappingCache(client=self.client)
        self._base_id = base_id

    @property
    def base_id(self) -> str:
        bid = self._base_id or get_base_id()
        if not bid:
            raise StoreTaskDispatcherError("未初始化：config.json 中无 base_id")
        return bid

    def _find_notification_tables(self) -> List[Dict[str, Any]]:
        """从 AI表格 中查找所有动态通知明细表（表名以 '-通知' 结尾），返回 [{table_id, table_name}]。

        【性能优化】使用 aitable_base_get_cached 避免重复调用。
        """
        try:
            payload = self.client.aitable_base_get_cached(self.base_id)
            data = payload.get("data") or payload
            tables = data.get("tables") or []
            return [
                {"table_id": t.get("tableId") or t.get("id"), "table_name": t.get("tableName") or t.get("name")}
                for t in tables
                if (t.get("tableName") or t.get("name", "")).endswith(S.NOTIFICATION_TABLE_SUFFIX)
            ]
        except DwsError:
            raise
        except Exception as exc:
            logger.error(
                "查找通知明细表失败 base_id=%s: %s，无法查询通知状态",
                self.base_id, exc,
            )
            return []

    # ------------------------------------------------------------------
    # 查询通知明细
    # ------------------------------------------------------------------

    def query_notifications(
        self,
        task_id: Optional[str] = None,
        store_name: Optional[str] = None,
        notify_status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """查询通知明细表，了解通知发送状态。

        新架构下，通知明细存储在动态表（如「早会巡检-20260424-通知」）中，
        本方法自动查找所有以「-通知」结尾的表并合并结果。

        【性能优化】使用 aitable_record_query_batch 并发查询所有通知表。

        Args:
            task_id: 按任务 ID 过滤。
            store_name: 按门店名称过滤。
            notify_status: 按通知状态过滤（pending/sent/failed）。
            limit: 最大返回条数。
        """
        notif_tables = self._find_notification_tables()
        if not notif_tables:
            logger.error("查询通知明细失败: AI表格 '%s' 中未找到任何通知明细表（以'-通知'结尾），"
                         "可能尚未派发或表被删除。", self.base_id)
            return []

        # 【性能优化】并发查询所有通知表
        table_ids = [tbl["table_id"] for tbl in notif_tables]
        batch_results = self.client.aitable_record_query_batch(
            self.base_id, table_ids, limit=limit, max_workers=5
        )

        # 构建 table_id -> table_name 的映射
        tid_to_name = {tbl["table_id"]: tbl["table_name"] for tbl in notif_tables}

        rows = []
        for tbl_id, result in batch_results.items():
            tbl_name = tid_to_name.get(tbl_id, "")
            for record in extract_records(result):
                # 用原始 cells 解析，兼容 fieldId 或 fieldName key
                row = _extract_raw_values(record)
                row["_table_name"] = tbl_name
                if task_id and row.get("task_id") != task_id:
                    continue
                if store_name and store_name not in (row.get("store_name") or ""):
                    continue
                if notify_status and row.get("notify_status") != notify_status:
                    continue
                rows.append(row)
        return rows

    # ------------------------------------------------------------------
    # 查询动态任务表
    # ------------------------------------------------------------------

    def query_task_table(
        self,
        task_table_id: str,
        store_name: Optional[str] = None,
        submit_status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """查询动态任务表，了解门店提交状态。

        纯 prefill 模式下记录存在即视为已提交，submit_status 参数仅用于
        向后兼容旧调用方，传入时仍按字段值过滤（如果记录中有该字段）。

        Args:
            task_table_id: 动态任务表的 tableId。
            store_name: 按门店名称过滤。
            submit_status: 按提交状态过滤（向后兼容，新代码不应依赖此参数）。
            limit: 最大返回条数。
        """
        try:
            result = self.client.aitable_record_query(
                self.base_id,
                task_table_id,
                filters=None,
                limit=limit,
            )
        except DwsError:
            raise
        except Exception as exc:
            logger.error(
                "查询任务表失败 task_table_id=%s: %s，返回空列表可能掩盖实际错误",
                task_table_id, exc,
            )
            return []

        rows = []
        for record in extract_records(result):
            # 动态任务表字段不在固定 schema 中，直接取原始值
            row = _extract_raw_values(record)
            if store_name and store_name not in (row.get("store_name") or ""):
                continue
            if submit_status and row.get("submit_status") != submit_status:
                continue
            rows.append(row)
        return rows

    # ------------------------------------------------------------------
    # Markdown 输出
    # ------------------------------------------------------------------

    def format_notifications_as_markdown(
        self, rows: List[Dict[str, Any]]
    ) -> str:
        """将通知明细列表格式化为 Markdown 表格。"""
        if not rows:
            return "_暂无数据_"
        headers = ["门店", "店长", "通知状态", "派发时间", "最近联系", "任务表"]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows:
            lines.append(
                f"| {row.get('store_name', '')} "
                f"| {row.get('manager_name', '')} "
                f"| {row.get('notify_status', '')} "
                f"| {row.get('dispatched_at', '')} "
                f"| {row.get('last_contacted_at', '')} "
                f"| {row.get('task_table_name', '')} |"
            )
        return "\n".join(lines)


def _extract_raw_values(record: Dict[str, Any]) -> Dict[str, Any]:
    """从 dws record 中提取原始字段值（不依赖 fieldId 映射）。"""
    result: Dict[str, Any] = {}
    cells = record.get("cells") or record.get("fields") or {}
    if isinstance(cells, dict):
        for key, val in cells.items():
            if isinstance(val, dict):
                result[key] = val.get("value") or val.get("text") or val
            elif isinstance(val, list) and val:
                result[key] = ", ".join(
                    str(v.get("text") or v.get("value") or v) for v in val
                )
            else:
                result[key] = val
    return result


__all__ = ["Monitor"]
