"""巡店模版（TEMPLATE_TABLE）维护。

新架构变化：
- 新增 ``custom_fields`` 字段：JSON 数组字符串，存储管理员自定义的巡检字段定义
  格式：[{"name": "陈列情况", "type": "singleSelect", "options": ["正常", "异常"]}, ...]
- 移除 ``form_id`` / ``form_base_url``：表单现在挂在动态任务表上，由 dispatcher 创建任务时处理
- 模版只负责定义"要巡检什么字段"和"派发给哪些门店"

字段类型写入注意事项：
- richText 类型（description）：需要传 dws doc 格式
- date 类型（created_at/updated_at）：需要传毫秒时间戳（int）
- singleSelect 类型（status）：直接传选项名称字符串
"""

from __future__ import annotations

import json
import logging
import random
import string
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from scripts.domain import filters as F
from scripts.domain import schema as S
from scripts.domain.exceptions import StoreTaskDispatcherError
from scripts.domain.records import (
    build_cell_value,
    cells_by_name,
    extract_records,
    get_record_id,
    values_by_name,
)
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache
from scripts.utils.datetime_format import fmt_datetime

logger = logging.getLogger(__name__)

# 允许通过 update_template 更新的字段
# 重构后：
# - description 改为「模板介绍文本」（仍是 richText），不再参与消息渲染
# - 新增 dispatch_message（richText）：派发消息正文 Markdown 模板，提醒消息复用
# - 删除 remind_topic / remind_message：老库残留字段不再可写、读取时被忽略
_WRITABLE_FIELDS = {
    "name",
    "description",
    "message_title",
    "dispatch_message",
    "status",
    "custom_fields",
    "summary_receivers",
    "remind_time",
    "granularity",
    "expected_duration",
    "updated_at",
    # 建表策略相关字段
    "table_strategy",
    "table_row_limit",
    "active_instance_id",
    "managed_instance_ids",
}

# 支持的自定义字段类型（dws aitable field type）
# 完整列表可通过 `dws aitable table create -h` 查询；
# AI 字段（aiConfig）可通过 `dws aitable field create -h` 查询。
SUPPORTED_CUSTOM_FIELD_TYPES = {
    # ── 基础字段 ──
    "text": "单行文本",
    "richText": "多行文本",
    "number": "数字",
    "singleSelect": "单选",
    "multipleSelect": "多选",
    "checkbox": "勾选框",
    "date": "日期",
    "url": "链接",
    "telephone": "电话",
    "email": "邮件",
    "attachment": "附件",
    # ── 扩展字段 ──
    "currency": "货币",
    "user": "人员",
    "department": "部门",
    "group": "群组",
    "progress": "进度",
    "rating": "评分",
    "idCard": "身份证",
    "barcode": "条码",
    "geolocation": "地理位置",
    "address": "行政区域",
    # ── 关联 / 引用字段（需额外 config） ──
    "unidirectionalLink": "单向关联",
    "bidirectionalLink": "双向关联",
}


def generate_template_id(now: Optional[datetime] = None) -> str:
    """生成模板 ID：``TPL_{yyyyMMddHHmmss}_{rand4}``。"""
    now = now or datetime.now()
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"TPL_{now.strftime('%Y%m%d%H%M%S')}_{suffix}"


def parse_custom_fields(custom_fields_json: str) -> List[Dict[str, Any]]:
    """解析 custom_fields JSON 字符串，返回字段定义列表（dws field 格式）。

    支持的属性：
    - ``name``（必填）：字段名称
    - ``type``（可选，默认 text）：字段类型，见 ``SUPPORTED_CUSTOM_FIELD_TYPES``
    - ``options``（可选）：singleSelect / multipleSelect 的选项列表（简写格式）
    - ``config``（可选）：dws 原生字段配置，直接透传
    - ``aiConfig``（可选）：AI 字段配置，直接透传给 ``dws aitable field create``
    - ``hidden``（可选）：表单视图中隐藏该字段
    """
    if not custom_fields_json:
        return []
    try:
        raw = json.loads(custom_fields_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []

    result = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        field_def: Dict[str, Any] = {
            "name": item["name"],
            "type": item.get("type", "text"),
        }
        options = item.get("options", [])
        if options and field_def["type"] in ("singleSelect", "multipleSelect"):
            field_def["config"] = {
                "options": [{"name": str(opt)} for opt in options]
            }
        elif item.get("config"):
            field_def["config"] = item["config"]
        # 透传 aiConfig：AI 字段配置（outputType / prompt / imageConfig 等），
        # 由 dws aitable field create 消费，建表阶段需通过 field create 单独创建。
        if item.get("aiConfig"):
            field_def["aiConfig"] = item["aiConfig"]
        # 透传 hidden 属性：标记为 True 时，该字段在表单视图中隐藏，
        # 但仍会被建表创建并支持通过 prefill 写入与服务端读取。
        if item.get("hidden"):
            field_def["hidden"] = True
        # 透传 AI 审核三属性：ai_review / ai_standards / ai_prompt。
        # 这些属性由 table_manager._create_ai_review_fields 消费，
        # 在建表阶段为 attachment 字段自动创建配套的「AI 审核_xxx」字段。
        if item.get("ai_review"):
            field_def["ai_review"] = item["ai_review"]
        if item.get("ai_standards"):
            field_def["ai_standards"] = item["ai_standards"]
        if item.get("ai_prompt"):
            field_def["ai_prompt"] = item["ai_prompt"]
        result.append(field_def)

    if len(result) < 1:
        raise StoreTaskDispatcherError("任务模版至少需要定义一个自定义字段")

    return result


def build_custom_fields_json(field_definitions: List[Dict[str, Any]]) -> str:
    """将字段定义列表序列化为 JSON 字符串存入模版表。"""
    return json.dumps(field_definitions, ensure_ascii=False)


def _to_rich_text(text: str) -> Dict[str, Any]:
    """将纯文本字符串转为 AITable richText 写入格式。

    官方规范：richText 字段写入时使用 ``{"markdown": "..."}`` 格式。
    """
    return build_cell_value("richText", text)  # type: ignore[return-value]


class TemplateManager:
    """巡店模版 CRUD。"""

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
        return self.cache.get_table_id(self.base_id, S.TEMPLATE_TABLE)

    # ------------------------------------------------------------------
    # 增
    # ------------------------------------------------------------------

    def create_template(
        self,
        *,
        name: str,
        description: str,
        custom_fields: Optional[List[Dict[str, Any]]] = None,
        summary_receivers: Optional[str] = None,
        remind_time: Optional[str] = None,
        created_by: Optional[str] = None,
        status: str = "enabled",
        template_id: Optional[str] = None,
        now: Optional[datetime] = None,
        # 消息模板相关字段（None 表示不写入，由 messenger 在发送时 fallback 到默认模板）
        message_title: Optional[str] = None,
        # 派发消息正文 Markdown 模板（重构后新增；提醒消息复用同一份模板）
        dispatch_message: Optional[str] = None,
        # 任务粒度：daily（按天，默认）/ hourly（按小时）
        granularity: Optional[str] = None,
        # 期望完成时长：格式 "Xh" / "Xm" / "XhYm"，如 "2h"、"30m"、"1h30m"
        expected_duration: Optional[str] = None,
        # 建表策略：auto（默认，按行数自动切表）/ per_year / per_month / once
        table_strategy: Optional[str] = None,
        # 单表行数上限（仅 auto 策略有效），超过则新建任务实例表，默认 10000
        table_row_limit: Optional[int] = None,
        # 已废弃参数（向后兼容；调用方仍可能传入，统一忽略不写库）
        remind_topic: Optional[str] = None,  # noqa: ARG002 - deprecated
        remind_message: Optional[str] = None,  # noqa: ARG002 - deprecated
    ) -> str:
        """新建模版，返回 ``template_id``。

        消息相关字段说明（重构后）：

        - ``description``：模板介绍文本（richText，管理后台展示用，**不再**参与消息渲染）
        - ``message_title``：派发消息标题（钉钉消息列表显示），支持占位符；
          提醒消息复用同一份标题，第 N 次提醒（N≥2）由 messenger 自动加
          ``【第N次提醒】`` 前缀
        - ``dispatch_message``：派发消息正文 Markdown 模板（richText），
          提醒消息复用同一份模板

        所有消息字段为空时，由 :class:`scripts.services.messenger.Messenger`
        在发送时 fallback 到 :mod:`scripts.domain.message_defaults` 中的内置默认值。

        ``remind_topic`` / ``remind_message`` 已废弃：参数仍保留入参以兼容老调用，
        但**不会写入数据库**；老库残留字段会被代码完全忽略。
        """
        now = now or datetime.now()
        tpl_id = template_id or generate_template_id(now)
        custom_fields_json = build_custom_fields_json(custom_fields or [])
        now_str = fmt_datetime(now)

        logger.debug("[create_template] 开始创建模版，template_id=%s, name=%s", tpl_id, name)
        logger.debug("[create_template] 参数详情: status=%s, granularity=%s, expected_duration=%s, "
                     "remind_time=%s, summary_receivers=%s, created_by=%s",
                     status, granularity, expected_duration, remind_time, summary_receivers, created_by)
        logger.debug("[create_template] description 长度=%d，内容预览: %s",
                     len(description), description[:120] + ("…" if len(description) > 120 else ""))
        logger.debug("[create_template] custom_fields_json=%s", custom_fields_json)
        logger.debug("[create_template] message_title=%s, dispatch_message=%s",
                     message_title,
                     (dispatch_message[:80] + "…" if dispatch_message and len(dispatch_message) > 80 else dispatch_message))
        if remind_topic or remind_message:
            logger.debug(
                "[create_template] 收到已废弃参数 remind_topic / remind_message，"
                "将被忽略不写入数据库（重构后由 dispatch_message + 自动【第N次提醒】前缀替代）",
            )

        logger.debug("[create_template] description 长度=%d，内容预览: %s",
                     len(description), description[:120] + ("…" if len(description) > 120 else ""))
        if dispatch_message:
            logger.debug("[create_template] dispatch_message 长度=%d", len(dispatch_message))
        else:
            logger.debug("[create_template] dispatch_message 为空，不写入 richText 字段（messenger 发送时使用默认模板）")

        values = {
            "template_id": tpl_id,
            "name": name,
            # richText 字段必须传 doc 格式，不能传裸字符串（AITable 不会自动包装）
            "description": _to_rich_text(description),
            # 消息模板字段：None 表示不写入，由 messenger 在发送时 fallback 到默认模板
            "message_title": message_title or None,
            # dispatch_message 也是 richText，为空则不写入字段
            "dispatch_message": _to_rich_text(dispatch_message) if dispatch_message else None,
            "status": status,
            "custom_fields": custom_fields_json,
            # 以下可选字段：None 表示不写入，避免向 AITable 传空字符串导致 InvalidArgument
            "summary_receivers": summary_receivers or None,
            "remind_time": remind_time or None,
            "created_by": created_by or None,
            # date 类型传格式化日期字符串（与 schema _DATE_TIME_CONFIG 对齐）
            "created_at": now_str,
            "updated_at": now_str,
            # 任务粒度：daily（按天，默认）/ hourly（按小时）
            "granularity": granularity or "daily",
            # 期望完成时长：如 "2h"、"30m"、"1h30m"；为空则不写入
            "expected_duration": expected_duration or None,
            # 建表策略：auto（默认）/ per_year / per_month / once；为空则不写入（dispatcher 读取时兜底 auto）
            "table_strategy": table_strategy or None,
            # 单表行数上限：为空则不写入（dispatcher 读取时兜底 10000）
            "table_row_limit": table_row_limit if table_row_limit is not None else None,
        }
        logger.debug("[create_template] 构造 values（fieldName→value）完成，共 %d 个字段: %s",
                     len(values), list(values.keys()))

        logger.debug("[create_template] 调用 cells_by_name，base_id=%s, table=%s", self.base_id, S.TEMPLATE_TABLE)
        try:
            cells = cells_by_name(self.cache, self.base_id, S.TEMPLATE_TABLE, values)
        except KeyError as exc:
            logger.debug("[create_template] cells_by_name 字段映射失败: %s", exc)
            raise
        logger.debug("[create_template] cells_by_name 转换完成，共 %d 个 cell，fieldId 列表: %s",
                     len(cells), list(cells.keys()))

        table_id = self._table_id()
        records_payload = [{"cells": cells}]
        logger.debug("[create_template] 调用 aitable_record_create，base_id=%s, table_id=%s",
                     self.base_id, table_id)
        logger.debug("[create_template] records payload（JSON）: %s",
                     json.dumps(records_payload, ensure_ascii=False))

        try:
            result = self.client.aitable_record_create(
                self.base_id, table_id, records_payload
            )
            logger.debug("[create_template] aitable_record_create 返回: %s", result)
        except Exception as exc:
            logger.debug("[create_template] aitable_record_create 调用异常: %s", exc)
            raise

        logger.debug("[create_template] 模版创建成功，template_id=%s", tpl_id)
        return tpl_id

    # ------------------------------------------------------------------
    # 改
    # ------------------------------------------------------------------

    def update_template(self, template_id: str, **fields: Any) -> str:
        invalid = set(fields) - _WRITABLE_FIELDS
        if invalid:
            raise StoreTaskDispatcherError(f"不允许更新字段: {sorted(invalid)}")
        rid = self._find_record_id(template_id)
        if not rid:
            raise StoreTaskDispatcherError(f"模板 {template_id!r} 不存在")

        # custom_fields 如果传入的是 list，自动序列化为 JSON
        if "custom_fields" in fields and isinstance(fields["custom_fields"], list):
            fields["custom_fields"] = build_custom_fields_json(fields["custom_fields"])

        # description / dispatch_message 是 richText 类型，必须转为 doc 格式，不能传裸字符串
        if "description" in fields and isinstance(fields["description"], str):
            fields["description"] = _to_rich_text(fields["description"])
        if "dispatch_message" in fields and isinstance(fields["dispatch_message"], str):
            fields["dispatch_message"] = _to_rich_text(fields["dispatch_message"])

        # updated_at 传格式化日期字符串（与 schema _DATE_TIME_CONFIG 对齐）
        fields["updated_at"] = fmt_datetime(datetime.now())

        cells = cells_by_name(self.cache, self.base_id, S.TEMPLATE_TABLE, fields)
        if not cells:
            return rid
        self.client.aitable_record_update(
            self.base_id,
            self._table_id(),
            [{"recordId": rid, "cells": cells}],
        )
        return rid

    def enable_template(self, template_id: str) -> str:
        return self.update_template(template_id, status="enabled")

    def disable_template(self, template_id: str) -> str:
        return self.update_template(template_id, status="disabled")

    # ------------------------------------------------------------------
    # 查
    # ------------------------------------------------------------------

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        record = self._find_record(template_id)
        if not record:
            return None
        out = values_by_name(self.cache, self.base_id, S.TEMPLATE_TABLE, record)
        out["recordId"] = get_record_id(record)
        return out

    def get_template_custom_fields(
        self, template_id: str
    ) -> List[Dict[str, Any]]:
        """获取模版的自定义字段定义列表（已解析为 dws field 格式）。"""
        tpl = self.get_template(template_id)
        if not tpl:
            return []
        return parse_custom_fields(tpl.get("custom_fields") or "")

    def list_templates(
        self,
        *,
        only_enabled: bool = False,
        limit: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """列出所有模版。

        Args:
            only_enabled: 仅返回 ``status='enabled'``。
            limit: 最多返回条数（默认 10，上限 100）。
            sort_by: 排序字段名（默认 created_at）。
            sort_order: 排序方向：asc 升序 / desc 降序（默认 desc）。
        """
        t_start = time.time()
        limit = min(limit, 100)
        filters = None
        if only_enabled:
            field_id = self.cache.get_field_id(
                self.base_id, S.TEMPLATE_TABLE, "status"
            )
            filters = F.and_(F.eq(field_id, "enabled"))
        t_filter = time.time()
        logger.debug("[list_templates] filter构造耗时: %.3fs", t_filter - t_start)

        # 构造 DWS 服务端排序
        sort_field_id = self.cache.get_field_id(
            self.base_id, S.TEMPLATE_TABLE, sort_by
        )
        sort_param = [{"fieldId": sort_field_id, "direction": sort_order}] if sort_field_id else None
        t_sort = time.time()
        logger.debug("[list_templates] sort构造耗时: %.3fs", t_sort - t_filter)

        result = self.client.aitable_record_query(
            self.base_id, self._table_id(), filters, limit=limit, sort=sort_param
        )
        t_query = time.time()
        logger.debug("[list_templates] DWS查询耗时: %.3fs", t_query - t_sort)

        out = []
        for r in extract_records(result):
            d = values_by_name(self.cache, self.base_id, S.TEMPLATE_TABLE, r)
            d["recordId"] = get_record_id(r)
            out.append(d)
        t_parse = time.time()
        logger.debug("[list_templates] 结果解析耗时: %.3fs, 记录数: %d", t_parse - t_query, len(out))
        logger.debug("[list_templates] 总耗时: %.3fs", t_parse - t_start)
        return out

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _find_record(self, template_id: str) -> Optional[Dict[str, Any]]:
        field_id = self.cache.get_field_id(
            self.base_id, S.TEMPLATE_TABLE, "template_id"
        )
        filters = F.and_(F.eq(field_id, template_id))
        result = self.client.aitable_record_query(
            self.base_id, self._table_id(), filters, limit=1
        )
        records = extract_records(result)
        return records[0] if records else None

    def _find_record_id(self, template_id: str) -> Optional[str]:
        rec = self._find_record(template_id)
        return get_record_id(rec) if rec else None

    def update_template_instance_meta(
        self,
        template_id: str,
        *,
        active_instance_id: Optional[str] = None,
        managed_instance_ids: Optional[str] = None,
    ) -> str:
        """专用于更新模版的任务实例表元数据（active_instance_id / managed_instance_ids）。

        Args:
            template_id: 模版 ID。
            active_instance_id: 当前活跃任务实例表 ID（None 表示不更新该字段）。
            managed_instance_ids: 历史任务实例表 ID 列表，JSON 数组字符串（None 表示不更新）。

        Returns:
            模版记录的 recordId。

        Raises:
            StoreTaskDispatcherError: 模版不存在。
        """
        fields: Dict[str, Any] = {}
        if active_instance_id is not None:
            fields["active_instance_id"] = active_instance_id
        if managed_instance_ids is not None:
            fields["managed_instance_ids"] = managed_instance_ids
        if not fields:
            rid = self._find_record_id(template_id)
            if not rid:
                raise StoreTaskDispatcherError(f"模板 {template_id!r} 不存在")
            return rid
        return self.update_template(template_id, **fields)


__all__ = [
    "TemplateManager",
    "generate_template_id",
    "parse_custom_fields",
    "build_custom_fields_json",
    "SUPPORTED_CUSTOM_FIELD_TYPES",
]
