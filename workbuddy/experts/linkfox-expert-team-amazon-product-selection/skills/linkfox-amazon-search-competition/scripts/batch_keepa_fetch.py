#!/usr/bin/env python3
"""批量 Keepa Product Request — 为前3页竞品分析补充深度数据

从合并后的 SERP JSON 提取 ASIN 列表，按 5 个一批调用 Keepa API（history=1），
合并结果输出为 keepa_enriched.json。

Usage:
  python batch_keepa_fetch.py <merged_products.json> --domain <keepa_domain_id> [--inline] [--no-cache]
  python batch_keepa_fetch.py <merged_products.json> --domain 1

参数:
  merged_products.json  Step 2 输出的合并商品 JSON
  --domain              Keepa 站点 ID (1=US, 2=UK, 3=DE, 4=FR, 5=JP, 6=CA, 8=IT, 9=ES)
  --inline              强制全量打印到 stdout
  --no-cache            禁用本地缓存
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from linkfox_paths import get_api_base, resolve_data_path

SLUG = "linkfox-keepa-product-request"
BATCH_SIZE = 5
BATCH_DELAY_SEC = 2.0
MAX_RETRY = 3
RETRY_BACKOFF = [1, 2, 4]
COOLDOWN_SEC = 120  # 限流冷却时间（秒）
SMALL_THRESHOLD = 8000
CACHE_TTL_SEC = 24 * 60 * 60

# Keepa 值为 -1 或 0 时表示不可用
INVALID_VALUES = {-1, 0, "0", "-1", "", None}

# 需要提取的 Keepa 字段列表
KEEPA_FIELDS = [
    "asin", "parentAsin", "brand", "manufacturer", "model", "color", "material",
    "price", "primePrice", "currency", "rating", "ratings", "reviewCount",
    "salesRank", "salesRank30", "salesRank90", "salesRank180",
    "monthlySalesUnits", "monthlySalesRevenue",
    "monthlySalesUnits1MonthAgo", "monthlySalesUnits2MonthsAgo",
    "monthlySalesUnits3MonthsAgo", "monthlySalesUnits4MonthsAgo",
    "monthlySalesUnits5MonthsAgo", "monthlySalesUnits6MonthsAgo",
    "monthlySalesUnits7MonthsAgo", "monthlySalesUnits8MonthsAgo",
    "monthlySalesUnits9MonthsAgo", "monthlySalesUnits10MonthsAgo",
    "monthlySalesUnits11MonthsAgo", "monthlySalesUnits12MonthsAgo",
    "availableDate", "lastUpdate", "fulfillment", "fbaFees", "profit",
    "referralFeePercentage", "buyBoxSellerId", "sellerNum", "variationNum",
    "isHazmat", "isAdultProduct", "rootCategory", "categoryTree",
    "categoryTreeId", "subcategories", "imageUrl", "productImageUrls",
    "asinUrl", "urlSlug", "packageHeight", "packageLength", "packageWidth",
    "packageDimensions", "packageQuantity", "packageWeight", "weight",
    "itemHeight", "itemLength", "itemWidth", "dimensionsType", "dimension",
]


# ── 工具函数 ──────────────────────────────────────────────────

def get_api_key() -> str:
    key = os.environ.get("LINKFOX_AGENT_API_KEY") or os.environ.get("LINKFOXAGENT_API_KEY")
    if not key:
        print("API Key 未配置", file=sys.stderr)
        sys.exit(1)
    return key


# ── 缓存 ──────────────────────────────────────────────────────

def _cache_key(params: dict) -> str:
    raw = json.dumps(params, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _cache_path(params: dict) -> str:
    cwd = os.getcwd()
    path = os.path.join(cwd, "linkfox", ".cache", SLUG)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{SLUG}-{_cache_key(params)}.json")


def _load_cache(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    if time.time() - os.path.getmtime(path) > CACHE_TTL_SEC:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            payload.setdefault("_cache", {})["hit"] = True
        return payload
    except (OSError, json.JSONDecodeError):
        return None


def _save_cache(path: str, payload: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# ── 核心函数 ──────────────────────────────────────────────────

def extract_asins(merged_path: str) -> list[dict]:
    """从 merged_products.json 提取 ASIN 列表。"""
    with open(merged_path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        products = data
    elif isinstance(data, dict):
        products = data.get("products", data.get("items", []))
    else:
        products = []
    return [{"asin": p.get("asin"), "organic_rank": p.get("organic_rank")} for p in products if p.get("asin")]


def make_batches(asins: list[str], size: int = BATCH_SIZE) -> list[list[str]]:
    """按 size 个一组分批。"""
    return [asins[i:i + size] for i in range(0, len(asins), size)]


def call_keepa_batch(asin_list: list[str], domain: int, history: int = 1) -> dict:
    """调用一次 Keepa API（单批最多 5 ASIN）。"""
    params = {
        "asin": ",".join(asin_list),
        "domain": str(domain),
        "history": history,
    }
    api_url = get_api_base() + "/keepa/productRequest"
    api_key = get_api_key()
    data = json.dumps(params).encode("utf-8")
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
        "User-Agent": "LinkFox-Skill/2.0",
        "SESSION_ID": os.environ.get("SESSION_ID", ""),
        "MESSAGE_ID": os.environ.get("MESSAGE_ID", ""),
        "MODE_ID": os.environ.get("MODE_ID", ""),
        "APP_NAME": os.environ.get("APP_NAME", ""),
    }
    req = Request(api_url, data=data, headers=headers, method="POST")
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


def _normalize_value(val):
    """将 Keepa 的 -1/0 值统一转为 None。"""
    if isinstance(val, (list, dict)):
        return val
    if val in INVALID_VALUES:
        return None
    return val


def parse_keepa_response(response: dict) -> dict[str, dict]:
    """解析 Keepa 响应，按 ASIN 索引。"""
    if not isinstance(response, dict):
        return {}
    if response.get("errcode") != 200 and "error" in response:
        return {}

    products = response.get("products", [])
    if not products:
        # 兼容直接返回数组的情况
        if isinstance(response, list):
            products = response

    result = {}
    for p in products:
        if not isinstance(p, dict):
            continue
        asin = p.get("asin")
        if not asin:
            continue
        item = {}
        for field in KEEPA_FIELDS:
            val = p.get(field)
            item[field] = _normalize_value(val)
        result[asin] = item
    return result


def fetch_all(asins: list[str], domain: int, use_cache: bool = True) -> dict:
    """批量获取所有 ASIN 的 Keepa 数据。3 次重试失败后停止全部批次并计算冷却时间。"""
    batches = make_batches(asins)
    all_data = {}
    success_count = 0
    failed_asins = []
    cached_hits = 0
    stopped_early = False
    stop_reason = ""
    retry_after_ts = None
    retry_after_str = ""
    rate_limited = False

    for i, batch in enumerate(batches):
        if stopped_early:
            failed_asins.extend(batch)
            continue

        params = {
            "asin": ",".join(batch),
            "domain": str(domain),
            "history": 1,
        }

        # 缓存检查
        cache_p = _cache_path(params)
        cached = _load_cache(cache_p) if use_cache else None

        if cached is not None:
            cached_hits += 1
            parsed = parse_keepa_response(cached)
            for asin, data in parsed.items():
                all_data[asin] = data
                success_count += 1
            print(f"  Batch {i+1}/{len(batches)} [cache hit]: {len(parsed)} ASINs", file=sys.stderr)
            continue

        # API 调用（含重试）
        response = None
        batch_failed = False
        for attempt in range(MAX_RETRY):
            if attempt > 0:
                delay = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                print(f"  Batch {i+1}/{len(batches)} retry {attempt}/{MAX_RETRY} after {delay}s...", file=sys.stderr)
                time.sleep(delay)

            response = call_keepa_batch(batch, domain, history=1)

            # 检查积分不足
            if isinstance(response, dict):
                err = response.get("error", "")
                errmsg = response.get("errmsg", "")
                err_str = str(err) + str(errmsg)

                if "402" in err_str or "积分" in err_str or "余额" in err_str or "quota" in err_str.lower():
                    stopped_early = True
                    stop_reason = "积分不足"
                    print(f"  Batch {i+1}/{len(batches)}: 积分不足，停止全部批次", file=sys.stderr)
                    failed_asins.extend(batch)
                    break

                if "401" in err_str or "认证" in err_str:
                    stopped_early = True
                    stop_reason = "认证失败"
                    print(f"  Batch {i+1}/{len(batches)}: 认证失败，停止全部批次", file=sys.stderr)
                    failed_asins.extend(batch)
                    break

                # 检查限流（429 / rate limit / too many requests）
                if "429" in err_str or "rate" in err_str.lower() or "too many" in err_str.lower() or "limit" in err_str.lower():
                    rate_limited = True
                    if attempt < MAX_RETRY - 1:
                        continue  # 继续重试
                    else:
                        # 3 次重试均因限流失败，停止全部批次
                        stopped_early = True
                        stop_reason = "限流（429）"
                        retry_after_ts = time.time() + COOLDOWN_SEC
                        retry_after_dt = datetime.fromtimestamp(retry_after_ts)
                        retry_after_str = retry_after_dt.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"  Batch {i+1}/{len(batches)}: 3次重试均被限流，停止全部批次", file=sys.stderr)
                        print(f"  >>> 建议冷却 {COOLDOWN}s 后重新执行，预计恢复时间: {retry_after_str}", file=sys.stderr)
                        failed_asins.extend(batch)
                        break

                if "error" not in response:
                    break  # 成功
            else:
                break  # 非预期格式，跳出

        if stopped_early:
            continue

        if response is None or (isinstance(response, dict) and "error" in response):
            # 非限流类失败（网络超时等），3 次重试后也停止
            if not rate_limited:
                stopped_early = True
                stop_reason = "网络错误（3次重试失败）"
                retry_after_ts = time.time() + COOLDOWN_SEC
                retry_after_dt = datetime.fromtimestamp(retry_after_ts)
                retry_after_str = retry_after_dt.strftime("%Y-%m-%d %H:%M:%S")
                print(f"  Batch {i+1}/{len(batches)} [FAILED after 3 retries]: 停止全部批次", file=sys.stderr)
                print(f"  >>> 建议 {COOLDOWN}s 后重新执行，预计恢复时间: {retry_after_str}", file=sys.stderr)
            failed_asins.extend(batch)
            continue

        # 保存缓存
        if use_cache:
            _save_cache(cache_p, response)

        # 解析
        parsed = parse_keepa_response(response)
        for asin, data in parsed.items():
            all_data[asin] = data
            success_count += 1

        # 统计未返回的 ASIN
        for asin in batch:
            if asin not in parsed:
                failed_asins.append(asin)

        cost_token = response.get("costToken", "?")
        print(f"  Batch {i+1}/{len(batches)} [OK]: {len(parsed)} ASINs, costToken={cost_token}", file=sys.stderr)

        # 批次间延迟
        if i < len(batches) - 1:
            time.sleep(BATCH_DELAY_SEC)

    # 计算剩余未完成的批次
    remaining_batches = 0
    if stopped_early:
        completed_asins = set(all_data.keys())
        remaining_batches = sum(1 for b in batches if any(a not in completed_asins for a in b))

    return {
        "meta": {
            "total_asins": len(asins),
            "success": success_count,
            "failed": len(failed_asins),
            "failed_asins": failed_asins,
            "batches": len(batches),
            "batches_completed": len(batches) - remaining_batches if stopped_early else len(batches),
            "batches_remaining": remaining_batches,
            "cached_hits": cached_hits,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "domain": domain,
            "history": 1,
            "stopped_early": stopped_early,
            "stop_reason": stop_reason,
            "rate_limited": rate_limited,
            "cooldown_sec": COOLDOWN_SEC if stopped_early else 0,
            "retry_after": retry_after_str,
            "retry_after_timestamp": retry_after_ts,
        },
        "data": all_data,
    }


def merge_keepa_into_products(products: list[dict], keepa_data: dict) -> list[dict]:
    """将 Keepa 数据平铺合并到 products 中。"""
    data = keepa_data.get("data", {})
    out = []
    for p in products:
        q = dict(p)
        asin = p.get("asin")
        keepa_item = data.get(asin)
        if keepa_item:
            for k, v in keepa_item.items():
                # 不覆盖 SERP 已有的关键字段
                if k in ("asin", "title", "imageUrl", "asinUrl"):
                    continue
                q[k] = v
            q["keepa_available"] = True
        else:
            q["keepa_available"] = False
        out.append(q)
    return out


# ── 主流程 ────────────────────────────────────────────────────

def main():
    argv = sys.argv[1:]
    inline = "--inline" in argv
    use_cache = "--no-cache" not in argv
    argv = [a for a in argv if a not in ("--inline", "--no-cache")]

    domain = None
    remaining = []
    i = 0
    while i < len(argv):
        if argv[i] == "--domain" and i + 1 < len(argv):
            domain = int(argv[i + 1])
            i += 2
        else:
            remaining.append(argv[i])
            i += 1
    argv = remaining

    if not argv or domain is None:
        print(
            f"Usage: {os.path.basename(__file__)} <merged_products.json> --domain <id> [--inline] [--no-cache]",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = argv[0]
    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 提取 ASIN
    asin_info = extract_asins(input_path)
    asins = [a["asin"] for a in asin_info]
    if not asins:
        print("No ASINs found in input file", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(asins)} ASINs, {len(make_batches(asins))} batches (domain={domain})", file=sys.stderr)

    # 批量获取
    result = fetch_all(asins, domain, use_cache=use_cache)

    # 同时输出合并后的 products（含 Keepa 字段）
    with open(input_path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list):
        products = raw
    elif isinstance(raw, dict):
        products = raw.get("products", raw.get("items", []))
    else:
        products = []

    merged_products = merge_keepa_into_products(products, result)
    result["merged_products"] = merged_products

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    ts = int(time.time())
    out_path = resolve_data_path("linkfox-keepa-batch-fetch", ts)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(serialized)
        print(f"Saved full response: {out_path} ({len(serialized)} bytes)")
    except OSError as e:
        print(f"Failed to save to {out_path}: {e}", file=sys.stderr)

    # 摘要
    meta = result.get("meta", {})
    print(f"\n=== Keepa Batch Fetch Summary ===")
    print(f"  Total ASINs: {meta.get('total_asins')}")
    print(f"  Success: {meta.get('success')}")
    print(f"  Failed: {meta.get('failed')}")
    if meta.get("failed_asins"):
        print(f"  Failed ASINs: {meta['failed_asins'][:10]}...")
    print(f"  Batches: {meta.get('batches')} (completed: {meta.get('batches_completed', meta.get('batches'))}, remaining: {meta.get('batches_remaining', 0)})")
    print(f"  Cache hits: {meta.get('cached_hits')}")
    if meta.get("stopped_early"):
        print(f"  STOPPED EARLY: {meta.get('stop_reason')}")
        if meta.get("rate_limited"):
            print(f"  >>> 限流冷却: {meta.get('cooldown_sec')}s")
        print(f"  >>> 建议重新执行时间: {meta.get('retry_after', '未知')}")
        print(f"  >>> 已获取 {meta.get('success')}/{meta.get('total_asins')} 个 ASIN，重新执行时缓存命中会跳过已完成的批次")

    if inline:
        print(serialized)


if __name__ == "__main__":
    main()
