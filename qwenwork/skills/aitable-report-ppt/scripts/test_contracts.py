#!/usr/bin/env python3
"""Small deterministic contract tests for approval and drill-down gates."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_fetch_module():
    path = ROOT / "scripts/fetch_dingtalk_aitable.py"
    spec = importlib.util.spec_from_file_location("fetch_dingtalk_aitable", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(*args: str, expect: int = 0) -> None:
    completed = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    if completed.returncode != expect:
        raise AssertionError(f"expected exit {expect}, got {completed.returncode}\n{completed.stdout}\n{completed.stderr}")


def load_oracle_module():
    path = ROOT / "scripts/build_verification_oracle.py"
    spec = importlib.util.spec_from_file_location("build_verification_oracle", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def values_equal(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(values_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(values_equal(x, y) for x, y in zip(a, b))
    return a == b


def run_python_semantic_checks(oracle, fixture: Path) -> dict:
    records = json.loads((fixture / "records.json").read_text(encoding="utf-8"))
    fields = json.loads((fixture / "fields.json").read_text(encoding="utf-8"))
    case = json.loads((fixture / "case.json").read_text(encoding="utf-8"))
    results = {}
    for check in case["checks"]:
        kind = check["kind"]
        if kind == "aggregate":
            scoped = oracle.filter_records(records, check["filter_ast"]) if check.get("filter_ast") else records
            results[check["id"]] = oracle.aggregate_field(scoped, check.get("field"), check["function"], check.get("null_policy", "exclude"))
        elif kind == "group":
            rows = oracle.group_aggregate(records, dict(check["config"], fields=fields))
            results[check["id"]] = {"categories": [r["label"] for r in rows], "values": [r["value"] for r in rows]}
        elif kind == "filter":
            results[check["id"]] = {"count": len(oracle.filter_records(records, check["filter_ast"]))}
        elif kind == "format":
            results[check["id"]] = oracle.round_half_away(check["value"], check["decimals"])
        elif kind == "bucket":
            results[check["id"]] = oracle.bucket_date(check["ms"], check["granularity"])
        else:
            raise AssertionError(f"unknown check kind: {kind}")
    return results


def test_semantic_traps() -> None:
    """Three-way comparison per semantics-1.0: Python oracle vs JS runtime,
    both against the human-reviewed expected values. Cross-implementation
    equality is asserted unconditionally; the expected comparison is only
    asserted once a human has set reviewed:true (never let either
    implementation author its own answer key)."""
    oracle = load_oracle_module()
    traps = ROOT / "evals/fixtures/semantic-traps"
    unreviewed = []
    for fixture in sorted(path for path in traps.iterdir() if path.is_dir()):
        expected_file = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))
        expected = expected_file["results"]
        python_results = run_python_semantic_checks(oracle, fixture)
        node = subprocess.run(["node", str(ROOT / "scripts/run_semantic_checks.js"), str(fixture)], capture_output=True, text=True)
        if node.returncode:
            raise AssertionError(f"JS semantic harness failed for {fixture.name}\n{node.stderr}")
        js_results = json.loads(node.stdout)
        for check_id in expected:
            py_value, js_value = python_results.get(check_id), js_results.get(check_id)
            if not values_equal(py_value, js_value):
                raise AssertionError(f"{fixture.name}/{check_id}: python={py_value!r} != js={js_value!r} (双实现分歧)")
            if expected_file.get("reviewed"):
                if not values_equal(py_value, expected[check_id]):
                    raise AssertionError(f"{fixture.name}/{check_id}: 实现结果 {py_value!r} != 审定期望 {expected[check_id]!r}")
        if not expected_file.get("reviewed"):
            unreviewed.append(fixture.name)
    if unreviewed:
        print(f"warning: {len(unreviewed)} fixtures pending human review (expected 未审定，仅比对了双实现一致性): {', '.join(unreviewed)}")


def main() -> None:
    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    confirmation_text = (ROOT / "references/reporting/confirmation-interaction.md").read_text(encoding="utf-8")
    engine_text = (ROOT / "references/presentation/frontend-slides-engine.md").read_text(encoding="utf-8")
    assert "确认必须进入宿主等待态" in skill_text
    assert "原生结构化提问工具" in skill_text
    assert "千问办公硬约束" in skill_text
    assert "--limit 100 --all --page-limit 0" in skill_text
    assert "AskUserQuestion" in confirmation_text
    assert "request_user_input" in confirmation_text
    assert "跳过不等于批准" in confirmation_text
    assert "Stop after asking" in engine_text
    assert "预览不设计、不展示、不验收下钻" in skill_text
    assert "不强制共享页面 DOM 或视觉组件" in skill_text

    fetch = load_fetch_module()
    base_id, table_id, view_id = fetch.parse_aitable_url(
        "https://docs.dingtalk.com/i/nodes/YMyQA2dXW7MwpyPaSZm4Z5PbJzlwrZgb?"
        "iframeQuery=entrance%3Ddata%26sheetId%3DhERWDMS%26viewId%3DqvGDAH2"
    )
    assert (base_id, table_id, view_id) == ("YMyQA2dXW7MwpyPaSZm4Z5PbJzlwrZgb", "hERWDMS", "qvGDAH2")
    assert fetch.classify_error("unknown flag: --max-page-size") == ("command_validation", False)
    assert fetch.classify_error("INVALID_LIMIT: limit must be between 1 and 100") == ("command_validation", False)
    assert fetch.classify_error('{"error":{"type":"SYSTEM_ERROR","retryable":true}}') == ("transient_service", True)
    assert fetch.classify_error('{"error":{"type":"ORG_DOC_TOKEN_MISMATCH","message":"no permission","retryable":false}}') == ("permission", False)

    with tempfile.TemporaryDirectory(prefix="aitable-contracts-") as directory:
        work = Path(directory)
        blueprint_path = work / "content-blueprint.json"
        approval_path = work / "content-approval.json"
        preview_path = work / "preview.html"
        design_path = work / "design-selection.json"
        spec_path = work / "report-spec.json"
        manifest_path = work / "manifest.json"
        records_path = work / "records.json"
        report_path = work / "report.html"

        blueprint = {
            "report": {"title": "测试报告", "purpose": "汇报", "audience": "管理层", "delivery_type": "presentation", "density": "reading-first"},
            "story": {"core_message": "核心结论", "narrative": "先结论后证据", "estimated_slide_count": 1, "chapters": ["总体结果"]},
            "slides": [{
                "id": "slide_overall", "title": "总体结果", "management_question": "结果如何？", "key_message": "已完成核验",
                "body_points": ["结论"], "source_refs": ["source_main"],
                "charts": [{"type": "bar", "title": "分布", "data_summary": "A=1", "metric_ids": ["metric_a"]}],
            }],
        }
        write(blueprint_path, blueprint)
        blueprint_hash = hashlib.sha256(blueprint_path.read_bytes()).hexdigest()
        write(approval_path, {
            "status": "approved", "approved_at": "2026-08-18T16:00:00+08:00", "approval_source": "user_explicit",
            "blueprint_path": str(blueprint_path), "blueprint_sha256": blueprint_hash,
            "approved_scope": ["story", "key_messages", "slide_allocation", "chart_plan"],
            "approved_degradations": ["no_original_record_links"], "requested_changes": [],
        })
        preview_path.write_text(
            "<!doctype html><html><head><meta charset='utf-8'><title>主题预览</title>"
            "<style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}"
            "body{display:grid;place-items:center}.preview-stage{width:min(100vw,calc(100vh * 16 / 9));aspect-ratio:16/9;background:#eef4ff;padding:6%;}</style>"
            "</head><body><main class='preview-stage'><h1>主题预览</h1><p>110 条测试用例</p></main></body></html>\n",
            encoding="utf-8",
        )
        write(design_path, {
            "status": "approved", "selected_preview": "style-b", "approved_at": "2026-08-18T16:01:00+08:00",
            "approval_source": "user_explicit", "selection_mode": "preview", "selected_preview_path": str(preview_path),
            "selected_preview_sha256": hashlib.sha256(preview_path.read_bytes()).hexdigest(),
        })
        spec = {
            "schema_version": "1.0", "report": {"title": "测试", "audience": "管理层", "purpose": "汇报", "confidentiality": "internal", "snapshot_at": "2026-08-18"},
            "sources": [{"id": "source_main", "name": "明细", "type": "aitable"}],
            "metrics": [{"id": "metric_a", "label": "数量", "kind": "data_fact", "evidence": ["source_main"], "verification": "exact"}],
            "findings": [], "charts": [],
            "drilldowns": [{
                "id": "drill_a", "source_id": "source_main", "columns": ["编号"], "mode": "local_only",
                "trigger": {"type": "metric", "ref_id": "metric_a"},
                "membership": {"filter_ast": {"op": "all"}, "expected_record_count": 1, "verification": {"method": "exact"}},
            }],
            "sections": [{"id": "overall", "label": "总体", "title": "总体结果", "purpose": "看结果", "metric_ids": ["metric_a"]}],
            "privacy": {}, "modes": {"presentation": {"enabled": True, "stage": "1920x1080", "density": "reading-first"}, "reading": {"enabled": False, "requested_by_user": False}},
            "validation": {"browser": {"drills": [{
                "drilldown_id": "drill_a", "name": "数量卡下钻", "trigger": "[data-metric-id='metric_a']",
                "modal": ".avd-root.avd-open", "rows": ".avd-table tbody tr", "expected_count": 1,
                "open_row": ".avd-row-button", "back": ".avd-header-back", "close": ".avd-close",
                "hidden_selectors": [".avd-meta", ".avd-source", ".avd-detail-toolbar"],
            }]}}
        }
        write(spec_path, spec)
        write(manifest_path, {"record_id_fidelity": "missing", "record_id_coverage": 0.0, "record_link_coverage": 0.0})
        write(records_path, {"data": {"records": [{"localRowKey": "local-1", "cells": {"编号": "CASE-01"}}]}})

        run(str(ROOT / "scripts/validate_content_blueprint.py"), str(blueprint_path), "--approval", str(approval_path))
        run(str(ROOT / "scripts/validate_theme_selection.py"), str(design_path))
        preview_check = subprocess.run(["node", str(ROOT / "scripts/validate_visual_report.js"), str(preview_path), "--preview"], capture_output=True, text=True)
        if preview_check.returncode:
            raise AssertionError(f"preview validation failed\n{preview_check.stdout}\n{preview_check.stderr}")
        run(str(ROOT / "scripts/validate_report_spec.py"), str(spec_path))
        run(str(ROOT / "scripts/validate_generation_gate.py"), "--spec", str(spec_path), "--blueprint", str(blueprint_path), "--content-approval", str(approval_path), "--design-selection", str(design_path), "--manifest", str(manifest_path))
        run(str(ROOT / "scripts/build_visual_report.py"), "--spec", str(spec_path), "--records", str(records_path), "--output", str(report_path), "--blueprint", str(blueprint_path), "--content-approval", str(approval_path), "--design-selection", str(design_path), "--manifest", str(manifest_path))
        html = report_path.read_text(encoding="utf-8")
        assert "readingModeBtn" not in html
        assert "Standard AI-table drill-down" in html
        assert "class=\"deck-stage\"" in html

        # Baseline guard: the page must consume the shared runtime and must not
        # carry a second implementation of correctness-critical logic.
        assert 'data-inlined="runtime"' in html, "baseline must inline report-runtime.js"
        assert "VisualReportRuntime.create" in html, "baseline must create the runtime"
        for forbidden in ("function aggregate(", "function matches(", "function rowsFor(", "function openDrill("):
            assert forbidden not in html, f"duplicate implementation leaked into baseline HTML: {forbidden}"

        # Independent oracle: built from the same snapshot + spec, compared by
        # the browser validator against the page's observation-only API.
        oracle_path = work / "verification-oracle.json"
        run(str(ROOT / "scripts/build_verification_oracle.py"), "--records", str(records_path), "--spec", str(spec_path), "--output", str(oracle_path))
        run(str(ROOT / "scripts/validate_generation_gate.py"), "--spec", str(spec_path), "--blueprint", str(blueprint_path), "--content-approval", str(approval_path), "--design-selection", str(design_path), "--manifest", str(manifest_path), "--oracle", str(oracle_path))
        browser_check = subprocess.run(["node", str(ROOT / "scripts/validate_visual_report.js"), str(report_path), str(spec_path), "--oracle", str(oracle_path)], capture_output=True, text=True)
        if browser_check.returncode:
            raise AssertionError(f"browser validation failed\n{browser_check.stdout}\n{browser_check.stderr}")

        # Drill coverage gate: a data chart with group_by but no drilldown must
        # fail spec validation (every data chart / statistic must be drillable).
        spec_cov = json.loads(spec_path.read_text(encoding="utf-8"))
        spec_cov["charts"].append({
            "id": "chart_uncovered", "title": "未覆盖", "question": "?", "type": "bar",
            "source_id": "source_main", "evidence": ["source_main"],
            "aggregation": {"group_by": "编号", "value_field": "编号", "function": "count"},
        })
        write(spec_path, spec_cov)
        run(str(ROOT / "scripts/validate_report_spec.py"), str(spec_path), expect=1)
        # opting out with a reason makes it pass again
        spec_cov["charts"][-1]["drilldown_required"] = False
        spec_cov["charts"][-1]["drilldown_opt_out_reason"] = "回归测试占位图，无需下钻"
        write(spec_path, spec_cov)
        run(str(ROOT / "scripts/validate_report_spec.py"), str(spec_path))
        write(spec_path, spec)

        # member-keymap.json is an internal build artifact and must never ship.
        (work / "member-keymap.json").write_text("{}", encoding="utf-8")
        run(str(ROOT / "scripts/validate_generation_gate.py"), "--spec", str(spec_path), "--blueprint", str(blueprint_path), "--content-approval", str(approval_path), "--design-selection", str(design_path), "--manifest", str(manifest_path), "--delivery-dir", str(work), expect=1)
        (work / "member-keymap.json").unlink()

        # Overreach guard 1: invented delivery-scope fields in design-selection
        # must fail both the theme validator and the generation gate.
        design = json.loads(design_path.read_text(encoding="utf-8"))
        design["additional_full_versions"] = ["style-a", "style-c"]
        overreach_path = work / "design-selection-overreach.json"
        write(overreach_path, design)
        run(str(ROOT / "scripts/validate_theme_selection.py"), str(overreach_path), expect=1)
        run(str(ROOT / "scripts/validate_generation_gate.py"), "--spec", str(spec_path), "--blueprint", str(blueprint_path), "--content-approval", str(approval_path), "--design-selection", str(overreach_path), "--manifest", str(manifest_path), expect=1)

        # Overreach guard 2: delivering more reports than the approved single
        # selection must fail the delivery-dir check.
        (work / "report-extra.html").write_text("<html></html>", encoding="utf-8")
        run(str(ROOT / "scripts/validate_generation_gate.py"), "--spec", str(spec_path), "--blueprint", str(blueprint_path), "--content-approval", str(approval_path), "--design-selection", str(design_path), "--manifest", str(manifest_path), "--delivery-dir", str(work), expect=1)
        (work / "report-extra.html").unlink()
        # single report + approved single selection passes the same check
        run(str(ROOT / "scripts/validate_generation_gate.py"), "--spec", str(spec_path), "--blueprint", str(blueprint_path), "--content-approval", str(approval_path), "--design-selection", str(design_path), "--manifest", str(manifest_path), "--delivery-dir", str(work))

        # A full original-record drill-down must fail without complete real IDs and links.
        spec["drilldowns"][0]["mode"] = "full"
        write(spec_path, spec)
        run(str(ROOT / "scripts/validate_generation_gate.py"), "--spec", str(spec_path), "--blueprint", str(blueprint_path), "--content-approval", str(approval_path), "--design-selection", str(design_path), "--manifest", str(manifest_path), expect=1)

        # A stale oracle (built before the spec changed) must hard-fail the gate,
        # even when the change is otherwise harmless (title only).
        spec["drilldowns"][0]["mode"] = "local_only"
        spec["report"]["title"] = "测试·改标题"
        write(spec_path, spec)
        run(str(ROOT / "scripts/validate_generation_gate.py"), "--spec", str(spec_path), "--blueprint", str(blueprint_path), "--content-approval", str(approval_path), "--design-selection", str(design_path), "--manifest", str(manifest_path), "--oracle", str(oracle_path), expect=1)
        spec["report"]["title"] = "测试"

        # A continuous reading page cannot be silently enabled.
        spec["drilldowns"][0]["mode"] = "local_only"
        spec["modes"]["reading"] = {"enabled": True, "requested_by_user": False}
        write(spec_path, spec)
        run(str(ROOT / "scripts/validate_report_spec.py"), str(spec_path), expect=1)

    test_semantic_traps()
    print("contract tests passed")


if __name__ == "__main__":
    main()
