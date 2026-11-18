#!/usr/bin/env python3
"""Validate structural completeness for a medical-translation delivery."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys
from typing import Any
import unicodedata
import xml.etree.ElementTree as ET


FORBIDDEN_SUP_TAG_RE = re.compile(r"(?i)</?sup\b[^>]*>")
RAW_SUP_PAIR_RE = re.compile(
    r"(?is)<\s*sup\b[^>]*>(?P<content>.*?)<\s*/\s*sup\s*>"
)
FULLWIDTH_SUP_PAIR_RE = re.compile(
    r"(?is)＜\s*sup\b[^＞]*＞(?P<content>.*?)＜\s*/\s*sup\s*＞"
)
FORMATTING_PAIR_RE = re.compile(
    r"(?is)<\s*(?P<tag>strong|i)\b(?P<attrs>[^>]*)>"
    r"(?P<content>.*?)<\s*/\s*(?P=tag)\s*>"
)
LEGACY_FORMATTING_TAG_RE = re.compile(
    r"(?i)<\s*/?\s*(?:strong|i)\b[^>]*>"
)
VOID_PAIR_RE = re.compile(
    r"(?is)<\s*(?P<tag>br|hr)\s*>\s*<\s*/\s*(?P=tag)\s*>"
)
VOID_TAG_RE = re.compile(r"(?i)<\s*(?P<tag>br|hr)\s*>")
INVALID_VOID_CLOSING_RE = re.compile(r"(?i)<\s*/\s*(?:br|hr)\s*>")
RAW_NUMERIC_LESS_THAN_RE = re.compile(
    r"<(?=\s*[+\-−]?(?:\d+(?:[.,]\d*)?|[.,]\d+))"
)
TABLE_BLOCK_RE = re.compile(r"(?is)<table(?:\s+[^>]*)?>.*?</table>")
NUMBERED_ANCHOR_ID_RE = re.compile(
    r"(?i)^\s*"
    r"(?:(?:e?fig(?:ure)?|图|table|表|supp(?:lement(?:ary)?)?"
    r"(?:\s+material)?|补充材料)\s*[\.\-_:：]?\s*)?"
    r"(?P<number>s?\d+[a-z]?)\s*$"
)
SUPERSCRIPT_MAP = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "+": "⁺",
    "-": "⁻",
    "−": "⁻",
    "=": "⁼",
    "(": "⁽",
    ")": "⁾",
    "a": "ᵃ",
    "b": "ᵇ",
    "c": "ᶜ",
    "d": "ᵈ",
    "e": "ᵉ",
    "f": "ᶠ",
    "g": "ᵍ",
    "h": "ʰ",
    "i": "ⁱ",
    "j": "ʲ",
    "k": "ᵏ",
    "l": "ˡ",
    "m": "ᵐ",
    "n": "ⁿ",
    "o": "ᵒ",
    "p": "ᵖ",
    "r": "ʳ",
    "s": "ˢ",
    "t": "ᵗ",
    "u": "ᵘ",
    "v": "ᵛ",
    "w": "ʷ",
    "x": "ˣ",
    "y": "ʸ",
    "z": "ᶻ",
    "A": "ᴬ",
    "B": "ᴮ",
    "D": "ᴰ",
    "E": "ᴱ",
    "G": "ᴳ",
    "H": "ᴴ",
    "I": "ᴵ",
    "J": "ᴶ",
    "K": "ᴷ",
    "L": "ᴸ",
    "M": "ᴹ",
    "N": "ᴺ",
    "O": "ᴼ",
    "P": "ᴾ",
    "R": "ᴿ",
    "T": "ᵀ",
    "U": "ᵁ",
    "V": "ⱽ",
    "W": "ᵂ",
    "α": "ᵅ",
    "β": "ᵝ",
    "γ": "ᵞ",
    "δ": "ᵟ",
    "θ": "ᶿ",
    "φ": "ᵠ",
    "χ": "ᵡ",
}
SAFE_SUPERSCRIPT_PUNCTUATION = set(" \t\r\n,.;:/*†‡")


def normalize_text(text: str) -> str:
    return (
        unicodedata.normalize("NFKC", text)
        .replace("−", "-")
        .replace("–", "-")
        .replace("\u00a0", " ")
    )


def strip_markup(text: str) -> str:
    text = re.sub(
        r"(?is)</?(?:p|li|tr|td|th|table|ul|ol|blockquote|callout|h[1-9])"
        r"(?:\s+[^>]*)?>",
        "\n",
        text,
    )
    return html.unescape(re.sub(r"(?is)<[^>]+>", " ", text))


def contains_forbidden_sup(text: str) -> bool:
    """Catch raw or one/two-layer escaped sup tags without unbounded decoding."""
    candidate = text
    for _ in range(3):
        normalized = normalize_text(candidate)
        if FORBIDDEN_SUP_TAG_RE.search(normalized):
            return True
        decoded = html.unescape(normalized)
        if decoded == normalized:
            break
        candidate = decoded
    return False


def escaped_sup_pair_re(depth: int) -> re.Pattern[str]:
    prefix = "&" + ("amp;" * (depth - 1))
    return re.compile(
        rf"(?is){re.escape(prefix + 'lt;')}sup"
        rf"(?:\s+.*?)?{re.escape(prefix + 'gt;')}"
        rf"(?P<content>.*?)"
        rf"{re.escape(prefix + 'lt;')}/sup{re.escape(prefix + 'gt;')}"
    )


def to_unicode_superscript(content: str) -> str | None:
    """Convert only characters with an unambiguous Unicode representation."""
    converted: list[str] = []
    for character in content:
        mapped = SUPERSCRIPT_MAP.get(character)
        if mapped is not None:
            converted.append(mapped)
            continue
        if character in SAFE_SUPERSCRIPT_PUNCTUATION:
            converted.append(character)
            continue
        if character in SUPERSCRIPT_MAP.values():
            converted.append(character)
            continue
        return None
    return "".join(converted)


def autofix_obvious_markup(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Apply only lossless, deterministic XML markup fixes."""
    fixed = text
    changes: list[dict[str, Any]] = []

    def convert_pairs(
        pattern: re.Pattern[str],
        kind: str,
    ) -> None:
        nonlocal fixed
        count = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal count
            converted = to_unicode_superscript(match.group("content"))
            if converted is None:
                return match.group(0)
            count += 1
            return converted

        fixed = pattern.sub(replace, fixed)
        if count:
            changes.append({"kind": kind, "count": count})

    for depth in (2, 1):
        convert_pairs(
            escaped_sup_pair_re(depth),
            f"escaped-sup-to-unicode-depth-{depth}",
        )
    convert_pairs(FULLWIDTH_SUP_PAIR_RE, "fullwidth-sup-to-unicode")
    convert_pairs(RAW_SUP_PAIR_RE, "sup-to-unicode")

    fixed, numeric_less_than_count = RAW_NUMERIC_LESS_THAN_RE.subn(
        "&lt;",
        fixed,
    )
    if numeric_less_than_count:
        changes.append(
            {
                "kind": "raw-numeric-less-than-to-entity",
                "count": numeric_less_than_count,
            }
        )

    formatting_counts = {"strong": 0, "i": 0}

    def replace_formatting_pair(match: re.Match[str]) -> str:
        tag = match.group("tag").lower()
        attrs = match.group("attrs")
        content = match.group("content")
        if attrs.rstrip().endswith("/"):
            return match.group(0)
        if re.search(rf"(?is)<\s*/?\s*{re.escape(tag)}\b", content):
            return match.group(0)
        formatting_counts[tag] += 1
        target_tag = "b" if tag == "strong" else "em"
        return f"<{target_tag}>{content}</{target_tag}>"

    for _ in range(4):
        next_fixed = FORMATTING_PAIR_RE.sub(replace_formatting_pair, fixed)
        if next_fixed == fixed:
            break
        fixed = next_fixed
    if formatting_counts["strong"]:
        changes.append(
            {"kind": "strong-pair-to-b", "count": formatting_counts["strong"]}
        )
    if formatting_counts["i"]:
        changes.append(
            {"kind": "i-pair-to-em", "count": formatting_counts["i"]}
        )

    fixed, void_pair_count = VOID_PAIR_RE.subn(
        lambda match: f"<{match.group('tag').lower()}/>",
        fixed,
    )
    if void_pair_count:
        changes.append(
            {"kind": "paired-void-to-self-closing", "count": void_pair_count}
        )

    fixed, void_count = VOID_TAG_RE.subn(
        lambda match: f"<{match.group('tag').lower()}/>",
        fixed,
    )
    if void_count:
        changes.append({"kind": "xml-self-close-void-tag", "count": void_count})

    return fixed, changes


def markup_well_formed_error(text: str) -> str | None:
    """Return a concise error when the Feishu XML fragment is not well formed."""
    try:
        ET.fromstring(f"<translation-root>{text}</translation-root>")
    except ET.ParseError as exc:
        return str(exc)
    return None


def normalized_marker(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        strip_markup(normalize_text(text)),
    ).strip().casefold()


def table_blocks(text: str) -> list[str]:
    return [match.group(0) for match in TABLE_BLOCK_RE.finditer(text)]


def inferred_marker_candidates(field: str, identifier: str) -> list[str]:
    """Infer common translated labels from an unambiguous numbered item ID."""
    match = NUMBERED_ANCHOR_ID_RE.fullmatch(identifier)
    if not match:
        return []
    number = match.group("number")
    if field == "figures":
        prefixes = ("图", "figure", "fig.", "fig")
    elif field == "tables":
        prefixes = ("表", "table")
    else:
        prefixes = (
            "补充材料",
            "supplement",
            "supplementary material",
        )
    candidates: list[str] = []
    for prefix in prefixes:
        candidates.extend((f"{prefix}{number}", f"{prefix} {number}"))
    return list(dict.fromkeys(candidates))


def contains_inferred_marker(text: str, candidate: str) -> bool:
    """Match a numbered label without treating Figure 10 as Figure 1."""
    marker = normalized_marker(candidate)
    return bool(
        re.search(
            rf"(?<![0-9a-z]){re.escape(marker)}(?![0-9a-z])",
            text,
        )
    )


def ledger_required_markers(
    ledger: dict[str, Any],
    errors: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return only registered table, figure, and supplement markers."""
    markers: list[dict[str, Any]] = []
    table_requirements: list[dict[str, Any]] = []

    def collect_structured_items(
        field: str,
        item_label: str,
    ) -> None:
        items = ledger.get(field, [])
        if not isinstance(items, list):
            errors.append(f"coverage ledger {field} must be a list")
            return
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(
                    f"coverage ledger {field}[{index}] must be an object"
                )
                continue
            if item.get("required", True) is False:
                continue
            identifier = str(
                item.get("id", f"{item_label}-{index + 1}")
            ).strip()
            composite = str(item.get("target_marker", "")).strip()
            number = str(item.get("target_number", "")).strip()
            caption = str(item.get("target_caption_marker", "")).strip()
            primary_markers: list[str] = []
            if composite:
                primary_markers.append(composite)
            elif caption:
                if number:
                    primary_markers.append(number)
                primary_markers.append(caption)
            else:
                inferred_candidates = inferred_marker_candidates(
                    field,
                    identifier,
                )
                if inferred_candidates:
                    markers.append(
                        {
                            "label": f"{item_label}:{identifier}:1",
                            "marker": identifier,
                            "candidates": inferred_candidates,
                            "inferred_from_id": True,
                        }
                    )
                else:
                    errors.append(
                        f"coverage ledger {identifier} needs a numbered id "
                        "such as Fig. 1/Table 1 or an explicit target_marker"
                    )
            if field == "tables":
                table_requirements.append(
                    {
                        "id": identifier,
                    }
                )
            for marker_index, marker in enumerate(primary_markers):
                markers.append(
                    {
                        "label": (
                            f"{item_label}:{identifier}:{marker_index + 1}"
                        ),
                        "marker": marker,
                        "candidates": [marker],
                        "inferred_from_id": False,
                    }
                )

    collect_structured_items("figures", "figure")
    collect_structured_items("tables", "table")
    collect_structured_items("supplements", "supplement")

    return markers, table_requirements


def validate_coverage(
    translation_section: str,
    ledger: dict[str, Any] | None,
    errors: list[str],
) -> dict[str, Any]:
    if ledger is None:
        return {
            "provided": False,
            "required_markers": 0,
            "missing_markers": [],
            "inferred_markers": [],
            "required_table_blocks": 0,
            "actual_table_blocks": len(table_blocks(translation_section)),
        }

    markers, table_requirements = ledger_required_markers(ledger, errors)
    normalized_translation = normalized_marker(translation_section)
    missing_markers: list[dict[str, str]] = []
    inferred_markers: list[dict[str, Any]] = []
    for requirement in markers:
        candidates = requirement["candidates"]
        if requirement["inferred_from_id"]:
            present = any(
                contains_inferred_marker(
                    normalized_translation,
                    candidate,
                )
                for candidate in candidates
            )
        else:
            present = any(
                normalized_marker(candidate) in normalized_translation
                for candidate in candidates
            )
        if requirement["inferred_from_id"]:
            inferred_markers.append(
                {
                    "label": requirement["label"],
                    "id": requirement["marker"],
                    "candidates": candidates,
                }
            )
        if not present:
            missing_markers.append(
                {
                    "label": requirement["label"],
                    "marker": (
                        " / ".join(candidates)
                        if requirement["inferred_from_id"]
                        else requirement["marker"]
                    ),
                }
            )
    actual_table_count = len(table_blocks(translation_section))
    if actual_table_count < len(table_requirements):
        for requirement in table_requirements[actual_table_count:]:
            missing_markers.append(
                {
                    "label": f"table:{requirement['id']}:block",
                    "marker": (
                        "a distinct actual <table> block; the title/caption "
                        "marker may be outside the table"
                    ),
                }
            )
    if missing_markers:
        errors.append(
            "coverage ledger markers missing from translation: "
            f"{missing_markers}"
        )

    return {
        "provided": True,
        "required_markers": len(markers),
        "missing_markers": missing_markers,
        "inferred_markers": inferred_markers,
        "required_table_blocks": len(table_requirements),
        "actual_table_blocks": actual_table_count,
    }


def validate(
    source: str,
    translation: str,
    *,
    coverage_ledger: dict[str, Any] | None = None,
    require_full: bool = False,
) -> dict[str, object]:
    """Run only minimal deterministic XML and table/figure checks."""
    del source, require_full
    target_section = normalize_text(translation).strip()
    errors: list[str] = []
    if contains_forbidden_sup(translation):
        errors.append(
            "forbidden <sup> markup found; use ordinary Unicode "
            "superscript/subscript characters for fixed medical values "
            "or <latex> for formulas"
        )
    if LEGACY_FORMATTING_TAG_RE.search(translation):
        errors.append(
            "unresolved legacy formatting markup found; use paired <b>/<em> "
            "or rerun the explicit safe autofix"
        )
    if INVALID_VOID_CLOSING_RE.search(translation):
        errors.append(
            "invalid closing </br> or </hr> markup found; use <br/> or <hr/>"
        )
    markup_error = markup_well_formed_error(translation)
    if markup_error:
        errors.append(f"translation XML is not well formed: {markup_error}")
    if not strip_markup(target_section).strip():
        errors.append("translation text is empty")

    coverage_report = validate_coverage(
        target_section,
        coverage_ledger,
        errors,
    )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": [],
        "translation_section": {
            "mode": "whole_target",
            "heading_required": False,
        },
        "coverage": coverage_report,
        "checks": {
            "whole_target_nonempty": True,
            "markup_well_formed": markup_error is None,
            "table_figure_inventory": coverage_ledger is not None,
            "forbidden_sup": True,
        },
        "note": (
            "本校验器只检查译文非空、XML 良构、登记表格的真实 "
            "<table> 块、表图/补充材料文字锚点和禁用的 <sup>。"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        metavar="FILE",
        help=(
            "translation XML; legacy 'source translation' invocation is also "
            "accepted, but the source file is not read"
        ),
    )
    parser.add_argument(
        "--coverage-ledger",
        type=Path,
        help="JSON coverage ledger built before translation",
    )
    parser.add_argument(
        "--require-full",
        action="store_true",
        help=(
            "deprecated compatibility flag; accepted but ignored because "
            "scope and gaps are not machine-validated"
        ),
    )
    parser.add_argument(
        "--autofix",
        action="store_true",
        help=(
            "rewrite the translation file with deterministic markup fixes "
            "before validation"
        ),
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    try:
        if len(args.inputs) == 1:
            translation_path = args.inputs[0]
        elif len(args.inputs) == 2:
            translation_path = args.inputs[1]
        else:
            raise ValueError(
                "expected translation.xml or legacy source.txt translation.xml"
            )
        translation = translation_path.read_text(encoding="utf-8")
        autofix_changes: list[dict[str, Any]] = []
        if args.autofix:
            fixed_translation, autofix_changes = autofix_obvious_markup(
                translation
            )
            if fixed_translation != translation:
                translation_path.write_text(
                    fixed_translation,
                    encoding="utf-8",
                )
                translation = fixed_translation
        coverage_ledger_bytes = (
            args.coverage_ledger.read_bytes()
            if args.coverage_ledger
            else None
        )
        coverage_ledger = (
            json.loads(coverage_ledger_bytes.decode("utf-8"))
            if coverage_ledger_bytes is not None
            else None
        )
        if coverage_ledger is not None and not isinstance(
            coverage_ledger,
            dict,
        ):
            raise ValueError("coverage ledger root must be a JSON object")
        report = validate(
            "",
            translation,
            coverage_ledger=coverage_ledger,
            require_full=args.require_full,
        )
        report["translation_sha256"] = hashlib.sha256(
            translation.encode("utf-8")
        ).hexdigest()
        report["autofix"] = {
            "requested": args.autofix,
            "changed": bool(autofix_changes),
            "changes": autofix_changes,
            "unresolved_sup": contains_forbidden_sup(translation),
            "unresolved_legacy_markup": bool(
                LEGACY_FORMATTING_TAG_RE.search(translation)
                or INVALID_VOID_CLOSING_RE.search(translation)
            ),
            "markup_well_formed": (
                markup_well_formed_error(translation) is None
            ),
        }
        if coverage_ledger_bytes is not None:
            report["coverage"]["ledger_sha256"] = hashlib.sha256(
                coverage_ledger_bytes
            ).hexdigest()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {
            "valid": False,
            "errors": [f"cannot read input: {exc}"],
            "warnings": [],
        }

    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    return 0 if report.get("valid") else 1


if __name__ == "__main__":
    sys.exit(main())
