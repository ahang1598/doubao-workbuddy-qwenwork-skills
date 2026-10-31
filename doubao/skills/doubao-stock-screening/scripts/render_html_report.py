#!/usr/bin/env python3
"""Render a research Markdown report as a self-contained, finance-styled HTML file.

Usage: python3 scripts/render_html_report.py report.md --output report.html
Put a JSON chart specification in a <!-- chart ... --> block to render a native,
responsive SVG chart. Markdown images remain available for non-chart artwork.
Use {{embed:relative-chart.html}} for custom interactive charts.
"""

import argparse
import base64
import html
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse

from native_charts import render_chart


CSS = """
:root{--navy:#101f35;--navy2:#1a3554;--ink:#17283c;--muted:#607086;--line:#dbe3eb;--paper:#fff;--canvas:#f2f5f8;--accent:#b48945;--teal:#13756e;--risk:#aa4a48}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--canvas);color:var(--ink);font:15px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:1060px;margin:32px auto 64px;background:var(--paper);box-shadow:0 16px 48px #10243a13;border:1px solid var(--line)}
header{background:linear-gradient(125deg,var(--navy),var(--navy2));color:white;padding:36px 52px;border-bottom:4px solid var(--accent)}
header .eyebrow{font-size:12px;letter-spacing:.22em;color:#d5bc8e;font-weight:700}header h1{font-size:30px;line-height:1.35;margin:12px 0 0;font-weight:700;color:#fff}
article{padding:34px 52px 55px}h1,h2,h3,h4{color:var(--navy);line-height:1.4}article h1{font-size:25px}h2{font-size:21px;margin:34px 0 15px;padding:0 0 10px;border-bottom:2px solid var(--accent)}h3{font-size:17px;margin:26px 0 11px}h4{font-size:15px;margin:20px 0 8px}
p{margin:0 0 15px}strong{color:var(--navy)}a{color:var(--teal);text-decoration:none;border-bottom:1px solid #83b5b0}a:hover{text-decoration:underline}
.table-wrap{overflow-x:auto;margin:17px 0 24px;border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-size:13px;min-width:480px}th{background:var(--navy);color:white;text-align:left;font-weight:600}td,th{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}tbody tr:nth-child(even){background:#f6f8fa}tbody tr:hover{background:#edf4f4}
ul,ol{padding-left:1.5em;margin:0 0 18px}li{margin:5px 0}blockquote{border-left:4px solid var(--accent);background:#faf8f3;margin:18px 0;padding:12px 18px;color:var(--muted)}blockquote p:last-child{margin-bottom:0}
figure{margin:20px 0}article img{max-width:100%;height:auto;display:block;margin:18px auto;border:1px solid var(--line)}figcaption{font-size:12px;color:var(--muted);margin-top:6px}.report-chart{border:1px solid var(--line);padding:20px 20px 14px;background:#fff}.report-chart .chart-scroll{overflow-x:auto}.report-chart svg{display:block;width:100%;height:auto;overflow:visible}.report-chart figcaption strong{display:block;font-size:15px;color:var(--navy);margin-bottom:3px}.report-chart .chart-meta{display:block;margin-top:4px}.report-chart .scroll-hint{display:none}iframe.chart{display:block;width:100%;height:560px;border:1px solid var(--line);background:white;margin:18px 0}
pre{overflow:auto;background:#0e1d31;color:#e9eef4;padding:16px 18px}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.9em}p code,li code{background:#f0f3f6;padding:2px 4px}hr{border:0;border-top:1px solid var(--line);margin:28px 0}
@media(max-width:700px){main{margin:0;border:0}header{padding:24px}header h1{font-size:25px}article{padding:24px}.report-chart{padding:12px 8px}.report-chart svg{min-width:650px}.report-chart .scroll-hint{display:block;color:var(--teal);margin-top:5px}iframe.chart{height:460px}}@media print{body{background:white}main{box-shadow:none;border:0;margin:0}header{-webkit-print-color-adjust:exact;print-color-adjust:exact}.report-chart,iframe.chart{break-inside:avoid}a{color:inherit}}
"""

LINK = re.compile(r'(!?)\[([^\]]*)\]\(([^)]+)\)')
BARE_URL = re.compile(r'https?://[^\s<>]+')
def plain(raw):
    """Escape prose while keeping source-index URLs clickable."""
    parts = []
    last = 0
    for match in BARE_URL.finditer(raw):
        url = match.group(0).rstrip('.,;，。；)）')
        if not url:
            continue
        parts.append(html.escape(raw[last:match.start()]))
        parts.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(url)}</a>')
        last = match.start() + len(url)
    parts.append(html.escape(raw[last:]))
    return ''.join(parts)


def asset_url(raw, root):
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"报告资源不存在: {path}")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if not mime.startswith("image/"):
        raise ValueError(f"图片必须是图像文件: {path}")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def inline(raw, root):
    parts = []
    last = 0
    for match in LINK.finditer(raw):
        parts.append(plain(raw[last:match.start()]))
        is_image, label, target = match.groups()
        if is_image:
            parts.append(f'<img src="{asset_url(target, root)}" alt="{html.escape(label, quote=True)}">')
        else:
            scheme = urlparse(target).scheme.lower()
            if scheme in {"http", "https", "mailto"} or (not scheme and not target.startswith("//")):
                parts.append(f'<a href="{html.escape(target, quote=True)}">{html.escape(label)}</a>')
            else:
                parts.append(html.escape(match.group(0)))
        last = match.end()
    parts.append(plain(raw[last:]))
    result = ''.join(parts)
    result = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result)
    result = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', result)
    result = re.sub(r'`([^`]+)`', r'<code>\1</code>', result)
    return result


def split_row(line):
    return [cell.strip() for cell in line.strip().strip('|').split('|')]


def is_separator(line):
    return bool(re.fullmatch(r'\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*', line))


def render(markdown, root):
    lines = markdown.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped == '<!-- chart':
            chart_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != '-->':
                chart_lines.append(lines[i]); i += 1
            if i >= len(lines):
                raise ValueError('图表缺少结束标记 -->')
            try:
                spec = json.loads('\n'.join(chart_lines))
            except json.JSONDecodeError as exc:
                raise ValueError(f'图表 JSON 无效：{exc}') from exc
            out.append(render_chart(spec))
            i += 1
            continue
        embed = re.fullmatch(r'\{\{embed:(.+?\.html)\}\}', stripped)
        if embed:
            chart_path = (root / embed.group(1)).resolve()
            if not chart_path.is_file():
                raise FileNotFoundError(f"图表不存在: {chart_path}")
            chart = chart_path.read_text(encoding='utf-8')
            resize = "<script>function reportHeight(){parent.postMessage({type:'finance-chart-height',height:document.documentElement.scrollHeight},'*')}addEventListener('load',reportHeight);new ResizeObserver(reportHeight).observe(document.body);setTimeout(reportHeight,300)</script>"
            close = chart.lower().rfind('</body>')
            chart = chart[:close] + resize + chart[close:] if close >= 0 else chart + resize
            out.append(f'<iframe class="chart" title="金融图表" sandbox="allow-scripts" srcdoc="{html.escape(chart, quote=True)}"></iframe>')
            i += 1
            continue
        if stripped.startswith('```'):
            language = stripped[3:].strip()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code.append(lines[i]); i += 1
            out.append(f'<pre><code class="language-{html.escape(language, quote=True)}">{html.escape(chr(10).join(code))}</code></pre>')
            i += 1
            continue
        heading = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading:
            level = min(len(heading.group(1)), 4)
            out.append(f'<h{level}>{inline(heading.group(2), root)}</h{level}>')
            i += 1
            continue
        if i + 1 < len(lines) and '|' in line and is_separator(lines[i + 1]):
            headers = split_row(line)
            rows = []
            i += 2
            while i < len(lines) and '|' in lines[i] and lines[i].strip():
                rows.append(split_row(lines[i])); i += 1
            out.append('<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th>{inline(c, root)}</th>' for c in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{inline(c, root)}</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></div>')
            continue
        if re.fullmatch(r'[-*_]{3,}', stripped):
            out.append('<hr>'); i += 1; continue
        if re.match(r'^\s*>', line):
            quote = []
            while i < len(lines) and re.match(r'^\s*>', lines[i]):
                quote.append(re.sub(r'^\s*>\s?', '', lines[i])); i += 1
            out.append('<blockquote><p>' + '<br>'.join(inline(x, root) for x in quote) + '</p></blockquote>')
            continue
        list_match = re.match(r'^\s*([-+*]|\d+[.)])\s+(.+)$', line)
        if list_match:
            tag = 'ol' if list_match.group(1)[0].isdigit() else 'ul'
            items = []
            while i < len(lines):
                match = re.match(r'^\s*([-+*]|\d+[.)])\s+(.+)$', lines[i])
                if not match or match.group(1)[0].isdigit() != (tag == 'ol'):
                    break
                items.append(f'<li>{inline(match.group(2), root)}</li>'); i += 1
            out.append(f'<{tag}>' + ''.join(items) + f'</{tag}>')
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,6})\s|\s*([-+*]|\d+[.)])\s|\s*>|```|\{\{embed:|<!-- chart', lines[i]):
            if i + 1 < len(lines) and '|' in lines[i] and is_separator(lines[i + 1]):
                break
            paragraph.append(lines[i]); i += 1
        body = '<br>'.join(inline(x, root) for x in paragraph)
        out.append(f'<p>{body}</p>')
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser(description='生成自包含金融风格 HTML 研究报告')
    parser.add_argument('markdown', type=Path, help='经过事实与内容门禁的读者版 Markdown')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--title')
    args = parser.parse_args()
    source = args.markdown.resolve()
    body = source.read_text(encoding='utf-8')
    title = args.title or next((m.group(1).strip() for line in body.splitlines() if (m := re.match(r'^#\s+(.+)', line))), source.stem)
    resize_listener = "<script>addEventListener('message',function(event){if(!event.data||event.data.type!=='finance-chart-height')return;for(const frame of document.querySelectorAll('iframe.chart')){if(frame.contentWindow===event.source){frame.style.height=Math.max(240,Math.min(3000,Number(event.data.height)+16))+'px';break}}})</script>"
    page = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(title) + '</title><style>' + CSS + '</style></head><body><main><header><div class="eyebrow">EQUITY RESEARCH · 投资研究</div><h1>' + html.escape(title) + '</h1></header><article>' + render(body, source.parent) + '</article></main>' + resize_listener + '</body></html>'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
