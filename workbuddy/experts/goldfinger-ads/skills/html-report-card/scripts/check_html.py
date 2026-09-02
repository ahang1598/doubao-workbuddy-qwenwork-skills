#!/usr/bin/env python3
"""HTML 卡片自检脚本 —— 检查是否违反 design-rules.md 的硬规则。

用法:
    python3 check_html.py <file.html> [more.html ...]

退出码: 0 = 无 error；1 = 有 error
"""
import re
import sys
from pathlib import Path


class Report:
    def __init__(self, name):
        self.name = name
        self.errors = []
        self.warns = []

    def err(self, rule, msg):
        self.errors.append(f'[规则{rule}] {msg}')

    def warn(self, rule, msg):
        self.warns.append(f'[规则{rule}] {msg}')

    def show(self):
        print(f'\n=== {self.name} ===')
        if not self.errors and not self.warns:
            print('  ✅ 全部通过')
            return
        for e in self.errors:
            print(f'  ❌ {e}')
        for w in self.warns:
            print(f'  ⚠️  {w}')


def strip_comments(html):
    return re.sub(r'<!--.*?-->', '', html, flags=re.S)


def check(path):
    r = Report(path.name)
    raw = path.read_text(encoding='utf-8', errors='replace')
    html = strip_comments(raw)

    # ---- CSS 内联（可移植性） ----
    if 'PASTE assets/theme.css HERE' in raw:
        r.err('0', 'theme.css 占位符未替换 —— CSS 没内联，发给别人会掉样式')
    elif '<style>' not in raw:
        r.err('0', '未找到 <style> 内联样式块')
    else:
        style = re.search(r'<style>(.*?)</style>', raw, re.S)
        if style and len(style.group(1).strip()) < 500:
            r.err('0', '内联样式过短，theme.css 可能未完整粘贴')

    # ---- 规则 10：Markdown 残留 ----
    body = re.sub(r'<style>.*?</style>', '', html, flags=re.S)
    body = re.sub(r'<script>.*?</script>', '', body, flags=re.S)
    if re.search(r'\*\*[^*\n]+\*\*', body):
        n = len(re.findall(r'\*\*[^*\n]+\*\*', body))
        r.err('10', f'残留 Markdown 加粗 `**...**` {n} 处，应写成 <strong>')
    if re.search(r'`[^`\n]+`', body):
        n = len(re.findall(r'`[^`\n]+`', body))
        r.err('10', f'残留 Markdown 代码 `...` {n} 处，应写成 <code>')
    if re.search(r'\]\([^)]+\)', body):
        r.err('10', '残留 Markdown 链接 `](...)`，应写成 <a href>')
    for pat, desc in [(r'^\s*#{1,6}\s', 'Markdown 标题 #'),
                      (r'^\s*[-*]\s+\S', 'Markdown 列表 - / *'),
                      (r'^\s*\|.*\|.*$', 'Markdown 表格 |')]:
        if re.search(pat, body, re.M):
            r.warn('10', f'疑似残留 {desc}（确认是否应转为 HTML 标签）')

    # ---- 规则 2：.lead 固定前缀 / 废话占位 ----
    leads = re.findall(r'<p class="lead">(.*?)</p>', html, re.S)
    for L in leads:
        if re.match(r'\s*<strong>\s*(结论|小结|总结|核心判断)\s*[:：]', L):
            r.err('2', f'.lead 出现固定前缀（禁「结论：」「小结：」）：{L[:40].strip()}...')
        txt = re.sub(r'<[^>]+>', '', L).strip()
        if re.match(r'^(以下是|下面是|本节介绍|本节说明|这里列出)', txt):
            r.err('2', f'.lead 是复述标题的废话，应删除整行：{txt[:36]}...')
        if len(txt) > 75:
            r.warn('2', f'.lead 超 60 字（{len(txt)} 字），建议精简：{txt[:30]}...')

    # ---- 规则 1：禁 h3/h4 降级 ----
    for tag in ('h3', 'h4', 'h5'):
        if re.search(rf'<{tag}[\s>]', html):
            r.err('1', f'出现 <{tag}>，小标题一律用 h2.section-title + 序号')

    # ---- 规则 1/9：序号连续性 ----
    idxs = re.findall(r'<span class="idx">\s*(\d+)\s*</span>', html)
    if idxs:
        nums = [int(x) for x in idxs]
        if nums != list(range(1, len(nums) + 1)):
            r.err('1', f'章节序号不连续：{nums}（应为 1..{len(nums)}）')

    # ---- 规则 3：同一 section 蓝黄混排 ----
    for sec in re.findall(r'<section[^>]*>(.*?)</section>', html, re.S):
        warn_n = len(re.findall(r'class="callout callout-warn"', sec))
        blue_n = len(re.findall(r'class="callout"(?!\s*callout-warn)', sec))
        if warn_n and blue_n:
            r.err('3', '同一 section 内蓝黄 callout 混排，应拆成两个 section')
        # ---- 规则 12：≥2 条 warn 并列 ----
        if warn_n >= 2:
            r.err('12', f'同 section 出现 {warn_n} 条 callout-warn 并列，'
                         '风险并列应改用裸 <ul class="plain-list">')

    # ---- 规则 12：callout-warn 内嵌 plain-list（旧写法已废） ----
    if re.search(r'<div class="callout callout-warn">.*?<ul class="plain-list">', html, re.S):
        r.err('12', 'callout-warn 内嵌 plain-list 是已废弃写法，风险并列请用裸 plain-list')

    # ---- 规则 7：icon 只允许在 banner meta ----
    meta = re.search(r'<div class="meta"(?:[^>]*)?>.*?</div>', html, re.S)
    meta_txt = meta.group(0) if meta else ''
    all_icons = re.findall(r'<i class="bi[^"]*"', html)
    meta_icons = re.findall(r'<i class="bi[^"]*"', meta_txt)
    if len(all_icons) > len(meta_icons):
        r.err('7', f'banner meta 之外出现 {len(all_icons)-len(meta_icons)} 个 icon，仅 meta 行允许')

    # ---- 规则 4：KV 表必须带 thead ----
    for tbl in re.findall(r'<table class="data-table">(.*?)</table>', html, re.S):
        if 'kv-key' in tbl and '<thead>' not in tbl:
            r.err('4', 'KV 型表格缺 <thead> 表头')

    # ---- emoji / blockquote ----
    if re.search(r'<blockquote', html):
        r.err('3', '出现 <blockquote>，提示条一律用 .callout')
    if re.search(r'[\U0001F300-\U0001FAFF\u2728\u26A0\u2705\u274C]', body):
        r.warn('3', '正文出现 emoji，规范建议靠颜色与标题词区分语义')

    # ---- banner 结构 ----
    if not re.search(r'<div class="banner"(?:[^>]*)?>', html):
        r.err('14', '缺少 banner 区块')
    else:
        if not re.search(r'<h1 class="title"(?:[^>]*)?>', html):
            r.err('14', 'banner 缺 <h1 class="title">')
        if '{{' in raw:
            leftover = sorted(set(re.findall(r'\{\{[^}]{1,40}\}\}', raw)))
            if leftover:
                r.err('14', f'占位符未替换（{len(leftover)} 种）：{", ".join(leftover[:6])}'
                             + (' ...' if len(leftover) > 6 else ''))
        # 花括号单层占位（如 {角色名}）只告警，可能是正文内容
        single = sorted(set(re.findall(r'(?<!\{)\{[\u4e00-\u9fa5A-Za-z_][^{}]{0,20}\}(?!\})', body)))
        if single:
            r.warn('14', f'疑似未替换的占位：{", ".join(single[:5])}'
                         + (' ...' if len(single) > 5 else ''))

    return r


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    reports = []
    for a in sys.argv[1:]:
        p = Path(a)
        if not p.exists():
            print(f'❌ 文件不存在: {p}')
            sys.exit(1)
        reports.append(check(p))
    for r in reports:
        r.show()
    ne = sum(len(r.errors) for r in reports)
    nw = sum(len(r.warns) for r in reports)
    print(f'\n合计：{ne} error / {nw} warning')
    sys.exit(1 if ne else 0)


if __name__ == '__main__':
    main()
