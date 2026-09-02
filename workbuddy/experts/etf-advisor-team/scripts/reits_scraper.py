# -*- coding: utf-8 -*-
"""
REITs Scraper — 公募 REITs 行情池

数据源:
  1. 东财 datacenter REIT 列表 API — 全部 50+ 只公募 REITs 行情
  2. 集思录 REITs 列表（备源 — web_fetch 兜底）
  3. 上交所 / 深交所 REITs 专区（公告与项目细节）

功能模块:
  1. 全市场公募 REITs 列表（代码 / 名称 / 类型 / 规模 / 涨跌 / 估值）
  2. 按底层资产分类（产权类：产业园 / 仓储物流 / 保租房；
     特许经营权类：高速公路 / 能源 / 生态环保）
  3. 二级市场表现 + 折溢价
  4. 大财政 + REITs 主题包配置建议

用法:
  python reits_scraper.py --all
  python reits_scraper.py --list
  python reits_scraper.py --by-type
  python reits_scraper.py --all --output FinancialData/reits_market.md
"""

# --- UTF-8 bootstrap (auto-injected, idempotent) ---
import os as _bootstrap_os, sys as _bootstrap_sys
_bootstrap_dir = _bootstrap_os.path.dirname(_bootstrap_os.path.abspath(__file__))
if _bootstrap_dir not in _bootstrap_sys.path:
    _bootstrap_sys.path.insert(0, _bootstrap_dir)
try:
    from _utf8_bootstrap import enable_utf8_io as _bootstrap_enable
    _bootstrap_enable()
except Exception:
    pass
# --- end UTF-8 bootstrap ---


import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests is required.", file=sys.stderr)
    sys.exit(1)


TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json",
}

# 东财 push2 公募 REITs 全市场行情接口
# 板块代码 m:1+t:9+e:97（深市 REIT）+ m:0+t:23（沪市 REIT）
# 实际东财 REIT 板块 secid 为 b:MK0710（公募 REITs 板块）
EM_REITS_URL = ("https://push2.eastmoney.com/api/qt/clist/get?"
                "fs=b%3AMK0710&"
                "fields=f12,f14,f2,f3,f4,f5,f6,f17,f15,f16,f18,f7,f8,f9,f23,f10,f100,f124&"
                "fid=f3&po=1&pz=200&pn=1")

# 备选：直接按市场过滤（沪 m:1 / 深 m:0，类型 t:1+s:fb 闭式基金）
EM_REITS_FALLBACK = ("https://push2.eastmoney.com/api/qt/clist/get?"
                     "fs=m%3A1%2Bs%3A0%2Bt%3A23%2Cm%3A0%2Bs%3A0%2Bt%3A23&"
                     "fields=f12,f14,f2,f3,f4,f5,f6&fid=f3&po=1&pz=200&pn=1")


def _http_get(url, timeout=TIMEOUT):
    return requests.get(url, headers=HEADERS, timeout=timeout)


def fetch_reits_list():
    """全市场公募 REITs 行情。"""
    for url in [EM_REITS_URL, EM_REITS_FALLBACK]:
        try:
            r = _http_get(url)
            r.raise_for_status()
            data = r.json()
            rows = data.get("data", {}).get("diff", []) if isinstance(data, dict) else []
            if rows:
                # 字段：f12=代码 f14=名称 f2=最新价 f3=涨跌幅 f4=涨跌额
                # f5=成交量 f6=成交额 f15=最高 f16=最低 f17=今开 f18=昨收
                # f7=振幅 f8=换手率 f23=PB 估值 f10=量比
                return [{
                    "code": x.get("f12"),
                    "name": x.get("f14"),
                    "latest": x.get("f2"),
                    "change_pct": x.get("f3"),
                    "change_amt": x.get("f4"),
                    "volume": x.get("f5"),
                    "amount_yi": (x.get("f6", 0) / 1e8) if x.get("f6") else None,
                    "high": x.get("f15"),
                    "low": x.get("f16"),
                    "open": x.get("f17"),
                    "prev_close": x.get("f18"),
                    "amplitude": x.get("f7"),
                    "turnover_pct": x.get("f8"),
                    "pb": x.get("f23"),
                    "volume_ratio": x.get("f10"),
                } for x in rows]
        except Exception as exc:
            print(f"⚠️ {url[:60]}: {exc}", file=sys.stderr)
            continue
    return None


def classify_reits(reits_list):
    """根据名称粗分类。"""
    if not reits_list:
        return {}

    categories = {
        "产业园": [],          # 产权类
        "仓储物流": [],
        "保租房": [],          # 保障性租赁住房
        "消费基础设施": [],    # 购物中心 / 消费类
        "高速公路": [],        # 特许经营权类
        "能源": [],            # 风电 / 光伏 / 水电
        "生态环保": [],        # 污水/垃圾处理
        "其他": [],
    }

    for r in reits_list:
        name = str(r.get("name", ""))
        if any(k in name for k in ["产业园", "科技园", "园区", "REIT-产园"]):
            categories["产业园"].append(r)
        elif any(k in name for k in ["仓储", "物流", "REIT-仓储"]):
            categories["仓储物流"].append(r)
        elif any(k in name for k in ["保租", "租赁", "REIT-租住"]):
            categories["保租房"].append(r)
        elif any(k in name for k in ["消费", "购物", "百货", "REIT-消费"]):
            categories["消费基础设施"].append(r)
        elif any(k in name for k in ["高速", "公路", "REIT-公路"]):
            categories["高速公路"].append(r)
        elif any(k in name for k in ["风电", "光伏", "水电", "电力", "新能源", "REIT-清洁能源"]):
            categories["能源"].append(r)
        elif any(k in name for k in ["环保", "水务", "污水", "垃圾"]):
            categories["生态环保"].append(r)
        else:
            categories["其他"].append(r)

    return categories


def to_markdown(reits, by_type):
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("# 公募 REITs 行情池\n")
    lines.append(f"**数据采集时间**: {ts}")
    lines.append("📎 **信源API**: 东财 push2 公募 REITs 板块 API (b:MK0710)\n")
    lines.append("---\n")

    if not reits:
        lines.append("⚠️ 公募 REITs 数据获取失败（非交易时段返回空 / 板块代码失效）\n")
        lines.append("**兜底**: `web_fetch('https://www.jisilu.cn/data/cnreit/', '提取全部公募 REITs 列表')`")
        return "\n".join(lines)

    lines.append(f"## 1. 全市场总览\n")
    lines.append(f"- **REITs 总数**: {len(reits)} 只")
    lines.append("")

    # 涨幅榜前 10
    sorted_up = sorted(reits, key=lambda x: x.get("change_pct") or -999, reverse=True)[:10]
    lines.append("### 涨幅榜 TOP 10\n")
    lines.append("| # | 代码 | 名称 | 最新价 | 涨跌幅 | 成交额(亿) | 换手率 | PB |")
    lines.append("|---|------|------|-------|--------|-----------|-------|-----|")
    for i, x in enumerate(sorted_up, 1):
        amt = f"{x['amount_yi']:.2f}" if x.get("amount_yi") is not None else "—"
        lines.append(
            f"| {i} | {x['code']} | {x['name']} | {x['latest']} | "
            f"{x['change_pct']}% | {amt} | "
            f"{x.get('turnover_pct', '—')}% | {x.get('pb', '—')} |"
        )
    lines.append("")

    # 跌幅榜前 10
    sorted_down = sorted(reits, key=lambda x: x.get("change_pct") or 999)[:10]
    lines.append("### 跌幅榜 TOP 10\n")
    lines.append("| # | 代码 | 名称 | 最新价 | 涨跌幅 | 成交额(亿) | 换手率 | PB |")
    lines.append("|---|------|------|-------|--------|-----------|-------|-----|")
    for i, x in enumerate(sorted_down, 1):
        amt = f"{x['amount_yi']:.2f}" if x.get("amount_yi") is not None else "—"
        lines.append(
            f"| {i} | {x['code']} | {x['name']} | {x['latest']} | "
            f"{x['change_pct']}% | {amt} | "
            f"{x.get('turnover_pct', '—')}% | {x.get('pb', '—')} |"
        )
    lines.append("")

    # 按底层资产分类
    lines.append("## 2. 按底层资产类型分类\n")
    if by_type:
        for cat, items in by_type.items():
            if not items:
                continue
            lines.append(f"### {cat}（{len(items)} 只）\n")
            lines.append("| 代码 | 名称 | 最新价 | 涨跌幅 | 成交额(亿) | PB |")
            lines.append("|------|------|-------|--------|-----------|-----|")
            for x in items[:15]:  # 每类最多展示 15 只
                amt = f"{x['amount_yi']:.2f}" if x.get("amount_yi") is not None else "—"
                lines.append(
                    f"| {x['code']} | {x['name']} | {x['latest']} | "
                    f"{x['change_pct']}% | {amt} | {x.get('pb', '—')} |"
                )
            lines.append("")

    # 主题判断
    lines.append("## 3. 大财政 + REITs 主题包配置建议\n")
    lines.append("| 类型 | 主题角色 | 触发条件 | 权重建议 |")
    lines.append("|------|---------|---------|---------|")
    lines.append("| 产业园 / 仓储物流（产权类） | 经济复苏 + 实物租金弹性 | 工业企业利润同比转正 + 出租率 >85% | 30-40% |")
    lines.append("| 保租房 | 政策红利 + 稳定现金流 | 一线租金同比 +3% 持续 | 15-20% |")
    lines.append("| 消费基础设施 | 消费修复弹性 | 社零同比 >5% + 客流恢复至 2019 同期 | 10-15% |")
    lines.append("| 高速公路（特许经营权） | 类债型防御 + 大财政基建 | 长端利率下行至 1.8% 以下 | 15-20% |")
    lines.append("| 能源（风光水电） | 双碳政策 + ESG 偏好 | 电价稳定 + 国补到位 | 10-15% |")
    lines.append("| 生态环保 | 政策稳定 + 弱周期 | 防御配置 | 5-10% |")
    lines.append("")
    lines.append("**REITs 主题包整体触发条件**：")
    lines.append("- 长端国债收益率 ↓ 至 1.8% 以下（增强类债资产相对吸引力）")
    lines.append("- 中证 REITs 指数 PB 分位 < 30%")
    lines.append("- 大财政发力（专项债前置 + 基建实物量回升）")
    lines.append("- 三者满足 ≥2 → REITs 主题包权重 8-12%")
    lines.append("")

    lines.append("---\n")
    lines.append("## 数据信源\n")
    lines.append("- **东财 push2 公募 REITs 板块 API** — https://push2.eastmoney.com/api/qt/clist/get (b:MK0710)")
    lines.append("- **集思录 REITs 数据**（备源） — https://www.jisilu.cn/data/cnreit/")
    lines.append("- **上交所 REITs 专区** — https://reits.sse.com.cn/")
    lines.append("- **深交所 REITs 专区** — https://reits.szse.cn/")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="公募 REITs 行情池采集")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--by-type", action="store_true")
    parser.add_argument("--output", help="Markdown 输出路径")
    parser.add_argument("--json", help="JSON 数据输出")
    args = parser.parse_args()

    if not any([args.all, args.list, args.by_type]):
        parser.print_help()
        return 1

    reits = fetch_reits_list() if (args.all or args.list or args.by_type) else None
    by_type = classify_reits(reits) if (args.all or args.by_type) and reits else {}

    md = to_markdown(reits, by_type)

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"✅ 输出: {out_path}")
    else:
        print(md)

    if args.json:
        json_path = Path(args.json).resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps({
            "reits_list": reits, "by_type": by_type,
            "collected_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"✅ JSON: {json_path}")

    if not reits:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
