#!/usr/bin/env python3
"""对住宿方案执行 PASS/CHECK/STOP 门禁与一致口径加权评分。"""

import argparse
import json
import math
import sys


DEFAULT_WEIGHTS = {
    "安全与合规": 30,
    "总成本": 20,
    "通勤与时间": 20,
    "学习休息": 15,
    "校园融入": 10,
    "灵活性隐私": 5,
}
VALID_GATES = {"PASS", "CHECK", "STOP"}
MAX_OPTIONS = 50


def reject_constant(value):
    raise ValueError(f"不允许非有限数值: {value}")


def finite_number(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label} 必须是数字，不能是布尔值")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} 必须是数字") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} 必须是有限数字")
    return number


def validate_weights(raw):
    if raw is None:
        return {key: float(value) for key, value in DEFAULT_WEIGHTS.items()}
    if not isinstance(raw, dict):
        raise ValueError("weights 必须是对象")
    expected = set(DEFAULT_WEIGHTS)
    actual = set(raw)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"weights 维度不匹配: missing={missing}, extra={extra}")
    weights = {key: finite_number(raw[key], f"weights.{key}") for key in DEFAULT_WEIGHTS}
    if any(value < 0 for value in weights.values()):
        raise ValueError("weights 必须为非负数")
    if not math.isclose(sum(weights.values()), 100.0, abs_tol=1e-6):
        raise ValueError("weights 总和必须为 100")
    return weights


def main():
    parser = argparse.ArgumentParser(description="住宿方案加权评分与门禁")
    parser.add_argument("--input", required=True, help="JSON 输入文件")
    args = parser.parse_args()
    try:
        with open(args.input, "r", encoding="utf-8") as file:
            data = json.load(file, parse_constant=reject_constant)
        if not isinstance(data, dict):
            raise ValueError("JSON 根节点必须是对象")

        weights = validate_weights(data.get("weights"))
        options = data.get("options")
        if not isinstance(options, list) or not 2 <= len(options) <= MAX_OPTIONS:
            raise ValueError(f"options 数量必须为 2-{MAX_OPTIONS}")

        results = []
        seen_names = set()
        for index, option in enumerate(options, start=1):
            if not isinstance(option, dict):
                raise ValueError(f"options[{index}] 必须是对象")
            name = str(option.get("name") or "").strip()
            if not name or len(name) > 80:
                raise ValueError(f"options[{index}].name 必须是 1-80 字符")
            if name in seen_names:
                raise ValueError(f"方案名称重复: {name}")
            seen_names.add(name)

            gate = str(option.get("gate") or "CHECK").upper()
            if gate not in VALID_GATES:
                raise ValueError(f"{name}: gate 必须是 PASS/CHECK/STOP")
            scores = option.get("scores")
            if not isinstance(scores, dict):
                raise ValueError(f"{name}: scores 必须是对象")
            extra_scores = sorted(set(scores) - set(weights))
            if extra_scores:
                raise ValueError(f"{name}: 未知评分维度 {extra_scores}")

            weighted = 0.0
            coverage_weight = 0.0
            missing = []
            for dimension, weight in weights.items():
                value = scores.get(dimension)
                if value in (None, "", "unknown"):
                    missing.append(dimension)
                    continue
                score = finite_number(value, f"{name}.{dimension}")
                if not 1 <= score <= 5:
                    raise ValueError(f"{name}: {dimension} 分数必须在 1-5")
                weighted += score / 5.0 * weight
                coverage_weight += weight

            complete_score = None if missing else round(weighted, 1)
            known_score = None if coverage_weight == 0 else round(weighted / coverage_weight * 100, 1)
            results.append(
                {
                    "name": name,
                    "gate": gate,
                    "score": complete_score,
                    "known_dimension_score": known_score,
                    "missing_dimensions": missing,
                    "recommendable": gate != "STOP",
                    "recommendation_mode": (
                        "blocked" if gate == "STOP" else "conditional" if gate == "CHECK" else "normal"
                    ),
                }
            )

        rankable = [
            result
            for result in results
            if result["recommendable"] and result["score"] is not None
        ]
        rankable.sort(key=lambda result: result["score"], reverse=True)
        output = {
            "weights": weights,
            "results": results,
            "ranking": [result["name"] for result in rankable],
            "warning": "STOP 不得推荐；CHECK 只能作为条件式候选；缺失维度的方案不进入排名。",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
