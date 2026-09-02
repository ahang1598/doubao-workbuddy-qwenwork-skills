# -*- coding: utf-8 -*-
"""
Risk Index Scraper — 全球地缘风险与市场恐慌指数

数据源:
  1. FRED API — GPR 地缘政治风险指数（Caldara & Iacoviello）、VIXCLS 恐慌指数、
                T10Y2Y 利差、STLFSI 圣路易斯金融压力指数
  2. CBOE 公开数据 — VIX/SKEW（通过 Stooq 备源）
  3. ICE BofA — MOVE 债券波动率指数（FRED：BAMLH0A0HYM2 高收益债利差作为代理）

功能模块:
  1. GPR 地缘政治风险（月度）
  2. VIX 恐慌指数 + SKEW 黑天鹅指数
  3. MOVE 债券波动率（高收益债利差代理）
  4. STLFSI 金融压力指数
  5. 综合：HALO 主题包触发判断

用法:
  python risk_index_scraper.py --all
  python risk_index_scraper.py --gpr
  python risk_index_scraper.py --vix
  python risk_index_scraper.py --bond-vol
  python risk_index_scraper.py --stress
  python risk_index_scraper.py --all --output FinancialData/risk_indices.md
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
import csv
import io
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests is required.", file=sys.stderr)
    sys.exit(1)


TIMEOUT = 25
HEADERS = {"User-Agent": "Mozilla/5.0 AppleWebKit/537.36", "Accept": "*/*"}
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
STOOQ_SKEW = "https://stooq.com/q/d/l/?s=^skew&d1={start}&d2={end}&i=d"

# 关键风险指标
RISK_SERIES = {
    # 地缘风险
    "GPRD":         ("GPR 每日地缘政治风险指数", "指数", "geopolitical"),
    "GPRC_USA":     ("GPR 美国地缘风险", "指数", "geopolitical"),
    # 市场恐慌
    "VIXCLS":       ("CBOE VIX 恐慌指数", "指数", "equity_vol"),
    "VXNCLS":       ("纳斯达克 100 波动率", "指数", "equity_vol"),
    # 债券波动率代理
    "BAMLH0A0HYM2": ("ICE BofA 美国高收益债 OAS 利差", "%", "credit_spread"),
    "BAMLC0A0CM":   ("ICE BofA 美国投资级 OAS 利差", "%", "credit_spread"),
    # 金融压力
    "STLFSI4":      ("圣路易斯金融压力指数", "指数", "stress"),
    "NFCI":         ("芝加哥联储金融条件指数", "指数", "stress"),
}


def _http_get(url, timeout=TIMEOUT):
    return requests.get(url, headers=HEADERS, timeout=timeout)


def fetch_fred_series(series_id, days=365):
    url = FRED_CSV.format(sid=series_id)
    try:
        r = _http_get(url)
        r.raise_for_status()
        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        if len(rows) < 2:
            return []
        out = []
        cutoff = (datetime.now() - timedelta(days=days)).date()
        for row in rows[1:]:
            if len(row) < 2:
                continue
            d_str, v_str = row[0].strip(), row[1].strip()
            if v_str in ("", ".", "NA"):
                continue
            try:
                d = datetime.strptime(d_str, "%Y-%m-%d").date()
                if d < cutoff:
                    continue
                out.append((d, float(v_str)))
            except (ValueError, TypeError):
                continue
        return out
    except Exception as exc:
        print(f"⚠️ FRED {series_id}: {exc}", file=sys.stderr)
        return []


def fetch_category(category, days=365):
    result = {}
    for sid, (name, unit, cat) in RISK_SERIES.items():
        if cat != category:
            continue
        data = fetch_fred_series(sid, days=days)
        if not data:
            continue
        latest_date, latest_val = data[-1]
        week_ago = data[-6][1] if len(data) > 6 else None
        month_ago = data[-22][1] if len(data) > 22 else None
        # 历史百分位（粗略）
        all_vals = [v for _, v in data]
        sorted_vals = sorted(all_vals)
        pct = (sorted_vals.index(latest_val) / len(sorted_vals)) * 100 if sorted_vals else None

        result[sid] = {
            "name": name,
            "unit": unit,
            "latest_date": latest_date.strftime("%Y-%m-%d"),
            "latest": round(latest_val, 3),
            "week_ago": round(week_ago, 3) if week_ago else None,
            "month_ago": round(month_ago, 3) if month_ago else None,
            "delta_30d": round(latest_val - month_ago, 3) if month_ago else None,
            "percentile_1y": round(pct, 1) if pct else None,
        }
    return result


def fetch_skew():
    """CBOE SKEW 指数（黑天鹅警报）— 通过 Stooq 公开 CSV。"""
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
    url = STOOQ_SKEW.format(start=start, end=end)
    try:
        r = _http_get(url)
        r.raise_for_status()
        if "Date" not in r.text[:50]:
            return None
        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        out = []
        for row in rows[1:]:
            if len(row) < 5:
                continue
            try:
                d = datetime.strptime(row[0], "%Y-%m-%d").date()
                close = float(row[4])
                out.append((d, close))
            except (ValueError, TypeError):
                continue
        if not out:
            return None
        latest_date, latest = out[-1]
        week_ago = out[-6][1] if len(out) > 6 else None
        month_ago = out[-22][1] if len(out) > 22 else None
        return {
            "name": "CBOE SKEW 指数（黑天鹅警报）",
            "unit": "指数",
            "latest_date": latest_date.strftime("%Y-%m-%d"),
            "latest": round(latest, 2),
            "week_ago": round(week_ago, 2) if week_ago else None,
            "month_ago": round(month_ago, 2) if month_ago else None,
            "interpretation": ">150 高警戒（黑天鹅风险高）；100-130 正常；<100 极度乐观/反向警报",
        }
    except Exception as exc:
        print(f"⚠️ Stooq SKEW: {exc}", file=sys.stderr)
        return None


def to_markdown(geo, equity_vol, credit, stress, skew_data):
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("# 全球风险与市场恐慌指数\n")
    lines.append(f"**数据采集时间**: {ts}")
    lines.append("📎 **信源API**: FRED CSV API + Stooq SKEW CSV API\n")
    lines.append("---\n")

    sections = [
        ("1. 地缘政治风险（GPR）", geo, "Caldara & Iacoviello 编制，基于全球主流英文媒体地缘事件文本挖掘"),
        ("2. 市场恐慌指数（VIX/VXN）", equity_vol, "VIX>30 显著恐慌；20-30 警觉；<15 自满"),
        ("3. 信用利差（高收益债 / 投资级）", credit, "高收益 OAS >5% = 信用恶化；<3% = 信用宽松"),
        ("4. 金融压力指数", stress, "STLFSI 正值表示压力高于均值，<-1 极度宽松，>1 显著紧缩"),
    ]

    for title, data, hint in sections:
        lines.append(f"## {title}\n")
        if not data:
            lines.append("⚠️ 数据获取失败\n")
            continue
        lines.append(f"> {hint}\n")
        lines.append("| 指标 | 最新值 | 1周前 | 1月前 | 30日变化 | 1年百分位 | 最新日期 |")
        lines.append("|------|-------|-------|-------|---------|----------|---------|")
        for sid, d in data.items():
            arrow = "↑" if d.get("delta_30d") and d["delta_30d"] > 0 else (
                "↓" if d.get("delta_30d") and d["delta_30d"] < 0 else "→")
            lines.append(
                f"| {d['name']} ({sid}) | **{d['latest']}** | "
                f"{d['week_ago'] if d['week_ago'] is not None else '—'} | "
                f"{d['month_ago'] if d['month_ago'] is not None else '—'} | "
                f"{arrow} {d['delta_30d']:+.3f}" if d['delta_30d'] is not None else "—"
                f" | {d.get('percentile_1y', '—')}% | {d['latest_date']} |"
            )
        lines.append("")

    # SKEW
    lines.append("## 5. CBOE SKEW（黑天鹅警报）\n")
    if skew_data:
        lines.append(f"- **最新值**: {skew_data['latest']}（{skew_data['latest_date']}）")
        lines.append(f"- **1 周前**: {skew_data['week_ago']}")
        lines.append(f"- **1 月前**: {skew_data['month_ago']}")
        lines.append(f"- **解读**: {skew_data['interpretation']}")
        lines.append("")
    else:
        lines.append("⚠️ Stooq SKEW 失败，建议用 `web_search 'CBOE SKEW index latest'` 兜底\n")

    # 综合
    lines.append("## 6. 综合研判 — HALO / 不可能三角触发判断\n")
    lines.append("| 主题 / 规则 | 触发条件 | 当前判断 |")
    lines.append("|------------|---------|---------|")
    lines.append("| **HALO 主题包**（重资产/低淘汰率防御） | GPR 月度均值 > 150 + VIX > 25 + 高收益 OAS > 4.5% 三者满足 ≥2 | 见上表 |")
    lines.append("| **不可能三角**（黄金-原油-美元同向涨幅） | 任一指数 30 日涨幅 > 15-20% 触发避险敞口刚性约束 | 见 `gold_market.md` / `eia_energy.md` |")
    lines.append("| **TACO 主题包反向触发**（缓和带来踏空风险） | VIX 从 >30 快速回落至 <20 + GPR 30 日 -20% | 风险偏好修复期减仓避险 |")
    lines.append("| **衰退预警** | STLFSI > 0.5 + NFCI 上行 + 高收益 OAS > 5% | 切换至长久期债 + 必需消费 |")
    lines.append("")

    lines.append("---\n")
    lines.append("## 数据信源\n")
    lines.append("- **FRED Geopolitical Risk Index** — https://www.matteoiacoviello.com/gpr.htm (Caldara & Iacoviello)")
    lines.append("- **FRED VIX/VXN** — CBOE 通过 FRED 镜像")
    lines.append("- **FRED ICE BofA 信用利差** — Bank of America Merrill Lynch 公开 OAS")
    lines.append("- **FRED STLFSI4 / NFCI** — 圣路易斯联储 / 芝加哥联储金融压力指数")
    lines.append("- **Stooq SKEW** — CBOE SKEW 历史日线")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="全球风险与市场恐慌指数采集")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--gpr", action="store_true")
    parser.add_argument("--vix", action="store_true")
    parser.add_argument("--credit", action="store_true")
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--skew", action="store_true")
    parser.add_argument("--output", help="Markdown 输出路径")
    parser.add_argument("--json", help="JSON 数据输出")
    args = parser.parse_args()

    if not any([args.all, args.gpr, args.vix, args.credit, args.stress, args.skew]):
        parser.print_help()
        return 1

    geo = fetch_category("geopolitical") if (args.all or args.gpr) else {}
    equity_vol = fetch_category("equity_vol") if (args.all or args.vix) else {}
    credit = fetch_category("credit_spread") if (args.all or args.credit) else {}
    stress = fetch_category("stress") if (args.all or args.stress) else {}
    skew_data = fetch_skew() if (args.all or args.skew) else None

    md = to_markdown(geo, equity_vol, credit, stress, skew_data)

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
            "geopolitical": geo, "equity_vol": equity_vol, "credit_spread": credit,
            "stress": stress, "skew": skew_data,
            "collected_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"✅ JSON: {json_path}")

    total = sum(len(d) for d in [geo, equity_vol, credit, stress])
    if total == 0 and not skew_data:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
