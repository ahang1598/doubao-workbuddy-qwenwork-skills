#!/usr/bin/env python3
"""Render finalized display Markdown as a standalone, dependency-free HTML report.

The source must already have passed finalize_report.py so fact bindings have
become numbered references. This helper never reads the raw audit source.
Keep the default CSS aligned with references/html-style.md, which is read
after the analysis draft is complete and before HTML generation.
"""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse


HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
RULE = re.compile(r"^\s*(?:---+|\*\*\*+)\s*$")
LIST = re.compile(r"^(\s*)([-*+] |\d+\. )(.*)$")
SOURCE = re.compile(r"^\s*(\d+)\.\s+")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
CITATION = re.compile(r"(?<![!\w])\[(\d+)\]")


def safe_url(url: str, source_dir: Path, image: bool = False) -> str:
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https", "mailto") or url.startswith("#"):
        return html.escape(url, quote=True)
    if image and not parsed.scheme and not url.startswith("/"):
        path = (source_dir / url).resolve()
        if path.is_file() and path.stat().st_size <= 2_000_000:
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if mime in ("image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"):
                payload = base64.b64encode(path.read_bytes()).decode("ascii")
                return f"data:{mime};base64,{payload}"
    return ""


def inline(text: str, source_dir: Path) -> str:
    tokens: list[str] = []

    def stash(fragment: str) -> str:
        tokens.append(fragment)
        return f"\ue000{len(tokens) - 1}\ue001"

    def image(match: re.Match[str]) -> str:
        url = safe_url(match.group(2), source_dir, image=True)
        if not url:
            return stash(html.escape(match.group(1)))
        return stash(f'<img src="{url}" alt="{html.escape(match.group(1), quote=True)}" loading="lazy">')

    text = IMAGE.sub(image, text)

    def link(match: re.Match[str]) -> str:
        url = safe_url(match.group(2), source_dir)
        label = html.escape(match.group(1))
        if not url:
            return stash(label)
        external = ' target="_blank" rel="noopener noreferrer"' if url.startswith("http") else ""
        return stash(f'<a href="{url}"{external}>{label}</a>')

    text = LINK.sub(link, text)
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", lambda m: stash(f"<code>{m.group(1)}</code>"), text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = CITATION.sub(lambda m: stash(f'<a class="cite" href="#source-{m.group(1)}" aria-label="来源 {m.group(1)}">[{m.group(1)}]</a>'), text)
    return re.sub(r"\ue000(\d+)\ue001", lambda m: tokens[int(m.group(1))], text)


def slug(text: str, used: set[str]) -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text).strip("-").lower() or "section"
    candidate = base
    number = 2
    while candidate in used:
        candidate = f"{base}-{number}"
        number += 1
    used.add(candidate)
    return candidate


def is_table_separator(line: str) -> bool:
    cells = [part.strip() for part in line.strip().strip("|").split("|")]
    return len(cells) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def table_cells(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def render_table(lines: list[str], source_dir: Path) -> str:
    headers = table_cells(lines[0])
    rows = [table_cells(line) for line in lines[2:]]
    head = "".join(f"<th scope=\"col\">{inline(cell, source_dir)}</th>" for cell in headers)
    body = "".join("<tr>" + "".join(f"<td>{inline(cell, source_dir)}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render(markdown: str, source_dir: Path) -> str:
    lines = markdown.splitlines()
    title = next((m.group(2) for line in lines if (m := HEADING.match(line)) and len(m.group(1)) == 1), "财报分析")
    heading_data: list[tuple[int, str, str]] = []
    used: set[str] = set()
    for line in lines:
        match = HEADING.match(line)
        if match and len(match.group(1)) >= 2:
            heading_data.append((len(match.group(1)), match.group(2), slug(match.group(2), used)))
    main_headings = [(name, ident) for level, name, ident in heading_data if level == 2]
    nav = "".join(f'<a href="#{ident}">{html.escape(name)}</a>' for name, ident in main_headings) if len(main_headings) >= 4 else ""
    output: list[str] = []
    section_name = ""
    heading_index = 0
    section_open = False
    list_type = ""
    in_code = False
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f'<p>{inline(" ".join(paragraph), source_dir)}</p>')
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = ""

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush_paragraph(); close_list()
            if in_code:
                output.append("</code></pre>")
            else:
                output.append("<pre><code>")
            in_code = not in_code
            i += 1
            continue
        if in_code:
            output.append(html.escape(line) + "\n")
            i += 1
            continue
        match = HEADING.match(line)
        if match:
            flush_paragraph(); close_list()
            level, name = len(match.group(1)), match.group(2)
            if level == 1:
                i += 1
                continue
            if level == 2:
                if section_open:
                    output.append("</section>")
                section_name = name
                css = " overview" if "概览" in name or name.startswith("结论") else ""
                if "数据来源" in name:
                    css = " sources"
                ident = heading_data[heading_index][2]
                output.append(f'<section class="report-section{css}" id="{ident}"><h2>{inline(name, source_dir)}</h2>')
                section_open = True
            else:
                ident = heading_data[heading_index][2]
                output.append(f'<h{level} id="{ident}">{inline(name, source_dir)}</h{level}>')
            heading_index += 1
            i += 1
            continue
        if not stripped:
            flush_paragraph(); close_list()
            i += 1
            continue
        if RULE.match(line):
            flush_paragraph(); close_list(); output.append("<hr>")
            i += 1
            continue
        if i + 1 < len(lines) and "|" in line and is_table_separator(lines[i + 1]):
            flush_paragraph(); close_list()
            table_lines = [line, lines[i + 1]]
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                table_lines.append(lines[i]); i += 1
            output.append(render_table(table_lines, source_dir))
            continue
        item = LIST.match(line)
        if item:
            flush_paragraph()
            kind = "ol" if item.group(2)[0].isdigit() else "ul"
            if kind != list_type:
                close_list(); output.append(f"<{kind}>"); list_type = kind
            content = item.group(3)
            source_match = SOURCE.match(line) if section_name == "数据来源" else None
            source_id = f' id="source-{source_match.group(1)}"' if source_match else ""
            output.append(f"<li{source_id}>{inline(content, source_dir)}</li>")
            i += 1
            continue
        if stripped.startswith(">"):
            flush_paragraph(); close_list()
            output.append(f'<blockquote>{inline(stripped.lstrip("> "), source_dir)}</blockquote>')
            i += 1
            continue
        close_list()
        paragraph.append(stripped)
        i += 1
    flush_paragraph(); close_list()
    if section_open:
        output.append("</section>")
    content = "\n".join(output)
    navigation = f'<nav aria-label="报告章节"><div class="wrap">{nav}</div></nav>' if nav else ""
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>{html.escape(title)}</title>
<style>
:root{{--ink:#191919;--muted:#747474;--line:#e5e6e8;--soft:#f5f5f5;--accent:#3c7d67;--blue:#4678bd;--orange:#cf7744;--red:#bd6262}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:#fff;color:var(--ink);font:15px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1340px;margin:auto;padding:0 24px}}header{{padding:30px 0 16px}}h1{{font-size:25px;line-height:1.35;margin:0 0 6px;font-weight:720;letter-spacing:-.02em}}.subtitle{{font-size:13px;color:var(--muted)}}
nav{{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);overflow:auto;white-space:nowrap}}nav .wrap{{display:flex;gap:3px}}nav a{{display:inline-block;padding:13px 16px;color:#676767;text-decoration:none;font-size:13px;border-bottom:2px solid transparent}}nav a:hover,nav a:focus{{color:var(--ink);border-color:var(--ink)}}
main{{padding:22px 0 70px}}.report-section{{border:1px solid var(--line);border-radius:15px;padding:22px 22px 24px;margin:0 0 18px;scroll-margin-top:65px}}.report-section.overview{{background:#f3f3f3;border-color:#ddd}}.report-section.sources{{background:#fafafa}}
h2{{font-size:20px;line-height:1.45;margin:0 0 15px;letter-spacing:-.01em}}h3{{font-size:16px;line-height:1.45;margin:24px 0 9px}}p{{margin:10px 0}}ul,ol{{padding-left:23px;margin:10px 0}}li{{padding:2px 0}}li::marker{{color:#555}}strong{{font-weight:700}}a{{color:#427968;text-underline-offset:3px}}a:hover{{color:#275a4a}}.cite{{font-size:11px;text-decoration:none;vertical-align:super;margin-left:2px;color:#4d826f}}
.table-scroll{{overflow:auto;margin:14px 0 18px;border:1px solid var(--line);border-radius:10px}}table{{width:100%;border-collapse:collapse;font-size:13px;min-width:560px}}th{{text-align:left;background:#f4f5f5;color:#444;font-weight:650}}th,td{{padding:10px 12px;border-bottom:1px solid #ececec;vertical-align:top}}tbody tr:last-child td{{border-bottom:0}}tbody tr:hover{{background:#fafafa}}blockquote{{margin:14px 0;padding:7px 15px;border-left:3px solid #93ac9f;background:#f6f8f7;color:#4b4b4b}}hr{{height:1px;border:0;background:var(--line);margin:24px 0}}pre{{overflow:auto;background:#f5f5f5;padding:14px;border-radius:9px}}code{{font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace}}p img{{max-width:100%;height:auto;display:block;margin:15px auto}}.report-section.sources li{{overflow-wrap:anywhere}}
@media(max-width:760px){{.wrap{{padding:0 15px}}header{{padding-top:20px}}h1{{font-size:21px}}nav a{{padding:11px 12px}}main{{padding-top:15px}}.report-section{{padding:17px;margin-bottom:13px}}}}
@media print{{nav{{display:none}}.wrap{{max-width:none}}.report-section{{break-inside:avoid;border-color:#ccc}}a{{color:inherit}}}}
</style></head><body>
<header><div class="wrap"><h1>{html.escape(title)}</h1><div class="subtitle">上市公司财报分析 · 数据与判断均附来源</div></div></header>
{navigation}
<main class="wrap">{content}</main>
</body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal HTML renderer; use finalize_report.py for delivery")
    parser.add_argument("input", help="Finalized display Markdown")
    parser.add_argument("output", help="Standalone HTML output")
    args = parser.parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(input_path.read_text(encoding="utf-8"), input_path.parent), encoding="utf-8")
    print(f"HTML report saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
