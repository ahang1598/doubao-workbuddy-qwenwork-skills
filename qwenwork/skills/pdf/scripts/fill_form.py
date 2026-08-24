#!/usr/bin/env python3
"""
fill_form.py — PDF Form Filler

Fills a PDF form using the JSON descriptor produced by inspect_form.py.
Supports both AcroForm (fillable fields) and layout-based PDFs.

Layout-based filling uses pymupdf (fitz) to write text directly into the page
content stream, ensuring consistent rendering across all PDF viewers. Falls back
to FreeText annotations via pypdf if pymupdf is unavailable.

Usage:
    # Fill AcroForm fields
    python scripts/fill_form.py form.pdf fields_with_values.json output.pdf

    # Fill layout-based form
    python scripts/fill_form.py form.pdf annotations_with_values.json output.pdf \
        --font-size 10 --font-color black
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import resolve_qwenwork_cli, run_document_tool
from _execution_route import BackendFailure
from _semantic_route import execute_semantic_script


_CJK_RANGES = (
    ('\u2e80', '\u2fff'),  # CJK Radicals Supplement + Kangxi Radicals
    ('\u3000', '\u303f'),  # CJK Symbols and Punctuation (incl. 、。「」)
    ('\u3040', '\u30ff'),  # Hiragana + Katakana
    ('\u3400', '\u4dbf'),  # CJK Extension A (rare personal-name chars)
    ('\u4e00', '\u9fff'),  # CJK Unified Ideographs (base block)
    ('\uac00', '\ud7af'),  # Hangul Syllables
    ('\uf900', '\ufaff'),  # CJK Compatibility Ideographs
    ('\ufe30', '\ufe4f'),  # CJK Compatibility Forms
    ('\uff00', '\uffef'),  # Halfwidth and Fullwidth Forms (incl. ＡＢ, ，。)
)


def _has_cjk(text: str) -> bool:
    return any(lo <= ch <= hi for ch in text for lo, hi in _CJK_RANGES)


def fill_acroform(pdf_path: Path, descriptor: dict, output_path: Path) -> int:
    """
    Fill AcroForm fields.

    Splits values by script: CJK-containing values are filled via pymupdf so the
    appearance stream uses a CJK-capable font (china-ss); ASCII-only values go
    through pypdf's standard path. This avoids the "characters not supported by
    font encoding" corruption that happens when pypdf encodes CJK against a
    form's Helvetica-based /DA.

    Returns count of filled fields.
    """
    try:
        import pypdf
    except ImportError:
        print("Error: pypdf required. Run: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    field_values: dict[str, str] = {}
    for field in descriptor.get("fields", []):
        fill_val = field.get("fill_value", "")
        if fill_val:
            name = field["name"]
            if field.get("type") == "checkbox":
                checked_val = field.get("checked_value", "Yes")
                field_values[name] = checked_val if fill_val.lower() in ("true", "yes", "1", "on") else "Off"
            else:
                field_values[name] = fill_val

    cjk_values = {k: v for k, v in field_values.items() if _has_cjk(v)}
    ascii_values = {k: v for k, v in field_values.items() if not _has_cjk(v)}

    current_path = pdf_path
    tmp_path: Path | None = None

    if ascii_values:
        reader = pypdf.PdfReader(str(current_path))
        writer = pypdf.PdfWriter()
        writer.append(reader)
        for page in writer.pages:
            writer.update_page_form_field_values(page, ascii_values, auto_regenerate=True)
        target = output_path if not cjk_values else output_path.with_suffix(output_path.suffix + ".ascii.tmp")
        with open(target, "wb") as fh:
            writer.write(fh)
        current_path = target
        if cjk_values:
            tmp_path = target

    if cjk_values:
        try:
            import fitz
        except ImportError:
            print("Error: pymupdf required for CJK AcroForm filling. Run: pip install pymupdf",
                  file=sys.stderr)
            sys.exit(1)
        # pymupdf cannot change text_font on an existing widget, so the
        # regenerated /AP would still reference the form's non-CJK /DA font and
        # render as blank boxes. We therefore combine two actions:
        #   (1) widget.field_value = value — stores the Unicode string in /V so
        #       downstream form readers (pypdf, Acrobat JS, etc.) extract it
        #       correctly;
        #   (2) page.insert_text at the widget rect with china-ss — paints the
        #       text into the page content stream so *every* viewer renders it
        #       correctly regardless of the field's /DA font.
        cjk_scale = _cjk_render_scale(fitz)
        doc = fitz.open(str(current_path))
        try:
            for page in doc:
                for widget in page.widgets() or []:
                    name = widget.field_name
                    if name not in cjk_values:
                        continue
                    value = cjk_values[name]
                    widget.field_value = value
                    widget.update()
                    rect = widget.rect
                    font_size = (rect.height - 4) * cjk_scale
                    if font_size <= 0:
                        font_size = 10 * cjk_scale
                    baseline = fitz.Point(rect.x0 + 2, rect.y0 + font_size)
                    page.insert_text(baseline, value, fontname="china-ss",
                                     fontsize=font_size, color=(0, 0, 0))
            doc.save(str(output_path))
        finally:
            doc.close()
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
    elif not ascii_values:
        # No fill values — just copy through so downstream gets the expected file.
        reader = pypdf.PdfReader(str(pdf_path))
        writer = pypdf.PdfWriter()
        writer.append(reader)
        with open(output_path, "wb") as fh:
            writer.write(fh)

    return len(field_values)


def fill_annotation_based(pdf_path: Path, descriptor: dict, output_path: Path,
                           font_size: float, font_color: tuple) -> int:
    """
    Fill a layout-based form by writing text into the page content stream.
    Uses pymupdf (fitz) for reliable cross-viewer rendering; falls back to
    FreeText annotations via pypdf if fitz is unavailable.
    Returns count of filled entries.
    """
    # Honour the font size detected by inspect_form.py unless the caller overrode it
    effective_font_size = descriptor.get("suggested_font_size", font_size)
    try:
        import fitz
        return _fill_fitz(pdf_path, descriptor, output_path, effective_font_size, font_color)
    except ImportError:
        print("Warning: pymupdf not found, falling back to annotation-based fill "
              "(text may not display in all PDF viewers). "
              "Install with: pip install pymupdf", file=sys.stderr)
        return _fill_annotations_pypdf(pdf_path, descriptor, output_path, effective_font_size, font_color)


def _cjk_render_scale(fitz_module) -> float:
    """
    Measure the ratio of china-ss actual rendered height to nominal font size.
    Different CJK fonts have different ascender metrics; this factor lets us
    correct the font size so filled text visually matches the template's SimSun.
    Result is cached on the module after the first call.
    """
    cached = getattr(_cjk_render_scale, "_cache", None)
    if cached is not None:
        return cached
    fitz = fitz_module
    doc = fitz.open()
    page = doc.new_page(width=100, height=30)
    page.insert_text(fitz.Point(5, 20), "测", fontname="china-ss", fontsize=10)
    blocks = page.get_text("dict")["blocks"]
    doc.close()
    try:
        span = blocks[0]["lines"][0]["spans"][0]
        actual_h = span["bbox"][3] - span["bbox"][1]
        scale = 10.0 / actual_h  # e.g. 10/9.6 ≈ 0.833
    except (IndexError, KeyError, ZeroDivisionError):
        scale = 1.0
    _cjk_render_scale._cache = scale
    return scale


def _fill_fitz(pdf_path: Path, descriptor: dict, output_path: Path,
               font_size: float, font_color: tuple) -> int:
    """Write text directly into page content stream via pymupdf.

    For annotations marked is_placeholder=True, the original placeholder text
    (e.g. '[taxpayer_name]') is permanently erased via redact_annot before the
    real value is drawn at the same position.  This prevents the placeholder and
    the real value from coexisting in the output PDF.

    Font size priority (highest to lowest):
      1. ann["font_size"]  — size detected from the placeholder glyph itself
         by inspect_form.py; guarantees visual consistency with the template.
      2. descriptor["suggested_font_size"]  — median size across the whole page.
      3. font_size argument  — caller-supplied fallback (default 10 pt).
    """
    import fitz

    cjk_scale = _cjk_render_scale(fitz)
    global_font_size = descriptor.get("suggested_font_size", font_size)

    doc = fitz.open(str(pdf_path))
    try:
        annotations = descriptor.get("annotations", [])
        r, g, b = font_color
        filled_count = 0

        # Pass 1: mark redaction areas for all placeholders.
        # Redactions are the only reliable way to erase existing glyphs from the
        # PDF content stream; draw_rect only paints on top and can be seen through.
        for ann in annotations:
            if not ann.get("is_placeholder"):
                continue
            fill_value = ann.get("fill_value", "").strip()
            if not fill_value:
                continue
            page_idx = ann.get("page", 1) - 1
            if page_idx >= len(doc):
                continue
            ph_x0 = float(ann.get("x0", ann.get("fill_x", 0)))
            ph_y0 = float(ann.get("top", ann.get("fill_y", 0)))
            ph_x1 = float(ann.get("x1", ph_x0 + 60))
            # Use per-field font size for the fallback height so that placeholders
            # larger than global_font_size are fully erased (e.g. 14pt title field
            # when the page median is 10pt).
            ph_font_size = float(ann.get("font_size", global_font_size))
            ph_y1 = float(ann.get("bottom", ph_y0 + ph_font_size + 2))
            doc[page_idx].add_redact_annot(
                fitz.Rect(ph_x0, ph_y0, ph_x1, ph_y1), fill=(1, 1, 1)
            )

        # Apply redactions across all pages (rewrites content streams).
        for page in doc:
            page.apply_redactions()

        # Pass 2: insert real values at each annotation's fill position.
        for ann in annotations:
            fill_value = ann.get("fill_value", "").strip()
            if not fill_value:
                continue
            page_idx = ann.get("page", 1) - 1
            if page_idx >= len(doc):
                continue

            x0  = float(ann.get("fill_x", ann.get("x1", 0) + 5))
            top = float(ann.get("fill_y", ann.get("top", 0)))

            # Use per-field font size when available so every field matches
            # the original template's glyph size exactly.
            field_font_size = float(ann.get("font_size", global_font_size))

            if _has_cjk(fill_value):
                fontname = "china-ss"
                # Placeholder replacement: the template's exact pt size is known
                # (from ann["font_size"]), so use it directly without cjk_scale
                # correction.  cjk_scale compensates for china-ss rendering taller
                # than SimSun at the same nominal size, but when we're targeting an
                # exact glyph-matched pt value that correction would shrink the text
                # below the original.
                #
                # Non-placeholder (label-adjacent fill): no exact size is known; we
                # use global_font_size as a visual-match target and apply cjk_scale
                # so it looks the same height as the surrounding SimSun glyphs.
                if ann.get("is_placeholder"):
                    effective = field_font_size
                else:
                    effective = field_font_size * cjk_scale
            else:
                fontname = "helv"
                effective = field_font_size

            point = fitz.Point(x0, top + effective)
            doc[page_idx].insert_text(point, fill_value, fontname=fontname,
                                      fontsize=effective, color=(r, g, b))
            filled_count += 1

        doc.save(str(output_path))
    finally:
        doc.close()
    return filled_count


def _fill_annotations_pypdf(pdf_path: Path, descriptor: dict, output_path: Path,
                             font_size: float, font_color: tuple) -> int:
    """
    Fallback: write text directly into each page's content stream via pypdf.

    Unlike the old FreeText-annotation approach (which many viewers silently hide),
    this injects raw PDF operators (BT … ET) into the existing page content stream
    so the text is permanently visible in every PDF viewer and in print.

    For placeholder tokens (is_placeholder=True), a white filled rectangle is
    prepended to erase the original placeholder glyph before the real value is
    drawn at the same position.

    Per-field font size (ann["font_size"]) is used when available so every field
    matches the original template's glyph size exactly, preventing the mixed
    7/8/10 pt inconsistency that occurs when sizes are hard-coded.

    Limitation: only Latin-1 characters are supported without pymupdf.
    Install pymupdf for full Unicode / CJK support.
    """
    try:
        import pypdf
        import pypdf.generic as generic
    except ImportError:
        print("Error: pypdf required. Run: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    reader = pypdf.PdfReader(str(pdf_path))
    writer = pypdf.PdfWriter()
    writer.append(reader)

    annotations = descriptor.get("annotations", [])
    global_font_size = descriptor.get("suggested_font_size", font_size)
    filled_count = 0
    r, g, b = font_color

    # Warn once when any placeholder will be erased via white-rect overlay.
    # Unlike the fitz path (which uses redact_annot to truly remove glyphs),
    # this pypdf fallback only paints a white rectangle on top — the original
    # text remains in the content stream and is still selectable / copyable.
    if any(ann.get("is_placeholder") and ann.get("fill_value", "").strip()
           for ann in annotations):
        print(
            "Warning: pypdf fallback path — placeholder erasure uses white-rect overlay; "
            "original text remains selectable in the PDF content stream. "
            "Install pymupdf for true glyph redaction.",
            file=sys.stderr,
        )

    # Ensure the fill font is registered in each page's resource dict once.
    # Using a unique resource name /F_FillHelv (rather than /Helvetica) avoids
    # colliding with any existing /Helvetica entry in the original PDF's font dict.
    fill_font_refs: dict[int, object] = {}

    def _ensure_helvetica(page_idx: int) -> None:
        if page_idx in fill_font_refs:
            return
        page = writer.pages[page_idx]
        resources = page.get("/Resources")
        if resources is None:
            resources = generic.DictionaryObject()
            page[generic.NameObject("/Resources")] = resources
        fonts = resources.get("/Font")
        if fonts is None:
            fonts = generic.DictionaryObject()
            resources[generic.NameObject("/Font")] = fonts  # type: ignore[index]
        if "/F_FillHelv" not in fonts:
            helvetica_obj = generic.DictionaryObject({
                generic.NameObject("/Type"):     generic.NameObject("/Font"),
                generic.NameObject("/Subtype"):  generic.NameObject("/Type1"),
                generic.NameObject("/BaseFont"): generic.NameObject("/Helvetica"),
                generic.NameObject("/Encoding"): generic.NameObject("/WinAnsiEncoding"),
            })
            # _add_object is a pypdf internal API (no public equivalent); pin pypdf >= 3.x
            fonts[generic.NameObject("/F_FillHelv")] = writer._add_object(helvetica_obj)  # type: ignore[index]
        fill_font_refs[page_idx] = True

    for ann in annotations:
        fill_value = ann.get("fill_value", "").strip()
        if not fill_value:
            continue

        page_idx = ann.get("page", 1) - 1
        if page_idx >= len(writer.pages):
            continue

        page = writer.pages[page_idx]
        page_height = float(page.mediabox.height)

        # Per-field font size takes priority over the global fallback.
        field_font_size = float(ann.get("font_size", global_font_size))

        # Convert pdfplumber top-origin coords to PDF bottom-origin baseline.
        x0 = float(ann.get("fill_x", ann.get("x1", 0) + 5))
        top_from_top = float(ann.get("fill_y", ann.get("top", 0)))
        baseline_y = page_height - top_from_top - field_font_size

        # Encode as Latin-1; warn and replace CJK with '?' (install pymupdf for CJK).
        try:
            fill_value.encode("latin-1")
            text_for_stream = fill_value
        except UnicodeEncodeError:
            text_for_stream = fill_value.encode("latin-1", errors="replace").decode("latin-1")
            print(
                f"Warning: field contains characters outside Latin-1 (CJK?); "
                f"install pymupdf for full Unicode support. "
                f"Affected value: {fill_value!r}",
                file=sys.stderr,
            )

        escaped = (
            text_for_stream
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

        # For placeholder tokens: prepend a white filled rectangle to erase the
        # original placeholder glyph before the real value is drawn at the same spot.
        erase_ops = b""
        if ann.get("is_placeholder"):
            ph_x0  = float(ann.get("x0",     x0))
            ph_top = float(ann.get("top",     top_from_top))
            ph_x1  = float(ann.get("x1",      x0 + 60))
            ph_bot = float(ann.get("bottom",  top_from_top + field_font_size + 2))
            rect_y0 = page_height - ph_bot
            rect_y1 = page_height - ph_top
            erase_ops = (
                f"q 1 1 1 rg "
                f"{ph_x0:.3f} {rect_y0:.3f} "
                f"{ph_x1 - ph_x0:.3f} {rect_y1 - rect_y0:.3f} re f Q "
            ).encode("latin-1")

        text_ops = erase_ops + (
            f"q "
            f"BT "
            f"/F_FillHelv {field_font_size:.2f} Tf "
            f"{r:.3f} {g:.3f} {b:.3f} rg "
            f"{x0:.3f} {baseline_y:.3f} Td "
            f"({escaped}) Tj "
            f"ET "
            f"Q"
        ).encode("latin-1")

        # Append as a new uncompressed stream object so we never need to
        # decompress-then-recompress the existing page content.
        new_stream = generic.EncodedStreamObject()
        new_stream.set_data(text_ops)
        ref = writer._add_object(new_stream)

        contents = page.get("/Contents")
        if contents is None:
            page[generic.NameObject("/Contents")] = ref
        else:
            if not isinstance(contents, generic.ArrayObject):
                contents = generic.ArrayObject([contents])
            contents.append(ref)
            page[generic.NameObject("/Contents")] = contents

        _ensure_helvetica(page_idx)
        filled_count += 1

    with open(output_path, "wb") as fh:
        writer.write(fh)
    return filled_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill a PDF form from a JSON descriptor.")
    parser.add_argument("pdf_file", help="Input PDF path")
    parser.add_argument("values_file", help="JSON descriptor with fill_value fields set")
    parser.add_argument("output_file", help="Output filled PDF path")
    parser.add_argument("--font-size", type=float, default=10.0,
                        help="Font size for layout-based filling (default: 10)")
    parser.add_argument("--font-color", default="black",
                        choices=["black", "blue", "red"],
                        help="Font color for layout-based filling (default: black)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)
    values_path = Path(args.values_file)
    output_path = Path(args.output_file)

    for p in (pdf_path, values_path):
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            sys.exit(1)

    descriptor = json.loads(values_path.read_text(encoding="utf-8"))
    form_type = descriptor.get("form_type", "acroform")

    values: dict[str, str | bool] = {}
    if form_type == "acroform":
        for field in descriptor.get("fields", []):
            name = field.get("name")
            value = field.get("fill_value", "")
            if isinstance(name, str) and name and isinstance(value, (str, bool)) and value != "":
                values[name] = value
    else:
        for annotation in descriptor.get("annotations", []):
            label = annotation.get("label")
            value = annotation.get("fill_value", "")
            if isinstance(label, str) and label and isinstance(value, (str, bool)) and value != "":
                values[label.strip("[]")] = value

    def local_ready() -> bool:
        return all(
            importlib.util.find_spec(module) is not None
            for module in ("pypdf", "fitz")
        )

    def cloud_ready() -> bool:
        if not values or args.font_color != "black" or args.font_size != 10.0:
            return False
        try:
            return resolve_qwenwork_cli(required=False) is not None
        except RuntimeError:
            return False

    def run_cloud() -> Path:
        try:
            run_document_tool(
                ("document", "pdf", "fill-form"),
                pdf_path,
                save_path=output_path,
                flags=(("values-json", json.dumps(values, ensure_ascii=False, separators=(",", ":"))),),
            )
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_FORM_FILL_FAILED", retryable=True) from exc
        return output_path

    def valid_pdf(path: Path) -> bool:
        if not path.is_file() or path.stat().st_size < 5:
            return False
        with path.open("rb") as source:
            return source.read(5) == b"%PDF-"

    try:
        handled = execute_semantic_script(
            argv=[str(Path(__file__).resolve()), *sys.argv[1:]],
            local_ready=local_ready,
            cloud_ready=cloud_ready,
            run_cloud=run_cloud,
            local_result=lambda: output_path,
            validate=valid_pdf,
        )
        if handled:
            return
    except BackendFailure as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    color_map = {
        "black": (0.0, 0.0, 0.0),
        "blue": (0.0, 0.0, 0.8),
        "red": (0.8, 0.0, 0.0),
    }
    font_color = color_map[args.font_color]

    if form_type == "acroform":
        count = fill_acroform(pdf_path, descriptor, output_path)
        print(f"AcroForm: filled {count} field(s) → {output_path}")
    else:
        count = fill_annotation_based(pdf_path, descriptor, output_path,
                                      args.font_size, font_color)
        print(f"Layout-based: filled {count} field(s) → {output_path}")

    if count == 0:
        print("Warning: no fill_value entries were non-empty. Output PDF is unchanged.")


if __name__ == "__main__":
    main()
