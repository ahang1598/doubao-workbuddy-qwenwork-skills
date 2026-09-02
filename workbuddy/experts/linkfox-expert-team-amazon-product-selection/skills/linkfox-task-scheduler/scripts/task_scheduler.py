#!/usr/bin/env python3
"""
LinkFox 定时任务管理 - LinkFox Skill
统一调用定时任务的五个接口：create / update / update-status / delete / list。

Usage:
  python task_scheduler.py <action> '<JSON parameters>'           # 自动：小结果全量；大结果写文件+摘要
  python task_scheduler.py <action> '<JSON parameters>' --inline  # 强制全量打印到 stdout

  <action> ∈ create | update | update-status | delete | list

输出策略（脚本默认行为）：
  - **始终**将完整响应写入 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/linkfox-task-scheduler-<timestamp>.json`（`<session>` 取自环境变量 `SESSION_ID`；**禁止写入 /tmp**，当前目录不可写则报错）
  - 响应体 ≤ 8 KB：落盘后把完整 JSON 打印到 stdout
  - 响应体 > 8 KB：落盘后 stdout 只输出摘要（顶层字段、常见计数如 `total`/`costToken`、最大列表字段的长度 + 前 3 条样本）
  - 加 `--inline` 强制全量打印到 stdout（同样落盘）
  - `delete` 接口后端无返回体，脚本会输出操作成功提示

环境变量：
  - LINKFOX_AGENT_API_KEY  : 必填，作为 Authorization 头
  - LINKFOX_TOOL_GATEWAY  : 可选，覆盖默认 base url（默认 https://tool-gateway.linkfox.com）
"""

import json
import os
import sys
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


SLUG = "linkfox-task-scheduler"

# action -> 端点路径
ACTIONS = {
    "create": "/task/add4api",
    "update": "/task/update4api",
    "update-status": "/task/updateStatus4api",
    "delete": "/task/delete4api",
    "list": "/task/list4api",
}

# 客户端合成 action（不直接对应 API 端点，需预处理后转为 ACTIONS 中的操作）
SYNTHETIC_ACTIONS = {"remind"}

# 响应小于等于该字节数时，直接全量输出，不落文件
SMALL_THRESHOLD = 8000


def base_url():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
    from linkfox_paths import get_api_base
    return get_api_base()


def get_api_key():
    key = os.environ.get("LINKFOX_AGENT_API_KEY")
    if not key:
        print(
            "API Key not configured. Please complete authorization first:\n"
            "1. Visit https://skill.linkfox.com/linkfoxskills/guide.htm to obtain your Key\n"
            "2. Set the environment variable: export LINKFOX_AGENT_API_KEY=your-key-here",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def preprocess_remind(params):
    """把 remind 参数转成 create 参数，在客户端计算目标时刻。"""
    from datetime import datetime, timedelta

    delay_minutes = float(params.get("delayMinutes", 0))
    delay_hours = float(params.get("delayHours", 0))
    total_minutes = delay_minutes + delay_hours * 60

    if total_minutes <= 0:
        print(
            "remind action requires delayMinutes > 0 or delayHours > 0",
            file=sys.stderr,
        )
        sys.exit(1)

    message = params.get("message", "提醒时间到！")
    title = params.get("title", "定时提醒")
    feishu_webhook = params.get("feishuWebhook") or params.get("webhookUrl")

    now = datetime.now()
    target = now + timedelta(minutes=total_minutes)
    exec_point = target.strftime("%Y-%m-%d")
    exec_time = target.strftime("%H:%M")

    create_params = {
        "title": title,
        "promptContent": message,
        "taskStatus": True,
        "execType": 4,
        "execPoint": exec_point,
        "execTime": exec_time,
    }

    if not feishu_webhook:
        print(
            "remind action requires feishuWebhook or webhookUrl "
            "(noticeList is required; provide a Feishu bot webhook address)",
            file=sys.stderr,
        )
        sys.exit(1)

    create_params["noticeList"] = [
        {"noticeType": 3, "address": feishu_webhook, "sign": ""}
    ]

    return "create", create_params


def call_api(action, params):
    api_key = get_api_key()
    url = base_url() + ACTIONS[action]
    data = json.dumps(params).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
            "User-Agent": "LinkFox-Skill/2.0",
            "SESSION_ID": os.environ.get("SESSION_ID", ""),
            "MESSAGE_ID": os.environ.get("MESSAGE_ID", ""),
            "MODE_ID": os.environ.get("MODE_ID", ""),
        "APP_NAME": os.environ.get("APP_NAME", ""),
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=120) as response:
            body = response.read().decode("utf-8")
            if not body.strip():
                # delete 等接口可能无返回体
                return {"_empty": True}
            return json.loads(body)
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(body) if body else {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception:
            return {"error": f"HTTP {e.code}: {e.reason}", "details": body}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}


def _find_main_list(obj):
    """递归找到元素数最多的 list 字段。不写死字段名，适配任何结构。"""
    best = (None, None, -1)

    def walk(node, path):
        nonlocal best
        if isinstance(node, list):
            if len(node) > best[2]:
                best = (path, node, len(node))
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)

    walk(obj, "")
    return best[0], best[1]


def summarize(result):
    """打印紧凑摘要。"""
    if not isinstance(result, dict):
        print(f"Response type: {type(result).__name__}")
        print(json.dumps(result, ensure_ascii=False)[:500])
        return

    print(f"Top-level keys: {list(result.keys())}")

    for k in ("errcode", "errorCode", "code", "errmsg", "errorMsg", "msg",
              "total", "totalCount", "count", "pageNum", "currentPage",
              "pageSize", "perPage", "pages", "costToken", "costTime", "success"):
        if k in result:
            v = result[k]
            if isinstance(v, (int, float, bool, str)):
                print(f"  {k}: {v}")

    list_path, main_list = _find_main_list(result)
    if list_path is not None and main_list:
        print(f"\nMain list field: `{list_path}` (length={len(main_list)})")
        sample = main_list[:3]
        print(f"Sample (first {len(sample)} of {len(main_list)}):")
        print(json.dumps(sample, indent=2, ensure_ascii=False))


def _resolve_output_path(ts):
    """落到 <cwd>/linkfox/<日期>/<session>/data/<slug>-<ts>.json，按 SESSION_ID 聚合到同一会话。"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
    from linkfox_paths import resolve_data_path
    return resolve_data_path(SLUG, ts)


def main():
    argv = sys.argv[1:]
    inline = False
    if "--inline" in argv:
        inline = True
        argv = [a for a in argv if a != "--inline"]

    if len(argv) < 2:
        print(
            "Usage: task_scheduler.py <action> '<JSON parameters>' [--inline]\n"
            f"  <action> ∈ {' | '.join(ACTIONS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    action = argv[0].strip().lower()
    all_valid = set(ACTIONS) | SYNTHETIC_ACTIONS
    if action not in all_valid:
        print(
            f"Unknown action '{action}'. Valid: {', '.join(sorted(all_valid))}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        params = json.loads(argv[1])
    except json.JSONDecodeError as e:
        print(f"Invalid parameter format: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(params, dict):
        print("Parameters must be a JSON object.", file=sys.stderr)
        sys.exit(1)

    # memberId 由后端从 token 注入，调用方传了也会被覆盖；这里主动剔除避免误导。
    params.pop("memberId", None)

    # 合成 action 预处理：转换为底层 API action + 参数
    if action == "remind":
        action, params = preprocess_remind(params)

    # templateId 是 add4api 的非必填来源追溯字段，调用方不需要传入
    if action == "create":
        params.pop("templateId", None)

    result = call_api(action, params)

    # delete 等无返回体的成功响应
    if isinstance(result, dict) and result.get("_empty"):
        print(f"OK: {action} succeeded (no response body).")
        return

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    ts = int(time.time())
    out_path = _resolve_output_path(ts)
    try:
        with open(out_path, "w") as f:
            f.write(serialized)
        print(f"Saved full response: {out_path} ({len(serialized)} bytes)")
    except OSError as e:
        print(f"Failed to save to {out_path}: {e}", file=sys.stderr)

    if inline or len(serialized.encode("utf-8")) <= SMALL_THRESHOLD:
        print(serialized)
    else:
        summarize(result)


if __name__ == "__main__":
    main()
