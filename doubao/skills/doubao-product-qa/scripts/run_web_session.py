#!/usr/bin/env python3
"""确定性编排本地 Web 服务、readiness、Playwright/项目 runner、证据和清理。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qa_run_common import coverage_snapshot, semantic_findings
from platform_process import prepare_command, process_group_options, stop_process_tree


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("配置根节点必须是对象")
    if not payload.get("base_url"):
        raise ValueError("缺少 base_url")
    for field in ("start_command", "test_command"):
        value = payload.get(field)
        if value is not None and (not isinstance(value, list) or not value or not all(isinstance(arg, str) and arg for arg in value)):
            raise ValueError(f"{field} 必须是非空字符串数组")
    return payload


def readiness(url: str, expected: set[int], timeout: float = 3.0) -> tuple[bool, int | None, str | None]:
    try:
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "qa-product-testing/1"})
        hostname = urllib.parse.urlparse(url).hostname
        opener = (
            urllib.request.build_opener(urllib.request.ProxyHandler({}))
            if hostname in {"127.0.0.1", "localhost", "::1"}
            else urllib.request.build_opener()
        )
        with opener.open(request, timeout=timeout) as response:
            return response.status in expected, response.status, None
    except urllib.error.HTTPError as exc:
        return exc.code in expected, exc.code, str(exc)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, None, str(exc)


def stop_process(process: subprocess.Popen[bytes] | None, system: str | None = None) -> dict[str, Any]:
    return stop_process_tree(process, system)


def update_qa_run(path: Path, config: dict[str, Any], result: dict[str, Any], out: Path) -> None:
    run = json.loads(path.read_text(encoding="utf-8"))
    case_id = config.get("case_id")
    if not case_id:
        return
    execution_id_base = str(config.get("execution_id") or f"EXE-WEB-{int(time.time())}")
    existing_execution_ids = {str(item.get("id", "")) for item in run.get("executions", [])}
    execution_id = execution_id_base
    attempt = 1
    while execution_id in existing_execution_ids:
        attempt += 1
        execution_id = f"{execution_id_base}-A{attempt}"
    runner_kind = str(config.get("runner_kind", "playwright")).lower()
    execution_level = "full_automation" if runner_kind == "playwright" and result["status"] in {"passed", "failed"} else "partial_validation"
    validation_scope = "formal" if execution_level == "full_automation" else "exploratory"
    evidence_level = "L3_reproducible" if validation_scope == "formal" else "L2_observation"
    evidence_prefix = execution_id.replace("EXE-", "EVD-", 1)
    evidence_items = [
        {"id": f"{evidence_prefix}-STDOUT", "type": "log", "path": os.path.relpath(out / "test-stdout.log", path.parent), "description": "Web runner stdout", "level": evidence_level, "validation_scope": validation_scope},
        {"id": f"{evidence_prefix}-STDERR", "type": "log", "path": os.path.relpath(out / "test-stderr.log", path.parent), "description": "Web runner stderr", "level": evidence_level, "validation_scope": validation_scope},
        {"id": f"{evidence_prefix}-SUMMARY", "type": "log", "path": os.path.relpath(out / "web-session-summary.json", path.parent), "description": "Web session lifecycle summary", "level": evidence_level, "validation_scope": validation_scope},
    ]
    evidence_ids = [item["id"] for item in evidence_items]
    before_evidence = len(run.get("evidence", []))
    before_executions = len(run.get("executions", []))
    run.setdefault("evidence", []).extend(evidence_items)
    execution = {
        "id": execution_id,
        "case_id": case_id,
        "status": result["status"],
        "execution_level": execution_level,
        "validation_scope": validation_scope,
        "execution_method": "automated",
        "selected_path": f"web-session/{runner_kind}",
        "summary": result["message"],
        "assertions": {"readiness": result["readiness"]["ok"], "runner_exit_code": result.get("runner_exit_code")},
        "evidence_ids": evidence_ids,
        "attempt": attempt,
    }
    run.setdefault("executions", []).append(execution)
    run["revision"] = int(run.get("revision", 1)) + 1
    revision = run["revision"]
    ledger = run.setdefault("change_ledger", [])
    change_numbers = [
        int(str(item.get("id", ""))[4:])
        for item in ledger
        if str(item.get("id", "")).startswith("CHG-")
        and str(item.get("id", ""))[4:].isdigit()
    ]

    def add_change(object_type: str, before: int, added_ids: list[str], number: int) -> None:
        ledger.append({
            "id": f"CHG-{number:03d}",
            "revision": revision,
            "action": "ADD",
            "object_type": object_type,
            "added_ids": added_ids,
            "removed_ids": [],
            "modified_ids": [],
            "before_count": before,
            "after_count": before + len(added_ids),
            "delta_count": len(added_ids),
            "source": "run_web_session.py",
            "summary": f"追加 Web {object_type} 记录",
        })

    next_number = max(change_numbers, default=0) + 1
    add_change("evidence", before_evidence, evidence_ids, next_number)
    add_change("execution", before_executions, [execution_id], next_number + 1)
    manifest = run.setdefault("delivery_manifest", {"source_revision": revision, "outputs": []})
    manifest["source_revision"] = revision
    for output in manifest.get("outputs", []):
        if output.get("status") not in {"failed", "local_fallback"}:
            output["status"] = "stale"
            output["validated"] = False
    run["release_decision"] = {
        "decision": "undetermined",
        "rationale": "Web 执行已追加；需要重新完成证据归因和发布门禁。",
        "conditions": [],
    }
    run["coverage"] = coverage_snapshot(run)
    run["execution_level"] = execution_level
    findings = semantic_findings(run, path.parent)
    errors = [item for item in findings if item["level"] == "error"]
    if errors:
        raise ValueError(json.dumps(errors, ensure_ascii=False))
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行本地 Web session 并只清理本次启动的服务")
    parser.add_argument("config", type=Path, help="JSON 配置")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--qa-run", type=Path, help="可选 qa-run.json；配置需包含 case_id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.expanduser().resolve()
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    try:
        config = load_config(config_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 2

    project_dir = Path(config.get("project_dir") or config_path.parent).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"项目目录不存在：{project_dir}", file=sys.stderr)
        return 2
    readiness_url = str(config.get("readiness_url") or config["base_url"])
    expected = {int(value) for value in config.get("readiness_statuses", [200])}
    wait_seconds = float(config.get("readiness_timeout_seconds", 60))
    env = os.environ.copy()
    for key, value in config.get("env", {}).items():
        env[str(key)] = str(value)
    env.update({"QA_BASE_URL": str(config["base_url"]), "QA_ARTIFACT_DIR": str(out)})
    no_proxy = {value.strip() for value in str(env.get("NO_PROXY") or env.get("no_proxy") or "").split(",") if value.strip()}
    no_proxy.update({"127.0.0.1", "localhost", "::1"})
    env["NO_PROXY"] = ",".join(sorted(no_proxy))
    env["no_proxy"] = env["NO_PROXY"]
    storage_state = config.get("storage_state")
    if storage_state:
        storage_path = (project_dir / str(storage_state)).resolve()
        if not storage_path.is_file():
            print(f"storage_state 不存在：{storage_path}", file=sys.stderr)
            return 2
        env["QA_STORAGE_STATE"] = str(storage_path)
    env.setdefault("PLAYWRIGHT_JSON_OUTPUT_NAME", str(out / "playwright-results.json"))
    env.setdefault("PLAYWRIGHT_HTML_OUTPUT_DIR", str(out / "playwright-report"))

    service_process: subprocess.Popen[bytes] | None = None
    service_stdout = (out / "service-stdout.log").open("wb")
    service_stderr = (out / "service-stderr.log").open("wb")
    cleanup: dict[str, Any] = {"started_by_runner": False, "stopped": False}
    result: dict[str, Any]
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        ready, status_code, ready_error = readiness(readiness_url, expected)
        reused = ready
        if not ready:
            start_command = config.get("start_command")
            if not start_command:
                result = {
                    "schema_version": 1, "status": "blocked", "message": "服务未就绪且未提供 start_command",
                    "readiness": {"ok": False, "url": readiness_url, "status_code": status_code, "error": ready_error},
                    "service_reused": False, "runner_exit_code": None, "started_at": started_at,
                }
                return_code = 3
            else:
                service_process = subprocess.Popen(
                    prepare_command(start_command),
                    cwd=str(project_dir),
                    env=env,
                    stdout=service_stdout,
                    stderr=service_stderr,
                    shell=False,
                    **process_group_options(),
                )
                deadline = time.monotonic() + wait_seconds
                while time.monotonic() < deadline:
                    if service_process.poll() is not None:
                        break
                    ready, status_code, ready_error = readiness(readiness_url, expected)
                    if ready:
                        break
                    time.sleep(0.5)
                if not ready:
                    result = {
                        "schema_version": 1, "status": "blocked", "message": "服务未在期限内就绪",
                        "readiness": {"ok": False, "url": readiness_url, "status_code": status_code, "error": ready_error},
                        "service_reused": False, "runner_exit_code": None, "started_at": started_at,
                    }
                    return_code = 3
        if ready:
            test_command = config.get("test_command")
            if not test_command:
                result = {
                    "schema_version": 1, "status": "blocked", "message": "页面已就绪，但未提供标准 test_command；结构化 Agent 浏览器应走 Skill 探索路径",
                    "readiness": {"ok": True, "url": readiness_url, "status_code": status_code, "error": None},
                    "service_reused": reused, "runner_exit_code": None, "started_at": started_at,
                }
                return_code = 3
            else:
                with (out / "test-stdout.log").open("wb") as stdout, (out / "test-stderr.log").open("wb") as stderr:
                    completed = subprocess.run(
                        prepare_command(test_command),
                        cwd=str(project_dir),
                        env=env,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=int(config.get("test_timeout_seconds", 1800)),
                        check=False,
                    )
                passed = completed.returncode in {int(value) for value in config.get("expected_exit_codes", [0])}
                result = {
                    "schema_version": 1, "status": "passed" if passed else "failed",
                    "message": "Web runner 执行通过" if passed else "Web runner 执行失败",
                    "readiness": {"ok": True, "url": readiness_url, "status_code": status_code, "error": None},
                    "service_reused": reused, "runner_exit_code": completed.returncode, "started_at": started_at,
                }
                return_code = 0 if passed else 1
    except subprocess.TimeoutExpired:
        result = {
            "schema_version": 1, "status": "blocked", "message": "Web runner 超时",
            "readiness": {"ok": True, "url": readiness_url}, "service_reused": False,
            "runner_exit_code": None, "started_at": started_at,
        }
        return_code = 3
    finally:
        cleanup = stop_process(service_process)
        service_stdout.close()
        service_stderr.close()

    result["cleanup"] = cleanup
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    summary_path = out / "web-session-summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not (out / "test-stdout.log").exists():
        (out / "test-stdout.log").write_text("", encoding="utf-8")
    if not (out / "test-stderr.log").exists():
        (out / "test-stderr.log").write_text("", encoding="utf-8")
    if args.qa_run:
        try:
            update_qa_run(args.qa_run.expanduser().resolve(), config, result, out)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Web 结果写入 qa-run 失败：{exc}", file=sys.stderr)
            return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return return_code


if __name__ == "__main__":
    sys.exit(main())
