"""派发引擎（Facade 模式）。

将原 3331 行的单体 Dispatcher 拆分为 7 个职责清晰的子模块后，
本文件保留为 Facade 类，通过组合子模块提供统一的公共 API。

子模块：
- dispatch_helpers: 纯工具函数 + DispatchSummary dataclass
- table_manager: 动态表管理（建表、字段、表单视图）
- task_record_service: 任务记录 CRUD
- notification_service: 通知派发服务
- instance_service: 任务实例查询与更新
- task_lifecycle: 任务生命周期管理（ensure_task 等）
"""

from __future__ import annotations

import json
import logging
import random  # noqa: F401 — 向后兼容，测试 patch scripts.services.dispatcher.random.choices
import string  # noqa: F401
from dataclasses import dataclass, field  # noqa: F401
from datetime import datetime
from typing import Any, Dict, List, Optional

from scripts.domain import filters as F  # noqa: F401
from scripts.domain import schema as S  # noqa: F401
from scripts.domain.records import (  # noqa: F401
    build_cell_value,
    cells_by_name,
    extract_cell_value as _extract_cell_value,
    extract_records,
    extract_url_value,
    extract_url_value as _extract_url_value,
    get_record_id,
    values_by_name,
)
from scripts.domain.form_link_builder import build as build_form_link  # noqa: F401

from scripts.domain.exceptions import DispatchError, StoreTaskDispatcherError
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache
from scripts.services.messenger import Messenger
from scripts.services.store_service import StoreManager
from scripts.services.template_service import TemplateManager

# 子模块导入
from scripts.services.dispatch_helpers import (  # noqa: F401 — 向后兼容重导出
    DispatchSummary,
    _calc_deadline,
    _extract_fields_from_table,
    _extract_form_link,
    _extract_record_id,
    _extract_records,
    _extract_table_id,
    _extract_view_id,
    _find_table_id_by_name,
    _is_valid_share_link,
    _parse_notified_at,
    _prompt_resend_for_store,
    _prompt_user_for_share_link,
    _resolve_task_record_status,
    make_instance_table_name,
    make_notification_id,
    make_task_id,
)
from scripts.services.table_manager import TableManager
from scripts.services.task_record_service import TaskRecordService
from scripts.services.notification_service import NotificationService
from scripts.services.instance_service import InstanceService
from scripts.services.task_lifecycle import TaskLifecycle

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dispatcher Facade
# ---------------------------------------------------------------------------

class Dispatcher:
    """派发引擎 Facade。

    通过组合 6 个子模块提供统一 API，保持与原始单体 Dispatcher 完全
    相同的公共方法签名，对外透明。

    支持两种构造方式：
    - 正常 ``__init__``：立即初始化子模块。
    - ``__new__`` 跳过构造（测试场景）：通过惰性初始化在首次访问时自动创建。
    """

    # 需要惰性初始化的子模块属性名
    _SUBMODULE_ATTRS = frozenset({
        "_table_manager", "_task_record_service", "_instance_service",
        "_notification_service", "_task_lifecycle",
    })

    def __init__(
        self,
        client: Optional[DwsClient] = None,
        cache: Optional[MappingCache] = None,
        base_id: Optional[str] = None,
        store_manager: Optional[StoreManager] = None,
        template_manager: Optional[TemplateManager] = None,
        messenger: Optional[Messenger] = None,
    ) -> None:
        self.client = client or DwsClient()
        self.cache = cache or MappingCache(client=self.client)
        self._base_id = base_id
        self.store_manager = store_manager or StoreManager(
            client=self.client, cache=self.cache, base_id=base_id
        )
        self.template_manager = template_manager or TemplateManager(
            client=self.client, cache=self.cache, base_id=base_id
        )
        self.messenger = messenger or Messenger(client=self.client)

        # ── 子模块实例化 ──────────────────────────────────────────
        self._init_submodules()

    def _init_submodules(self) -> None:
        """创建/重建所有子模块实例，使用当前 self 上的 client/cache 等属性。"""
        base_id = getattr(self, "_base_id", None)
        self._table_manager = TableManager(
            client=self.client, cache=self.cache, base_id=base_id,
        )
        self._task_record_service = TaskRecordService(
            client=self.client, cache=self.cache, base_id=base_id,
            table_manager=self._table_manager,
        )
        self._instance_service = InstanceService(
            client=self.client, cache=self.cache, base_id=base_id,
            table_manager=self._table_manager,
        )
        self._notification_service = NotificationService(
            client=self.client, cache=self.cache, base_id=base_id,
            table_manager=self._table_manager,
            messenger=self.messenger,
            store_manager=self.store_manager,
            task_record_service=self._task_record_service,
        )
        # 注入 query_filled_store_ids 回调（打破循环依赖）
        self._notification_service._query_filled_store_ids_fn = (
            self._instance_service.query_filled_store_ids
        )
        self._task_lifecycle = TaskLifecycle(
            client=self.client, cache=self.cache, base_id=base_id,
            table_manager=self._table_manager,
            task_record_service=self._task_record_service,
            template_manager=self.template_manager,
            notification_service=self._notification_service,
        )

    def __getattr__(self, name: str):
        """惰性初始化：当通过 __new__ 跳过 __init__ 时自动创建子模块。"""
        if name in self._SUBMODULE_ATTRS:
            # 检查是否有最基本的属性（client/cache）才能初始化
            if hasattr(self, "client") and hasattr(self, "cache"):
                self._init_submodules()
                return getattr(self, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    @property
    def base_id(self) -> str:
        bid = self._base_id or get_base_id()
        if not bid:
            raise StoreTaskDispatcherError("未初始化：config.json 中无 base_id")
        return bid

    # ==================================================================
    # 入口
    # ==================================================================

    def dispatch_template(
        self,
        template: Dict[str, Any],
        *,
        now: Optional[datetime] = None,
        reuse_strategy: str = "latest",
        form_url: Optional[str] = None,
        extra_info: Optional[str] = None,
    ) -> DispatchSummary:
        """对一个模版执行一次完整派发（= ensure_task + notify_targets）。

        本方法是 2 阶段流程的薄壳串联，保留向后兼容。
        新代码建议直接调用 ``ensure_task`` 和 ``notify_targets`` 以获得更细
        粒度的控制。

        Args:
            template: 模版 dict。
            now: 派发时间（默认当前时间）。
            reuse_strategy: 复用策略。
            form_url: 外部传入的表单分享链接。
            extra_info: 本次派发附加的额外信息。

        Returns:
            DispatchSummary。
        """
        now = now or datetime.now()
        tpl_id = template.get("template_id")
        if not tpl_id:
            raise DispatchError("模版缺少 template_id 字段")

        # 阶段 1：创建/复用任务
        task_context = self.ensure_task(
            template, now=now, reuse_strategy=reuse_strategy,
            form_url=form_url, extra_info=extra_info,
        )

        # 边界：解析目标若为空，提前返回
        targets = self._resolve_targets(template)
        if not targets:
            logger.warning("template %s has no target stores", tpl_id)
            return DispatchSummary(
                task_id=task_context["task_id"],
                instance_table_name=task_context["instance_table_name"],
                template_id=tpl_id,
                total=0,
            )

        # 阶段 2：派发给所有目标门店
        return self.notify_targets(
            template,
            task_context,
            duplicate_strategy="resend",
            now=now,
            extra_info=extra_info,
        )

    # ==================================================================
    # 阶段 1 委托：TaskLifecycle
    # ==================================================================

    def ensure_task(
        self,
        template: Dict[str, Any],
        *,
        now: Optional[datetime] = None,
        reuse_strategy: str = "new",
        form_url: Optional[str] = None,
        existing_task: Optional[Dict[str, Any]] = None,
        force_new: bool = False,
        extra_info: Optional[str] = None,
    ) -> Dict[str, Any]:
        """阶段 1：创建或复用派发任务，确保所有资源就绪。"""
        return self._task_lifecycle.ensure_task(
            template, now=now, reuse_strategy=reuse_strategy,
            form_url=form_url, existing_task=existing_task,
            force_new=force_new, extra_info=extra_info,
        )

    def dispatch_with_existing_task(
        self,
        template: Dict[str, Any],
        existing_task: Dict[str, Any],
        *,
        skip_dispatched: bool = True,
        now: Optional[datetime] = None,
    ) -> DispatchSummary:
        """复用已有任务对目标门店补发/重发通知。"""
        return self._task_lifecycle.dispatch_with_existing_task(
            template, existing_task,
            skip_dispatched=skip_dispatched, now=now,
        )

    # ==================================================================
    # 阶段 2 委托：NotificationService
    # ==================================================================

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
        """阶段 2：基于已有 task_context 给指定门店发通知。"""
        return self._notification_service.notify_targets(
            template, task_context,
            duplicate_strategy=duplicate_strategy,
            only_pending=only_pending,
            cooldown_seconds=cooldown_seconds,
            scope_desc=scope_desc,
            target_store_ids=target_store_ids,
            tags=tags, now=now, extra_info=extra_info,
            message_override=message_override,
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
        """查询通知明细。"""
        return self._notification_service.query_notification_details(
            notification_table_id, instance_table_id,
            status_filter=status_filter,
            notified_from=notified_from,
            notified_to=notified_to,
            stayed_over_minutes=stayed_over_minutes,
            limit=limit,
        )

    def query_pending_notifications(
        self,
        task_id: str,
        notification_table_id: str,
        instance_table_id: str,
    ) -> List[Dict[str, Any]]:
        """查询待处理通知。"""
        return self._notification_service.query_pending_notifications(
            task_id, notification_table_id, instance_table_id,
        )

    def query_recent_notified_store_ids(
        self,
        notification_table_id: str,
        cutoff_seconds: int,
        *,
        now: Optional[datetime] = None,
    ) -> set:
        """查询最近通知过的门店 ID 集合。"""
        return self._notification_service.query_recent_notified_store_ids(
            notification_table_id, cutoff_seconds, now=now,
        )

    def query_dispatched_store_ids(
        self, notification_table_id: str, task_id: str = ""
    ) -> set:
        """查询已派发门店 ID 集合。"""
        return self._notification_service.query_dispatched_store_ids(
            notification_table_id, task_id=task_id,
        )

    # ==================================================================
    # 任务记录 委托：TaskRecordService
    # ==================================================================

    def _upsert_task_record(self, **kwargs) -> None:
        """向「任务记录」固定表 upsert 一条派发元数据记录。"""
        return self._task_record_service.upsert_task_record(**kwargs)

    def query_today_tasks(
        self, template_id: str, today: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """查询当天同模版的任务列表。"""
        return self._task_record_service.query_today_tasks(template_id, today)

    def query_tasks(
        self,
        template_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """通用任务查询，支持多维度过滤。"""
        return self._task_record_service.query_tasks(
            template_id=template_id, status=status,
            date_from=date_from, date_to=date_to, limit=limit,
        )

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
        """更新任务记录的字段。"""
        return self._task_record_service.update_task(
            task_id, form_url=form_url, status=status,
            scope_desc=scope_desc, store_count=store_count,
            success_count=success_count, now=now,
        )

    # ==================================================================
    # 任务实例 委托：InstanceService
    # ==================================================================

    def query_filled_store_ids(self, instance_table_id: str) -> set:
        """查询已填写门店 ID 集合。"""
        return self._instance_service.query_filled_store_ids(instance_table_id)

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
        """查询动态任务实例表中的巡检记录。"""
        return self._instance_service.query_instances(
            task_id, field_filters=field_filters,
            filter_empty=filter_empty,
            filter_not_empty=filter_not_empty,
            store_id=store_id, limit=limit,
        )

    def update_instance_fields(
        self,
        task_id: str,
        record_id: str,
        field_values: Dict[str, Any],
    ) -> bool:
        """更新动态任务实例表中的自定义字段值。"""
        return self._instance_service.update_instance_fields(
            task_id, record_id, field_values,
        )

    # ==================================================================
    # 内部辅助（保留向后兼容）
    # ==================================================================

    def _resolve_targets(
        self,
        template: Dict[str, Any],
        *,
        target_store_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """解析模板的目标门店列表（全量拉取）。

        派发通知必须拿到完整门店清单，因此走 list_all_stores（DWS --all
        自动翻页，内置 200ms 防抖）。若指定了 target_store_ids 则按 ID
        精确查询，不走分页。
        """
        if target_store_ids:
            return self.store_manager.list_stores_by_ids(target_store_ids)
        return self.store_manager.list_all_stores(only_active=True, tags_any_of=tags)

    # 以下方法委托给子模块，保留以兼容测试和可能的内部引用

    # ── TableManager 委托 ────────────────────────────────────────
    def _load_field_map(self, table_id: str) -> Dict[str, str]:
        return self._table_manager._load_field_map(table_id)

    def _get_task_record_table_id(self) -> Optional[str]:
        return self._table_manager._get_task_record_table_id()

    def _find_table_id_by_table_name(self, table_name: str) -> Optional[str]:
        return self._table_manager._find_table_id_by_table_name(table_name)

    def _table_exists(self, table_id: str) -> bool:
        return self._table_manager._table_exists(table_id)

    def _create_ai_table(self, table_name, all_fields):
        return self._table_manager._create_ai_table(table_name, all_fields)

    def _create_task_instance(self, table_name, template_id, task_id, custom_fields):
        return self._table_manager._create_task_instance(
            table_name, template_id, task_id, custom_fields,
        )

    def _create_task_notification(self, table_name):
        return self._table_manager._create_task_notification(table_name)

    def _get_visible_field_ids(self, table_id, custom_field_names):
        return self._table_manager._get_visible_field_ids(table_id, custom_field_names)

    def _create_form_view(self, table_id, visible_field_ids=None):
        return self._table_manager._create_form_view(table_id, visible_field_ids)

    def _reuse_or_create_form_view(self, table_id, visible_field_ids=None):
        return self._table_manager._reuse_or_create_form_view(table_id, visible_field_ids)

    # ── NotificationService 委托 ─────────────────────────────────
    def _dispatch_one(self, **kwargs):
        return self._notification_service._dispatch_one(**kwargs)

    def _write_notification(self, **kwargs):
        return self._notification_service._write_notification(**kwargs)

    def _find_notification_record_by_id(self, *args, **kwargs):
        return self._notification_service._find_notification_record_by_id(*args, **kwargs)

    @staticmethod
    def _build_notif_cells(field_values, notif_field_map, *, keep_empty=False):
        return NotificationService._build_notif_cells(
            field_values, notif_field_map, keep_empty=keep_empty,
        )

    def _update_notification_status(self, **kwargs):
        return self._notification_service._update_notification_status(**kwargs)

    # ── InstanceService 委托 ─────────────────────────────────────
    def _resolve_instance_table_id(self, task_id):
        return self._instance_service._resolve_instance_table_id(task_id)
