"""门店清单（MAPPING_TABLE）维护（需求文档 §2.3.1）。

提供门店与店长映射的 CRUD，以及备用通讯录查询。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from scripts.domain import filters as F
from scripts.domain import schema as S
from scripts.domain.exceptions import StoreTaskDispatcherError
from scripts.domain.records import (
    cells_by_name,
    extract_records,
    get_record_id,
    values_by_name,
)
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache

logger = logging.getLogger(__name__)

# 允许通过 add_store 设置的字段（白名单，与 schema 一致）
_WRITABLE_FIELDS = {
    "store_id",
    "store_name",
    "tags",
    "manager",
    "status",
}


class StoreManager:
    """门店清单 CRUD。"""

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
            raise StoreTaskDispatcherError(
                "未初始化：config.json 中无 base_id，请先运行 init create/query/url"
            )
        return bid

    def _table_id(self) -> str:
        return self.cache.get_table_id(self.base_id, S.MAPPING_TABLE)

    def get_store_table_url(self) -> str:
        """返回门店清单表的 AI 表格链接，供用户直接在表格中管理门店。"""
        return f"https://docs.dingtalk.com/i/nodes/{self.base_id}"

    # ------------------------------------------------------------------
    # 增
    # ------------------------------------------------------------------

    def add_store(
        self,
        store_name: str,
        manager: str,
        *,
        store_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: str = "active",
    ) -> str:
        """新增门店。返回新建记录的 ``recordId``。

        Args:
            store_name: 门店名称。
            manager: 店长 userId 字符串，写入 user 类型字段。
            store_id: 门店 ID，可选。为空时自动生成 ``S_{yyyyMMddHHmmss}_{rand4}``。
            tags: 标签列表。
            status: 状态，默认 active。

        Raises:
            StoreTaskDispatcherError: ``store_id`` 已存在。
        """
        if not store_id:
            import random
            import string
            from datetime import datetime as _dt
            now = _dt.now()
            rand4 = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
            store_id = f"S_{now.strftime('%Y%m%d%H%M%S')}_{rand4}"
        existing = self._find_record_id(store_id)
        if existing:
            raise StoreTaskDispatcherError(
                f"门店 {store_id!r} 已存在（recordId={existing}），请用 update_store 更新"
            )

        values = {
            "store_id": store_id,
            "store_name": store_name,
            "manager": manager,
            "tags": tags,
            "status": status,
        }
        cells = cells_by_name(self.cache, self.base_id, S.MAPPING_TABLE, values)
        result = self.client.aitable_record_create(
            self.base_id, self._table_id(), [{"cells": cells}]
        )
        records = extract_records(result)
        if records and get_record_id(records[0]):
            return get_record_id(records[0])
        # 兜底：dws 可能返回不同结构，回查一次
        rid = self._find_record_id(store_id)
        if not rid:
            raise StoreTaskDispatcherError(
                f"门店 {store_id!r} 创建后未能定位到 recordId，原始返回: {result!r}"
            )
        return rid

    # ------------------------------------------------------------------
    # 改
    # ------------------------------------------------------------------

    def update_store(self, store_id: str, **fields: Any) -> str:
        """按 ``store_id`` 更新门店字段。返回更新的 ``recordId``。"""
        invalid = set(fields) - _WRITABLE_FIELDS
        if invalid:
            raise StoreTaskDispatcherError(f"不允许更新字段: {sorted(invalid)}")
        rid = self._find_record_id(store_id)
        if not rid:
            raise StoreTaskDispatcherError(f"门店 {store_id!r} 不存在")
        cells = cells_by_name(self.cache, self.base_id, S.MAPPING_TABLE, fields)
        if not cells:
            return rid
        self.client.aitable_record_update(
            self.base_id,
            self._table_id(),
            [{"recordId": rid, "cells": cells}],
        )
        return rid

    # ------------------------------------------------------------------
    # 删
    # ------------------------------------------------------------------

    def delete_store(self, store_id: str) -> bool:
        rid = self._find_record_id(store_id)
        if not rid:
            return False
        self.client.aitable_record_delete(self.base_id, self._table_id(), rid)
        return True

    # ------------------------------------------------------------------
    # 查
    # ------------------------------------------------------------------

    def get_store(self, store_id: str) -> Optional[Dict[str, Any]]:
        record = self._find_record(store_id)
        if not record:
            return None
        out = values_by_name(self.cache, self.base_id, S.MAPPING_TABLE, record)
        out["recordId"] = get_record_id(record)
        return out

    def list_stores(
        self,
        *,
        only_active: bool = False,
        tags_any_of: Optional[List[str]] = None,
        limit: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        fetch_all: bool = False,
    ) -> List[Dict[str, Any]]:
        """列出门店记录。

        支持两种模式：
        - **分页模式**（默认）：按 ``limit`` 返回单页数据，适用于 CLI ``store list``
          等展示场景。DWS 服务端 ``--limit`` 封顶 100，无需客户端额外截断。
        - **全量模式**（``fetch_all=True``）：使用 DWS ``--all`` 自动翻页，CLI 内置
          200ms 页间间隔防抖，不会触发限流。适用于派发通知等必须拿到完整门店列表
          的场景。上限 page_limit=20（即 2000 条），对门店清单绰绰有余。

        Args:
            only_active: 仅返回 ``status='active'`` 的门店。
            tags_any_of: 标签筛选，任意命中即可。
            limit: 单页拉取条数（仅 fetch_all=False 时生效）。
                DWS 服务端硬限最大 100，超过自动截断。
            sort_by: 排序字段名（默认 created_at）。
            sort_order: 排序方向：asc / desc（默认 desc）。
            fetch_all: 启用全量拉取。内部使用 ``--all --page-limit 20``。
        """
        t_start = time.time()
        conds = []
        if only_active:
            field_id = self.cache.get_field_id(
                self.base_id, S.MAPPING_TABLE, "status"
            )
            conds.append(F.eq(field_id, "active"))
        if tags_any_of:
            field_id = self.cache.get_field_id(
                self.base_id, S.MAPPING_TABLE, "tags"
            )
            conds.append(F.any_of(field_id, *tags_any_of))
        filters = F.and_(*conds) if conds else None
        t_filter = time.time()
        logger.debug("[list_stores] filter构造耗时: %.3fs", t_filter - t_start)

        # 构造 DWS 服务端排序
        sort_field_id = self.cache.get_field_id(
            self.base_id, S.MAPPING_TABLE, sort_by
        )
        sort_param = [{"fieldId": sort_field_id, "direction": sort_order}] if sort_field_id else None
        t_sort = time.time()
        logger.debug("[list_stores] sort构造耗时: %.3fs", t_sort - t_filter)

        if fetch_all:
            # 使用 DWS --all 自动翻页（CLI 内置 200ms 页间间隔防抖）
            # page_limit=20 即最多 2000 条门店，对门店清单场景绰绰有余
            result = self.client.aitable_record_query(
                self.base_id, self._table_id(), filters,
                sort=sort_param, fetch_all=True, page_limit=20,
            )
        else:
            # DWS 服务端 --limit 封顶 100，无需客户端额外截断
            result = self.client.aitable_record_query(
                self.base_id, self._table_id(), filters,
                limit=limit, sort=sort_param,
            )
        t_query = time.time()
        logger.debug("[list_stores] DWS查询耗时: %.3fs", t_query - t_sort)

        out = []
        for r in extract_records(result):
            d = values_by_name(self.cache, self.base_id, S.MAPPING_TABLE, r)
            d["recordId"] = get_record_id(r)
            out.append(d)
        t_parse = time.time()
        logger.debug(
            "[list_stores] 结果解析耗时: %.3fs, 记录数: %d, fetch_all=%s",
            t_parse - t_query, len(out), fetch_all,
        )
        logger.debug("[list_stores] 总耗时: %.3fs", t_parse - t_start)
        return out

    def list_all_stores(
        self,
        *,
        only_active: bool = False,
        tags_any_of: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """全量拉取门店（DWS --all 自动翻页）。

        派发巡店通知时必须使用此方法，确保拿到所有目标门店。
        底层使用 DWS CLI 的 --all 模式，页间自带 200ms 间隔防抖，
        page_limit=20（上限 2000 条门店）。

        Note:
            之前使用 list_stores(limit=10) 导致只通知前 10 家门店的 Bug
            已通过本方法修复——派发场景务必调用 list_all_stores 而非 list_stores。
        """
        return self.list_stores(
            only_active=only_active,
            tags_any_of=tags_any_of,
            fetch_all=True,
        )

    def list_stores_by_ids(self, store_ids: List[str]) -> List[Dict[str, Any]]:
        """按 store_id 列表精确取门店。"""
        if not store_ids:
            return []
        # dws filter 没有原生 in，用 or 拼接
        field_id = self.cache.get_field_id(
            self.base_id, S.MAPPING_TABLE, "store_id"
        )
        conds = [F.eq(field_id, sid) for sid in store_ids]
        filters = F.or_(*conds) if len(conds) > 1 else conds[0]
        result = self.client.aitable_record_query(
            self.base_id, self._table_id(), filters
        )
        out = []
        for r in extract_records(result):
            d = values_by_name(self.cache, self.base_id, S.MAPPING_TABLE, r)
            d["recordId"] = get_record_id(r)
            out.append(d)
        return out

    # ------------------------------------------------------------------
    # 备用通讯录查询
    # ------------------------------------------------------------------

    def batch_add_stores(self, stores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量新增门店，返回统计结果。

        Args:
            stores: 门店列表，每项至少包含 ``store_name``、``manager``，
                ``store_id`` 可选（为空时自动生成）。

        Returns:
            ``{"success": N, "failed": N, "skipped": N, "errors": [...]}``
        """
        success = 0
        failed = 0
        skipped = 0
        errors: List[Dict[str, Any]] = []

        for i, store in enumerate(stores):
            store_name = store.get("store_name")
            manager = store.get("manager")
            if not store_name or not manager:
                errors.append({
                    "index": i,
                    "store_id": store.get("store_id", ""),
                    "reason": "缺少 store_name 或 manager",
                })
                failed += 1
                continue

            try:
                self.add_store(
                    store_name=store_name,
                    manager=manager,
                    store_id=store.get("store_id"),
                    tags=store.get("tags"),
                    status=store.get("status", "active"),
                )
                success += 1
            except StoreTaskDispatcherError as exc:
                if "已存在" in str(exc):
                    skipped += 1
                else:
                    failed += 1
                errors.append({
                    "index": i,
                    "store_id": store.get("store_id", ""),
                    "reason": str(exc),
                })
            except Exception as exc:
                failed += 1
                errors.append({
                    "index": i,
                    "store_id": store.get("store_id", ""),
                    "reason": str(exc),
                })

        return {
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
        }

    def find_manager_by_name(self, name: str) -> List[Dict[str, Any]]:
        """通过钉钉通讯录按姓名查找 UserID。"""
        try:
            result = self.client.contact_user_search(name)
        except Exception as exc:  # pragma: no cover - 由 client 抛 DwsError
            logger.warning("contact_user_search failed: %s", exc)
            return []
        return _extract_users(result)

    def find_manager_by_mobile(self, mobile: str) -> List[Dict[str, Any]]:
        try:
            result = self.client.contact_user_search_mobile(mobile)
        except Exception as exc:  # pragma: no cover
            logger.warning("contact_user_search_mobile failed: %s", exc)
            return []
        return _extract_users(result)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _find_record(self, store_id: str) -> Optional[Dict[str, Any]]:
        field_id = self.cache.get_field_id(
            self.base_id, S.MAPPING_TABLE, "store_id"
        )
        filters = F.and_(F.eq(field_id, store_id))
        result = self.client.aitable_record_query(
            self.base_id, self._table_id(), filters, limit=1
        )
        records = extract_records(result)
        return records[0] if records else None

    def _find_record_id(self, store_id: str) -> Optional[str]:
        rec = self._find_record(store_id)
        return get_record_id(rec) if rec else None


def _extract_users(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    # dws contact user search 返回 {"result": [...], "success": true}
    for key in ("result", "users", "items", "list"):
        items = payload.get(key)
        if isinstance(items, list):
            return items
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_users(data)
    return []


__all__ = ["StoreManager"]
