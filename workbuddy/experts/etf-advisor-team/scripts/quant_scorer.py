#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 定量评分计算器

将团队分析框架中确定性的数学计算从 LLM 推理移至代码执行，
节省 token 并确保计算准确性。

功能模块：
  1. 基金四维评价打分 (fund_four_dim) — 业绩35% + 风险25% + 持仓20% + 风格20%
  2. 全量计算 (all)

用法：
  python quant_scorer.py fund_four_dim --perf-score 80 --risk-score 70 --holding-score 65 --style-score 75
  python quant_scorer.py fund_four_dim --perf-score 80 --risk-score 70 --holding-score 65 --style-score 75 --perf-excellent --risk-excellent --holding-excellent
  python quant_scorer.py all --json-input data.json

输出：JSON 格式，可直接被 LLM 读取。
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
from typing import Any


def _print_utf8(text: str):
    """Windows 兼容的 UTF-8 输出（避免 GBK 编码错误）。"""
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()


# ============================================================
# 模块1：基金四维评价打分
# ============================================================

# 四维权重配置
FOUR_DIM_WEIGHTS = {
    "performance": 0.35,  # 业绩维度
    "risk":        0.25,  # 风险维度
    "holding":     0.20,  # 持仓维度
    "style":       0.20,  # 风格维度
}

# 各维度合格线/优秀线/风险线（百分制）
FOUR_DIM_THRESHOLDS = {
    "performance": {
        "name": "业绩维度",
        "weight_pct": "35%",
        "core_metrics": "年化收益率、超额收益、夏普比率、卡玛比率、最大回撤",
        "qualified_line": 60,   # 合格线: 近3年同类前1/3、夏普>1.0
        "excellent_line": 80,   # 优秀线: 近5年同类前1/4、夏普>1.5、卡玛>1.0
        "risk_line": 30,        # 风险线
    },
    "risk": {
        "name": "风险维度",
        "weight_pct": "25%",
        "core_metrics": "年化波动率、下行标准差、β系数、熊市抗跌比",
        "qualified_line": 60,   # 合格线: 波动率≤同类均值、抗跌比<1.0
        "excellent_line": 80,   # 优秀线: 波动率<同类75%分位、抗跌比<0.7
        "risk_line": 30,
    },
    "holding": {
        "name": "持仓维度",
        "weight_pct": "20%",
        "core_metrics": "行业集中度、个股集中度、换手率、重仓股ROE",
        "qualified_line": 60,   # 合格线: 换手率≤同类2倍、集中度30%-65%
        "excellent_line": 80,   # 优秀线: 重仓股连续跑赢基准、换手率≤同类均值
        "risk_line": 30,
    },
    "style": {
        "name": "风格维度",
        "weight_pct": "20%",
        "core_metrics": "市值风格一致性、估值风格一致性、行业轮动幅度、仓位稳定性",
        "qualified_line": 60,   # 合格线: 近8季风格标准差<15%
        "excellent_line": 80,   # 优秀线: 近8季风格标准差<10%、行业配置连续稳定
        "risk_line": 30,
    },
}


def calc_fund_four_dim(
    perf_score: float,
    risk_score: float,
    holding_score: float,
    style_score: float,
    perf_excellent: bool = False,
    risk_excellent: bool = False,
    holding_excellent: bool = False,
    style_excellent: bool = False,
) -> dict:
    """
    基金四维评价打分（参考郑兆磊团队基金研究方法论）。

    对主动管理型基金从四个维度综合评分，用于最终推荐排序的加权参考。

    评分方式:
      LLM 根据采集到的基金数据，对每个维度打分(0-100百分制)：
      - 0-29:  风险线以下（该维度存在明显风险）
      - 30-59: 风险线以上但未达合格线
      - 60-79: 合格线（达到基本筛选标准）
      - 80-100: 优秀线（达到核心推荐标准）

    四维综合评分使用规则:
      - 四维全部达到合格线 → 可入候选池
      - 三维达到优秀线 → 可作为核心推荐标的
      - 任一维度在风险线以下 → 需特别说明风险，不作为首选推荐

    参数:
        perf_score:      业绩维度得分(0-100)
        risk_score:      风险维度得分(0-100)
        holding_score:   持仓维度得分(0-100)
        style_score:     风格维度得分(0-100)
        perf_excellent:  业绩是否达优秀线(可选，默认由分数自动判断)
        risk_excellent:  风险是否达优秀线
        holding_excellent: 持仓是否达优秀线
        style_excellent: 风格是否达优秀线

    返回:
        dict 包含各维度得分、加权总分、资格判断、推荐级别
    """
    # 限制在合法范围
    perf_score = max(0, min(100, perf_score))
    risk_score = max(0, min(100, risk_score))
    holding_score = max(0, min(100, holding_score))
    style_score = max(0, min(100, style_score))

    scores = {
        "performance": perf_score,
        "risk": risk_score,
        "holding": holding_score,
        "style": style_score,
    }

    # 加权总分
    weighted_total = (
        perf_score * FOUR_DIM_WEIGHTS["performance"]
        + risk_score * FOUR_DIM_WEIGHTS["risk"]
        + holding_score * FOUR_DIM_WEIGHTS["holding"]
        + style_score * FOUR_DIM_WEIGHTS["style"]
    )

    # 各维度状态判断
    dim_results = {}
    qualified_count = 0
    excellent_count = 0
    risk_alert_dims = []

    for key, score in scores.items():
        config = FOUR_DIM_THRESHOLDS[key]
        # 判断是否达优秀线（如果显式传入了excellent标记就用，否则靠分数判断）
        is_excellent_map = {
            "performance": perf_excellent,
            "risk": risk_excellent,
            "holding": holding_excellent,
            "style": style_excellent,
        }
        is_excellent = is_excellent_map[key] or score >= config["excellent_line"]
        is_qualified = score >= config["qualified_line"]
        is_risk = score < config["risk_line"]

        if is_excellent:
            excellent_count += 1
            status = "✅ 优秀"
        elif is_qualified:
            status = "✅ 合格"
        elif is_risk:
            status = "🔴 风险"
            risk_alert_dims.append(config["name"])
        else:
            status = "🟡 待改善"

        if is_qualified or is_excellent:
            qualified_count += 1

        dim_results[config["name"]] = {
            "score": score,
            "weight": config["weight_pct"],
            "weighted_score": round(score * FOUR_DIM_WEIGHTS[key], 1),
            "status": status,
            "qualified_line": config["qualified_line"],
            "excellent_line": config["excellent_line"],
            "core_metrics": config["core_metrics"],
        }

    # 综合资格判断
    all_qualified = qualified_count >= 4
    three_excellent = excellent_count >= 3
    has_risk = len(risk_alert_dims) > 0

    if has_risk:
        recommendation = "⚠️ 存在风险维度"
        recommendation_detail = f"以下维度低于风险线：{', '.join(risk_alert_dims)}。需特别说明风险，不作为首选推荐"
        recommendation_level = "risk_alert"
    elif three_excellent:
        recommendation = "🌟 核心推荐标的"
        recommendation_detail = f"{excellent_count}个维度达到优秀线，可作为核心推荐标的"
        recommendation_level = "core_recommend"
    elif all_qualified:
        recommendation = "✅ 候选池标的"
        recommendation_detail = "四维全部达到合格线，可入候选池"
        recommendation_level = "candidate"
    else:
        recommendation = "🟡 部分达标"
        recommendation_detail = f"{qualified_count}/4 维度达标，{4 - qualified_count} 维度未达合格线"
        recommendation_level = "partial"

    return {
        "module": "基金四维评价打分",
        "methodology": "参考郑兆磊团队基金研究方法论",
        "dimensions": dim_results,
        "summary": {
            "weighted_total_score": round(weighted_total, 1),
            "max_score": 100,
            "qualified_count": qualified_count,
            "excellent_count": excellent_count,
            "risk_alert_dimensions": risk_alert_dims,
        },
        "recommendation": recommendation,
        "recommendation_detail": recommendation_detail,
        "recommendation_level": recommendation_level,
    }


# ============================================================
# 全量计算（从JSON文件读入所有参数）
# ============================================================

def calc_all(data: dict) -> dict:
    """从统一的 JSON 输入计算所有模块。"""
    results = {}

    if "fund_four_dim" in data:
        fd = data["fund_four_dim"]
        results["fund_four_dim"] = calc_fund_four_dim(
            perf_score=fd["perf_score"],
            risk_score=fd["risk_score"],
            holding_score=fd["holding_score"],
            style_score=fd["style_score"],
            perf_excellent=fd.get("perf_excellent", False),
            risk_excellent=fd.get("risk_excellent", False),
            holding_excellent=fd.get("holding_excellent", False),
            style_excellent=fd.get("style_excellent", False),
        )

    return results


# ============================================================
# CLI 入口
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ETF 定量评分计算器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="计算模块")

    # fund_four_dim
    fd = sub.add_parser("fund_four_dim", help="基金四维评价打分")
    fd.add_argument("--perf-score", type=float, required=True, help="业绩维度得分(0-100)")
    fd.add_argument("--risk-score", type=float, required=True, help="风险维度得分(0-100)")
    fd.add_argument("--holding-score", type=float, required=True, help="持仓维度得分(0-100)")
    fd.add_argument("--style-score", type=float, required=True, help="风格维度得分(0-100)")
    fd.add_argument("--perf-excellent", action="store_true", help="业绩达优秀线")
    fd.add_argument("--risk-excellent", action="store_true", help="风险达优秀线")
    fd.add_argument("--holding-excellent", action="store_true", help="持仓达优秀线")
    fd.add_argument("--style-excellent", action="store_true", help="风格达优秀线")

    # all (JSON input)
    a = sub.add_parser("all", help="全量计算(JSON输入)")
    a.add_argument("--json-input", type=str, required=True, help="JSON输入文件路径")

    # 全局选项
    parser.add_argument("--output", "-o", type=str, default=None, help="输出文件路径")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    result: Any = None

    if args.command == "fund_four_dim":
        result = calc_fund_four_dim(
            perf_score=args.perf_score,
            risk_score=args.risk_score,
            holding_score=args.holding_score,
            style_score=args.style_score,
            perf_excellent=args.perf_excellent,
            risk_excellent=args.risk_excellent,
            holding_excellent=args.holding_excellent,
            style_excellent=args.style_excellent,
        )
    elif args.command == "all":
        with open(args.json_input, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = calc_all(data)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    # 输出
    if hasattr(args, 'output') and args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        _print_utf8(f"✅ 结果已保存至 {args.output}")
    else:
        _print_utf8(output_json)


if __name__ == "__main__":
    main()
