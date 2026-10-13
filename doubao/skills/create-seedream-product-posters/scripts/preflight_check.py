#!/usr/bin/env python3
"""Validate a product-poster concept before image generation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


DENSITY_RANGES = {"D1": (6, 8), "D2": (8, 11), "D3": (11, 15)}
BLUEPRINTS = {
    "centered-monument",
    "asymmetric-monument",
    "product-result-triangle",
    "diagonal-editorial",
    "refreshment-tower",
    "campaign-stack",
    "social-narrative",
}
MECHANISMS = {
    "launch-authority",
    "functional-proof",
    "routine-convenience",
    "sensory-desire",
    "cultural-value",
    "urgent-conversion",
    "social-identity",
    "surprise-collectability",
}
LAYERS = {"foreground", "product", "interaction", "environment", "information"}
REQUIRED_COPY_KEYS = {"headline"}
BANNED_COPY = {"即刻探索", "Explore Now"}
CLAIM_SOURCES = {"visible", "user-supplied", "omitted"}
HEADLINE_AXES = {"top-centered", "upper-left", "upper-right", "diagonal", "split", "collage"}
PRODUCT_AXES = {"centered", "left", "right", "diagonal", "narrative"}
BOTTOM_SYSTEMS = {
    "three-equal-cards",
    "slogan-close",
    "trust-rail",
    "cta-dock",
    "open-scene",
    "editorial-caption",
}

TEMPLATE = {
    "reference_image": "/absolute/path/product.png",
    "output_language": "zh-CN",
    "product_category": "portable electronics",
    "input_quality": "B",
    "product_signals": {
        "form": "rigid",
        "material": "glossy",
        "use": "held",
        "desire": "convenience",
    },
    "product_truth_lock": [
        "exactly one product",
        "preserve silhouette",
        "preserve base color",
        "preserve visible label",
    ],
    "negative_geometry_lock": ["no extra openings or controls"],
    "primary_mechanism": "functional-proof",
    "secondary_mechanism": None,
    "density": "D2",
    "module_count": 9,
    "blueprint": "asymmetric-monument",
    "bands": {
        "A": [0, 8],
        "B": [8, 28],
        "C": [26, 38],
        "D": [34, 79],
        "E": [79, 92],
        "F": [92, 100],
    },
    "anchors": ["headline", "product", "cta"],
    "richness_layers": ["foreground", "product", "environment", "information"],
    "product_scale": {"width_percent": 55, "height_percent": 50},
    "requires_cta": True,
    "copy_manifest": {
        "eyebrow": "新品",
        "headline": "主标题",
        "support": "一句支持文案",
        "benefits": ["卖点一", "卖点二", "卖点三"],
        "badge": "推荐",
        "cta": "立即了解",
        "footer": "服务或口号",
    },
    "claim_provenance": {
        "support": "user-supplied",
        "benefits": ["visible", "visible", "user-supplied"],
    },
    "anti_template": {
        "category_specific_devices": [
            "device derived from product form or material",
            "device derived from use or interaction",
        ],
        "interaction_or_material_proof": "one visible proof tied to the product",
        "foreground_depth_device": "one purposeful foreground frame",
        "bottom_closure_device": "one deliberate non-generic close",
        "avoided_template_signature": "top headline + centered product + three equal bottom cards",
    },
    "layout_signature": {
        "headline_axis": "upper-left",
        "product_axis": "right",
        "bottom_system": "slogan-close",
    },
    "verified_offer": False,
    "contains_price_or_numeric_claim": False,
    "unsupported_facts_excluded": True,
    "bottom_closure": True,
    "aspect_ratio": "9:16",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def english_word_count(value: object) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", str(value)))


def validate(data: dict, require_existing_image: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    image = data.get("reference_image")
    if not isinstance(image, str) or not image.startswith("/"):
        fail(errors, "reference_image must be an absolute path")
    elif require_existing_image and not Path(image).is_file():
        fail(errors, f"reference_image does not exist: {image}")

    language = data.get("output_language", "zh-CN")
    if language not in {"zh-CN", "en"}:
        fail(errors, "output_language must be zh-CN or en")

    if not str(data.get("product_category", "")).strip():
        fail(errors, "product_category is required")

    quality = data.get("input_quality")
    if quality not in {"A", "B", "C", "D"}:
        fail(errors, "input_quality must be A, B, C, or D")
    if quality == "D":
        fail(errors, "input quality D is not generation-ready; request a better photo")

    signals = data.get("product_signals")
    if not isinstance(signals, dict):
        fail(errors, "product_signals must be an object")
    else:
        for key in ("form", "material", "use", "desire"):
            if not str(signals.get(key, "")).strip():
                fail(errors, f"product_signals.{key} is required")

    truth = data.get("product_truth_lock")
    if not isinstance(truth, list) or not 4 <= len(truth) <= 8:
        fail(errors, "product_truth_lock must contain 4–8 visible facts")
    elif any(not str(item).strip() for item in truth):
        fail(errors, "product_truth_lock contains a blank item")

    negative = data.get("negative_geometry_lock")
    if not isinstance(negative, list) or not negative:
        fail(errors, "negative_geometry_lock must contain at least one invariant")

    primary = data.get("primary_mechanism")
    if primary not in MECHANISMS:
        fail(errors, f"primary_mechanism must be one of {sorted(MECHANISMS)}")
    secondary = data.get("secondary_mechanism")
    if secondary is not None and secondary not in MECHANISMS:
        fail(errors, "secondary_mechanism must be null or a valid mechanism")
    if secondary == primary:
        fail(errors, "secondary_mechanism must differ from primary_mechanism")

    density = data.get("density")
    if density not in DENSITY_RANGES:
        fail(errors, "density must be D1, D2, or D3")
    modules = data.get("module_count")
    if not isinstance(modules, int):
        fail(errors, "module_count must be an integer")
    elif density in DENSITY_RANGES:
        low, high = DENSITY_RANGES[density]
        if not low <= modules <= high:
            fail(errors, f"{density} requires {low}–{high} modules, got {modules}")

    blueprint = data.get("blueprint")
    if blueprint not in BLUEPRINTS:
        fail(errors, f"blueprint must be one of {sorted(BLUEPRINTS)}")

    bands = data.get("bands")
    if not isinstance(bands, dict) or set(bands) != set("ABCDEF"):
        fail(errors, "bands must define exactly A, B, C, D, E, and F")
    else:
        previous_start = -1
        for name in "ABCDEF":
            span = bands[name]
            if (
                not isinstance(span, list)
                or len(span) != 2
                or not all(isinstance(value, (int, float)) for value in span)
            ):
                fail(errors, f"band {name} must be [start, end]")
                continue
            start, end = span
            if not 0 <= start < end <= 100:
                fail(errors, f"band {name} must stay within 0–100 and start before end")
            if start < previous_start:
                fail(errors, f"band {name} starts before the preceding band")
            previous_start = start
        if isinstance(bands.get("F"), list) and bands["F"][1] < 98:
            fail(errors, "band F must close near the bottom edge (end >= 98)")

    anchors = data.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != 3 or len(set(anchors)) != 3:
        fail(errors, "anchors must contain exactly three distinct attention anchors")
    elif "product" not in anchors:
        fail(errors, "anchors must include product")

    layers = data.get("richness_layers")
    if not isinstance(layers, list) or len(set(layers)) < 3:
        fail(errors, "richness_layers must contain at least three distinct layers")
    elif not set(layers).issubset(LAYERS):
        fail(errors, f"richness_layers may only use {sorted(LAYERS)}")
    elif "product" not in layers or "information" not in layers:
        fail(errors, "richness_layers must include product and information")

    scale = data.get("product_scale")
    if not isinstance(scale, dict):
        fail(errors, "product_scale must be an object")
    else:
        width = scale.get("width_percent", 0)
        height = scale.get("height_percent", 0)
        if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
            fail(errors, "product_scale values must be numeric")
        elif width < 45 and height < 32:
            fail(errors, "hero product must occupy >=45% width or >=32% height")
        if width > 90 or height > 80:
            warnings.append("product scale may leave too little room for copy and closure")

    copy = data.get("copy_manifest")
    requires_cta = data.get("requires_cta")
    if not isinstance(requires_cta, bool):
        fail(errors, "requires_cta must be true or false")
    if not isinstance(copy, dict):
        fail(errors, "copy_manifest must be an object")
    else:
        missing = [key for key in REQUIRED_COPY_KEYS if not str(copy.get(key, "")).strip()]
        if missing:
            fail(errors, f"copy_manifest is missing required text: {', '.join(missing)}")
        benefits = copy.get("benefits")
        if benefits is not None and (
            not isinstance(benefits, list) or len(benefits) not in {0, 3}
        ):
            fail(errors, "copy_manifest.benefits must be absent, empty, or contain exactly three items")
        cta = str(copy.get("cta", "")).strip()
        footer = str(copy.get("footer", "")).strip()
        closing_slogan = str(copy.get("closing_slogan", "")).strip()
        if requires_cta is True and not cta:
            fail(errors, "requires_cta=true requires non-empty copy_manifest.cta")
        if requires_cta is False and cta:
            fail(errors, "requires_cta=false requires copy_manifest.cta to be empty")
        if requires_cta is False and not (footer or closing_slogan):
            fail(errors, "publicity poster without CTA requires a footer or closing_slogan")
        if language == "en":
            english_limits = {
                "eyebrow": 6,
                "headline": 8,
                "support": 16,
                "badge": 4,
                "cta": 4,
                "closing_slogan": 10,
                "footer": 12,
            }
            for key, limit in english_limits.items():
                value = copy.get(key, "")
                if str(value).strip() and english_word_count(value) > limit:
                    fail(errors, f"English copy_manifest.{key} must be <= {limit} words")
            if isinstance(benefits, list):
                for index, benefit in enumerate(benefits):
                    if english_word_count(benefit) > 6:
                        fail(errors, f"English benefit {index + 1} must be <= 6 words")
        for key, value in copy.items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                if str(item).strip().casefold() in {text.casefold() for text in BANNED_COPY}:
                    fail(errors, f"copy_manifest.{key} uses banned generic copy: {item}")

    provenance = data.get("claim_provenance")
    if not isinstance(provenance, dict):
        fail(errors, "claim_provenance must be an object")
    elif isinstance(copy, dict):
        support = str(copy.get("support", "")).strip()
        support_source = provenance.get("support")
        if support_source not in CLAIM_SOURCES:
            fail(errors, f"claim_provenance.support must be one of {sorted(CLAIM_SOURCES)}")
        elif support and support_source == "omitted":
            fail(errors, "non-empty support copy requires visible or user-supplied provenance")
        elif not support and support_source != "omitted":
            fail(errors, "empty support copy requires claim_provenance.support=omitted")

        benefits = copy.get("benefits")
        benefit_sources = provenance.get("benefits")
        if not isinstance(benefit_sources, list):
            fail(errors, "claim_provenance.benefits must be a list")
        elif isinstance(benefits, list):
            if len(benefit_sources) != len(benefits):
                fail(errors, "claim_provenance.benefits must match copy_manifest.benefits length")
            else:
                for index, (benefit, source) in enumerate(zip(benefits, benefit_sources)):
                    if source not in CLAIM_SOURCES:
                        fail(
                            errors,
                            f"claim_provenance.benefits[{index}] must be one of {sorted(CLAIM_SOURCES)}",
                        )
                    elif str(benefit).strip() and source == "omitted":
                        fail(
                            errors,
                            f"non-empty benefit {index + 1} requires visible or user-supplied provenance",
                        )

    anti_template = data.get("anti_template")
    if not isinstance(anti_template, dict):
        fail(errors, "anti_template must be an object")
    else:
        devices = anti_template.get("category_specific_devices")
        if (
            not isinstance(devices, list)
            or len(devices) < 2
            or any(not str(item).strip() for item in devices)
        ):
            fail(errors, "anti_template.category_specific_devices needs at least two non-blank devices")
        for key in (
            "interaction_or_material_proof",
            "foreground_depth_device",
            "bottom_closure_device",
            "avoided_template_signature",
        ):
            if not str(anti_template.get(key, "")).strip():
                fail(errors, f"anti_template.{key} is required")

    layout_signature = data.get("layout_signature")
    if not isinstance(layout_signature, dict):
        fail(errors, "layout_signature must be an object")
    else:
        headline_axis = layout_signature.get("headline_axis")
        product_axis = layout_signature.get("product_axis")
        bottom_system = layout_signature.get("bottom_system")
        if headline_axis not in HEADLINE_AXES:
            fail(errors, f"layout_signature.headline_axis must be one of {sorted(HEADLINE_AXES)}")
        if product_axis not in PRODUCT_AXES:
            fail(errors, f"layout_signature.product_axis must be one of {sorted(PRODUCT_AXES)}")
        if bottom_system not in BOTTOM_SYSTEMS:
            fail(errors, f"layout_signature.bottom_system must be one of {sorted(BOTTOM_SYSTEMS)}")
        if (
            headline_axis == "top-centered"
            and product_axis == "centered"
            and bottom_system == "three-equal-cards"
        ):
            fail(
                errors,
                "generic triptych is banned: top-centered headline + centered product + three equal bottom cards",
            )

    numeric = data.get("contains_price_or_numeric_claim")
    verified = data.get("verified_offer")
    if numeric is True and verified is not True:
        fail(errors, "price or numeric claim requires verified_offer=true")
    if primary == "urgent-conversion":
        if verified is not True:
            fail(errors, "urgent-conversion requires a verified offer")
        if requires_cta is not True:
            fail(errors, "urgent-conversion requires requires_cta=true")

    if data.get("unsupported_facts_excluded") is not True:
        fail(errors, "unsupported_facts_excluded must be true")
    if data.get("bottom_closure") is not True:
        fail(errors, "bottom_closure must be true")
    if data.get("aspect_ratio") != "9:16":
        warnings.append("default mobile poster aspect ratio is 9:16")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("concept", nargs="?", help="path to concept JSON")
    parser.add_argument(
        "--write-template",
        metavar="PATH",
        help="write a valid starter concept JSON and exit",
    )
    parser.add_argument(
        "--skip-image-exists",
        action="store_true",
        help="validate structure without checking reference_image on disk",
    )
    args = parser.parse_args()

    if args.write_template:
        path = Path(args.write_template)
        path.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n")
        print(path)
        return 0

    if not args.concept:
        parser.error("concept is required unless --write-template is used")

    try:
        data = json.loads(Path(args.concept).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("ERROR: concept JSON root must be an object", file=sys.stderr)
        return 2

    errors, warnings = validate(data, not args.skip_image_exists)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAIL: {len(errors)} error(s)", file=sys.stderr)
        return 1

    print("PASS: poster concept is generation-ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
