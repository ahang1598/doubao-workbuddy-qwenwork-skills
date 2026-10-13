"""统计服务（Stats）。

基于「任务记录」表（TASK_RECORD_TABLE）与每个任务对应的「动态任务表」做多维度聚合：

- :meth:`StatsService.template_usage_ranking` ：模板使用次数排行
- :meth:`StatsService.template_active_rate`   ：模板活跃率（启用模板 / 全部模板，
  以及指定时间窗口内有派发的模板占比）
- :meth:`StatsService.task_completion_metrics` ：任务完成率与平均耗时（按模板维度）
- :meth:`StatsService.store_ranking`          ：门店表现排行
- :meth:`StatsService.trend`                  ：时间趋势（按天 / 周）

完成定义：
- 动态任务表中 **存在记录** 即视为已提交（纯 prefill 模式下，记录仅在
  店长提交表单时创建，因此记录存在 ≡ 已提交）
- 平均耗时 = ``submitted_at - task_record.initiated_at``（秒）

容错：
- 任务记录中 ``instance_table_id``（兼容旧字段名 ``task_table_id``）为空 / 动态任务实例表已被手工删除（``DwsError``）→ 跳过
  该任务，记 warning 日志，不阻断整体聚合。
- 跨多张动态任务表查询的开销与时间窗口成正比，通过默认最近 7 天 + 任务记录
  时间过滤来控制规模。
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from scripts.domain import filters as F
from scripts.domain import schema as S
from scripts.domain.exceptions import DwsError, StoreTaskDispatcherError
from scripts.domain.records import (
    extract_records,
    get_record_id,
    values_by_name,
)
from scripts.infrastructure.config import get_base_id
from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache, _extract_fields
from scripts.services.store_service import StoreManager
from scripts.services.template_service import TemplateManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------


@dataclass
class TemplateUsage:
    """模板使用排行的单行结果。"""

    template_id: str
    template_name: str
    status: str  # enabled / disabled / unknown
    dispatch_count: int
    last_dispatch_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "status": self.status,
            "dispatch_count": self.dispatch_count,
            "last_dispatch_at": self.last_dispatch_at,
        }


@dataclass
class TemplateActiveRate:
    """模板活跃率聚合结果。"""

    total: int
    enabled: int
    disabled: int
    active_in_range: int  # 时间窗口内有派发的模板数
    enabled_rate: float  # enabled / total
    active_rate: float  # active_in_range / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "enabled": self.enabled,
            "disabled": self.disabled,
            "active_in_range": self.active_in_range,
            "enabled_rate": self.enabled_rate,
            "active_rate": self.active_rate,
        }


@dataclass
class TaskMetric:
    """任务完成率与平均耗时（按模板维度聚合）。"""

    template_id: str
    template_name: str
    dispatch_count: int  # 时间窗口内派发次数
    total_targets: int  # 累计 target_store_count
    submitted: int
    pending: int
    completion_rate: float
    avg_duration_seconds: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "dispatch_count": self.dispatch_count,
            "total_targets": self.total_targets,
            "submitted": self.submitted,
            "pending": self.pending,
            "completion_rate": self.completion_rate,
            "avg_duration_seconds": self.avg_duration_seconds,
        }


@dataclass
class StoreMetric:
    """门店表现排行。"""

    store_id: str
    store_name: str
    total_assigned: int
    submitted: int
    completion_rate: float
    avg_duration_seconds: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "store_id": self.store_id,
            "store_name": self.store_name,
            "total_assigned": self.total_assigned,
            "submitted": self.submitted,
            "completion_rate": self.completion_rate,
            "avg_duration_seconds": self.avg_duration_seconds,
        }


@dataclass
class TrendPoint:
    """时间趋势的单个桶。"""

    bucket: str  # YYYY-MM-DD（day）或 YYYY-Www（week）
    dispatch_count: int  # 该桶内派发次数（任务记录条数）
    total_targets: int
    submitted: int
    completion_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bucket": self.bucket,
            "dispatch_count": self.dispatch_count,
            "total_targets": self.total_targets,
            "submitted": self.submitted,
            "completion_rate": self.completion_rate,
        }


# ---------------------------------------------------------------------------
# 时间格式
# ---------------------------------------------------------------------------

# 任务记录里 task_date 是 dws date 字段，序列化后通常是 "YYYY-MM-DD HH:mm:ss"
_DT_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d",
)


def _parse_dt(text: Any) -> Optional[datetime]:
    """把任务记录 / 动态任务表中的时间字段解析成 ``datetime``。

    兼容字符串、毫秒时间戳两种形式；解析失败返回 ``None``。
    """
    if text is None or text == "":
        return None
    # 毫秒时间戳
    if isinstance(text, (int, float)):
        try:
            return datetime.fromtimestamp(text / 1000.0)
        except (ValueError, OSError, OverflowError):
            return None
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # ISO 8601 带 tz
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _format_iso(dt: datetime) -> str:
    """格式化为 dws filter 接受的 ISO8601 字符串（含本地 tz）。"""
    if dt.tzinfo is None:
        # 假定为本地时间
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


def _bucket_of(dt: datetime, granularity: str) -> str:
    if granularity == "week":
        # ISO 周编号，如 2026-W17
        return f"{dt.strftime('%G')}-W{dt.strftime('%V')}"
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# StatsService
# ---------------------------------------------------------------------------


class StatsService:
    """统计聚合服务。

    所有方法都接受 ``since`` / ``until``（``datetime``，本地时间，inclusive 起、
    exclusive 止），调用方负责解析 ``--days`` / ``--from`` / ``--to`` 等 CLI 入参。
    """

    def __init__(
        self,
        client: Optional[DwsClient] = None,
        cache: Optional[MappingCache] = None,
        base_id: Optional[str] = None,
        template_manager: Optional[TemplateManager] = None,
        store_manager: Optional[StoreManager] = None,
    ) -> None:
        self.client = client or DwsClient()
        self.cache = cache or MappingCache(client=self.client)
        self._base_id = base_id
        self.template_manager = template_manager or TemplateManager(
            client=self.client, cache=self.cache, base_id=base_id
        )
        self.store_manager = store_manager or StoreManager(
            client=self.client, cache=self.cache, base_id=base_id
        )
        # 缓存：base_id + table_id -> {field_name: field_id}
        self._dyn_field_map_cache: Dict[Tuple[str, str], Dict[str, str]] = {}
        # 模板元信息缓存（同一次 stats 调用中只查一次）
        self._templates_meta_cache: Optional[Dict[str, Dict[str, str]]] = None
        # 任务记录查询缓存：(since_iso, until_iso, template_id) -> records
        self._task_records_cache: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
        # 动态任务表数据缓存：table_id -> records list
        self._dyn_table_data_cache: Dict[str, List[Dict[str, Any]]] = {}

    @property
    def base_id(self) -> str:
        bid = self._base_id or get_base_id()
        if not bid:
            raise StoreTaskDispatcherError(
                "未初始化：config.json 中无 base_id，请先运行 init create/query/url"
            )
        return bid

    def _task_record_table_id(self) -> str:
        return self.cache.get_table_id(self.base_id, S.TASK_RECORD_TABLE)

    # ------------------------------------------------------------------
    # 基础查询：任务记录
    # ------------------------------------------------------------------

    def query_task_records(
        self,
        *,
        since: datetime,
        until: datetime,
        template_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """按时间范围（+ 可选模板）查任务记录，返回 fieldName-key 形式的 dict 列表。

        过滤条件：``task_date`` 在 ``[since, until)`` 区间内。
        失败时记 warning 并返回空列表（避免单次 dws 抖动毁掉整个统计）。

        同参数调用在同一 StatsService 实例内有缓存，避免多个统计方法重复查询。
        """
        # 缓存 key
        cache_key = (_format_iso(since), _format_iso(until), template_id or "")
        if cache_key in self._task_records_cache:
            return self._task_records_cache[cache_key]

        try:
            init_field = self.cache.get_field_id(
                self.base_id, S.TASK_RECORD_TABLE, "task_date"
            )
        except StoreTaskDispatcherError as exc:
            logger.warning("任务记录表缺少 task_date 字段: %s", exc)
            return []

        conds: List[Dict[str, Any]] = [
            F.after(init_field, _format_iso(since)),
            F.before(init_field, _format_iso(until)),
        ]
        if template_id:
            try:
                tpl_field = self.cache.get_field_id(
                    self.base_id, S.TASK_RECORD_TABLE, "template_id"
                )
                conds.append(F.eq(tpl_field, template_id))
            except StoreTaskDispatcherError as exc:
                logger.warning("任务记录表缺少 template_id 字段: %s", exc)
                return []
        filters = F.and_(*conds)

        try:
            payload = self.client.aitable_record_query(
                self.base_id, self._task_record_table_id(), filters
            )
        except DwsError as exc:
            logger.warning("查询任务记录失败: %s", exc)
            return []

        records = extract_records(payload)
        out: List[Dict[str, Any]] = []
        for r in records:
            d = values_by_name(self.cache, self.base_id, S.TASK_RECORD_TABLE, r)
            d["recordId"] = get_record_id(r)
            out.append(d)

        self._task_records_cache[cache_key] = out
        return out

    # ------------------------------------------------------------------
    # 1. 模板使用排行
    # ------------------------------------------------------------------

    def template_usage_ranking(
        self,
        *,
        since: datetime,
        until: datetime,
        template_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[TemplateUsage]:
        """按 ``dispatch_count`` 倒序返回模板使用排行。"""
        records = self.query_task_records(
            since=since, until=until, template_id=template_id
        )

        # 聚合：template_id -> (count, last_dispatch_at, template_name)
        agg: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "last": None, "name": ""}
        )
        for rec in records:
            tid = rec.get("template_id") or ""
            if not tid:
                continue
            entry = agg[tid]
            entry["count"] += 1
            init_dt = _parse_dt(rec.get("task_date"))
            if init_dt is not None:
                if entry["last"] is None or init_dt > entry["last"]:
                    entry["last"] = init_dt
            tname = rec.get("template_name")
            if tname and not entry["name"]:
                entry["name"] = tname

        # 兜底：从模板表补 name + status
        templates_meta = self._load_templates_meta()

        out: List[TemplateUsage] = []
        for tid, entry in agg.items():
            meta = templates_meta.get(tid, {})
            name = entry["name"] or meta.get("name", "") or tid
            status = meta.get("status", "unknown")
            last_dt: Optional[datetime] = entry["last"]
            out.append(
                TemplateUsage(
                    template_id=tid,
                    template_name=name,
                    status=status,
                    dispatch_count=entry["count"],
                    last_dispatch_at=(
                        last_dt.strftime("%Y-%m-%d %H:%M:%S")
                        if last_dt
                        else None
                    ),
                )
            )
        out.sort(key=lambda x: (-x.dispatch_count, x.template_id))
        return out[: max(limit, 0)] if limit else out

    # ------------------------------------------------------------------
    # 2. 模板活跃率
    # ------------------------------------------------------------------

    def template_active_rate(
        self, *, since: datetime, until: datetime
    ) -> TemplateActiveRate:
        """模板活跃率：启用占比 + 时间窗口内有派发的模板占比。"""
        templates_meta = self._load_templates_meta()
        total = len(templates_meta)
        enabled = sum(
            1 for m in templates_meta.values() if m.get("status") == "enabled"
        )
        disabled = total - enabled

        records = self.query_task_records(since=since, until=until)
        active_ids = {r.get("template_id") for r in records if r.get("template_id")}
        active_in_range = len(active_ids)

        return TemplateActiveRate(
            total=total,
            enabled=enabled,
            disabled=disabled,
            active_in_range=active_in_range,
            enabled_rate=round(enabled / total, 4) if total else 0.0,
            active_rate=round(active_in_range / total, 4) if total else 0.0,
        )

    # ------------------------------------------------------------------
    # 3. 任务完成率 & 平均耗时（按模板维度）
    # ------------------------------------------------------------------

    def task_completion_metrics(
        self,
        *,
        since: datetime,
        until: datetime,
        template_id: Optional[str] = None,
    ) -> List[TaskMetric]:
        """按模板维度聚合：完成率 + 平均耗时。"""
        records = self.query_task_records(
            since=since, until=until, template_id=template_id
        )
        templates_meta = self._load_templates_meta()

        # 【性能优化】批量预加载所有动态任务表数据，消除 N+1 查询
        self._batch_preload_task_tables(records)

        # 一次性把每条任务记录的动态任务表 rows 拉出来（按 template_id 累加）
        agg: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "name": "",
                "dispatch": 0,
                "targets": 0,
                "submitted": 0,
                "duration_sum": 0.0,
                "duration_count": 0,
            }
        )
        for rec in records:
            tid = rec.get("template_id") or ""
            if not tid:
                continue
            entry = agg[tid]
            entry["dispatch"] += 1
            entry["targets"] += _to_int(rec.get("target_store_count"))
            tname = rec.get("template_name")
            if tname and not entry["name"]:
                entry["name"] = tname

            sub_count, dur_sum, dur_cnt, _ = self._collect_task_table_metrics(rec)
            entry["submitted"] += sub_count
            entry["duration_sum"] += dur_sum
            entry["duration_count"] += dur_cnt

        out: List[TaskMetric] = []
        for tid, entry in agg.items():
            meta = templates_meta.get(tid, {})
            name = entry["name"] or meta.get("name", "") or tid
            targets = entry["targets"]
            submitted = entry["submitted"]
            pending = max(targets - submitted, 0)
            rate = round(submitted / targets, 4) if targets else 0.0
            avg = (
                round(entry["duration_sum"] / entry["duration_count"], 1)
                if entry["duration_count"]
                else None
            )
            out.append(
                TaskMetric(
                    template_id=tid,
                    template_name=name,
                    dispatch_count=entry["dispatch"],
                    total_targets=targets,
                    submitted=submitted,
                    pending=pending,
                    completion_rate=rate,
                    avg_duration_seconds=avg,
                )
            )
        out.sort(key=lambda x: (-x.completion_rate, -x.dispatch_count, x.template_id))
        return out

    # ------------------------------------------------------------------
    # 4. 门店表现排行
    # ------------------------------------------------------------------

    def store_ranking(
        self,
        *,
        since: datetime,
        until: datetime,
        template_id: Optional[str] = None,
        limit: int = 20,
        sort_by: str = "completion_rate",
    ) -> List[StoreMetric]:
        """门店表现排行：按 ``completion_rate`` 或 ``avg_duration`` 排序。"""
        if sort_by not in ("completion_rate", "avg_duration"):
            raise ValueError(
                f"sort_by 必须是 completion_rate / avg_duration，收到: {sort_by!r}"
            )

        records = self.query_task_records(
            since=since, until=until, template_id=template_id
        )

        # 【性能优化】批量预加载所有动态任务表数据，消除 N+1 查询
        self._batch_preload_task_tables(records)

        # store_id -> {name, total, submitted, dur_sum, dur_cnt}
        agg: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "name": "",
                "total": 0,
                "submitted": 0,
                "duration_sum": 0.0,
                "duration_count": 0,
            }
        )
        for rec in records:
            _, _, _, store_rows = self._collect_task_table_metrics(rec)
            for row in store_rows:
                sid = row.get("store_id") or ""
                if not sid:
                    continue
                entry = agg[sid]
                entry["total"] += 1
                if not entry["name"] and row.get("store_name"):
                    entry["name"] = row["store_name"]
                if row.get("submitted"):
                    entry["submitted"] += 1
                dur = row.get("duration_seconds")
                if dur is not None:
                    entry["duration_sum"] += dur
                    entry["duration_count"] += 1

        out: List[StoreMetric] = []
        for sid, entry in agg.items():
            total = entry["total"]
            submitted = entry["submitted"]
            avg = (
                round(entry["duration_sum"] / entry["duration_count"], 1)
                if entry["duration_count"]
                else None
            )
            out.append(
                StoreMetric(
                    store_id=sid,
                    store_name=entry["name"] or sid,
                    total_assigned=total,
                    submitted=submitted,
                    completion_rate=round(submitted / total, 4) if total else 0.0,
                    avg_duration_seconds=avg,
                )
            )

        if sort_by == "completion_rate":
            out.sort(key=lambda x: (-x.completion_rate, x.store_id))
        else:
            # 平均耗时：None 排到末尾，其他升序（越快越好）
            out.sort(
                key=lambda x: (
                    x.avg_duration_seconds is None,
                    x.avg_duration_seconds or 0.0,
                    x.store_id,
                )
            )
        return out[: max(limit, 0)] if limit else out

    # ------------------------------------------------------------------
    # 5. 时间趋势
    # ------------------------------------------------------------------

    def trend(
        self,
        *,
        since: datetime,
        until: datetime,
        template_id: Optional[str] = None,
        granularity: str = "day",
    ) -> List[TrendPoint]:
        """按 ``day`` / ``week`` 桶聚合派发数与完成数。"""
        if granularity not in ("day", "week"):
            raise ValueError(
                f"granularity 必须是 day / week，收到: {granularity!r}"
            )
        records = self.query_task_records(
            since=since, until=until, template_id=template_id
        )

        # 【性能优化】批量预加载所有动态任务表数据，消除 N+1 查询
        self._batch_preload_task_tables(records)

        buckets: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"dispatch": 0, "targets": 0, "submitted": 0}
        )
        for rec in records:
            init_dt = _parse_dt(rec.get("task_date"))
            if init_dt is None:
                continue
            key = _bucket_of(init_dt, granularity)
            entry = buckets[key]
            entry["dispatch"] += 1
            entry["targets"] += _to_int(rec.get("target_store_count"))
            sub_count, _, _, _ = self._collect_task_table_metrics(rec)
            entry["submitted"] += sub_count

        out: List[TrendPoint] = []
        for bucket in sorted(buckets.keys()):
            e = buckets[bucket]
            targets = e["targets"]
            submitted = e["submitted"]
            out.append(
                TrendPoint(
                    bucket=bucket,
                    dispatch_count=e["dispatch"],
                    total_targets=targets,
                    submitted=submitted,
                    completion_rate=(
                        round(submitted / targets, 4) if targets else 0.0
                    ),
                )
            )
        return out

    # ------------------------------------------------------------------
    # 内部：模板元信息
    # ------------------------------------------------------------------

    def _load_templates_meta(self) -> Dict[str, Dict[str, str]]:
        """加载所有模板的 ``{template_id: {name, status}}``。

        同一 StatsService 实例内带缓存，避免多个统计方法重复查询。
        """
        if self._templates_meta_cache is not None:
            return self._templates_meta_cache
        try:
            templates = self.template_manager.list_templates()
        except Exception as exc:  # pragma: no cover - 防御
            logger.warning("加载模板列表失败: %s", exc)
            return {}
        meta: Dict[str, Dict[str, str]] = {}
        for t in templates:
            tid = t.get("template_id")
            if not tid:
                continue
            meta[tid] = {
                "name": t.get("name", "") or "",
                "status": t.get("status", "unknown") or "unknown",
            }
        self._templates_meta_cache = meta
        return meta

    # ------------------------------------------------------------------
    # 内部：动态任务表统计（批量优化）
    # ------------------------------------------------------------------

    def _batch_preload_task_tables(
        self, records: List[Dict[str, Any]]
    ) -> None:
        """批量预加载所有动态任务表的数据到缓存。

        从 records 中收集所有不重复的 instance_table_id，然后使用
        DwsClient.aitable_record_query_batch 并发查询，将结果缓存到
        self._dyn_table_data_cache。

        这是消除 N+1 查询的核心方法。
        """
        # 收集所有不重复的 table_id
        table_ids: List[str] = []
        seen: set = set()
        for rec in records:
            tid = (
                rec.get("instance_table_id")
                or rec.get("task_table_id")
                or ""
            )
            if tid and tid not in seen and tid not in self._dyn_table_data_cache:
                table_ids.append(tid)
                seen.add(tid)

        if not table_ids:
            return

        logger.debug(
            "批量预加载 %d 张动态任务表数据", len(table_ids)
        )

        # 先预加载字段映射（如果未缓存的话）
        for tid in table_ids:
            key = (self.base_id, tid)
            if key not in self._dyn_field_map_cache:
                try:
                    self._get_dyn_field_map(tid)
                except DwsError as exc:
                    logger.warning(
                        "动态任务表 %s 字段读取失败，跳过: %s", tid, exc
                    )

        # 批量并发查询所有动态任务表数据
        batch_results = self.client.aitable_record_query_batch(
            self.base_id, table_ids, max_workers=5
        )

        # 将结果解析为 records 列表并缓存
        for tid, payload in batch_results.items():
            self._dyn_table_data_cache[tid] = extract_records(payload)

    def _collect_task_table_metrics(
        self, task_record: Dict[str, Any]
    ) -> Tuple[int, float, int, List[Dict[str, Any]]]:
        """从动态任务表中读取统计指标。

        优先从 _dyn_table_data_cache 读取（由 _batch_preload_task_tables 预加载），
        若缓存未命中则回退到单次查询。

        Returns:
            ``(submitted_count, duration_sum, duration_count, store_rows)``

            其中 ``store_rows`` 是每行的 ``{store_id, store_name, submitted, duration_seconds}``
            列表，供门店维度聚合复用，避免重复拉表。
        """
        # 兼容新字段名 instance_table_id 和旧字段名 task_table_id
        table_id = (
            task_record.get("instance_table_id")
            or task_record.get("task_table_id")
            or ""
        )
        if not table_id:
            return 0, 0.0, 0, []

        # 解析 task_date，用于算 duration
        init_dt = _parse_dt(task_record.get("task_date"))

        try:
            field_map = self._get_dyn_field_map(table_id)
        except DwsError as exc:
            logger.warning(
                "动态任务表 %s 字段读取失败（可能已被删除），跳过: %s",
                table_id,
                exc,
            )
            return 0, 0.0, 0, []

        if not field_map:
            return 0, 0.0, 0, []

        # 优先从批量预加载缓存读取
        if table_id in self._dyn_table_data_cache:
            records = self._dyn_table_data_cache[table_id]
        else:
            # 回退：单次查询
            try:
                payload = self.client.aitable_record_query(
                    self.base_id, table_id, None
                )
            except DwsError as exc:
                logger.warning(
                    "动态任务表 %s 数据读取失败（可能已被删除），跳过: %s",
                    table_id,
                    exc,
                )
                return 0, 0.0, 0, []
            records = extract_records(payload)
            # 缓存以备后续调用
            self._dyn_table_data_cache[table_id] = records

        reverse = {fid: name for name, fid in field_map.items()}

        submitted_count = 0
        duration_sum = 0.0
        duration_count = 0
        store_rows: List[Dict[str, Any]] = []
        for r in records:
            cells = r.get("cells") or r.get("fields") or {}
            if not isinstance(cells, dict):
                continue
            row = {reverse.get(k, k): v for k, v in cells.items()}
            # 纯 prefill 模式下记录存在即视为已提交
            submitted = True
            row_info: Dict[str, Any] = {
                "store_id": row.get("store_id") or "",
                "store_name": row.get("store_name") or "",
                "submitted": submitted,
                "duration_seconds": None,
            }
            if submitted:
                submitted_count += 1
                sub_dt = _parse_dt(row.get("submitted_at"))
                if init_dt is not None and sub_dt is not None:
                    delta = (sub_dt - init_dt).total_seconds()
                    if delta > 0:
                        duration_sum += delta
                        duration_count += 1
                        row_info["duration_seconds"] = delta
            store_rows.append(row_info)
        return submitted_count, duration_sum, duration_count, store_rows

    def _get_dyn_field_map(self, table_id: str) -> Dict[str, str]:
        """获取动态任务表的 fieldName→fieldId 映射（带本服务级缓存）。"""
        key = (self.base_id, table_id)
        if key in self._dyn_field_map_cache:
            return self._dyn_field_map_cache[key]
        payload = self.client.aitable_table_get(self.base_id, table_id)
        fields = _extract_fields(payload)
        mapping: Dict[str, str] = {}
        for f in fields:
            name = f.get("name") or f.get("fieldName")
            fid = f.get("fieldId") or f.get("id")
            if name and fid:
                mapping[name] = fid
        self._dyn_field_map_cache[key] = mapping
        return mapping


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------


def _to_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


__all__ = [
    "StatsService",
    "TemplateUsage",
    "TemplateActiveRate",
    "TaskMetric",
    "StoreMetric",
    "TrendPoint",
]
