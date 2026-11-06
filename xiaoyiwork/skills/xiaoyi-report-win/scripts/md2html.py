#!/usr/bin/env python3
"""Markdown 转 HTML 转换脚本（Python 版）。

用法：
  python md2html.py <input.md> [output.html]
  python md2html.py report.md --theme dark --title "研究报告"
  python md2html.py report.md --reports-root /tmp/reports
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_REPORTS_ROOT = (Path.home() / ".openclaw" / "workspace" / "reports").resolve()

THEMES = {
    "light": {
        "body_bg": "#ffffff",
        "text": "#1a1a1a",
        "heading": "#1a1a1a",
        "link": "#2563eb",
        "link_hover": "#1d4ed8",
        "code": "#f3f4f6",
        "code_text": "#1f2937",
        "blockquote": "#f9fafb",
        "blockquote_border": "#d1d5db",
        "muted": "#666666",
        "table_header": "#f9fafb",
        "table_border": "#e5e7eb",
        "table_stripe": "#fafafa",
        "table_hover": "#f0f4ff",
        "hr": "#e5e7eb",
        "shadow": "rgba(0, 0, 0, 0.1)",
        "scroll_hint": "rgba(0, 0, 0, 0.08)",
        "footer": "#888888",
    },
    "dark": {
        "body_bg": "#1a1a1a",
        "text": "#e5e5e5",
        "heading": "#ffffff",
        "link": "#60a5fa",
        "link_hover": "#93c5fd",
        "code": "#2d2d2d",
        "code_text": "#e5e5e5",
        "blockquote": "#2d2d2d",
        "blockquote_border": "#4a4a4a",
        "muted": "#b3b3b3",
        "table_header": "#2d2d2d",
        "table_border": "#4a4a4a",
        "table_stripe": "#222222",
        "table_hover": "#2d2d3d",
        "hr": "#4a4a4a",
        "shadow": "rgba(0, 0, 0, 0.3)",
        "scroll_hint": "rgba(255, 255, 255, 0.06)",
        "footer": "#9ca3af",
    },
}

CODE_SPAN_RE = re.compile(r"`([^`]+)`")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD_ITALIC_RE = [
    (re.compile(r"\*\*\*(.+?)\*\*\*"), r"<strong><em>\1</em></strong>"),
    (re.compile(r"___(.+?)___"), r"<strong><em>\1</em></strong>"),
]
BOLD_RE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"__(.+?)__"), r"<strong>\1</strong>"),
]
ITALIC_RE = [
    (re.compile(r"\*(.+?)\*"), r"<em>\1</em>"),
    (re.compile(r"_(.+?)_"), r"<em>\1</em>"),
]


def fail(message: str) -> None:
    print(f"错误：{message}", file=sys.stderr)
    raise ValueError(message)


def is_within_directory(candidate_path: Path, allowed_root: Path) -> bool:
    try:
        candidate_path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def safe_url(url: str) -> str:
    trimmed = url.strip()
    parsed = urlparse(trimmed)
    if not parsed.scheme:
        return html.escape(trimmed, quote=True)
    if parsed.scheme.lower() in {"http", "https", "mailto"}:
        return html.escape(trimmed, quote=True)
    return "#"


def resolve_allowed_input_path(input_file: str, reports_root: Path) -> Path:
    absolute_input_path = Path(input_file).expanduser().resolve()

    if absolute_input_path.suffix.lower() != ".md":
        fail("只允许读取 .md 文件")

    if not absolute_input_path.exists():
        fail(f"文件不存在: {input_file}")

    real_input_path = absolute_input_path.resolve(strict=True)
    if not is_within_directory(real_input_path, reports_root):
        fail(f"输入文件必须位于允许目录内: {reports_root}")

    return real_input_path


def resolve_allowed_output_path(output_file: str, reports_root: Path) -> Path:
    absolute_output_path = Path(output_file).expanduser().resolve()
    output_dir = absolute_output_path.parent

    if not output_dir.exists():
        fail(f"输出目录不存在: {output_dir}")

    real_output_dir = output_dir.resolve(strict=True)
    if not is_within_directory(real_output_dir, reports_root):
        fail(f"输出文件必须位于允许目录内: {reports_root}")

    return real_output_dir / absolute_output_path.name


def inline_format(text: str) -> str:
    escaped = html.escape(text, quote=False)

    placeholders: list[str] = []

    def reserve(fragment: str) -> str:
        placeholders.append(fragment)
        return f"\x00{len(placeholders) - 1}\x00"

    def replace_image(match: re.Match[str]) -> str:
        alt = html.escape(match.group(1), quote=True)
        src = safe_url(match.group(2))
        return reserve(f'<img src="{src}" alt="{alt}">')

    def replace_link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = safe_url(match.group(2))
        return reserve(f'<a href="{href}" target="_blank" rel="noopener noreferrer">{label}</a>')

    def replace_code(match: re.Match[str]) -> str:
        code_text = match.group(1)
        return reserve(f"<code>{code_text}</code>")

    escaped = IMAGE_RE.sub(replace_image, escaped)
    escaped = LINK_RE.sub(replace_link, escaped)
    escaped = CODE_SPAN_RE.sub(replace_code, escaped)

    for pattern, replacement in BOLD_ITALIC_RE:
        escaped = pattern.sub(replacement, escaped)
    for pattern, replacement in BOLD_RE:
        escaped = pattern.sub(replacement, escaped)
    for pattern, replacement in ITALIC_RE:
        escaped = pattern.sub(replacement, escaped)

    for index, fragment in enumerate(placeholders):
        escaped = escaped.replace(f"\x00{index}\x00", fragment)

    return escaped


def is_table_row(line: str) -> bool:
    return bool(re.match(r"^\|.+\|$", line.strip()))


def is_separator_row(line: str) -> bool:
    trimmed = line.strip().removeprefix("|").removesuffix("|")
    return all(re.match(r"^\s*[-:]+\s*$", cell) for cell in trimmed.split("|"))


def parse_cells(line: str) -> list[str]:
    trimmed = line.strip().removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in trimmed.split("|")]


def parse_markdown(markdown: str) -> str:
    lines = markdown.split("\n")
    output: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        trimmed = line.strip()

        if trimmed == "":
            i += 1
            continue

        if trimmed.startswith("```"):
            lang = trimmed[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(html.escape(lines[i]))
                i += 1
            if i < len(lines):
                i += 1
            output.append(
                f'<pre><code class="language-{html.escape(lang, quote=True)}">'
                + "\n".join(code_lines)
                + "</code></pre>"
            )
            continue

        if is_table_row(trimmed):
            table_rows: list[str] = []
            while i < len(lines) and is_table_row(lines[i].strip()):
                table_rows.append(lines[i].strip())
                i += 1

            if len(table_rows) >= 2 and is_separator_row(table_rows[1]):
                header_cells = parse_cells(table_rows[0])
                header_html = "".join(f"<th>{inline_format(cell)}</th>" for cell in header_cells)
                body_rows = table_rows[2:]
                body_html = "\n".join(
                    "<tr>"
                    + "".join(f"<td>{inline_format(cell)}</td>" for cell in parse_cells(row))
                    + "</tr>"
                    for row in body_rows
                )
                output.append(
                    '<div class="table-wrapper"><table>'
                    f"<thead><tr>{header_html}</tr></thead>"
                    f"<tbody>{body_html}</tbody>"
                    "</table></div>"
                )
            else:
                for row in table_rows:
                    output.append(f"<p>{inline_format(row)}</p>")
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", trimmed)
        if heading_match:
            level = len(heading_match.group(1))
            output.append(f"<h{level}>{inline_format(heading_match.group(2))}</h{level}>")
            i += 1
            continue

        if re.match(r"^(---+|\*\*\*+|___+)$", trimmed):
            output.append("<hr>")
            i += 1
            continue

        if trimmed.startswith("> ") or trimmed == ">":
            quote_lines: list[str] = []
            while i < len(lines) and (lines[i].strip().startswith("> ") or lines[i].strip() == ">"):
                quote_lines.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            output.append("<blockquote>" + "<br>".join(inline_format(item) for item in quote_lines) + "</blockquote>")
            continue

        if re.match(r"^[-*+]\s+", trimmed):
            list_items: list[str] = []
            while i < len(lines) and re.match(r"^[-*+]\s+", lines[i].strip()):
                list_items.append(re.sub(r"^[-*+]\s+", "", lines[i].strip()))
                i += 1
            output.append("<ul>" + "".join(f"<li>{inline_format(item)}</li>" for item in list_items) + "</ul>")
            continue

        if re.match(r"^\d+\.\s+", trimmed):
            list_items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                list_items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            output.append("<ol>" + "".join(f"<li>{inline_format(item)}</li>" for item in list_items) + "</ol>")
            continue

        output.append(f"<p>{inline_format(trimmed)}</p>")
        i += 1

    return "\n".join(output)


def generate_html(markdown: str, *, theme_name: str = "light", title: str = "深度研究报告") -> str:
    theme = THEMES[theme_name]
    content = parse_markdown(markdown)
    safe_title = html.escape(title)

    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>{safe_title}</title>
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, \"Noto Sans SC\", sans-serif;
      line-height: 1.8;
      color: {theme['text']};
      background-color: {theme['body_bg']};
      padding: 40px 20px;
    }}

    .container {{
      max-width: 900px;
      margin: 0 auto;
      background: {theme['body_bg']};
      padding: 40px 60px;
      box-shadow: 0 4px 20px {theme['shadow']};
      border-radius: 12px;
    }}

    h1, h2, h3, h4, h5, h6 {{
      color: {theme['heading']};
      margin: 1.5em 0 0.8em;
      font-weight: 600;
      line-height: 1.3;
    }}

    h1 {{
      font-size: 2.2em;
      border-bottom: 3px solid {theme['link']};
      padding-bottom: 0.3em;
      margin-bottom: 1em;
    }}

    h2 {{
      font-size: 1.6em;
      border-bottom: 1px solid {theme['hr']};
      padding-bottom: 0.3em;
      margin-top: 2em;
    }}

    h3 {{ font-size: 1.3em; color: {theme['link']}; }}
    h4 {{ font-size: 1.1em; }}

    p {{ margin: 1em 0; }}

    a {{
      color: {theme['link']};
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: border-color 0.2s;
    }}

    a:hover {{
      color: {theme['link_hover']};
      border-bottom-color: {theme['link_hover']};
    }}

    strong {{ font-weight: 600; }}
    em {{ font-style: italic; }}

    blockquote {{
      margin: 1.5em 0;
      padding: 15px 20px;
      background: {theme['blockquote']};
      border-left: 4px solid {theme['blockquote_border']};
      border-radius: 0 8px 8px 0;
      color: {theme['muted']};
    }}

    blockquote p {{ margin: 0; }}

    pre {{
      background: {theme['code']};
      padding: 20px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 1.5em 0;
      font-size: 0.9em;
    }}

    code {{
      font-family: \"Fira Code\", \"JetBrains Mono\", Consolas, Monaco, monospace;
      background: {theme['code']};
      color: {theme['code_text']};
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.9em;
    }}

    pre code {{
      background: none;
      padding: 0;
    }}

    .table-wrapper {{
      width: 100%;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      margin: 1.5em 0;
      border-radius: 8px;
      border: 1px solid {theme['table_border']};
      position: relative;
    }}

    table {{
      width: 100%;
      min-width: 400px;
      border-collapse: collapse;
      font-size: 0.95em;
    }}

    thead {{
      position: sticky;
      top: 0;
      z-index: 1;
    }}

    th {{
      background: {theme['table_header']};
      font-weight: 600;
      white-space: nowrap;
      padding: 12px 16px;
      text-align: left;
      border-bottom: 2px solid {theme['table_border']};
    }}

    td {{
      padding: 10px 16px;
      text-align: left;
      border-bottom: 1px solid {theme['table_border']};
      word-break: break-word;
    }}

    tbody tr:nth-child(even) {{
      background: {theme['table_stripe']};
    }}

    tbody tr:hover {{
      background: {theme['table_hover']};
    }}

    ul, ol {{
      margin: 1em 0;
      padding-left: 2em;
    }}

    li {{ margin: 0.5em 0; }}

    hr {{
      border: none;
      border-top: 1px solid {theme['hr']};
      margin: 2em 0;
    }}

    img {{
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      margin: 1em 0;
    }}

    .report-header {{
      text-align: center;
      padding: 20px 0 30px;
      border-bottom: 1px solid {theme['hr']};
      margin-bottom: 30px;
    }}

    .report-header .author {{
      font-size: 0.9em;
      color: {theme['link']};
      font-weight: 500;
    }}

    .report-header .author-icon {{
      margin-right: 8px;
    }}

    .report-footer {{
      text-align: center;
      padding: 30px 0 20px;
      border-top: 1px solid {theme['hr']};
      margin-top: 40px;
      color: {theme['footer']};
      font-size: 0.9em;
    }}

    .report-footer .author {{
      color: {theme['link']};
      font-weight: 500;
    }}

    @media print {{
      body {{ padding: 0; background: white; color: black; }}
      .container {{ box-shadow: none; padding: 0; max-width: 100%; }}
      a {{ color: black; text-decoration: underline; }}
      .table-wrapper {{ overflow: visible; border: none; }}
      table {{ min-width: 0; font-size: 0.85em; }}
      th, td {{ padding: 6px 8px; }}
      .report-header, .report-footer {{ border-color: #cccccc; }}
    }}

    @media (max-width: 768px) {{
      body {{ padding: 10px 4px; }}
      .container {{ padding: 16px 12px; }}
      h1 {{ font-size: 1.6em; }}
      h2 {{ font-size: 1.3em; }}

      .table-wrapper {{
        margin-left: -12px;
        margin-right: -12px;
        border-radius: 0;
        border-left: none;
        border-right: none;
        background:
          linear-gradient(to right, {theme['body_bg']} 30%, transparent),
          linear-gradient(to left, {theme['body_bg']} 30%, transparent),
          linear-gradient(to right, {theme['scroll_hint']}, transparent 30px),
          linear-gradient(to left, {theme['scroll_hint']}, transparent 30px);
        background-position: left center, right center, left center, right center;
        background-size: 40px 100%, 40px 100%, 40px 100%, 40px 100%;
        background-repeat: no-repeat;
        background-attachment: local, local, scroll, scroll;
      }}

      table {{ font-size: 0.85em; }}

      th, td {{ padding: 8px 10px; }}

      th:first-child,
      td:first-child {{
        position: sticky;
        left: 0;
        z-index: 1;
        background: {theme['body_bg']};
        border-right: 2px solid {theme['table_border']};
      }}

      th:first-child {{
        background: {theme['table_header']};
        z-index: 2;
      }}
    }}
  </style>
</head>
<body>
  <div class=\"container\">
    <header class=\"report-header\">
      <div class=\"author\"><span class=\"author-icon\">🎨</span>小艺报告专家 · 内容由AI生成仅供参考</div>
    </header>
    {content}
    <footer class=\"report-footer\">
      <div class=\"author\"><span class=\"author-icon\">🎨</span>小艺报告专家 · 内容由AI生成仅供参考</div>
    </footer>
  </div>
</body>
</html>"""


def extract_title(markdown: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", markdown, flags=re.MULTILINE)
    if not match:
        return fallback
    return re.sub(r"[：:].*$", "", match.group(1)).strip() or fallback


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Markdown 转 HTML 转换工具")
    parser.add_argument("input", help="输入的 Markdown 文件")
    parser.add_argument("output", nargs="?", help="输出的 HTML 文件（默认与输入同名）")
    parser.add_argument("--theme", choices=sorted(THEMES.keys()), default="light", help="主题")
    parser.add_argument("--title", default="深度研究报告", help="页面标题")
    parser.add_argument(
        "--reports-root",
        default=str(DEFAULT_REPORTS_ROOT),
        help="允许读写的根目录，默认使用 ~/.openclaw/workspace/reports",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    reports_root = Path(os.path.expanduser(args.reports_root)).resolve()
    if not reports_root.exists():
        fail(f"允许目录不存在: {reports_root}")

    safe_input_file = resolve_allowed_input_path(args.input, reports_root)
    output_file = args.output or str(safe_input_file.with_suffix(".html"))
    safe_output_file = resolve_allowed_output_path(output_file, reports_root)

    markdown = safe_input_file.read_text(encoding="utf-8")
    title = extract_title(markdown, args.title)
    html_output = generate_html(markdown, theme_name=args.theme, title=title)
    safe_output_file.write_text(html_output, encoding="utf-8")

    print("转换完成")
    print(f"  输入: {safe_input_file}")
    print(f"  输出: {safe_output_file}")
    print(f"  主题: {args.theme}")


if __name__ == "__main__":
    main()
