#!/usr/bin/env python3
"""Enforce the 90-point visual QA gate for product posters."""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path


CRITERIA = {
    "product_fidelity": {
        "silhouette_proportions": 8,
        "color_material": 6,
        "packaging_closure_accessories": 6,
        "logo_label": 6,
        "count_orientation": 4,
    },
    "message_conversion": {
        "clear_promise": 6,
        "headline_two_seconds": 5,
        "product_identifiable": 5,
        "benefits_support": 4,
        "cta_offer_path": 5,
    },
    "layout_typography": {
        "hierarchy_reading_order": 6,
        "spacing_safe_zones": 4,
        "product_copy_balance": 4,
        "short_text_accuracy": 4,
        "system_consistency": 2,
    },
    "art_direction": {
        "palette_theme": 4,
        "lighting_material": 4,
        "purposeful_scene_props": 3,
        "recognizable_original_family": 2,
        "thumbnail_impact": 2,
    },
    "trust_finish": {
        "no_fabrication_confusion": 4,
        "no_generation_artifacts": 3,
        "no_unintended_text": 2,
        "resolution_format": 1,
    },
}
CATEGORY_MINIMUMS = {
    "product_fidelity": 25,
    "message_conversion": 20,
    "layout_typography": 16,
    "art_direction": 11,
    "trust_finish": 8,
}
STYLE_DIMENSIONS = {
    "brightness",
    "palette",
    "layout_axis",
    "type_personality",
    "scene_material",
    "density_motifs",
}
EVIDENCE_FLAGS = {
    "anti_template_checked",
    "compared_with_source",
    "claim_provenance_checked",
    "inspected_full_size",
    "inspected_thumbnail",
    "copy_manifest_checked",
    "claims_checked",
    "product_specific_devices_checked",
    "safe_zones_checked",
}

TEMPLATE = {
    "poster": "/absolute/path/poster.png",
    "source_product": "/absolute/path/product.png",
    "concept_preflight_passed": True,
    "evidence": {key: True for key in sorted(EVIDENCE_FLAGS)},
    "hard_rejections": [],
    "scores": {
        category: {criterion: maximum for criterion, maximum in criteria.items()}
        for category, criteria in CRITERIA.items()
    },
    "style_dimensions": {
        "brightness": "high-key",
        "palette": "ivory-blue",
        "layout_axis": "asymmetric",
        "type_personality": "editorial-serif",
        "scene_material": "glass-silk-daylight",
        "density_motifs": "D2-rounded-chips",
    },
}


def validate_report(
    data: dict, require_files: bool
) -> tuple[list[str], list[str], int, dict[str, int]]:
    errors: list[str] = []
    warnings: list[str] = []

    for field in ("poster", "source_product"):
        value = data.get(field)
        if not isinstance(value, str) or not value.startswith("/"):
            errors.append(f"{field} must be an absolute path")
        elif require_files and not Path(value).is_file():
            errors.append(f"{field} does not exist: {value}")

    if data.get("concept_preflight_passed") is not True:
        errors.append("concept_preflight_passed must be true")

    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence must be an object")
    else:
        missing = sorted(key for key in EVIDENCE_FLAGS if evidence.get(key) is not True)
        if missing:
            errors.append("missing required QA evidence: " + ", ".join(missing))

    hard = data.get("hard_rejections")
    if not isinstance(hard, list):
        errors.append("hard_rejections must be an array")
    elif hard:
        errors.append("hard rejection present: " + "; ".join(map(str, hard)))

    scores = data.get("scores")
    category_totals: dict[str, int] = {}
    if not isinstance(scores, dict):
        errors.append("scores must be an object")
    else:
        unknown_categories = set(scores) - set(CRITERIA)
        if unknown_categories:
            errors.append(f"unknown score categories: {sorted(unknown_categories)}")
        for category, criteria in CRITERIA.items():
            supplied = scores.get(category)
            if not isinstance(supplied, dict):
                errors.append(f"scores.{category} must be an object")
                continue
            unknown = set(supplied) - set(criteria)
            missing = set(criteria) - set(supplied)
            if unknown:
                errors.append(f"scores.{category} has unknown criteria: {sorted(unknown)}")
            if missing:
                errors.append(f"scores.{category} is missing: {sorted(missing)}")
            subtotal = 0
            for criterion, maximum in criteria.items():
                value = supplied.get(criterion)
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(f"scores.{category}.{criterion} must be an integer")
                    continue
                if not 0 <= value <= maximum:
                    errors.append(
                        f"scores.{category}.{criterion} must be 0–{maximum}, got {value}"
                    )
                    continue
                subtotal += value
            category_totals[category] = subtotal
            minimum = CATEGORY_MINIMUMS[category]
            if subtotal < minimum:
                errors.append(
                    f"{category} subtotal {subtotal} is below minimum {minimum}"
                )

    total = sum(category_totals.values())
    if total < 90:
        errors.append(f"total score {total} is below 90")

    style = data.get("style_dimensions")
    if not isinstance(style, dict):
        errors.append("style_dimensions must be an object")
    else:
        missing = STYLE_DIMENSIONS - set(style)
        unknown = set(style) - STYLE_DIMENSIONS
        if missing:
            errors.append(f"style_dimensions is missing: {sorted(missing)}")
        if unknown:
            errors.append(f"unknown style dimensions: {sorted(unknown)}")
        for key in STYLE_DIMENSIONS & set(style):
            if not str(style[key]).strip():
                errors.append(f"style_dimensions.{key} must not be blank")

    if total == 100:
        warnings.append("perfect scores require unusually strong evidence; avoid defaulting to 100")

    return errors, warnings, total, category_totals


def validate_batch(reports: list[dict]) -> list[str]:
    errors: list[str] = []
    for left, right in combinations(reports, 2):
        left_name = Path(str(left.get("poster", "left"))).name
        right_name = Path(str(right.get("poster", "right"))).name
        left_style = left.get("style_dimensions", {})
        right_style = right.get("style_dimensions", {})
        if not isinstance(left_style, dict) or not isinstance(right_style, dict):
            continue
        differences = sum(
            left_style.get(key) != right_style.get(key) for key in STYLE_DIMENSIONS
        )
        if differences < 4:
            errors.append(
                f"{left_name} vs {right_name}: only {differences}/6 style dimensions differ"
            )
    return errors


def load(path: str) -> dict:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="*", help="one or more QA report JSON files")
    parser.add_argument("--write-template", metavar="PATH")
    parser.add_argument("--skip-file-exists", action="store_true")
    args = parser.parse_args()

    if args.write_template:
        path = Path(args.write_template)
        path.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n")
        print(path)
        return 0
    if not args.reports:
        parser.error("at least one report is required unless --write-template is used")

    loaded: list[dict] = []
    failed = False
    for report_path in args.reports:
        try:
            report = load(report_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR [{report_path}]: {exc}", file=sys.stderr)
            failed = True
            continue
        loaded.append(report)
        errors, warnings, total, subtotals = validate_report(
            report, not args.skip_file_exists
        )
        for warning in warnings:
            print(f"WARNING [{report_path}]: {warning}")
        if errors:
            failed = True
            for error in errors:
                print(f"ERROR [{report_path}]: {error}", file=sys.stderr)
        else:
            breakdown = ", ".join(f"{key}={value}" for key, value in subtotals.items())
            print(f"PASS [{report_path}]: {total}/100 ({breakdown})")

    batch_errors = validate_batch(loaded)
    if batch_errors:
        failed = True
        for error in batch_errors:
            print(f"ERROR [batch]: {error}", file=sys.stderr)

    if failed:
        print("FAIL: QA gate rejected delivery", file=sys.stderr)
        return 1
    print("PASS: QA gate approved delivery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
