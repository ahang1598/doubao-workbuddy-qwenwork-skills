"""dws CLI 子进程封装层。

将所有 ``dws`` 命令统一通过 :class:`DwsClient` 调用：
自动追加 ``-y -f json`` 参数，解析 JSON 输出，并在网络/超时类错误时按
指数退避重试。

所有命令都返回 ``dict``（dws JSON 输出经 ``json.loads`` 后的结构）。

为了便于单元测试 mock，全模块只通过 :func:`subprocess.run` 与外部交互。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from scripts.domain.exceptions import DwsError

logger = logging.getLogger(__name__)

def _resolve_dws_bin() -> str:
    """解析 dws 可执行文件路径。

    优先级：
    1. 环境变量 ``DWS_BIN_PATH``（显式指定）
    2. 本地配置文件 config.json 中的 ``dws_bin_path`` 字段
    3. 回退到 ``dws``（打包部署环境，依赖 PATH）
    """
    # env_path = os.environ.get("DWS_BIN_PATH")
    # if env_path:
    #     return env_path
    # try:
    #     from scripts.infrastructure.config import get_dws_bin_path
    #     config_path = get_dws_bin_path()
    #     if config_path:
    #         return config_path
    # except Exception as exc:
    #     logger.warning("读取 dws 可执行路径配置失败，回退到 PATH 中的 'dws': %s", exc)
    return "dws"


DEFAULT_DWS_BIN = _resolve_dws_bin()
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY = 3
DEFAULT_BACKOFF_BASE = 0.5  # 秒，指数退避基准

# 被认为可重试的 dws 错误码 / 关键字
_RETRYABLE_KEYWORDS = (
    "timeout",
    "timed out",
    "connection reset",
    "connection refused",
    "temporarily unavailable",
    "rate limit",
)


# dws 在 stdout JSON 中常见的可重试 server_error_code（business_error 类）
_RETRYABLE_SERVER_ERROR_CODES = {
    "TIMEOUT_ERROR",
    "RATE_LIMIT",
    "RATE_LIMITED",
    "TOO_MANY_REQUESTS",
    "SERVICE_UNAVAILABLE",
    "INTERNAL_ERROR",
}

def _stdout_retryable(stdout: str) -> bool:
    """检查 dws stdout JSON 是否标识为可重试错误。

    dws 失败时仍可能输出结构化 JSON（``-f json`` 模式），形如：
    ``{"error": {"retryable": true, "server_error_code": "TIMEOUT_ERROR", ...}}``
    需同时识别两类信号：
    1. ``error.retryable == true``（dws 显式标记）
    2. ``error.server_error_code`` 命中可重试错误码白名单
    """
    text = (stdout or "").strip()
    if not text:
        return False
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not isinstance(obj, dict):
        return False
    err_obj = obj.get("error")
    if not isinstance(err_obj, dict):
        return False
    if err_obj.get("retryable") is True:
        return True
    code = err_obj.get("server_error_code") or err_obj.get("code")
    if isinstance(code, str) and code.upper() in _RETRYABLE_SERVER_ERROR_CODES:
        return True
    return False

def _is_retryable(
    stderr: str,
    exc: Optional[BaseException] = None,
    stdout: str = "",
) -> bool:
    """根据 stderr / stdout 内容或异常类型判断是否可重试。

    Args:
        stderr: 子进程 stderr。
        exc: 触发本次判定的异常（如 TimeoutExpired）。
        stdout: 子进程 stdout（dws 在 ``-f json`` 模式下失败也会输出 JSON，
            其中可能含 ``error.retryable=true`` 或 ``server_error_code=TIMEOUT_ERROR``
            等可重试标记，必须一并识别，否则会出现"重试 1/2 次后被静默放弃"的故障）。
    """
    if isinstance(exc, subprocess.TimeoutExpired):
        return True
    lowered = (stderr or "").lower()
    if any(kw in lowered for kw in _RETRYABLE_KEYWORDS):
        return True
    # 关键修复：dws business_error 的 retryable 标记写在 stdout JSON 里
    return _stdout_retryable(stdout)


class DwsClient:
    """dws CLI 的薄封装。

    Args:
        bin_path: dws 可执行路径，默认 ``dws``。
        timeout: 单次命令最长等待时间（秒）。
        max_retry: 失败重试次数（仅对网络/超时类错误重试）。
        backoff_base: 指数退避基准秒数，第 ``n`` 次重试等待 ``base * 2**(n-1)``。
    """

    def __init__(
        self,
        bin_path: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retry: int = DEFAULT_RETRY,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        base_get_ttl: float = 300.0,
    ) -> None:
        self.bin_path = bin_path or DEFAULT_DWS_BIN
        self.timeout = timeout
        self.max_retry = max_retry
        self.backoff_base = backoff_base
        # base_get 缓存：base_id -> (result_dict, timestamp)
        self._base_get_cache: Dict[str, tuple] = {}
        self._base_get_ttl = base_get_ttl

    # ------------------------------------------------------------------
    # 底层 subprocess 调用
    # ------------------------------------------------------------------

    def _run(self, args: Sequence[str], *, parse_json: bool = True) -> Any:
        """执行 dws 命令，自动追加 ``-y -f json``。

        Returns:
            ``parse_json=True`` 时返回 JSON 解析结果；否则返回原始 stdout 字符串。

        Raises:
            DwsError: 命令返回非零或 JSON 解析失败。
        """
        full_args: List[str] = [self.bin_path, *args]
        # 仅在用户未自行指定 -f / -y 时追加，避免重复
        if not any(a in ("-y", "--yes") for a in args):
            full_args.append("-y")
        if parse_json and not any(a in ("-f", "--format") for a in args):
            full_args.extend(["-f", "json"])

        last_exc: Optional[BaseException] = None
        for attempt in range(1, self.max_retry + 1):
            t0 = time.time()
            try:
                logger.debug("dws exec (attempt %d): %s", attempt, full_args)
                proc = subprocess.run(
                    full_args,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                logger.debug("dws exec TIMEOUT after %.3fs: %s", time.time() - t0, full_args)
                last_exc = exc
                logger.warning("dws timeout on attempt %d: %s", attempt, exc)
                if attempt >= self.max_retry:
                    raise DwsError(
                        f"dws 命令超时（{self.timeout}s）",
                        code="TIMEOUT",
                        stdout="",
                        stderr=str(exc),
                        args_list=list(full_args),
                    ) from exc
                self._sleep_backoff(attempt)
                continue
            except FileNotFoundError as exc:
                # dws 可执行文件不存在，无重试意义
                raise DwsError(
                    f"未找到 dws 可执行文件: {self.bin_path}",
                    code="ENOENT",
                    stderr=str(exc),
                    args_list=list(full_args),
                ) from exc

            elapsed = time.time() - t0
            logger.debug("dws exec done in %.3fs (rc=%d): %s", elapsed, proc.returncode, full_args)

            if proc.returncode != 0:
                if (
                    attempt < self.max_retry
                    and _is_retryable(proc.stderr, stdout=proc.stdout)
                ):
                    # 优先打印 stdout（dws -f json 失败时结构化错误在 stdout），
                    # 兜底用 stderr，确保 trace_id / server_error_code 可见。
                    logger.warning(
                        "dws retryable failure on attempt %d: %s",
                        attempt,
                        proc.stdout.strip() or proc.stderr.strip(),
                    )
                    self._sleep_backoff(attempt)
                    continue
                code = self._extract_error_code(proc.stdout, proc.stderr)
                raise DwsError(
                    proc.stderr.strip() or proc.stdout.strip() or "dws 命令执行失败",
                    code=code,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    args_list=list(full_args),
                )

            if not parse_json:
                return proc.stdout

            stdout = proc.stdout.strip()
            if not stdout:
                return {}
            try:
                result = json.loads(stdout)
            except json.JSONDecodeError as exc:
                raise DwsError(
                    f"dws 输出不是有效 JSON: {exc.msg}",
                    code="JSON_DECODE",
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    args_list=list(full_args),
                ) from exc

            # AITable CLI 在业务错误时仍以退出码 0 返回，错误信息放在
            # JSON 的 status/error 字段里，需要在此统一检测并抛出异常。
            if isinstance(result, dict) and result.get("status") == "error":
                error_info = result.get("error") or {}
                error_code = error_info.get("code") or "API_ERROR"
                error_message = error_info.get("message") or result.get("summary") or "AITable 返回错误"
                raise DwsError(
                    error_message,
                    code=error_code,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    args_list=list(full_args),
                )

            return result

        # 理论不可达
        raise DwsError(  # pragma: no cover
            "dws 命令异常退出（重试已耗尽）",
            code="UNKNOWN",
            args_list=list(full_args),
        ) from last_exc

    def _sleep_backoff(self, attempt: int) -> None:
        delay = self.backoff_base * (2 ** (attempt - 1))
        time.sleep(delay)

    @staticmethod
    def _extract_error_code(stdout: str, stderr: str) -> Optional[str]:
        """尝试从 stdout（dws 失败时也可能输出 JSON）或 stderr 中抽取错误码。"""
        for text in (stdout, stderr):
            text = (text or "").strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                code = obj.get("code") or obj.get("errorCode")
                if code:
                    return str(code)
        return None

    # ------------------------------------------------------------------
    # aitable: base
    # ------------------------------------------------------------------

    def aitable_base_get(self, base_id: str) -> dict:
        """获取 AI表格 详情（含 ``tables`` 列表）。"""
        return self._run(["aitable", "base", "get", "--base-id", base_id])

    def aitable_base_get_cached(self, base_id: str) -> dict:
        """获取 AI表格 详情（带 TTL 缓存）。

        同一 DwsClient 实例内，对同一 base_id 的调用在 TTL（默认 300s）内
        直接返回缓存结果，避免多个服务重复调用 ``aitable base get``。
        """
        now = time.time()
        if base_id in self._base_get_cache:
            result, ts = self._base_get_cache[base_id]
            if now - ts < self._base_get_ttl:
                return result
        result = self.aitable_base_get(base_id)
        self._base_get_cache[base_id] = (result, now)
        return result

    def aitable_record_query_batch(
        self,
        base_id: str,
        table_ids: List[str],
        *,
        filters: Optional[dict] = None,
        limit: Optional[int] = None,
        sort: Optional[list] = None,
        max_workers: int = 5,
    ) -> Dict[str, dict]:
        """并发批量查询多张表的记录。

        Args:
            base_id: Base ID。
            table_ids: 要查询的表 ID 列表。
            filters: 统一的过滤条件（所有表共用），None 表示无过滤。
            limit: 每张表的记录数限制。
            sort: 排序条件。
            max_workers: 最大并发数（默认 5）。

        Returns:
            dict，key 为 table_id，value 为 aitable_record_query 的返回结果。
            查询失败的表不会出现在返回结果中（错误会记录日志）。
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if not table_ids:
            return {}

        results: Dict[str, dict] = {}

        def _query_one(table_id: str) -> tuple:
            t0 = time.time()
            data = self.aitable_record_query(
                base_id, table_id, filters, limit=limit, sort=sort
            )
            elapsed = time.time() - t0
            logger.debug(
                "batch_query table %s done in %.3fs", table_id, elapsed
            )
            return (table_id, data)

        if len(table_ids) == 1:
            try:
                tid, data = _query_one(table_ids[0])
                results[tid] = data
            except Exception as exc:
                logger.warning("batch_query 单表查询失败 [%s]: %s", table_ids[0], exc)
            return results

        with ThreadPoolExecutor(max_workers=min(max_workers, len(table_ids))) as executor:
            future_to_tid = {
                executor.submit(_query_one, tid): tid for tid in table_ids
            }
            for future in as_completed(future_to_tid):
                tid = future_to_tid[future]
                try:
                    _, data = future.result()
                    results[tid] = data
                except Exception as exc:
                    logger.warning("batch_query 查询失败 [%s]: %s", tid, exc)

        return results

    def aitable_base_list(self, limit: int = 10) -> dict:
        """列出最近访问过的 AI表格。"""
        return self._run(["aitable", "base", "list", "--limit", str(limit)])

    def aitable_base_search(self, query: str) -> dict:
        """按关键词搜索 AI表格。"""
        return self._run(["aitable", "base", "search", "--query", query])

    def aitable_base_create(self, name: str) -> dict:
        """创建新 AI表格。"""
        return self._run(["aitable", "base", "create", "--name", name])

    def aitable_base_delete(self, base_id: str) -> dict:
        """删除 AI表格（高危，调用前必须二次确认）。"""
        return self._run(["aitable", "base", "delete", "--base-id", base_id])

    # ------------------------------------------------------------------
    # aitable: table
    # ------------------------------------------------------------------

    def aitable_table_get(
        self, base_id: str, table_ids: Union[str, Iterable[str]]
    ) -> dict:
        """获取一张或多张表的字段目录。

        Args:
            table_ids: 单个 tableId 或 tableId 列表（dws 支持逗号分隔）。
        """
        ids = table_ids if isinstance(table_ids, str) else ",".join(table_ids)
        return self._run(
            [
                "aitable",
                "table",
                "get",
                "--base-id",
                base_id,
                "--table-ids",
                ids,
            ]
        )

    def aitable_table_create(
        self,
        base_id: str,
        table_name: str,
        fields: list,
    ) -> dict:
        """创建一张新表。

        Args:
            fields: dws 字段定义列表（最多 15 个）。每项含 ``name`` / ``type`` /
                可选 ``config``。
        """
        return self._run(
            [
                "aitable",
                "table",
                "create",
                "--base-id",
                base_id,
                "--name",
                table_name,
                "--fields",
                json.dumps(fields, ensure_ascii=False),
            ]
        )

    def aitable_table_delete(self, base_id: str, table_id: str) -> dict:
        """删除数据表（不可逆）。

        注意：AI表格 中最后一张表无法删除，服务端会报错。
        """
        return self._run(
            [
                "aitable",
                "table",
                "delete",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
            ]
        )

    def aitable_dashboard_delete(self, base_id: str, dashboard_id: str) -> dict:
        """删除仪表盘（级联删除其下所有图表，不可逆）。"""
        return self._run(
            [
                "aitable",
                "dashboard",
                "delete",
                "--base-id",
                base_id,
                "--dashboard-id",
                dashboard_id,
            ]
        )

    # ------------------------------------------------------------------
    # aitable: field
    # ------------------------------------------------------------------

    def aitable_field_get(
        self,
        base_id: str,
        table_id: str,
        field_ids: Union[str, Iterable[str]],
    ) -> dict:
        ids = field_ids if isinstance(field_ids, str) else ",".join(field_ids)
        return self._run(
            [
                "aitable",
                "field",
                "get",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
                "--field-ids",
                ids,
            ]
        )

    def aitable_field_create(
        self,
        base_id: str,
        table_id: str,
        fields: list,
    ) -> dict:
        """补齐字段（单次最多 15 个）。

        dws field create 接口要求字段名用 ``fieldName``，而 schema.py 中统一
        使用 ``name``。此处做自动转换，调用方无需关心两套命名的差异。
        """
        normalized_fields = [
            {**{k: v for k, v in f.items() if k != "name"}, "fieldName": f["name"]}
            if "name" in f and "fieldName" not in f
            else f
            for f in fields
        ]
        result = self._run(
            [
                "aitable",
                "field",
                "create",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
                "--fields",
                json.dumps(normalized_fields, ensure_ascii=False),
            ]
        )
        failed_count = (result.get("data") or {}).get("failedCount", 0)
        if failed_count > 0:
            failed_results = (result.get("data") or {}).get("results", [])
            failed_details = [
                f"{r.get('fieldName') or r.get('name', '?')}: {r.get('reason') or r.get('errorMessage', 'unknown')}"
                for r in failed_results
                if not r.get("success")
            ]
            raise DwsError(
                f"field_create 部分失败：{failed_count}/{len(normalized_fields)} 个字段创建失败"
                + (f"，详情: {failed_details}" if failed_details else ""),
                code="FIELD_CREATE_PARTIAL_FAILURE",
                stdout=json.dumps(result, ensure_ascii=False),
                stderr="",
            )
        return result

    def aitable_field_create_single(
        self,
        base_id: str,
        table_id: str,
        name: str,
        field_type: str,
        config: Optional[dict] = None,
        ai_config: Optional[dict] = None,
    ) -> dict:
        """创建单个字段（支持 AI 字段）。

        与 :meth:`aitable_field_create` 互不干扰：

        - ``aitable_field_create()``: 批量创建（``--fields '[...]'``），不支持 ``--ai-config``
        - 本方法: 单个创建（``--name`` + ``--type``），支持 ``--ai-config``

        Args:
            base_id: Base ID。
            table_id: 表 ID。
            name: 字段名称。
            field_type: 字段类型（如 ``text``、``attachment`` 等）。
            config: 字段通用配置（可选）。
            ai_config: AI 字段配置（可选），包含 ``outputType`` 和 ``prompt`` 数组。
        """
        args: List[str] = [
            "aitable",
            "field",
            "create",
            "--base-id",
            base_id,
            "--table-id",
            table_id,
            "--name",
            name,
            "--type",
            field_type,
        ]
        if config is not None:
            args.extend(["--config", json.dumps(config, ensure_ascii=False)])
        if ai_config is not None:
            args.extend(["--ai-config", json.dumps(ai_config, ensure_ascii=False)])
        return self._run(args)

    def aitable_field_get_all(self, base_id: str, table_id: str) -> dict:
        """获取表的全部字段信息。

        Returns:
            dws JSON 输出，其中 ``data.fields`` 为字段列表。
        """
        return self._run(
            [
                "aitable",
                "field",
                "get",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
            ]
        )

    # ------------------------------------------------------------------
    # aitable: view
    # ------------------------------------------------------------------

    def aitable_view_get(self, base_id: str, table_id: str) -> dict:
        return self._run(
            [
                "aitable",
                "view",
                "get",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
            ]
        )

    def aitable_view_create(
        self,
        base_id: str,
        table_id: str,
        view_type: str,
        name: str,
    ) -> dict:
        return self._run(
            [
                "aitable",
                "view",
                "create",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
                "--view-type",
                view_type,
                "--name",
                name,
            ]
        )

    def aitable_view_create_form(
        self,
        base_id: str,
        table_id: str,
        name: str = "巡检上报表单",
        config: Optional[dict] = None,
        view_sub_type: Optional[str] = None,
    ) -> dict:
        """创建 FormDesigner 类型的表单视图，返回原始 dict。

        Args:
            base_id: Base 唯一标识。
            table_id: 数据表唯一标识。
            name: 表单视图名称。
            config: 可选，视图配置，支持 visibleFieldIds（控制表单可见字段）。
                示例：{"visibleFieldIds": ["fldXxx", "fldYyy"]}
            view_sub_type: 可选，视图子类型，用于实现「每人只能填一次」等限制。

        Returns:
            dws 返回的原始 dict，预期含 viewId / shareUrl / formUrl 等字段。
        """
        args = [
            "aitable",
            "view",
            "create",
            "--base-id",
            base_id,
            "--table-id",
            table_id,
            "--view-type",
            "FormDesigner",
            "--name",
            name,
        ]
        if config:
            args += ["--config", json.dumps(config, ensure_ascii=False)]
        if view_sub_type:
            args += ["--view-sub-type", view_sub_type]
        return self._run(args)

    def aitable_view_get_detail(
        self,
        base_id: str,
        table_id: str,
        view_id: str,
    ) -> dict:
        """获取指定视图的详情，用于提取表单链接。"""
        return self._run(
            [
                "aitable",
                "view",
                "get",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
                "--view-ids",
                view_id,
            ]
        )

    def aitable_view_publish_share(
        self,
        base_id: str,
        table_id: str,
        view_id: str,
    ) -> dict:
        """发布并分享表单视图，返回含分享链接的响应。

        通过 view update 传入 shareStatus=true 来发布表单，
        平台会在响应中返回 shareUrl 等分享链接字段。
        失败时抛出 DwsError。
        """
        return self._run(
            [
                "aitable",
                "view",
                "update",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
                "--view-id",
                view_id,
                "--config",
                json.dumps({"authTypeCode": 0, "loadLastSubmit": True, "status": 1}, ensure_ascii=False),
            ]
        )

    def aitable_view_update(
        self,
        base_id: str,
        table_id: str,
        view_id: str,
        config: Optional[dict] = None,
    ) -> dict:
        """更新视图配置（如 visibleFieldIds）。

        通过 dws aitable view update --config 更新指定视图的配置。
        典型场景：模版 custom_fields 的 hidden 属性变更后，
        需要同步更新已有表单视图的 visibleFieldIds。

        与 aitable_view_publish_share 的区别：
        - publish_share 专用于发布分享（传 authTypeCode/status 等参数）
        - 本方法专用于更新视图配置（如 visibleFieldIds）
        """
        args = [
            "aitable", "view", "update",
            "--base-id", base_id,
            "--table-id", table_id,
            "--view-id", view_id,
        ]
        if config:
            args += ["--config", json.dumps(config, ensure_ascii=False)]
        return self._run(args)

    # ------------------------------------------------------------------
    # aitable: record
    # ------------------------------------------------------------------

    def aitable_record_query(
        self,
        base_id: str,
        table_id: str,
        filters: Optional[dict] = None,
        *,
        fields: Optional[Sequence[str]] = None,
        limit: Optional[int] = None,
        sort: Optional[list] = None,
        cursor: Optional[str] = None,
        fetch_all: bool = False,
        page_limit: int = 50,
    ) -> dict:
        """查询表记录。

        Args:
            fetch_all: 启用自动翻页模式（--all），拉取全量数据。
            page_limit: fetch_all 模式下最大翻页次数，默认 50（即 5000 条）。
                设为 0 表示无限制。
            cursor: 分页游标，用于手动分页或断点续传。
        """
        args = [
            "aitable",
            "record",
            "query",
            "--base-id",
            base_id,
            "--table-id",
            table_id,
        ]
        if fields:
            args.extend(["--fields", ",".join(fields)])
        if filters is not None:
            # dws 要求 --filters 最外层必须是 and/or，否则会被静默忽略，
            # 等同于无条件查询全表（曾导致任务记录/通知记录被误覆盖，详见
            # .aone_copilot/issue/aitable-filter-upsert-overwrite.md）。
            # 这里做一次兜底自动包裹，防止调用方误传裸条件。
            outer_op = filters.get("operator") if isinstance(filters, dict) else None
            if outer_op not in ("and", "or"):
                logger.warning(
                    "aitable_record_query 收到裸 filter（operator=%s），"
                    "自动包裹为 and。建议调用方显式使用 F.and_/F.or_。",
                    outer_op,
                )
                filters = {"operator": "and", "operands": [filters]}
            args.extend(["--filters", json.dumps(filters, ensure_ascii=False)])
        if fetch_all:
            args.append("--all")
            if page_limit != 50:
                args.extend(["--page-limit", str(page_limit)])
        elif limit is not None:
            args.extend(["--limit", str(limit)])
        if cursor is not None:
            args.extend(["--cursor", cursor])
        if sort is not None:
            args.extend(["--sort", json.dumps(sort, ensure_ascii=False)])
        return self._run(args)

    def aitable_record_create(
        self,
        base_id: str,
        table_id: str,
        records: list,
    ) -> dict:
        """新增记录。

        Args:
            records: 形如 ``[{"cells": {"<fldId>": <value>, ...}}, ...]``
        """
        records_json = json.dumps(records, ensure_ascii=False)
        logger.debug(
            "[aitable_record_create] 调用，base_id=%s, table_id=%s, records_count=%d",
            base_id, table_id, len(records),
        )
        logger.debug("[aitable_record_create] records JSON: %s", records_json)
        result = self._run(
            [
                "aitable",
                "record",
                "create",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
                "--records",
                records_json,
            ]
        )
        logger.debug("[aitable_record_create] 返回结果: %s", result)
        return result

    def aitable_record_update(
        self,
        base_id: str,
        table_id: str,
        records: list,
    ) -> dict:
        """更新记录。

        Args:
            records: 形如 ``[{"recordId": "...", "cells": {"<fldId>": <value>}}, ...]``
        """
        return self._run(
            [
                "aitable",
                "record",
                "update",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
                "--records",
                json.dumps(records, ensure_ascii=False),
            ]
        )

    def aitable_record_delete(
        self,
        base_id: str,
        table_id: str,
        record_ids: Union[str, Iterable[str]],
    ) -> dict:
        ids = record_ids if isinstance(record_ids, str) else ",".join(record_ids)
        return self._run(
            [
                "aitable",
                "record",
                "delete",
                "--base-id",
                base_id,
                "--table-id",
                table_id,
                "--record-ids",
                ids,
            ]
        )

    # ------------------------------------------------------------------
    # chat / contact
    # ------------------------------------------------------------------

    def chat_message_send(
        self,
        open_dingtalk_id: str,
        content: str,
        *,
        title: Optional[str] = None,
    ) -> dict:
        """向指定用户发送钉钉单聊消息（默认按 Markdown 渲染）。

        Args:
            open_dingtalk_id: 接收人的 openDingTalkId（从 user 字段或
                ``contact user search`` 返回中获取）。
            content: 消息正文，支持 Markdown 语法（粗体 ``**xx**``、链接
                ``[name](url)``、bullet ``- ``、标题 ``###`` 等）。作为
                ``dws chat message send`` 的位置参数传入。
            title: 钉钉消息列表中显示的消息标题。``None`` 或空字符串时不
                传 ``--title``，由 dws 用消息内容首行做兜底。

        注意：
            - dws ``chat message send`` 的 ``--msg-type`` 仅用于切换
              ``image`` / ``file`` 富媒体；普通 Markdown 文本无需指定，
              dws 会自动按 Markdown 渲染（对纯文本完全兼容）。
            - ``--user`` 参数已废弃，现在使用 ``--open-dingtalk-id``。
        """
        args = [
            "chat",
            "message",
            "send",
            "--open-dingtalk-id",
            open_dingtalk_id,
        ]
        if title:
            args.extend(["--title", title])
        # content 作为位置参数（与 dws 帮助里的 Examples 一致）
        args.append(content)
        return self._run(args)

    def contact_user_search(self, keyword: str) -> dict:
        """按姓名/关键词搜索用户，返回 userId 列表。"""
        return self._run(
            ["contact", "user", "search", "--query", keyword]
        )

    def contact_user_get(self, user_ids: Union[str, List[str]]) -> dict:
        """批量获取用户详情。

        Args:
            user_ids: 单个 userId 字符串或 userId 列表。

        Returns:
            dws 原始返回，格式示例::

                {"result": [{"orgEmployeeModel": {"orgUserId": "000001",
                 "orgUserName": "张三", ...}}], "success": true}
        """
        if isinstance(user_ids, list):
            ids_str = ",".join(user_ids)
        else:
            ids_str = user_ids
        return self._run(
            ["contact", "user", "get", "--ids", ids_str]
        )

    def get_user_name(self, user_id: str) -> Optional[str]:
        """通过 userId 查询用户姓名。

        调用 ``contact user get --ids <userId>``，从返回的
        ``result[0].orgEmployeeModel.orgUserName`` 提取姓名。
        """
        try:
            result = self.contact_user_get(user_id)
            users = result.get("result", [])
            if users:
                emp = users[0].get("orgEmployeeModel") or {}
                return emp.get("orgUserName")
        except DwsError:
            raise
        except Exception as exc:
            logger.warning("查询用户姓名失败 userId=%s: %s", user_id, exc)
        return None

    def get_open_dingtalk_id(self, manager_name: str) -> Optional[str]:
        """通过姓名搜索用户，返回 openDingTalkId。

        用于 ``dws chat message send --open-dingtalk-id`` 参数。
        当门店 manager 字段中未直接包含 openDingTalkId 时，
        通过 userId → 姓名 → search 的链路降级获取。
        """
        try:
            result = self.contact_user_search(manager_name)
            users = result.get("result", [])
            if users:
                return users[0].get("openDingTalkId")
        except DwsError:
            raise
        except Exception as exc:
            logger.warning("搜索用户 openDingTalkId 失败 name=%s: %s", manager_name, exc)
        return None

    def contact_user_search_mobile(self, mobile: str) -> dict:
        return self._run(
            ["contact", "user", "search-mobile", "--mobile", mobile]
        )

    def contact_user_get_self(self) -> dict:
        return self._run(["contact", "user", "get-self"])


__all__ = ["DwsClient", "DEFAULT_DWS_BIN"]
