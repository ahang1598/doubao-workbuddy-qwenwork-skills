#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch a DingTalk AI-table snapshot with bounded retries and explicit degradation.

The skill is portable: it invokes the ``dws`` executable from PATH and never
contains machine-specific account routing. Structured APIs are preferred
because they preserve real record IDs. If those APIs remain unavailable after
bounded retries, the script requests an official Excel export and records the
loss of row-level drill-down capability in ``manifest.json``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


TRANSIENT_MARKERS = (
    "system_error", "system error", "internal error", "temporarily unavailable",
    "service unavailable", "timeout", "timed out", "rate limit",
    "too many requests",
)
AUTH_MARKERS = ("not authenticated", "token invalid", "token expired", "unauthorized", "未登录", "登录失效")
PERMISSION_MARKERS = (
    "forbidden", "permission denied", "no permission", "does not have read access",
    "org_doc_token_mismatch", "无权限", "没有权限",
)
NOT_FOUND_MARKERS = ("not found", "does not exist", "不存在")
COMMAND_MARKERS = (
    "unknown flag", "unknown command", "invalid filter operator", "invalid_limit",
    "limit must be between", "required flag", "flag needs an argument", "accepts ",
    "invalid value for --",
)


@dataclass
class DwsCommandError(RuntimeError):
    command: list[str]
    message: str
    category: str
    retryable: bool
    trace_ids: tuple[str, ...] = ()

    def __str__(self) -> str:
        return f"DWS 命令失败（{self.category}）：{' '.join(self.command[:4])}\n{self.message}"


def command_prefix() -> list[str]:
    dws = shutil.which("dws")
    if not dws:
        raise SystemExit("未找到 dws。请先安装并登录钉钉 DWS CLI，或改用导出的 CSV/JSON/XLSX。")
    return [dws]


def parse_aitable_url(value: str) -> tuple[str | None, str | None, str | None]:
    """Extract Base/table/view IDs from DingTalk AI-table URLs."""
    parsed = urlparse(value)
    match = re.search(r"/nodes/([^/?#]+)", parsed.path)
    base_id = match.group(1) if match else None
    outer = parse_qs(parsed.query)
    nested: dict[str, list[str]] = {}
    iframe_query = outer.get("iframeQuery", [""])[0]
    if iframe_query:
        nested = parse_qs(iframe_query)

    def first(*keys: str) -> str | None:
        for key in keys:
            values = nested.get(key) or outer.get(key)
            if values and values[0]:
                return values[0]
        return None

    return base_id, first("sheetId", "tableId"), first("viewId")


def explicit_retryable(message: str) -> bool | None:
    normalized = message.replace('\\"', '"')
    match = re.search(r'"retryable"\s*:\s*(true|false)', normalized, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower() == "true"


def extract_trace_ids(message: str) -> tuple[str, ...]:
    normalized = message.replace('\\"', '"')
    values = re.findall(r'"trace_id"\s*:\s*"([^"]+)"', normalized)
    return tuple(dict.fromkeys(values))


def classify_error(message: str) -> tuple[str, bool]:
    lower = message.lower()
    if any(marker in lower for marker in COMMAND_MARKERS):
        return "command_validation", False
    if any(marker in lower for marker in AUTH_MARKERS):
        return "authentication", False
    if any(marker in lower for marker in PERMISSION_MARKERS):
        return "permission", False
    if any(marker in lower for marker in NOT_FOUND_MARKERS):
        return "not_found", False
    retryable_flag = explicit_retryable(message)
    if retryable_flag is not None:
        return ("transient_service" if retryable_flag else "command"), retryable_flag
    retryable = any(marker in lower for marker in TRANSIENT_MARKERS)
    return ("transient_service" if retryable else "command"), retryable


def run_json_once(prefix: list[str], args: list[str]) -> Any:
    completed = subprocess.run(prefix + args + ["--format", "json"], capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or f"exit={completed.returncode}"
        category, retryable = classify_error(message)
        raise DwsCommandError(args, message, category, retryable, extract_trace_ids(message))
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise DwsCommandError(args, f"DWS 未返回有效 JSON：{error}", "invalid_json", False) from error


def run_json(prefix: list[str], args: list[str], retries: int = 2) -> Any:
    """Run once plus at most two transient retries (2s and 5s)."""
    delays = (2, 5)
    for attempt in range(retries + 1):
        try:
            return run_json_once(prefix, args)
        except DwsCommandError as error:
            if not error.retryable or attempt >= retries:
                raise
            time.sleep(delays[min(attempt, len(delays) - 1)])
    raise AssertionError("unreachable")


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


def records_from(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"].get("records", [])
    if isinstance(payload, dict):
        return payload.get("records", [])
    return []


def nested_value(payload: Any, keys: set[str]) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and value:
                return value
        for value in payload.values():
            found = nested_value(value, keys)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = nested_value(value, keys)
            if found:
                return found
    return None


def collect_values(payload: Any, key: str) -> set[str]:
    values: set[str] = set()
    if isinstance(payload, dict):
        for item_key, value in payload.items():
            if item_key == key and value:
                values.add(str(value))
            else:
                values.update(collect_values(value, key))
    elif isinstance(payload, list):
        for value in payload:
            values.update(collect_values(value, key))
    return values


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_fallback(prefix: list[str], args: argparse.Namespace, output: Path, primary_error: DwsCommandError) -> dict[str, Any]:
    scope = "view" if args.view_id else "table"
    export_args = [
        "aitable", "export", "data", "--base-id", args.base_id, "--scope", scope,
        "--table-id", args.table_id, "--export-format", "excel", "--timeout-ms", "30000",
    ]
    if args.view_id:
        export_args += ["--view-id", args.view_id]
    export_payload = run_json(prefix, export_args, retries=1)
    save_json(output / "export-result.json", export_payload)

    download_url = nested_value(export_payload, {"downloadUrl", "download_url", "url"})
    file_name = nested_value(export_payload, {"fileName", "file_name", "name"}) or "fallback-export.xlsx"
    download = {"available": bool(download_url), "path": None, "error": None}
    if download_url and not args.skip_export_download:
        target = output / Path(str(file_name)).name
        try:
            urllib.request.urlretrieve(str(download_url), target)
            download["path"] = target.name
        except Exception as error:  # keep degradation explicit; do not conceal download failures
            download["error"] = str(error)

    data_access_status = "retrieved_via_export" if download["path"] else ("export_ready" if download_url else "failed")
    manifest = {
        "base_id": args.base_id,
        "table_id": args.table_id,
        "view_id": args.view_id,
        "retrieval_status": "degraded_export",
        "data_access_status": data_access_status,
        "structured_api_status": "failed",
        "source_format": "official_excel_export",
        "record_count": None,
        "field_count": None,
        "complete_pagination": False,
        "record_id_fidelity": "missing",
        "record_id_coverage": 0.0,
        "record_link_coverage": 0.0,
        "original_record_drilldown": False,
        "degradation_requires_user_approval": True,
        "failure_scope": "structured_fields_records_and_original_links",
        "must_not_report_as": "data_retrieval_failed" if data_access_status != "failed" else None,
        "recommended_user_message": "数据已通过官方导出取得，但缺少真实 recordId 和钉钉原始记录链接。" if data_access_status != "failed" else "结构化读取和官方导出均失败。",
        "primary_failure": {
            "category": primary_error.category,
            "message": primary_error.message,
            "retryable": primary_error.retryable,
            "trace_ids": list(primary_error.trace_ids),
        },
        "export": download,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "runtime_dependency": "DWS CLI from PATH; no account router and no other skill required",
    }
    save_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="只读抓取钉钉 AI 表格字段、全量记录和真实明细链接")
    parser.add_argument("--url", help="钉钉 AI 表格 URL；自动解析 baseId、sheetId/tableId 和 viewId")
    parser.add_argument("--base-id")
    parser.add_argument("--table-id")
    parser.add_argument("--view-id")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--skip-record-links", action="store_true")
    parser.add_argument("--no-export-fallback", action="store_true")
    parser.add_argument("--skip-export-download", action="store_true")
    args = parser.parse_args()

    if args.url:
        url_base_id, url_table_id, url_view_id = parse_aitable_url(args.url)
        args.base_id = args.base_id or url_base_id
        args.table_id = args.table_id or url_table_id
        args.view_id = args.view_id or url_view_id
    if not args.base_id or not args.table_id:
        parser.error("必须提供 --url，或同时提供 --base-id 与 --table-id")

    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    prefix = command_prefix()

    try:
        auth = run_json(prefix, ["auth", "status"], retries=0)
    except DwsCommandError as error:
        raise SystemExit(str(error)) from error
    auth_data = auth.get("data", auth) if isinstance(auth, dict) else {}
    if not auth_data.get("authenticated") or not auth_data.get("token_valid"):
        raise SystemExit("DWS 当前未处于有效登录状态。请先完成登录，再重新运行。")

    base_access_verified = False
    try:
        table = run_json(prefix, ["aitable", "+base-get", "--base-id", args.base_id])
        base_access_verified = True
        catalog_table_ids = collect_values(table, "tableId")
        if catalog_table_ids and args.table_id not in catalog_table_ids:
            raise DwsCommandError(
                ["aitable", "+base-get"],
                f"目标 tableId={args.table_id} 不属于当前 Base；目录中的 tableId={sorted(catalog_table_ids)}",
                "not_found",
                False,
            )
        fields = run_json(prefix, ["aitable", "+field-get", "--base-id", args.base_id, "--table-id", args.table_id])
        field_rows = fields.get("data", {}).get("fields") or fields.get("fields") or []
        field_ids = [str(item["fieldId"]) for item in field_rows if item.get("fieldId")]
        if not field_ids:
            raise DwsCommandError(["aitable", "field", "get"], "目标表没有返回真实字段定义", "incomplete_data", False)

        merged: dict[str, dict[str, Any]] = {}
        observed_rows = 0
        missing_record_ids: set[int] = set()
        field_chunks = chunks(field_ids, 100)
        for chunk_index, field_chunk in enumerate(field_chunks):
            payload = run_json(prefix, [
                "aitable", "record", "query", "--base-id", args.base_id, "--table-id", args.table_id,
                "--limit", "100", "--all", "--page-limit", "0", "--field-ids", ",".join(field_chunk),
            ])
            chunk_records = records_from(payload)
            if chunk_index == 0:
                observed_rows = len(chunk_records)
            for row_index, record in enumerate(chunk_records):
                record_id = str(record.get("recordId") or "")
                if not record_id:
                    missing_record_ids.add(row_index)
                    continue
                current = merged.setdefault(record_id, {"recordId": record_id, "cells": {}})
                current["cells"].update(record.get("cells") or {})
    except DwsCommandError as error:
        if error.category == "permission" and base_access_verified:
            error.category = "interface_identity_mismatch"
        if args.no_export_fallback or error.category in {"authentication", "not_found"} or (error.category == "permission" and not base_access_verified):
            raise SystemExit(str(error)) from error
        try:
            manifest = export_fallback(prefix, args, output, error)
        except DwsCommandError as export_error:
            raise SystemExit(f"结构化读取失败，官方导出也失败。\n{error}\n{export_error}") from export_error
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return

    records = list(merged.values())
    denominator = max(observed_rows, len(records) + len(missing_record_ids))
    id_coverage = len(records) / denominator if denominator else 1.0
    records_payload = {
        "data": {"records": records, "hasMore": False},
        "retrieval": {"complete": True, "field_chunks": len(field_chunks)},
    }

    links_payload: dict[str, Any] = {"items": [], "total": 0}
    link_error: dict[str, str] | None = None
    if records and not args.skip_record_links:
        share_args = [
            "aitable", "+record-share-links", "--base", args.base_id, "--table", args.table_id,
            "--record-ids", ",".join(record["recordId"] for record in records),
        ]
        if args.view_id:
            share_args += ["--view-id", args.view_id]
        try:
            links_payload = run_json(prefix, share_args)
        except DwsCommandError as error:
            link_error = {"category": error.category, "message": error.message}

    link_items = links_payload.get("items") if isinstance(links_payload, dict) else []
    if not isinstance(link_items, list):
        link_items = []
    link_coverage = len(link_items) / len(records) if records else 1.0
    full_drilldown = id_coverage == 1.0 and link_coverage == 1.0
    manifest = {
        "base_id": args.base_id,
        "table_id": args.table_id,
        "view_id": args.view_id,
        "retrieval_status": "complete" if full_drilldown else "complete_without_original_record_links",
        "data_access_status": "complete",
        "structured_api_status": "complete",
        "source_format": "structured_api",
        "record_count": len(records),
        "field_count": len(field_rows),
        "complete_pagination": True,
        "record_id_fidelity": "real" if id_coverage == 1.0 else "missing",
        "record_id_coverage": round(id_coverage, 6),
        "record_link_coverage": round(link_coverage, 6),
        "original_record_drilldown": full_drilldown,
        "failure_scope": None if full_drilldown else "original_record_links_only",
        "recommended_user_message": "结构化数据和原始记录链接均已完整取得。" if full_drilldown else "结构化数据已完整取得，但部分钉钉原始记录链接不可用。",
        "degradation_requires_user_approval": not full_drilldown,
        "record_link_failure": link_error,
        "account": {"user_name": auth_data.get("user_name"), "corp_name": auth_data.get("corp_name"), "user_id": auth_data.get("user_id")},
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "runtime_dependency": "DWS CLI from PATH; no account router and no other skill required",
    }

    for name, payload in {
        "auth.json": auth,
        "table.json": table,
        "fields.json": fields,
        "records.json": records_payload,
        "record-links.json": links_payload,
        "manifest.json": manifest,
    }.items():
        save_json(output / name, payload)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
