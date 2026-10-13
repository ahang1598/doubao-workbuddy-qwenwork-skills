#!/usr/bin/env python3
"""Validate report-spec.json invariants without a JSON-schema dependency."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


TOP_LEVEL = (
    "schema_version",
    "report",
    "sources",
    "metrics",
    "findings",
    "charts",
    "drilldowns",
    "sections",
    "privacy",
    "modes",
    "validation",
)
KINDS = {"data_fact", "rule_calculation", "human_conclusion", "ai_inference"}
DRILL_MODES = {"full", "local_only", "aggregate_only"}
TRIGGER_TYPES = {"chart", "metric", "text", "table"}


def add(errors: list[dict], path: str, message: str) -> None:
    errors.append({"path": path, "message": message})


def array(spec: dict, key: str, errors: list[dict]) -> list:
    value = spec.get(key)
    if not isinstance(value, list):
        add(errors, key, "must be an array")
        return []
    return value


def ids(rows: list[dict], key: str, errors: list[dict]) -> set[str]:
    values = [row.get("id") for row in rows if isinstance(row, dict)]
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            add(errors, f"{key}[{index}].id", "must be a non-empty string")
    duplicates = [value for value, count in Counter(values).items() if value and count > 1]
    for value in duplicates:
        add(errors, key, f"duplicate id: {value}")
    return {value for value in values if isinstance(value, str) and value}


def require(row: dict, fields: tuple[str, ...], base: str, errors: list[dict]) -> None:
    for field in fields:
        if field not in row or row[field] in (None, "", []):
            add(errors, f"{base}.{field}", "is required")


def validate(spec: Any) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    if not isinstance(spec, dict):
        return {"valid": False, "errors": [{"path": "$", "message": "root must be an object"}], "warnings": []}

    for key in TOP_LEVEL:
        if key not in spec:
            add(errors, key, "missing top-level key")
    if spec.get("schema_version") != "1.0":
        add(errors, "schema_version", "must equal 1.0")

    report = spec.get("report") if isinstance(spec.get("report"), dict) else {}
    require(report, ("title", "audience", "purpose", "confidentiality", "snapshot_at"), "report", errors)
    if report.get("confidentiality") not in {"internal", "external_masked", "public"}:
        add(errors, "report.confidentiality", "must be internal, external_masked, or public")

    sources = array(spec, "sources", errors)
    metrics = array(spec, "metrics", errors)
    findings = array(spec, "findings", errors)
    charts = array(spec, "charts", errors)
    drills = array(spec, "drilldowns", errors)
    sections = array(spec, "sections", errors)

    source_ids = ids(sources, "sources", errors)
    metric_ids = ids(metrics, "metrics", errors)
    finding_ids = ids(findings, "findings", errors)
    chart_ids = ids(charts, "charts", errors)
    drill_ids = ids(drills, "drilldowns", errors)
    ids(sections, "sections", errors)
    evidence_ids = source_ids | metric_ids | chart_ids | finding_ids

    for index, source in enumerate(sources):
        if isinstance(source, dict):
            require(source, ("id", "name", "type"), f"sources[{index}]", errors)

    for collection_name, rows in (("metrics", metrics), ("findings", findings)):
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                add(errors, f"{collection_name}[{index}]", "must be an object")
                continue
            base = f"{collection_name}[{index}]"
            require(row, ("id", "kind", "evidence"), base, errors)
            if row.get("kind") not in KINDS:
                add(errors, f"{base}.kind", f"must be one of {sorted(KINDS)}")
            if collection_name == "metrics":
                require(row, ("label", "verification"), base, errors)
            else:
                require(row, ("text",), base, errors)
            evidence = row.get("evidence") if isinstance(row.get("evidence"), list) else []
            if not evidence:
                add(errors, f"{base}.evidence", "must contain at least one evidence reference")
            for ref in evidence:
                if ref not in evidence_ids:
                    add(errors, f"{base}.evidence", f"unknown reference: {ref}")
            if row.get("kind") == "ai_inference" and not row.get("human_approved"):
                add(errors, base, "AI inference requires human_approved=true before formal delivery")

    for index, chart in enumerate(charts):
        if not isinstance(chart, dict):
            add(errors, f"charts[{index}]", "must be an object")
            continue
        base = f"charts[{index}]"
        require(chart, ("id", "title", "question", "type", "source_id", "evidence"), base, errors)
        # 非 count 口径的热力图，每格显示什么必须由规格说清楚。
        # 渲染器不得用成员数冒充——对达成率一类的口径，成员数是记录条数，
        # 与要显示的值毫无关系，而两端一旦都取自同一个错误来源就永远自洽。
        if chart.get("type") == "heatmap" and chart.get("drilldown_required") is not False:
            agg = chart.get("aggregation") if isinstance(chart.get("aggregation"), dict) else {}
            cells = chart.get("cells")
            if agg.get("function") != "count":
                if not isinstance(cells, list) or not cells:
                    add(errors, f"{base}.cells",
                        "a non-count heat-map must declare each cell's value; member count is not the value")
                else:
                    for cell_index, cell in enumerate(cells):
                        if not isinstance(cell, dict) or not all(k in cell for k in ("x", "y", "value")):
                            add(errors, f"{base}.cells[{cell_index}]", "each cell needs x, y and value")
            if isinstance(cells, list):
                seen = set()
                for cell in cells:
                    if not isinstance(cell, dict):
                        continue
                    key = (str(cell.get("x")), str(cell.get("y")))
                    if key in seen:
                        add(errors, f"{base}.cells", f"duplicate cell coordinate {key}")
                    seen.add(key)
        if chart.get("source_id") not in source_ids:
            add(errors, f"{base}.source_id", "does not reference a known source")
        for ref in chart.get("evidence", []):
            if ref not in evidence_ids:
                add(errors, f"{base}.evidence", f"unknown reference: {ref}")
        if chart.get("drilldown_id") and chart["drilldown_id"] not in drill_ids:
            add(errors, f"{base}.drilldown_id", "does not reference a known drilldown")

    for index, drill in enumerate(drills):
        if not isinstance(drill, dict):
            add(errors, f"drilldowns[{index}]", "must be an object")
            continue
        base = f"drilldowns[{index}]"
        require(drill, ("id", "source_id", "columns", "mode"), base, errors)
        if drill.get("source_id") not in source_ids:
            add(errors, f"{base}.source_id", "does not reference a known source")
        if drill.get("mode") not in DRILL_MODES:
            add(errors, f"{base}.mode", f"must be one of {sorted(DRILL_MODES)}")
        if drill.get("mode") != "aggregate_only":
            trigger = drill.get("trigger") if isinstance(drill.get("trigger"), dict) else {}
            membership = drill.get("membership") if isinstance(drill.get("membership"), dict) else {}
            require(trigger, ("type", "ref_id"), f"{base}.trigger", errors)
            require(
                membership,
                ("filter_ast", "expected_record_count", "verification"),
                f"{base}.membership",
                errors,
            )
            trigger_type = trigger.get("type")
            ref_id = trigger.get("ref_id")
            if trigger_type not in TRIGGER_TYPES:
                add(errors, f"{base}.trigger.type", f"must be one of {sorted(TRIGGER_TYPES)}")
            if trigger_type == "chart" and ref_id not in chart_ids:
                add(errors, f"{base}.trigger.ref_id", "does not reference a known chart")
            if trigger_type == "metric" and ref_id not in metric_ids:
                add(errors, f"{base}.trigger.ref_id", "does not reference a known metric")
            if not isinstance(membership.get("filter_ast"), dict):
                add(errors, f"{base}.membership.filter_ast", "must be an object")
            expected = membership.get("expected_record_count")
            if not isinstance(expected, int) or isinstance(expected, bool) or expected < 0:
                add(errors, f"{base}.membership.expected_record_count", "must be a non-negative integer")
            if not isinstance(membership.get("verification"), dict):
                add(errors, f"{base}.membership.verification", "must be an object")

    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            add(errors, f"sections[{index}]", "must be an object")
            continue
        base = f"sections[{index}]"
        require(section, ("id", "label", "title", "purpose"), base, errors)
        for key, known in (("metric_ids", metric_ids), ("finding_ids", finding_ids), ("chart_ids", chart_ids)):
            for ref in section.get(key, []):
                if ref not in known:
                    add(errors, f"{base}.{key}", f"unknown reference: {ref}")

    # Drill-down coverage (hard gate): every data chart (one that has a
    # group_by, or is a heatmap) and every computed statistic must be traceable
    # to its underlying records. Missing coverage fails the spec instead of
    # silently shipping non-drillable charts/metrics. Opt out per item with
    # drilldown_required:false + drilldown_opt_out_reason (e.g. a pure target
    # trend line or a placeholder).
    data_chart_types = {
        "bar", "stacked_bar", "grouped_bar", "line", "area", "pie", "donut",
        "scatter", "radar", "heatmap", "treemap", "funnel",
    }
    chart_cover: set[str] = set()
    metric_cover: set[str] = set()
    # expect_iframe 只有在用例真的打开记录行时才有意义。
    # 只声明不执行，等于凭一句话就解锁了「401 算人工项」这个降级。
    browser_cases = ((spec.get("validation") or {}).get("browser") or {}).get("drills") or []
    for case_index, case in enumerate(browser_cases):
        if isinstance(case, dict) and case.get("expect_iframe") and not case.get("open_row"):
            add(errors, f"validation.browser.drills[{case_index}]",
                "expect_iframe requires open_row: an embedded record can only be checked "
                "by a case that actually opens one")

    for drill in drills:
        if not isinstance(drill, dict):
            continue
        trig = drill.get("trigger") if isinstance(drill.get("trigger"), dict) else {}
        if trig.get("type") == "chart" and trig.get("ref_id"):
            chart_cover.add(trig["ref_id"])
        if trig.get("type") == "metric" and trig.get("ref_id"):
            metric_cover.add(trig["ref_id"])
    for chart in charts:
        if isinstance(chart, dict) and chart.get("drilldown_id"):
            chart_cover.add(chart.get("id"))
    for index, chart in enumerate(charts):
        if not isinstance(chart, dict):
            continue
        ctype = chart.get("type")
        agg = chart.get("aggregation") if isinstance(chart.get("aggregation"), dict) else {}
        needs_drill = ctype in data_chart_types and bool(agg.get("group_by") or ctype == "heatmap")
        if not needs_drill:
            continue
        if chart.get("drilldown_required") is False:
            if not chart.get("drilldown_opt_out_reason"):
                add(errors, f"charts[{index}].drilldown_opt_out_reason", "required when drilldown_required is false")
            continue
        if chart.get("id") not in chart_cover:
            add(errors, f"charts[{index}]", f"data chart '{chart.get('id')}' ({ctype}) must be drillable: each category should open its records. Declare a chart-trigger drilldown (one template per chart is fine), or set drilldown_required:false with drilldown_opt_out_reason.")
    for index, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            continue
        if metric.get("kind") not in {"data_fact", "rule_calculation"}:
            continue
        if metric.get("drilldown_required") is False:
            if not metric.get("drilldown_opt_out_reason"):
                add(errors, f"metrics[{index}].drilldown_opt_out_reason", "required when drilldown_required is false")
            continue
        if metric.get("id") not in metric_cover:
            add(errors, f"metrics[{index}]", f"statistic '{metric.get('id')}' must be traceable to records: declare a metric-trigger drilldown, or set drilldown_required:false with drilldown_opt_out_reason.")

    privacy = spec.get("privacy") if isinstance(spec.get("privacy"), dict) else {}
    if report.get("confidentiality") == "public":
        if privacy.get("allow_record_links") is not False:
            add(errors, "privacy.allow_record_links", "public reports must explicitly disable record links")
        if drills:
            warnings.append({"path": "drilldowns", "message": "public report contains drilldown definitions; verify they expose aggregates only"})

    modes = spec.get("modes") if isinstance(spec.get("modes"), dict) else {}
    presentation = modes.get("presentation") if isinstance(modes.get("presentation"), dict) else {}
    reading = modes.get("reading") if isinstance(modes.get("reading"), dict) else {}
    if not presentation.get("enabled") and not reading.get("enabled"):
        add(errors, "modes", "at least presentation or reading must be enabled")
    if presentation.get("enabled"):
        if presentation.get("stage") != "1920x1080":
            add(errors, "modes.presentation.stage", "must equal 1920x1080")
        if presentation.get("density") not in {"speaker-led", "reading-first"}:
            add(errors, "modes.presentation.density", "must be speaker-led or reading-first")
    if reading.get("enabled") and reading.get("requested_by_user") is not True:
        add(errors, "modes.reading.requested_by_user", "continuous reading mode requires explicit user request")

    if not sections:
        add(errors, "sections", "must contain at least one section")
    if not sources:
        add(errors, "sources", "must contain at least one source")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("--output")
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    result = validate(spec)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
