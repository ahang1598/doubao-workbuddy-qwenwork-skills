#!/usr/bin/env python3
"""用正态近似复算两独立比例实验的样本量，不补统计参数默认值。"""

from __future__ import annotations

import argparse
import json
import math
import sys
from statistics import NormalDist


def probability(name: str, value: float, *, open_interval: bool = True) -> float:
    valid = 0 < value < 1 if open_interval else 0 <= value <= 1
    if not valid or not math.isfinite(value):
        interval = "0 到 1 之间" if open_interval else "0 到 1（含端点）"
        raise ValueError(f"{name} 必须在{interval}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="复算两独立比例实验的近似样本量；所有统计参数必须显式提供")
    parser.add_argument("--baseline", required=True, type=float, help="对照组基线比例，0 到 1")
    parser.add_argument("--mde", required=True, type=float, help="绝对最小可检测效应，例如 0.01 表示 1 个百分点")
    parser.add_argument("--alpha", required=True, type=float, help="显著性水平，0 到 1")
    parser.add_argument("--power", required=True, type=float, help="统计把握度，0 到 1")
    parser.add_argument("--allocation", required=True, type=float, help="处理组样本占总样本比例，0 到 1")
    parser.add_argument("--sides", required=True, choices=("one", "two"), help="单侧或双侧检验")
    parser.add_argument("--direction", required=False, choices=("increase", "decrease"), help="效应方向；必须显式提供")
    parser.add_argument("--daily-eligible-traffic", type=float, help="可选：每日可进入实验的合格流量，用于估算最短样本收集天数")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.direction is None:
            raise ValueError("必须显式提供 --direction increase 或 --direction decrease")
        p1 = probability("baseline", args.baseline)
        probability("alpha", args.alpha)
        probability("power", args.power)
        treatment_share = probability("allocation", args.allocation)
        if not math.isfinite(args.mde) or args.mde <= 0:
            raise ValueError("mde 必须是大于 0 的绝对比例差")

        p2 = p1 + args.mde if args.direction == "increase" else p1 - args.mde
        probability("baseline ± mde", p2)

        ratio = treatment_share / (1 - treatment_share)
        pooled = (p1 + ratio * p2) / (1 + ratio)
        alpha_tail = args.alpha / 2 if args.sides == "two" else args.alpha
        z_alpha = NormalDist().inv_cdf(1 - alpha_tail)
        z_power = NormalDist().inv_cdf(args.power)

        null_variance_factor = pooled * (1 - pooled) * (1 + 1 / ratio)
        alt_variance_factor = p1 * (1 - p1) + p2 * (1 - p2) / ratio
        control_n_raw = (
            (z_alpha * math.sqrt(null_variance_factor) + z_power * math.sqrt(alt_variance_factor)) ** 2
            / (p2 - p1) ** 2
        )
        control_n = math.ceil(control_n_raw)
        treatment_n = math.ceil(control_n * ratio)
        total_n = control_n + treatment_n

        result: dict[str, object] = {
            "method": "two_independent_proportions_normal_approximation",
            "baseline": p1,
            "treatment_rate_at_mde": p2,
            "absolute_mde": args.mde,
            "alpha": args.alpha,
            "power": args.power,
            "sides": args.sides,
            "direction": args.direction,
            "treatment_allocation": treatment_share,
            "control_sample": control_n,
            "treatment_sample": treatment_n,
            "total_sample": total_n,
            "note": "统计近似值，不包含流量波动、污染、聚类、序贯检验、多重比较或损耗修正。",
        }
        if args.daily_eligible_traffic is not None:
            if not math.isfinite(args.daily_eligible_traffic) or args.daily_eligible_traffic <= 0:
                raise ValueError("daily-eligible-traffic 必须大于 0")
            result["minimum_collection_days_from_traffic_only"] = math.ceil(total_n / args.daily_eligible_traffic)
            result["traffic_note"] = "仅按流量除法估算，不替代完整周期、周内效应和数据延迟判断。"

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
