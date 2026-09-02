#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""信源-引用交叉审计器 — 对抗「脚本产出 vs 报告引用」数字串台

设计目的（accuracy-uplift v13 · P0-6）
─────────────────────────────────────────────────────────────────────
基本面双门禁的 R7 只在基本面报告生效；但汇总决策报告同样引用脚本产出
的核心数字（EPS / 营收 / 净利润 / ROE），历史上发生过把
consensus.json 里 EPS=20.85 误引成 13.5 的事故。本审计把「原始数据
JSON ↔ 报告正文引用值」的一致性校验扩展到所有报告模式。

数据源（按 code 自动从 FinancialData 加载）
─────────────────────────────────────────────────────────────────────
- {code}_consensus.json  : consensus_forecast.data[] 各年度
    一致预期EPS(元) / 一致预期营收(亿) / 一致预期净利润(亿) / ROE(%)

校验逻辑
─────────────────────────────────────────────────────────────────────
对每个关键指标：抽取 consensus 各年度值集合，在报告正文中找到该指标
的引用数字；若报告引用了该指标却没有任何一处落在 consensus 任一年度
值 ±TOLERANCE 内 → WARN（可能引用错误，或与一致预期重大分歧未说明）。

容差：EPS 8%、营收 8%、净利润 8%、ROE 2pct。

软门禁性质：只 WARN，不阻断。数据缺失仅给提示性 WARN，不抛异常。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _find_financial_data_dir() -> Optional[Path]:
    """定位工作区根目录下的 FinancialData（唯一存放位置）。"""
    here = Path(__file__).resolve()
    # scripts -> 插件目录 -> 上级目录（逐层向上探测工作区根）
    for up in (3, 2, 4):
        cand = here.parents[up] / "FinancialData" if up < len(here.parents) else None
        if cand and cand.is_dir():
            return cand
    cwd_cand = Path.cwd() / "FinancialData"
    if cwd_cand.is_dir():
        return cwd_cand
    return None


def _extract_code(report_path: Path) -> Optional[str]:
    m = re.search(r"_(\d{6})_", report_path.name)
    return m.group(1) if m else None


def _load_consensus(fd_dir: Path, code: str) -> Optional[dict]:
    p = fd_dir / f"{code}_consensus.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _report_numbers_near(text: str, keyword_patterns: List[str], unit_re: str) -> List[float]:
    """在 keyword 附近 30 字内抓取带 unit 的数字。"""
    vals: List[float] = []
    num_unit = re.compile(r"(\d{1,5}(?:\.\d{1,2})?)\s*(?:" + unit_re + r")")
    for kp in keyword_patterns:
        for km in re.finditer(kp, text):
            window = text[km.start(): km.end() + 40]
            for nm in num_unit.finditer(window):
                try:
                    vals.append(float(nm.group(1)))
                except Exception:
                    pass
    return vals


def _within_tol(value: float, targets: List[float], pct: float, abs_tol: float = 0.0) -> bool:
    for t in targets:
        if t == 0:
            if abs(value - t) <= abs_tol:
                return True
            continue
        if abs(value - t) / abs(t) <= pct or abs(value - t) <= abs_tol:
            return True
    return False


def audit_source_citation(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        return warns
    code = _extract_code(report_path)
    if not code:
        return warns  # 文件名无 code，跳过（如对话临时文件）
    fd_dir = _find_financial_data_dir()
    if not fd_dir:
        warns.append("[信源引用·WARN] 未找到 FinancialData 目录，无法做信源-引用交叉审计。")
        return warns
    consensus = _load_consensus(fd_dir, code)
    if not consensus:
        warns.append(
            f"[信源引用·WARN] 未找到 `{code}_consensus.json`，跳过一致预期交叉审计。"
            "若报告引用了 EPS/营收/净利润，建议补采一致预期数据后复核。"
        )
        return warns

    rows = (consensus.get("consensus_forecast") or {}).get("data") or []
    if not rows:
        return warns

    eps_targets = [float(r["一致预期EPS(元)"]) for r in rows if r.get("一致预期EPS(元)") is not None]
    rev_targets = [float(r["一致预期营收(亿)"]) for r in rows if r.get("一致预期营收(亿)") is not None]
    np_targets = [float(r["一致预期净利润(亿)"]) for r in rows if r.get("一致预期净利润(亿)") is not None]
    roe_targets = [float(r["ROE(%)"]) for r in rows if r.get("ROE(%)") is not None]

    text = report_path.read_text(encoding="utf-8", errors="replace")

    # EPS
    if eps_targets:
        eps_vals = _report_numbers_near(text, [r"EPS", r"每股收益"], r"元")
        eps_vals = [v for v in eps_vals if 0 < v < 100]  # EPS 合理区间
        if eps_vals and not any(_within_tol(v, eps_targets, 0.08) for v in eps_vals):
            warns.append(
                f"[信源引用·WARN] 报告 EPS 引用 {sorted(set(eps_vals))[:5]} 元，"
                f"与一致预期 {[round(x,2) for x in eps_targets]} 元无任一落入 ±8%。"
                "请核对是否引用串台；若为自有预测且与一致预期分歧，请在正文显式说明分歧原因。"
            )

    # 营收（亿）
    if rev_targets:
        rev_vals = _report_numbers_near(text, [r"营收", r"营业收入", r"收入"], r"亿")
        rev_vals = [v for v in rev_vals if v > 0]
        if rev_vals and not any(_within_tol(v, rev_targets, 0.08) for v in rev_vals):
            warns.append(
                f"[信源引用·WARN] 报告营收引用与一致预期 {[round(x,1) for x in rev_targets]} 亿无任一落入 ±8%。"
                "请核对引用是否串台或显式说明分歧。"
            )

    # 净利润（亿）
    if np_targets:
        np_vals = _report_numbers_near(text, [r"归母净利", r"净利润", r"归属于母公司"], r"亿")
        np_vals = [v for v in np_vals if v > 0]
        if np_vals and not any(_within_tol(v, np_targets, 0.08) for v in np_vals):
            warns.append(
                f"[信源引用·WARN] 报告净利润引用与一致预期 {[round(x,1) for x in np_targets]} 亿无任一落入 ±8%。"
                "请核对引用是否串台或显式说明分歧。"
            )

    # ROE（pct）
    if roe_targets:
        roe_vals = _report_numbers_near(text, [r"ROE", r"净资产收益率"], r"%|％")
        roe_vals = [v for v in roe_vals if 0 < v < 100]
        if roe_vals and not any(_within_tol(v, roe_targets, 0.0, abs_tol=2.0) for v in roe_vals):
            warns.append(
                f"[信源引用·WARN] 报告 ROE 引用与一致预期 {[round(x,1) for x in roe_targets]}% 偏差均 > 2pct，请核对。"
            )

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="信源-引用交叉审计器（P0-6）")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = audit_source_citation(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 信源-引用交叉审计 PASS: {report_path.name}")
        else:
            print(f"⚠️ 信源-引用交叉审计 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
