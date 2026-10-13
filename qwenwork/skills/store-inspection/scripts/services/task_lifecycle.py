"""任务生命周期管理模块。

从 Dispatcher 中提取任务生命周期管理相关方法，封装为 TaskLifecycle 类。
负责任务的创建、复用、表管理、form_url 处理等核心逻辑。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import time

from scripts.services.dispatch_helpers import (
    DispatchSummary,
    _calc_deadline,
    _extract_form_link,
    _extract_records,
    _find_table_id_by_name,
    _is_valid_share_link,
    _prompt_user_for_share_link,
    make_instance_table_name,
    make_task_id,
)
from scripts.domain.form_link_builder import extract_form_share_url
from scripts.domain import schema as S
from scripts.domain.records import extract_url_value, values_by_name
from scripts.domain.exceptions import DispatchError, StoreTaskDispatcherError
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache
from scripts.services.template_service import parse_custom_fields
from scripts.utils.datetime_format import fmt_date

logger = logging.getLogger(__name__)


class TaskLifecycle:
    """任务生命周期管理类。

    负责：
    - 确保任务就绪（ensure_task）
    - 解析已有任务（_resolve_existing_task）
    - 按表名查找同天任务（_find_same_day_task_by_table_name）
    - 新建任务（_ensure_new_task）
    - 复用任务（_ensure_existing_task）
    - 基于已有任务派发（dispatch_with_existing_task）
    """

    def __init__(
        self,
        client: DwsClient,
        cache: MappingCache,
        base_id: Optional[str] = None,
        table_manager=None,
        task_record_service=None,
        template_manager=None,
        notification_service=None,
    ) -> None:
        self.client = client
        self.cache = cache
        self._base_id = base_id
        self.table_manager = table_manager
        self.task_record_service = task_record_service
        self.template_manager = template_manager
        self.notification_service = notification_service

    @property
    def base_id(self) -> str:
        bid = self._base_id or get_base_id()
        if not bid:
            raise StoreTaskDispatcherError("未初始化：config.json 中无 base_id")
        return bid

    # ==================================================================
    # 内部工具方法
    # ==================================================================

    def _auto_fetch_form_url(
        self,
        instance_table_id: str,
        form_view_id: str,
        max_retries: int = 3,
        retry_interval: int = 2,
    ) -> str:
        """通过 view get 详情自动获取表单分享链接（含重试机制）。

        与新建分支（table_manager._create_form_view）保持一致的重试逻辑：
        最多重试 max_retries 次，每次间隔 retry_interval 秒，
        依次尝试 _extract_form_link 和 extract_form_share_url 两种提取方式。

        Returns:
            合法的表单分享链接；获取失败返回空字符串。
        """
        for attempt in range(1, max_retries + 1):
            detail = None
            try:
                detail = self.client.aitable_view_get_detail(
                    self.base_id, instance_table_id, form_view_id,
                )
                form_link = _extract_form_link(detail)
                if form_link:
                    logger.info(
                        "复用任务自动获取 form_url 成功 (attempt %d/%d): %s",
                        attempt, max_retries, form_link,
                    )
                    return form_link
            except Exception as exc:
                logger.warning(
                    "复用任务获取表单视图详情失败 table=%s view=%s "
                    "(attempt %d/%d): %s",
                    instance_table_id, form_view_id, attempt, max_retries, exc,
                )

            # fallback：从 formInfo.shareUuid 拼接分享链接
            if detail:
                form_link = extract_form_share_url(detail)
                if form_link:
                    logger.info(
                        "复用任务从 shareUuid 拼接 form_url 成功 (attempt %d/%d): %s",
                        attempt, max_retries, form_link,
                    )
                    return form_link

            if attempt < max_retries:
                logger.info(
                    "表单链接尚未就绪，等待 %d 秒后重试 (%d/%d)...",
                    retry_interval, attempt, max_retries,
                )
                time.sleep(retry_interval)

        logger.warning(
            "复用任务自动获取 form_url 失败（已重试 %d 次），将降级到人工引导",
            max_retries,
        )
        return ""

    # ==================================================================
    # 阶段 1：创建/复用派发任务（ensure_task）
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
        """阶段 1：创建或复用派发任务，确保所有资源（表 + form_url）就绪。

        Args:
            template: 模板 dict。必须包含 ``template_id`` 和 ``name``。
            now: 任务发起时间，默认当前时间。
            reuse_strategy:
                - ``"new"``：强制创建新任务（建新表 + 引导分享新 form_url）
                - ``"latest"``：复用当天最新一条任务记录（缺表自动重建，
                  form_url 不合法时引导重新分享）
                - ``"<task_id>"``：指定 task_id 复用（同 latest 行为，
                  但用指定的任务记录而非最新一条）
            form_url: 外部传入的表单分享链接（可选）。传入合法链接时跳过
                交互式引导，直接写入任务记录。适用于 Agent 在对话中拿到
                用户粘贴的链接后回传给 CLI 的场景。
            existing_task: 调用方已知的任务记录 dict（可选）。传入时直接
                走复用分支，完全跳过 ``_resolve_existing_task`` 的查询逻辑。
                用于跨天任务复用场景——``query_today_tasks`` 只查当天，
                传入已知记录可避免跨天任务被误判为"找不到"而降级新建。
            force_new: 为 True 时跳过 ``_find_same_day_task_by_table_name``
                最终防线，直接新建任务。仅在用户**明确**通过 ``--reuse new``
                表达"我要新建"意图时由 CLI 层传入，禁止 Agent 自动触发场景
                使用（防止 Agent 误触发重复建表）。

        Returns:
            task_context dict，字段：

            - ``task_id``: 任务 ID
            - ``instance_table_name``: 巡检表名
            - ``instance_table_id``: 巡检表 ID
            - ``notification_table_name``: 通知表名
            - ``notification_table_id``: 通知表 ID
            - ``notif_field_map``: 通知表字段名→fieldId 映射
            - ``form_url``: 合法的表单分享链接（空字符串表示用户跳过分享）
            - ``form_view_id``: 表单视图 ID
            - ``is_new``: True 表示本次新建，False 表示复用

        Raises:
            DispatchError: 模板缺少 template_id；或新建任务时建表失败。
        """
        now = now or datetime.now()
        tpl_id = template.get("template_id")
        if not tpl_id:
            raise DispatchError("模版缺少 template_id 字段")

        # 调用方已知任务记录时，直接复用，跳过所有查询（避免跨天任务降级新建）
        if existing_task is not None:
            return self._ensure_existing_task(
                template, existing_task, now=now, form_url=form_url,
                extra_info=extra_info,
            )

        # 复用分支：根据策略找到 existing_task
        if reuse_strategy != "new":
            resolved = self._resolve_existing_task(tpl_id, reuse_strategy, now)
            if resolved:
                return self._ensure_existing_task(
                    template, resolved, now=now, form_url=form_url,
                    extra_info=extra_info,
                )
            logger.debug(
                "ensure_task: 未找到可复用任务（strategy=%s），降级为新建",
                reuse_strategy,
            )
            # 找不到就降级为新建（不报错，避免阻塞）

        # ── 新建分支前的最终防线（防重复创建）────────────────────────
        # 在真正建表之前，再做一次"按表名查同天同模版任务"的兜底检查：
        # 即使 reuse_strategy=="new" 或 query_today_tasks 偶发返回空导致降级，
        # 只要 AI表格 里已经存在同名任务表（说明今天已经派发过该模版），就强制
        # 复用，绝不重复建表。这样可以彻底消除"模型在收到 form_url 后重新跑
        # dispatch run / dispatch task 导致重复建表"的故障。
        #
        # 例外：force_new=True 时（用户明确通过 --reuse new 表达新建意图），
        # 跳过此防线，尊重用户意图直接新建。
        if not force_new:
            same_day_task = self._find_same_day_task_by_table_name(template, now)
            if same_day_task:
                logger.warning(
                    "ensure_task: 检测到当天已有同名任务表（task_id=%s, table=%s），"
                    "强制复用以避免重复创建（原 reuse_strategy=%s）",
                    same_day_task.get("task_id"),
                    same_day_task.get("instance_table_name"),
                    reuse_strategy,
                )
                return self._ensure_existing_task(
                    template, same_day_task, now=now, form_url=form_url,
                    extra_info=extra_info,
                )

        # 新建分支
        return self._ensure_new_task(
            template, now=now, form_url=form_url, extra_info=extra_info,
        )

    # ------------------------------------------------------------------
    # ensure_task 内部辅助：解析已有任务、新建任务、复用任务
    # ------------------------------------------------------------------

    def _resolve_existing_task(
        self,
        template_id: str,
        reuse_strategy: str,
        now: datetime,
    ) -> Optional[Dict[str, Any]]:
        """根据 reuse_strategy 找到要复用的 existing_task 记录。

        - reuse_strategy="latest" → 当天最新一条
        - reuse_strategy=<task_id> → 当天匹配 task_id 的那条
        """
        today = fmt_date(now)
        today_tasks = self.task_record_service.query_today_tasks(template_id, today)
        if not today_tasks:
            return None
        if reuse_strategy == "latest":
            return today_tasks[0]
        # 否则视为指定 task_id
        for task in today_tasks:
            if task.get("task_id") == reuse_strategy:
                return task
        return None

    def _find_same_day_task_by_table_name(
        self,
        template: Dict[str, Any],
        now: datetime,
    ) -> Optional[Dict[str, Any]]:
        """按"当天该模版预计生成的任务表名"在任务记录中查找已存在的任务。

        作为新建任务前的最终防线，专治以下故障场景：
        - 用户/Agent 误用 ``--reuse new`` 重复触发派发
        - ``query_today_tasks`` 因网络抖动返回空，触发 ``latest → new`` 降级

        匹配规则（必须同时满足）：
        1. ``template_id`` 匹配
        2. ``instance_table_name == make_instance_table_name(template.name, now)``
        3. ``task_date`` 以当天日期开头（防止 per_year 等粗粒度表名跨天误匹配）

        Returns:
            匹配到的任务记录 dict（同 ``query_today_tasks`` 项结构）；找不到返回 None。
        """
        tpl_id = template.get("template_id")
        if not tpl_id:
            return None
        expected_table_name = make_instance_table_name(
            template.get("name", "巡店任务"), now,
        )
        today = fmt_date(now)
        try:
            base_payload = self.client.aitable_base_get(self.base_id)
            task_record_table_id = _find_table_id_by_name(
                base_payload, S.TASK_RECORD_TABLE,
            )
            if not task_record_table_id:
                return None
            payload = self.client.aitable_record_query(
                self.base_id, task_record_table_id,
            )
            records = _extract_records(payload)
            candidates: List[Dict[str, Any]] = []
            for r in records:
                # cells 以 fieldId 为 key，需翻译回 fieldName 才能按名称过滤
                fields = values_by_name(
                    self.cache, self.base_id, S.TASK_RECORD_TABLE, r
                )
                if fields.get("template_id") != tpl_id:
                    continue
                if fields.get("instance_table_name") != expected_table_name:
                    continue
                # 必须是当天的任务，防止 per_year 粒度下跨天旧任务被误匹配
                task_date = fields.get("task_date", "")
                if not task_date.startswith(today):
                    continue
                candidates.append({
                    "record_id": r.get("recordId") or r.get("id", ""),
                    **fields,
                })
            if not candidates:
                return None
            # 同名任务理论上当天只应有一条，多条时取最新的，避免歧义
            candidates.sort(
                key=lambda x: x.get("task_date", ""), reverse=True,
            )
            return candidates[0]
        except Exception as exc:
            # 此函数是防重复建表的最终防线，查询失败不能静默返回 None，
            # 否则调用方会误判为"无同名任务"而继续新建，导致重复建表。
            raise DispatchError(
                f"_find_same_day_task_by_table_name 查询失败，"
                f"为防止重复建表已中止派发: {exc}"
            ) from exc

    def _ensure_new_task(
        self,
        template: Dict[str, Any],
        *,
        now: datetime,
        form_url: Optional[str] = None,
        extra_info: Optional[str] = None,
    ) -> Dict[str, Any]:
        """新建任务的完整流程：占位 → 建表 → 引导分享 → 回写。"""
        tpl_id = template["template_id"]
        granularity = template.get("granularity") or "per_year"
        task_id = make_task_id(tpl_id, now)
        instance_table_name = make_instance_table_name(template.get("name", "巡店任务"), now, granularity)
        notification_table_name = S.build_notification_table_name(instance_table_name)

        # 计算计划截止时间（deadline）：由 expected_duration 解析后加到 now 上
        expected_duration = template.get("expected_duration") or ""
        deadline_value, deadline_str = _calc_deadline(now, expected_duration)

        # 1. 占位写入任务记录（status=进行中，表 ID / form_url 留空）
        empty_summary = DispatchSummary(
            task_id=task_id,
            instance_table_name=instance_table_name,
            template_id=tpl_id,
            total=0,
        )
        self.task_record_service.upsert_task_record(
            task_id=task_id, template=template,
            instance_table_name=instance_table_name, instance_table_id="",
            notification_table_name=notification_table_name,
            notification_table_id="",
            summary=empty_summary, now=now,
            form_url="", form_view_id="",
            deadline_value=deadline_value,
            status_override="进行中",
            extra_info=extra_info,
        )

        # 2. 创建巡检表 + 通知表
        custom_fields = parse_custom_fields(template.get("custom_fields") or "")
        instance_table_id, form_base_link, form_view_id, _ = self.table_manager._create_task_instance(
            instance_table_name, tpl_id, task_id, custom_fields
        )
        notification_table_id, notif_field_map = self.table_manager._create_task_notification(
            notification_table_name
        )

        # 3. 表 ID 立即回写任务记录（哪怕后续引导分享中断也不丢失）
        self.task_record_service.upsert_task_record(
            task_id=task_id, template=template,
            instance_table_name=instance_table_name, instance_table_id=instance_table_id,
            notification_table_name=notification_table_name,
            notification_table_id=notification_table_id,
            summary=empty_summary, now=now,
            form_url=form_base_link if _is_valid_share_link(form_base_link) else "",
            form_view_id=form_view_id,
            deadline_value=deadline_value,
            status_override="进行中",
            extra_info=extra_info,
        )

        # 4. form_url 处理：外部传入合法链接时跳过引导，否则引导用户分享
        if form_url and _is_valid_share_link(form_url):
            form_base_link = form_url
        elif not _is_valid_share_link(form_base_link):
            form_base_link = _prompt_user_for_share_link(
                instance_table_id=instance_table_id,
                form_view_id=form_view_id,
                base_id=self.base_id,
                current_link="",
            )

        # 5. 拿到合法 form_url 后再次回写
        if _is_valid_share_link(form_base_link):
            self.task_record_service.upsert_task_record(
                task_id=task_id, template=template,
                instance_table_name=instance_table_name, instance_table_id=instance_table_id,
                notification_table_name=notification_table_name,
                notification_table_id=notification_table_id,
                summary=empty_summary, now=now,
                form_url=form_base_link, form_view_id=form_view_id,
                status_override="进行中",
                extra_info=extra_info,
            )

        return {
            "task_id": task_id,
            "instance_table_name": instance_table_name,
            "instance_table_id": instance_table_id,
            "notification_table_name": notification_table_name,
            "notification_table_id": notification_table_id,
            "notif_field_map": notif_field_map,
            "form_url": form_base_link if _is_valid_share_link(form_base_link) else "",
            "form_view_id": form_view_id,
            "is_new": True,
            "deadline_str": deadline_str,
            "extra_info": extra_info or "",
        }

    def _ensure_existing_task(
        self,
        template: Dict[str, Any],
        existing_task: Dict[str, Any],
        *,
        now: datetime,
        form_url: Optional[str] = None,
        extra_info: Optional[str] = None,
    ) -> Dict[str, Any]:
        """复用任务的完整流程：补齐缺失的表 + 校验/补齐 form_url。

        ``extra_info`` 不为 None 时会覆盖任务记录的 ``extra_info`` 字段（允许
        重发时换一段附加信息）；为 None 时保留任务记录中已有的 extra_info。
        """
        tpl_id = template["template_id"]
        task_id = existing_task.get("task_id", "")
        instance_table_name = existing_task.get("instance_table_name", "")
        instance_table_id = existing_task.get("instance_table_id", "")
        notification_table_name = (
            existing_task.get("notification_table_name", "")
            or S.build_notification_table_name(instance_table_name)
        )
        notification_table_id = existing_task.get("notification_table_id", "")
        # 兼容老版 form_base_link 字段；form_url 是 url 类型字段，读出来是
        # {"link": "...", "text": "..."} 的 dict，需用 extract_url_value 解包
        existing_form_url = (
            extract_url_value(existing_task.get("form_url"))
            or extract_url_value(existing_task.get("form_base_link"))
            or ""
        )
        form_view_id = existing_task.get("form_view_id", "")

        # 1. 巡检表是否存在；不存在则重建
        if not self.table_manager._table_exists(instance_table_id):
            if instance_table_id:
                logger.warning(
                    "复用任务 %s：原巡检表 %s 已不存在，自动重建",
                    task_id, instance_table_id,
                )
            else:
                logger.debug("复用任务 %s：缺少 instance_table_id，自动建表", task_id)
            custom_fields = parse_custom_fields(template.get("custom_fields") or "")
            instance_table_id, new_form_link, new_form_view_id, _ = (
                self.table_manager._create_task_instance(
                    instance_table_name, tpl_id, task_id, custom_fields,
                )
            )
            # 原 form_url 不合法时，用新表的链接覆盖（也可能仍不合法）
            if not _is_valid_share_link(existing_form_url):
                existing_form_url = new_form_link
                form_view_id = new_form_view_id

        # 2. 通知表是否存在；不存在则重建
        if not self.table_manager._table_exists(notification_table_id):
            if notification_table_id:
                logger.warning(
                    "复用任务 %s：原通知表 %s 已不存在，自动重建",
                    task_id, notification_table_id,
                )
            notification_table_id, notif_field_map = (
                self.table_manager._create_task_notification(notification_table_name)
            )
        else:
            notif_field_map = self.table_manager._load_field_map(notification_table_id)

        # 3. form_url 处理：外部传入合法链接时跳过引导，否则引导用户重新分享
        if form_url and _is_valid_share_link(form_url):
            existing_form_url = form_url
            # 外部传入合法链接，立即持久化到任务记录
            empty_summary = DispatchSummary(
                task_id=task_id, instance_table_name=instance_table_name,
                template_id=tpl_id, total=0,
            )
            self.task_record_service.upsert_task_record(
                task_id=task_id, template=template,
                instance_table_name=instance_table_name, instance_table_id=instance_table_id,
                notification_table_name=notification_table_name,
                notification_table_id=notification_table_id,
                summary=empty_summary, now=now,
                form_url=existing_form_url,
                form_view_id=form_view_id,
                status_override="进行中",
                extra_info=extra_info,
            )
        elif not _is_valid_share_link(existing_form_url):
            # 3a. 自动获取：通过 view get 详情提取 shareUuid 拼接分享链接
            #     与新建分支（table_manager._create_form_view）保持一致的重试机制
            if instance_table_id and form_view_id:
                auto_form_url = self._auto_fetch_form_url(
                    instance_table_id, form_view_id,
                )
                if auto_form_url:
                    existing_form_url = auto_form_url

            # 3b. 自动获取失败，降级到人工引导
            if not _is_valid_share_link(existing_form_url):
                existing_form_url = _prompt_user_for_share_link(
                    instance_table_id=instance_table_id,
                    form_view_id=form_view_id,
                    base_id=self.base_id,
                    current_link="",
                )
            # 拿到合法链接后立即回写任务记录（持久化，下次复用直接读）
            if _is_valid_share_link(existing_form_url):
                empty_summary = DispatchSummary(
                    task_id=task_id, instance_table_name=instance_table_name,
                    template_id=tpl_id, total=0,
                )
                self.task_record_service.upsert_task_record(
                    task_id=task_id, template=template,
                    instance_table_name=instance_table_name, instance_table_id=instance_table_id,
                    notification_table_name=notification_table_name,
                    notification_table_id=notification_table_id,
                    summary=empty_summary, now=now,
                    form_url=existing_form_url,
                    form_view_id=form_view_id,
                    status_override="进行中",
                    extra_info=extra_info,
                )
        elif extra_info is not None:
            # form_url 已合法、未触发回写但调用方传入了新的 extra_info：
            # 单独 upsert 一次，把 extra_info 持久化到任务记录。
            empty_summary = DispatchSummary(
                task_id=task_id, instance_table_name=instance_table_name,
                template_id=tpl_id, total=0,
            )
            self.task_record_service.upsert_task_record(
                task_id=task_id, template=template,
                instance_table_name=instance_table_name, instance_table_id=instance_table_id,
                notification_table_name=notification_table_name,
                notification_table_id=notification_table_id,
                summary=empty_summary, now=now,
                form_url=existing_form_url,
                form_view_id=form_view_id,
                status_override="进行中",
                extra_info=extra_info,
            )

        # 合并 extra_info：调用方传入新值则覆盖，否则沿用任务记录中已有的值
        merged_extra_info = (
            extra_info
            if extra_info is not None
            else (existing_task.get("extra_info") or "")
        )

        return {
            "task_id": task_id,
            "instance_table_name": instance_table_name,
            "instance_table_id": instance_table_id,
            "notification_table_name": notification_table_name,
            "notification_table_id": notification_table_id,
            "notif_field_map": notif_field_map,
            "form_url": existing_form_url if _is_valid_share_link(existing_form_url) else "",
            "form_view_id": form_view_id,
            "is_new": False,
            "extra_info": merged_extra_info,
        }

    def dispatch_with_existing_task(
        self,
        template: Dict[str, Any],
        existing_task: Dict[str, Any],
        *,
        skip_dispatched: bool = True,
        now: Optional[datetime] = None,
    ) -> DispatchSummary:
        """复用已有任务对目标门店补发/重发通知（= ensure_task + notify_targets）。

        本方法是 2 阶段流程的薄壳串联，保留向后兼容。新代码建议直接调用
        ``ensure_task(reuse_strategy=<task_id>)`` + ``notify_targets`` 以获
        得更细粒度的控制（如逐店重复通知确认）。

        Args:
            template: 模版 dict。
            existing_task: 任务记录 dict，至少包含 ``task_id`` 字段。
            skip_dispatched: True=已派发门店一律跳过；False=已派发门店一律重发。
                如需逐店询问，请改用 ``notify_targets(duplicate_strategy="ask")``。
            now: 派发时间，默认当前时间。
        """
        now = now or datetime.now()
        task_id = existing_task.get("task_id", "")

        # 阶段 1：复用指定任务（按需补齐表 + 校验/补齐 form_url）
        task_context = self.ensure_task(
            template, now=now, reuse_strategy=task_id or "latest",
        )

        # 阶段 2：根据 skip_dispatched 决定 duplicate_strategy
        duplicate_strategy = "skip" if skip_dispatched else "resend"
        return self.notification_service.notify_targets(
            template,
            task_context,
            duplicate_strategy=duplicate_strategy,
            now=now,
        )
