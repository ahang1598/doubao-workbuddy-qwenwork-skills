#!/usr/bin/env python3
"""Validate cross-layer facts and render the only allowed final summary.

Registry schema:
{
  "metrics": [{
    "metric_id": "primary_metric",
    "label": "主指标",
    "authority": "source_field",
    "source_value": 12345,
    "computed_value": 12345,
    "artifact_value": 12345,
    "value": 12345,
    "unit": "个",
    "period": "目标期间",
    "source": "源表!B2",
    "artifact_source": "最终产物!B2",
    "tolerance": 0
  }]
}

`authority` is either `source_field` or `derived`. Derived metrics must also
provide a non-empty `formula`. Numeric layers must agree within tolerance;
text layers must agree exactly after trimming.
"""

import argparse
import json
import math


def fail(message):
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False, indent=2))
    raise SystemExit(2)


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def equal(left, right, tolerance):
    if finite_number(left) and finite_number(right):
        return abs(float(left) - float(right)) <= tolerance
    return str(left).strip() == str(right).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True)
    parser.add_argument("--ids", default="")
    args = parser.parse_args()

    try:
        payload = json.load(open(args.registry, encoding="utf-8"))
        metrics = payload["metrics"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        fail(str(exc))
    if not isinstance(metrics, list) or not metrics:
        fail("metrics must be a non-empty list")

    required = (
        "metric_id", "label", "authority", "source_value", "computed_value",
        "artifact_value", "value", "unit", "period", "source", "artifact_source",
    )
    indexed = {}
    for metric in metrics:
        if not isinstance(metric, dict):
            fail("every metric must be an object")
        missing = [field for field in required if field not in metric]
        if missing:
            fail(f"missing fields for metric: {missing}")
        metric_id = str(metric["metric_id"]).strip()
        if not metric_id or metric_id in indexed:
            fail(f"metric_id must be unique and non-empty: {metric_id!r}")
        authority = metric["authority"]
        if authority not in ("source_field", "derived"):
            fail(f"authority must be source_field or derived: {metric_id}")
        if authority == "derived" and not str(metric.get("formula", "")).strip():
            fail(f"derived metric requires formula: {metric_id}")
        tolerance = metric.get("tolerance", 0)
        if not finite_number(tolerance) or tolerance < 0:
            fail(f"tolerance must be a finite non-negative number: {metric_id}")
        for field in ("label", "unit", "period", "source", "artifact_source"):
            if not str(metric[field]).strip():
                fail(f"{field} must be non-empty: {metric_id}")
        layers = [
            ("source_value", metric["source_value"]),
            ("computed_value", metric["computed_value"]),
            ("artifact_value", metric["artifact_value"]),
            ("value", metric["value"]),
        ]
        for field, value in layers:
            if isinstance(value, float) and not math.isfinite(value):
                fail(f"non-finite {field}: {metric_id}")
        anchor = metric["source_value"] if authority == "source_field" else metric["computed_value"]
        for field, value in layers:
            if not equal(anchor, value, float(tolerance)):
                fail(
                    f"cross-layer mismatch for {metric_id}: authority={authority}, "
                    f"anchor={anchor!r}, {field}={value!r}, tolerance={tolerance}"
                )
        indexed[metric_id] = metric

    ids = [item.strip() for item in args.ids.split(",") if item.strip()]
    unknown = [item for item in ids if item not in indexed]
    if unknown:
        fail(f"unknown metric ids: {unknown}")
    selected = [indexed[item] for item in ids] if ids else metrics

    print("| 指标 | 期间/范围 | 值 | 单位 | 权威来源 | 最终产物回读来源 |")
    print("|---|---|---:|---|---|---|")
    for metric in selected:
        print(
            f"| {metric['label']} | {metric['period']} | {metric['value']} | "
            f"{metric['unit']} | {metric['source']} | {metric['artifact_source']} |"
        )


if __name__ == "__main__":
    main()
