#!/usr/bin/env python3
"""
inspect_form.py — PDF Form Inspector

Examines a PDF to determine whether it has fillable AcroForm fields or
requires annotation-based filling. Outputs a JSON descriptor that can be
edited with values and then passed to fill_form.py.

Usage:
    python scripts/inspect_form.py form.pdf
    python scripts/inspect_form.py form.pdf --output fields.json
    python scripts/inspect_form.py form.pdf --output fields.json --check-overlaps
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import extract_document_tool_metadata, resolve_qwenwork_cli, run_document_tool
from _execution_route import BackendFailure
from _semantic_route import execute_semantic_script


def _normalize_field_type(raw_type: str) -> str:
    mapping = {
        "/Tx": "text",
        "/Btn": "checkbox",
        "/Ch": "choice",
        "/Sig": "signature",
    }
    return mapping.get(raw_type, raw_type.lstrip("/").lower())


def inspect_acroform(pdf_path: Path) -> dict:
    """Inspect AcroForm fields using pypdf."""
    try:
        import pypdf
    except ImportError:
        return {"error": "pypdf not installed. Run: pip install pypdf"}

    reader = pypdf.PdfReader(str(pdf_path))
    fields = reader.get_fields() or {}

    form_fields: list[dict] = []
    for name, field in fields.items():
        raw_type = field.get("/FT", "")
        ftype = _normalize_field_type(str(raw_type))

        entry: dict = {
            "name": name,
            "type": ftype,
            "current_value": str(field.get("/V", "") or "").lstrip("/"),
            "fill_value": "",  # <-- user fills this in
        }

        # checkbox / radio: expose allowed values
        if ftype == "checkbox":
            on_val = str(field.get("/AS", "/Yes")).lstrip("/")
            entry["checked_value"] = on_val if on_val != "Off" else "Yes"
            entry["unchecked_value"] = "Off"

        # choice: expose options
        if ftype == "choice":
            opts = field.get("/Opt", [])
            entry["options"] = [str(o).lstrip("/") for o in opts]

        form_fields.append(entry)

    return {
        "form_type": "acroform",
        "field_count": len(form_fields),
        "fields": form_fields,
    }


def _find_containing_cell(
    x0: float, top: float, x1: float, bottom: float,
    cells: list[dict],
) -> dict | None:
    """Return the smallest rect that fully contains the given bounding box."""
    best = None
    best_area = float("inf")
    for cell in cells:
        if (cell["x0"] <= x0 and cell["top"] <= top
                and cell["x1"] >= x1 and cell["bottom"] >= bottom):
            area = (cell["x1"] - cell["x0"]) * (cell["bottom"] - cell["top"])
            if area < best_area:
                best = cell
                best_area = area
    return best


def inspect_layout_based(pdf_path: Path) -> dict:
    """
    For non-fillable PDFs: extract text positions to identify label/field zones.
    Returns a structure suitable for annotation-based filling.

    Fill position is determined per-label by detecting the containing cell and
    choosing the direction (right vs below) that has more available space.
    """
    try:
        import pdfplumber
    except ImportError:
        return {"error": "pdfplumber not installed. Run: pip install pdfplumber"}

    annotations: list[dict] = []
    font_sizes: list[float] = []

    with pdfplumber.open(str(pdf_path)) as doc:
        for page_idx, page in enumerate(doc.pages):
            # Collect font sizes from actual characters for auto font-size detection
            for char in (page.chars or []):
                size = float(char.get("size", 0))
                if size > 0:
                    font_sizes.append(size)

            # Extract real cells (filter out hairline rules)
            cells = [
                r for r in (page.rects or [])
                if (r["x1"] - r["x0"]) > 5 and (r["bottom"] - r["top"]) > 5
            ]

            # Build a char-level lookup: (page_idx, word_text_approx) -> font size.
            # We group chars by their top-coordinate band to associate each word
            # with the font size of its constituent characters.
            char_size_by_region: list[tuple[float, float, float, float, float]] = []
            for char in (page.chars or []):
                size = float(char.get("size", 0))
                if size > 0:
                    char_size_by_region.append((
                        float(char.get("x0", 0)),
                        float(char.get("top", 0)),
                        float(char.get("x1", 0)),
                        float(char.get("bottom", 0)),
                        size,
                    ))

            def _font_size_at(wx0: float, wtop: float, wx1: float, wbot: float) -> float | None:
                """Return the modal font size of chars overlapping the given bbox."""
                sizes = [
                    s for cx0, ct, cx1, cb, s in char_size_by_region
                    if cx0 < wx1 and cx1 > wx0 and ct < wbot and cb > wtop
                ]
                if not sizes:
                    return None
                # Use mode (most frequent size) to handle mixed-size edge cases
                return max(set(sizes), key=sizes.count)

            words = page.extract_words(x_tolerance=5, y_tolerance=5) or []
            for word in words:
                text   = word["text"]

                # [placeholder] tokens use ASCII identifier syntax: [field_name].
                # Detect them early so long identifiers (≥ 30 chars) are not silently
                # dropped by the noise filter below.
                _is_ph = bool(re.match(r'^\[[A-Za-z_][A-Za-z0-9_]*\]$', text))

                # Skip very long words that are unlikely to be form labels or placeholders
                # (e.g. base64 blobs, URL fragments). Exempt confirmed [placeholder] tokens
                # so that names like [taxpayer_registration_number] are not silently lost.
                if len(text) >= 30 and not _is_ph:
                    continue

                wx0    = float(word["x0"])
                wtop   = float(word["top"])
                wx1    = float(word["x1"])
                wbot   = float(word["bottom"])
                wh     = wbot - wtop  # label height ≈ font size

                # Detect [placeholder] tokens — ASCII identifier, min 5 chars to avoid
                # false-positives from bibliography refs [1], section markers [注], etc.
                is_placeholder = _is_ph and len(text) >= 5

                if is_placeholder:
                    fill_x = round(wx0, 1)
                    fill_y = round(wtop, 1)
                else:
                    cell = _find_containing_cell(wx0, wtop, wx1, wbot, cells)

                    if cell:
                        right_space = cell["x1"]     - wx1  - 3
                        below_space = cell["bottom"]  - wbot - 2
                        # Fill below when there is meaningfully more vertical room
                        # (threshold: at least 1.5× the label height)
                        if below_space > wh * 1.5 and below_space > right_space:
                            fill_x = round(wx0, 1)
                            fill_y = round(wbot + 2, 1)
                        else:
                            fill_x = round(wx1 + 3, 1)
                            fill_y = round(wtop, 1)
                    else:
                        # No enclosing cell found — fall back to right of label
                        fill_x = round(wx1 + 5, 1)
                        fill_y = round(wtop, 1)

                entry: dict = {
                    "page":       page_idx + 1,
                    "label":      text,
                    "x0":         round(wx0, 1),
                    "top":        round(wtop, 1),
                    "x1":         round(wx1, 1),
                    "bottom":     round(wbot, 1),
                    "fill_x":     fill_x,
                    "fill_y":     fill_y,
                    "fill_value": "",
                }
                if is_placeholder:
                    entry["is_placeholder"] = True
                    # Record the placeholder's own font size so fill_form.py can
                    # insert the replacement text at exactly the same size, ensuring
                    # visual consistency across all fields regardless of the form's
                    # global suggested_font_size.
                    detected_size = _font_size_at(wx0, wtop, wx1, wbot)
                    if detected_size is not None:
                        entry["font_size"] = round(detected_size, 1)

                annotations.append(entry)

    # Use median font size from template so fill text matches the form's visual scale
    suggested_font_size = 8.0
    if font_sizes:
        font_sizes.sort()
        suggested_font_size = round(font_sizes[len(font_sizes) // 2], 1)

    return {
        "form_type": "layout_based",
        "annotation_count": len(annotations),
        "suggested_font_size": suggested_font_size,
        "annotations": annotations[:100],
        "note": "Set fill_value on each annotation. Coordinates use top-left origin (pdfplumber convention); fill_form.py handles coordinate conversion automatically.",
    }


def check_annotation_overlaps(annotations: list[dict], font_size: float = 10.0) -> list[dict]:
    """
    Validate layout-based annotation bounding boxes for two types of problems:
    1. Overlapping fill zones (would produce visually colliding text)
    2. Fill zones too small for the given font size

    Returns a list of issue dicts, empty if all clear.
    """
    issues: list[dict] = []
    min_box_height = font_size * 1.1  # need at least 110% of font size in height

    for i, ann in enumerate(annotations):
        fill_x  = float(ann.get("fill_x", ann.get("x1", 0) + 5))
        fill_y  = float(ann.get("fill_y", ann.get("top", 0)))
        fill_x1 = fill_x + max(len(ann.get("fill_value", "")) * font_size * 0.6, 40)
        fill_y1 = fill_y + font_size + 4

        box_height = fill_y1 - fill_y
        if box_height < min_box_height:
            issues.append({
                "type": "too_small",
                "annotation_index": i,
                "label": ann.get("label", ""),
                "page": ann.get("page", 1),
                "detail": f"box height {box_height:.1f}pt < minimum {min_box_height:.1f}pt for font size {font_size}",
            })

        # Check overlap against all subsequent annotations on the same page
        for j, other in enumerate(annotations[i + 1:], start=i + 1):
            if other.get("page", 1) != ann.get("page", 1):
                continue
            ox  = float(other.get("fill_x", other.get("x1", 0) + 5))
            oy  = float(other.get("fill_y", other.get("top", 0)))
            ox1 = ox + max(len(other.get("fill_value", "")) * font_size * 0.6, 40)
            oy1 = oy + font_size + 4

            # AABB overlap test
            if fill_x < ox1 and fill_x1 > ox and fill_y < oy1 and fill_y1 > oy:
                issues.append({
                    "type": "overlap",
                    "annotation_index_a": i,
                    "annotation_index_b": j,
                    "label_a": ann.get("label", ""),
                    "label_b": other.get("label", ""),
                    "page": ann.get("page", 1),
                    "detail": "fill zones overlap — text will collide",
                })

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a PDF form and generate a field descriptor JSON."
    )
    parser.add_argument("pdf_file", help="Input PDF path")
    parser.add_argument("--output", "-o", help="Save field descriptor to this JSON file")
    parser.add_argument("--check-overlaps", action="store_true",
                        help="After inspection, validate annotation fill zones for overlaps "
                             "and size issues (layout_based forms only)")
    parser.add_argument("--font-size", type=float, default=10.0,
                        help="Font size used for overlap/size validation (default: 10)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else None

    def local_ready() -> bool:
        return all(
            importlib.util.find_spec(module) is not None
            for module in ("pypdf", "pdfplumber")
        )

    def cloud_ready() -> bool:
        try:
            return resolve_qwenwork_cli(required=False) is not None
        except RuntimeError:
            return False

    def run_cloud() -> Path | bool:
        try:
            result = run_document_tool(("document", "pdf", "inspect-form"), pdf_path)
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_FORM_INSPECTION_FAILED", retryable=True) from exc
        try:
            metadata = extract_document_tool_metadata(result)
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_FORM_INSPECTION_INVALID", retryable=True) from exc
        descriptor = metadata.get("form")
        if not isinstance(descriptor, dict):
            raise BackendFailure("CLOUD_FORM_INSPECTION_INVALID", retryable=True)
        if args.check_overlaps and descriptor.get("form_type") == "layout_based":
            issues = check_annotation_overlaps(descriptor.get("annotations", []), args.font_size)
            descriptor["overlap_check"] = {
                "font_size": args.font_size,
                "issue_count": len(issues),
                "issues": issues,
            }
        encoded = json.dumps(descriptor, indent=2, ensure_ascii=False)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(encoded, encoding="utf-8")
            print(f"Field descriptor saved → {output_path}")
            return output_path
        print(encoded)
        return True

    def valid_result(result: Path | bool) -> bool:
        if result is True:
            return True
        if not isinstance(result, Path) or not result.is_file() or result.stat().st_size < 2:
            return False
        try:
            return isinstance(json.loads(result.read_text(encoding="utf-8")), dict)
        except (OSError, json.JSONDecodeError):
            return False

    try:
        handled = execute_semantic_script(
            argv=[str(Path(__file__).resolve()), *sys.argv[1:]],
            local_ready=local_ready,
            cloud_ready=cloud_ready,
            run_cloud=run_cloud,
            local_result=lambda: output_path if output_path is not None else True,
            validate=valid_result,
        )
        if handled:
            return
    except BackendFailure as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # First check for AcroForm
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        acroform = reader.trailer.get("/Root", {}).get("/AcroForm")
        has_acroform = acroform is not None and bool(reader.get_fields())
    except Exception:
        has_acroform = False

    if has_acroform:
        descriptor = inspect_acroform(pdf_path)
        if "error" in descriptor:
            print(f"Error: {descriptor['error']}", file=sys.stderr)
            sys.exit(1)
        print(f"Form type: AcroForm — {descriptor['field_count']} fillable field(s) detected")
    else:
        descriptor = inspect_layout_based(pdf_path)
        if "error" in descriptor:
            print(f"Error: {descriptor['error']}", file=sys.stderr)
            sys.exit(1)
        print(f"Form type: Layout-based — {descriptor['annotation_count']} label zone(s) detected")
        print("Tip: Edit fill_value in the output JSON, then run fill_form.py")

        if args.check_overlaps:
            issues = check_annotation_overlaps(
                descriptor.get("annotations", []), args.font_size
            )
            descriptor["overlap_check"] = {
                "font_size": args.font_size,
                "issue_count": len(issues),
                "issues": issues,
            }
            if issues:
                print(f"\nOverlap check: {len(issues)} issue(s) found")
                for issue in issues:
                    prefix = "  OVERLAP" if issue["type"] == "overlap" else "  TOO_SMALL"
                    print(f"{prefix} (page {issue['page']}): {issue['detail']}")
                    if issue["type"] == "overlap":
                        print(f"    Labels: '{issue['label_a']}' ↔ '{issue['label_b']}'")
            else:
                print("\nOverlap check: no issues found ✓")

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(descriptor, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Field descriptor saved → {out_path}")
    else:
        print(json.dumps(descriptor, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
