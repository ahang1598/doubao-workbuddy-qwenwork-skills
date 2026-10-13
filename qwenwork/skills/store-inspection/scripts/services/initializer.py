"""系统初始化模块。

提供 3 种初始化模式：
- :meth:`Initializer.init_create`  - 新建 AI表格 + 3 张固定表（模式 A）
- :meth:`Initializer.init_query`   - 列出/搜索已有 AI表格，由调用方挑选（模式 B）
- :meth:`Initializer.init_url`     - 通过 URL 或 BASE_ID 绑定已有 AI表格（模式 C）

并提供：
- :meth:`Initializer.validate`     - 校验 AI表格 是否包含 3 张固定表及其骨架字段
- :meth:`Initializer.auto_repair`  - 根据校验报告自动补齐缺失表/字段
- :meth:`Initializer.reset`        - 清空本地配置（不删除 AI表格）

固定表（3 张）：门店清单、巡店模版、任务记录
  - 「通知明细」已废弃为固定表，改为与任务表一对一的动态表（由 dispatcher 创建）
动态任务表：由 dispatcher 在创建任务时按模版定义动态创建，命名如「每日巡检-20260424」
动态通知明细表：每次任务创建时同步创建，命名如「每日巡检-20260424-通知」
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from scripts.domain import schema as S
from scripts.domain.exceptions import (
    DwsError,
    DuplicateBaseError,
    InitializationError,
    SchemaValidationError,
)
from scripts.infrastructure import config as cfg
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import (
    MappingCache,
    _extract_fields,
    _extract_tables,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_NAME = "门店巡检任务中心"

# ---------------------------------------------------------------------------
# 校验报告数据结构
# ---------------------------------------------------------------------------

@dataclass
class TableValidationItem:
    """单张表的校验结果。"""

    table_name: str
    exists: bool = False
    table_id: Optional[str] = None
    missing_fields: List[Dict[str, Any]] = field(default_factory=list)
    type_mismatched: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationReport:
    """整体校验报告。"""

    base_id: str
    base_accessible: bool = False
    tables: Dict[str, TableValidationItem] = field(default_factory=dict)
    error_message: Optional[str] = None

    @property
    def is_passed(self) -> bool:
        if not self.base_accessible or self.error_message:
            return False
        for item in self.tables.values():
            if not item.exists:
                return False
            if item.missing_fields or item.type_mismatched:
                return False
        return True

    def to_dict(self) -> dict:
        return {
            "base_id": self.base_id,
            "base_accessible": self.base_accessible,
            "is_passed": self.is_passed,
            "error_message": self.error_message,
            "tables": {
                name: {
                    "exists": item.exists,
                    "table_id": item.table_id,
                    "missing_fields": item.missing_fields,
                    "type_mismatched": item.type_mismatched,
                }
                for name, item in self.tables.items()
            },
        }


# ---------------------------------------------------------------------------
# Initializer
# ---------------------------------------------------------------------------

class Initializer:
    """系统初始化执行器。"""

    def __init__(
        self,
        client: Optional[DwsClient] = None,
        cache: Optional[MappingCache] = None,
    ) -> None:
        self.client = client or DwsClient()
        self.cache = cache or MappingCache(client=self.client)

    # ------------------------------------------------------------------
    # 模式 A：新建
    # ------------------------------------------------------------------

    def init_create(self, base_name: str = DEFAULT_BASE_NAME) -> str:
        """新建 AI表格 并创建 3 张固定表（门店清单、巡店模版、任务记录）。

        注意：「通知明细」已废弃为固定表，改为与任务表一对一的动态表，
        由 dispatcher 在每次派发时自动创建，无需在此处初始化。

        Args:
            base_name: AI表格 名称，默认为 ``DEFAULT_BASE_NAME``（门店巡检任务中心）。

        Returns:
            新建的 ``base_id``。

        Raises:
            DuplicateBaseError: 检测到同名 AI表格 已存在时抛出，携带已有 AI表格 的 ID 和链接。
            InitializationError: 任一步骤失败时抛出，并尽量保留已创建的资源
                让用户决定是否清理。
        """
        if not base_name or not (1 <= len(base_name) <= 50):
            raise InitializationError("表格名称长度必须在 1~50 字符之间")

        # 0a. 本地绑定检测：config 已有 base_id 时直接复用，跳过创建 Base，
        #     通过 validate + auto_repair 补齐缺失表/字段后返回。
        existing_base_id = cfg.get_base_id()
        if existing_base_id:
            logger.debug(
                "config 已绑定 base_id=%s，跳过创建，直接校验并补齐",
                existing_base_id,
            )
            report = self.validate(existing_base_id)
            if not report.is_passed:
                self.auto_repair(existing_base_id, report)
                report = self.validate(existing_base_id)
            if not report.is_passed:
                raise SchemaValidationError(
                    f"AI表格 {existing_base_id!r} 校验未通过，请手工修复后重试",
                    report=report.to_dict(),
                )
            return existing_base_id

        # 0b. 同名检测：创建前搜索是否已存在同名 AI表格
        try:
            search_payload = self.client.aitable_base_search(base_name)
            existing_bases = _extract_base_summaries(search_payload)
            for b in existing_bases:
                if b.get("baseName") == base_name:
                    dup_id = b.get("baseId", "")
                    dup_link = f"https://docs.dingtalk.com/i/nodes/{dup_id}"
                    raise DuplicateBaseError(
                        f"已存在同名 AI表格「{base_name}」，请使用 `init url {dup_id}` 复用",
                        base_id=dup_id,
                        base_link=dup_link,
                    )
        except DuplicateBaseError:
            raise
        except DwsError as exc:
            logger.warning(
                "同名检测搜索失败，跳过检测继续创建（存在重复创建同名 AI表格 的风险）: %s",
                exc,
            )

        # 1. 创建 AI表格
        try:
            payload = self.client.aitable_base_create(base_name)
        except DwsError as exc:
            raise InitializationError(f"创建 AI表格 失败: {exc}") from exc

        base_id = _extract_base_id(payload)
        if not base_id:
            raise InitializationError(
                f"dws aitable base create 未返回 baseId，原始响应: {payload!r}"
            )
        logger.debug("base created: %s", base_id)

        # 1b. 立即持久化 base_id（含 corp_id），确保后续建表失败时不会丢失绑定关系，
        #     用户可通过 init validate --auto-repair 补齐缺失表。
        corp_id = self._fetch_corp_id()
        cfg.save(base_id, corp_id=corp_id)
        self.cache.invalidate(base_id)

        # 2. 创建 3 张固定表
        for table_name in S.ALL_TABLE_NAMES:
            try:
                self._create_table_with_phases(base_id, table_name)
            except DwsError as exc:
                raise InitializationError(
                    f"创建表 {table_name!r} 失败（AI表格 已创建: {base_id}，"
                    f"可调用 init validate --auto-repair 补齐，"
                    f"或调用 dws aitable base delete 删除后重试）: {exc}"
                ) from exc

        # 3. 清理 AI表格 自带的默认数据表和仪表盘
        self._cleanup_default_resources(base_id)

        return base_id

    # ------------------------------------------------------------------
    # 模式 B：查询
    # ------------------------------------------------------------------

    def init_query(self, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出候选 AI表格 供 CLI/Skill 层展示给用户挑选。

        Returns:
            形如 ``[{"baseId": "xxx", "baseName": "..."}, ...]`` 的候选列表。
        """
        try:
            if keyword:
                payload = self.client.aitable_base_search(keyword)
            else:
                payload = self.client.aitable_base_list(limit=10)
        except DwsError as exc:
            raise InitializationError(f"查询 AI表格 列表失败: {exc}") from exc
        return _extract_base_summaries(payload)

    # ------------------------------------------------------------------
    # 模式 C：URL / BASE_ID
    # ------------------------------------------------------------------

    def init_url(
        self, url_or_id: str, *, auto_repair: bool = False
    ) -> str:
        """通过 URL 或 BASE_ID 绑定已有 AI表格。

        Args:
            url_or_id: AI 表格分享链接或裸 BASE_ID。
            auto_repair: 校验失败时是否自动补齐（不能修复字段类型不匹配）。

        Returns:
            校验通过后持久化的 ``base_id``。
        """
        base_id = parse_base_id(url_or_id)
        if not base_id:
            raise InitializationError(
                f"无法从 {url_or_id!r} 解析出 BASE_ID，"
                f"请检查链接格式或直接传 BAS_ 开头的 ID"
            )
        # 先持久化 base_id（含 corp_id），确保后续 auto_repair / validate 中途失败时
        # 用户仍可通过 init validate / init url --auto-repair 重试，而不会丢失绑定。
        corp_id = self._fetch_corp_id()
        cfg.save(base_id, corp_id=corp_id)
        self.cache.invalidate(base_id)
        report = self.validate(base_id)
        if not report.is_passed:
            if auto_repair:
                self.auto_repair(base_id, report)
                report = self.validate(base_id)
        if not report.is_passed:
            raise SchemaValidationError(
                f"AI表格 {base_id!r} 校验未通过，请修复后重试", report=report.to_dict()
            )
        return base_id

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------

    def validate(self, base_id: str) -> ValidationReport:
        """校验 AI表格 是否包含 3 张固定表（门店清单、巡店模版、任务记录）及其骨架字段。

        注意：「通知明细」已废弃为固定表，不再校验。
        动态通知明细表由 dispatcher 在每次派发时自动创建，命名如「每日巡检-20260424-通知」。
        """
        report = ValidationReport(base_id=base_id)

        # 1. AI表格 可访问 + 取 tables
        try:
            base_payload = self.client.aitable_base_get(base_id)
        except DwsError as exc:
            report.error_message = f"AI表格 不可访问: {exc}"
            return report
        report.base_accessible = True

        existing_tables = {
            (t.get("tableName") or t.get("name")): (t.get("tableId") or t.get("id"))
            for t in _extract_tables(base_payload)
            if t.get("tableName") or t.get("name")
        }

        # 2. 校验 3 张固定表的存在性和骨架字段
        for table_name in S.ALL_TABLE_NAMES:
            item = TableValidationItem(table_name=table_name)
            tid = existing_tables.get(table_name)
            if not tid:
                report.tables[table_name] = item
                continue
            item.exists = True
            item.table_id = tid

            try:
                table_payload = self.client.aitable_table_get(base_id, tid)
            except DwsError as exc:
                item.missing_fields = [
                    {"name": "<unknown>", "reason": f"无法读取表字段: {exc}"}
                ]
                report.tables[table_name] = item
                continue

            existing_fields = {
                (f.get("name") or f.get("fieldName")): f.get("type")
                for f in _extract_fields(table_payload)
                if f.get("name") or f.get("fieldName")
            }

            schema = S.get_table_schema(table_name)
            for spec in schema["fields"]:
                fname = spec["name"]
                expected_type = spec["type"]
                if fname not in existing_fields:
                    item.missing_fields.append({"name": fname, "type": expected_type})
                    continue
                actual_type = existing_fields[fname]
                if actual_type and actual_type != expected_type:
                    item.type_mismatched.append(
                        {
                            "name": fname,
                            "expected": expected_type,
                            "actual": actual_type,
                        }
                    )

            report.tables[table_name] = item

        return report

    # ------------------------------------------------------------------
    # 自动修复
    # ------------------------------------------------------------------

    def auto_repair(self, base_id: str, report: ValidationReport) -> None:
        """根据校验报告自动补齐缺失的表/字段。

        不会修复字段类型不匹配（避免数据丢失），由用户手工处理。
        修复过程中的每一步都会通过 logger 记录，调用方可通过日志观察进度。
        """
        if not report.base_accessible:
            raise InitializationError("AI表格 不可访问，无法自动修复")
        for table_name, item in report.tables.items():
            if not item.exists:
                logger.debug("[auto-repair] 创建缺失表: %s", table_name)
                try:
                    self._create_table_with_phases(base_id, table_name)
                    logger.debug("[auto-repair] 表创建成功: %s", table_name)
                except Exception as exc:
                    logger.error("[auto-repair] 创建表 %r 失败: %s", table_name, exc)
                    raise
                continue
            if item.missing_fields:
                schema = S.get_table_schema(table_name)
                spec_by_name = {f["name"]: f for f in schema["fields"]}
                fields_to_create = [
                    spec_by_name[m["name"]]
                    for m in item.missing_fields
                    if m["name"] in spec_by_name
                ]
                if fields_to_create:
                    field_names = ", ".join(f["name"] for f in fields_to_create)
                    logger.debug(
                        "[auto-repair] 补充字段 [%s] 到表 %s", field_names, table_name
                    )
                    try:
                        self._create_fields_in_chunks(
                            base_id, item.table_id, fields_to_create
                        )
                        logger.debug(
                            "[auto-repair] 字段补充成功 [%s] (%s)", field_names, table_name
                        )
                    except Exception as exc:
                        logger.error(
                            "[auto-repair] 补充字段失败 [%s] (%s): %s",
                            field_names, table_name, exc,
                        )
                        raise
            if item.type_mismatched:
                for mismatch in item.type_mismatched:
                    logger.warning(
                        "[auto-repair] 跳过字段 %r (%s)：类型不匹配（期望 %s，实际 %s），需手工修复",
                        mismatch["name"], table_name, mismatch["expected"], mismatch["actual"],
                    )

    # ------------------------------------------------------------------
    # 重置
    # ------------------------------------------------------------------

    def _fetch_corp_id(self) -> Optional[str]:
        """通过 ``dws contact user get-self`` 获取当前用户的 corpId。

        corpId 对同一组织是固定的，获取后持久化到 config.json，
        后续写入 user 类型字段时自动使用。获取失败仅记 warning 日志，
        不阻塞初始化流程。
        """
        existing = cfg.get_corp_id()
        if existing:
            return existing
        try:
            result = self.client.contact_user_get_self()
            if not isinstance(result, dict):
                logger.warning("dws contact user get-self 返回非 dict: %s", type(result))
                return None
            corp_id = result.get("corpId")
            if not corp_id or not isinstance(corp_id, str):
                # 兼容嵌套结构：result[0].orgEmployeeModel.corpId
                items = result.get("result")
                if isinstance(items, list) and items and isinstance(items[0], dict):
                    emp = items[0].get("orgEmployeeModel") or {}
                    corp_id = emp.get("corpId") if isinstance(emp, dict) else None
            if isinstance(corp_id, str) and corp_id:
                logger.debug("获取 corpId 成功: %s", corp_id)
                return corp_id
            logger.warning("dws contact user get-self 未返回有效 corpId: %s", result)
        except Exception as exc:
            logger.warning("获取 corpId 失败（不影响初始化）: %s", exc)
        return None

    def reset(self) -> None:
        """删除本地 config.json + 清空缓存。不会删除 AI表格。"""
        cfg.reset()
        self.cache.invalidate()

    # ------------------------------------------------------------------
    # 内部：清理 AI表格 默认资源
    # ------------------------------------------------------------------

    # 新建 AI表格 时服务端自动附带的默认资源名称
    _DEFAULT_TABLE_NAME = "数据表"
    _DEFAULT_DASHBOARD_NAME = "仪表盘"

    def _cleanup_default_resources(self, base_id: str) -> None:
        """清理新建 AI表格 时服务端自动附带的默认「数据表」和「仪表盘」。

        在 3 张固定表创建完成后调用。精确匹配名为「数据表」的数据表和
        名为「仪表盘」的仪表盘并删除。清理失败仅记 warning 日志，
        不影响 init_create 整体成功。
        """
        try:
            base_payload = self.client.aitable_base_get(base_id)
        except Exception as exc:
            logger.warning("清理默认资源：获取 AI表格 详情失败，跳过清理: %s", exc)
            return

        # --- 删除名为「数据表」的默认表 ---
        existing_tables = _extract_tables(base_payload)
        for table in existing_tables:
            table_name = table.get("tableName") or table.get("name")
            table_id = table.get("tableId") or table.get("id")
            if table_name == self._DEFAULT_TABLE_NAME and table_id:
                try:
                    self.client.aitable_table_delete(base_id, table_id)
                    logger.debug("已删除默认数据表: %s (%s)", table_name, table_id)
                except Exception as exc:
                    logger.warning(
                        "删除默认数据表 %r (%s) 失败，跳过: %s",
                        table_name, table_id, exc,
                    )

        # --- 删除名为「仪表盘」的默认仪表盘 ---
        dashboards = _extract_dashboards(base_payload)
        for dashboard in dashboards:
            dashboard_id = dashboard.get("dashboardId") or dashboard.get("id")
            dashboard_name = dashboard.get("dashboardName") or dashboard.get("name")
            if dashboard_name == self._DEFAULT_DASHBOARD_NAME and dashboard_id:
                try:
                    self.client.aitable_dashboard_delete(base_id, dashboard_id)
                    logger.debug("已删除默认仪表盘: %s (%s)", dashboard_name, dashboard_id)
                except Exception as exc:
                    logger.warning(
                        "删除默认仪表盘 %r (%s) 失败，跳过: %s",
                        dashboard_name, dashboard_id, exc,
                    )

    # ------------------------------------------------------------------
    # 内部：分阶段建表 / 分块建字段
    # ------------------------------------------------------------------

    def _create_ai_table(self, base_id: str, table_name: str, all_fields: List[dict]) -> str:
        """统一的 AI 表格创建接口，所有建表逻辑共用此方法。

        流程：
        1. 字段拆分：按 TABLE_CREATE_FIELD_LIMIT（15）拆分为 phase1 / phase2
        2. 首次创建：调用 aitable_table_create 携带 phase1 字段建表
        3. 补齐字段：若有 phase2，分批调用 aitable_field_create 追加；
           建表后回查实际字段，对静默丢失的字段再次补齐
        4. 补齐失败则中止：二次回查仍有缺失字段时抛 InitializationError，
           避免静默吞掉字段导致后续写入/校验异常

        Args:
            base_id: Base ID。
            table_name: 要创建的表名。
            all_fields: 完整字段列表（按期望顺序）。

        Returns:
            新建表的 tableId。

        Raises:
            InitializationError: 建表失败、未返回 tableId、或字段补齐后仍有缺失时抛出。
        """
        # 步骤 1：字段拆分
        phase1 = all_fields[: S.TABLE_CREATE_FIELD_LIMIT]
        phase2 = all_fields[S.TABLE_CREATE_FIELD_LIMIT :]

        # 步骤 2：首次创建（携带 phase1 字段）
        payload = self.client.aitable_table_create(base_id, table_name, phase1)
        table_id = _extract_table_id(payload)
        if not table_id:
            raise InitializationError(
                f"创建表 {table_name!r} 后未返回 tableId，原始响应: {payload!r}"
            )
        logger.debug("table created: %s -> %s", table_name, table_id)

        # 步骤 3：补齐 phase2 字段（分批追加）
        if phase2:
            for i in range(0, len(phase2), S.FIELD_CREATE_LIMIT):
                chunk = phase2[i : i + S.FIELD_CREATE_LIMIT]
                self.client.aitable_field_create(base_id, table_id, chunk)

        # 步骤 3b：回查实际字段，补齐 dws 静默丢失的字段
        # dws 对带 config.options 的字段类型有时会静默丢字段，必须回查并补齐
        try:
            table_payload = self.client.aitable_table_get(base_id, table_id)
            from scripts.infrastructure.mapping_cache import _extract_fields
            actual_fields = _extract_fields(table_payload)
            actual_field_names = {
                f.get("name") or f.get("fieldName")
                for f in actual_fields
                if f.get("name") or f.get("fieldName")
            }
        except DwsError as exc:
            logger.warning(
                "回查表 %r 字段失败，跳过补齐检查（表结构可能不完整，"
                "可运行 init validate --auto-repair 修复）: %s",
                table_name, exc,
            )
            return table_id

        expected_names = [f["name"] for f in all_fields]
        missing_names = [name for name in expected_names if name not in actual_field_names]
        if missing_names:
            logger.warning(
                "表 %s 建表后字段缺失，尝试补齐: missing=%s expected=%d actual=%d",
                table_name, missing_names, len(expected_names), len(actual_field_names),
            )
            missing_field_defs = [f for f in all_fields if f["name"] in set(missing_names)]
            for i in range(0, len(missing_field_defs), S.FIELD_CREATE_LIMIT):
                chunk = missing_field_defs[i : i + S.FIELD_CREATE_LIMIT]
                self.client.aitable_field_create(base_id, table_id, chunk)

            # 步骤 4：二次回查，补齐失败则中止
            try:
                table_payload = self.client.aitable_table_get(base_id, table_id)
                actual_fields = _extract_fields(table_payload)
                actual_field_names = {
                    f.get("name") or f.get("fieldName")
                    for f in actual_fields
                    if f.get("name") or f.get("fieldName")
                }
            except DwsError as exc:
                raise InitializationError(
                    f"表 {table_name!r} 字段补齐后二次回查失败: {exc}"
                ) from exc

            still_missing = [name for name in expected_names if name not in actual_field_names]
            if still_missing:
                raise InitializationError(
                    f"表 {table_name!r} 字段创建不完整，补齐后仍缺失 {still_missing}。"
                    f"这是严重问题，已中止执行。"
                    f"请检查 schema.py 中的字段定义（特别是 singleSelect/multipleSelect "
                    f"的 options、type 拼写等）后重试。"
                )

        return table_id

    def _create_table_with_phases(self, base_id: str, table_name: str) -> str:
        """按 schema 的完整字段列表建表，返回 ``tableId``。

        委托给 :meth:`_create_ai_table` 统一处理字段拆分、首次创建、补齐字段及
        补齐失败中止的完整流程。
        """
        schema = S.get_table_schema(table_name)
        all_fields = schema["fields"]
        return self._create_ai_table(base_id, table_name, all_fields)

    def _create_fields_in_chunks(
        self, base_id: str, table_id: str, fields: List[dict]
    ) -> None:
        """按 :data:`schema.FIELD_CREATE_LIMIT` 分批 ``field create``。

        用于 :meth:`auto_repair` 中对已有表补齐缺失字段的场景。
        """
        for i in range(0, len(fields), S.FIELD_CREATE_LIMIT):
            chunk = fields[i : i + S.FIELD_CREATE_LIMIT]
            self.client.aitable_field_create(base_id, table_id, chunk)


# ---------------------------------------------------------------------------
# 解析助手
# ---------------------------------------------------------------------------

_BASE_ID_PATTERN = re.compile(r"BAS_[A-Za-z0-9_-]+")
# 钉钉 AI 表格 baseId 可能是 BAS_ 前缀或纯字母数字形式（如 7NkDwLng8Z9XERpDIxdrwl4MJKMEvZBY）
_BARE_BASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,}$")


def parse_base_id(url_or_id: str) -> Optional[str]:
    """从 URL 或裸 ID 解析 BASE_ID。

    支持：
    - ``BAS_xxxxxx``（传统 BAS_ 前缀格式）
    - ``7NkDwLng8Z9XERpDIxdrwl4MJKMEvZBY``（纯字母数字格式，≥16 字符）
    - ``https://docs.dingtalk.com/i/nodes/BAS_xxxxxx?...``
    - ``https://docs.dingtalk.com/i/nodes/7NkDwLng8Z9XERpDIxdrwl4MJKMEvZBY``
    """
    if not url_or_id:
        return None
    text = url_or_id.strip()
    # 裸 ID 形式（无斜杠、无问号）：BAS_ 前缀或纯字母数字（≥16 字符）
    if "/" not in text and "?" not in text:
        if text.startswith("BAS_") or _BARE_BASE_ID_PATTERN.match(text):
            return text
    # URL 形式：取 /nodes/ 后到 ? 前
    parsed = urlparse(text)
    if parsed.scheme:
        path = parsed.path
        m = re.search(r"/nodes/([^/?#]+)", path)
        if m:
            return m.group(1)
    # 兜底：全文正则匹配 BAS_*
    m = _BASE_ID_PATTERN.search(text)
    if m:
        return m.group(0)
    return None


def _extract_base_id(payload: dict) -> Optional[str]:
    """兼容多种 ``base create`` 返回结构提取 baseId。"""
    if not isinstance(payload, dict):
        return None
    for key in ("baseId", "base_id", "id"):
        val = payload.get(key)
        if val:
            return val
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_base_id(data)
    return None


def _extract_table_id(payload: dict) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in ("tableId", "table_id", "id"):
        val = payload.get(key)
        if val:
            return val
    if isinstance(payload.get("tables"), list) and payload["tables"]:
        first = payload["tables"][0]
        if isinstance(first, dict):
            for key in ("tableId", "id"):
                if first.get(key):
                    return first[key]
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_table_id(data)
    return None


def _extract_base_summaries(payload: dict) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in ("bases", "items", "list"):
        items = payload.get(key)
        if isinstance(items, list):
            return [
                {
                    "baseId": b.get("baseId") or b.get("id"),
                    "baseName": b.get("baseName") or b.get("name"),
                }
                for b in items
                if isinstance(b, dict)
            ]
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_base_summaries(data)
    return []


def _extract_views(payload: dict) -> List[dict]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("views")
    if isinstance(items, list):
        return items
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_views(data)
    return []


def _extract_dashboards(payload: dict) -> List[dict]:
    """从 ``aitable base get`` 返回中提取 dashboards 列表。

    兼容两种风格：
    - ``{"dashboards": [...]}``
    - ``{"data": {"dashboards": [...]}}``
    """
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("dashboards"), list):
        return payload["dashboards"]
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("dashboards"), list):
        return data["dashboards"]
    return []


__all__ = [
    "Initializer",
    "ValidationReport",
    "TableValidationItem",
    "parse_base_id",
]
