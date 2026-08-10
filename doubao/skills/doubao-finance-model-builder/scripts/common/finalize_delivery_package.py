#!/usr/bin/env python3
"""Create a deterministic run record and hash manifest without copying artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_STAGES = (
    "scope_locked",
    "equity_evidence_frozen",
    "evidence_frozen",
    "calculation_validated",
    "artifact_verified",
    "formula_semantics_audited",
    "artifact_directly_audited",
    "delivery_validated",
)
ALLOWED = {"PASS", "INCOMPLETE", "FAIL"}


def safe_file(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError(f"artifact path escapes package root: {relative}")
    return candidate


def record(root: Path, relative: str, role: str) -> dict[str, Any]:
    path = safe_file(root, relative)
    if not path.is_file():
        return {"path": relative, "role": role, "exists": False, "bytes": 0, "sha256": None}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": relative, "role": role, "exists": True, "bytes": path.stat().st_size, "sha256": digest}


def build(plan: dict[str, Any], stage_results: dict[str, Any], root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    stages_input = stage_results.get("stages", {})
    stages: dict[str, str] = {}
    hard_failures = list(stage_results.get("hard_failures", []))
    warnings = list(stage_results.get("warnings", []))
    equity_required = plan.get("meta", {}).get("model_purpose") == "formal" and bool(set(plan.get("workflows", [])) & {"dcf", "comps"})
    required_stages = REQUIRED_STAGES if equity_required else tuple(name for name in REQUIRED_STAGES if name != "equity_evidence_frozen")
    deliverables = plan.get("deliverables", {})
    hero = deliverables.get("hero")
    formal_workbook = plan.get("meta", {}).get("model_purpose") == "formal" and bool(
        set(plan.get("workflows", [])) & {"three_statements", "dcf", "lbo", "comps"}
    )
    if formal_workbook and (not isinstance(hero, str) or not hero.lower().endswith(".xlsx")):
        hard_failures.append("formal finance workflow requires an .xlsx hero artifact")
    for name in required_stages:
        if name == "equity_evidence_frozen":
            raw = stages_input.get(name)
            if not isinstance(raw, dict) or raw.get("evidence_file") != "equity-evidence-validation.json":
                hard_failures.append("equity_evidence_frozen requires equity-evidence-validation.json")
                stages[name] = "FAIL"
                continue
            evidence_file = safe_file(root, raw["evidence_file"])
            try:
                evidence_payload = json.loads(evidence_file.read_text(encoding="utf-8"))
                status = evidence_payload.get("model_status_code")
            except (OSError, json.JSONDecodeError):
                status = "FAIL"
                evidence_payload = {}
            manifest_file = safe_file(root, "equity-evidence.json")
            manifest_hash = hashlib.sha256(manifest_file.read_bytes()).hexdigest() if manifest_file.is_file() else None
            if raw.get("status") != "PASS" or status != "PASS" or evidence_payload.get("manifest_sha256") != manifest_hash:
                hard_failures.append("equity evidence validation did not pass")
                stages[name] = "FAIL"
            else:
                stages[name] = "PASS"
            continue
        if name == "artifact_directly_audited":
            raw = stages_input.get(name)
            if not isinstance(raw, dict) or raw.get("status") != "PASS" or not isinstance(raw.get("audit_file"), str):
                hard_failures.append("artifact_directly_audited requires a PASS audit_file")
                stages[name] = "FAIL"
                continue
            audit_file = safe_file(root, raw["audit_file"])
            try:
                audit_payload = json.loads(audit_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                audit_payload = {}
            hero_file = safe_file(root, hero) if isinstance(hero, str) and hero else None
            hero_hash = hashlib.sha256(hero_file.read_bytes()).hexdigest() if hero_file and hero_file.is_file() else None
            audit_hash = audit_payload.get("artifact_sha256") or audit_payload.get("workbook_sha256")
            workflow_ok = audit_payload.get("workflow") in set(plan.get("workflows", []))
            if audit_payload.get("status") != "PASS" or audit_hash != hero_hash or not workflow_ok:
                hard_failures.append("direct artifact audit did not pass, match the hero hash, and match the workflow")
                stages[name] = "FAIL"
            else:
                stages[name] = "PASS"
            continue
        if name == "formula_semantics_audited":
            raw = stages_input.get(name)
            if not isinstance(raw, dict) or raw.get("status") != "PASS" or not isinstance(raw.get("audit_file"), str):
                hard_failures.append("formula_semantics_audited requires a PASS audit_file")
                stages[name] = "FAIL"
                continue
            audit_file = safe_file(root, raw["audit_file"])
            try:
                audit_payload = json.loads(audit_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                audit_payload = {}
            hero_file = safe_file(root, hero) if isinstance(hero, str) and hero else None
            hero_hash = hashlib.sha256(hero_file.read_bytes()).hexdigest() if hero_file and hero_file.is_file() else None
            workflow_ok = audit_payload.get("workflow") in set(plan.get("workflows", []))
            if (
                audit_payload.get("status") != "PASS"
                or audit_payload.get("artifact_sha256") != hero_hash
                or not workflow_ok
            ):
                hard_failures.append("formula semantic audit did not pass, match the hero hash, and match the workflow")
                stages[name] = "FAIL"
            else:
                stages[name] = "PASS"
            continue
        status = stages_input.get(name, "INCOMPLETE")
        if status not in ALLOWED:
            hard_failures.append(f"invalid stage status for {name}: {status}")
            status = "FAIL"
        stages[name] = status

    support = deliverables.get("support", [])
    files: list[dict[str, Any]] = []
    if isinstance(hero, str) and hero:
        files.append(record(root, hero, "hero"))
    else:
        hard_failures.append("deliverables.hero is missing")
    for item in support if isinstance(support, list) else []:
        if isinstance(item, str) and item:
            files.append(record(root, item, "support"))

    missing_hero = any(item["role"] == "hero" and not item["exists"] for item in files)
    missing_support = [item["path"] for item in files if item["role"] == "support" and not item["exists"]]
    if missing_hero:
        hard_failures.append("hero artifact is missing")
    if missing_support:
        warnings.append("missing support artifacts: " + ", ".join(missing_support))

    if hard_failures or "FAIL" in stages.values():
        model_status = "FAIL"
    elif missing_support or "INCOMPLETE" in stages.values():
        model_status = "INCOMPLETE"
    else:
        model_status = "PASS"

    run_record = {
        "task_id": plan.get("meta", {}).get("task_id"),
        "workflows": plan.get("workflows", []),
        "stages": stages,
        "model_status": model_status,
        "hard_failures": sorted(set(hard_failures)),
        "warnings": sorted(set(warnings)),
        "conclusion_allowed": model_status == "PASS" and plan.get("result_policy", {}).get("conclusion_requires_pass") is True,
    }
    manifest = {"package_root": str(root.resolve()), "files": files, "model_status": model_status}
    return run_record, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="生成建模交付包运行记录和哈希清单")
    parser.add_argument("plan", type=Path)
    parser.add_argument("stage_results", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    stages = json.loads(args.stage_results.read_text(encoding="utf-8"))
    run_record, manifest = build(plan, stages, args.root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "run-record.json").write_text(json.dumps(run_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "artifact-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run_record, ensure_ascii=False, indent=2))
    return 0 if run_record["model_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
