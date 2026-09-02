#!/usr/bin/env python3
"""商品库-创建Listing - LinkFox Skill
调用 /product-center/v1/skill/product/listing/create 接口。

Usage:
  python product_center_listing_create.py '<JSON parameters>'           # 自动:小结果全量;大结果落盘+摘要
"""

import json
import os
import re
import sys
import time
from urllib.parse import quote, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

API_PATH = "/product-center/v1/skill/product/listing/create"
SLUG = "linkfox-product-center-listing-create"


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
        query_params["offerSource"] = offer_source
        used.add("offerSource")
    if query_params:
        api_path_filled = f"{api_path_filled}?{urlencode(query_params)}"
    body = {k: v for k, v in (params or {}).items() if k not in used}
    _coerce_body_fields(body)
    return api_path_filled, body


def _strip_markdown(text):
    """去掉常见 markdown 标记，保留纯文本。

    亚马逊等前台不渲染 markdown，**/__/`/#/- 等会以字面符号落库显示，
    故对落库文案做清洗：去掉加粗/代码/标题/列表标记，单 * 与 _ 保留以免破坏产品码。
    """
    if not isinstance(text, str):
        return text
    text = re.sub(r'^\s*([-*+]\s+|\d+\.\s+)', '', text, flags=re.M)  # 行首列表标记
    text = re.sub(r'^\s*#{1,6}\s+', '', text, flags=re.M)            # 行首标题标记
    text = re.sub(r'(?<!\w)\*\*(.+?)\*\*(?!\w)', r'\1', text)        # **加粗**(两侧非单词字符才删,避免误伤词内型号)
    text = re.sub(r'(?<!\w)__(.+?)__(?!\w)', r'\1', text)            # __加粗__
    text = re.sub(r'(?<!\w)`(.+?)`(?!\w)', r'\1', text)              # `代码`
    return text


def _dedup_keywords(body):
    """对 keywords JSON 中每个分组数组去重，保持顺序。"""
    raw = body.get("keywords")
    if not raw:
        return
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return
    if not isinstance(obj, dict):
        return
    for key, val in obj.items():
        if isinstance(val, list):
            obj[key] = list(dict.fromkeys(val))
    body["keywords"] = json.dumps(obj, ensure_ascii=False)


def _coerce_body_fields(body):
    """对已知字段做防御性类型转换，兼容调用方传 list/dict 的场景。"""
    if "bulletPoints" in body and isinstance(body["bulletPoints"], list):
        body["bulletPoints"] = "\n".join(str(item) for item in body["bulletPoints"])
    if "keywords" in body and not isinstance(body["keywords"], str):
        body["keywords"] = json.dumps(body["keywords"], ensure_ascii=False)
    _dedup_keywords(body)
    if "productImages" in body and isinstance(body["productImages"], str):
        body["productImages"] = [body["productImages"]]
    if "productVideos" in body and isinstance(body["productVideos"], str):
        body["productVideos"] = [body["productVideos"]]
    # 落库文案清洗 markdown 标记，避免字面 **/`/# 等显示到前台
    for fld in ("title", "bulletPoints"):
        if isinstance(body.get(fld), str):
            body[fld] = _strip_markdown(body[fld])


def validate(params):
    errs = []
    if params.get("offerSource") in (None, ""):
        errs.append("offerSource 必填(调用方按自身角色硬编码:10/11/12/13/14/15)")
    if not str(params.get("platform") or "").strip():
        errs.append("platform 必填")
    if not str(params.get("marketplace") or "").strip():
        errs.append("marketplace 必填")
    if not params.get("skuId") and not (str(params.get("productName") or "").strip() and params.get("productImages")):
        errs.append("未传 skuId 时 productName + productImages 必填")
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
