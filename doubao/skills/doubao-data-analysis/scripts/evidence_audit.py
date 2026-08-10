#!/usr/bin/env python3
"""Deterministic audits for rule thresholds, sets, and reported totals."""

import argparse
import csv
import json
import math
import operator
import sys
from collections import defaultdict


OPS = {
    "gt": operator.gt,
    "ge": operator.ge,
    "lt": operator.lt,
    "le": operator.le,
    "eq": operator.eq,
    "ne": operator.ne,
}


def emit(payload, code=0):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def number(value, field):
    try:
        result = float(str(value).replace(",", "").strip())
    except Exception:
        raise ValueError(f"{field} is not numeric: {value!r}")
    if not math.isfinite(result):
        raise ValueError(f"{field} is not finite: {value!r}")
    return result


def read_rows(paths):
    rows = []
    headers = None
    for path in paths:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            current = reader.fieldnames or []
            if not current:
                raise ValueError(f"missing header: {path}")
            if headers is None:
                headers = current
            elif current != headers:
                raise ValueError(f"header mismatch: {path}")
            for row_no, row in enumerate(reader, 2):
                row["_source"] = path
                row["_row"] = row_no
                rows.append(row)
    return headers or [], rows


def rule_check(args):
    headers, rows = read_rows(args.input)
    keys = [item.strip() for item in args.keys.split(",") if item.strip()]
    required = keys + [args.metric]
    missing = [field for field in required if field not in headers]
    if missing:
        emit({"ok": False, "errors": [f"missing fields: {missing}"]}, 2)

    groups = defaultdict(lambda: {"count": 0, "total": 0.0, "evidence": []})
    try:
        for row in rows:
            key = tuple(row[field] for field in keys)
            value = number(row[args.metric], args.metric)
            item = groups[key]
            item["count"] += 1
            item["total"] += value
            item["evidence"].append({
                "source": row["_source"],
                "row": row["_row"],
                "value": value,
            })
    except ValueError as exc:
        emit({"ok": False, "errors": [str(exc)]}, 2)

    comparator = OPS[args.op]
    candidates, violations, compliant_splits = [], [], []
    for key, item in groups.items():
        result = {
            "key": dict(zip(keys, key)),
            "record_count": item["count"],
            "aggregate": item["total"],
            "evidence": item["evidence"],
        }
        if item["count"] > 1:
            candidates.append(result)
        if comparator(item["total"], args.threshold):
            violations.append(result)
        elif item["count"] > 1:
            compliant_splits.append(result)

    emit({
        "ok": True,
        "mode": "aggregate_threshold",
        "rule": f"sum({args.metric}) {args.op} {args.threshold}",
        "row_count": len(rows),
        "group_count": len(groups),
        "candidate_group_count": len(candidates),
        "violation_count": len(violations),
        "compliant_split_count": len(compliant_splits),
        "violations": violations,
        "compliant_splits": compliant_splits,
    })


def match_condition(row, condition):
    field = condition["field"]
    op = condition["op"]
    expected = condition.get("value")
    if field not in row:
        raise ValueError(f"missing field in set condition: {field}")
    actual = row[field]
    if op in ("gt", "ge", "lt", "le"):
        return OPS[op](number(actual, field), number(expected, "value"))
    if op in ("eq", "ne"):
        return OPS[op](str(actual), str(expected))
    if op == "contains":
        return str(expected) in str(actual)
    raise ValueError(f"unsupported set operator: {op}")


def set_audit(args):
    headers, rows = read_rows(args.input)
    if args.id not in headers:
        emit({"ok": False, "errors": [f"missing id field: {args.id}"]}, 2)
    try:
        spec = json.load(open(args.spec, encoding="utf-8"))
        definitions = spec["sets"]
        sets = {}
        for name, conditions in definitions.items():
            if isinstance(conditions, dict):
                conditions = [conditions]
            sets[name] = {
                row[args.id]
                for row in rows
                if all(match_condition(row, condition) for condition in conditions)
            }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        emit({"ok": False, "errors": [str(exc)]}, 2)

    intersections = {}
    names = sorted(sets)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            overlap = sets[left] & sets[right]
            intersections[f"{left}&{right}"] = {
                "size": len(overlap),
                "ids": sorted(overlap),
            }
    union = set().union(*sets.values()) if sets else set()
    emit({
        "ok": True,
        "row_count": len(rows),
        "sets": {
            name: {"size": len(values), "ids": sorted(values)}
            for name, values in sets.items()
        },
        "intersections": intersections,
        "union": {"size": len(union), "ids": sorted(union)},
    })


def reconcile(args):
    try:
        spec = json.load(open(args.spec, encoding="utf-8"))
        tolerance = float(spec.get("tolerance", 1e-6))
        checks = []
        ok = True
        for claim in spec["claims"]:
            components = [number(value, "component") for value in claim["components"]]
            expected = number(claim["reported"], "reported")
            recomputed = sum(components)
            passed = abs(recomputed - expected) <= tolerance
            ok = ok and passed
            checks.append({
                "name": claim["name"],
                "reported": expected,
                "recomputed": recomputed,
                "delta": expected - recomputed,
                "pass": passed,
            })
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        emit({"ok": False, "errors": [str(exc)]}, 2)
    emit({"ok": ok, "checks": checks}, 0 if ok else 1)


def _normalize(value):
    text = "" if value is None else str(value).strip()
    try:
        numeric = float(text.replace(",", ""))
        if math.isfinite(numeric):
            return ("number", numeric)
    except ValueError:
        pass
    return ("text", text)


def record_reconcile(args):
    """Compare two CSV extracts by stable business keys and selected fields."""
    source_headers, source_rows = read_rows([args.source])
    output_headers, output_rows = read_rows([args.output])
    keys = [item.strip() for item in args.keys.split(",") if item.strip()]
    fields = [item.strip() for item in args.fields.split(",") if item.strip()]
    required = keys + fields
    missing = {
        "source": [field for field in required if field not in source_headers],
        "output": [field for field in required if field not in output_headers],
    }
    if any(missing.values()):
        emit({"ok": False, "errors": ["missing fields"], "missing": missing}, 2)

    def index_rows(rows, label):
        indexed, duplicates = {}, []
        for row in rows:
            key = tuple(row[field] for field in keys)
            if key in indexed:
                duplicates.append({"key": dict(zip(keys, key)), "side": label})
            else:
                indexed[key] = row
        return indexed, duplicates

    source_index, source_duplicates = index_rows(source_rows, "source")
    output_index, output_duplicates = index_rows(output_rows, "output")
    source_keys, output_keys = set(source_index), set(output_index)
    only_source = source_keys - output_keys
    only_output = output_keys - source_keys
    mismatches = []
    for key in sorted(source_keys & output_keys):
        for field in fields:
            source_kind, source_value = _normalize(source_index[key][field])
            output_kind, output_value = _normalize(output_index[key][field])
            if source_kind == output_kind == "number":
                passed = abs(source_value - output_value) <= args.tolerance
            else:
                passed = source_kind == output_kind and source_value == output_value
            if not passed:
                mismatches.append({
                    "key": dict(zip(keys, key)),
                    "field": field,
                    "source": source_index[key][field],
                    "output": output_index[key][field],
                })

    ok = not (
        source_duplicates or output_duplicates or only_source or only_output or mismatches
    )
    emit({
        "ok": ok,
        "source_rows": len(source_rows),
        "output_rows": len(output_rows),
        "duplicate_keys": source_duplicates + output_duplicates,
        "only_source": [dict(zip(keys, key)) for key in sorted(only_source)],
        "only_output": [dict(zip(keys, key)) for key in sorted(only_output)],
        "value_mismatches": mismatches,
        "tolerance": args.tolerance,
    }, 0 if ok else 1)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    rule = sub.add_parser("rule-check")
    rule.add_argument("--input", nargs="+", required=True)
    rule.add_argument("--keys", required=True)
    rule.add_argument("--metric", required=True)
    rule.add_argument("--op", choices=sorted(OPS), required=True)
    rule.add_argument("--threshold", type=float, required=True)
    rule.set_defaults(func=rule_check)

    sets = sub.add_parser("set-audit")
    sets.add_argument("--input", nargs="+", required=True)
    sets.add_argument("--id", required=True)
    sets.add_argument("--spec", required=True)
    sets.set_defaults(func=set_audit)

    totals = sub.add_parser("reconcile")
    totals.add_argument("--spec", required=True)
    totals.set_defaults(func=reconcile)

    records = sub.add_parser("record-reconcile")
    records.add_argument("--source", required=True)
    records.add_argument("--output", required=True)
    records.add_argument("--keys", required=True)
    records.add_argument("--fields", required=True)
    records.add_argument("--tolerance", type=float, default=1e-6)
    records.set_defaults(func=record_reconcile)

    args = parser.parse_args()
    try:
        args.func(args)
    except (OSError, ValueError) as exc:
        emit({"ok": False, "errors": [str(exc)]}, 2)


if __name__ == "__main__":
    main()
