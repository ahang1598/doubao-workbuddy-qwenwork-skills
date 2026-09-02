#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""盈利预测严谨性验证器（accuracy-uplift v14）

落地三条盈利预测严谨性改进：

① 现金含金量门（对标 FF G7）
   §4.1.4 不能只看利润表 EPS/归母净利，必须校验「利润的含金量」——
   用间接法简版反推经营性现金流 CFO，给出 CFO/净利润比率（<0.6 触发盈利质量预警）。
   forecast_engine 的 `L5_three_statement` 已自动产出该测算，正文须显式披露。

③ 量价三件套硬约束（对标 FF G14/G15/G16，制造业必须）
   分部加总营收里的「量 × 价」假设必须经得起三重拷问：
   - 供给约束：产能/良率/关键物料是否 binding（缺芯/缺料时出货受限）
   - ASP 独立验证：禁止仅用「营收÷出货量」倒推 ASP，须有三方报价交叉验证
   - 良率有据：涉及产能/出货量的良率假设必须有数据来源，禁止刻板印象拍数

④ 假设三分类（对标 FF COMPUTE/JUDGE/ASSUME）
   关键假设应标注其性质：COMPUTE（有公式+数据可算）/ JUDGE（需商业判断）/
   ASSUME（实在无数据才假设，须最小化）。让读者一眼看出哪些数字"最虚"。

软门禁性质：只 WARN，不阻断。短线/超短线（无 §4.1.4）自动跳过。
与 v12/v13 一致：函数签名 validate_forecast_quality(report_path) -> List[str]。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_TRADE_NAME_RE = re.compile(r"交易决策报告_|_trade|基本面_")


def _extract_section_414(text: str) -> str:
    """切出 §4.1.4 章节正文（到下一个同级/更高级标题为止）。失败则返回全文。"""
    m = re.search(r"#{3,6}\s*4\.1\.4[^\n]*\n", text)
    if not m:
        return text
    start = m.end()
    nxt = re.search(r"\n#{1,6}\s*(4\.1\.5|4\.2|5[\.、\s]|五[、\s]|##\s)", text[start:])
    return text[start: start + nxt.start()] if nxt else text[start:]


def _has_414_forecast(text: str) -> bool:
    return "4.1.4" in text and any(k in text for k in ("盈利预测", "EPS", "归母净利"))


def _is_manufacturing(sec: str, text: str) -> bool:
    """是否为有量价拆解的制造业（出现出货量/产能/良率/产线等物理量词）。"""
    kws = ("出货量", "出货", "销量", "产能", "良率", "产线", "产销", "交付量", "装机")
    return any(k in sec for k in kws) or sum(1 for k in kws if k in text) >= 2


# ── ① 现金含金量 ──────────────────────────────────────────────────────────
def _check_cash_quality(report_path: Path, text: str) -> List[str]:
    warns: List[str] = []
    has_cfo = any(k in text for k in (
        "经营活动现金流", "经营性现金流", "经营现金流", "现金含金量", "CFO", "OCF", "现金流量表"
    ))
    has_ratio = (
        "含金量" in text
        or "CFO/净利" in text
        or "CFO/归母" in text
        or bool(re.search(r"(CFO|OCF|经营.{0,4}现金流).{0,14}(/|÷|比值?|对比).{0,8}净利", text))
    )
    if not has_cfo:
        warns.append(
            "[现金含金量·WARN] §4.1.4 盈利预测只看了利润表（EPS/归母净利），未校验『利润的含金量』。"
            "建议补一行经营性现金流测算：CFO ≈ 净利润 + 折旧摊销 − Δ应收 − Δ存货 + Δ应付，"
            "并给出 CFO/净利润 比率（<0.6 为盈利质量预警）。"
            "forecast.json 的 `L5_three_statement` 已自动算好 CFO/FCF/CFO净利比/CCC，直接引用即可。"
        )
    elif not has_ratio:
        warns.append(
            "[现金含金量·WARN] 已提及经营现金流，但未给出 CFO/净利润 含金量比率及 <0.6 预警判断。"
            "高增速公司常见『账面利润高、现金流跟不上』，必须把含金量比率落到买卖结论里。"
        )
    # 与 forecast.json L5 交叉：若中性档已被引擎判为预警，正文必须正视
    fc = report_path.parent / f"{report_path.stem}_forecast.json"
    if fc.exists():
        try:
            data = json.loads(fc.read_text(encoding="utf-8", errors="replace"))
            base = (data.get("L5_three_statement") or {}).get("base") or {}
            flagged = [
                v.get("year_label")
                for v in base.values()
                if isinstance(v, dict) and "预警" in str(v.get("cash_quality_flag", ""))
            ]
            if flagged:
                warns.append(
                    f"[现金含金量·WARN] forecast.json L5 测算显示中性档 {flagged} 年 CFO/净利润 < 0.6"
                    "（盈利质量预警）。请在 §4.1.4 显式披露该信号，并讨论其对估值（FCF 折现）与买卖时点的影响，"
                    "不得只报喜（高 EPS）不报忧（现金流弱）。"
                )
        except Exception:  # noqa: BLE001
            pass
    return warns


# ── ③ 量价三件套（制造业）────────────────────────────────────────────────
def _check_volume_price_rigor(sec: str, text: str) -> List[str]:
    warns: List[str] = []
    if not _is_manufacturing(sec, text):
        return warns  # 非量价拆解型（金融/公用事业/平台）不适用
    has_supply = any(k in text for k in (
        "供给约束", "产能约束", "binding", "缺芯", "缺料", "物料紧缺", "供应紧张", "产能利用率", "瓶颈"
    ))
    has_asp_verify = (
        bool(re.search(r"ASP[^\n]{0,24}(验证|交叉|三方|第三方|报价|招标|外部)", text))
        or bool(re.search(r"(单价|均价)[^\n]{0,18}(三方|第三方|报价|交叉验证|外部报价)", text))
        or "ASP独立验证" in text
    )
    has_yield = bool(re.search(r"良率[^\n]{0,24}(来源|披露|调研|纪要|行业均值|数据|约\s*\d)", text))
    missing: List[str] = []
    if not has_supply:
        missing.append(
            "供给约束（出货量须 = min(产能×利用率×良率, 需求×市占, 关键物料/单耗)，"
            "缺芯/缺料时供给可能是 binding constraint）"
        )
    if not has_asp_verify:
        missing.append(
            "ASP 独立验证（禁止仅用『营收÷出货量』倒推均价，须用三方报价/招标价/竞品价交叉验证，"
            "光模块等快降价行业去年与今年 ASP 可差 30-50%）"
        )
    if not has_yield:
        missing.append("良率有据（涉及产能/出货量的良率假设必须有数据来源，禁止『新品默认 60-70%』式拍数）")
    if missing:
        warns.append(
            "[量价三件套·WARN] §4.1.4 分部加总营收的『量×价』假设缺少制造业硬约束校验，缺："
            + "；".join(missing)
            + "。这三件套决定了量价假设是否经得起物理与市场约束，建议在分部加总表下逐项补齐。"
        )
    return warns


# ── ④ 假设三分类（COMPUTE / JUDGE / ASSUME）─────────────────────────────────
def _check_assumption_taxonomy(sec: str) -> List[str]:
    warns: List[str] = []
    has_taxonomy = (
        bool(re.search(r"COMPUTE|JUDGE|ASSUME", sec, re.I))
        or all(k in sec for k in ("计算", "判断", "假设"))
        and bool(re.search(r"(计算|判断|假设)\s*[类型项]|性质[:：]", sec))
    )
    if not has_taxonomy:
        warns.append(
            "[假设三分类·WARN] §4.1.4 关键假设披露表建议为每条假设标注性质："
            "COMPUTE（有公式+数据可算，最可靠）/ JUDGE（需商业判断）/ ASSUME（实在无数据才假设，须最小化）。"
            "三分类能让读者一眼看出哪些数字最『虚』（ASSUME 越少越好），是盈利预测证据链的核心约束。"
        )
    return warns


def validate_forecast_quality(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        return warns
    if not _TRADE_NAME_RE.search(report_path.name):
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")
    if not _has_414_forecast(text):
        return warns
    sec = _extract_section_414(text)
    warns.extend(_check_cash_quality(report_path, text))
    warns.extend(_check_volume_price_rigor(sec, text))
    warns.extend(_check_assumption_taxonomy(sec))
    return warns


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="盈利预测严谨性验证器（v14：现金含金量+量价三件套+假设三分类）")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_forecast_quality(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 盈利预测严谨性 PASS: {report_path.name}")
        else:
            print(f"⚠️ 盈利预测严谨性 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
