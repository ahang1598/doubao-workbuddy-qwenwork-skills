"""动态表管理服务 - TableManager。

从 Dispatcher 中提取的动态表管理相关方法，负责：
- AI 表格创建与管理
- 表单视图创建与分享
- 字段映射加载
- 通知表创建
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from scripts.domain import schema as S
from scripts.domain.ai_prompt_builder import build_ai_field_specs_from_custom_fields
from scripts.domain.exceptions import DispatchError, DwsError, StoreTaskDispatcherError
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache

# 从 dispatch_helpers 导入辅助函数
from scripts.services.dispatch_helpers import (
    _extract_fields_from_table,
    _extract_form_link,
    _extract_table_id,
    _extract_view_id,
    _find_table_id_by_name,
    _is_valid_share_link,
)
from scripts.domain.form_link_builder import extract_form_share_url

logger = logging.getLogger(__name__)


class TableManager:
    """动态表管理器，封装 AI 表格的创建、查询和管理操作。

    Attributes:
        client: DWS 客户端实例。
        cache: 映射缓存实例。
        base_id: Base ID（从配置获取）。
    """

    def __init__(
        self,
        client: DwsClient,
        cache: MappingCache,
        base_id: str | None = None,
    ) -> None:
        """初始化 TableManager。

        Args:
            client: DWS 客户端实例。
            cache: 映射缓存实例。
            base_id: Base ID，为空时从配置自动获取。
        """
        self.client = client
        self.cache = cache
        self._base_id = base_id

    @property
    def base_id(self) -> str:
        """获取 AI表格 ID，优先使用构造时传入的值，否则从配置获取。

        Returns:
            AI表格 ID 字符串。
        """
        if self._base_id:
            return self._base_id
        return get_base_id()

    def _create_ai_table(
        self,
        table_name: str,
        all_fields: List[Dict[str, Any]],
    ) -> str:
        """统一的 AI 表格创建接口，所有建表逻辑共用此方法。

        流程：
        1. 字段拆分：按 TABLE_CREATE_FIELD_LIMIT（15）拆分为 phase1 / phase2
        2. 首次创建：调用 aitable_table_create 携带 phase1 字段建表
        3. 补齐字段：若有 phase2，分批调用 aitable_field_create 追加；
           建表后回查实际字段，对静默丢失的字段再次补齐
        4. 补齐失败则中止：二次回查仍有缺失字段时抛 DispatchError，
           避免静默吞掉字段导致后续写入/展示异常

        Args:
            table_name: 要创建的表名。
            all_fields: 完整字段列表（按期望顺序）。

        Returns:
            新建表的 tableId。

        Raises:
            DispatchError: 建表失败、未返回 tableId、或字段补齐后仍有缺失时抛出。
        """
        # 步骤 1：字段拆分
        # AI 字段（带 aiConfig）不支持通过 table create --fields 创建，
        # 必须在建表后通过 field create 单独追加。
        regular_fields = [f for f in all_fields if "aiConfig" not in f]
        ai_fields = [f for f in all_fields if "aiConfig" in f]
        phase1 = regular_fields[: S.TABLE_CREATE_FIELD_LIMIT]
        phase2 = regular_fields[S.TABLE_CREATE_FIELD_LIMIT :] + ai_fields

        # 步骤 2：首次创建（携带 phase1 字段）
        try:
            payload = self.client.aitable_table_create(self.base_id, table_name, phase1)
        except DwsError as exc:
            raise DispatchError(f"创建表 {table_name!r} 失败: {exc}") from exc

        table_id = _extract_table_id(payload)
        if not table_id:
            raise DispatchError(
                f"创建表 {table_name!r} 后未返回 tableId，原始响应: {payload!r}"
            )
        logger.debug("table created: %s -> %s", table_name, table_id)

        # 步骤 3：补齐 phase2 字段（分批追加）
        if phase2:
            try:
                for i in range(0, len(phase2), S.FIELD_CREATE_LIMIT):
                    chunk = phase2[i : i + S.FIELD_CREATE_LIMIT]
                    self.client.aitable_field_create(self.base_id, table_id, chunk)
            except DwsError as exc:
                raise DispatchError(
                    f"表 {table_name!r} phase2 字段补齐失败: {exc}"
                ) from exc

        # 步骤 3b：回查实际字段，补齐 dws 静默丢失的字段
        # dws 对带 config.options 的字段类型有时会静默丢字段，必须回查并补齐
        actual_field_map = self._load_field_map(table_id)
        expected_names = [f["name"] for f in all_fields]
        missing_names = [name for name in expected_names if name not in actual_field_map]
        if missing_names:
            logger.warning(
                "表 %s 建表后字段缺失，尝试补齐: missing=%s expected=%d actual=%d",
                table_name, missing_names, len(expected_names), len(actual_field_map),
            )
            missing_field_defs = [f for f in all_fields if f["name"] in set(missing_names)]
            try:
                for i in range(0, len(missing_field_defs), S.FIELD_CREATE_LIMIT):
                    chunk = missing_field_defs[i : i + S.FIELD_CREATE_LIMIT]
                    self.client.aitable_field_create(self.base_id, table_id, chunk)
            except DwsError as exc:
                raise DispatchError(
                    f"表 {table_name!r} 缺失字段补齐失败 missing={missing_names}: {exc}"
                ) from exc

            # 步骤 4：二次回查，补齐失败则中止
            actual_field_map = self._load_field_map(table_id)
            still_missing = [name for name in expected_names if name not in actual_field_map]
            if still_missing:
                raise DispatchError(
                    f"表 {table_name!r} 字段创建不完整，补齐后仍缺失 {still_missing}。"
                    f"这是严重问题，已中止执行。"
                    f"请检查字段定义（特别是 singleSelect/multipleSelect 的 options、"
                    f"type 拼写等）后重试。"
                )

        return table_id

    def _create_task_instance(
        self,
        table_name: str,
        template_id: str,
        task_id: str,
        custom_fields: List[Dict[str, Any]],
    ) -> tuple:
        """动态创建任务表，返回 (tableId, form_base_link, form_view_id, visible_field_ids) 元组。

        - tableId: 新建任务表的 ID
        - form_base_link: 表单视图的分享链接（空字符串表示创建失败）
        - form_view_id: 表单视图 ID
        - visible_field_ids: 自定义字段的 fieldId 列表（用于表单只显示这些字段）

        字段 = 骨架字段 + 模版自定义字段。
        建表逻辑统一由 _create_ai_table 处理（字段拆分 → 首次创建 → 补齐字段 → 补齐失败中止）。
        建表成功后自动创建 FormDesigner 表单视图并提取表单链接。

        关键校验：
        1. 自定义字段名禁止与骨架字段重名（dws 会拒绝整张表创建，且报错信息不直观）
        2. 自定义字段名禁止重复
        """
        # 1. 入口校验：与骨架字段重名 / 自定义字段名重复
        skeleton_names = set(S.TASK_INSTANCE_SKELETON_FIELD_NAMES)
        custom_names: List[str] = []
        seen_custom: set = set()
        for f in custom_fields:
            name = f.get("name")
            if not name:
                raise DispatchError(
                    f"自定义字段缺少 name: {f!r}，请检查模版的 custom_fields 配置"
                )
            if name in skeleton_names:
                raise DispatchError(
                    f"自定义字段名 {name!r} 与系统骨架字段冲突（骨架字段为 "
                    f"{sorted(skeleton_names)}），请改名后重试"
                )
            if name in seen_custom:
                raise DispatchError(
                    f"自定义字段名 {name!r} 重复，请检查模版的 custom_fields 配置"
                )
            seen_custom.add(name)
            custom_names.append(name)

        # 1.1 计算"对店长可见"的自定义字段名（剔除 hidden=True 的字段）。
        # hidden 字段仍会被建表创建并支持通过 prefill 写入与服务端读取，
        # 仅在表单视图的 visibleFieldIds 中被排除。
        hidden_custom_names = set(S.get_hidden_custom_field_names(custom_fields))
        visible_custom_names = [n for n in custom_names if n not in hidden_custom_names]

        # 2. 拼装完整字段列表（骨架字段 + 自定义字段）
        all_fields = S.build_task_instance_fields(custom_fields)

        # ── 兜底：同名表已存在则直接复用，禁止重复创建 ─────────────
        # 这是底层最后一道防线：即使上层逻辑误判走到了"新建"分支，只要 AI表格 里
        # 已经存在同名任务表（最常见的场景：当天该模版已派发过一次），就直接
        # 复用其 tableId，避免出现两张「每日巡检-20260426」的重复表。
        existing_table_id = self._find_table_id_by_table_name(table_name)
        if existing_table_id:
            logger.warning(
                "_create_task_instance: AI表格 中已存在同名任务表，直接复用以避免重复创建 "
                "table_name=%s table_id=%s",
                table_name, existing_table_id,
            )
            table_id = existing_table_id
            # 复用已有表时，不重复建字段：直接用现有字段做后续处理。
            # 表单视图也尝试从已有视图中查找；找不到再建。
            # 使用 visible_custom_names（已剔除 hidden=True 字段），保证复用场景下
            # 隐藏字段也不会进入 visibleFieldIds。
            visible_field_ids = self._get_visible_field_ids(table_id, visible_custom_names)
            form_base_link, form_view_id = self._reuse_or_create_form_view(
                table_id, visible_field_ids,
            )
            return table_id, form_base_link, form_view_id, visible_field_ids

        # 3. 统一建表接口：字段拆分 → 首次创建 → 补齐字段 → 补齐失败中止
        table_id = self._create_ai_table(table_name, all_fields)

        # ★4. AI 审核字段创建（降级策略：失败→纯文本字段，不中断流程）
        ai_review_fields = S.get_ai_review_fields(custom_fields)
        if ai_review_fields:
            self._create_ai_review_fields(table_id, custom_fields)

        # 5. 获取表单可见字段 ID，骨架字段自动隐藏。
        # 使用 visible_custom_names（已剔除 hidden=True 字段），实现"建字段但表单不可见"。
        # 注意：AI 审核字段自动隐藏（不在 visible_custom_names 中）。
        visible_field_ids = self._get_visible_field_ids(table_id, visible_custom_names)

        # 6. 创建表单视图并获取链接（失败不阻断派发）
        form_base_link, form_view_id = self._create_form_view(
            table_id, visible_field_ids,
        )

        return table_id, form_base_link, form_view_id, visible_field_ids

    def _create_ai_review_fields(
        self,
        table_id: str,
        custom_fields: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """为任务实例表创建 AI 审核字段（降级策略：失败→纯文本字段）。

        流程：
        1. 从 custom_fields 筛选 ``ai_review=True`` 的 attachment 字段
        2. 通过 field-get 获取 attachment 字段的 fieldId 映射
        3. 使用 AiPromptBuilder 构建每个 AI 审核字段的完整配置
        4. 逐一调用 DwsClient.aitable_field_create_single 创建 AI 字段
        5. 创建失败时降级为同名纯文本字段（无 ai_config）

        Args:
            table_id: 任务实例表的 tableId。
            custom_fields: 模板的自定义字段定义列表。

        Returns:
            AI 审核字段的创建结果列表，每项含 ``field_name``、``success``、
            ``degraded``（是否降级为纯文本）信息。
        """
        results: List[Dict[str, Any]] = []

        # 1. 获取字段名→fieldId 映射
        field_id_map = self._load_field_map(table_id)
        if not field_id_map:
            logger.warning(
                "_create_ai_review_fields: 无法加载字段映射，跳过 AI 审核字段创建 "
                "table_id=%s",
                table_id,
            )
            return results

        # 2. 批量构建 AI 审核字段配置
        ai_specs = build_ai_field_specs_from_custom_fields(custom_fields, field_id_map)
        if not ai_specs:
            logger.debug(
                "_create_ai_review_fields: 无需创建 AI 审核字段 table_id=%s",
                table_id,
            )
            return results

        logger.info(
            "_create_ai_review_fields: 准备创建 %d 个 AI 审核字段 table_id=%s",
            len(ai_specs), table_id,
        )

        # 3. 逐一创建，失败则降级
        for spec in ai_specs:
            result_entry = {
                "field_name": spec.field_name,
                "target_field": spec.target_field_name,
                "success": False,
                "degraded": False,
            }

            try:
                self.client.aitable_field_create_single(
                    self.base_id,
                    table_id,
                    name=spec.field_name,
                    field_type="text",
                    ai_config=spec.ai_config,
                )
                result_entry["success"] = True
                logger.info(
                    "AI 审核字段创建成功: %s → %s (table=%s)",
                    spec.target_field_name, spec.field_name, table_id,
                )
            except (DwsError, StoreTaskDispatcherError) as exc:
                logger.warning(
                    "AI 审核字段创建失败，降级为纯文本字段: %s (table=%s): %s",
                    spec.field_name, table_id, exc,
                )
                # 降级：创建同名纯文本字段（无 ai_config）
                try:
                    self.client.aitable_field_create_single(
                        self.base_id,
                        table_id,
                        name=spec.field_name,
                        field_type="text",
                    )
                    result_entry["degraded"] = True
                    result_entry["success"] = True
                    logger.info(
                        "降级纯文本字段创建成功: %s (table=%s)",
                        spec.field_name, table_id,
                    )
                except (DwsError, StoreTaskDispatcherError) as fallback_exc:
                    logger.error(
                        "降级纯文本字段也创建失败: %s (table=%s): %s",
                        spec.field_name, table_id, fallback_exc,
                    )

            results.append(result_entry)

        # 汇总日志
        success_count = sum(1 for r in results if r["success"])
        degraded_count = sum(1 for r in results if r["degraded"])
        failed_count = len(results) - success_count
        logger.info(
            "_create_ai_review_fields 完成: total=%d success=%d degraded=%d failed=%d "
            "table_id=%s",
            len(results), success_count, degraded_count, failed_count, table_id,
        )

        return results

    def _get_visible_field_ids(
        self, table_id: str, custom_field_names: List[str]
    ) -> List[str]:
        """获取表单视图的可见字段 ID 列表。

        钉钉 AI 表格规则：
        - 骨架字段（store_id 等）不放入列表即自动隐藏
        - inspection_id（主键字段）必须出现在 visibleFieldIds 中，否则表单创建失败；
          该字段通过 prefill 自动填入，店长无感知
        - 自定义字段供店长填写

        Note:
            钉钉 AI 表格 view config API 仅支持 visibleFieldIds、filter、sort、
            group、fieldWidths，不支持 requiredFieldIds / readonlyFieldIds。
            「店长」字段的必填设置需要用户在表单视图中手动配置。

        Returns:
            表单可见字段 ID 列表，失败时返回空列表。
        """
        try:
            payload = self.client.aitable_table_get(self.base_id, table_id)
            fields = _extract_fields_from_table(payload)
            if not fields:
                return []

            # 字段名 → ID 映射
            name_to_id = {
                f.get("name") or f.get("fieldName"): f.get("fieldId") or f.get("id")
                for f in fields
                if (f.get("name") or f.get("fieldName")) and (f.get("fieldId") or f.get("id"))
            }
            custom_ids = [
                name_to_id[n] for n in custom_field_names if n in name_to_id
            ]

            # submitted_at 是 createdTime 系统字段，自动记录提交时间，需在表单中展示
            submitted_at_ids = (
                [name_to_id["submitted_at"]]
                if "submitted_at" in name_to_id
                else []
            )

            # 「派发日期」通过 prefill 带入，对店长可见
            dispatch_date_ids = (
                [name_to_id[S.FIELD_DISPLAY_DISPATCH_DATE]]
                if S.FIELD_DISPLAY_DISPATCH_DATE in name_to_id
                else []
            )

            # 「店长」（user/成员类型），表单中可见，店长提交时需选择自己
            manager_ids = (
                [name_to_id[S.FIELD_DISPLAY_MANAGER]]
                if S.FIELD_DISPLAY_MANAGER in name_to_id
                else []
            )

            # inspection_id 是首字段/主键，钉钉 AI 表格要求 primary_field
            # 必须在 visibleFieldIds 中，否则表单创建会失败。
            # 目前平台不支持表单只读字段，暂时先保留可见。
            primary_field_id = name_to_id.get(S.FIELD_DISPLAY_INSPECTION_ID)
            primary_field_ids = [primary_field_id] if primary_field_id else []

            # 「特殊情况备注」（richText 骨架字段），店长在表单中填写
            special_note_ids = (
                [name_to_id[S.FIELD_DISPLAY_SPECIAL_NOTE]]
                if S.FIELD_DISPLAY_SPECIAL_NOTE in name_to_id
                else []
            )

            visible_ids = (
                primary_field_ids
                + dispatch_date_ids
                + manager_ids
                + submitted_at_ids
                + special_note_ids
                + custom_ids
            )
            logger.debug(
                "visible field ids for table %s: count=%d",
                table_id, len(visible_ids),
            )
            return visible_ids
        except Exception as exc:
            logger.warning(
                "获取可见字段 ID 失败 table_id=%s: %s，表单将显示所有字段（含系统字段）",
                table_id, exc,
            )
            return []

    def _create_form_view(
        self,
        table_id: str,
        visible_field_ids: Optional[List[str]] = None,
    ) -> tuple:
        """为任务表创建 FormDesigner 表单视图，发布分享后返回 (form_link, view_id)。

        Args:
            table_id: 任务表 ID。
            visible_field_ids: 表单可见字段 ID 列表（派发时间 + 提交时间 + 自定义字段）。
                为空时不传 visibleFieldIds，表单显示所有字段。

        Returns:
            (form_link, view_id) 元组：
            - form_link: 分享链接（无法获取时为空字符串）
            - view_id: 表单视图 ID（创建失败时为空字符串）

        流程：
        1. 创建 FormDesigner 表单视图
        2. 调用「发布并分享」（view update）获取分享链接
        3. 若仍无链接，从 view get 详情中提取
        4. 若所有方式均失败，返回空链接（由调用方决定 fallback）

        Note:
            钉钉 AI 表格 view config API 不支持 requiredFieldIds / readonlyFieldIds。
            「店长」字段的必填设置需要用户在发布表单时手动配置。

        失败时记录警告日志，不阻断派发主流程。
        """
        try:
            config: Optional[Dict[str, Any]] = None
            if visible_field_ids:
                config = {"visibleFieldIds": visible_field_ids}

            payload = self.client.aitable_view_create_form(
                self.base_id,
                table_id,
                S.DEFAULT_FORM_VIEW_NAME,
                config=config,
            )
            form_link = _extract_form_link(payload)
            view_id = _extract_view_id(payload)

            if form_link:
                logger.debug("form view created for table %s: %s", table_id, form_link)
                return form_link, view_id or ""

            # 调用「发布并分享」接口，获取分享链接
            if view_id:
                try:
                    share_payload = self.client.aitable_view_publish_share(
                        self.base_id, table_id, view_id
                    )
                    form_link = _extract_form_link(share_payload)
                    if form_link:
                        logger.debug(
                            "form share link obtained for table %s: %s",
                            table_id,
                            form_link,
                        )
                        return form_link, view_id
                except Exception as share_exc:
                    logger.warning(
                        "发布分享表单视图失败 table_id=%s view_id=%s: %s",
                        table_id, view_id, share_exc,
                    )

                # 若发布分享未返回链接，尝试从 view get 详情中提取（含重试机制）
                # AI 表格服务在发布表单后可能存在同步延迟，shareUuid 不会立即可用，
                # 因此重试最多 3 次，每次间隔 2 秒，以等待服务端数据同步完成。
                max_retries = 3
                retry_interval = 2  # 秒
                detail: dict | None = None
                for attempt in range(1, max_retries + 1):
                    try:
                        detail = self.client.aitable_view_get_detail(
                            self.base_id, table_id, view_id
                        )
                        form_link = _extract_form_link(detail)
                        if form_link:
                            logger.debug(
                                "form link extracted from view detail for table %s "
                                "(attempt %d): %s",
                                table_id, attempt, form_link,
                            )
                            return form_link, view_id
                    except Exception as detail_exc:
                        logger.warning(
                            "获取表单视图详情失败 table_id=%s view_id=%s "
                            "(attempt %d/%d): %s",
                            table_id, view_id, attempt, max_retries, detail_exc,
                        )

                    # 第 4 级 fallback：从 view 详情的 formInfo.shareUuid 拼接分享链接
                    if detail:
                        form_link = extract_form_share_url(detail)
                        if form_link:
                            logger.debug(
                                "form link built from shareUuid for table %s "
                                "(attempt %d): %s",
                                table_id, attempt, form_link,
                            )
                            return form_link, view_id

                    # 未获取到链接且还有重试机会，等待后重试
                    if attempt < max_retries:
                        logger.info(
                            "表单链接尚未就绪，等待 %d 秒后重试 (%d/%d)...",
                            retry_interval, attempt, max_retries,
                        )
                        time.sleep(retry_interval)

            logger.warning(
                "无法获取表单分享链接，table_id=%s，"
                "可能是 AI 表格服务同步延迟，将引导用户手动处理",
                table_id,
            )
            return "", view_id or ""
        except Exception as exc:
            logger.error(
                "创建表单视图失败 table_id=%s: %s，派发时将使用空链接",
                table_id, exc,
            )

        return "", ""

    def _reuse_or_create_form_view(
        self,
        table_id: str,
        visible_field_ids: Optional[List[str]] = None,
    ) -> tuple:
        """复用已有的 FormDesigner 表单视图；找不到再调用 ``_create_form_view`` 新建。

        在"同名任务表已存在则直接复用"的兜底分支中使用：避免对已有表重复
        创建表单视图，引发"同一个表挂多个表单视图"的脏数据。

        Returns:
            (form_link, view_id) 元组。任何步骤失败都返回 (\"\", \"\")，由调用
            方决定 fallback 行为（一般是引导用户重新分享）。
        """
        # 1. 先尝试列出已有视图，找一个 FormDesigner 类型的复用
        try:
            payload = self.client.aitable_view_get(self.base_id, table_id)
            views = []
            if isinstance(payload, dict):
                if isinstance(payload.get("views"), list):
                    views = payload["views"]
                else:
                    data = payload.get("data")
                    if isinstance(data, dict) and isinstance(data.get("views"), list):
                        views = data["views"]
            for v in views:
                if not isinstance(v, dict):
                    continue
                if (v.get("viewType") or v.get("type")) != S.FORM_VIEW_TYPE:
                    continue
                view_id = v.get("viewId") or v.get("id") or ""
                if not view_id:
                    continue
                # 拿到表单视图后，尝试取分享链接（含重试机制）
                form_link = ""
                detail = None
                max_retries = 3
                retry_interval = 2  # 秒
                for attempt in range(1, max_retries + 1):
                    try:
                        detail = self.client.aitable_view_get_detail(
                            self.base_id, table_id, view_id,
                        )
                        form_link = _extract_form_link(detail)
                        if form_link:
                            break
                    except Exception as exc:
                        logger.warning(
                            "_reuse_or_create_form_view: 获取已有表单视图详情失败 "
                            "table_id=%s view_id=%s (attempt %d/%d): %s",
                            table_id, view_id, attempt, max_retries, exc,
                        )
                    # 显式 fallback：从 formInfo.shareUuid 提取（兼容新版 API）
                    if not form_link and detail:
                        from scripts.domain.form_link_builder import extract_form_share_url
                        form_link = extract_form_share_url(detail)
                        if form_link:
                            break
                    if attempt < max_retries:
                        logger.info(
                            "_reuse_or_create_form_view: 表单链接尚未就绪，"
                            "等待 %d 秒后重试 (%d/%d)...",
                            retry_interval, attempt, max_retries,
                        )
                        time.sleep(retry_interval)
                logger.debug(
                    "_reuse_or_create_form_view: 复用已有表单视图 "
                    "table_id=%s view_id=%s form_link=%s",
                    table_id, view_id, form_link or "(空)",
                )
                return form_link, view_id
        except Exception as exc:
            logger.warning(
                "_reuse_or_create_form_view: 列出已有视图失败 table_id=%s: %s",
                table_id, exc,
            )

        # 2. 没有已有的 FormDesigner 视图，回退到创建新视图
        return self._create_form_view(table_id, visible_field_ids)

    # ------------------------------------------------------------------
    # 表单视图可见字段更新
    # ------------------------------------------------------------------

    def update_form_view_visible_fields(
        self,
        table_id: str,
        view_id: str,
        custom_fields: List[Dict[str, Any]],
    ) -> bool:
        """根据最新的 custom_fields 重新计算并更新表单视图的 visibleFieldIds。

        典型场景：用户通过 ``template update --custom-fields`` 修改了字段的
        ``hidden`` 属性后，需要同步更新已有表单视图的可见字段配置。

        流程：
        1. 从 custom_fields 中剔除 hidden=True 的字段名
        2. 调用 _get_visible_field_ids 获取新的 visibleFieldIds
        3. 调用 client.aitable_view_update 更新视图配置

        Note:
            钉钉 AI 表格 view config API 不支持 requiredFieldIds / readonlyFieldIds。
            「店长」字段的必填设置需要用户在表单视图中手动配置。

        Args:
            table_id: 任务实例表 ID。
            view_id: 表单视图 ID。
            custom_fields: 最新的自定义字段定义列表。

        Returns:
            True 表示更新成功，False 表示更新失败（已记录日志）。
        """
        try:
            # 1. 计算可见的自定义字段名（剔除 hidden=True）
            hidden_names = set(S.get_hidden_custom_field_names(custom_fields))
            visible_custom_names = [
                f["name"] for f in custom_fields
                if f.get("name") and f["name"] not in hidden_names
            ]

            # 2. 获取新的 visibleFieldIds
            visible_field_ids = self._get_visible_field_ids(table_id, visible_custom_names)
            if not visible_field_ids:
                logger.warning(
                    "update_form_view_visible_fields: 无法计算 visibleFieldIds，"
                    "跳过更新 table_id=%s view_id=%s",
                    table_id, view_id,
                )
                return False

            # 3. 仅更新 visibleFieldIds（API 不支持 requiredFieldIds / readonlyFieldIds）
            view_config: Dict[str, Any] = {"visibleFieldIds": visible_field_ids}

            self.client.aitable_view_update(
                self.base_id,
                table_id,
                view_id,
                config=view_config,
            )
            logger.info(
                "update_form_view_visible_fields: 已更新表单视图配置 "
                "table_id=%s view_id=%s visible=%d",
                table_id, view_id, len(visible_field_ids),
            )
            return True
        except Exception as exc:
            logger.warning(
                "update_form_view_visible_fields: 更新表单视图失败 "
                "table_id=%s view_id=%s: %s",
                table_id, view_id, exc,
            )
            return False

    # ------------------------------------------------------------------
    # 通用辅助：表是否存在 / 字段映射加载 / 任务记录表 ID 解析
    # ------------------------------------------------------------------

    def _table_exists(self, table_id: str) -> bool:
        """判断 tableId 对应的表是否仍存在（防止用户在 AI 表格里手动删了表）。

        通过 ``aitable_table_get`` 探活，DwsError 视为不存在。
        空 table_id 直接视为不存在。
        """
        if not table_id:
            return False
        try:
            self.client.aitable_table_get(self.base_id, table_id)
            return True
        except DwsError:
            return False
        except Exception as exc:  # pragma: no cover - 网络异常等
            logger.warning("_table_exists 探活异常 table_id=%s: %s", table_id, exc)
            return False

    def _load_field_map(self, table_id: str) -> Dict[str, str]:
        """加载某张表的 fieldName -> fieldId 映射（不依赖 cache，直接查询表定义）。

        失败时返回空 dict，调用方降级用 fieldName 写入。
        """
        field_name_to_id: Dict[str, str] = {}
        try:
            tbl_payload = self.client.aitable_table_get(self.base_id, table_id)
            tbl_fields = _extract_fields_from_table(tbl_payload)
            for f in tbl_fields:
                name = f.get("fieldName") or f.get("name")
                fid = f.get("fieldId") or f.get("id")
                if name and fid:
                    field_name_to_id[name] = fid
        except Exception as exc:
            logger.warning("加载字段映射失败 table_id=%s: %s", table_id, exc)
        return field_name_to_id

    def _find_table_id_by_table_name(self, table_name: str) -> Optional[str]:
        """根据表名在 Base 中查找对应的 tableId（实例方法，调用 client.aitable_base_get）。

        Args:
            table_name: 要查找的表名。

        Returns:
            tableId，找不到时返回 None。
        """
        try:
            base_payload = self.client.aitable_base_get(self.base_id)
            return _find_table_id_by_name(base_payload, table_name)
        except Exception as exc:
            logger.warning(
                "_find_table_id_by_table_name 查询失败 table_name=%s: %s",
                table_name, exc,
            )
            return None

    def _get_task_record_table_id(self) -> Optional[str]:
        """解析「任务记录」固定表的 tableId（优先走 cache，失败回退到 base get）。"""
        try:
            return self.cache.get_table_id(self.base_id, S.TASK_RECORD_TABLE)
        except Exception as cache_exc:
            logger.debug("从 cache 获取任务记录表 ID 失败，回退到 base get: %s", cache_exc)
        try:
            base_payload = self.client.aitable_base_get(self.base_id)
            return _find_table_id_by_name(base_payload, S.TASK_RECORD_TABLE)
        except Exception as exc:
            logger.error(
                "解析任务记录表 ID 失败，AI表格=%s 表=%r: %s",
                self.base_id, S.TASK_RECORD_TABLE, exc,
            )
            return None

    # ------------------------------------------------------------------
    # 动态建表：通知明细表
    # ------------------------------------------------------------------

    def _create_task_notification(self, table_name: str) -> tuple:
        """动态创建通知明细表，返回 (tableId, field_name_to_id) 元组。

        命名规则：「{任务表名}-通知」，如「每日巡检-20260424-通知」。
        字段与原通知明细固定表一致。
        建表逻辑统一由 _create_ai_table 处理（字段拆分 → 首次创建 → 补齐字段 → 补齐失败中止）。
        失败时抛出 DispatchError。
        """
        # ── 兜底：同名表已存在则直接复用，禁止重复创建 ─────────────
        # 通知表名形如「巡检-20260426-通知」，当天该任务已经存在通知表时直接复用，
        # 避免出现两张同名通知表。
        existing_table_id = self._find_table_id_by_table_name(table_name)
        if existing_table_id:
            logger.warning(
                "_create_task_notification: AI表格 中已存在同名通知表，直接复用以避免重复创建 "
                "table_name=%s table_id=%s",
                table_name, existing_table_id,
            )
            return existing_table_id, self._load_field_map(existing_table_id)

        # 统一建表接口：字段拆分 → 首次创建 → 补齐字段 → 补齐失败中止
        table_id = self._create_ai_table(table_name, S.NOTIFICATION_TABLE_FIELDS)

        # 查出新建表的 fieldName -> fieldId 映射，供写入时直接使用
        field_name_to_id = self._load_field_map(table_id)
        logger.debug("notification table field map: %s", field_name_to_id)

        return table_id, field_name_to_id
