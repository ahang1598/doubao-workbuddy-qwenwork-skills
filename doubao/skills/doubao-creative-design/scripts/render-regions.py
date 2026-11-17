"""Render self-contained HTML region viewers from layout.json; no image assets required."""
import argparse
import json
from html import escape
from pathlib import Path


STYLE = '''body{margin:16px;font-family:"PingFang SC","Heiti SC",sans-serif;color:#242424}
svg{display:block;width:100%;height:auto;margin:0 0 16px}
.region-label{height:100%;display:flex;align-items:center;justify-content:center;text-align:center;line-height:1.3;font-family:"PingFang SC","Heiti SC",sans-serif;color:#242424}
.region-label span{white-space:pre-wrap;overflow-wrap:anywhere;min-width:0}
nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
button[aria-current="page"]{font-weight:bold}'''


def number(value):
    return str(value)


def region_svg(page):
    width, height = page['width'], page['height']
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {number(width)} {number(height)}" '
             f'width="{number(width)}" height="{number(height)}" style="max-width:{number(width)}px" '
             f'role="img" aria-label="{escape(page["title"], quote=True)}：区域结构示意">',
             f'<rect width="{number(width)}" height="{number(height)}" fill="#eeeeee"/>']
    for region in sorted(page['regions'], key=lambda item: item['z']):
        x, y, w, h = region['box']
        cx, cy = x + w / 2, y + h / 2
        fill = '#b8b8b8' if region['kind'] == 'image' else '#e4e4e4'
        transform = f'rotate({number(region["rotation"])} {number(cx)} {number(cy)})'
        common = f'fill="{fill}" stroke="#898989" stroke-width="2" transform="{transform}"'
        parts.append(f'<g data-region="{escape(region["id"], quote=True)}" data-z="{number(region["z"])}">')
        if region['shape'] == 'ellipse':
            parts.append(f'<ellipse cx="{number(cx)}" cy="{number(cy)}" rx="{number(w / 2)}" ry="{number(h / 2)}" {common}/>')
        else:
            parts.append(f'<rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" {common}/>')
        size = {'primary': 46, 'secondary': 30, 'body': 25, 'meta': 19}[region['hierarchy']]
        if '\n' in region['role']:
            size = min(size, 36)
        parts.append(f'<foreignObject x="{number(x + 12)}" y="{number(y + 2)}" width="{number(w - 24)}" height="{number(h - 4)}">'
                     f'<div xmlns="http://www.w3.org/1999/xhtml" class="region-label" style="font-size:{size}px">'
                     f'<span>{escape(region["role"])}</span></div></foreignObject></g>')
    parts.append('</svg>')
    return ''.join(parts)


def details(page):
    rows = ''.join('<li>' + escape(region['role']) + '：' +
                   ('图片区域' if region['kind'] == 'image' else '文字区域') + '</li>'
                   for region in page['regions'])
    return '<details><summary>区域用途说明</summary><ul>' + rows + '</ul></details>'


def document(title, body):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + escape(title) + '</title><style>' + STYLE + '</style></head><body>' + body + '</body></html>')


def page_html(page):
    return document(page['title'], region_svg(page) + details(page))


def index_html(suite):
    buttons = ''.join(f'<button type="button" data-page="{i}" aria-controls="page-{i}" '
                      f'aria-current="{"page" if i == 0 else "false"}">{i + 1} · {escape(page["title"])}</button>'
                      for i, page in enumerate(suite['pages']))
    sections = ''.join(f'<section id="page-{i}" class="layout-page"' + (' hidden' if i else '') + '>'
                       + '<h2>' + escape(page['title']) + '</h2>' + region_svg(page) + details(page) + '</section>'
                       for i, page in enumerate(suite['pages']))
    script = '''<script>
const buttons = Array.from(document.querySelectorAll('nav button'));
const pages = Array.from(document.querySelectorAll('.layout-page'));
buttons.forEach((button, n) => button.addEventListener('click', () => {
  pages.forEach((page, i) => { page.hidden = i !== n; });
  buttons.forEach((item, i) => item.setAttribute('aria-current', i === n ? 'page' : 'false'));
}));
</script>'''
    return document(suite['name'], '<h1>' + escape(suite['name']) + '</h1>'
                    '<p>纯区域结构。文字是用途标签；灰色框是空间占位。本页不是成品，不包含原设计参考图片。</p>'
                    '<nav aria-label="切换布局页">' + buttons + '</nav>' + sections
                    + '<p><a href="layout.json">布局 JSON</a></p>' + script)


def main():
    parser = argparse.ArgumentParser(description='从布局 JSON 重建 HTML 结构查看页；不生成或依赖 PNG/JPG')
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='新的临时输出目录，不写回模板库')
    args = parser.parse_args()
    root = args.output.resolve()
    if root.exists():
        raise ValueError('输出目录已存在；请选择新目录')
    assets = (Path(__file__).resolve().parents[1] / 'assets').resolve()
    if root == assets or assets in root.parents:
        raise ValueError('输出目录不得位于发布资源目录内')
    suite = json.loads(args.layout.read_text())
    destinations = {root / 'index.html', root / 'layout.json'}
    for page in suite['pages']:
        file = Path(page['file'])
        if file.is_absolute() or '..' in file.parts or file.suffix != '.html':
            raise ValueError('页面路径须为相对 HTML 路径')
        destination = (root / file).resolve()
        if not destination.is_relative_to(root) or destination in destinations:
            raise ValueError('页面路径重复、越界或使用保留名称')
        destinations.add(destination)
    if any(parent in destinations for path in destinations for parent in path.parents):
        raise ValueError('页面路径存在文件与目录冲突')
    root.mkdir(parents=True)
    (root / 'layout.json').write_text(json.dumps(suite, ensure_ascii=False, indent=2))
    for page in suite['pages']:
        destination = root / page['file']
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(page_html(page))
    (root / 'index.html').write_text(index_html(suite))
    print('已重建' + str(len(suite['pages'])) + '页 HTML 区域预览')


if __name__ == '__main__':
    main()
