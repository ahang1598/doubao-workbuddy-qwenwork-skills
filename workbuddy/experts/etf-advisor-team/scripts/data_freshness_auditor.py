#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""数据时效审计器 — 对抗「用过期数据下今天的判断」

设计目的（accuracy-uplift v13 · P2-8）
─────────────────────────────────────────────────────────────────────
门禁原本只校验「信源文件是否存在」，不校验数据是否过期。行情/资金/筹码
类数据时效性极强，财报/行业类数据也有保鲜期。本审计扫描 FinancialData
下该 code 的 JSON 文件，解析时间戳，按文件类别套用不同的过期阈值。

时间字段兼容（按优先级）
─────────────────────────────────────────────────────────────────────
fetch_time / fetched_at / metadata.fetched_at / metadata.fetch_time /
update_time / updated_at / date / 采集时间 / 更新时间

类别阈值（距今天数）
─────────────────────────────────────────────────────────────────────
行情/资金/筹码/龙虎榜（quote/realtime/fund_flow/chip/longhu/margin/north）: 7 天
一致预期/研报/机构（consensus/analyst/institution/report）              : 90 天
财报/基本面/资产质量（fundamental/asset_quality/financ/historical）     : 180 天
行业/板块（industry/sector）                                            : 365 天
默认                                                                    : 180 天

软门禁性质：只 WARN，不阻断。无时间戳的文件跳过（不误报）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TIME_KEYS = [
    "fetch_time", "fetched_at", "fetch_at", "update_time", "updated_at",
    "date", "采集时间", "更新时间", "时间",
]

# (关键词列表, 阈值天数, 类别名)
CATEGORY_RULES = [
    (["quote", "realtime", "fund_flow", "chip", "longhu", "longhubang", "margin",
      "northbound", "securities_lending", "volume_price", "capital_tide", "pytdx", "tick"], 7, "行情/资金/筹码"),
    (["consensus", "analyst", "institution_holding", "report_page", "earnings"], 90, "一致预期/研报/机构"),
    (["fundamental", "asset_quality", "financ", "historical", "worksheet", "projection",
      "assumption", "three_statement"], 180, "财报/基本面"),
    (["industry", "sector"], 365, "行业/板块"),
]
DEFAULT_THRESHOLD = 180


def _find_financial_data_dir() -> Optional[Path]:
    here = Path(__file__).resolve()
    for up in (3, 2, 4):
        if up < len(here.parents):
            cand = here.parents[up] / "FinancialData"
            if cand.is_dir():
                return cand
    cwd_cand = Path.cwd() / "FinancialData"
    return cwd_cand if cwd_cand.is_dir() else None


def _extract_code(report_path: Path) -> Optional[str]:
    m = re.search(r"_(\d{6})_", report_path.name)
    return m.group(1) if m else None


def _parse_dt(s: str) -> Optional[datetime]:
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s[:len(fmt) + 4], fmt)
        except Exception:
            continue
    m = re.search(r"(20\d{2})[-/]?(\d{1,2})[-/]?(\d{1,2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            return None
    return None


def _find_timestamp(obj) -> Optional[datetime]:
    """从 JSON 对象（dict/嵌套）中按优先级找时间字段。"""
    if isinstance(obj, dict):
        # 先查 metadata 子对象
        meta = obj.get("metadata")
        if isinstance(meta, dict):
            for k in TIME_KEYS:
                if k in meta and meta[k]:
                    dt = _parse_dt(meta[k])
                    if dt:
                        return dt
        for k in TIME_KEYS:
            if k in obj and obj[k]:
                dt = _parse_dt(obj[k])
                if dt:
                    return dt
        # 递归一层常见包裹键
        for wrap in ("consensus_forecast", "summary", "data", "result"):
            if wrap in obj and isinstance(obj[wrap], dict):
                dt = _find_timestamp(obj[wrap])
                if dt:
                    return dt
    return None


def _threshold_for(filename: str) -> tuple:
    low = filename.lower()
    for keywords, days, label in CATEGORY_RULES:
        if any(kw in low for kw in keywords):
            return days, label
    return DEFAULT_THRESHOLD, "默认"


def audit_data_freshness(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        return warns
    code = _extract_code(report_path)
    if not code:
        return warns
    fd_dir = _find_financial_data_dir()
    if not fd_dir:
        return warns

    now = datetime.now()
    stale: List[tuple] = []
    for jf in sorted(fd_dir.glob(f"{code}_*.json")):
        try:
            obj = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        dt = _find_timestamp(obj)
        if not dt:
            continue  # 无时间戳，不误报
        age = (now - dt).days
        if age < 0:
            continue
        threshold, label = _threshold_for(jf.name)
        if age > threshold:
            stale.append((jf.name, age, threshold, label))

    if stale:
        # 按超期严重度排序
        stale.sort(key=lambda x: x[1] - x[2], reverse=True)
        detail = "；".join(f"{n}（{label}·{age}天>{thr}天）" for n, age, thr, label in stale[:8])
        more = f"，另 {len(stale) - 8} 项" if len(stale) > 8 else ""
        warns.append(
            f"[数据时效·WARN] 检测到 {len(stale)} 项信源数据超过保鲜期：{detail}{more}。"
            "时效性强的数据（行情/资金/筹码）过期会直接误导择时与结论，建议在下结论前重新采集。"
        )
    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="数据时效审计器（P2-8）")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = audit_data_freshness(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 数据时效审计 PASS: {report_path.name}")
        else:
            print(f"⚠️ 数据时效审计 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
