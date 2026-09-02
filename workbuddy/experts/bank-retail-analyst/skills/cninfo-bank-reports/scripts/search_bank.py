#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索巨潮资讯网上的银行股票信息
用法: python3 search_bank.py --name "某某银行"
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.cninfo.com.cn/",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

# 常见上市银行信息（通过官方接口获取的真实 orgId）
KNOWN_BANKS = {
    "工商银行":       {"stock_code": "601398", "org_id": "jjxt0000019",  "plate": "sse"},
    "中国工商银行":   {"stock_code": "601398", "org_id": "jjxt0000019",  "plate": "sse"},
    "建设银行":       {"stock_code": "601939", "org_id": "9900003682",   "plate": "sse"},
    "中国建设银行":   {"stock_code": "601939", "org_id": "9900003682",   "plate": "sse"},
    "农业银行":       {"stock_code": "601288", "org_id": "jjxt0000020",  "plate": "sse"},
    "中国农业银行":   {"stock_code": "601288", "org_id": "jjxt0000020",  "plate": "sse"},
    "中国银行":       {"stock_code": "601988", "org_id": "jjxt0000028",  "plate": "sse"},
    "交通银行":       {"stock_code": "601328", "org_id": "9900002841",   "plate": "sse"},
    "招商银行":       {"stock_code": "600036", "org_id": "gssh0600036",  "plate": "sse"},
    "浦发银行":       {"stock_code": "600000", "org_id": "gssh0600000",  "plate": "sse"},
    "上海浦东发展银行":{"stock_code": "600000", "org_id": "gssh0600000",  "plate": "sse"},
    "中信银行":       {"stock_code": "601998", "org_id": "9900002721",   "plate": "sse"},
    "光大银行":       {"stock_code": "601818", "org_id": "9900006246",   "plate": "sse"},
    "中国光大银行":   {"stock_code": "601818", "org_id": "9900006246",   "plate": "sse"},
    "华夏银行":       {"stock_code": "600015", "org_id": "gssh0600015",  "plate": "sse"},
    "民生银行":       {"stock_code": "600016", "org_id": "gssh0600016",  "plate": "sse"},
    "中国民生银行":   {"stock_code": "600016", "org_id": "gssh0600016",  "plate": "sse"},
    "平安银行":       {"stock_code": "000001", "org_id": "gssz0000001",  "plate": "szse"},
    "兴业银行":       {"stock_code": "601166", "org_id": "9900002081",   "plate": "sse"},
    "北京银行":       {"stock_code": "601169", "org_id": "9900003642",   "plate": "sse"},
    "南京银行":       {"stock_code": "601009", "org_id": "9900003284",   "plate": "sse"},
    "宁波银行":       {"stock_code": "002142", "org_id": "9900003281",   "plate": "szse"},
    "江苏银行":       {"stock_code": "600919", "org_id": "9900006248",   "plate": "sse"},
    "上海银行":       {"stock_code": "601229", "org_id": "9900010207",   "plate": "sse"},
    "邮储银行":       {"stock_code": "601658", "org_id": "9900005091",   "plate": "sse"},
    "中国邮政储蓄银行":{"stock_code": "601658", "org_id": "9900005091",  "plate": "sse"},
    "杭州银行":       {"stock_code": "600926", "org_id": "9900006251",   "plate": "sse"},
    "成都银行":       {"stock_code": "601838", "org_id": "9900021318",   "plate": "sse"},
    "长沙银行":       {"stock_code": "601577", "org_id": "9900021960",   "plate": "sse"},
}


def search_cninfo(keyword):
    """通过巨潮资讯搜索接口查询股票信息（返回真实 orgId）"""
    url = "https://www.cninfo.com.cn/new/information/topSearch/query"
    data = urllib.parse.urlencode({
        "keyWord": keyword,
        "maxNum": 10,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None


def guess_plate(stock_code):
    """根据股票代码推断上市市场"""
    code = str(stock_code).lstrip("0")
    if stock_code.startswith("6") or stock_code.startswith("11"):
        return "sse"
    elif stock_code.startswith("0") or stock_code.startswith("3") or stock_code.startswith("2"):
        return "szse"
    elif len(stock_code) == 5 and stock_code.startswith("0"):
        return "hk"
    return "sse"


def find_bank(name):
    """查找银行信息：优先本地知识库，其次在线搜索"""
    # 1. 精确匹配本地知识库
    if name in KNOWN_BANKS:
        info = KNOWN_BANKS[name].copy()
        info["bank_name"] = name
        _print_info(name, info, "本地库")
        return info

    # 2. 模糊匹配本地知识库（包含匹配）
    for bank_name, info in KNOWN_BANKS.items():
        if name in bank_name or bank_name in name:
            result = info.copy()
            result["bank_name"] = bank_name
            _print_info(f"{bank_name}（匹配输入：{name}）", result, "本地库")
            return result

    # 3. 在线搜索巨潮资讯
    print(f"[在线搜索] 正在巨潮资讯查询: {name} ...")
    raw = search_cninfo(name)

    if raw and isinstance(raw, list) and len(raw) > 0:
        # 优先取A股
        a_stocks = [r for r in raw if r.get("category") == "A股"]
        candidates = a_stocks if a_stocks else raw

        if candidates:
            item = candidates[0]
            stock_code = item.get("code", "")
            org_id = item.get("orgId", "")
            short_name = item.get("zwjc", name)
            plate = guess_plate(stock_code)

            info = {
                "stock_code": stock_code,
                "org_id": org_id,
                "plate": plate,
                "bank_name": short_name,
            }
            _print_info(short_name, info, "在线搜索")

            if len(candidates) > 1:
                print(f"\n  其他候选（共{len(candidates)}个）:")
                for c in candidates[1:4]:
                    print(f"    - {c.get('zwjc','')}: code={c.get('code','')}, "
                          f"orgId={c.get('orgId','')}, 市场={c.get('category','')}")
            return info

    print(f"[错误] 未找到银行: {name}")
    print("请手动指定 --stock-code 和 --org-id 参数")
    print("\n常见银行参考:")
    for bname, binfo in list(KNOWN_BANKS.items())[:10]:
        print(f"  {bname}: code={binfo['stock_code']}, orgId={binfo['org_id']}")
    return None


def _print_info(name, info, source=""):
    plate_label = {"sse": "上交所(sse)", "szse": "深交所(szse)", "hk": "港交所(hk)"}
    prefix = f"[{source}] " if source else ""
    print(f"{prefix}找到银行: {name}")
    print(f"  股票代码: {info['stock_code']}")
    print(f"  orgId:    {info['org_id']}")
    print(f"  市场:     {plate_label.get(info['plate'], info['plate'])}")


def main():
    parser = argparse.ArgumentParser(
        description="搜索巨潮资讯网上市银行信息",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 search_bank.py --name "某某银行"
  python3 search_bank.py --name "某某银行"
  python3 search_bank.py --name "某某银行" --json
        """
    )
    parser.add_argument("--name", "-n", required=True, help="银行名称，如'某某银行'")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出结果")

    args = parser.parse_args()

    info = find_bank(args.name)
    if info is None:
        sys.exit(1)

    if args.json:
        print("\n=== JSON_OUTPUT_START ===")
        print(json.dumps(info, ensure_ascii=False, indent=2))
        print("=== JSON_OUTPUT_END ===")


if __name__ == "__main__":
    main()
