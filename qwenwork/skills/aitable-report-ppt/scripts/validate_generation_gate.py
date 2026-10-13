#!/usr/bin/env python3
"""Refuse formal generation until content, design and drill-down capability are approved."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def load(path: str | None, label: str, errors: list[str]) -> dict[str, Any]:
    if not path:
        errors.append(f"missing {label} path")
        return {}
    target = Path(path).resolve()
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"cannot read {label}: {error}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    return value


def file_hash(path: str) -> str:
    return hashlib.sha256(Path(path).resolve().read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--blueprint", required=True)
    parser.add_argument("--content-approval", required=True)
    parser.add_argument("--design-selection", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--oracle", help="verification-oracle.json 路径；提供时校验其指纹与当前规格一致")
    parser.add_argument("--delivery-dir", help="交付目录；提供时校验 member-keymap.json 未混入交付物")
    parser.add_argument("--output")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    spec = load(args.spec, "report spec", errors)
    blueprint = load(args.blueprint, "content blueprint", errors)
    content = load(args.content_approval, "content approval", errors)
    design = load(args.design_selection, "design selection", errors)
    manifest = load(args.manifest, "snapshot manifest", errors) if args.manifest else {}

    if content.get("status") != "approved" or content.get("approval_source") != "user_explicit":
        errors.append("core framework and content must be explicitly approved")
    try:
        blueprint_hash = file_hash(args.blueprint)
    except OSError as error:
        blueprint_hash = None
        errors.append(f"cannot hash content blueprint: {error}")
    if blueprint_hash and content.get("blueprint_sha256") != blueprint_hash:
        errors.append("content approval does not match the current blueprint")

    if design.get("status") != "approved" or not design.get("selected_preview"):
        errors.append("visual theme must be explicitly approved")
    if design.get("approval_source") != "user_explicit":
        errors.append("design approval_source must equal user_explicit")
    selection_mode = design.get("selection_mode")
    if selection_mode not in {"preview", "user_named_theme", "reuse_previous", "all_versions"}:
        errors.append("design selection_mode is invalid")
    # Contract whitelist: delivery scope is expressed ONLY by selection_mode.
    # Invented fields (e.g. additional_full_versions) that widen delivery
    # beyond the user's current-session choice are a hard failure.
    allowed_design_fields = {
        "status", "selected_preview", "approved_at", "approval_source", "selection_mode",
        "selected_preview_path", "selected_preview_sha256", "note", "requested_changes",
    }
    unknown_design_fields = sorted(set(design) - allowed_design_fields)
    if unknown_design_fields:
        errors.append(
            f"design selection contains unknown fields {unknown_design_fields}; "
            "delivery scope beyond the selected theme requires the user to explicitly "
            "choose selection_mode=all_versions on the confirmation card in this session"
        )
    if selection_mode == "preview":
        preview_path = design.get("selected_preview_path")
        preview_hash = design.get("selected_preview_sha256")
        if not preview_path or not preview_hash:
            errors.append("preview selection requires path and SHA-256")
        else:
            try:
                if file_hash(preview_path) != preview_hash:
                    errors.append("selected preview changed after approval")
            except OSError as error:
                errors.append(f"cannot verify selected preview: {error}")

    modes = spec.get("modes") if isinstance(spec.get("modes"), dict) else {}
    enabled = [name for name in ("presentation", "reading") if isinstance(modes.get(name), dict) and modes[name].get("enabled")]
    if not enabled:
        errors.append("at least one output mode must be enabled")
    if modes.get("reading", {}).get("enabled") and not modes.get("reading", {}).get("requested_by_user"):
        errors.append("continuous reading mode requires explicit user request")

    degradations = set(content.get("approved_degradations") or [])
    drills = spec.get("drilldowns") if isinstance(spec.get("drilldowns"), list) else []
    full_drills = [drill for drill in drills if isinstance(drill, dict) and drill.get("mode") == "full"]
    local_drills = [drill for drill in drills if isinstance(drill, dict) and drill.get("mode") == "local_only"]
    if full_drills:
        if not manifest:
            errors.append("full original-record drill-down requires a snapshot manifest")
        elif manifest.get("record_id_fidelity") != "real" or manifest.get("record_id_coverage") != 1.0 or manifest.get("record_link_coverage") != 1.0:
            errors.append("full drill-down requires 100% real record IDs and 100% real record links")
    if local_drills and manifest and manifest.get("record_link_coverage", 0) < 1.0:
        if "no_original_record_links" not in degradations:
            errors.append("local-only drill-down degradation has not been explicitly approved")
        else:
            warnings.append("formal output uses approved local-only drill-down")
    if manifest.get("record_id_fidelity") not in (None, "real", "missing"):
        errors.append("synthetic IDs must never be represented as record IDs")

    blueprint_slides = blueprint.get("slides") or []
    if not blueprint_slides:
        errors.append("content blueprint has no page-by-page content list")
    else:
        # 蓝图与规格必须真的对得上。此前只检查"蓝图非空"，于是一份声明 1 页的
        # 蓝图可以放行一份 3 页的规格——用户确认过的内容和实际生成的内容各说各话，
        # 而内容确认关卡的全部意义就在于两者一致。
        sections = spec.get("sections") or [] if isinstance(spec, dict) else []
        declared = (blueprint.get("story") or {}).get("estimated_slide_count")
        if isinstance(declared, int) and declared != len(blueprint_slides):
            errors.append(
                f"blueprint story.estimated_slide_count ({declared}) does not match its own "
                f"slides list ({len(blueprint_slides)})")
        if sections and len(blueprint_slides) != len(sections):
            errors.append(
                f"approved blueprint has {len(blueprint_slides)} pages but the spec generates "
                f"{len(sections)} — the user approved different content from what will be built")
        blueprint_ids = [s.get("id") for s in blueprint_slides if isinstance(s, dict) and s.get("id")]
        section_ids = [s.get("id") for s in sections if isinstance(s, dict) and s.get("id")]
        if blueprint_ids and section_ids and len(blueprint_ids) == len(section_ids):
            # 要抓的是「页面对不上」——少了一页、多了一页、张冠李戴，不是「名字不一样」。
            # 蓝图常按自己的命名习惯给页 ID 加前缀（slide_overall ↔ overall），
            # 只要这个前缀在每一页上都一致，它就是约定而非漂移；一旦只有某几页
            # 对不上，那才是真的错位。判据认的是一致性，不是字面相等。
            prefixes = set()
            for blueprint_id, section_id in zip(blueprint_ids, section_ids):
                if blueprint_id == section_id:
                    prefixes.add("")
                elif blueprint_id.endswith(section_id):
                    prefixes.add(blueprint_id[: -len(section_id)])
                else:
                    prefixes.add(None)  # 连后缀都对不上，无法用约定解释
            if len(prefixes) > 1 or None in prefixes:
                mismatched = [(b, s) for b, s in zip(blueprint_ids, section_ids) if b != s]
                errors.append(
                    "blueprint page ids do not line up with spec section ids: "
                    + ", ".join(f"{b}!={s}" for b, s in mismatched[:4]))

    if args.oracle:
        oracle = load(args.oracle, "verification oracle", errors)
        if oracle:
            try:
                spec_hash = file_hash(args.spec)
            except OSError as error:
                spec_hash = None
                errors.append(f"cannot hash report spec: {error}")
            if spec_hash and oracle.get("report_spec_sha256") != spec_hash:
                errors.append("verification oracle is stale: report_spec_sha256 does not match the current spec (rebuild the oracle)")
            if oracle.get("semantics_version") != spec.get("semantics_version", "1.0"):
                errors.append("verification oracle semantics_version does not match the spec")

    if args.delivery_dir:
        keymap = Path(args.delivery_dir) / "member-keymap.json"
        if keymap.exists():
            errors.append("member-keymap.json is an internal build artifact and must never enter the delivery directory")
        # Delivered report count must equal the approved selection scope:
        # one report unless the user explicitly chose all_versions.
        reports = sorted(p.name for p in Path(args.delivery_dir).glob("report*.html"))
        if selection_mode != "all_versions" and len(reports) > 1:
            errors.append(
                f"delivery directory contains {len(reports)} formal reports {reports} "
                "but the user approved a single theme; remove the extras or obtain an "
                "explicit all_versions selection"
            )
    result = {"valid": not errors, "errors": errors, "warnings": warnings, "enabled_modes": enabled}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
