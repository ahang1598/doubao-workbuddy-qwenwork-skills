#!/usr/bin/env python3
"""Aggregate atomic finance-model checks into G0-G5 quality gates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


STATUSES = {"PASS", "INCOMPLETE", "FAIL", "NOT_APPLICABLE"}
WORKFLOWS = {"dcf", "comps", "lbo", "three_statements"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError(f"path escapes task root: {relative}")
    return candidate


def normalize_status(payload: dict[str, Any]) -> str:
    for key in ("status", "model_status_code", "model_status"):
        value = payload.get(key)
        if isinstance(value, str) and value.upper() in STATUSES:
            return value.upper()
    if payload.get("valid") is True:
        return "PASS"
    if payload.get("valid") is False:
        return "FAIL"
    return "INCOMPLETE"


def locate(root: Path, names: Iterable[str]) -> Path | None:
    directories = (root, root / "quality", root / "outputs", root / "calculation")
    for directory in directories:
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def load_atomic(root: Path, check_id: str, names: list[str], required: bool = True) -> dict[str, Any]:
    path = locate(root, names)
    if path is None:
        return {
            "check_id": check_id,
            "status": "INCOMPLETE" if required else "NOT_APPLICABLE",
            "required": required,
            "result_file": None,
            "errors": ["缺少机器验证结果：" + " / ".join(names)] if required else [],
            "warnings": [],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        status = normalize_status(payload)
        parse_error = None
    except (OSError, json.JSONDecodeError) as exc:
        payload = {}
        status = "INCOMPLETE"
        parse_error = str(exc)
    errors = list(payload.get("errors") or [])
    warnings = list(payload.get("warnings") or [])
    if parse_error:
        errors.append(f"无法解析验证结果：{parse_error}")
    return {
        "check_id": check_id,
        "status": status,
        "required": required,
        "result_file": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
        "result_sha256": file_sha256(path),
        "errors": errors,
        "warnings": warnings,
        "artifact_sha256": payload.get("artifact_sha256") or payload.get("workbook_sha256"),
    }


def aggregate(gate_id: str, label: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    required_statuses = [item["status"] for item in checks if item.get("required", True)]
    if "FAIL" in required_statuses:
        status = "FAIL"
    elif "INCOMPLETE" in required_statuses:
        status = "INCOMPLETE"
    else:
        status = "PASS"
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "checks": checks,
        "errors": [error for item in checks for error in item.get("errors", [])],
        "warnings": [warning for item in checks for warning in item.get("warnings", [])],
    }


def result_names_for_calculation(workflows: set[str]) -> list[tuple[str, list[str]]]:
    mapping = {
        "dcf": ["dcf-validation.json", "calculation-validation.json"],
        "comps": ["comps-validation.json", "calculation-validation.json"],
        "lbo": ["lbo-validation.json", "calculation-validation.json"],
        "three_statements": ["three-statements-validation.json", "calculation-validation.json"],
    }
    return [(f"g3.{workflow}", mapping[workflow]) for workflow in sorted(workflows)]


def build_gates(root: Path, workflows: set[str], hero_relative: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    hero = safe_path(root, hero_relative)
    hero_exists = hero.is_file()
    hero_bytes = hero.stat().st_size if hero_exists else 0
    hero_nonempty = hero_exists and hero_bytes > 0
    hero_hash = file_sha256(hero) if hero_nonempty else None

    g0 = aggregate(
        "G0",
        "任务与读取",
        [
            load_atomic(root, "g0.reading_integrity", ["reading-integrity.json"]),
            load_atomic(root, "g0.execution_plan", ["execution-plan-validation.json"]),
        ],
    )

    g1_checks = [
        load_atomic(root, "g1.announcement_sweep", ["announcement-sweep-validation.json"]),
        load_atomic(root, "g1.source_validation", ["source-validation.json"]),
    ]
    if workflows.intersection({"dcf", "comps"}):
        g1_checks.append(load_atomic(root, "g1.equity_evidence", ["equity-evidence-validation.json"]))
    g1 = aggregate("G1", "证据与时点", g1_checks)

    g2 = aggregate(
        "G2",
        "模型与口径合约",
        [load_atomic(root, "g2.model_contract", ["model-contract-validation.json"])],
    )

    g3 = aggregate(
        "G3",
        "确定性计算",
        [load_atomic(root, check_id, names) for check_id, names in result_names_for_calculation(workflows)],
    )

    g4_checks = [
        load_atomic(root, "g4.unified_model_audit", ["model-audit.json"]),
        load_atomic(root, "g4.formula_semantics", ["formula-semantic-audit.json"]),
        load_atomic(root, "g4.direct_artifact", ["artifact-audit.json"]),
        load_atomic(root, "g4.visual_audit", ["visual-audit.json"]),
    ]
    for item in g4_checks:
        audit_hash = item.get("artifact_sha256")
        if item["status"] == "PASS" and audit_hash != hero_hash:
            item["status"] = "FAIL"
            item["errors"].append("审计工作簿哈希与最终主要交付物不一致")
    g4 = aggregate("G4", "Excel产物", g4_checks)

    parity = load_atomic(root, "g5.cross_artifact_parity", ["cross-artifact-parity.json"])
    delivery_checks = [parity]
    if not hero_exists:
        delivery_checks.append(
            {
                "check_id": "g5.hero",
                "status": "FAIL",
                "required": True,
                "errors": ["主要交付工作簿不存在"],
                "warnings": [],
            }
        )
    elif not hero_nonempty:
        delivery_checks.append(
            {
                "check_id": "g5.hero",
                "status": "FAIL",
                "required": True,
                "errors": ["主要交付工作簿大小为0，不构成已生成的产物"],
                "warnings": [],
            }
        )
    elif hero.suffix.lower() != ".xlsx":
        delivery_checks.append(
            {
                "check_id": "g5.hero",
                "status": "FAIL",
                "required": True,
                "errors": ["正式金融工作流主要交付物必须是.xlsx"],
                "warnings": [],
            }
        )
    else:
        delivery_checks.append(
            {
                "check_id": "g5.hero",
                "status": "PASS",
                "required": True,
                "artifact": hero_relative,
                "artifact_sha256": hero_hash,
                "errors": [],
                "warnings": [],
            }
        )
    g5 = aggregate("G5", "交付与结论", delivery_checks)
    prior_statuses = [g0["status"], g1["status"], g2["status"], g3["status"], g4["status"]]
    if g5["status"] == "PASS" and any(status != "PASS" for status in prior_statuses):
        g5["status"] = "INCOMPLETE"
        g5["errors"].append("上游质量门未全部通过，结论发布仍被阻断")

    manifest = {
        "package_root": str(root),
        "hero": {
            "path": hero_relative,
            "exists": hero_exists,
            "bytes": hero_bytes,
            "sha256": hero_hash,
        },
    }
    return [g0, g1, g2, g3, g4, g5], manifest


def release_decision(overall_status: str) -> dict[str, Any]:
    allowed = overall_status == "PASS"
    return {
        "status": overall_status,
        "conclusion_allowed": allowed,
        "allowed_outputs": (
            ["target_price", "valuation_range", "upside_downside", "investment_conclusion", "model_complete"]
            if allowed
            else ["limitations", "failed_checks", "missing_evidence", "next_steps"]
        ),
        "suppressed_outputs": (
            []
            if allowed
            else [
                "target_price",
                "valuation_range",
                "upside_downside",
                "investment_conclusion",
                "recommended_multiple",
                "moic",
                "irr",
                "model_complete",
            ]
        ),
    }


def run(root: Path, workflows: set[str], hero: str, output_dir: Path) -> dict[str, Any]:
    gates, manifest = build_gates(root, workflows, hero)
    statuses = [gate["status"] for gate in gates]
    overall = "FAIL" if "FAIL" in statuses else ("INCOMPLETE" if "INCOMPLETE" in statuses else "PASS")
    report = {
        "overall_status": overall,
        "workflows": sorted(workflows),
        "hero": hero,
        "gates": {gate["gate_id"]: gate["status"] for gate in gates},
        "conclusion_allowed": overall == "PASS",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    names = {
        "G0": "g0-task.json",
        "G1": "g1-evidence.json",
        "G2": "g2-model-contract.json",
        "G3": "g3-calculation.json",
        "G4": "g4-workbook.json",
        "G5": "g5-delivery.json",
    }
    for gate in gates:
        (output_dir / names[gate["gate_id"]]).write_text(
            json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    decision = release_decision(overall)
    (output_dir / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "release-decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "artifact-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"report": report, "release_decision": decision, "gates": gates}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--workflow", action="append", choices=sorted(WORKFLOWS), required=True)
    parser.add_argument("--hero", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=["fail-fast", "full-audit"], default="fail-fast")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    result = run(root, set(args.workflow), args.hero, output)
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0 if result["report"]["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
