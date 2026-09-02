#!/usr/bin/env python3
"""Build a live capability inventory from linkfoxagent-v2.

This script treats linkfoxagent-v2/*/SKILL.md as the source of truth. The
generated catalog/platform/vendor views are navigation aids only; runtime
dependencies must still be the minimal set of skills a workflow actually calls.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
CREATOR_ROOT = SCRIPT_DIR.parent
DEFAULT_V2_ROOT = CREATOR_ROOT.parent
DEFAULT_RECIPES = CREATOR_ROOT / "references" / "tier1-recipes.yaml"

PLATFORM_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("amazon", ("amazon", "aba", "keepa", "sif", "sellersprite", "junglescout", "jiimore", "sorftime")),
    ("walmart", ("walmart", "wallysmarter")),
    ("ebay", ("ebay",)),
    ("ozon", ("ozon", "mpstats")),
    ("tiktok", ("tiktok", "fastmoss", "echotik")),
    ("shopee", ("shopee", "youying")),
    ("1688", ("1688",)),
    ("google", ("google",)),
    ("product-center", ("product-center",)),
    ("lark", ("lark",)),
    ("aigc", ("aigc",)),
    ("ip-compliance", ("zhihuiya", "ruiguan", "patent", "trademark", "copyright")),
]

CAPABILITY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("product_detail", ("product-detail", "detail", "bibliography", "description-data", "claim-data", "abstract-data")),
    ("product_search", ("product-search", "search", "discovery", "billboard", "rank", "query")),
    ("search_by_image", ("search-by-image", "image-search", "patent-image-search")),
    ("keyword_research", ("keyword", "traffic-keyword", "aba", "sif")),
    ("reviews", ("review", "reviews")),
    ("market_research", ("market", "opportunity", "statistics", "niche")),
    ("trend", ("trend", "series")),
    ("listing", ("listing",)),
    ("image_generation", ("imagegen", "image-competitor")),
    ("video_generation", ("videogen",)),
    ("product_center", ("product-center", "variant")),
    ("report", ("report-generator", "html")),
    ("file_upload", ("file-upload",)),
    ("skill_creation", ("skill-creator",)),
    ("ip_compliance", ("patent", "trademark", "copyright", "legal-status", "ruiguan", "zhihuiya")),
    ("orchestration", ("orchestration", "superagent", "scheduler")),
]

VENDOR_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("amazon_frontend", ("linkfox-amazon-",)),
    ("amazon_aba", ("linkfox-aba-",)),
    ("keepa", ("linkfox-keepa-",)),
    ("sif", ("linkfox-sif-",)),
    ("sellersprite", ("linkfox-sellersprite-",)),
    ("jiimore", ("linkfox-jiimore-",)),
    ("sorftime", ("linkfox-sorftime-",)),
    ("walmart", ("linkfox-walmart-",)),
    ("wallysmarter", ("linkfox-wallysmarter-",)),
    ("mpstats", ("linkfox-mpstats-",)),
    ("fastmoss", ("linkfox-fastmoss-",)),
    ("echotik", ("linkfox-echotik-",)),
    ("youying", ("linkfox-youying-",)),
    ("dld", ("linkfox-dld-",)),
    ("google_trend", ("linkfox-google-trend-",)),
    ("zhihuiya", ("linkfox-zhihuiya-",)),
    ("ruiguan", ("linkfox-ruiguan-",)),
    ("product_center", ("linkfox-product-center-",)),
    ("aigc", ("linkfox-aigc-",)),
    ("linkfox_internal", ("linkfox-report-generator", "linkfox-file-upload", "linkfox-skill-creator", "linkfox-ecommerce-skill-creator")),
]


def _frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    data: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    for raw in match.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if current_key and current_list is not None and raw.startswith((" ", "\t")):
            item = raw.strip()
            if item.startswith("- "):
                current_list.append(item[2:].strip().strip("'\""))
            continue
        current_key = None
        current_list = None
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "[]":
            data[key] = []
        elif value == "":
            data[key] = []
            current_key = key
            current_list = data[key]
        else:
            if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
                value = value[1:-1]
            data[key] = value
    return data


def _load_meta(skill_dir: Path) -> dict[str, Any]:
    meta_path = skill_dir / "_meta.json"
    if not meta_path.exists():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _contains_any(haystack: str, needles: Iterable[str]) -> bool:
    return any(needle in haystack for needle in needles)


def _infer_many(slug: str, description: str, rules: list[tuple[str, tuple[str, ...]]]) -> list[str]:
    haystack = f"{slug}\n{description}".lower()
    found = [label for label, needles in rules if _contains_any(haystack, needles)]
    return found or ["other"]


def _infer_vendor(slug: str, description: str) -> str:
    haystack = f"{slug}\n{description}".lower()
    for label, prefixes in VENDOR_RULES:
        if any(haystack.startswith(prefix) or prefix in haystack for prefix in prefixes):
            return label
    if slug.startswith("linkfox-"):
        parts = slug.split("-")
        if len(parts) >= 3:
            return parts[1]
    return "other"


def _infer_tier(slug: str, description: str) -> str:
    haystack = f"{slug}\n{description}".lower()
    if "skill-creator" in slug:
        return "creator"
    if slug in {"linkfox-report-generator", "linkfox-file-upload", "lark-base"}:
        return "infrastructure"
    if _contains_any(haystack, ("workflow", "流程", "编排", "orchestration", "superagent", "listing-master")):
        return "tier2_or_tier3"
    return "tier1_or_utility"


def build_inventory(v2_root: Path, query: str | None = None) -> list[dict[str, Any]]:
    query_l = (query or "").lower().strip()
    rows: list[dict[str, Any]] = []
    for child in sorted(v2_root.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = _frontmatter(text)
        meta = _load_meta(child)
        name = str(fm.get("name") or child.name).strip()
        description = str(fm.get("description") or "").strip()
        haystack = f"{child.name}\n{name}\n{description}".lower()
        if query_l and query_l not in haystack:
            continue
        rows.append(
            {
                "slug": child.name,
                "name": name,
                "description": description,
                "platforms": _infer_many(child.name, description, PLATFORM_RULES),
                "capabilities": _infer_many(child.name, description, CAPABILITY_RULES),
                "vendor": _infer_vendor(child.name, description),
                "tier_hint": _infer_tier(child.name, description),
                "version": meta.get("version"),
                "path": str(child),
            }
        )
    return rows


def _escape_cell(value: Any) -> str:
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    if value is None:
        value = ""
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_inventory(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| slug | platforms | capabilities | vendor | tier | description |",
        "|------|-----------|--------------|--------|------|-------------|",
    ]
    for row in rows:
        lines.append(
            "| `{slug}` | {platforms} | {capabilities} | {vendor} | {tier} | {description} |".format(
                slug=row["slug"],
                platforms=_escape_cell(row["platforms"]),
                capabilities=_escape_cell(row["capabilities"]),
                vendor=_escape_cell(row["vendor"]),
                tier=_escape_cell(row["tier_hint"]),
                description=_escape_cell(row["description"]),
            )
        )
    return "\n".join(lines)


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = row.get(key)
        values = value if isinstance(value, list) else [value]
        for item in values:
            grouped[str(item or "other")].append(row)
    return dict(sorted(grouped.items()))


def render_grouped(rows: list[dict[str, Any]], key: str, title: str) -> str:
    lines = [
        f"# {title}",
        "",
        "> Generated from live `linkfoxagent-v2/*/SKILL.md`. This file is a navigation view, not the source of truth.",
        "",
    ]
    for group_name, group_rows in _group(rows, key).items():
        lines.extend([f"## {group_name} ({len(group_rows)})", ""])
        lines.extend(
            [
                "| slug | platforms | capabilities | vendor | description |",
                "|------|-----------|--------------|--------|-------------|",
            ]
        )
        for row in group_rows:
            lines.append(
                "| `{slug}` | {platforms} | {capabilities} | {vendor} | {description} |".format(
                    slug=row["slug"],
                    platforms=_escape_cell(row["platforms"]),
                    capabilities=_escape_cell(row["capabilities"]),
                    vendor=_escape_cell(row["vendor"]),
                    description=_escape_cell(row["description"]),
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _extract_recipe_slugs(recipe_path: Path) -> set[str]:
    if not recipe_path.exists():
        return set()
    text = recipe_path.read_text(encoding="utf-8", errors="replace")
    slug_re = re.compile(r"\b(?:linkfox-[a-z0-9-]+|agent-listing-result-html-skill|lark-base)\b")
    return set(slug_re.findall(text))


def validate_recipes(rows: list[dict[str, Any]], recipe_path: Path) -> dict[str, Any]:
    known = {row["slug"] for row in rows}
    referenced = _extract_recipe_slugs(recipe_path)
    missing = sorted(referenced - known)
    return {
        "recipe_path": str(recipe_path),
        "referenced_count": len(referenced),
        "missing_count": len(missing),
        "missing": missing,
    }


def render_recipe_validation(report: dict[str, Any]) -> str:
    lines = [
        f"# Recipe Slug Validation",
        "",
        f"- recipe_path: `{report['recipe_path']}`",
        f"- referenced_count: {report['referenced_count']}",
        f"- missing_count: {report['missing_count']}",
    ]
    if report["missing"]:
        lines.extend(["", "## Missing", ""])
        lines.extend(f"- `{slug}`" for slug in report["missing"])
    return "\n".join(lines)


def write_indexes(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "v2-inventory.generated.md": render_inventory(rows) + "\n",
        "tier1-catalog.generated.md": render_grouped(rows, "capabilities", "Capability Index"),
        "tier1-by-platform.generated.md": render_grouped(rows, "platforms", "Platform Index"),
        "tier1-by-vendor.generated.md": render_grouped(rows, "vendor", "Vendor Index"),
    }
    written: list[Path] = []
    for filename, content in outputs.items():
        path = out_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_V2_ROOT), help="linkfoxagent-v2 root")
    parser.add_argument("--query", help="case-insensitive substring filter")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--view",
        choices=("inventory", "catalog", "platform", "vendor", "recipes-validation"),
        default="inventory",
        help="markdown/json view to print",
    )
    parser.add_argument("--write-indexes", help="directory to write generated markdown indexes")
    parser.add_argument("--validate-recipes", default=str(DEFAULT_RECIPES), help="recipe file to validate")
    parser.add_argument("--strict-recipes", action="store_true", help="exit 1 when recipe validation has missing slugs")
    args = parser.parse_args()

    rows = build_inventory(Path(args.root).resolve(), args.query)

    if args.write_indexes:
        written = write_indexes(rows, Path(args.write_indexes).resolve())
        for path in written:
            print(path)
        return 0

    if args.view == "recipes-validation":
        report = validate_recipes(rows, Path(args.validate_recipes).resolve())
        if args.format == "json":
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(render_recipe_validation(report))
        return 1 if args.strict_recipes and report["missing"] else 0

    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if args.view == "catalog":
        print(render_grouped(rows, "capabilities", "Capability Index"), end="")
    elif args.view == "platform":
        print(render_grouped(rows, "platforms", "Platform Index"), end="")
    elif args.view == "vendor":
        print(render_grouped(rows, "vendor", "Vendor Index"), end="")
    else:
        print(render_inventory(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
