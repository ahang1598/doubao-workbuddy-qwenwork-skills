#!/usr/bin/env python3
"""商品库-Listing详情 - LinkFox Skill
调用 /product-center/v1/skill/product/listing/{listingId} 接口。

占位符（被 scaffold_skill.py 或手工替换）：
  商品库-Listing详情  中文一句话标题      /product-center/v1/skill/product/listing/{listingId}  网关端点路径
  linkfox-product-center-listing-detail      skill 标识(=目录名)  product_center_listing_detail.py   本脚本文件名

Usage:
  python product_center_listing_detail.py '<JSON parameters>'           # 强制落盘，输出路径+摘要
"""

import json
import os
import re
import sys
import time
from urllib.parse import quote, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

API_PATH = "/product-center/v1/skill/product/listing/{listingId}"
SLUG = "linkfox-product-center-listing-detail"


# API_PATH 中的 {xxx} 占位符；脚本运行时从 params 取同名字段做 URL 替换。
PATH_PLACEHOLDERS = re.compile(r"\{(\w+)\}")


def _paths():
    """通过 ../../_shared 导入共享 linkfox_paths。"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
    import linkfox_paths
    return linkfox_paths


def get_api_key():
    key = os.environ.get("LINKFOX_AGENT_API_KEY")
    if not key:
        print(
            "API Key not configured. Please complete authorization first:\n"
            "1. Visit https://agent.linkfox.com → 设置 → API KEY to obtain your Key\n"
            "2. Set the environment variable: export LINKFOX_AGENT_API_KEY=your-key-here",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _build_url(params):
    """把 API_PATH 里的 {xxx} 占位符按同名字段替换到路径，剩余字段拍 query string。"""
    used = set()

    def repl(m):
        name = m.group(1)
        used.add(name)
        if params is None or params.get(name) in (None, ""):
            print(f"Path variable '{name}' is required in params", file=sys.stderr)
            sys.exit(1)
        return quote(str(params[name]), safe="")

    api_path_filled = PATH_PLACEHOLDERS.sub(repl, API_PATH)
    url = _paths().get_api_base() + api_path_filled

    if params is None:
        params = {}
    if not params.get("agentSessionId"):
        env_session_id = os.environ.get("SESSION_ID", "").strip()
        if env_session_id:
            params = {**params, "agentSessionId": env_session_id}

    # 剩余字段（非 path variable、非空）走 query string
    if params:
        remaining = [(k, v) for k, v in params.items()
                     if k not in used and v is not None and v != ""]
        if remaining:
            url = f"{url}?{urlencode(remaining, doseq=True)}"
    return url


def validate(params):
    errs = []
    if params.get("offerSource") in (None, ""):
        errs.append("offerSource 必填(调用方按自身角色硬编码:10/11/12/13/14/15)")
    if params.get("listingId") in (None, ""):
        errs.append("listingId 必填")
    if errs:
        print("参数校验失败:\n- " + "\n- ".join(errs), file=sys.stderr)
        sys.exit(1)


def call_api(params):
    """原接口为 GET + @PathVariable；脚本内部按占位符填路径，余下字段走 query。"""
    req = Request(
        _build_url(params),
        headers={
            "Authorization": get_api_key(),  # 值即 key 本身，不带 Bearer
            "User-Agent": "LinkFox-Skill/2.0",
            "SESSION_ID": os.environ.get("SESSION_ID", ""),
        "MESSAGE_ID": os.environ.get("MESSAGE_ID", ""),
        "MODE_ID": os.environ.get("MODE_ID", ""),
        "APP_NAME": os.environ.get("APP_NAME", ""),
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(body) if body else {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception:
            return {"error": f"HTTP {e.code}: {e.reason}", "details": body}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}


def _find_main_list(obj):
    """递归找到元素数最多的 list 字段。不写死字段名，适配任意结构。"""
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
    """打印紧凑摘要：顶层字段 + 常见计数 + 最大列表前 3 条。"""
    if not isinstance(result, dict):
        print(f"Response type: {type(result).__name__}")
        print(json.dumps(result, ensure_ascii=False)[:500])
        return

    print(f"Top-level keys: {list(result.keys())}")

    for k in ("errcode", "errorCode", "code", "errmsg", "msg",
              "total", "totalCount", "count", "currentPage", "perPage",
              "costToken", "costTime", "success"):
        if k in result and isinstance(result[k], (int, float, bool, str)):
            print(f"  {k}: {result[k]}")

    list_path, main_list = _find_main_list(result)
    if list_path is not None and main_list:
        sample = main_list[:3]
        print(f"\nMain list field: `{list_path}` (length={len(main_list)})")
        print(f"Sample (first {len(sample)} of {len(main_list)}):")
        print(json.dumps(sample, indent=2, ensure_ascii=False))


def _resolve_output_path(ts):
    """落到 <cwd>/linkfox/<date>/<session>/data/<slug>-<ts>.json。"""
    return _paths().resolve_data_path(SLUG, ts)


def main():
    argv = sys.argv[1:]
    if not argv:
        print(f"Usage: {os.path.basename(__file__)} '<JSON parameters>'", file=sys.stderr)
        sys.exit(1)

    try:
        params = json.loads(argv[0])
    except json.JSONDecodeError as e:
        print(f"Invalid parameter format: {e}", file=sys.stderr)
        sys.exit(1)

    validate(params)
    result = call_api(params)

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    ts = int(time.time())
    out_path = _resolve_output_path(ts)
    try:
        with open(out_path, "w") as f:
            f.write(serialized)
        print(f"Saved full response: {out_path} ({len(serialized)} bytes)")
    except OSError as e:
        print(f"Failed to save to {out_path}: {e}", file=sys.stderr)

    summarize(result)


if __name__ == "__main__":
    main()
