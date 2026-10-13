#!/usr/bin/env python3
"""
A股个股数据采集脚本 — justice-plutus v1.0
通过免费公开接口获取股票行情、基本面和近期新闻，供 Agent 分析使用。
无需任何 API Key，可直接运行。
"""

import json
import sys
import urllib.request
import urllib.error
import re
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))


def fetch_sina_realtime(code: str) -> dict:
    """通过新浪财经获取实时行情"""
    prefix = "sh" if code.startswith("6") else "sz"
    url = f"https://hq.sinajs.cn/list={prefix}{code}"
    req = urllib.request.Request(url, headers={
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("gbk")
        parts = raw.split('"')[1].split(",")
        if len(parts) < 32:
            return {"error": f"无效代码或无数据: {code}"}
        return {
            "code": code,
            "name": parts[0],
            "open": parts[1],
            "prev_close": parts[2],
            "price": parts[3],
            "high": parts[4],
            "low": parts[5],
            "volume": f"{int(parts[8]) / 10000:.0f}万手",
            "amount": f"{float(parts[9]) / 1e8:.2f}亿",
            "change_pct": f"{(float(parts[3]) - float(parts[2])) / float(parts[2]) * 100:.2f}%",
            "date": parts[30],
            "time": parts[31],
        }
    except Exception as e:
        return {"error": f"获取 {code} 行情失败: {e}"}


def fetch_sina_kline(code: str, days: int = 60) -> list:
    """通过新浪财经获取近N日日K线数据"""
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}{code}"
    url = (
        f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        f"CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={days}"
    )
    try:
        req = urllib.request.Request(url, headers={
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
        # 新浪返回的是 JSON 数组
        data = json.loads(raw)
        result = []
        for item in data:
            result.append({
                "date": item.get("day", ""),
                "open": item.get("open", ""),
                "close": item.get("close", ""),
                "high": item.get("high", ""),
                "low": item.get("low", ""),
                "volume": item.get("volume", ""),
                "amount": str(float(item.get("volume", 0)) * float(item.get("close", 1))),
            })
        return result
    except Exception as e:
        return [{"error": f"获取K线失败: {e}"}]


def compute_technicals(klines: list) -> dict:
    """基于日K线计算简单技术指标"""
    if not klines or "error" in klines[0]:
        return {"error": "无K线数据，无法计算指标"}

    closes = [float(k["close"]) for k in klines]
    volumes = [int(k["volume"]) for k in klines]

    def ma(data, n):
        if len(data) < n:
            return None
        return sum(data[-n:]) / n

    latest = closes[-1]
    ma5 = ma(closes, 5)
    ma10 = ma(closes, 10)
    ma20 = ma(closes, 20)
    ma60 = ma(closes, 60)
    vol_ma5 = ma(volumes, 5)

    # 近5日涨跌幅
    if len(closes) >= 6:
        pct_5d = (closes[-1] / closes[-6] - 1) * 100
    else:
        pct_5d = None

    # 近20日涨跌幅
    if len(closes) >= 21:
        pct_20d = (closes[-1] / closes[-21] - 1) * 100
    else:
        pct_20d = None

    # 近60日最高/最低
    high_60 = max(float(k["high"]) for k in klines[-60:]) if len(klines) >= 60 else max(float(k["high"]) for k in klines)
    low_60 = min(float(k["low"]) for k in klines[-60:]) if len(klines) >= 60 else min(float(k["low"]) for k in klines)

    return {
        "latest_close": latest,
        "MA5": round(ma5, 3) if ma5 else None,
        "MA10": round(ma10, 3) if ma10 else None,
        "MA20": round(ma20, 3) if ma20 else None,
        "MA60": round(ma60, 3) if ma60 else None,
        "vol_MA5": int(vol_ma5) if vol_ma5 else None,
        "latest_volume": volumes[-1],
        "pct_5d": f"{pct_5d:.2f}%" if pct_5d is not None else None,
        "pct_20d": f"{pct_20d:.2f}%" if pct_20d is not None else None,
        "high_60d": high_60,
        "low_60d": low_60,
        "position_60d": f"{(latest - low_60) / (high_60 - low_60) * 100:.1f}%" if high_60 != low_60 else "N/A",
    }


def fetch_stock_data(code: str) -> dict:
    """汇总获取单只股票的全部数据"""
    result = {"code": code, "fetch_time": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")}

    # 实时行情
    result["realtime"] = fetch_sina_realtime(code)

    # 日K线
    klines = fetch_sina_kline(code, 60)
    result["klines_60d"] = klines

    # 技术指标
    result["technicals"] = compute_technicals(klines)

    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python fetch_data.py <股票代码1> [代码2] [代码3] ...")
        print("示例: python fetch_data.py 600519 000858 300750")
        sys.exit(1)

    codes = sys.argv[1:]
    # 验证代码格式
    for c in codes:
        if not re.match(r'^\d{6}$', c):
            print(json.dumps({"error": f"无效代码格式: {c}，需要6位数字"}, ensure_ascii=False))
            sys.exit(1)

    all_data = {}
    for code in codes:
        print(f"[采集] {code} ...", file=sys.stderr)
        all_data[code] = fetch_stock_data(code)

    # 输出 JSON 结果
    print(json.dumps(all_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
