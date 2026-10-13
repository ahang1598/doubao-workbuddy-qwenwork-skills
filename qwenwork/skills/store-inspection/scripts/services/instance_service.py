"""任务实例服务（InstanceService）。

从原 Dispatcher 类中提取任务实例相关方法，封装为独立的 InstanceService 类。
负责查询和更新动态任务实例表中的记录。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from scripts.services.dispatch_helpers import _extract_records
from scripts.domain import filters as F
from scripts.domain import schema as S
from scripts.domain.records import extract_cell_value as _extract_cell_value, extract_records, get_record_id, values_by_name
from scripts.domain.exceptions import DispatchError, DwsError
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache

logger = logging.getLogger(__name__)


class InstanceService:
    """任务实例服务，负责任务实例表的查询和更新操作。

    Args:
        client: DWS 客户端实例。
        cache: 映射缓存实例。
        base_id: Base ID，可选，未提供时从配置读取。
        table_manager: TableManager 实例，用于加载字段映射和获取任务记录表 ID。
    """

    def __init__(
        self,
        client: DwsClient,
        cache: MappingCache,
        base_id: Optional[str] = None,
        table_manager=None,
    ) -> None:
        self.client = client
        self.cache = cache
        self._base_id = base_id
        self.table_manager = table_manager

    @property
    def base_id(self) -> str:
        bid = self._base_id or get_base_id()
        if not bid:
            raise DispatchError("未初始化：config.json 中无 base_id")
        return bid

    def _resolve_instance_table_id(self, task_id: str) -> Optional[str]:
        """通过 task_id 从任务记录表查找对应的 instance_table_id。

        Args:
            task_id: 任务 ID。

        Returns:
            instance_table_id，未找到则返回 None。
        """
        try:
            task_record_table_id = self.table_manager._get_task_record_table_id()
            if not task_record_table_id:
                logger.warning("_resolve_instance_table_id: 未找到任务记录表")
                return None

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
                logger.warning(
                    "_resolve_instance_table_id: 未找到任务记录 task_id=%s", task_id
                )
                return None

            record = records[0]
            fields = values_by_name(
                self.cache, self.base_id, S.TASK_RECORD_TABLE, record
            )
            return fields.get("instance_table_id")
        except DwsError:
            raise
        except Exception as exc:
            logger.warning(
                "_resolve_instance_table_id 失败 task_id=%s: %s", task_id, exc
            )
            return None

    def query_instances(
        self,
        task_id: str,
        *,
        field_filters: Optional[Dict[str, Any]] = None,
        filter_empty: Optional[List[str]] = None,
        filter_not_empty: Optional[List[str]] = None,
        store_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """查询动态任务实例表中的巡检记录。

        Args:
            task_id: 任务 ID，用于定位对应的动态任务实例表。
            field_filters: 按字段名过滤，键为 fieldName，值为期望匹配的值。
            filter_empty: 需要为空值的字段名列表。
            filter_not_empty: 需要非空值的字段名列表。
            store_id: 按门店 ID 精确过滤。
            limit: 最多返回 N 条记录。

        Returns:
            记录列表，每个元素包含 record_id 和所有字段值。
        """
        try:
            instance_table_id = self._resolve_instance_table_id(task_id)
            if not instance_table_id:
                logger.warning(
                    "query_instances: 未找到任务对应的实例表 task_id=%s", task_id
                )
                return []

            field_map = self.table_manager._load_field_map(instance_table_id)
            if not field_map:
                logger.warning(
                    "query_instances: 无法加载字段映射 table_id=%s",
                    instance_table_id,
                )
                return []

            # 构建 filter 条件
            conditions: List[Dict[str, Any]] = []

            if field_filters:
                for field_name, field_value in field_filters.items():
                    field_id = field_map.get(field_name)
                    if field_id:
                        conditions.append(F.eq(field_id, field_value))
                    else:
                        logger.warning(
                            "query_instances: 字段 %s 不在字段映射中", field_name
                        )

            if filter_empty:
                for field_name in filter_empty:
                    field_id = field_map.get(field_name)
                    if field_id:
                        conditions.append(F.is_empty(field_id))
                    else:
                        logger.warning(
                            "query_instances: 字段 %s 不在字段映射中", field_name
                        )

            if filter_not_empty:
                for field_name in filter_not_empty:
                    field_id = field_map.get(field_name)
                    if field_id:
                        conditions.append(F.is_not_empty(field_id))
                    else:
                        logger.warning(
                            "query_instances: 字段 %s 不在字段映射中", field_name
                        )

            if store_id:
                store_id_field = field_map.get("store_id")
                if store_id_field:
                    conditions.append(F.eq(store_id_field, store_id))
                else:
                    logger.warning(
                        "query_instances: store_id 字段不在字段映射中"
                    )

            # 显式传入所有字段的 fieldId，确保 API 返回 attachment 等特殊类型字段的完整内容。
            # 不传 --fields 时，dws record query 可能不返回附件字段的 url 等详情。
            all_field_ids = list(field_map.values())

            # 执行查询
            filter_expr = F.and_(*conditions) if conditions else None
            if filter_expr is not None:
                payload = self.client.aitable_record_query(
                    self.base_id, instance_table_id, filter_expr,
                    fields=all_field_ids, limit=limit,
                )
            elif limit is not None:
                payload = self.client.aitable_record_query(
                    self.base_id, instance_table_id,
                    fields=all_field_ids, limit=limit,
                )
            else:
                payload = self.client.aitable_record_query(
                    self.base_id, instance_table_id,
                    fields=all_field_ids,
                )

            records = _extract_records(payload)
            reverse_map = {fid: name for name, fid in field_map.items()}
            results: List[Dict[str, Any]] = []
            for r in records:
                cells = r.get("cells") or r.get("fields") or {}
                fields_by_name: Dict[str, Any] = {}
                for fid, cell_value in cells.items():
                    name = reverse_map.get(fid, fid)
                    fields_by_name[name] = _extract_cell_value(cell_value)
                results.append({
                    "record_id": get_record_id(r),
                    **fields_by_name,
                })
            return results
        except DwsError:
            raise
        except Exception as exc:
            logger.warning("query_instances 失败 task_id=%s: %s", task_id, exc)
            return []

    def update_instance_fields(
        self,
        task_id: str,
        record_id: str,
        field_values: Dict[str, Any],
    ) -> bool:
        """更新动态任务实例表中的自定义字段值。

        Args:
            task_id: 任务 ID，用于定位对应的动态任务实例表。
            record_id: 要更新的记录 ID。
            field_values: 要更新的字段值字典，键为 fieldName，值为新值。

        Returns:
            True 表示更新成功，False 表示失败。

        Raises:
            DispatchError: 如果 field_values 中包含骨架字段。
        """
        # 校验 field_values 中不含骨架字段
        skeleton_set = set(S.TASK_INSTANCE_SKELETON_FIELD_NAMES)
        invalid_fields = [f for f in field_values if f in skeleton_set]
        if invalid_fields:
            raise DispatchError(
                f"不允许更新骨架字段: {invalid_fields}，骨架字段为 "
                f"{sorted(skeleton_set)}"
            )

        try:
            instance_table_id = self._resolve_instance_table_id(task_id)
            if not instance_table_id:
                logger.warning(
                    "update_instance_fields: 未找到任务对应的实例表 task_id=%s",
                    task_id,
                )
                return False

            field_map = self.table_manager._load_field_map(instance_table_id)
            if not field_map:
                logger.warning(
                    "update_instance_fields: 无法加载字段映射 table_id=%s",
                    instance_table_id,
                )
                return False

            # 将 field_values 的 fieldName 转为 fieldId 构建 cells
            cells: Dict[str, Any] = {}
            for field_name, field_value in field_values.items():
                field_id = field_map.get(field_name)
                if field_id:
                    cells[field_id] = field_value
                else:
                    logger.warning(
                        "update_instance_fields: 字段 %s 不在字段映射中，跳过",
                        field_name,
                    )

            if not cells:
                logger.debug(
                    "update_instance_fields: 无有效字段需要更新 task_id=%s",
                    task_id,
                )
                return True

            self.client.aitable_record_update(
                self.base_id,
                instance_table_id,
                [{"recordId": record_id, "cells": cells}],
            )
            logger.debug(
                "update_instance_fields: 记录已更新 task_id=%s record_id=%s "
                "fields=%s",
                task_id, record_id, list(field_values),
            )
            return True
        except (DispatchError, DwsError):
            raise
        except Exception as exc:
            logger.warning(
                "update_instance_fields 失败 task_id=%s record_id=%s: %s",
                task_id, record_id, exc,
            )
            return False

    def query_filled_store_ids(self, instance_table_id: str) -> set:
        """查询动态任务表中已存在记录的 store_id 集合（即"已填写"门店）。

        判定规则：巡检表中存在记录即视为"已填写"（不论 submit_status，
        因为 submit_status 的回写依赖外部业务表同步，存在延迟；以巡检表
        行存在为权威依据）。

        Args:
            instance_table_id: 动态任务表的 tableId。

        Returns:
            已填写门店 ID 的 set，查询失败或表不存在返回空 set。
        """
        if not instance_table_id:
            return set()
        try:
            field_map = self.table_manager._load_field_map(instance_table_id)
            store_id_field = field_map.get("store_id")
            if not store_id_field:
                logger.warning(
                    "query_filled_store_ids: 任务表 %s 缺少 store_id 字段",
                    instance_table_id,
                )
                return set()

            payload = self.client.aitable_record_query(
                self.base_id, instance_table_id
            )
            records = _extract_records(payload)
            filled = set()
            for r in records:
                cells = r.get("cells") or r.get("fields") or {}
                store_val = _extract_cell_value(cells.get(store_id_field))
                if store_val:
                    filled.add(str(store_val))
            return filled
        except DwsError:
            raise
        except Exception as exc:
            logger.warning("query_filled_store_ids 失败: %s", exc)
            return set()
