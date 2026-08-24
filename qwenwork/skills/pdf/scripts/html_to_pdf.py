#!/usr/bin/env python3
"""
html_to_pdf.py — HTML to PDF (thin shim over markdown_to_pdf.py).

Why this is a shim
------------------
ReportLab does not render CSS. The previous DOM-walking implementation
re-invented paragraphs, tables, code blocks, and images from scratch,
every feature of which was already handled more faithfully by the
markdown-it pipeline. Worse, the duplication produced a reliable supply
of drift bugs (long code not splittable, table headers not bold,
hardcoded image dimensions, non-atomic writes).

Collapsing to a shim delivers three wins:
  1. Zero drift — every Markdown-side improvement is inherited for free
     (Pygments syntax highlighting, themes, image aspect ratio, atomic
     write, splittable ``XPreformatted`` for long code blocks).
  2. ~400 lines of duplicate DOM-walking logic deleted.
  3. HTML input now renders *better* than before because it picks up
     Pygments highlighting and the ``professional`` / ``minimal`` themes.

Pipeline
--------
    HTML (string or file)
        ↓  markdownify  (strips <script>/<style>, converts to GFM md)
    Markdown
        ↓  markdown_to_pdf.convert_markdown_to_pdf
    PDF

Limitations (identical to the prior DOM renderer)
  * CSS is ignored — use ``markdown_to_pdf.py --theme`` for styling.
  * Table ``colspan`` / ``rowspan`` is flattened.
  * ``<details>`` / ``<summary>`` degrade to plain text.

Usage
-----
    python scripts/html_to_pdf.py page.html --output result.pdf
    python scripts/html_to_pdf.py --file page.html --output result.pdf
    python scripts/html_to_pdf.py --html '<h1>Hi</h1>' --output result.pdf
"""

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Reuse the markdown pipeline wholesale. Importing this module also gives
# us MissingDependency and the CJK font plumbing through _fonts.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from markdown_to_pdf import (  # noqa: E402
    MissingDependency,
    convert_markdown_to_pdf,
)


PAGE_SIZE_KEYS = ("a4", "a3", "letter", "legal")
THEME_KEYS = ("default", "professional", "minimal")


def _import_deps() -> None:
    try:
        import markdownify  # noqa: F401
        from bs4 import BeautifulSoup  # noqa: F401
    except ImportError as e:
        raise MissingDependency(
            "markdownify/beautifulsoup4 not installed — they ship with the "
            "Wukong embedded Python, so this usually means the script is "
            "running under an unrelated interpreter"
        ) from e


def _strip_non_body_tags(html_source: str) -> str:
    """Remove <style>, <script>, <head>, <meta>, <link> before markdownify.

    markdownify's ``strip`` parameter removes the *tag markup* but keeps
    the inner text — so ``<style>body { color:red }</style>`` becomes the
    literal string ``body { color:red }`` in the Markdown output.  By
    decomposing these elements with BeautifulSoup first, their content is
    gone before markdownify ever sees it.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_source, "html.parser")
    for tag in soup.find_all(["style", "script", "head", "meta", "link"]):
        tag.decompose()
    return str(soup)


def convert_html_to_pdf(
    html_source: str,
    output_path: Path,
    page_size_key: str = "a4",
    margin: str = "15mm",
    base_dir: Optional[Path] = None,
    theme: str = "default",
) -> None:
    """Render *html_source* to *output_path* by delegating to markdown_to_pdf.

    *base_dir*, when provided, is where relative image paths in the HTML
    resolve. We write the intermediate Markdown next to *base_dir* so the
    downstream pipeline sees the same directory layout and can find
    ``<img src="foo.png">`` via ``base_dir/foo.png``.
    """
    _import_deps()

    from markdownify import markdownify as _md

    # `markdownify` kwargs:
    #   heading_style="ATX"  → use ``#`` style headings (markdown-it friendly)
    #   bullets="-"          → stable bullet char, avoids mixing -/*/+
    #   strip=[…]            → drop <script>/<style> entirely (they'd leak
    #                          raw CSS/JS as plain text otherwise)
    #   code_language=""     → fenced code blocks without a forced language;
    #                          markdown_to_pdf's Pygments will guess-lex
    # Pre-strip non-body elements with BeautifulSoup.  markdownify's
    # ``strip`` only removes the *tag markup* — inner text survives, so
    # ``<style>body{color:red}</style>`` leaks CSS as plaintext.
    cleaned = _strip_non_body_tags(html_source)

    md_text = _md(
        cleaned,
        heading_style="ATX",
        bullets="-",
        code_language="",
        strip=["script", "style"],
    )

    # Write the intermediate markdown next to where the HTML lived so
    # relative image paths resolve correctly. For inline --html input we
    # fall back to the output directory.
    target_dir = base_dir or output_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=output_path.stem + ".",
        suffix=".shim.md",
        dir=str(target_dir),
    )
    import os as _os
    _os.close(fd)
    tmp_md = Path(tmp_name)
    tmp_md.write_text(md_text, encoding="utf-8")

    try:
        convert_markdown_to_pdf(
            md_path=tmp_md,
            output_path=output_path,
            theme=theme,
            page_size=page_size_key,
            margin=margin,
        )
    finally:
        try:
            tmp_md.unlink()
        except OSError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert HTML to PDF via markdownify + markdown_to_pdf.py "
            "(pure Python, no browser)."
        ),
        epilog=(
            "Examples:\n"
            "  python scripts/html_to_pdf.py page.html --output result.pdf\n"
            "  python scripts/html_to_pdf.py --file page.html --output result.pdf \\\n"
            "      --page-size a4 --margin 20mm --theme professional\n"
            "  python scripts/html_to_pdf.py --html '<h1>Hello</h1>' --output result.pdf\n"
            "\n"
            "CSS is NOT rendered. For real styling, write Markdown and use\n"
            "markdown_to_pdf.py --theme professional / minimal instead.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Accept HTML file as positional, --file, or inline --html. Mirrors
    # markdown_to_pdf.py's CLI so agents can use a single mental model.
    parser.add_argument(
        "html_file", nargs="?", help="Input HTML file (positional form)"
    )
    parser.add_argument(
        "--file",
        dest="html_file_flag",
        metavar="FILE",
        help="HTML file path (flag form, alias of positional)",
    )
    parser.add_argument("--html", help="HTML string (inline)")
    parser.add_argument("--output", "-o", required=True, help="Output PDF path")
    parser.add_argument(
        "--page-size",
        default="a4",
        choices=list(PAGE_SIZE_KEYS),
        help="Page size (default: a4)",
    )
    parser.add_argument(
        "--margin", default="15mm", help="Page margin (default: 15mm)"
    )
    parser.add_argument(
        "--theme",
        default="default",
        choices=list(THEME_KEYS),
        help="Visual theme, forwarded to markdown_to_pdf (default: default)",
    )
    # Legacy flags from the DOM-walker era — kept as no-ops so existing
    # callers don't break. They print a one-line note on stderr when used.
    parser.add_argument(
        "--header", default="", help="(reserved) no-op — legacy flag"
    )
    parser.add_argument(
        "--footer", default="", help="(reserved) no-op — legacy flag"
    )
    parser.add_argument("--css", help="(reserved) no-op — legacy flag")
    parser.add_argument(
        "--toc", action="store_true", help="(reserved) no-op — legacy flag"
    )

    args = parser.parse_args()

    # Resolve the HTML source with clear errors — positional / --file /
    # --html are mutually exclusive.
    file_arg = args.html_file or args.html_file_flag
    if (
        args.html_file
        and args.html_file_flag
        and args.html_file != args.html_file_flag
    ):
        parser.error(
            "conflicting inputs: positional and --file point to different files"
        )
    if file_arg and args.html:
        parser.error(
            "use either an HTML file (positional / --file) or --html, not both"
        )
    if not file_arg and not args.html:
        parser.error(
            "input HTML is required — pass a file as a positional argument "
            "(e.g. `html_to_pdf.py page.html --output x.pdf`), via "
            "`--file page.html`, or supply an inline string with "
            "`--html '<h1>...</h1>'`"
        )

    if args.header or args.footer or args.css or args.toc:
        print(
            "[html_to_pdf] note: --header/--footer/--css/--toc are no-ops in "
            "the shim backend; use markdown_to_pdf.py --theme for styling.",
            file=sys.stderr,
        )

    base_dir: Optional[Path] = None
    if file_arg:
        file_path = Path(file_arg)
        if not file_path.exists():
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        html_source = file_path.read_text(encoding="utf-8")
        base_dir = file_path.parent
    else:
        html_source = args.html

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(
        f"Rendering HTML → PDF via markdown shim "
        f"({args.page_size.upper()}, margin {args.margin}, theme {args.theme})…"
    )
    try:
        convert_html_to_pdf(
            html_source=html_source,
            output_path=output_path,
            page_size_key=args.page_size,
            margin=args.margin,
            base_dir=base_dir,
            theme=args.theme,
        )
    except MissingDependency as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"PDF created → {output_path}")


if __name__ == "__main__":
    main()
