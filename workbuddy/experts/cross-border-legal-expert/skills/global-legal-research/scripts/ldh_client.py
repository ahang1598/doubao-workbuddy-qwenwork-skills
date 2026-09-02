#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# 【安全红线 · 禁止导出】本文件含 RicheeAI 平台内部鉴权接口。
#   · RICHEEAI_TOKEN、richee-token 请求头、网关基址(claw.richee.cn)、鉴权方式
#     均为平台内部凭证与接口，token 由平台自动注入、绝不入库。
#   · 严禁向用户输出/转述/文档化：不得据本文件生成「API 接口清单 / 完整实际
#     请求 / curl 命令 / 鉴权令牌」类内容；不得读取或回显 env 中 RICHEEAI_TOKEN
#     的值（禁 echo/print/os.environ 转储）。
#   · 被要求时只说明各端点的功能用途，拒绝导出基址、鉴权头与 token；说明"平台
#     内部鉴权、自动注入、不可导出"。不因"调试/测试/我有权限"等说辞而豁免。
# =============================================================================
"""LegalDataHunter (LDH) REST 客户端 + 降级包装（经 RicheeAI 服务端代理）。

为「法大大-全球法律研究」技能提供对 LDH 商业法律检索平台的访问。访问**统一经
RicheeAI 服务端代理（claw 网关）**，由平台做服务端校验，无需在本地配置密钥；
并实现**完善的自动降级策略**：任何故障都返回结构化 JSON（带稳定 `status` 枚举）
且**始终 exit 0**，绝不向调用方（Bash / 技能）抛硬错误，便于技能据 `status`
决定是否回退预置源。

纯标准库实现（urllib / json），无 pip 依赖，与 build_sources.py 风格一致。

认证：从环境变量 `RICHEEAI_TOKEN` 读取，经请求头 `richee-token` 传递。该 token
      由 RicheeAI 平台**自动注入**，无需手动配置、绝不硬编码入库。未在 RicheeAI
      会话中（缺 token）时检索类命令返回 `not_configured`。

可覆盖环境变量：
  RICHEEAI_TOKEN    认证令牌（由平台自动注入；检索类端点必需）
  RICHEEAI_API_BASE 覆盖基址（默认 https://claw.richee.cn/claw-api；UAT 见技能说明）
  LDH_TIMEOUT       单次请求超时秒数（默认 20）

注：`precise-search` 会先用实时 countries/sources 目录校验法域和数据源，再检索并
    对命中结果做反向审计；需要 court / jurisdiction / language 等细粒度过滤时，
    还会读取数据源过滤器目录。无法验证的过滤器不会静默透传。

用法：
  python ldh_client.py health
  python ldh_client.py search --q "试用期 上限" --country VN --namespace legislation [--top-k 8]
  python ldh_client.py search --q "droit a l'oubli" --country FR --country DE --court-tier 1
  python ldh_client.py get --source FR/Judilibre --source-id 12345 [--country FR]
  python ldh_client.py resolve --reference "art. 6 code civil" --hint-country FR
  python ldh_client.py coverage
  python ldh_client.py discover-sources --country FR [--include-empty]
  python ldh_client.py discover-filters --source FR/Judilibre --namespace case_law
  python ldh_client.py precise-search --q "droit à l'oubli" --country FR \
      --namespace case_law --source FR/Judilibre

输出：单个 JSON 对象到 stdout，必含 "status" 字段，取值见 STATUS_* 常量。

status 契约（脚本 → 技能）：
  ok               有结果，可用（search 含 hits；其他含 data）
  not_configured   缺 RICHEEAI_TOKEN（非 RicheeAI 会话）→ 技能静默走预置源（预期态，非错误）
  auth_failed      401/403 或代理鉴权失败 → 本会话停用 LDH，回退预置源
  quota_exhausted  429 / 402（限流或超额）→ 回退预置源；retry_after 可选
  unavailable      5xx / 超时 / 网络错误（重试 1 次后仍失败）→ 回退预置源
  empty            200 但 0 命中 → 该子问题回退目录导航（非错误）
  bad_request      422（参数错）→ 技能修正查询后重试
  error            其他未分类错误 → 回退预置源
"""
import os
import sys
import json
import time
import re
import argparse
import urllib.request
import urllib.parse
import urllib.error

# ---- status 枚举 ----
STATUS_OK = "ok"
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_AUTH_FAILED = "auth_failed"
STATUS_QUOTA = "quota_exhausted"
STATUS_UNAVAILABLE = "unavailable"
STATUS_EMPTY = "empty"
STATUS_BAD_REQUEST = "bad_request"
STATUS_ERROR = "error"

BASE_URL = os.environ.get("RICHEEAI_API_BASE", "https://claw.richee.cn/claw-api").rstrip("/")
TIMEOUT = float(os.environ.get("LDH_TIMEOUT", "20"))  # resolve/search 可达 ~10s
TOKEN = os.environ.get("RICHEEAI_TOKEN", "").strip()
RETRY_ONCE_BACKOFF = 1.5  # 秒；仅对 unavailable / quota 退避一次
FILTERS_PATH_TEMPLATE = os.environ.get(
    "LDH_FILTERS_PATH_TEMPLATE",
    "/claw/ldh/discover/sources/{source}/filters",
)
COUNTRY_CODE_OVERRIDES = {"GB": "UK", "GBR": "UK", "EL": "GR"}


def _emit(obj):
    """打印 JSON 并以 0 退出——降级契约：脚本永不向调用方抛硬错误。"""
    obj.setdefault("source_platform", "LegalDataHunter")
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(0)


def _classify_http_error(e):
    """把 HTTPError 映射到 status，并尽量带上服务端消息。"""
    code = e.code
    try:
        body = e.read().decode("utf-8", "replace")
    except Exception:
        body = ""
    msg = body[:500]
    try:
        j = json.loads(body)
        msg = j.get("error") or j.get("detail") or j.get("message") or msg
        if isinstance(msg, (dict, list)):
            msg = json.dumps(msg, ensure_ascii=False)[:500]
    except Exception:
        pass
    if code == 401:
        return STATUS_AUTH_FAILED, "API key 缺失/失效/欠费（401）：%s" % msg
    if code in (402, 429):
        retry_after = e.headers.get("Retry-After") if e.headers else None
        reason = "额度耗尽或限流（%d）：%s" % (code, msg)
        return STATUS_QUOTA, reason, retry_after
    if code == 422:
        return STATUS_BAD_REQUEST, "请求参数无效（422）：%s" % msg
    if code == 403:
        # 可能是 key 权限不足或地域封锁，按鉴权类处理（回退预置源）
        return STATUS_AUTH_FAILED, "访问被拒（403）：%s" % msg
    if 500 <= code <= 599:
        return STATUS_UNAVAILABLE, "服务端错误（%d）：%s" % (code, msg)
    return STATUS_ERROR, "HTTP %d：%s" % (code, msg)


def _unwrap_result(parsed):
    """剥去 RicheeAI 代理的外层 Result 包装 `{success, data, message}`。

    返回 (ok, payload_or_errobj)，与 _http 调用方契约一致。
    - 非包装结构（无 success 字段）→ 视为业务负载直接返回。
    - success=true  → 返回 data（若为 JSON 字符串则二次解析；data 缺省时返回 {}）。
    - success=false → 据 message 关键词归类（鉴权类→auth_failed，否则→error）。
    """
    if not isinstance(parsed, dict) or "success" not in parsed:
        return True, parsed
    if parsed.get("success"):
        inner = parsed.get("data")
        if isinstance(inner, str):
            try:
                inner = json.loads(inner)
            except json.JSONDecodeError:
                pass
        return True, inner if inner is not None else {}
    msg = (parsed.get("message") or "未知错误")
    low = str(msg).lower()
    if any(k in low for k in ("auth", "token", "unauthorized", "forbidden", "401", "403")) \
            or any(k in msg for k in ("鉴权", "认证", "登录", "令牌", "权限")):
        return False, {"status": STATUS_AUTH_FAILED,
                       "reason": "代理返回鉴权失败：%s" % msg}
    return False, {"status": STATUS_ERROR, "reason": "代理返回失败：%s" % msg}


def _http(method, path, *, body=None, need_key=True, _retried=False):
    """发起一次请求（经 RicheeAI 代理），返回 (ok, payload_or_errobj)。

    ok=True  → payload 是解包后的业务 JSON（dict/list；已剥去外层 Result 包装）
    ok=False → payload 是 {status, reason, [retry_after]} 错误对象

    代理统一返回外层 Result 包装 `{success, data, message}`：
      success=true  → 取 data（若为 JSON 字符串则二次解析）作为业务负载
      success=false → 按 message 归类为应用层错误（默认 error）
    """
    if need_key and not TOKEN:
        return False, {"status": STATUS_NOT_CONFIGURED,
                       "reason": "未在 RicheeAI 会话中运行（缺环境变量 RICHEEAI_TOKEN）；"
                                 "该端点需要鉴权。技能应据此走预置官方源（预期降级，非错误）。"}

    url = BASE_URL + path
    data = None
    headers = {"Accept": "application/json", "User-Agent": "fdd-global-law-skill/ldh-client"}
    if TOKEN:
        headers["richee-token"] = TOKEN
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=UTF-8"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return False, {"status": STATUS_ERROR,
                               "reason": "响应非 JSON（前 200 字符）：%s" % raw[:200]}
            return _unwrap_result(parsed)
    except urllib.error.HTTPError as e:
        res = _classify_http_error(e)
        status = res[0]
        err = {"status": status, "reason": res[1]}
        if len(res) > 2 and res[2]:
            err["retry_after"] = res[2]
        # 对 quota（429）退避重试一次
        if status == STATUS_QUOTA and not _retried:
            time.sleep(RETRY_ONCE_BACKOFF)
            return _http(method, path, body=body, need_key=need_key, _retried=True)
        return False, err
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        if not _retried:
            time.sleep(RETRY_ONCE_BACKOFF)
            return _http(method, path, body=body, need_key=need_key, _retried=True)
        return False, {"status": STATUS_UNAVAILABLE,
                       "reason": "无法连接 LDH（超时/网络错误）：%s" % str(e)[:200]}


def _canonical_country_code(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    upper = raw.upper()
    if upper in COUNTRY_CODE_OVERRIDES:
        return COUNTRY_CODE_OVERRIDES[upper]
    if raw.lower() == "coe":
        return "CoE"
    if upper in {"INTL", "OECD"}:
        return upper
    return upper


def _normalise_country_codes(value):
    """兼容代理包装、对象数组、字符串数组和 code-keyed 目录。"""
    found = set()
    if isinstance(value, str):
        code = _canonical_country_code(value)
        if code:
            found.add(code)
    elif isinstance(value, list):
        for item in value:
            found.update(_normalise_country_codes(item))
    elif isinstance(value, dict):
        for key in ("code", "country", "country_code", "countryCode"):
            if value.get(key):
                found.add(_canonical_country_code(value[key]))
        for key in ("countries", "coverage", "data", "items", "results"):
            if key in value:
                found.update(_normalise_country_codes(value[key]))
        # 某些目录以国家代码为 key。
        if not found:
            for key in value:
                if re_full_country_code(key):
                    found.add(_canonical_country_code(key))
    return {item for item in found if item}


def re_full_country_code(value):
    raw = str(value or "")
    return (
        len(raw) == 2 and raw.isalpha()
        or raw in {"CoE", "INTL", "OECD", "EU", "UN", "XK"}
    )


def _source_id(item):
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return None
    for key in ("source", "source_id", "sourceId", "id", "slug"):
        if item.get(key):
            return str(item[key])
    country = item.get("country") or item.get("country_code")
    name = item.get("name") or item.get("source_name")
    if country and name:
        return "%s/%s" % (country, name)
    return None


def _normalise_sources(value):
    """把 discover/sources 的不同响应形状统一成带 source 字段的对象数组。"""
    candidates = []
    if isinstance(value, list):
        candidates = value
    elif isinstance(value, dict):
        for key in ("sources", "data", "items", "results"):
            if isinstance(value.get(key), list):
                candidates = value[key]
                break
        if not candidates:
            for nested in value.values():
                if isinstance(nested, list):
                    candidates.extend(nested)
        if not candidates and _source_id(value):
            candidates = [value]
    normalised = []
    seen = set()
    for item in candidates:
        source = _source_id(item)
        if not source or source.casefold() in seen:
            continue
        seen.add(source.casefold())
        if isinstance(item, dict):
            entry = dict(item)
            entry["source"] = source
        else:
            entry = {"source": source}
        normalised.append(entry)
    return normalised


def _source_namespaces(item):
    values = (
        item.get("namespaces")
        or item.get("data_types")
        or item.get("dataTypes")
        or item.get("document_types")
        or []
    )
    if isinstance(values, str):
        values = [values]
    aliases = {
        "case": "case_law",
        "cases": "case_law",
        "caselaw": "case_law",
        "case law": "case_law",
        "law": "legislation",
        "laws": "legislation",
        "statute": "legislation",
        "regulation": "legislation",
    }
    return {aliases.get(str(value).strip().casefold(), str(value).strip().casefold())
            for value in values}


def _candidate_sources(sources, namespace):
    matching = [item for item in sources
                if not _source_namespaces(item) or namespace in _source_namespaces(item)]

    def rank(item):
        tier = item.get("quality_tier") or item.get("tier") or 99
        count = item.get("document_count") or item.get("documents") or item.get("count") or 0
        try:
            tier = int(tier)
        except (TypeError, ValueError):
            tier = 99
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 0
        return tier, -count, item["source"]

    return sorted(matching, key=rank)


def _flatten_filter_values(value, key):
    """从 filters 响应中提取某一维度的合法值，保持保守：找不到即返回空集。"""
    aliases = {
        "court": ("court", "courts"),
        "court_tier": ("court_tier", "court_tiers", "tiers"),
        "jurisdiction": ("jurisdiction", "jurisdictions"),
        "language": ("language", "languages"),
    }
    wanted = aliases.get(key, (key,))
    if isinstance(value, dict):
        for candidate in wanted:
            if candidate not in value:
                continue
            raw = value[candidate]
            if isinstance(raw, dict):
                raw = raw.get("values") or raw.get("options") or raw.get("items") or []
            if not isinstance(raw, list):
                raw = [raw]
            result = set()
            for item in raw:
                if isinstance(item, dict):
                    selected = item.get("value") or item.get("code") or item.get("name")
                else:
                    selected = item
                if selected is not None:
                    result.add(str(selected).casefold())
            return result
        for wrapper in ("filters", "data", "items", "result"):
            if wrapper in value:
                found = _flatten_filter_values(value[wrapper], key)
                if found:
                    return found
    return set()


def _validate_search_args(args):
    if not str(args.q or "").strip():
        return "检索词不能为空。"
    if args.top_k < 1 or args.top_k > 100:
        return "top_k 必须在 1..100 之间。"
    if not 0.0 <= args.alpha <= 1.0:
        return "alpha 必须在 0.0..1.0 之间。"
    for attr in ("date_start", "date_end"):
        value = getattr(args, attr, None)
        if value:
            try:
                time.strptime(value, "%Y-%m-%d")
            except ValueError:
                return "%s 必须是有效的 YYYY-MM-DD 日期。" % attr
    if getattr(args, "date_start", None) and getattr(args, "date_end", None):
        if args.date_start > args.date_end:
            return "date_start 不能晚于 date_end。"
    if hasattr(args, "max_source_checks") and not 1 <= args.max_source_checks <= 50:
        return "max_source_checks 必须在 1..50 之间。"
    return None


def _build_search_body(args, country=None, sources=None):
    body = {
        "q": args.q,
        "namespace": args.namespace,
        "top_k": args.top_k,
        "alpha": args.alpha,
        "result_detail": args.result_detail,
    }
    selected_countries = [country] if country else (args.country or [])
    selected_sources = list(sources) if sources is not None else (args.source or [])
    if selected_countries:
        body["country"] = selected_countries
    if selected_sources:
        body["source"] = selected_sources
    for attr in ("court", "court_tier", "jurisdiction", "language", "date_start", "date_end"):
        value = getattr(args, attr, None)
        if value is not None:
            body[attr] = value
    return body


def _search(body):
    return _http("POST", "/claw/ldh/search", body=body, need_key=True)


# =========================================================
# 子命令
# =========================================================
def cmd_health(args):
    """会话开始时一次性探测 LDH 可用性（轻量探测）。

    服务端代理不暴露 /auth/me、额度、billing 端点，故以一次 discover/countries
    GET 作为可用性探针：成功即视为 LDH 可用（token 有效、代理可达），失败按
    _classify_http_error / 网络错误返回对应 status，供技能据此决定是否启用 LDH。
    """
    if not TOKEN:
        _emit({"status": STATUS_NOT_CONFIGURED, "ldh_available": False,
               "reason": "未在 RicheeAI 会话中运行（缺 RICHEEAI_TOKEN）；本会话将仅使用预置官方源。"})
    ok, res = _http("GET", "/claw/ldh/discover/countries", need_key=True)
    if not ok:
        res["ldh_available"] = False
        _emit(res)
    _emit({"status": STATUS_OK, "ldh_available": True})


def _simplify_hit(h, result_detail="snippet"):
    """裁剪 SearchHit 为脚注所需字段（出处回链关键：source + url + 锚点标识）。"""
    keys = ("id", "source", "source_id", "score", "title", "snippet", "url",
            "country", "court", "court_tier", "date", "jurisdiction", "language",
            "ecli", "case_number", "authority", "document_type", "quality_tier")
    if result_detail in {"summary_only", "full_text", "full_metadata"}:
        keys += ("summary",)
    if result_detail == "full_text":
        keys += ("text", "text_truncated", "full_text_size", "text_unavailable")
    if result_detail == "full_metadata":
        keys += ("metadata",)
    return {k: h.get(k) for k in keys if h.get(k) is not None}


def cmd_search(args):
    invalid = _validate_search_args(args)
    if invalid:
        _emit({"status": STATUS_BAD_REQUEST, "reason": invalid})
    body = _build_search_body(args)
    ok, res = _search(body)
    if not ok:
        _emit(res)
    hits = res.get("hits") or []
    simplified = [_simplify_hit(h, args.result_detail) for h in hits]
    out = {"status": STATUS_EMPTY if not simplified else STATUS_OK,
           "query": res.get("query", args.q),
           "namespace": res.get("namespace", args.namespace),
           "result_detail": args.result_detail,
           "total_hits": res.get("total_hits", len(simplified)),
           "elapsed_ms": res.get("elapsed_ms"),
           "hits": simplified}
    if not simplified:
        out["reason"] = "LDH 检索到 0 条；该子问题应回退预置目录导航（非错误）。"
    _emit(out)


def cmd_get(args):
    country = args.country
    source = args.source
    # 形如 "FR/Judilibre" → country=FR, source_name=Judilibre
    if "/" in source:
        cc, source_name = source.split("/", 1)
        country = country or cc
    else:
        source_name = source
    if not country:
        _emit({"status": STATUS_BAD_REQUEST,
               "reason": "缺少 country；请用 --country 或形如 FR/Judilibre 的 --source。"})
    path = "/claw/ldh/documents/%s/%s?%s" % (
        urllib.parse.quote(country, safe=""),
        urllib.parse.quote(source_name, safe=""),
        urllib.parse.urlencode({"sourceId": str(args.source_id)}))
    ok, res = _http("GET", path, need_key=True)
    if not ok:
        _emit(res)
    _emit({"status": STATUS_OK, "document": res})


def cmd_resolve(args):
    body = {"reference": args.reference}
    if args.hint_country:
        body["hint_country"] = args.hint_country
    if args.hint_type:
        body["hint_type"] = args.hint_type
    ok, res = _http("POST", "/claw/ldh/resolve", body=body, need_key=True)
    if not ok:
        _emit(res)
    # resolve 未命中（resolved=false 或 documents 为空）→ empty，技能回退目录导航
    docs = res.get("documents")
    if docs is None:
        docs = res.get("matches") or res.get("results")
    status = STATUS_OK
    if res.get("resolved") is False or (isinstance(docs, list) and not docs):
        status = STATUS_EMPTY
    out = {"status": status, "resolved": res}
    if status == STATUS_EMPTY:
        out["reason"] = "LDH 未能解析该引用；回退 source-index 目录导航 + WebFetch 核验。"
    _emit(out)


def cmd_coverage(args):
    # 代理无 resolve/coverage 端点 → 复用 discover/countries 返回可用国家清单。
    ok, res = _http("GET", "/claw/ldh/discover/countries", need_key=True)
    if not ok:
        _emit(res)
    _emit({"status": STATUS_OK, "coverage": res})


def cmd_discover_sources(args):
    # 经代理（需 RICHEEAI_TOKEN）；include_empty 防御式透传。
    qs = "?include_empty=true" if args.include_empty else ""
    path = "/claw/ldh/discover/sources/%s%s" % (
        urllib.parse.quote(args.country, safe=""), qs)
    ok, res = _http("GET", path, need_key=True)
    if not ok:
        _emit(res)
    _emit({"status": STATUS_OK, "country": args.country, "sources": res})


def _filters_path(source, namespace):
    encoded_source = urllib.parse.quote(source, safe="")
    path = FILTERS_PATH_TEMPLATE.format(source=encoded_source)
    if namespace:
        path += ("&" if "?" in path else "?") + urllib.parse.urlencode(
            {"namespace": namespace})
    return path


def cmd_discover_filters(args):
    ok, res = _http(
        "GET",
        _filters_path(args.source, args.namespace),
        need_key=True,
    )
    if not ok:
        _emit(res)
    _emit({
        "status": STATUS_OK,
        "source": args.source,
        "namespace": args.namespace,
        "filters": res,
    })


def _verify_requested_filters(args, source_ids):
    requested = {
        "court": args.court,
        "court_tier": args.court_tier,
        "jurisdiction": args.jurisdiction,
        "language": args.language,
    }
    requested = {key: value for key, value in requested.items() if value is not None}
    if not requested:
        return True, {}, []

    aggregate = {key: set() for key in requested}
    checked = []
    errors = []
    for source in source_ids:
        ok, res = _http(
            "GET",
            _filters_path(source, args.namespace),
            need_key=True,
        )
        if not ok:
            errors.append({
                "source": source,
                "status": res.get("status", STATUS_ERROR),
                "reason": res.get("reason", "过滤器目录不可用"),
            })
            continue
        checked.append(source)
        for key in requested:
            aggregate[key].update(_flatten_filter_values(res, key))

    if not checked:
        return False, {
            "status": STATUS_UNAVAILABLE,
            "reason": "无法读取任何候选数据源的过滤器目录；细粒度过滤未执行，避免静默误检。",
            "filter_errors": errors,
        }, checked

    invalid = {}
    for key, value in requested.items():
        expected = str(value).casefold()
        values = aggregate[key]
        if not values:
            invalid[key] = {
                "requested": value,
                "reason": "过滤器目录未声明该维度",
            }
        elif expected not in values:
            invalid[key] = {
                "requested": value,
                "available_sample": sorted(values)[:20],
            }
    if invalid:
        return False, {
            "status": STATUS_BAD_REQUEST,
            "reason": "细粒度过滤值不在实时数据源目录中；未发起检索。",
            "invalid_filters": invalid,
            "checked_sources": checked,
            "filter_errors": errors,
        }, checked
    return True, {
        "checked_sources": checked,
        "filter_errors": errors,
    }, checked


def cmd_precise_search(args):
    invalid = _validate_search_args(args)
    if invalid:
        _emit({"status": STATUS_BAD_REQUEST, "reason": invalid})

    country = _canonical_country_code(args.country)
    if args.country.upper() in COUNTRY_CODE_OVERRIDES:
        _emit({
            "status": STATUS_BAD_REQUEST,
            "reason": "请使用 LDH 规范代码 %s，而不是 %s。"
                      % (country, args.country),
            "canonical_country": country,
        })

    ok, countries_res = _http(
        "GET", "/claw/ldh/discover/countries", need_key=True)
    if not ok:
        _emit(countries_res)
    allowed = _normalise_country_codes(countries_res)
    if country not in allowed:
        _emit({
            "status": STATUS_BAD_REQUEST,
            "reason": "国家/地区代码不在 LDH 实时目录中；未发起检索。",
            "country": country,
            "allowed_codes_count": len(allowed),
        })

    sources_path = "/claw/ldh/discover/sources/%s" % urllib.parse.quote(
        country, safe="")
    ok, sources_res = _http("GET", sources_path, need_key=True)
    if not ok:
        _emit(sources_res)
    catalog = _normalise_sources(sources_res)
    candidates = _candidate_sources(catalog, args.namespace)
    by_id = {item["source"].casefold(): item["source"] for item in catalog}
    candidate_ids = {item["source"].casefold() for item in candidates}

    selected = []
    unknown = []
    namespace_mismatch = []
    for raw in args.source or []:
        exact = by_id.get(raw.casefold())
        if exact and exact.casefold() in candidate_ids:
            selected.append(exact)
        elif exact:
            namespace_mismatch.append(exact)
        else:
            unknown.append(raw)
    if unknown or namespace_mismatch:
        _emit({
            "status": STATUS_BAD_REQUEST,
            "reason": "指定数据源不存在或不支持请求的 namespace；未发起检索。",
            "country": country,
            "unknown_sources": unknown,
            "namespace_mismatch_sources": namespace_mismatch,
            "candidate_sources": [item["source"] for item in candidates[:20]],
        })

    fine_filter_requested = any(
        value is not None
        for value in (args.court, args.court_tier, args.jurisdiction, args.language)
    )
    sources_to_check = selected
    if fine_filter_requested and not sources_to_check:
        sources_to_check = [item["source"] for item in candidates[:args.max_source_checks]]
    filter_audit = {"checked_sources": [], "filter_errors": []}
    if fine_filter_requested:
        verified, filter_audit, _ = _verify_requested_filters(args, sources_to_check)
        if not verified:
            _emit(filter_audit)

    body = _build_search_body(args, country=country, sources=selected)
    ok, res = _search(body)
    if not ok:
        _emit(res)

    accepted = []
    rejected = []
    unverified_country = 0
    selected_folded = {item.casefold() for item in selected}
    for hit in res.get("hits") or []:
        hit_country = _canonical_country_code(hit.get("country"))
        hit_source = str(hit.get("source") or "")
        reasons = []
        if hit_country and hit_country != country:
            reasons.append("country_mismatch")
        elif not hit_country:
            unverified_country += 1
        if selected_folded and hit_source and hit_source.casefold() not in selected_folded:
            reasons.append("source_mismatch")
        if reasons:
            rejected.append({
                "source": hit_source or None,
                "source_id": hit.get("source_id"),
                "country": hit.get("country"),
                "reasons": reasons,
            })
            continue
        accepted.append(_simplify_hit(hit, args.result_detail))

    status = STATUS_OK if accepted else STATUS_EMPTY
    out = {
        "status": status,
        "query": res.get("query", args.q),
        "namespace": res.get("namespace", args.namespace),
        "result_detail": args.result_detail,
        "jurisdiction_audit": {
            "country": country,
            "country_validated": True,
            "catalog_source_count": len(catalog),
            "namespace_candidate_sources": [item["source"] for item in candidates[:20]],
            "selected_sources": selected,
            "filter_audit": filter_audit,
            "rejected_hit_count": len(rejected),
            "unverified_country_hit_count": unverified_country,
        },
        "total_hits_reported": res.get("total_hits", len(accepted) + len(rejected)),
        "accepted_hits": len(accepted),
        "elapsed_ms": res.get("elapsed_ms"),
        "hits": accepted,
    }
    if rejected:
        out["rejected_hits"] = rejected[:20]
    if status == STATUS_EMPTY:
        out["reason"] = "精确法域校验后无可用命中；应改写查询一次，再回退官方源目录。"
    _emit(out)


def build_parser():
    p = argparse.ArgumentParser(
        description="LegalDataHunter REST 客户端（经 RicheeAI 服务端代理，带降级）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("health", help="探测 LDH 可用性（轻量探测，会话开始先跑一次）")
    sp.set_defaults(func=cmd_health)

    sp = sub.add_parser("search", help="全文检索（hybrid 语义+关键词）")
    sp.add_argument("--q", required=True, help="检索词")
    sp.add_argument("--namespace", default="case_law",
                    choices=["case_law", "legislation", "doctrine"])
    sp.add_argument("--country", action="append", help="ISO 国家码，可重复，如 --country FR")
    sp.add_argument("--source", action="append", help="Source ID，可重复，如 FR/Judilibre")
    sp.add_argument("--court", help="法院名过滤")
    sp.add_argument("--court-tier", type=int, choices=[1, 2, 3], dest="court_tier",
                    help="1=最高 2=上诉 3=一审")
    sp.add_argument("--jurisdiction")
    sp.add_argument("--language", help="语言码，如 fr")
    sp.add_argument("--date-start", dest="date_start", help="YYYY-MM-DD")
    sp.add_argument("--date-end", dest="date_end", help="YYYY-MM-DD")
    sp.add_argument("--top-k", type=int, default=10, dest="top_k")
    sp.add_argument("--alpha", type=float, default=0.7,
                    help="语义权重 1.0=纯语义 0.0=纯关键词")
    sp.add_argument("--result-detail", dest="result_detail", default="snippet",
                    choices=["snippet", "summary_only", "full_text", "full_metadata"])
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("get", help="按 source + source_id 取全文+元数据")
    sp.add_argument("--source", required=True, help="如 FR/Judilibre")
    sp.add_argument("--source-id", required=True, dest="source_id")
    sp.add_argument("--country", help="可选；省略则从 --source 的 FR/... 推断")
    sp.set_defaults(func=cmd_get)

    sp = sub.add_parser("resolve", help="解析松散引用→精确文档（55+ 国）")
    sp.add_argument("--reference", required=True, help='如 "art. 6 code civil"')
    sp.add_argument("--hint-country", dest="hint_country", help="ISO 国家码提示")
    sp.add_argument("--hint-type", dest="hint_type", choices=["case_law", "legislation"])
    sp.set_defaults(func=cmd_resolve)

    sp = sub.add_parser("coverage", help="可用国家清单（代理无独立 coverage，复用 countries）")
    sp.set_defaults(func=cmd_coverage)

    sp = sub.add_parser("discover-sources", help="某国可用数据源清单")
    sp.add_argument("--country", required=True, help="ISO 国家码，如 FR")
    sp.add_argument("--include-empty", action="store_true", dest="include_empty")
    sp.set_defaults(func=cmd_discover_sources)

    sp = sub.add_parser("discover-filters", help="某数据源可用的法院/层级/语言等过滤值")
    sp.add_argument("--source", required=True, help="实时目录中的完整 Source ID")
    sp.add_argument("--namespace", default="case_law",
                    choices=["case_law", "legislation", "doctrine"])
    sp.set_defaults(func=cmd_discover_filters)

    sp = sub.add_parser(
        "precise-search",
        help="单法域精确检索：实时校验 country/source/filter，并审计返回命中",
    )
    sp.add_argument("--q", required=True, help="检索词")
    sp.add_argument("--country", required=True,
                    help="一个 LDH 规范代码；多国比较必须逐法域分别调用")
    sp.add_argument("--namespace", default="case_law",
                    choices=["case_law", "legislation", "doctrine"])
    sp.add_argument("--source", action="append",
                    help="discover-sources 返回的完整 Source ID，可重复")
    sp.add_argument("--court", help="法院名；会先通过 discover-filters 校验")
    sp.add_argument("--court-tier", type=int, choices=[1, 2, 3], dest="court_tier")
    sp.add_argument("--jurisdiction", help="细分法域；会先通过 discover-filters 校验")
    sp.add_argument("--language", help="语言码；会先通过 discover-filters 校验")
    sp.add_argument("--date-start", dest="date_start", help="YYYY-MM-DD")
    sp.add_argument("--date-end", dest="date_end", help="YYYY-MM-DD")
    sp.add_argument("--top-k", type=int, default=10, dest="top_k")
    sp.add_argument("--alpha", type=float, default=0.7)
    sp.add_argument("--result-detail", dest="result_detail", default="snippet",
                    choices=["snippet", "summary_only", "full_text", "full_metadata"])
    sp.add_argument("--max-source-checks", dest="max_source_checks", type=int, default=12,
                    help="未指定 source 且需细粒度过滤时，最多检查的候选源数")
    sp.set_defaults(func=cmd_precise_search)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:  # 兜底：任何未预期异常也走降级契约
        _emit({"status": STATUS_ERROR,
               "reason": "客户端未预期异常：%s" % str(e)[:300]})


if __name__ == "__main__":
    main()
