"""argparse-based CLI for the artifact-preview skill.

Subcommands:
    render <file>      → render, then emit a JSON summary
    info <hash|dir|file> → dump the manifest
    list               → list cached previews
    clean [<hash>]     → remove a cached preview (or --all)

Every subcommand emits exactly one JSON object on **stdout**, in the same
envelope verifier-hub uses:

    {"ok": true,  "tool": "<sub>", "result": {...}}
    {"ok": false, "tool": "<sub>", "error": {"code": "...", "msg": "..."}}

That includes argument errors (code ``BAD_ARGS``). ``--help`` is the one
invocation that prints prose instead.

The CLI is invoked by the model via the hub's ``bin/preview`` entry point,
which sets up ``sys.path`` before importing this module.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import shutil
from pathlib import Path
from typing import Any

from . import _common as C
from ._types import Manifest, RenderOptions
from .cache import default_output_root
from .dispatch import detect_kind, render
from .manifest import load_manifest


def _build_parser() -> argparse.ArgumentParser:
    p = C.JsonArgumentParser(
        prog="preview",
        description=(
            "Render workspace artifacts to text + screenshots that the model "
            "can consume via Read. Run `preview render <file>` to render; "
            "the JSON output points at the manifest, text dump, thumbnail, "
            "and collage(s)."
        ),
    )
    p.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    sub = p.add_subparsers(dest="cmd", required=True,
                           parser_class=C.JsonArgumentParser)

    r = sub.add_parser("render", help="render an artifact to text + images")
    r.add_argument("path", help="file path inside the workspace")
    r.add_argument("--output-root", help="override .preview/ root (env: ARTIFACT_PREVIEW_HOME)")
    r.add_argument("--max-pages", type=int, default=12)
    r.add_argument("--page-range", help='1-indexed selector, e.g. "1-5,10"')
    r.add_argument("--no-collage", action="store_true")
    r.add_argument("--no-thumbnail", action="store_true")
    r.add_argument("--text-only", action="store_true",
                   help="skip image rendering; keeps images an earlier full "
                        "render already produced")
    r.add_argument("--force", action="store_true", help="ignore cache; re-render")
    r.add_argument("--jpeg-quality", type=int, default=85)
    r.add_argument("--out-max-dim", type=int, default=2048)
    r.add_argument("--soffice", help="path to the LibreOffice binary, used for "
                                    "pptx screenshots when it is not on PATH")
    r.add_argument("--chromium", help="path to a Chromium-family browser, used "
                                     "for html screenshots when it is not on PATH")

    i = sub.add_parser("info", help="dump the manifest for a previously rendered file")
    i.add_argument("target", help="cache hash, output dir, or original file path")
    i.add_argument("--output-root")

    ls = sub.add_parser("list", help="list cached previews")
    ls.add_argument("--output-root")

    c = sub.add_parser("clean", help="remove a cached preview")
    c.add_argument("hash", nargs="?", help="cache hash; omit with --all to clean everything")
    c.add_argument("--all", action="store_true")
    c.add_argument("--output-root")

    return p


def _resolve_target(target: str, root: Path) -> Path | None:
    """Map a CLI ``info`` target into an output dir."""
    cand = Path(target)
    if cand.is_dir() and (cand / "manifest.json").exists():
        return cand
    cand2 = root / target
    if cand2.is_dir() and (cand2 / "manifest.json").exists():
        return cand2
    if cand.is_file():
        from .cache import compute_source_hash

        h = compute_source_hash(cand)
        cand3 = root / h
        if (cand3 / "manifest.json").exists():
            return cand3
    return None


def _render_payload(manifest: Manifest) -> dict[str, Any]:
    out_dir = Path(manifest.output_dir)
    return {
        "output_dir": manifest.output_dir,
        "manifest": str(out_dir / "manifest.json"),
        "kind": manifest.kind,
        "page_count": manifest.page_count,
        "rendered_page_count": manifest.rendered_page_count,
        "collage_count": manifest.collage_count,
        "extracted_text_chars": manifest.extracted_text_chars,
        "text": (str(out_dir / manifest.text_relpath)
                 if manifest.text_relpath else None),
        "thumbnail": (str(out_dir / manifest.thumbnail_relpath)
                      if manifest.thumbnail_relpath else None),
        "collages": [str(out_dir / c.relpath) for c in manifest.collages],
        "pages": [str(out_dir / p.relpath) for p in manifest.pages],
        "warnings": manifest.warnings,
    }


def _cmd_render(args: argparse.Namespace) -> int:
    opts = RenderOptions(
        max_pages=args.max_pages,
        collage=not args.no_collage,
        page_range=args.page_range,
        thumbnail=not args.no_thumbnail,
        text_only=args.text_only,
        force=args.force,
        jpeg_quality=args.jpeg_quality,
        out_max_dim=args.out_max_dim,
        soffice=args.soffice,
        chromium=args.chromium,
    )
    src = Path(C.logical_abspath(args.path))
    if not src.exists():
        return C.emit(C.err("render", C.ErrCode.FILE_NOT_FOUND,
                            f"file not found: {src}"))
    if not src.is_file():
        return C.emit(C.err("render", C.ErrCode.NOT_A_FILE,
                            f"not a regular file: {src}"))
    kind = detect_kind(src)
    if kind == "unknown":
        return C.emit(C.err(
            "render", C.ErrCode.BAD_EXT,
            f"unsupported extension {src.suffix!r}; supported: pdf, pptx, docx, "
            f"xlsx, html, png/jpg/jpeg/webp/gif/bmp, txt/md/json/yaml/csv, zip"))

    manifest = render(src, args.output_root, opts)
    return C.emit(C.ok("render", _render_payload(manifest)))


def _manifest_payload(m: Manifest) -> dict[str, Any]:
    """Serialize the Manifest dataclass for the ``info`` subcommand."""
    return {
        "schema_version": m.schema_version,
        "source_path": m.source_path,
        "source_filename": m.source_filename,
        "source_hash": m.source_hash,
        "source_size_bytes": m.source_size_bytes,
        "kind": m.kind,
        "rendered_at_utc": m.rendered_at_utc,
        "output_dir": m.output_dir,
        "page_count": m.page_count,
        "rendered_page_count": m.rendered_page_count,
        "collage_count": m.collage_count,
        "extracted_text_chars": m.extracted_text_chars,
        "text_relpath": m.text_relpath,
        "thumbnail_relpath": m.thumbnail_relpath,
        "pages": [dataclasses.asdict(p) for p in m.pages],
        "collages": [dataclasses.asdict(c) for c in m.collages],
        "warnings": list(m.warnings),
        "options": dict(m.options),
        "summary": dict(m.summary),
    }


def _cmd_info(args: argparse.Namespace) -> int:
    root = _root_from(args)
    out_dir = _resolve_target(args.target, root)
    if out_dir is None:
        return C.emit(C.err("info", C.ErrCode.NOT_FOUND,
                            f"no cached preview for: {args.target}"))
    m = load_manifest(out_dir)
    return C.emit(C.ok("info", _manifest_payload(m)))


def _root_from(args: argparse.Namespace) -> Path:
    explicit = getattr(args, "output_root", None)
    return Path(C.logical_abspath(explicit)) if explicit else default_output_root()


def _cmd_list(args: argparse.Namespace) -> int:
    root = _root_from(args)
    entries: list[dict[str, Any]] = []
    if root.exists():
        for child in sorted(root.iterdir()):
            if not child.is_dir() or not (child / "manifest.json").exists():
                continue
            try:
                m = load_manifest(child)
                entries.append({
                    "hash": child.name,
                    "source_filename": m.source_filename,
                    "kind": m.kind,
                    "rendered_at_utc": m.rendered_at_utc,
                    "page_count": m.page_count,
                    "rendered_page_count": m.rendered_page_count,
                    "collage_count": m.collage_count,
                })
            except Exception as exc:  # noqa: BLE001 - one bad entry must not hide the rest
                entries.append({"hash": child.name, "error": str(exc)})
    return C.emit(C.ok("list", {"root": str(root), "count": len(entries),
                                "entries": entries}))


def _cmd_clean(args: argparse.Namespace) -> int:
    root = _root_from(args)
    if args.all:
        removed = str(root)
        if root.exists():
            shutil.rmtree(root)
        return C.emit(C.ok("clean", {"removed": removed, "scope": "all"}))
    if not args.hash:
        return C.emit(C.err("clean", C.ErrCode.BAD_ARGS,
                            "specify a cache <hash> or pass --all"))
    target = root / args.hash
    if not target.exists():
        return C.emit(C.err("clean", C.ErrCode.NOT_FOUND,
                            f"no such cache entry: {args.hash}"))
    shutil.rmtree(target)
    return C.emit(C.ok("clean", {"removed": str(target), "scope": "one"}))


_HANDLERS = {
    "render": _cmd_render,
    "info": _cmd_info,
    "list": _cmd_list,
    "clean": _cmd_clean,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except C.ArtifactPreviewError as exc:
        return C.emit(C.err("preview", exc.code, exc.msg))

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )
    handler = _HANDLERS.get(args.cmd)
    if handler is None:  # argparse's required=True makes this unreachable
        return C.emit(C.err("preview", C.ErrCode.BAD_ARGS,
                            f"unknown subcommand: {args.cmd!r}"))
    try:
        return handler(args)
    except C.ArtifactPreviewError as exc:
        return C.emit(C.err(args.cmd, exc.code, exc.msg))
    except Exception as exc:  # noqa: BLE001 - never leak a traceback to stdout
        return C.emit(C.err(args.cmd, C.ErrCode.INTERNAL,
                            f"{type(exc).__name__}: {exc}"))
