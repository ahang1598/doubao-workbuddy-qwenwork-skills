#!/usr/bin/env python3
"""Validate category Ref bindings for the bundled CSS and SVG libraries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from select_fonts import recommend


ROOT = Path(__file__).resolve().parents[2]
BINDINGS_PATH = ROOT / "assets/templates/ref-bindings.json"
CSS_CATALOG_PATH = ROOT / "assets/templates/css/catalog.json"
SVG_CATALOG_PATH = ROOT / "assets/svg/catalog.json"
SVG_REF = re.compile(r"asset:svg/([A-Za-z0-9][A-Za-z0-9._-]*\.svg)")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or list CSS/SVG candidates for a category Ref."
    )
    parser.add_argument(
        "--ref-key",
        help="After validation, print resolved CSS/SVG candidate names for this ref_key.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    bindings = load_json(BINDINGS_PATH)
    css_catalog = load_json(CSS_CATALOG_PATH)
    svg_catalog = load_json(SVG_CATALOG_PATH)

    refs = bindings.get("category_refs", {})
    ref_keys = set(refs)
    if not ref_keys:
        errors.append("category_refs is empty")
    naming = bindings.get("naming_contract", {})
    for field in ("category_ref_key", "template_id", "display_name", "resolution", "binding_meaning"):
        if not isinstance(naming.get(field), str) or not naming[field].strip():
            errors.append(f"naming_contract.{field} is required")
    if args.ref_key and args.ref_key not in ref_keys:
        errors.append(f"unknown requested ref_key: {args.ref_key}")

    for ref_key, record in refs.items():
        for field in ("spec", "visual"):
            relative = record.get(field)
            if not relative or not (ROOT / relative).is_file():
                errors.append(f"{ref_key}: missing {field}: {relative}")

    css_entries = css_catalog.get("entries", [])
    css_ids = [entry.get("id", "") for entry in css_entries]
    css_names = [entry.get("name", "") for entry in css_entries]
    for value in sorted(duplicates(css_ids)):
        errors.append(f"duplicate CSS id: {value}")
    for value in sorted(duplicates(css_names)):
        errors.append(f"duplicate CSS name: {value}")
    if css_catalog.get("ref_bindings") != "assets/templates/ref-bindings.json":
        errors.append("CSS catalog ref_bindings does not point to the shared catalog")

    for entry in css_entries:
        if entry.get('kind') == 'combination' or entry.get('id', '').startswith('combination.'):
            for language in ('zh', 'en', 'ko', 'ja'):
                for role in ('hero', 'sub', 'body', 'meta'):
                    try:
                        recommend(ROOT, combination=entry['id'], language=language, role=role, limit=1)
                    except ValueError as exc:
                        errors.append(str(exc))

    css_binding = bindings.get("css", {})
    default_refs = set(css_binding.get("default_ref_keys", []))
    unknown = default_refs - ref_keys
    if unknown:
        errors.append(f"unknown default CSS ref keys: {sorted(unknown)}")

    overrides = css_binding.get("entry_overrides", {})
    unknown_css_ids = set(overrides) - set(css_ids)
    if unknown_css_ids:
        errors.append(f"unknown CSS override ids: {sorted(unknown_css_ids)}")
    for css_id, keys in overrides.items():
        bad = set(keys) - ref_keys
        if bad:
            errors.append(f"{css_id}: unknown ref keys: {sorted(bad)}")
        if not keys:
            errors.append(f"{css_id}: empty ref binding")

    resolved_css: dict[str, set[str]] = {}
    for css_id in css_ids:
        resolved_css[css_id] = set(overrides.get(css_id, default_refs))
        if not resolved_css[css_id]:
            errors.append(f"{css_id}: resolves to no category Ref")

    svg_entries = svg_catalog.get("entries", [])
    svg_ids = [entry.get("id", "") for entry in svg_entries]
    svg_names = [entry.get("name", "") for entry in svg_entries]
    svg_paths = [entry.get("path", "") for entry in svg_entries]
    for value in sorted(duplicates(svg_ids)):
        errors.append(f"duplicate SVG id: {value}")
    for value in sorted(duplicates(svg_names)):
        errors.append(f"duplicate SVG name: {value}")
    for value in sorted(duplicates(svg_paths)):
        errors.append(f"duplicate SVG path: {value}")
    if svg_catalog.get("ref_bindings") != "assets/templates/ref-bindings.json":
        errors.append("SVG catalog ref_bindings does not point to the shared catalog")

    for entry in svg_entries:
        svg_id = entry.get("id", "<missing-id>")
        relative = entry.get("path")
        if not relative or not (ROOT / relative).is_file():
            errors.append(f"{svg_id}: missing SVG file: {relative}")
        bad_refs = set(entry.get("ref_keys", [])) - ref_keys
        if bad_refs:
            errors.append(f"{svg_id}: unknown ref keys: {sorted(bad_refs)}")
        if not entry.get("ref_keys"):
            errors.append(f"{svg_id}: no category Ref binding")
        bad_consumers = set(entry.get("css_consumer_ids", [])) - set(css_ids)
        if bad_consumers:
            errors.append(f"{svg_id}: unknown CSS consumers: {sorted(bad_consumers)}")

    disk_svg_paths = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "assets/svg").glob("*.svg")
    }
    catalog_svg_paths = set(svg_paths)
    if disk_svg_paths != catalog_svg_paths:
        errors.append(
            "SVG catalog/file mismatch: "
            f"missing={sorted(disk_svg_paths - catalog_svg_paths)}, "
            f"stale={sorted(catalog_svg_paths - disk_svg_paths)}"
        )

    referenced_svg_files: set[str] = set()
    for path in (ROOT / "assets/templates/css").rglob("*"):
        if path.suffix not in {".md", ".html"}:
            continue
        referenced_svg_files.update(SVG_REF.findall(path.read_text(encoding="utf-8")))
    catalog_svg_files = {Path(path).name for path in svg_paths}
    missing_catalog_entries = referenced_svg_files - catalog_svg_files
    if missing_catalog_entries:
        errors.append(f"CSS references uncataloged SVG files: {sorted(missing_catalog_entries)}")

    for ref_key in sorted(ref_keys):
        css_matches = [css_id for css_id, keys in resolved_css.items() if ref_key in keys]
        svg_matches = [entry["id"] for entry in svg_entries if ref_key in entry.get("ref_keys", [])]
        if not css_matches:
            errors.append(f"{ref_key}: no CSS candidates")
        if not svg_matches:
            errors.append(f"{ref_key}: no SVG candidates")

    if errors:
        for error in errors:
            print(error)
        return 1

    if args.ref_key:
        selected_css = [
            {
                "id": entry["id"],
                "name": entry["name"],
                "document": entry.get("document"),
                "anchor": entry.get("anchor"),
            }
            for entry in css_entries
            if args.ref_key in resolved_css[entry["id"]]
        ]
        selected_svg = [
            {"id": entry["id"], "name": entry["name"], "path": entry["path"]}
            for entry in svg_entries
            if args.ref_key in entry.get("ref_keys", [])
        ]
        print(
            json.dumps(
                {
                    "ref_key": args.ref_key,
                    "category": refs[args.ref_key],
                    "naming_contract": naming,
                    "css_candidates": selected_css,
                    "svg_candidates": selected_svg,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(
            "OK: "
            f"{len(ref_keys)} category Refs, "
            f"{len(css_entries)} CSS entries, "
            f"{len(svg_entries)} SVG entries"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
