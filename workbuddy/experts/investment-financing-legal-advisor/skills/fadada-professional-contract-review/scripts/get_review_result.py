#!/usr/bin/env python3
"""
获取审查结果脚本

查询审查进度和结果状态。支持两种模式：
  单发模式: python get_review_result.py <recordId>
  阻塞等待: python get_review_result.py <recordId> --wait [--interval 10] [--max-wait 570]

--wait 模式在脚本内部以退避间隔（interval -> 2x -> 30s 封顶）自动轮询，
直到 COMPLETED / FAILED 或 max-wait 超时，调用方只需一次 Bash 调用。

输出约定（两种模式一致）：
  非终态: stdout 单行紧凑 JSON {"success": true, "reviewStatus": "PROCESSING"}
  终态:   完整 API 返回体写入 <系统临时目录>/review_result_<recordId>.json，
          stdout 只输出摘要（状态、resultFile 路径、等待秒数、轮询次数）
  进度行写 stderr，不污染 stdout。

环境变量:
  RICHEEAI_TOKEN    - 认证 Token（由 RicheeAI 自动注入）
  RICHEEAI_API_BASE - API 基础域名（由 RicheeAI 自动注入）
  HTTP_PROXY / HTTPS_PROXY - 代理设置（可选）
"""

import argparse
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proxy_utils import get_auth_token, get_api_base_url, make_json_request

TERMINAL_STATUSES = ("COMPLETED", "FAILED")
MAX_INTERVAL = 30
MAX_CONSECUTIVE_FAILURES = 3


def query_once(record_id: str) -> dict:
    """单次查询审查结果"""
    token = get_auth_token()
    if not token:
        return {"success": False, "error": "未找到认证 Token"}

    base_url = get_api_base_url()
    endpoint = "/claw/contract/getReviewResult"
    params = {"recordId": record_id}
    url = f"{base_url}{endpoint}?{urllib.parse.urlencode(params)}"

    headers = {
        "richee-token": token,
        "User-Agent": "Mozilla/5.0 RicheeAI/1.0",
        "Accept": "application/json",
    }

    return make_json_request(url, headers, method="GET", timeout=60)


def extract_status(result: dict):
    """从 API 返回中提取审查状态；无法识别时返回 None"""
    data = result.get("data")
    if isinstance(data, dict):
        status = data.get("reviewStatus") or data.get("status")
        if isinstance(status, str) and status:
            return status
    elif isinstance(data, str) and data:
        return data
    return None


def save_result_file(record_id: str, result: dict) -> str:
    """完整返回体落盘，返回文件路径（跨平台临时目录，Windows 上为 %TEMP%）"""
    from skill_paths import work_root

    path = str(work_root() / f"review_result_{record_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return path


def emit_terminal(record_id: str, result: dict, status, waited: int, polls: int):
    """终态（或未知状态）输出：落盘 + stdout 摘要"""
    result_file = save_result_file(record_id, result)
    summary = {
        "success": True,
        "reviewStatus": status or "UNKNOWN",
        "recordId": record_id,
        "resultFile": result_file,
        "waited": waited,
        "polls": polls,
    }
    if status is None:
        summary["warning"] = "无法从返回体识别 reviewStatus，完整返回见 resultFile"
    print(json.dumps(summary, ensure_ascii=False))


def run(record_id: str, wait: bool, interval: int, max_wait: int):
    start = time.monotonic()
    polls = 0
    consecutive_failures = 0
    current_interval = interval

    while True:
        result = query_once(record_id)
        polls += 1
        elapsed = int(time.monotonic() - start)

        if not result.get("success"):
            # 等待模式下瞬时网络抖动不中断整个轮询，连续失败才退出
            consecutive_failures += 1
            if not wait or consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(json.dumps(result, ensure_ascii=False))
                sys.exit(1)
            print(f"[poll #{polls}] 请求失败({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): "
                  f"{result.get('error')}", file=sys.stderr)
        else:
            consecutive_failures = 0
            status = extract_status(result)

            if status in TERMINAL_STATUSES or status is None:
                emit_terminal(record_id, result, status, elapsed, polls)
                return

            if not wait:
                print(json.dumps({"success": True, "reviewStatus": status},
                                 ensure_ascii=False))
                return

            print(f"[poll #{polls}] reviewStatus={status} elapsed={elapsed}s",
                  file=sys.stderr)

        if elapsed + current_interval > max_wait:
            print(json.dumps({
                "success": True,
                "reviewStatus": "PROCESSING",
                "recordId": record_id,
                "waited": elapsed,
                "polls": polls,
                "timedOut": True,
            }, ensure_ascii=False))
            return

        time.sleep(current_interval)
        current_interval = min(current_interval * 2, MAX_INTERVAL)


def main():
    parser = argparse.ArgumentParser(description="获取合同审查结果")
    parser.add_argument("record_id", help="审查记录ID")
    parser.add_argument("--wait", action="store_true",
                        help="阻塞等待直到 COMPLETED/FAILED 或超时")
    parser.add_argument("--interval", type=int, default=10,
                        help="起始轮询间隔秒数（默认 10，退避至 30 封顶）")
    parser.add_argument("--max-wait", type=int, default=570,
                        help="最长等待秒数（默认 570，留余量给调用方 600s 超时）")
    args = parser.parse_args()

    record_id = args.record_id.strip()
    if not record_id:
        print(json.dumps({"success": False, "error": "recordId 不能为空"}, ensure_ascii=False))
        sys.exit(1)
    if args.interval < 1:
        print(json.dumps({"success": False, "error": "interval 必须 >= 1"}, ensure_ascii=False))
        sys.exit(1)

    run(record_id, args.wait, args.interval, args.max_wait)


if __name__ == "__main__":
    main()
