"""会话级 tableId / fieldId 映射缓存（增强版，支持 TTL）。

设计动机（详见需求文档 §2.2.4）：
- 仅持久化 ``base_id`` 到 config.json，4 张表的 ``tableId`` 与所有字段的
  ``fieldId`` 通过固定中文表名/字段名实时映射，会话内缓存，避免持久化
  导致的同步问题（用户在 AI 表格界面手工增删字段会改变 fieldId）。

缓存粒度：
- ``base_id`` 维度独立的两级 dict：
  - ``base_id -> {table_name: table_id}``
  - ``base_id -> {table_name -> {field_name: field_id}}``
- 当连续 N 次返回 "not found" 时，由调用方主动 :meth:`invalidate`
  触发重建。

增强特性（性能优化）：
- TTL 机制：缓存条目在 ``ttl`` 秒后自动过期，避免长时间运行时数据陈旧。
- 批量预加载：``preload_fields(base_id, table_names)`` 一次性加载多张表的字段映射。
- Base 元数据缓存：``aitable_base_get`` 结果带 TTL 缓存，避免多服务重复调用。
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from scripts.domain.exceptions import SchemaValidationError
from scripts.infrastructure.dws_client import DwsClient

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300  # 默认缓存有效期：5 分钟


class MappingCache:
    """会话级 tableId / fieldId 缓存（支持 TTL）。

    线程安全说明：本系统由 Agent 一次性调用，单进程触发，无需多线程锁。
    并发查询场景下，缓存预加载在并发启动前完成，运行时只读，无竞争。
    """

    def __init__(
        self,
        client: Optional[DwsClient] = None,
        ttl: float = DEFAULT_TTL,
    ) -> None:
        self._client = client or DwsClient()
        self._ttl = ttl
        # base_id -> {table_name: table_id}
        self._table_ids: Dict[str, Dict[str, str]] = {}
        # base_id -> table_name -> {field_name: field_id}
        self._field_ids: Dict[str, Dict[str, Dict[str, str]]] = {}
        # TTL 时间戳：记录每个缓存条目的加载时间
        # base_id -> load_timestamp (for table_ids)
        self._table_ids_ts: Dict[str, float] = {}
        # base_id -> table_name -> load_timestamp (for field_ids)
        self._field_ids_ts: Dict[str, Dict[str, float]] = {}
        # base_id -> (raw_result, load_timestamp) — base_get 原始结果缓存
        self._base_get_cache: Dict[str, tuple] = {}

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def get_table_id(self, base_id: str, table_name: str) -> str:
        """按表名获取 tableId，未命中或过期则懒加载所有表。"""
        if self._is_table_ids_expired(base_id):
            self._load_table_ids(base_id)
        cache = self._table_ids.get(base_id)
        if cache is None or table_name not in cache:
            self._load_table_ids(base_id)
            cache = self._table_ids.get(base_id, {})
        if table_name not in cache:
            raise SchemaValidationError(
                f"Base {base_id!r} 中未找到表 {table_name!r}，"
                f"可能是表被删除/改名，请运行 init validate 检查。"
            )
        return cache[table_name]

    def get_field_id(
        self, base_id: str, table_name: str, field_name: str
    ) -> str:
        """按表名 + 字段名获取 fieldId，懒加载该表的全部字段。"""
        table_cache = self._field_ids.setdefault(base_id, {})
        fields = table_cache.get(table_name)
        if fields is None or field_name not in fields or self._is_field_ids_expired(base_id, table_name):
            self._load_field_ids(base_id, table_name)
            fields = self._field_ids[base_id].get(table_name, {})
        if field_name not in fields:
            raise SchemaValidationError(
                f"表 {table_name!r} 中未找到字段 {field_name!r}，"
                f"可能字段被删除/改名，请运行 init validate 检查。"
            )
        return fields[field_name]

    def get_field_map(
        self, base_id: str, table_name: str
    ) -> Dict[str, str]:
        """获取某张表的 fieldName→fieldId 完整映射（懒加载，带 TTL）。"""
        table_cache = self._field_ids.setdefault(base_id, {})
        if table_name not in table_cache or self._is_field_ids_expired(base_id, table_name):
            self._load_field_ids(base_id, table_name)
        return dict(table_cache.get(table_name, {}))

    def preload_fields(self, base_id: str, table_names: List[str]) -> None:
        """批量预加载多张表的字段映射（减少后续懒加载的 API 调用）。

        适用于已知将要访问多张表字段的场景（如 stats、summary），
        提前加载避免后续逐个懒加载。
        """
        for table_name in table_names:
            if self._is_field_ids_expired(base_id, table_name):
                try:
                    self._load_field_ids(base_id, table_name)
                except Exception as exc:
                    logger.warning(
                        "preload_fields 加载 %s/%s 失败: %s",
                        base_id, table_name, exc,
                    )

    def get_base_meta(self, base_id: str) -> dict:
        """获取 Base 元数据（带 TTL 缓存）。

        返回 ``aitable_base_get`` 的原始结果，多次调用同一 base_id 时
        在 TTL 内直接返回缓存。
        """
        cached = self._base_get_cache.get(base_id)
        if cached is not None:
            result, ts = cached
            if time.time() - ts < self._ttl:
                return result
        result = self._client.aitable_base_get(base_id)
        self._base_get_cache[base_id] = (result, time.time())
        return result

    def invalidate(self, base_id: Optional[str] = None) -> None:
        """清空缓存。``base_id=None`` 时清空所有 base 的缓存。"""
        if base_id is None:
            self._table_ids.clear()
            self._field_ids.clear()
            self._table_ids_ts.clear()
            self._field_ids_ts.clear()
            self._base_get_cache.clear()
        else:
            self._table_ids.pop(base_id, None)
            self._field_ids.pop(base_id, None)
            self._table_ids_ts.pop(base_id, None)
            self._field_ids_ts.pop(base_id, None)
            self._base_get_cache.pop(base_id, None)

    # ------------------------------------------------------------------
    # TTL 过期检查
    # ------------------------------------------------------------------

    def _is_table_ids_expired(self, base_id: str) -> bool:
        """检查 table_ids 缓存是否过期。"""
        ts = self._table_ids_ts.get(base_id)
        if ts is None:
            return True
        return (time.time() - ts) >= self._ttl

    def _is_field_ids_expired(self, base_id: str, table_name: str) -> bool:
        """检查某张表的 field_ids 缓存是否过期。"""
        ts_map = self._field_ids_ts.get(base_id)
        if ts_map is None:
            return True
        ts = ts_map.get(table_name)
        if ts is None:
            return True
        return (time.time() - ts) >= self._ttl

    # ------------------------------------------------------------------
    # 内部加载
    # ------------------------------------------------------------------

    def _load_table_ids(self, base_id: str) -> None:
        """调用 ``aitable base get`` 加载全部表名→tableId 映射。"""
        result = self.get_base_meta(base_id)
        tables = _extract_tables(result)
        mapping: Dict[str, str] = {}
        for t in tables:
            name = t.get("tableName") or t.get("name")
            tid = t.get("tableId") or t.get("id")
            if name and tid:
                mapping[name] = tid
        self._table_ids[base_id] = mapping
        self._table_ids_ts[base_id] = time.time()
        logger.debug(
            "loaded table ids for base %s: %s", base_id, list(mapping.keys())
        )

    def _load_field_ids(self, base_id: str, table_name: str) -> None:
        """调用 ``aitable table get`` 加载某张表的全部字段映射。"""
        table_id = self.get_table_id(base_id, table_name)
        result = self._client.aitable_table_get(base_id, table_id)
        fields = _extract_fields(result)
        mapping: Dict[str, str] = {}
        for f in fields:
            name = f.get("name") or f.get("fieldName")
            fid = f.get("fieldId") or f.get("id")
            if name and fid:
                mapping[name] = fid
        self._field_ids.setdefault(base_id, {})[table_name] = mapping
        self._field_ids_ts.setdefault(base_id, {})[table_name] = time.time()
        logger.debug(
            "loaded field ids for %s/%s: %s",
            base_id,
            table_name,
            list(mapping.keys()),
        )


# ---------------------------------------------------------------------------
# 兼容多种 dws 返回结构的解析器
# ---------------------------------------------------------------------------


def _extract_tables(payload: dict) -> list:
    """从 ``aitable base get`` 返回中提取 tables 列表。

    兼容两种风格：
    - ``{"tables": [...]}``
    - ``{"data": {"tables": [...]}}``
    """
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("tables"), list):
        return payload["tables"]
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("tables"), list):
        return data["tables"]
    return []


def _extract_fields(payload: dict) -> list:
    """从 ``aitable table get`` 返回中提取 fields 列表。

    兼容多种风格：
    - ``{"fields": [...]}``
    - ``{"tables": [{"fields": [...]}]}``
    - ``{"data": {"tables": [{"fields": [...]}]}}``
    """
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("fields"), list):
        return payload["fields"]
    if isinstance(payload.get("tables"), list) and payload["tables"]:
        first = payload["tables"][0]
        if isinstance(first, dict) and isinstance(first.get("fields"), list):
            return first["fields"]
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_fields(data)
    return []


__all__ = ["MappingCache"]
