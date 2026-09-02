#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""置信度校准追踪 — 长期反馈让 agent 真正"学会准"

设计目的（accuracy-uplift v12 · 建议 6）
─────────────────────────────────────────────────────────────────────
1. 每份报告生成后，从正文抽取"置信度"声明，落入累积台账
   `OutputReport/_prediction_ledger.jsonl`（每行一条 JSON）
2. 提供 `review` 子命令：按置信度区间统计实际命中率
   （需要在台账中后续手动/自动回填 outcome=hit|miss）
3. 提供 `extract` 子命令：从报告抽取核心结论 + 置信度并 append 入台账

软门禁性质：抽取失败仅 WARN；review 仅做统计、不阻断任何交付。

台账行结构
─────────────────────────────────────────────────────────────────────
{
  "date": "2026-06-06",
  "report": "OutputReport/交易决策报告_002594_比亚迪_202606062200.md",
  "code": "002594",
  "claim": "6 个月目标价 320 元",
  "confidence": 0.65,
  "horizon_days": 180,
  "verify_date": "2026-12-06",
  "outcome": null,            # "hit" / "miss" / null（待验证）
  "outcome_note": ""
}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

LEDGER_NAME = "_prediction_ledger.jsonl"


def _extract_confidence_claims(text: str) -> List[Tuple[str, float]]:
    """从报告抽取「结论 + 置信度」配对。

    支持的格式：
      置信度 65%
      置信度: 0.65
      置信度（0-100%）: 65%
      综合胜率 65%（兼容旧格式）
    """
    results: List[Tuple[str, float]] = []
    # 模式1：xxx 置信度 NN%
    for m in re.finditer(r"([^\n。；！\?]{8,80}?)[\s\(（]*置信度[\s\)）]*[:：]?\s*(\d{1,3}(?:\.\d+)?)\s*%", text):
        claim = m.group(1).strip().lstrip("📌、，- ")
        conf = float(m.group(2)) / 100.0
        if 0 < conf <= 1:
            results.append((claim[:80], conf))
    # 模式2：xxx 置信度 0.65
    for m in re.finditer(r"([^\n。；！\?]{8,80}?)[\s\(（]*置信度[\s\)）]*[:：]?\s*(0\.\d{1,3})\b", text):
        claim = m.group(1).strip().lstrip("📌、，- ")
        conf = float(m.group(2))
        if 0 < conf <= 1:
            results.append((claim[:80], conf))
    # 去重（按 claim 前 40 字）
    seen = set()
    uniq: List[Tuple[str, float]] = []
    for c, v in results:
        k = c[:40]
        if k not in seen:
            seen.add(k)
            uniq.append((c, v))
    return uniq


def extract_to_ledger(report_path: Path, horizon_days: int = 180) -> List[str]:
    """从报告抽取置信度声明并 append 到台账。返回 WARN 列表。"""
    warns: List[str] = []
    if not report_path.exists():
        warns.append(f"[校准·WARN] 报告不存在: {report_path}")
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")
    pairs = _extract_confidence_claims(text)
    if not pairs:
        warns.append(
            "[校准·WARN] 报告中未发现任何「结论 + 置信度」配对。"
            "建议 6 要求每个核心结论附 0-100% 置信度。"
        )
        return warns

    # 从文件名提取 code
    m = re.search(r"_(\d{6})_", report_path.name)
    code = m.group(1) if m else "?"
    today = datetime.now()
    verify_date = (today + timedelta(days=horizon_days)).strftime("%Y-%m-%d")

    ledger_path = report_path.parent / LEDGER_NAME
    with ledger_path.open("a", encoding="utf-8") as fh:
        for claim, conf in pairs:
            row = {
                "date": today.strftime("%Y-%m-%d"),
                "report": str(report_path),
                "code": code,
                "claim": claim,
                "confidence": round(conf, 3),
                "horizon_days": horizon_days,
                "verify_date": verify_date,
                "outcome": None,
                "outcome_note": "",
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return warns


def review_calibration(ledger_path: Path) -> Dict:
    """按置信度区间统计命中率。"""
    if not ledger_path.exists():
        return {"error": f"台账不存在: {ledger_path}", "buckets": {}}
    rows: List[dict] = []
    with ledger_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    # 分桶
    buckets = {
        "0-30%": [], "30-50%": [], "50-60%": [], "60-70%": [], "70-80%": [], "80-90%": [], "90-100%": [],
    }
    for r in rows:
        c = r.get("confidence")
        if c is None:
            continue
        c = float(c)
        if c < 0.3:
            key = "0-30%"
        elif c < 0.5:
            key = "30-50%"
        elif c < 0.6:
            key = "50-60%"
        elif c < 0.7:
            key = "60-70%"
        elif c < 0.8:
            key = "70-80%"
        elif c < 0.9:
            key = "80-90%"
        else:
            key = "90-100%"
        buckets[key].append(r)

    summary = {}
    for k, lst in buckets.items():
        verified = [x for x in lst if x.get("outcome") in ("hit", "miss")]
        hit = [x for x in verified if x["outcome"] == "hit"]
        summary[k] = {
            "total": len(lst),
            "verified": len(verified),
            "hit": len(hit),
            "hit_rate": (len(hit) / len(verified)) if verified else None,
        }
    return {"buckets": summary, "total_rows": len(rows)}


def validate_calibration(report_path: Path) -> List[str]:
    """供 report_quality_checker.py 调用：检测正文有无置信度声明。"""
    warns: List[str] = []
    if not report_path.exists():
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")
    pairs = _extract_confidence_claims(text)
    if not pairs:
        warns.append(
            "[校准·WARN] 正文未检测到「结论 + 置信度（0-100%）」配对。"
            "建议 6 要求每个核心结论附置信度，便于长期校准追踪。"
            "建议格式：「📌 结论：6 个月目标价 320 元（置信度 65%）」"
        )
    return warns


def record_warn_count(report_path: Path, warn_count: int, note: str = "") -> None:
    """P0-7：把本次报告的软门禁 WARN 总数写入台账（便于跨报告追踪质量趋势）。

    台账行（type=gate_warn）：
      {"type":"gate_warn","date":...,"report":...,"code":...,
       "warn_count":N,"note":...}
    """
    ledger_path = report_path.parent / LEDGER_NAME
    m = re.search(r"_(\d{6})_", report_path.name)
    code = m.group(1) if m else "?"
    row = {
        "type": "gate_warn",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "report": str(report_path),
        "code": code,
        "warn_count": int(warn_count),
        "note": note,
    }
    try:
        with ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def warn_trend(ledger_path: Path, code: Optional[str] = None) -> Dict:
    """P0-7：统计软门禁 WARN 的历史趋势（可按 code 过滤）。"""
    if not ledger_path.exists():
        return {"error": f"台账不存在: {ledger_path}", "records": []}
    records: List[dict] = []
    with ledger_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("type") != "gate_warn":
                continue
            if code and r.get("code") != code:
                continue
            records.append(r)
    counts = [r.get("warn_count", 0) for r in records]
    return {
        "records": records[-20:],
        "n": len(records),
        "avg_warn": round(sum(counts) / len(counts), 2) if counts else None,
        "max_warn": max(counts) if counts else None,
        "latest_warn": counts[-1] if counts else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="置信度校准追踪")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_ext = sub.add_parser("extract", help="从报告抽取置信度并 append 到台账")
    p_ext.add_argument("report", help="报告 Markdown 路径")
    p_ext.add_argument("--horizon-days", type=int, default=180)
    p_rev = sub.add_parser("review", help="按置信度区间统计命中率")
    p_rev.add_argument("--ledger", default="OutputReport/_prediction_ledger.jsonl")
    p_chk = sub.add_parser("check", help="软门禁：检测报告是否含置信度声明")
    p_chk.add_argument("report", help="报告 Markdown 路径")
    p_trend = sub.add_parser("trend", help="统计软门禁 WARN 历史趋势")
    p_trend.add_argument("--ledger", default="OutputReport/_prediction_ledger.jsonl")
    p_trend.add_argument("--code", default=None)
    args = parser.parse_args()

    if args.cmd == "extract":
        warns = extract_to_ledger(Path(args.report), args.horizon_days)
        if warns:
            for w in warns:
                print(w)
            sys.exit(0)
        else:
            print(f"✅ 置信度抽取完成，已 append 至台账")
    elif args.cmd == "review":
        result = review_calibration(Path(args.ledger))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "check":
        warns = validate_calibration(Path(args.report))
        if warns:
            for w in warns:
                print(w)
        else:
            print("✅ 置信度软门禁 PASS")
    elif args.cmd == "trend":
        result = warn_trend(Path(args.ledger), args.code)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
