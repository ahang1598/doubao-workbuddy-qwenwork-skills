"""file — generic file inspection (kind agnostic).

Subcommands
-----------
artifact-list   Recursively list files under a directory; classify by kind.
validate        Confirm a file exists, has expected extension, and opens with the
                appropriate library (xlsx/docx/pdf/pptx).
extract-text    Extract plain text from any supported file (xlsx/docx/pdf/pptx/text).
count           Count files / total size under a directory (optionally filtered by ext).
"""
from __future__ import annotations

import argparse
import os
from typing import Any

from . import _common as C


# ---------------------------------------------------------------------------
# Subcommand registry
# ---------------------------------------------------------------------------

def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("artifact-list",
                       help="Recursively list files; classify by kind.")
    p.add_argument("directory")
    p.add_argument("--max-files", type=int, default=200,
                   help="cap on returned files (default 200)")
    p.add_argument("--include-hidden", action="store_true")

    p = sub.add_parser("validate",
                       help="Confirm a file is well-formed (opens with proper lib).")
    p.add_argument("file")
    p.add_argument("--expected-ext", default=None,
                   help="comma-separated allowed extensions (with dot); e.g. .xlsx,.xls")

    p = sub.add_parser("extract-text",
                       help="Extract plain text from a file (any supported kind).")
    p.add_argument("file")
    p.add_argument("--max-chars", type=int, default=20000,
                   help="cap on returned text (default 20000)")

    p = sub.add_parser("count",
                       help="Count files / total bytes under a directory.")
    p.add_argument("directory")
    p.add_argument("--ext", default=None,
                   help="comma-separated extensions to filter (e.g. .xlsx,.csv)")


# ---------------------------------------------------------------------------
# artifact-list
# ---------------------------------------------------------------------------

def cmd_artifact_list(args: argparse.Namespace) -> dict:
    abs_dir = C.resolve_path(args.directory)
    if not os.path.exists(abs_dir):
        raise C.VerifierError(C.ErrCode.FILE_NOT_FOUND, f"directory not found: {abs_dir}")
    if not os.path.isdir(abs_dir):
        raise C.VerifierError(C.ErrCode.NOT_A_FILE, f"not a directory: {abs_dir}")

    files: list[dict] = []
    truncated = False
    for root, dirs, names in os.walk(abs_dir):
        if not args.include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            names = [n for n in names if not n.startswith(".")]
        for name in sorted(names):
            full = os.path.join(root, name)
            files.append({
                "path": full,
                "rel": os.path.relpath(full, abs_dir),
                "size": C.file_size(full),
                "kind": C.detect_kind(full),
            })
            if len(files) >= args.max_files:
                truncated = True
                break
        if truncated:
            break

    # Build a one-line evidence string the agent can paste into rationale.
    summary_kinds: dict[str, int] = {}
    for f in files:
        summary_kinds[f["kind"]] = summary_kinds.get(f["kind"], 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(summary_kinds.items())) or "(empty)"

    return {
        "directory": abs_dir,
        "count": len(files),
        "truncated": truncated,
        "files": files,
        "_evidence": C.evidence(file=abs_dir, quote=f"{len(files)} files: {summary}"),
    }


# ---------------------------------------------------------------------------
# validate — open with the right library, surface parse errors.
# ---------------------------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> dict:
    expected_exts: tuple[str, ...] | None = None
    if args.expected_ext:
        expected_exts = tuple(
            (e if e.startswith(".") else "." + e).lower()
            for e in args.expected_ext.split(",") if e.strip()
        )
    path = C.require_file(args.file, expected_exts)
    kind = C.detect_kind(path)

    detail: dict[str, Any] = {"path": path, "kind": kind, "size": C.file_size(path)}
    try:
        if kind == "xlsx":
            openpyxl = C.lazy_import("openpyxl")
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            detail["sheets"] = list(wb.sheetnames)
            wb.close()
        elif kind == "docx":
            docx = C.lazy_import("docx")
            d = docx.Document(path)
            detail["paragraph_count"] = len(d.paragraphs)
            detail["table_count"] = len(d.tables)
        elif kind == "pdf":
            from . import _pdf_backend as B
            with B.open_pdf(path) as pdf:
                detail["page_count"] = pdf.page_count
                detail["backend"] = pdf.backend
        elif kind == "pptx":
            pptx = C.lazy_import("pptx")
            pres = pptx.Presentation(path)
            detail["slide_count"] = len(pres.slides)
        elif kind == "text":
            with open(path, encoding="utf-8", errors="replace") as f:
                detail["char_count"] = sum(len(line) for line in f)
        else:
            detail["note"] = f"kind={kind}: no validator available; file exists and is readable"
    except C.VerifierError:
        raise
    except Exception as e:
        raise C.VerifierError(C.ErrCode.PARSE_ERROR,
                              f"failed to open {path} as {kind}: {type(e).__name__}: {e}") from e

    quote_bits = [f"{kind}", f"size={detail['size']}"]
    for k in ("sheets", "page_count", "slide_count", "paragraph_count"):
        if k in detail:
            quote_bits.append(f"{k}={detail[k]}")
    detail["_evidence"] = C.evidence(file=path, quote=" ".join(quote_bits))
    return detail


# ---------------------------------------------------------------------------
# extract-text
# ---------------------------------------------------------------------------

def cmd_extract_text(args: argparse.Namespace) -> dict:
    path = C.require_file(args.file)
    kind = C.detect_kind(path)
    text = ""

    try:
        if kind == "xlsx":
            openpyxl = C.lazy_import("openpyxl")
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            parts: list[str] = []
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                parts.append(f"# sheet: {sheet}")
                for row in ws.iter_rows(values_only=True):
                    parts.append("\t".join("" if v is None else str(v) for v in row))
                if sum(len(p) for p in parts) > args.max_chars:
                    break
            wb.close()
            text = "\n".join(parts)
        elif kind == "docx":
            docx = C.lazy_import("docx")
            d = docx.Document(path)
            paras = [p.text for p in d.paragraphs if p.text]
            tables: list[str] = []
            for t in d.tables:
                for row in t.rows:
                    tables.append("\t".join(c.text for c in row.cells))
            text = "\n".join(paras + tables)
        elif kind == "pdf":
            from . import _pdf_backend as B
            parts = []
            with B.open_pdf(path) as pdf:
                for i in range(pdf.page_count):
                    parts.append(f"# page {i + 1}")
                    parts.append(pdf.page_text(i))
                    if sum(len(p) for p in parts) > args.max_chars:
                        break
            text = "\n".join(parts)
        elif kind == "pptx":
            pptx = C.lazy_import("pptx")
            pres = pptx.Presentation(path)
            parts = []
            for i, slide in enumerate(pres.slides):
                parts.append(f"# slide {i + 1}")
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for para in shape.text_frame.paragraphs:
                            t = "".join(r.text for r in para.runs)
                            if t:
                                parts.append(t)
                if sum(len(p) for p in parts) > args.max_chars:
                    break
            text = "\n".join(parts)
        elif kind == "text":
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read(args.max_chars + 1)
        else:
            raise C.VerifierError(C.ErrCode.BAD_EXT,
                                  f"extract-text: kind={kind!r} is not supported")
    except C.VerifierError:
        raise
    except Exception as e:
        raise C.VerifierError(C.ErrCode.PARSE_ERROR,
                              f"extract-text failed for {path}: {type(e).__name__}: {e}") from e

    truncated = len(text) > args.max_chars
    if truncated:
        text = text[: args.max_chars]
    return {
        "path": path,
        "kind": kind,
        "char_count": len(text),
        "truncated": truncated,
        "text": text,
        "_evidence": C.evidence(file=path, quote=f"{kind} extracted {len(text)} chars" + (" (truncated)" if truncated else "")),
    }


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------

def cmd_count(args: argparse.Namespace) -> dict:
    abs_dir = C.resolve_path(args.directory)
    if not os.path.isdir(abs_dir):
        raise C.VerifierError(C.ErrCode.NOT_A_FILE, f"not a directory: {abs_dir}")

    exts: set[str] | None = None
    if args.ext:
        exts = {
            (e if e.startswith(".") else "." + e).lower()
            for e in args.ext.split(",") if e.strip()
        }

    n = 0
    total = 0
    for root, _, names in os.walk(abs_dir):
        for name in names:
            if exts is not None and os.path.splitext(name)[1].lower() not in exts:
                continue
            n += 1
            total += C.file_size(os.path.join(root, name))

    return {
        "directory": abs_dir,
        "ext_filter": sorted(exts) if exts else None,
        "count": n,
        "total_bytes": total,
        "_evidence": C.evidence(file=abs_dir,
                                quote=f"{n} files, {total} bytes"
                                + (f" (ext in {sorted(exts)})" if exts else "")),
    }
