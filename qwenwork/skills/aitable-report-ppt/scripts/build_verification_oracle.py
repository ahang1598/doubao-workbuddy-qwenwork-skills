#!/usr/bin/env python3
"""Independent Python oracle for visual report verification.

Computes expected values for every metric, chart, and drill-down declared in
report-spec.json, directly from the raw snapshot, following semantics-1.0
(references/reporting/semantics.md). The output verification-oracle.json is the
"second ruler" that validate_visual_report.js compares the rendered page
against. This module MUST NOT share computation code with report-runtime.js —
the two are deliberately independent implementations of the same contract.

Scope note: validate_report_spec.py stays a static spec validator and never
reads business data; all data computation lives here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORACLE_VERSION = "1.0"
SEMANTICS_VERSION = "1.0"
def _runtime_contract_version() -> str:
    """读取 runtime 自己声明的合同版本。

    这里曾经硬编码为字符串。一旦 runtime 升版而这里忘了跟，指纹比对就会
    因为一个与数据无关的原因永久失败；反过来若 runtime 行为变了而版本没变，
    旧报告又会被当成兼容的。让唯一事实源留在 runtime 里。
    """
    source = (Path(__file__).resolve().parent.parent
              / "assets/components/report-runtime.js").read_text(encoding="utf-8")
    match = re.search(r"CONTRACT_VERSION\s*=\s*'([^']+)'", source)
    if not match:
        raise SystemExit("无法从 report-runtime.js 解析 CONTRACT_VERSION")
    return match.group(1)


def _runtime_asset_sha256() -> str:
    """runtime 源文件的哈希，供指纹比对确认页面内联的确实是这一版。

    页面一直声明这个字段，但先前无人比对，于是内联了过期 runtime 也查不出来。
    比对的两端必须同时存在——只加比对不产出，只会把所有报告卡在 undefined 上。
    """
    path = Path(__file__).resolve().parent.parent / "assets/components/report-runtime.js"
    return hashlib.sha256(path.read_bytes()).hexdigest()


RUNTIME_CONTRACT_VERSION = _runtime_contract_version()
RUNTIME_ASSET_SHA256 = _runtime_asset_sha256()

NUMERIC_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


class OracleError(SystemExit):
    def __init__(self, code: str, message: str) -> None:
        payload = {"status": "failed", "code": code, "message": message}
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        super().__init__(2)


# ---------------------------- facts (semantics-1.0) ----------------------------

def is_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, str):
        text = value.strip()
        if NUMERIC_RE.match(text):
            return float(text)
        return None
    return None


def norm_text(value: Any) -> str:
    return unicodedata.normalize("NFC", str(value)).strip()


def round_half_away(value: float | None, decimals: int = 0) -> float | None:
    if value is None:
        return None
    factor = 10 ** decimals
    sign = -1.0 if value < 0 else 1.0
    return sign * math.floor(abs(value) * factor + 0.5) / factor


def numeric_values(records: list[dict], field: str | None, null_policy: str) -> list[float]:
    out: list[float] = []
    for record in records:
        raw = record.get(field) if field else None
        num = None if is_null(raw) else to_number(raw)
        if num is None:
            if null_policy == "as_zero":
                out.append(0.0)
        else:
            out.append(num)
    return out


def aggregate_field(records: list[dict], field: str | None, fn: str, null_policy: str = "exclude") -> float | int | None:
    if fn == "count":
        return len(records)
    if fn == "distinct_count":
        seen: set[str] = set()
        for record in records:
            raw = record.get(field) if field else None
            if is_null(raw):
                continue
            seen.add(norm_text(raw))
        return len(seen)
    values = numeric_values(records, field, null_policy)
    if fn == "sum":
        total = 0.0
        for value in values:
            total += value
        return total
    if fn == "avg":
        denominator = len(records) if null_policy == "as_zero" else len(values)
        if denominator == 0:
            return None
        total = 0.0
        for value in values:
            total += value
        return total / denominator
    if fn in ("min", "max"):
        if not values:
            return None
        return min(values) if fn == "min" else max(values)
    if fn == "median":
        if not values:
            return None
        ordered = sorted(values)
        mid = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2
    raise OracleError("semantics_unsupported", f"aggregation not defined by semantics-1.0: {fn}")


def bucket_date(ms: float, granularity: str, tz_offset_minutes: int = 480) -> str:
    shifted = datetime.fromtimestamp((ms + tz_offset_minutes * 60000) / 1000, tz=timezone.utc)
    if granularity == "month":
        return f"{shifted.year:04d}-{shifted.month:02d}"
    return f"{shifted.year:04d}-{shifted.month:02d}-{shifted.day:02d}"


def field_options(fields: list, field_name: str) -> list[str] | None:
    for entry in fields or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("name") != field_name and entry.get("field") != field_name:
            continue
        options = entry.get("options")
        if not isinstance(options, list):
            return None
        resolved = []
        for option in options:
            if isinstance(option, dict):
                resolved.append(str(option.get("name") or option.get("label") or option.get("value")))
            else:
                resolved.append(str(option))
        return resolved
    return None


def group_keys_of(record: dict, group_by: str, null_policy: str, date_granularity: str | None, tz_offset_minutes: int) -> list[str]:
    raw = record.get(group_by)
    if is_null(raw):
        return ["未填写"] if null_policy == "as_category" else []
    if isinstance(raw, list):
        keys = [norm_text(item) for item in raw if not is_null(item)]
        if keys:
            return keys
        return ["未填写"] if null_policy == "as_category" else []
    if date_granularity:
        ms = to_number(raw)
        if ms is None:
            return ["未填写"] if null_policy == "as_category" else []
        return [bucket_date(ms, date_granularity, tz_offset_minutes)]
    return [norm_text(raw)]


def sort_rows(rows: list[dict], sort: dict | None) -> list[dict]:
    sort = dict(sort or {})
    if isinstance(sort.get("values"), list) and not sort.get("custom_order"):
        sort = {"by": "custom", "custom_order": sort["values"]}
    by = sort.get("by") or "value"
    ascending = sort.get("order") == "asc"

    if by == "custom":
        index = {norm_text(label): position for position, label in enumerate(sort.get("custom_order") or [])}
        return sorted(rows, key=lambda row: (index.get(row["label"], math.inf), row["label"]))
    if by == "label":
        return sorted(rows, key=lambda row: row["label"], reverse=not ascending)
    # by value; None sorts as -inf; ties broken by label code-point ascending
    def primary(row: dict) -> float:
        return -math.inf if row["value"] is None else row["value"]
    if ascending:
        return sorted(rows, key=lambda row: (primary(row), row["label"]))
    ordered = sorted(rows, key=lambda row: row["label"])
    return sorted(ordered, key=primary, reverse=True)


def group_aggregate(records: list[dict], config: dict) -> list[dict]:
    group_by = config.get("group_by")
    value_field = config.get("value_field")
    fn = config.get("function") or "count"
    null_policy = config.get("null_policy") or "exclude"
    zero_policy = config.get("zero_policy") or "show"
    tz_offset = config.get("tz_offset_minutes", 480)
    date_granularity = config.get("date_granularity")

    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for record in records:
        for key in group_keys_of(record, group_by, null_policy, date_granularity, tz_offset):
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(record)

    if zero_policy in ("show", "placeholder") and config.get("fields"):
        declared = field_options(config["fields"], group_by)
        for label in declared or []:
            key = norm_text(label)
            if key not in groups:
                groups[key] = []
                order.append(key)

    grand_total = aggregate_field(records, value_field, "sum", null_policy) if fn == "percentage" else None
    rows = []
    for label in order:
        members = groups[label]
        if fn == "percentage":
            part = aggregate_field(members, value_field, "sum", null_policy)
            value = None if grand_total == 0 else part / grand_total * 100
        else:
            value = aggregate_field(members, value_field, fn, null_policy)
        rows.append({"label": label, "value": value, "count": len(members)})

    if zero_policy == "hide":
        rows = [row for row in rows if row["value"] not in (0, None)]
    rows = sort_rows(rows, config.get("sort"))
    if null_policy == "as_category":
        tail = [row for row in rows if row["label"] == "未填写"]
        rows = [row for row in rows if row["label"] != "未填写"] + tail
    return rows


# ------------------------- membership (semantics-1.0) -------------------------

def _normalize_ast(ast: dict | None) -> dict:
    if not ast:
        return {"op": "and", "children": []}
    op = ast.get("op")
    if op == "all":
        return {"op": "and", "children": []}
    if op == "is_null":
        return {"op": "eq", "field": ast.get("field"), "value": None}
    if op == "not_null":
        return {"op": "ne", "field": ast.get("field"), "value": None}
    node = {"op": op, "field": ast.get("field"), "value": ast.get("value")}
    if op == "in" and "value" not in ast and isinstance(ast.get("values"), list):
        node["value"] = ast["values"]
    children = ast.get("children", ast.get("items"))
    if isinstance(children, list):
        node["children"] = [_normalize_ast(child) for child in children]
    return node


def _eq_scalar(field_value: Any, target: Any) -> bool:
    if target is None:
        return is_null(field_value)
    if is_null(field_value):
        return False
    if isinstance(target, (int, float)) and not isinstance(target, bool):
        num = to_number(field_value)
        if num is not None:
            return num == float(target)
    return norm_text(field_value) == norm_text(target)


def eval_ast(record: dict, ast: dict | None) -> bool:
    node = _normalize_ast(ast)
    op = node["op"]
    children = node.get("children") or []
    if op == "and":
        return all(eval_ast(record, child) for child in children)
    if op == "or":
        return any(eval_ast(record, child) for child in children)
    if op == "not":
        if len(children) != 1:
            raise OracleError("semantics_unsupported", "not requires exactly one child")
        return not eval_ast(record, children[0])

    actual = record.get(node.get("field"))
    elements = actual if isinstance(actual, list) else [actual]
    value = node.get("value")

    if op == "eq":
        if value is None:
            return is_null(actual)
        return any(_eq_scalar(element, value) for element in elements)
    if op == "ne":
        return not eval_ast(record, {"op": "eq", "field": node.get("field"), "value": value})
    if op == "in":
        items = value if isinstance(value, list) else []
        if is_null(actual):
            return any(item is None for item in items)
        return any(_eq_scalar(element, item) for element in elements for item in items)
    if op == "contains":
        if is_null(actual) or value is None:
            return False
        needle = norm_text(value)
        if needle == "":
            return False
        return any(not is_null(element) and needle in norm_text(element) for element in elements)
    if op in ("gt", "gte", "lt", "lte"):
        left = None if is_null(actual) else to_number(actual)
        right = to_number(value)
        if left is None or right is None:
            return False
        return {"gt": left > right, "gte": left >= right, "lt": left < right, "lte": left <= right}[op]
    raise OracleError("semantics_unsupported", f"operator not defined by semantics-1.0: {op}")


def filter_records(records: list[dict], ast: dict | None) -> list[dict]:
    return [record for record in records if eval_ast(record, ast)]


# ------------------------------ snapshot loading ------------------------------

def find_records(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        rows = payload["records"]
    elif isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return find_records(payload["data"])
    else:
        rows = []
    result = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        cells = row.get("cells") if isinstance(row.get("cells"), dict) else row
        flat = dict(cells)
        record_id = row.get("recordId") or row.get("rowId")
        if record_id:
            flat["__record_id"] = record_id
        else:
            flat["__local_row_key"] = row.get("localRowKey") or f"local-{index + 1}"
        result.append(flat)
    return result


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def member_digest(keys: list[str]) -> str:
    joined = "\n".join(sorted(keys))
    return "sha256:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()


# --------------------------------- oracle build --------------------------------

def normalize_chart_config(chart: dict, fields: list) -> dict:
    agg = chart.get("aggregation") if isinstance(chart.get("aggregation"), dict) else {}
    legacy_fn = chart.get("aggregation") if isinstance(chart.get("aggregation"), str) else None
    return {
        "group_by": agg.get("group_by") or chart.get("dimension"),
        "value_field": agg.get("value_field") or chart.get("measure"),
        "function": agg.get("function") or legacy_fn or "count",
        "null_policy": chart.get("null_policy") or "exclude",
        "zero_policy": chart.get("zero_policy") or "show",
        "sort": chart.get("sort"),
        "date_granularity": chart.get("date_granularity"),
        "fields": fields,
    }


def build_oracle(spec: dict, records: list[dict], fields: list, keymap: dict[str, str] | None,
                 snapshot_sha256: str, report_spec_sha256: str) -> dict:
    confidentiality = (spec.get("report") or {}).get("confidentiality", "internal")
    if confidentiality == "external_masked" and keymap is None:
        raise OracleError("keymap_missing", "external_masked 等级必须提供 --keymap（recordId → member_key 映射）")

    oracle: dict[str, Any] = {
        "oracle_version": ORACLE_VERSION,
        "snapshot_sha256": snapshot_sha256,
        "report_spec_sha256": report_spec_sha256,
        "semantics_version": spec.get("semantics_version", SEMANTICS_VERSION),
        "runtime_contract_version": RUNTIME_CONTRACT_VERSION,
        "runtime_asset_sha256": RUNTIME_ASSET_SHA256,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "confidentiality": confidentiality,
        "metrics": {},
        "charts": {},
        "drilldowns": {},
    }

    for metric in spec.get("metrics", []):
        formula = metric.get("formula")
        if not isinstance(formula, dict) or not formula.get("aggregation"):
            oracle["metrics"][metric["id"]] = {"source": "declared"}
            continue
        scoped = filter_records(records, metric["filter_ast"]) if metric.get("filter_ast") else records
        field = (formula.get("fields") or [None])[0]
        value = aggregate_field(scoped, field, formula["aggregation"], metric.get("null_policy", "exclude"))
        tolerance = metric.get("tolerance") or {"type": "exact"}
        oracle["metrics"][metric["id"]] = {"expected": value, "tolerance": tolerance, "source": "computed"}

    for chart in spec.get("charts", []):
        config = normalize_chart_config(chart, fields)
        if not config["group_by"]:
            oracle["charts"][chart["id"]] = {"source": "declared"}
            continue
        rows = group_aggregate(records, config)
        values = [row["value"] for row in rows]
        oracle["charts"][chart["id"]] = {
            "categories": [row["label"] for row in rows],
            "values": values,
            "total": sum(value for value in values if value is not None),
        }

    for drill in spec.get("drilldowns", []):
        ast = (drill.get("membership") or {}).get("filter_ast")
        members = filter_records(records, ast) if ast else list(records)
        entry: dict[str, Any] = {"expected_count": len(members), "mode": drill.get("mode")}
        if confidentiality != "public" and drill.get("mode") != "aggregate_only":
            keys = []
            for record in members:
                raw_key = record.get("__record_id") or record.get("__local_row_key")
                if raw_key is None:
                    continue
                if confidentiality == "external_masked":
                    mapped = (keymap or {}).get(str(raw_key))
                    if mapped is None:
                        raise OracleError("keymap_missing", f"keymap 缺少 recordId 映射：{raw_key}")
                    keys.append(mapped)
                else:
                    keys.append(str(raw_key))
            entry["member_digest"] = member_digest(keys)
        oracle["drilldowns"][drill["id"]] = entry

    return oracle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", help="含 records.json / fields.json / manifest.json 的快照目录")
    parser.add_argument("--records", help="records.json 路径（与 --snapshot-dir 二选一）")
    parser.add_argument("--fields", help="fields.json 路径")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--keymap", help="external_masked 等级的 recordId→member_key 映射（内部构建产物，禁止交付）")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.exists():
        raise OracleError("spec_invalid", f"规格文件不存在：{spec_path}")
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise OracleError("spec_invalid", f"规格不是合法 JSON：{error}")

    if args.snapshot_dir:
        records_path = Path(args.snapshot_dir) / "records.json"
        fields_path = Path(args.snapshot_dir) / "fields.json"
    else:
        if not args.records:
            raise OracleError("snapshot_corrupt", "必须提供 --snapshot-dir 或 --records")
        records_path = Path(args.records)
        fields_path = Path(args.fields) if args.fields else None
    if not records_path.exists():
        raise OracleError("snapshot_corrupt", f"记录文件不存在：{records_path}")

    records = find_records(json.loads(records_path.read_text(encoding="utf-8")))
    fields = []
    if fields_path and fields_path.exists():
        payload = json.loads(fields_path.read_text(encoding="utf-8"))
        fields = payload if isinstance(payload, list) else payload.get("fields", [])

    keymap = None
    if args.keymap:
        keymap = json.loads(Path(args.keymap).read_text(encoding="utf-8"))

    for referenced in [c.get("aggregation", {}).get("group_by") for c in spec.get("charts", []) if isinstance(c.get("aggregation"), dict)]:
        if referenced and records and not any(referenced in record for record in records):
            raise OracleError("field_missing", f"规格引用的字段在快照中不存在：{referenced}")

    oracle = build_oracle(
        spec, records, fields, keymap,
        snapshot_sha256=sha256_file(records_path),
        report_spec_sha256=sha256_file(spec_path),
    )
    output = Path(args.output)
    output.write_text(json.dumps(oracle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output))


if __name__ == "__main__":
    main()
