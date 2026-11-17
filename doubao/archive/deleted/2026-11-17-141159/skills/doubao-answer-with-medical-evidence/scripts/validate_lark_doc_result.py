#!/usr/bin/env python3
"""Validate lark-doc create, update, and fetch results for a full report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def unwrap_runner(payload: Any, problems: list[str]) -> Any:
    if not isinstance(payload, dict) or "ok" in payload or not isinstance(payload.get("stdout"), str):
        return payload
    if payload.get("interrupted") is True:
        problems.append("运行器返回 interrupted=true")
    stderr = payload.get("stderr")
    if isinstance(stderr, str) and stderr.strip():
        problems.append(f"运行器 stderr 不为空：{stderr.strip()}")
    try:
        return json.loads(payload["stdout"])
    except json.JSONDecodeError as exc:
        problems.append(f"运行器 stdout 不是有效 JSON：{exc}")
        return payload


def collect_nonempty_warnings(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key.lower() in {"warning", "warnings"}:
                if isinstance(item, list):
                    found.extend(f"{child_path}: {warning}" for warning in item if str(warning).strip())
                elif item is not None and item is not False and item != "" and str(item).strip():
                    found.append(f"{child_path}: {item}")
            found.extend(collect_nonempty_warnings(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(collect_nonempty_warnings(item, f"{path}[{index}]"))
    return found


def collect_failure_states(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            lowered = key.lower()
            if lowered in {"result", "status", "state"} and isinstance(item, str):
                normalized = re.sub(r"[\s-]+", "_", item.strip().lower())
                if normalized in {"failed", "failure", "error", "partial_success", "partial"}:
                    found.append(f"{child_path}={item}")
            if lowered in {"ok", "success"} and item is False:
                found.append(f"{child_path}=false")
            if lowered in {"partial", "partial_success"} and item is True:
                found.append(f"{child_path}=true")
            if (
                lowered in {"error", "errors", "error_msg", "errormsg", "error_message"}
                and item is not None
                and item is not False
                and item != ""
            ):
                found.append(f"{child_path}={item}")
            found.extend(collect_failure_states(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(collect_failure_states(item, f"{path}[{index}]"))
    return found


def validate_result(
    payload: Any,
    operation: str,
    scope: str,
    expected: list[str],
    expected_document_id: str | None = None,
) -> list[str]:
    problems: list[str] = []
    payload = unwrap_runner(payload, problems)
    if not isinstance(payload, dict):
        return problems + ["lark-doc 返回内容必须是 JSON 对象"]

    if payload.get("ok") is not True:
        problems.append(f"顶层 ok 必须为 true，当前为 {payload.get('ok')!r}")

    warnings = collect_nonempty_warnings(payload)
    if warnings:
        problems.append("warnings 必须为空：" + " | ".join(warnings))
    failures = collect_failure_states(payload)
    if failures:
        problems.append("返回值包含失败或 partial success 状态：" + " | ".join(failures))

    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    result = data.get("result")
    if result is not None and result != "success":
        problems.append(f"存在 data.result 时必须为 success，当前为 {result!r}")
    document = data.get("document") if isinstance(data.get("document"), dict) else {}

    permission_present = "permission_grant" in data or "permission_grant" in document
    if permission_present:
        permission = data.get("permission_grant") if "permission_grant" in data else document.get("permission_grant")
        if not isinstance(permission, dict):
            problems.append("permission_grant 存在时必须是对象，并明确返回 status=granted")
        elif permission.get("status") != "granted":
            problems.append(f"permission_grant.status 必须为 granted，当前为 {permission.get('status')!r}")

    if operation == "create":
        if not document.get("document_id"):
            problems.append("create 必须返回 data.document.document_id")
        url = document.get("url")
        if not isinstance(url, str) or not re.match(r"https?://", url):
            problems.append("create 必须返回带 http(s) 协议的 data.document.url")

    elif operation == "update":
        if result != "success":
            problems.append(f"update 必须返回 data.result=success，当前为 {result!r}")
        count = data.get("updated_blocks_count")
        if not isinstance(count, (int, float)) or isinstance(count, bool) or count <= 0:
            problems.append(f"update 必须返回 updated_blocks_count > 0，当前为 {count!r}")

    elif operation == "fetch":
        content = document.get("content")
        if not isinstance(content, str) or not content.strip():
            problems.append("fetch 必须返回非空 data.document.content")
            content = ""
        for item in expected:
            if item not in content:
                problems.append(f"fetch 回读缺少预期内容：{item}")
        if scope == "full":
            if not expected_document_id:
                problems.append("scope=full 时必须提供 create 返回的 --expected-document-id")
            elif document.get("document_id") != expected_document_id:
                problems.append(
                    "fetch document_id 与本次 create 返回值不一致："
                    f"{document.get('document_id')!r} != {expected_document_id!r}"
                )
            if not any(isinstance(item, str) and item.strip() for item in expected):
                problems.append("scope=full 时必须提供能确认文档完整的 --expect 内容锚点")
            for flag in ("truncated", "is_truncated", "has_more"):
                if document.get(flag) is True:
                    problems.append(f"scope=full 回读未返回完整正文：{flag}=true")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", choices=("create", "update", "fetch"), required=True)
    parser.add_argument("--scope", choices=("full", "outline"), default="full")
    parser.add_argument("--expect", action="append", default=[], help="required text in full fetch content")
    parser.add_argument(
        "--expected-document-id",
        help="document_id returned by the matching create call; required for a full fetch",
    )
    parser.add_argument("path", help="result JSON path, or - for stdin")
    args = parser.parse_args()

    if args.operation != "fetch" and args.scope != "full":
        parser.error("--scope 只适用于 fetch")

    try:
        raw = sys.stdin.read() if args.path == "-" else Path(args.path).read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"飞书返回值读取失败：{exc}", file=sys.stderr)
        return 2

    problems = validate_result(
        payload,
        args.operation,
        args.scope,
        args.expect,
        args.expected_document_id,
    )
    if problems:
        print("飞书文档操作未通过交付校验：", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "valid": True,
                "operation": args.operation,
                "scope": args.scope if args.operation == "fetch" else None,
                "expected_items_checked": len(args.expect),
                "warnings": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
