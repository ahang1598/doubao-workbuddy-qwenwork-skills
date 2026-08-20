"""docx — Word document inspection (read-only).

12 subcommands
--------------
outline           heading list (Heading 1/2/3 → text + index).
section-text      extract text under a heading (regex), with min-chars threshold.
count-chars       total visible characters (paragraphs + tables).
table-list        list tables: index, n_rows, n_cols, first-row preview.
table-field       read a single table cell by row/col index OR by row-header label.
has-revisions     detect tracked changes / comments.
check-clauses     check that all expected clause headings exist (set semantics).
signature-block   detect a signature block (盖章/签字/sign here/_____).
layout-compare    compare structure shape (heading_count, para_count, table_count) vs expected.
page-count        EXACT page count via LibreOffice headless conversion (requires soffice).
count-images      count inline + floating pictures (w:drawing / w:pict).
page-setup        page width/height + orientation (per section).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
from typing import Any

from . import _common as C

_DOCX_EXTS = (".docx", ".docm")
_EMU_PER_INCH = 914400  # OOXML measurement unit (English Metric Units)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("outline", help="List Heading 1/2/3 entries.")
    p.add_argument("file")
    p.add_argument("--max-level", type=int, default=3)

    p = sub.add_parser("section-text",
                       help="Extract text under a heading matching --heading-regex.")
    p.add_argument("file")
    p.add_argument("--heading-regex", required=True)
    p.add_argument("--max-chars", type=int, default=20000)

    p = sub.add_parser("count-chars", help="Total visible character count.")
    p.add_argument("file")

    p = sub.add_parser("table-list", help="List all tables (index, dims, header preview).")
    p.add_argument("file")

    p = sub.add_parser("table-field", help="Read a table cell by index or row-header.")
    p.add_argument("file")
    p.add_argument("--table-index", type=int, default=0)
    p.add_argument("--row", type=int, default=None)
    p.add_argument("--col", type=int, default=None)
    p.add_argument("--row-header", default=None,
                   help="if given, find first row whose first cell equals this; --col still required")

    p = sub.add_parser("has-revisions", help="Detect tracked changes / inline comments.")
    p.add_argument("file")

    p = sub.add_parser("check-clauses",
                       help="Check that ALL expected headings exist (subset semantics).")
    p.add_argument("file")
    p.add_argument("--expected", nargs="+", required=True)
    p.add_argument("--match", choices=("exact", "contains", "regex"), default="contains")

    p = sub.add_parser("signature-block",
                       help="Detect a signature/seal block (default cn+en patterns).")
    p.add_argument("file")
    p.add_argument("--pattern", default=None,
                   help="custom regex to OR into the default set")

    p = sub.add_parser("layout-compare",
                       help="Check shape: heading_count / paragraph_count / table_count thresholds.")
    p.add_argument("file")
    p.add_argument("--min-headings", type=int, default=None)
    p.add_argument("--min-paragraphs", type=int, default=None)
    p.add_argument("--min-tables", type=int, default=None)
    p.add_argument("--max-headings", type=int, default=None)
    p.add_argument("--max-paragraphs", type=int, default=None)
    p.add_argument("--max-tables", type=int, default=None)

    p = sub.add_parser(
        "page-count",
        help=("Page count. Default 'auto': try LibreOffice headless (exact); on "
              "DEP_MISSING/PARSE_ERROR fall back to XML heuristic. Override with "
              "--method {auto,soffice,heuristic}."),
    )
    p.add_argument("file")
    p.add_argument("--method", choices=("auto", "soffice", "heuristic"), default="auto",
                   help="auto = soffice→heuristic fallback (default); "
                        "soffice = exact only, error on missing dep; "
                        "heuristic = XML-only, no soffice attempt.")
    p.add_argument("--soffice", default=None,
                   help="explicit path to the soffice binary (default: auto-detect on PATH)")
    p.add_argument("--timeout", type=int, default=60,
                   help="soffice conversion timeout, seconds (default 60)")
    p.add_argument("--min-pages", type=int, default=None)
    p.add_argument("--max-pages", type=int, default=None)

    p = sub.add_parser("count-images",
                       help="Count inline + floating pictures across the document.")
    p.add_argument("file")
    p.add_argument("--min", type=int, default=None,
                   help="optional lower bound to assert on")

    p = sub.add_parser("page-setup",
                       help="Page width/height + orientation per section.")
    p.add_argument("file")
    p.add_argument("--expect-orientation", choices=("portrait", "landscape"), default=None,
                   help="if set, all sections must match this orientation to pass")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open(path: str):
    docx = C.lazy_import("docx")
    abs_path = C.require_file(path, _DOCX_EXTS)
    try:
        return docx.Document(abs_path), abs_path
    except Exception as e:
        raise C.VerifierError(C.ErrCode.PARSE_ERROR,
                              f"docx.Document({abs_path}) failed: {e}") from e


def _heading_level(p) -> int | None:
    name = (p.style.name or "") if p.style else ""
    m = re.match(r"^Heading\s+(\d+)$", name)
    return int(m.group(1)) if m else None


def _all_text(doc) -> str:
    parts: list[str] = []
    for p in doc.paragraphs:
        if p.text:
            parts.append(p.text)
    for t in doc.tables:
        for row in t.rows:
            parts.append("\t".join(c.text for c in row.cells))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# outline
# ---------------------------------------------------------------------------

def cmd_outline(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    headings: list[dict] = []
    for i, p in enumerate(doc.paragraphs):
        lvl = _heading_level(p)
        if lvl is not None and lvl <= args.max_level:
            headings.append({"index": i, "level": lvl, "text": p.text})
    return {
        "file": abs_path,
        "max_level": args.max_level,
        "count": len(headings),
        "headings": headings,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"{len(headings)} headings"
                                + (f", first: H{headings[0]['level']} {headings[0]['text']!r}" if headings else "")),
    }


# ---------------------------------------------------------------------------
# section-text
# ---------------------------------------------------------------------------

def cmd_section_text(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    try:
        regex = re.compile(args.heading_regex)
    except re.error as e:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, f"invalid regex: {e}") from e

    paras = doc.paragraphs
    start_i = -1
    matched_heading = None
    matched_level = -1
    for i, p in enumerate(paras):
        lvl = _heading_level(p)
        if lvl is not None and regex.search(p.text):
            start_i = i
            matched_heading = p.text
            matched_level = lvl
            break

    if start_i < 0:
        return {
            "file": abs_path, "heading_regex": args.heading_regex,
            "found": False, "text": "", "char_count": 0,
            "_evidence": C.evidence(file=abs_path,
                                    locator={"heading_regex": args.heading_regex},
                                    quote="heading not found"),
        }

    out: list[str] = []
    for p in paras[start_i + 1:]:
        lvl = _heading_level(p)
        if lvl is not None and lvl <= matched_level:
            break  # next same-or-higher heading ends the section
        if p.text:
            out.append(p.text)

    body = "\n".join(out)
    truncated = len(body) > args.max_chars
    if truncated:
        body = body[: args.max_chars]
    return {
        "file": abs_path, "heading_regex": args.heading_regex,
        "found": True, "matched_heading": matched_heading, "matched_level": matched_level,
        "char_count": len(body), "truncated": truncated, "text": body,
        "_evidence": C.evidence(file=abs_path,
                                locator={"heading_regex": args.heading_regex,
                                         "matched_heading": matched_heading},
                                quote=f"section under {matched_heading!r}: {len(body)} chars"
                                + (" (truncated)" if truncated else "")),
    }


# ---------------------------------------------------------------------------
# count-chars
# ---------------------------------------------------------------------------

def cmd_count_chars(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    text = _all_text(doc)
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return {
        "file": abs_path,
        "total_chars": len(text),
        "cjk_chars": cjk,
        "paragraph_count": len(doc.paragraphs),
        "table_count": len(doc.tables),
        "_evidence": C.evidence(file=abs_path,
                                quote=f"total={len(text)}, cjk={cjk}, "
                                f"paragraphs={len(doc.paragraphs)}, tables={len(doc.tables)}"),
    }


# ---------------------------------------------------------------------------
# table-list / table-field
# ---------------------------------------------------------------------------

def cmd_table_list(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    tables = []
    for i, t in enumerate(doc.tables):
        first_row = []
        if t.rows:
            first_row = [c.text for c in t.rows[0].cells]
        tables.append({
            "index": i,
            "rows": len(t.rows),
            "cols": len(t.columns),
            "first_row": first_row,
        })
    return {
        "file": abs_path, "count": len(tables), "tables": tables,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"{len(tables)} tables: " +
                                ", ".join(f"#{t['index']}({t['rows']}×{t['cols']})" for t in tables)),
    }


def cmd_table_field(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    if args.table_index < 0 or args.table_index >= len(doc.tables):
        raise C.VerifierError(C.ErrCode.NOT_FOUND,
                              f"table-index {args.table_index} out of range (have {len(doc.tables)} tables)")
    t = doc.tables[args.table_index]
    if args.col is None:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, "--col is required")

    row_idx: int | None = args.row
    matched_row_header: str | None = None
    if args.row_header is not None:
        for ri, row in enumerate(t.rows):
            if not row.cells:
                continue
            if row.cells[0].text.strip() == args.row_header.strip():
                row_idx = ri
                matched_row_header = row.cells[0].text
                break
        if row_idx is None:
            raise C.VerifierError(C.ErrCode.NOT_FOUND,
                                  f"row-header {args.row_header!r} not found in table #{args.table_index}")
    if row_idx is None:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, "either --row or --row-header is required")

    if row_idx < 0 or row_idx >= len(t.rows):
        raise C.VerifierError(C.ErrCode.NOT_FOUND, f"row {row_idx} out of range")
    if args.col < 0 or args.col >= len(t.rows[row_idx].cells):
        raise C.VerifierError(C.ErrCode.NOT_FOUND,
                              f"col {args.col} out of range in row {row_idx}")
    text = t.rows[row_idx].cells[args.col].text
    return {
        "file": abs_path, "table_index": args.table_index,
        "row": row_idx, "col": args.col, "text": text,
        "matched_row_header": matched_row_header,
        "_evidence": C.evidence(file=abs_path,
                                locator={"table": args.table_index, "row": row_idx, "col": args.col},
                                quote=text),
    }


# ---------------------------------------------------------------------------
# has-revisions
# ---------------------------------------------------------------------------

def cmd_has_revisions(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    # python-docx does not expose tracked changes directly; inspect the underlying XML.
    body_xml = doc.element.body.xml
    insertions = body_xml.count("<w:ins ")
    deletions = body_xml.count("<w:del ")
    comments = 0
    try:
        for rel in doc.part.rels.values():
            if rel.reltype.endswith("/comments"):
                from xml.etree import ElementTree as ET
                comments_xml = rel.target_part.blob.decode("utf-8", errors="ignore")
                comments = comments_xml.count("<w:comment ")
                break
    except Exception:
        pass
    has_any = (insertions + deletions + comments) > 0
    return {
        "file": abs_path,
        "insertions": insertions, "deletions": deletions, "comments": comments,
        "has_revisions": has_any,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"insertions={insertions}, deletions={deletions}, comments={comments}"),
    }


# ---------------------------------------------------------------------------
# check-clauses
# ---------------------------------------------------------------------------

def cmd_check_clauses(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    headings = [p.text for p in doc.paragraphs if _heading_level(p) is not None]

    def _hit(want: str) -> bool:
        for h in headings:
            if args.match == "exact" and h.strip() == want.strip():
                return True
            if args.match == "contains" and want in h:
                return True
            if args.match == "regex":
                try:
                    if re.search(want, h):
                        return True
                except re.error:
                    pass
        return False

    matched: list[str] = []
    missing: list[str] = []
    for w in args.expected:
        (matched if _hit(w) else missing).append(w)

    return {
        "file": abs_path, "match_mode": args.match,
        "expected": args.expected, "matched": matched, "missing": missing,
        "passed": not missing, "available_headings": headings[:50],
        "_evidence": C.evidence(file=abs_path,
                                quote=f"matched {len(matched)}/{len(args.expected)}; missing={missing}"),
    }


# ---------------------------------------------------------------------------
# signature-block
# ---------------------------------------------------------------------------

_DEFAULT_SIGNATURE_PATTERNS = [
    r"盖章", r"签字", r"签名", r"署名", r"乙方[（(]?签", r"甲方[（(]?签",
    r"\bSign\s*here\b", r"\bSignature\b", r"_{4,}",
]


def cmd_signature_block(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    text = _all_text(doc)
    patterns = list(_DEFAULT_SIGNATURE_PATTERNS)
    if args.pattern:
        patterns.append(args.pattern)
    hits: list[dict] = []
    for pat in patterns:
        try:
            for m in re.finditer(pat, text):
                hits.append({"pattern": pat, "match": m.group(0)})
                if len(hits) >= 20:
                    break
        except re.error:
            continue
        if len(hits) >= 20:
            break
    return {
        "file": abs_path,
        "patterns": patterns,
        "found": bool(hits),
        "hit_count": len(hits),
        "hits": hits,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"signature hits: {len(hits)}, first: {hits[0]['match'] if hits else '(none)'!r}"),
    }


# ---------------------------------------------------------------------------
# layout-compare
# ---------------------------------------------------------------------------

def cmd_layout_compare(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    n_head = sum(1 for p in doc.paragraphs if _heading_level(p) is not None)
    n_para = len(doc.paragraphs)
    n_tab = len(doc.tables)

    checks: list[dict] = []

    def _push(name: str, actual: int, want: int | None, op: str) -> None:
        if want is None:
            return
        passed = actual >= want if op == "min" else actual <= want
        checks.append({"check": f"{op}_{name}", "expected": want, "actual": actual, "passed": passed})

    _push("headings",   n_head, args.min_headings,  "min")
    _push("paragraphs", n_para, args.min_paragraphs, "min")
    _push("tables",     n_tab,  args.min_tables,    "min")
    _push("headings",   n_head, args.max_headings,  "max")
    _push("paragraphs", n_para, args.max_paragraphs, "max")
    _push("tables",     n_tab,  args.max_tables,    "max")

    overall: bool | None = all(c["passed"] for c in checks) if checks else None
    return {
        "file": abs_path,
        "headings": n_head, "paragraphs": n_para, "tables": n_tab,
        "checks": checks, "passed": overall,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"H={n_head} P={n_para} T={n_tab}; " +
                                ", ".join(f"{c['check']}={c['passed']}" for c in checks)),
    }


# ---------------------------------------------------------------------------
# page-count — exact via LibreOffice headless conversion to PDF, with an
# XML-heuristic fallback when soffice is missing/broken.
#
# Why two methods: GDPval rubrics like "single-page PDF" / "2-3 pages
# inclusive" need page count.  soffice gives the ground truth; the heuristic
# is the safety net for VMs without LibreOffice (DEP_MISSING) or with broken
# installs (PARSE_ERROR / shared-library failures).  The heuristic uses three
# signals in priority order, all from the underlying OOXML:
#
#   1. <w:lastRenderedPageBreak/> — Word writes these markers at the actual
#      page boundaries from its last layout pass.  When present this is
#      essentially exact (Word already did the rendering for us).
#   2. Explicit page breaks: <w:br w:type="page"/> + paragraphs whose pPr
#      contains <w:pageBreakBefore/>.
#   3. Section breaks: each non-continuous <w:sectPr> usually starts a new
#      page; we count them as +1.
#
# Heuristic accuracy on common GDPval shapes:
#   - "single-page memo" (no breaks)               → exact
#   - "memo with explicit break(s)"                 → exact
#   - "multi-section / mixed orientation report"    → near-exact
#   - "long flowing prose, no markers, no breaks"   → undercount (returns 1)
# When the heuristic is forced to undercount we mark `accuracy: 'approximate'`
# and surface the signal counts so the caller can reason about uncertainty.
# ---------------------------------------------------------------------------

def _resolve_soffice(explicit: str | None) -> str:
    if explicit:
        if not os.path.isfile(explicit):
            raise C.VerifierError(C.ErrCode.DEP_MISSING,
                                  f"soffice path {explicit!r} does not exist")
        return explicit
    found = C.find_office_binary()
    if found:
        return found
    raise C.VerifierError(C.ErrCode.DEP_MISSING, C.office_missing_msg())


def _page_count_via_soffice(abs_path: str, soffice: str, timeout: int) -> int:
    """Returns exact page count.  Raises VerifierError on any failure."""
    from . import _pdf_backend as B

    with tempfile.TemporaryDirectory(prefix="verifier-pagecount-") as tmpdir:
        try:
            proc = subprocess.run(
                [soffice, "--headless",
                 "-env:UserInstallation=" + C.dir_to_file_uri(
                     os.path.join(tmpdir, "loprofile")),
                 "--convert-to", "pdf",
                 "--outdir", tmpdir, abs_path],
                # Decode explicitly: text=True alone would use the locale
                # encoding, and on a zh-CN Windows host that is cp936, so a
                # soffice diagnostic containing any non-GBK byte would make
                # subprocess.run raise UnicodeDecodeError instead of letting us
                # report the real conversion failure.
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired as e:
            raise C.VerifierError(
                C.ErrCode.INTERNAL,
                f"soffice conversion timed out after {timeout}s "
                f"(file={abs_path}); raise --timeout if the doc is large",
            ) from e
        if proc.returncode != 0:
            raise C.VerifierError(
                C.ErrCode.PARSE_ERROR,
                f"soffice conversion failed (rc={proc.returncode}): "
                f"stderr={proc.stderr.strip()[:300]!r}",
            )
        base = os.path.splitext(os.path.basename(abs_path))[0] + ".pdf"
        pdf_path = os.path.join(tmpdir, base)
        if not os.path.isfile(pdf_path):
            pdfs = [n for n in os.listdir(tmpdir) if n.lower().endswith(".pdf")]
            if not pdfs:
                raise C.VerifierError(
                    C.ErrCode.PARSE_ERROR,
                    f"soffice produced no PDF in {tmpdir} (rc={proc.returncode})",
                )
            pdf_path = os.path.join(tmpdir, pdfs[0])
        try:
            # The reader must be closed before the TemporaryDirectory is torn
            # down: on Windows an open handle makes shutil.rmtree raise
            # PermissionError (WinError 32).
            with B.open_pdf(pdf_path) as pdf:
                return pdf.page_count
        except C.VerifierError:
            raise
        except Exception as e:
            raise C.VerifierError(
                C.ErrCode.PARSE_ERROR,
                f"failed to count pages in soffice-produced PDF {pdf_path}: {e}",
            ) from e


_LAST_RENDERED_PAGEBREAK_RE = re.compile(r"<w:lastRenderedPageBreak\b")
_EXPLICIT_PAGEBREAK_RE = re.compile(r'<w:br\b[^>]*w:type="page"')
_PAGEBREAK_BEFORE_RE = re.compile(r"<w:pageBreakBefore\b")
# section breaks: every w:sectPr starts a new section; w:type=continuous ones
# don't force a new page.  Default is nextPage.
_SECTPR_RE = re.compile(r"<w:sectPr\b[^>]*>(.*?)</w:sectPr>", re.DOTALL)
_SECT_TYPE_RE = re.compile(r'<w:type\s+w:val="([^"]+)"')


def _heuristic_page_count(abs_path: str) -> dict:
    """XML-only page count + accuracy hint. Returns dict with breakdown."""
    docx = C.lazy_import("docx")
    try:
        doc = docx.Document(abs_path)
    except Exception as e:
        raise C.VerifierError(
            C.ErrCode.PARSE_ERROR,
            f"docx.Document({abs_path}) failed: {e}",
        ) from e

    # We need the underlying body XML + headers/footers for full coverage,
    # but body alone catches >99% of relevant page-break markers.
    body_xml = doc.element.body.xml

    n_last_rendered = len(_LAST_RENDERED_PAGEBREAK_RE.findall(body_xml))
    n_explicit = len(_EXPLICIT_PAGEBREAK_RE.findall(body_xml))
    n_break_before = len(_PAGEBREAK_BEFORE_RE.findall(body_xml))

    # Section breaks: only count those that actually start a new page (default
    # = nextPage; continuous / nextColumn don't).
    n_sect_page = 0
    n_sect_continuous = 0
    for m in _SECTPR_RE.finditer(body_xml):
        body = m.group(1)
        type_m = _SECT_TYPE_RE.search(body)
        if type_m and type_m.group(1) == "continuous":
            n_sect_continuous += 1
        else:
            n_sect_page += 1
    # The very last sectPr is the document-level one; it doesn't start a new
    # page on its own — it just closes the doc.  Subtract one if we saw any.
    if n_sect_page > 0:
        n_sect_page -= 1

    # Decision: prefer lastRenderedPageBreak when present (exact), else combine.
    if n_last_rendered > 0:
        page_count = n_last_rendered + 1
        accuracy = "near-exact"
        rationale = f"{n_last_rendered} <w:lastRenderedPageBreak/> markers + 1"
    else:
        explicit_total = n_explicit + n_break_before + n_sect_page
        page_count = explicit_total + 1
        if explicit_total > 0:
            accuracy = "exact-for-explicit-breaks"
            rationale = (f"explicit breaks: br[type=page]={n_explicit} + "
                         f"pageBreakBefore={n_break_before} + "
                         f"section[type!=continuous]={n_sect_page} (+1)")
        else:
            # No markers at all — could be a single-page doc, or a long flowing
            # doc whose page breaks come from natural overflow.  Flag it.
            accuracy = "approximate (no break markers; may undercount long flowing docs)"
            rationale = "no break markers in XML; assuming 1 page"

    return {
        "page_count": page_count,
        "accuracy": accuracy,
        "rationale": rationale,
        "signals": {
            "last_rendered_page_break": n_last_rendered,
            "explicit_page_break": n_explicit,
            "page_break_before": n_break_before,
            "section_breaks_page": n_sect_page,
            "section_breaks_continuous": n_sect_continuous,
        },
    }


def cmd_page_count(args: argparse.Namespace) -> dict:
    abs_path = C.require_file(args.file, _DOCX_EXTS)

    method_used = None
    n_pages = None
    fallback_reason: str | None = None
    heuristic_detail: dict | None = None
    soffice_path: str | None = None

    # ---- Try soffice when allowed (auto + soffice modes)
    if args.method in ("auto", "soffice"):
        try:
            soffice_path = _resolve_soffice(args.soffice)
            n_pages = _page_count_via_soffice(abs_path, soffice_path, args.timeout)
            method_used = "soffice"
        except C.VerifierError as e:
            if args.method == "soffice":
                # Strict mode: re-raise so caller sees the original error.
                raise
            # Auto mode: remember why and fall through to the heuristic.
            fallback_reason = f"{e.code}: {e.msg[:200]}"

    # ---- Heuristic (forced or as fallback)
    if n_pages is None:
        heuristic_detail = _heuristic_page_count(abs_path)
        n_pages = heuristic_detail["page_count"]
        method_used = "heuristic"

    checks: list[dict] = []
    if args.min_pages is not None:
        checks.append({"check": "min_pages", "expected": args.min_pages,
                       "actual": n_pages, "passed": n_pages >= args.min_pages})
    if args.max_pages is not None:
        checks.append({"check": "max_pages", "expected": args.max_pages,
                       "actual": n_pages, "passed": n_pages <= args.max_pages})
    overall: bool | None = all(c["passed"] for c in checks) if checks else None

    quote_bits = [f"page_count={n_pages}", f"method={method_used}"]
    if heuristic_detail is not None:
        quote_bits.append(f"accuracy={heuristic_detail['accuracy']}")
    if fallback_reason is not None:
        quote_bits.append(f"soffice_fallback_reason={fallback_reason!r}")
    if checks:
        quote_bits.append("checks: " + ", ".join(
            f"{c['check']}={c['passed']}" for c in checks))

    out: dict = {
        "file": abs_path,
        "page_count": n_pages,
        "method": method_used,
        "checks": checks,
        "passed": overall,
        "_evidence": C.evidence(file=abs_path, quote="; ".join(quote_bits)),
    }
    if soffice_path is not None and method_used == "soffice":
        out["soffice"] = soffice_path
    if heuristic_detail is not None:
        out["heuristic"] = heuristic_detail
    if fallback_reason is not None:
        out["soffice_fallback_reason"] = fallback_reason
    return out


# ---------------------------------------------------------------------------
# count-images — walk underlying XML for w:drawing and w:pict.
#
# python-docx exposes ``InlineShape``s but misses floating drawings; counting
# the underlying XML elements is the most robust no-extra-dep approach.
# ---------------------------------------------------------------------------

_W_DRAWING_RE = re.compile(r"<w:drawing\b")
_W_PICT_RE = re.compile(r"<w:pict\b")


def cmd_count_images(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    body_xml = doc.element.body.xml
    n_drawing = len(_W_DRAWING_RE.findall(body_xml))
    n_pict = len(_W_PICT_RE.findall(body_xml))
    total = n_drawing + n_pict

    # Header / footer images count too (rubrics often include logos in headers).
    n_header = 0
    n_footer = 0
    try:
        for section in doc.sections:
            for hf, key in ((section.header, "header"), (section.footer, "footer")):
                try:
                    xml = hf._element.xml  # python-docx _Header/_Footer
                except Exception:
                    continue
                inc = len(_W_DRAWING_RE.findall(xml)) + len(_W_PICT_RE.findall(xml))
                if key == "header":
                    n_header += inc
                else:
                    n_footer += inc
    except Exception:
        pass
    total_with_hf = total + n_header + n_footer

    passed: bool | None = None
    if args.min is not None:
        passed = total_with_hf >= args.min

    return {
        "file": abs_path,
        "n_drawings": n_drawing,
        "n_pict": n_pict,
        "n_body_total": total,
        "n_header": n_header,
        "n_footer": n_footer,
        "n_total": total_with_hf,
        "passed": passed,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"images: body={total} (drawings={n_drawing}, pict={n_pict}), "
                                f"header={n_header}, footer={n_footer}, total={total_with_hf}"
                                + (f"; min={args.min}: {'OK' if passed else 'FAIL'}"
                                   if args.min is not None else "")),
    }


# ---------------------------------------------------------------------------
# page-setup — read sectPr for page size + orientation.
# ---------------------------------------------------------------------------

def _emu_to_inch(emu: int | float | None) -> float | None:
    if emu is None:
        return None
    try:
        return round(float(emu) / _EMU_PER_INCH, 3)
    except (TypeError, ValueError):
        return None


def cmd_page_setup(args: argparse.Namespace) -> dict:
    doc, abs_path = _open(args.file)
    sections: list[dict] = []
    for i, section in enumerate(doc.sections):
        # python-docx exposes width/height as Length (EMU); orientation as enum.
        try:
            w = int(section.page_width) if section.page_width is not None else None
        except Exception:
            w = None
        try:
            h = int(section.page_height) if section.page_height is not None else None
        except Exception:
            h = None
        # Derive orientation from dims (more robust than the enum across versions).
        if w is not None and h is not None:
            orientation = "landscape" if w > h else "portrait"
        else:
            try:
                orientation = section.orientation.name.lower() if section.orientation else None
            except Exception:
                orientation = None
        sections.append({
            "index": i,
            "page_width_emu": w,
            "page_height_emu": h,
            "page_width_in": _emu_to_inch(w),
            "page_height_in": _emu_to_inch(h),
            "orientation": orientation,
        })

    passed: bool | None = None
    if args.expect_orientation is not None:
        passed = bool(sections) and all(
            s["orientation"] == args.expect_orientation for s in sections
        )

    return {
        "file": abs_path,
        "section_count": len(sections),
        "sections": sections,
        "expect_orientation": args.expect_orientation,
        "passed": passed,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"{len(sections)} sections; orientations="
                                + ",".join((s["orientation"] or "?") for s in sections)
                                + (f"; expect={args.expect_orientation}: {'OK' if passed else 'FAIL'}"
                                   if args.expect_orientation is not None else "")),
    }
