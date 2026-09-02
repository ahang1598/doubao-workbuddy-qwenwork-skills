#!/usr/bin/env python3
"""
verify_cross_doc.py — 跨文件字段一致性核验（Step 1.5 之 2）。

输入：
  --fields  extract_cross_doc_fields.py 输出的 fields.json
  --rules   组织清单中的 cross_doc_rules JSON 数组（或包含该数组的对象）。
            支持旧 severity，也支持 iTerms v2 risk_level。
            或传 "auto" 让脚本根据 fields.json 中"出现在 ≥2 个文件"的字段自动派生

输出 violations JSON：
  {
    "rules": [...],
    "results": [
      {"rule_id":"X-001","field":"unit_price","status":"pass|fail|skip",
       "tolerance":"±5%","values_by_category":{"contract":"120","quote":"125"},
       "deviation":"4.17%","severity":"high","message":"..."}
    ],
    "summary": {"pass":N,"fail":N,"skip":N}
  }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

NUMBER_RE = re.compile(r"-?[0-9]+(?:[,，][0-9]{3})*(?:\.[0-9]+)?")


def parse_number(s: str) -> float | None:
    s = (s or "").strip().replace(",", "").replace("，", "")
    m = NUMBER_RE.search(s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_date(s: str) -> date | None:
    s = (s or "").strip()
    s = s.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-").replace(".", "-")
    s = re.sub(r"-+", "-", s).strip("-")
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_tolerance(t: str) -> tuple[str, float]:
    """返回 (kind, value)。kind ∈ {'exact','percent','days'}。"""
    if not t or t == "exact":
        return "exact", 0.0
    m = re.match(r"^±?([0-9]+(?:\.[0-9]+)?)\s*(%|天|d)$", t.strip())
    if not m:
        return "exact", 0.0
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "%":
        return "percent", val
    return "days", val


def collect_values_by_category(files: list[dict[str, Any]], field: str) -> dict[str, str]:
    """从 fields.json 的 files 数组中按 category 聚合每个 category 的字段第一命中值。"""
    out: dict[str, str] = {}
    for f in files:
        if f.get("category") in out:
            # 已有同 category 文件，跳过保第一份
            continue
        hits = f.get("fields", {}).get(field, [])
        if hits:
            out[f["category"]] = str(hits[0]["value"])
    return out


def rule_severity(rule: dict[str, Any]) -> str:
    """兼容旧 severity 与 iTerms v2 cross_doc_rules[].risk_level。"""
    return str(rule.get("severity") or rule.get("risk_level") or "mid")


def derive_rules(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    field_to_cats: dict[str, list[str]] = {}
    for f in files:
        for fname in f.get("fields", {}):
            field_to_cats.setdefault(fname, [])
            if f["category"] not in field_to_cats[fname]:
                field_to_cats[fname].append(f["category"])
    rules: list[dict[str, Any]] = []
    next_id = 1
    for fname, cats in field_to_cats.items():
        if len(cats) < 2:
            continue
        if fname in ("total_amount", "unit_price", "penalty_rate", "sla_indicator"):
            tolerance, severity = "±5%", "high"
        elif fname in ("delivery_date",):
            tolerance, severity = "±0天", "high"
        elif fname in ("quantity", "warranty_period"):
            tolerance, severity = "exact", "mid"
        else:
            tolerance, severity = "exact", "mid"
        rules.append(
            {
                "rule_id": f"X-{next_id:03d}",
                "field": fname,
                "must_match_across": cats,
                "tolerance": tolerance,
                "severity": severity,
                "note": "auto-derived",
            }
        )
        next_id += 1
    return rules


def evaluate_rule(rule: dict[str, Any], files: list[dict[str, Any]]) -> dict[str, Any]:
    field = rule["field"]
    values = collect_values_by_category(files, field)
    required_cats = rule.get("must_match_across", [])
    missing_cats = [c for c in required_cats if c not in values]
    if missing_cats or len(values) < 2:
        return {
            "rule_id": rule["rule_id"],
            "field": field,
            "status": "skip",
            "tolerance": rule.get("tolerance", "exact"),
            "values_by_category": values,
            "severity": rule_severity(rule),
            "message": f"字段 {field} 在 {missing_cats or '少于 2 份文件'} 中未找到，跳过比对",
        }

    kind, span = parse_tolerance(rule.get("tolerance", "exact"))
    raw_values = list(values.values())
    cat_pairs = list(values.items())

    # 构造比对结果
    if kind == "exact":
        normalized = {c: v.strip().replace(" ", "") for c, v in cat_pairs}
        first = next(iter(normalized.values()))
        status = "pass" if all(v == first for v in normalized.values()) else "fail"
        return {
            "rule_id": rule["rule_id"],
            "field": field,
            "status": status,
            "tolerance": rule.get("tolerance"),
            "values_by_category": values,
            "severity": rule_severity(rule),
            "message": "完全一致" if status == "pass" else f"不一致：{values}",
        }

    if kind == "percent":
        nums = {c: parse_number(v) for c, v in cat_pairs}
        if any(n is None for n in nums.values()):
            return {
                "rule_id": rule["rule_id"],
                "field": field,
                "status": "skip",
                "tolerance": rule.get("tolerance"),
                "values_by_category": values,
                "severity": rule_severity(rule),
                "message": "存在非数值无法解析，跳过",
            }
        vals = [n for n in nums.values() if n is not None]
        ref = max(abs(v) for v in vals) or 1.0
        deviation = (max(vals) - min(vals)) / ref * 100
        ok = deviation <= span
        return {
            "rule_id": rule["rule_id"],
            "field": field,
            "status": "pass" if ok else "fail",
            "tolerance": rule.get("tolerance"),
            "values_by_category": values,
            "deviation": f"{deviation:.2f}%",
            "severity": rule_severity(rule),
            "message": (
                f"偏差 {deviation:.2f}% 在容差 ±{span}% 内"
                if ok
                else f"偏差 {deviation:.2f}% 超过容差 ±{span}%"
            ),
        }

    if kind == "days":
        dates = {c: parse_date(v) for c, v in cat_pairs}
        if any(d is None for d in dates.values()):
            return {
                "rule_id": rule["rule_id"],
                "field": field,
                "status": "skip",
                "tolerance": rule.get("tolerance"),
                "values_by_category": values,
                "severity": rule_severity(rule),
                "message": "存在不可解析日期，跳过",
            }
        ds = sorted(d for d in dates.values() if d is not None)
        diff = (ds[-1] - ds[0]).days
        ok = diff <= span
        return {
            "rule_id": rule["rule_id"],
            "field": field,
            "status": "pass" if ok else "fail",
            "tolerance": rule.get("tolerance"),
            "values_by_category": values,
            "deviation": f"{diff}天",
            "severity": rule_severity(rule),
            "message": (
                f"日期差 {diff} 天在容差 ±{span}天 内"
                if ok
                else f"日期差 {diff} 天超过容差 ±{span}天"
            ),
        }

    return {
        "rule_id": rule["rule_id"],
        "field": field,
        "status": "skip",
        "tolerance": rule.get("tolerance"),
        "values_by_category": values,
        "severity": rule_severity(rule),
        "message": f"不支持的容差表达式: {rule.get('tolerance')}",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fields", required=True, help="extract_cross_doc_fields.py 输出的 fields.json")
    p.add_argument("--rules", required=True, help='cross_doc_rules JSON 路径，或 "auto"')
    p.add_argument("--output", required=True)
    args = p.parse_args()

    fields_payload = json.loads(Path(args.fields).expanduser().read_text(encoding="utf-8"))
    files = fields_payload.get("files", [])

    if args.rules == "auto":
        rules = derive_rules(files)
    else:
        rules_payload = json.loads(Path(args.rules).expanduser().read_text(encoding="utf-8"))
        if isinstance(rules_payload, dict):
            rules = rules_payload.get("cross_doc_rules", [])
        elif isinstance(rules_payload, list):
            rules = rules_payload
        else:
            print("[ERROR] rules 文件结构不识别", file=sys.stderr)
            return 2

    results = [evaluate_rule(r, files) for r in rules]
    summary = {
        "pass": sum(1 for r in results if r["status"] == "pass"),
        "fail": sum(1 for r in results if r["status"] == "fail"),
        "skip": sum(1 for r in results if r["status"] == "skip"),
    }

    out = {"rules": rules, "results": results, "summary": summary}
    Path(args.output).expanduser().write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"ok": True, "summary": summary, "output": args.output}, ensure_ascii=False
        )
    )
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
