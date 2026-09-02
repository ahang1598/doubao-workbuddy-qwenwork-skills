#!/usr/bin/env python3
"""商品库-创建变体 - LinkFox Skill
调用 /product-center/v1/skill/product/variant/create 接口。

Usage:
  python product_center_variant_create.py '<JSON parameters>'           # 自动:小结果全量;大结果落盘+摘要
  python product_center_variant_create.py '<JSON parameters>' --inline  # 强制全量打印到 stdout
"""

import json
import os
import re
import sys
import time
from urllib.parse import quote, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

API_PATH = "/product-center/v1/skill/product/variant/create"
SLUG = "linkfox-product-center-variant-create"

SMALL_THRESHOLD = 8000

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
            "1. Visit https://agent.linkfox.com -> 设置 -> API KEY to obtain your Key\n"
            "2. Set the environment variable: export LINKFOX_AGENT_API_KEY=your-key-here",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _split_path_and_body(params):
    """提取 path variable 字段填到路径占位符,剩余字段作为 JSON body。"""
    used = set()

    def repl(m):
        name = m.group(1)
        used.add(name)
        if params is None or params.get(name) in (None, ""):
            print(f"Path variable '{name}' is required in params", file=sys.stderr)
            sys.exit(1)
        return quote(str(params[name]), safe="")

    api_path_filled = PATH_PLACEHOLDERS.sub(repl, API_PATH)
    agent_session_id = str((params or {}).get("agentSessionId") or os.environ.get("SESSION_ID", "")).strip()
    offer_source = str((params or {}).get("offerSource") or "").strip()
    query_params = {}
    if agent_session_id:
        query_params["agentSessionId"] = agent_session_id
        used.add("agentSessionId")
    if offer_source:
        # offerSource 同时走 query(会话来源绑定)与 body(写入 sku.offerSource),故不加入 used,保留在 body。
        query_params["offerSource"] = offer_source
    if query_params:
        api_path_filled = f"{api_path_filled}?{urlencode(query_params)}"
    body = {k: v for k, v in (params or {}).items() if k not in used}
    return api_path_filled, body


def validate(params):
    errs = []
    if params.get("offerSource") in (None, ""):
        errs.append("offerSource 必填(调用方按自身角色硬编码:10/11/12/13/14/15)")
    if not params.get("images"):
        errs.append("images 必填(1-30 张原图 URL)")
    if not params.get("productId") and not str(params.get("productName") or "").strip():
        errs.append("未传 productId 时 productName 必填")
    if params.get("productId") and not str(params.get("skuName") or "").strip() \
            and not str(params.get("productName") or "").strip():
        errs.append("追加变体(传 productId)时 skuName 必填，用于区分同商品下的不同变体")
    if errs:
        print("参数校验失败:\n- " + "\n- ".join(errs), file=sys.stderr)
        sys.exit(1)


def call_api(params):
    """原接口为 POST + (可选 @PathVariable) + @RequestBody;脚本拼路径 + JSON body。"""
    api_path_filled, body = _split_path_and_body(params)
    url = _paths().get_api_base() + api_path_filled
    req = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": get_api_key(),
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
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        body_resp = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(body_resp) if body_resp else {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception:
            return {"error": f"HTTP {e.code}: {e.reason}", "details": body_resp}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}


def _find_main_list(obj):
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
    return _paths().resolve_data_path(SLUG, ts)


def main():
    argv = sys.argv[1:]
    inline = "--inline" in argv
    argv = [a for a in argv if a != "--inline"]

    if not argv:
        print(f"Usage: {os.path.basename(__file__)} '<JSON parameters>' [--inline]", file=sys.stderr)
        sys.exit(1)

    try:
        params = json.loads(argv[0])
    except json.JSONDecodeError as e:
        print(f"Invalid parameter format: {e}", file=sys.stderr)
        sys.exit(1)

    validate(params)
    result = call_api(params)

    if inline:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if len(serialized.encode("utf-8")) <= SMALL_THRESHOLD:
        print(serialized)
        return

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
