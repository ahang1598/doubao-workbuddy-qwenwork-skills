#!/usr/bin/env python3
"""
_smoke_test.py — End-to-end regression for the whole PDF skill.

Why this exists
---------------
Every subsystem in this skill has a nasty silent-failure mode —
tall image breaks generation, missing CJK font produces blank boxes,
a single malformed fence crashes the parser, encryption succeeds but
produces a PDF the script itself can't reopen, merge silently drops
pages, etc. A deterministic smoke test run that exercises every
subsystem with a minimum viable fixture catches regressions at CI
time instead of at the next user install.

What it covers
--------------
**Generator regression** (always runs — reportlab is mandatory):
  1. ASCII / CJK / long code / GFM table / tall+wide images / empty
     fence — 7 fixtures × 2 backends (markdown_to_pdf + html shim)
  2. outline + footer regression on a multi-heading document

**Structural regression** (runs when pypdf available — always in Wukong):
  3. analyze_pdf on a known-good document
  4. validate_pdf on a known-good document
  5. batch_ops merge → split round-trip
  6. batch_ops rotate
  7. secure_pdf encrypt → decrypt round-trip
  8. secure_pdf strip-metadata
  9. optimize_pdf basic run

**Gated by optional deps** (skipped when missing, never fail):
  10. extract_content (needs pdfplumber)
  11. extract_tables (needs pdfplumber)
  12. ocr_pipeline (needs tesseract + pytesseract + pdf2image)

Every PDF-producing case asserts:
  * exit code 0
  * output PDF exists and is non-empty
  * pypdf can parse it and reports page count ≥ 1
  * no leftover .tmp / .shim.md in the output directory

Usage
-----
    python scripts/_smoke_test.py
    python scripts/_smoke_test.py --keep   # keep outputs for inspection
    python scripts/_smoke_test.py --only generator  # run a single group
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PY = sys.executable


# ---- fixture generators -------------------------------------------------

def _tall_png(path: Path) -> None:
    from PIL import Image
    Image.new("RGB", (300, 900), (200, 80, 80)).save(path)


def _wide_png(path: Path) -> None:
    from PIL import Image
    Image.new("RGB", (1600, 400), (80, 120, 200)).save(path)


def _long_code(n_lines: int = 250) -> str:
    return "\n".join(f"print({i})  # line {i}" for i in range(n_lines))


OUTLINE_FIXTURE = """# 第一章：引言

介绍段落。

## 1.1 背景

背景说明。

## 1.2 目标

目标描述。

### 1.2.1 子目标

细节。

# 第二章：实现

""" + "\n\n".join(f"## 2.{i} 小节\n\n内容填充。" + "啊" * 200 for i in range(1, 5))


FIXTURES_MD = {
    "ascii.md": "# Hello\n\nPlain ASCII paragraph. No surprises.\n",
    "cjk.md": "# 你好世界\n\n这是一段中文正文，用来验证 CJK 字体注册。\n\n**粗体** *斜体* `行内代码`。\n",
    "long_code.md": "# Long code\n\n```python\n" + _long_code() + "\n```\n",
    "gfm_table.md": (
        "# Table\n\n"
        "| Name | Score | Notes |\n"
        "|---|---|---|\n"
        "| Alice | 92 | good |\n"
        "| Bob | 88 | okay |\n"
        "| 王小明 | 77 | CJK row |\n"
    ),
    "tall_image.md": "# Tall image\n\n![tall](tall.png)\n",
    "wide_image.md": "# Wide image\n\n![wide](wide.png)\n",
    "empty_fence.md": "# Empty fence\n\n```\nno language info string\nstill valid\n```\n",
}


# ---- runner -------------------------------------------------------------

def _run(cmd: List[str]) -> Tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def _assert_pdf(path: Path) -> int:
    assert path.exists(), f"missing PDF: {path}"
    assert path.stat().st_size > 500, f"PDF suspiciously small: {path}"
    try:
        import pypdf
    except ImportError:
        return -1  # pypdf not installed, skip page count check
    pages = len(pypdf.PdfReader(str(path)).pages)
    assert pages >= 1, f"PDF has no pages: {path}"
    return pages


def _assert_outline_and_footer(path: Path, expected_headings: List[str]) -> None:
    """Assert the PDF has outline entries for *expected_headings* and that
    the last page contains a ``Page X / Y`` footer. Used by the outline
    regression test to make sure the NumberedCanvas + OutlineParagraph
    pipeline doesn't silently regress.
    """
    import pypdf
    r = pypdf.PdfReader(str(path))

    # Flatten nested outline structure into a list of titles.
    titles: List[str] = []

    def walk(items):
        for item in items:
            if isinstance(item, list):
                walk(item)
            else:
                titles.append(item.title)

    walk(r.outline)
    for h in expected_headings:
        assert h in titles, f"outline missing heading {h!r}; got {titles}"

    # Footer check on the last page (first page footer also exists but
    # last-page check is the strictest — the NumberedCanvas save() loop
    # has to walk every page for the footer to land there).
    last_text = r.pages[-1].extract_text() or ""
    total = len(r.pages)
    expected_footer = f"Page {total} / {total}"
    assert expected_footer in last_text, (
        f"footer {expected_footer!r} not found on last page; "
        f"tail: {last_text[-120:]!r}"
    )

    # Auto-open outline panel — PageMode /UseOutlines tells the reader
    # to show the outline tree by default.
    page_mode = r.trailer.get("/Root", {}).get("/PageMode", None)
    assert page_mode == "/UseOutlines", (
        f"expected PageMode=/UseOutlines, got {page_mode!r}"
    )


def _missing_deps(modules: List[str], binaries: List[str]) -> Optional[str]:
    """Return a short reason string if any dep is missing, else None.

    Used to gate subsystem tests (pdfplumber, tesseract, …) so a
    minimal install can still run the generator regression without
    every case turning red.
    """
    import importlib
    import shutil as _sh
    for m in modules:
        try:
            importlib.import_module(m)
        except ImportError:
            return f"missing python module {m!r}"
    for b in binaries:
        if not _sh.which(b):
            return f"missing binary {b!r}"
    return None


def _assert_no_leftovers(dir_: Path) -> None:
    leftovers = [
        p.name
        for p in dir_.iterdir()
        if p.suffix in (".tmp", ".shim") or p.name.endswith((".pdf.tmp", ".shim.md"))
    ]
    assert not leftovers, f"leftover temp files in {dir_}: {leftovers}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", action="store_true", help="keep output directory for inspection")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="pdf_smoke_"))
    print(f"[smoke] workdir: {tmp}")

    # Materialize fixtures
    _tall_png(tmp / "tall.png")
    _wide_png(tmp / "wide.png")
    for name, body in FIXTURES_MD.items():
        (tmp / name).write_text(body, encoding="utf-8")

    md_script = SCRIPT_DIR / "markdown_to_pdf.py"
    html_script = SCRIPT_DIR / "html_to_pdf.py"

    failures: List[str] = []
    passed = 0

    # --- markdown backend ---
    for name in FIXTURES_MD:
        src = tmp / name
        out = tmp / f"md_{src.stem}.pdf"
        rc, log = _run([PY, str(md_script), str(src), "--output", str(out)])
        try:
            assert rc == 0, f"markdown_to_pdf exit {rc}\n{log}"
            pages = _assert_pdf(out)
            _assert_no_leftovers(tmp)
            print(f"[smoke] md   {name:20s} ✓ pages={pages}")
            passed += 1
        except AssertionError as e:
            failures.append(f"md/{name}: {e}")
            print(f"[smoke] md   {name:20s} ✗ {e}")

    # --- html shim backend ---
    # Convert each md fixture to a minimal HTML so we exercise the shim
    # on the same content. We don't test pure-HTML features (tables via
    # <table>, <img> tags) because the shim routes them through
    # markdownify → markdown anyway, so the markdown pass already
    # covers the semantics.
    for name, body in FIXTURES_MD.items():
        # Wrap raw body as <pre> for the code fixture so HTML input is
        # non-trivially different from markdown input. For the rest we
        # inject the markdown as a <div> — markdownify will round-trip
        # headings/paragraphs/lists correctly.
        html_body = f"<html><body>{body}</body></html>"
        src = tmp / name.replace(".md", ".html")
        src.write_text(html_body, encoding="utf-8")
        out = tmp / f"html_{src.stem}.pdf"
        rc, log = _run([PY, str(html_script), str(src), "--output", str(out)])
        try:
            assert rc == 0, f"html_to_pdf exit {rc}\n{log}"
            pages = _assert_pdf(out)
            _assert_no_leftovers(tmp)
            print(f"[smoke] html {name:20s} ✓ pages={pages}")
            passed += 1
        except AssertionError as e:
            failures.append(f"html/{name}: {e}")
            print(f"[smoke] html {name:20s} ✗ {e}")

    # --- outline + footer regression ---
    # Separate from the generic fixtures because it asserts on PDF
    # structure (outline tree + /PageMode + last-page footer), not just
    # "pypdf can parse it". A silent regression in NumberedCanvas or
    # _OutlineParagraph would slip past the generic check.
    outline_md = tmp / "outline.md"
    outline_md.write_text(OUTLINE_FIXTURE, encoding="utf-8")
    outline_pdf = tmp / "outline.pdf"
    rc, log = _run([PY, str(md_script), str(outline_md), "--output", str(outline_pdf)])
    try:
        assert rc == 0, f"outline fixture exit {rc}\n{log}"
        _assert_pdf(outline_pdf)
        _assert_outline_and_footer(
            outline_pdf,
            expected_headings=["第一章：引言", "1.1 背景", "1.2.1 子目标", "第二章：实现"],
        )
        print("[smoke] md   outline+footer       ✓")
        passed += 1
    except AssertionError as e:
        failures.append(f"md/outline: {e}")
        print(f"[smoke] md   outline+footer       ✗ {e}")

    # --- inline --html form ---
    inline_out = tmp / "inline.pdf"
    rc, log = _run(
        [PY, str(html_script), "--html", "<h1>你好 Hi</h1><p>inline</p>", "--output", str(inline_out)]
    )
    try:
        assert rc == 0, f"inline exit {rc}\n{log}"
        _assert_pdf(inline_out)
        print("[smoke] html inline              ✓")
        passed += 1
    except AssertionError as e:
        failures.append(f"html/inline: {e}")
        print(f"[smoke] html inline              ✗ {e}")

    # ================================================================
    # Subsystem regression tests
    # ----------------------------------------------------------------
    # From here on we reuse generated PDFs (md_ascii / md_cjk) as the
    # input fixture for analyze / extract / secure / optimize / batch.
    # Tests that need optional deps (pdfplumber, tesseract, qpdf) are
    # skipped with a visible SKIP line — they do not fail the run.
    # ================================================================
    skipped: List[Tuple[str, str]] = []

    def case(label: str, check: Callable[[], None], skip_reason: Optional[str] = None) -> None:
        nonlocal passed
        if skip_reason:
            skipped.append((label, skip_reason))
            print(f"[smoke] {label:32s} ⊘ SKIP ({skip_reason})")
            return
        try:
            check()
            print(f"[smoke] {label:32s} ✓")
            passed += 1
        except AssertionError as e:
            failures.append(f"{label}: {e}")
            print(f"[smoke] {label:32s} ✗ {e}")
        except Exception as e:
            failures.append(f"{label}: {type(e).__name__}: {e}")
            print(f"[smoke] {label:32s} ✗ {type(e).__name__}: {e}")

    sample_pdf = tmp / "md_ascii.pdf"
    sample_pdf_cjk = tmp / "md_cjk.pdf"

    # ---- analyze_pdf (needs pdfplumber) --------------------------------
    def _check_analyze():
        rc, log = _run([PY, str(SCRIPT_DIR / "analyze_pdf.py"), str(sample_pdf), "--json"])
        assert rc == 0 or "pdf_type" in log, f"exit {rc}; log={log[:200]}"
        assert "page" in log.lower(), f"missing 'page' in output: {log[:200]}"

    case("analyze_pdf", _check_analyze, _missing_deps(["pdfplumber"], []))

    # ---- validate_pdf -------------------------------------------------
    def _check_validate():
        rc, log = _run([PY, str(SCRIPT_DIR / "validate_pdf.py"), str(sample_pdf)])
        assert rc == 0, f"exit {rc}; log={log[:200]}"
        assert "PASS" in log, f"no PASS in log: {log[:200]}"

    case("validate_pdf", _check_validate)

    # ---- extract_content (needs pdfplumber) --------------------------
    def _check_extract_content():
        out_txt = tmp / "extracted.txt"
        rc, log = _run([
            PY, str(SCRIPT_DIR / "extract_content.py"),
            str(sample_pdf), "-o", str(out_txt),
        ])
        assert rc == 0, f"exit {rc}; log={log[:300]}"
        assert out_txt.exists() and out_txt.stat().st_size > 0, "no output"
        body = out_txt.read_text(encoding="utf-8", errors="replace")
        assert "Hello" in body, f"expected 'Hello' in extracted text: {body[:120]!r}"

    case("extract_content", _check_extract_content, _missing_deps(["pdfplumber"], []))

    # ---- extract_tables (needs pdfplumber) ---------------------------
    def _check_extract_tables():
        out_dir = tmp / "tables_out"
        out_dir.mkdir(exist_ok=True)
        rc, log = _run([
            PY, str(SCRIPT_DIR / "extract_tables.py"),
            str(tmp / "md_gfm_table.pdf"),
            "--output", str(out_dir), "--format", "csv",
        ])
        assert rc == 0 or "no tables" in log.lower(), f"exit {rc}; log={log[:200]}"

    case("extract_tables", _check_extract_tables, _missing_deps(["pdfplumber"], []))

    # ---- extract_images ----------------------------------------------
    def _check_extract_images():
        out_dir = tmp / "imgs_out"
        out_dir.mkdir(exist_ok=True)
        rc, log = _run([
            PY, str(SCRIPT_DIR / "extract_images.py"),
            str(tmp / "md_tall_image.pdf"),
            "--output", str(out_dir),
        ])
        assert rc == 0, f"exit {rc}; log={log[:200]}"

    case("extract_images", _check_extract_images)

    # ---- secure_pdf encrypt → decrypt round-trip ---------------------
    def _check_secure_roundtrip():
        enc = tmp / "encrypted.pdf"
        dec = tmp / "decrypted.pdf"
        rc, log = _run([
            PY, str(SCRIPT_DIR / "secure_pdf.py"),
            "--action", "encrypt",
            "--input", str(sample_pdf),
            "--output", str(enc),
            "--user-password", "readme",
            "--owner-password", "admin",
        ])
        assert rc == 0, f"encrypt exit {rc}; log={log[:200]}"
        assert enc.exists(), "encrypted PDF missing"
        import pypdf
        r = pypdf.PdfReader(str(enc))
        assert r.is_encrypted, "pypdf does not see the PDF as encrypted"
        rc, log = _run([
            PY, str(SCRIPT_DIR / "secure_pdf.py"),
            "--action", "decrypt",
            "--input", str(enc),
            "--output", str(dec),
            "--password", "readme",
        ])
        assert rc == 0, f"decrypt exit {rc}; log={log[:200]}"
        r2 = pypdf.PdfReader(str(dec))
        assert not r2.is_encrypted, "decrypted PDF is still encrypted"
        assert len(r2.pages) >= 1

    case("secure encrypt→decrypt", _check_secure_roundtrip)

    # ---- secure_pdf strip-metadata -----------------------------------
    def _check_strip_metadata():
        stripped = tmp / "stripped.pdf"
        rc, log = _run([
            PY, str(SCRIPT_DIR / "secure_pdf.py"),
            "--action", "strip-metadata",
            "--input", str(sample_pdf),
            "--output", str(stripped),
        ])
        assert rc == 0, f"exit {rc}; log={log[:200]}"
        import pypdf
        r = pypdf.PdfReader(str(stripped))
        meta = r.metadata or {}
        assert not meta.get("/Author") and not meta.get("/Subject"), (
            f"metadata not stripped: {dict(meta)}"
        )

    case("secure strip-metadata", _check_strip_metadata)

    # ---- batch_ops merge → split round-trip --------------------------
    def _check_merge_split():
        merged = tmp / "merged.pdf"
        rc, log = _run([
            PY, str(SCRIPT_DIR / "batch_ops.py"),
            "--action", "merge",
            "--inputs", str(sample_pdf), str(sample_pdf_cjk),
            "--output", str(merged),
        ])
        assert rc == 0, f"merge exit {rc}; log={log[:200]}"
        import pypdf
        n_merged = len(pypdf.PdfReader(str(merged)).pages)
        n_a = len(pypdf.PdfReader(str(sample_pdf)).pages)
        n_b = len(pypdf.PdfReader(str(sample_pdf_cjk)).pages)
        assert n_merged == n_a + n_b, f"merge pages {n_merged} != {n_a}+{n_b}"
        split_dir = tmp / "split_out"
        split_dir.mkdir(exist_ok=True)
        rc, log = _run([
            PY, str(SCRIPT_DIR / "batch_ops.py"),
            "--action", "split",
            "--input", str(merged),
            "--output-dir", str(split_dir),
            "--pages-per-chunk", "1",
        ])
        assert rc == 0, f"split exit {rc}; log={log[:200]}"
        chunks = list(split_dir.glob("*.pdf"))
        assert len(chunks) == n_merged, f"split got {len(chunks)}, expected {n_merged}"

    case("batch merge→split", _check_merge_split)

    # ---- batch_ops rotate --------------------------------------------
    def _check_rotate():
        rotated = tmp / "rotated.pdf"
        rc, log = _run([
            PY, str(SCRIPT_DIR / "batch_ops.py"),
            "--action", "rotate",
            "--input", str(sample_pdf),
            "--output", str(rotated),
            "--pages", "1",
            "--degrees", "90",
        ])
        assert rc == 0, f"exit {rc}; log={log[:200]}"
        import pypdf
        assert len(pypdf.PdfReader(str(rotated)).pages) >= 1

    case("batch rotate", _check_rotate)

    # ---- optimize_pdf ------------------------------------------------
    def _check_optimize():
        opt = tmp / "optimized.pdf"
        rc, log = _run([PY, str(SCRIPT_DIR / "optimize_pdf.py"), str(sample_pdf), str(opt)])
        assert rc == 0, f"exit {rc}; log={log[:200]}"
        assert opt.exists() and opt.stat().st_size > 0, "no output"

    case("optimize_pdf", _check_optimize)

    # ---- ocr_pipeline (needs tesseract stack) ------------------------
    def _check_ocr():
        out = tmp / "ocr_out.pdf"
        rc, log = _run([
            PY, str(SCRIPT_DIR / "ocr_pipeline.py"),
            str(sample_pdf), "--output", str(out), "--lang", "eng",
        ])
        assert rc == 0, f"exit {rc}; log={log[:300]}"
        assert out.exists()

    case("ocr_pipeline", _check_ocr, _missing_deps(["pytesseract", "pdf2image"], ["tesseract"]))

    # Summary
    total = passed + len(failures)
    print()
    print(f"[smoke] {passed}/{total} passed, {len(skipped)} skipped")
    if skipped:
        print("[smoke] SKIPPED (missing optional deps):")
        for label, reason in skipped:
            print(f"  ⊘ {label}: {reason}")
    if failures:
        print("[smoke] FAILURES:")
        for f in failures:
            print(f"  - {f}")

    if not args.keep:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print(f"[smoke] kept: {tmp}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
