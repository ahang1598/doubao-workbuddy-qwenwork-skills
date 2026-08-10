#!/usr/bin/env python3
"""
把结构化的报告内容（标题、段落、表格、图表、提示框）渲染成一份自包含的 HTML 报告，
图表以 base64 内嵌，不依赖外部文件，适合直接用浏览器打开或发送给他人。

只用 Python 标准库，无第三方依赖。图表 PNG 需先用 render_charts.py 生成。

输入 JSON 结构：
{
  "title": "报告标题",
  "meta": {"公司": "示例公司", "市场": "A股", "生成时间": "2026-07-19"},   # 可选，顶部信息条
  "sections": [
    {"type": "heading", "level": 2, "text": "一、公告基本信息"},
    {"type": "paragraph", "text": "正文段落……"},
    {"type": "table", "headers": ["报告期", "营业收入(亿元)"], "rows": [["2025Q3", "15.2"]], "caption": "来源：……"},
    {"type": "chart", "image_path": "revenue-trend.png", "caption": "图1：近5期营业收入与净利润（示例）"},
    {"type": "callout", "tone": "info", "text": "提示内容"}   # tone: info | warning | danger
  ]
}

用法：
  python3 render_html_report.py --input report-spec.json --output report.html --charts-dir charts
"""
import argparse
import base64
import html
import json
import mimetypes
import os
import sys

CSS = """
:root {
  --text-primary: #1a1a1a;
  --text-secondary: #555555;
  --border: #e2e2e2;
  --bg-subtle: #fafafa;
  --info-bg: #eaf2fb; --info-text: #1c5ba8;
  --warning-bg: #fdf3e2; --warning-text: #9a6a00;
  --danger-bg: #fbeaea; --danger-text: #b3261e;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 40px 16px;
  background: #ffffff;
  color: var(--text-primary);
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  line-height: 1.7;
}
article { max-width: 820px; margin: 0 auto; }
h1 { font-size: 24px; font-weight: 700; margin: 0 0 12px; }
h2 { font-size: 19px; font-weight: 700; margin: 32px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
h3 { font-size: 16px; font-weight: 600; margin: 24px 0 8px; }
h4 { font-size: 14px; font-weight: 600; margin: 20px 0 6px; color: var(--text-secondary); }
p { font-size: 14px; color: var(--text-primary); margin: 0 0 14px; }
.meta-bar {
  display: flex; flex-wrap: wrap; gap: 16px;
  background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 6px;
  padding: 12px 16px; margin-bottom: 20px; font-size: 13px; color: var(--text-secondary);
}
.meta-item b { color: var(--text-primary); font-weight: 600; }
.table-wrap { overflow-x: auto; margin: 12px 0 4px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { border: 1px solid var(--border); padding: 8px 10px; text-align: left; }
th { background: var(--bg-subtle); font-weight: 600; }
tr:nth-child(even) td { background: #fcfcfc; }
figure { margin: 16px 0; text-align: center; }
figure img { max-width: 100%; border: 1px solid var(--border); border-radius: 4px; }
.caption { font-size: 12px; color: var(--text-secondary); margin-top: 6px; text-align: left; }
.callout { border-radius: 6px; padding: 12px 14px; font-size: 13px; margin: 16px 0; }
.callout.info { background: var(--info-bg); color: var(--info-text); }
.callout.warning { background: var(--warning-bg); color: var(--warning-text); }
.callout.danger { background: var(--danger-bg); color: var(--danger-text); }
"""


def esc(text):
    return html.escape(str(text))


def render_heading(section, charts_dir):
    level = section.get("level", 2)
    level = min(max(level, 1), 4)
    return f"<h{level}>{esc(section['text'])}</h{level}>"


def render_paragraph(section, charts_dir):
    return f"<p>{esc(section['text'])}</p>"


def render_table(section, charts_dir):
    headers = section.get("headers", [])
    rows = section.get("rows", [])
    caption = section.get("caption")
    thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
    tbody = "".join(
        "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in rows
    )
    caption_html = f'<div class="caption">{esc(caption)}</div>' if caption else ""
    return f'<div class="table-wrap"><table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>{caption_html}'


def resolve_image_path(image_path, charts_dir):
    if os.path.isabs(image_path) and os.path.exists(image_path):
        return image_path
    candidates = []
    if charts_dir:
        candidates.append(os.path.join(charts_dir, os.path.basename(image_path)))
        candidates.append(os.path.join(charts_dir, image_path))
    candidates.append(image_path)
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"图表文件不存在，尝试过以下路径: {candidates}")


def render_chart(section, charts_dir):
    full_path = resolve_image_path(section["image_path"], charts_dir)
    mime, _ = mimetypes.guess_type(full_path)
    mime = mime or "image/png"
    with open(full_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    caption = section.get("caption")
    caption_html = f'<div class="caption">{esc(caption)}</div>' if caption else ""
    alt = esc(caption or "chart")
    return f'<figure><img src="data:{mime};base64,{b64}" alt="{alt}"/>{caption_html}</figure>'


def render_callout(section, charts_dir):
    tone = section.get("tone", "info")
    if tone not in ("info", "warning", "danger"):
        tone = "info"
    return f'<div class="callout {tone}">{esc(section["text"])}</div>'


RENDERERS = {
    "heading": render_heading,
    "paragraph": render_paragraph,
    "table": render_table,
    "chart": render_chart,
    "callout": render_callout,
}


def render_meta(meta):
    if not meta:
        return ""
    items = "".join(
        f'<span class="meta-item"><b>{esc(k)}</b>：{esc(v)}</span>' for k, v in meta.items()
    )
    return f'<div class="meta-bar">{items}</div>'


def main():
    parser = argparse.ArgumentParser(description="渲染公告解读报告为自包含 HTML")
    parser.add_argument("--input", required=True, help="报告内容规格 JSON 文件路径")
    parser.add_argument("--output", required=True, help="输出 HTML 文件路径")
    parser.add_argument("--charts-dir", default=None, help="图表 PNG 所在目录（chart section 的相对路径基准）")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        spec = json.load(f)

    title = spec.get("title", "公告解读报告")
    meta = spec.get("meta", {})
    sections = spec.get("sections", [])

    body_parts = [render_meta(meta)]
    for section in sections:
        s_type = section.get("type")
        renderer = RENDERERS.get(s_type)
        if not renderer:
            print(f"警告：未知的 section 类型 {s_type}，已跳过", file=sys.stderr)
            continue
        body_parts.append(renderer(section, args.charts_dir))

    html_doc = (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n<head>\n<meta charset="UTF-8"/>\n'
        f"<title>{esc(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<article>\n"
        f"<h1>{esc(title)}</h1>\n{''.join(body_parts)}\n</article>\n</body>\n</html>\n"
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_doc)

    print(f"已生成 HTML 报告: {args.output}")


if __name__ == "__main__":
    main()
