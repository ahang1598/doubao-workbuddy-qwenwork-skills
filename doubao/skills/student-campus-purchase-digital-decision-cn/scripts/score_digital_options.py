#!/usr/bin/env python3
"""Score digital candidates without ranking unsupported or blocked options."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
import sys
from pathlib import Path
from typing import Any


DIMENSIONS = {
    "performance",
    "portability",
    "battery",
    "display",
    "compatibility",
    "expandability",
    "after_sales",
    "price_value",
    "longevity",
}
MAX_CANDIDATES = 20
MAX_AMOUNT = 1_000_000_000
NETWORK_TOOL_STATUSES = {
    "available_authorized",
    "available_authorization_pending",
    "unavailable",
    "not_used",
}
PRICE_ACCESS_METHODS = {"user_provided", "public_web", "offline"}
AUTHORIZATION_STATUSES = {"authorized", "pending", "restricted", "not_applicable"}


def reject_constant(value: str) -> None:
    raise ValueError(f"不允许非有限数值: {value}")


def error(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    return 2


def finite_number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} 必须是数值")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{field} 必须是 {minimum}–{maximum} 的有限数值")
    return float(value)


def nonempty_string(value: Any, field: str, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} 必须是非空字符串")
    result = value.strip()
    if len(result) > maximum:
        raise ValueError(f"{field} 过长")
    return result


def timezone_timestamp(value: Any, field: str) -> str:
    result = nonempty_string(value, field, 40)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} 必须是 ISO 8601 时间") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} 必须包含时区")
    return result


def network_tool_status(value: Any) -> str:
    if not isinstance(value, dict):
        raise ValueError("runtime 必须是对象")
    status = value.get("network_tool_status")
    if status not in NETWORK_TOOL_STATUSES:
        raise ValueError("runtime.network_tool_status 非法")
    limitations = value.get("limitations", [])
    if not isinstance(limitations, list) or not all(
        isinstance(item, str) and item.strip() for item in limitations
    ):
        raise ValueError("runtime.limitations 必须是字符串数组")
    return status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按证据比较数码候选")
    parser.add_argument("--input", required=True, type=Path, help="候选比较 JSON 文件")
    return parser.parse_args()


def validate_weights(value: Any) -> dict[str, float]:
    if not isinstance(value, dict) or not value:
        raise ValueError("weights 必须是非空对象")
    unknown = sorted(set(value) - DIMENSIONS)
    if unknown:
        raise ValueError(f"weights 含未知维度: {', '.join(unknown)}")
    weights = {
        key: finite_number(weight, f"weights.{key}", 0, 100)
        for key, weight in value.items()
    }
    if sum(weights.values()) <= 0:
        raise ValueError("weights 总和必须大于 0")
    return weights


def main() -> int:
    args = parse_args()
    try:
        with args.input.open("r", encoding="utf-8") as handle:
            data = json.load(handle, parse_constant=reject_constant)
        if not isinstance(data, dict):
            raise ValueError("JSON 根节点必须是对象")

        tool_status = network_tool_status(data.get("runtime"))
        weights = validate_weights(data.get("weights"))
        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not 2 <= len(candidates) <= MAX_CANDIDATES:
            raise ValueError(f"candidates 必须是 2–{MAX_CANDIDATES} 项的数组")

        results = []
        seen_names: set[str] = set()
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise ValueError(f"candidates[{index}] 必须是对象")
            name = nonempty_string(candidate.get("name"), f"candidates[{index}].name")
            if name in seen_names:
                raise ValueError(f"候选名称重复: {name}")
            seen_names.add(name)

            constraints = candidate.get("hard_constraints", {})
            if not isinstance(constraints, dict):
                raise ValueError(f"{name}.hard_constraints 必须是对象")
            failed_constraints = []
            unknown_constraints = []
            for key, value in constraints.items():
                nonempty_string(key, f"{name}.hard_constraints 键")
                if value is False:
                    failed_constraints.append(key)
                elif value is None:
                    unknown_constraints.append(key)
                elif value is not True:
                    raise ValueError(f"{name}.hard_constraints.{key} 必须是 true、false 或 null")

            scores = candidate.get("scores", {})
            evidence = candidate.get("evidence", {})
            if not isinstance(scores, dict) or not isinstance(evidence, dict):
                raise ValueError(f"{name}.scores 和 evidence 必须是对象")
            unknown_score_keys = sorted(set(scores) - DIMENSIONS)
            unknown_evidence_keys = sorted(set(evidence) - DIMENSIONS)
            if unknown_score_keys or unknown_evidence_keys:
                raise ValueError(f"{name} 含未知评分或证据维度")

            missing_dimensions = []
            numerator = 0.0
            denominator = 0.0
            for dimension, weight in weights.items():
                if weight == 0:
                    continue
                if dimension not in scores or not evidence.get(dimension):
                    missing_dimensions.append(dimension)
                    continue
                score = finite_number(
                    scores[dimension], f"{name}.scores.{dimension}", 0, 10
                )
                nonempty_string(evidence[dimension], f"{name}.evidence.{dimension}", 500)
                numerator += score * weight
                denominator += weight

            price = candidate.get("price")
            price_checked_at = candidate.get("price_checked_at")
            price_source = candidate.get("price_source")
            price_access_method = candidate.get("price_access_method")
            price_authorization_status = candidate.get("price_authorization_status")
            dynamic_price_missing = False
            dynamic_price_authorization_unavailable = False
            if price is not None:
                price = finite_number(price, f"{name}.price", 0, MAX_AMOUNT)
                if (
                    not price_checked_at
                    or not price_source
                    or not price_access_method
                    or not price_authorization_status
                ):
                    dynamic_price_missing = True
                else:
                    price_checked_at = timezone_timestamp(price_checked_at, f"{name}.price_checked_at")
                    price_source = nonempty_string(price_source, f"{name}.price_source", 300)
                    if price_access_method not in PRICE_ACCESS_METHODS:
                        raise ValueError(f"{name}.price_access_method 非法")
                    if price_authorization_status not in AUTHORIZATION_STATUSES:
                        raise ValueError(f"{name}.price_authorization_status 非法")
                    if price_access_method in {"user_provided", "offline"}:
                        if price_authorization_status != "not_applicable":
                            raise ValueError(
                                f"{name} 的用户提供/离线价格必须使用 not_applicable"
                            )
                    elif price_authorization_status == "authorized":
                        if tool_status != "available_authorized":
                            raise ValueError(
                                f"{name} 声称联网价格已授权，但 network_tool_status 不匹配"
                            )
                    elif price_authorization_status in {"pending", "restricted"}:
                        dynamic_price_authorization_unavailable = True
                    else:
                        raise ValueError(
                            f"{name} 的 public_web 价格不能使用 not_applicable"
                        )

            eligible = not (
                failed_constraints
                or unknown_constraints
                or missing_dimensions
                or dynamic_price_missing
                or dynamic_price_authorization_unavailable
            )
            weighted_score = round(numerator / denominator, 3) if eligible and denominator else None
            results.append(
                {
                    "name": name,
                    "eligible": eligible,
                    "failed_hard_constraints": sorted(failed_constraints),
                    "unknown_hard_constraints": sorted(unknown_constraints),
                    "missing_for_scoring": sorted(missing_dimensions),
                    "dynamic_price_evidence_missing": dynamic_price_missing,
                    "dynamic_price_authorization_unavailable": dynamic_price_authorization_unavailable,
                    "weighted_score": weighted_score,
                    "price": price,
                    "price_checked_at": price_checked_at,
                    "price_source": price_source,
                    "price_access_method": price_access_method,
                    "price_authorization_status": price_authorization_status,
                }
            )

        rankable = [item for item in results if item["eligible"]]
        rankable.sort(key=lambda item: (-item["weighted_score"], item["name"]))
        output = {
            "ok": True,
            "runtime": {
                "network_tool_status": tool_status,
                "limitations": data["runtime"].get("limitations", []),
            },
            "weights": weights,
            "results": results,
            "ranking": [item["name"] for item in rankable],
            "warning": "硬约束失败或未知、证据缺失、动态价格缺来源/时间/授权，或联网授权待确认的候选不进入排名。",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
