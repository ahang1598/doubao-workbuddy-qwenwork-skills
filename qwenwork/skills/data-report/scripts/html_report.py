#!/usr/bin/env python3
"""HTML report technical validator (lean).

Skill philosophy: the model writes whatever HTML/layout it wants. This script
only checks that the output is *technically* sound so the delivered report
doesn't throw JS errors or have broken structure.

Checks (all non-business, pure technical):
  1. HTML basics: DOCTYPE present, </html> present, charset declared.
  2. Inline JS syntax: every <script> block passes `node --check`.
  3. Embedded JSON parsability:
     - no NaN/Infinity (JSON.parse rejects these)
     - if the HTML contains <script type="application/json"> blocks or
       CHART_SPECS declarations, those JSON payloads must parse.
  4. ECharts library availability: if the HTML calls `echarts.*`, there must
     be either a `<script src="...echarts...">` CDN tag or an inline copy of
     ECharts in the page.
  5. Chart container DOM ids: every `echarts.init(document.getElementById('X'))`
     must have a matching `<div id="X">` in the HTML.
  6. Python f-string leakage: detect `{var}` / `{obj.attr()}` patterns in
     visible HTML text that were meant to be substituted but weren't.

Usage:
    python scripts/html_report.py --validate-html report.html
    python scripts/html_report.py --validate-html report.html --strict  # warnings → errors

Output JSON:
    {
      "ok": true/false,
      "file": "/abs/path/report.html",
      "file_size_kb": 52.3,
      "validation": {
          "errors": [...],
          "warnings": [...],
          "checks": {"html": "pass", "js": "pass", "json": "pass",
                     "echarts": "pass", "dom_ids": "pass", "fstring": "pass",
                     "numeric_literal": "pass"}
      },
      "human_summary": "校验通过 (7 checks, 0 errors, 0 warnings)"
    }
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass


# ── SKILL 版本 (打包后产物 .version 文件存在时回显) ────────────────────

def _skill_version():
    """读 SKILL 根 .version 的 version 字段. 仅打包产物有; 本地开发返回 None."""
    if hasattr(_skill_version, '_cached'):
        return _skill_version._cached
    try:
        _v = (Path(__file__).resolve().parent.parent / '.version').read_text(
            encoding='utf-8', errors='replace')
        for _line in _v.splitlines():
            if _line.startswith('version:'):
                _skill_version._cached = _line.split(':', 1)[1].strip() or None
                return _skill_version._cached
    except Exception:
        pass
    _skill_version._cached = None
    return None


# ── JSON safety ────────────────────────────────────────────────────────

def _json_safe_check(data, path=''):
    """Detect NaN/Infinity which JSON.parse rejects."""
    issues = []
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            issues.append(f'{path}: 非法浮点值 {data}（JSON.parse 无法解析）')
    elif isinstance(data, dict):
        for k, v in data.items():
            issues.extend(_json_safe_check(v, f'{path}.{k}' if path else str(k)))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            issues.extend(_json_safe_check(v, f'{path}[{i}]'))
    return issues


def _check_json_parsable_in_html(html):
    """Find embedded JSON payloads and check they parse.

    Scans:
      1. <script type="application/json"> ... </script> blocks
      2. `CHART_SPECS = [...];` / `REPORT_DATA = {...};` declarations
      3. `/*__REPORT_DATA__*/ {...}` patterns
    """
    errors = []
    details = {'json_blocks_checked': 0, 'chart_specs_found': False}

    # 1. <script type="application/json"> blocks
    json_tag_pattern = re.compile(
        r'<script[^>]+type=["\']application/json["\'][^>]*>([\s\S]*?)</script>',
        re.IGNORECASE,
    )
    for idx, m in enumerate(json_tag_pattern.finditer(html)):
        payload = m.group(1).strip()
        if not payload:
            continue
        details['json_blocks_checked'] += 1
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as e:
            errors.append(
                f'<script type="application/json"> 块 #{idx + 1} 无法解析: '
                f'line {e.lineno}, col {e.colno}: {e.msg}'
            )
            continue
        nan_issues = _json_safe_check(parsed, f'json_block_{idx + 1}')
        errors.extend(nan_issues)

    # 2. CHART_SPECS / window.CHART_SPECS
    spec_pattern = re.compile(
        r'(?:var|let|const|window\.)\s*CHART_SPECS\s*=\s*(\[[\s\S]*?\])\s*;',
        re.MULTILINE,
    )
    for idx, m in enumerate(spec_pattern.finditer(html)):
        payload = m.group(1)
        details['chart_specs_found'] = True
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as e:
            errors.append(
                f'CHART_SPECS 声明 #{idx + 1} 不是合法 JSON: '
                f'line {e.lineno}, col {e.colno}: {e.msg}. '
                f'ECharts 需要 CHART_SPECS 是纯 JSON 数组，禁止使用 JS 函数/注释/未加引号的 key'
            )
            continue
        nan_issues = _json_safe_check(parsed, f'CHART_SPECS[{idx}]')
        errors.extend(nan_issues)

    # 3. /*__REPORT_DATA__*/ pattern
    rpt_pattern = re.compile(r'/\*__REPORT_DATA__\*/\s*(\{[\s\S]*?\})\s*</script>')
    for idx, m in enumerate(rpt_pattern.finditer(html)):
        try:
            parsed = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            errors.append(
                f'__REPORT_DATA__ 块 #{idx + 1} 无法解析: '
                f'line {e.lineno}, col {e.colno}: {e.msg}'
            )
            continue
        nan_issues = _json_safe_check(parsed, f'__REPORT_DATA__')
        errors.extend(nan_issues)

    return errors, details


# ── JS syntax via Node.js ──────────────────────────────────────────────

def _extract_js_blocks(html):
    """Extract inline (non-JSON, non-src) <script> blocks."""
    script_pattern = re.compile(
        r'<script(?:\s[^>]*)?>([^<]*(?:<(?!/script>)[^<]*)*)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    json_type_pattern = re.compile(r'type=["\']application/json["\']', re.IGNORECASE)
    src_pattern = re.compile(r'\bsrc\s*=', re.IGNORECASE)

    blocks = []
    for idx, m in enumerate(script_pattern.finditer(html)):
        tag_full = html[m.start():m.start() + html[m.start():].index('>') + 1]
        if json_type_pattern.search(tag_full):
            continue  # JSON data island, checked separately
        if src_pattern.search(tag_full):
            continue  # external script, nothing inline to check
        js = m.group(1).strip()
        if not js:
            continue
        blocks.append((idx, js))
    return blocks


_JS_STUB_HEADER = (
    # Minimal stubs so references to runtime globals don't trigger "not defined"
    # errors — we want *syntax* checking only.
    'var echarts={init:function(){return{setOption:function(){},resize:function(){}}},'
    'graphic:{LinearGradient:function(){}},format:{addCommas:function(x){return x}}};\n'
    'var document={getElementById:function(){return{}},querySelectorAll:function(){return[]},'
    'querySelector:function(){return{}},addEventListener:function(){}};\n'
    'var window={addEventListener:function(){},innerWidth:1024,innerHeight:768};\n'
    'var console={log:function(){},warn:function(){},error:function(){}};\n'
    'var CHART_SPECS=[],REPORT_DATA={},COLORS=[];\n'
)
_JS_STUB_LINES = _JS_STUB_HEADER.count('\n')


def _check_js_node(js_blocks):
    """Run each inline JS block through `node --check`. Returns (errors, used_node).

    历史 bug：tempfile close 后立即 subprocess 调 node，长 JS（>10KB）偶发被 node
    读到部分写入版本，导致虚假 SyntaxError。修复：写完 flush + fsync + 大小校验，
    并对 node 报错重试 1 次（避免一过性 false positive）。
    """
    node = shutil.which('node')
    if not node:
        return [], False

    def _write_and_check(wrapped: str) -> tuple[int, str]:
        """写 tmp + node --check；返回 (returncode, stderr)。保证写完整。

        注：必须用 newline='' 禁用 Python text mode 的换行符自动转换。
        Windows 默认 \\n → \\r\\n，导致实际文件大小 > expected，触发 size check
        误报为 'tmp file write short'（虽然实际是写多了）。
        node --check 接受 \\n 行结尾的 .js 文件，无需 Windows 风格 CRLF。
        """
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False,
                                             encoding='utf-8', newline='') as f:
                f.write(wrapped)
                f.flush()
                os.fsync(f.fileno())  # 强制刷到磁盘，避免 node 读到截断版本
                tmp_path = f.name
            # 二次校验：确认 tmp 文件大小与 wrapped 一致（newline='' 保证 1:1）
            expected = len(wrapped.encode('utf-8'))
            actual = os.path.getsize(tmp_path)
            if actual != expected:
                return -1, f'tmp file size mismatch: actual={actual} expected={expected} bytes'
            r = subprocess.run(
                [node, '--check', tmp_path],
                capture_output=True, text=True, timeout=10,
                # Windows: 显式 utf-8，否则 text=True 默认 cp936 导致 node stderr 中含中文路径
                # （如 tmp 在 C:\Users\张三\AppData\Local\Temp\...）时解码乱码
                encoding='utf-8', errors='replace',
            )
            return r.returncode, r.stderr.strip()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    errors = []
    for idx, js in js_blocks:
        wrapped = _JS_STUB_HEADER + js + '\n'
        rc, stderr = _write_and_check(wrapped)
        if rc != 0:
            # node 报错时重试 1 次，避免一过性 I/O race 导致的 false positive
            rc, stderr = _write_and_check(wrapped)
        if rc == 0:
            continue

        meaningful = [
            l for l in stderr.splitlines()
            if l.strip() and not re.match(r'^Node\.js v\d+\.\d+\.\d+', l.strip())
        ]
        syntax_line = next(
            (l for l in meaningful if re.match(r'^\s*\w+Error:', l)),
            None,
        )
        if syntax_line:
            # Adjust line number: subtract stub header lines
            adjusted = re.sub(
                r':(\d+)',
                lambda m: f':{max(1, int(m.group(1)) - _JS_STUB_LINES)}',
                syntax_line,
                count=1,
            )
            errors.append(f'<script> 块 #{idx + 1}: {adjusted}')
        else:
            errors.append(
                f'<script> 块 #{idx + 1}: node --check 失败但无明显语法错，'
                f'stderr={stderr[:200]}'
            )
    return errors, True


def _check_js_brackets(js_blocks):
    """Fallback when Node is unavailable: bracket/quote balance."""
    errors = []
    for idx, js in js_blocks:
        # Strip string literals and comments (best-effort) before balance check
        stripped = re.sub(r'//[^\n]*', '', js)
        stripped = re.sub(r'/\*[\s\S]*?\*/', '', stripped)
        stripped = re.sub(r'"(?:[^"\\]|\\.)*"', '""', stripped)
        stripped = re.sub(r"'(?:[^'\\]|\\.)*'", "''", stripped)
        stripped = re.sub(r'`(?:[^`\\]|\\.)*`', '``', stripped)
        opens = stripped.count('(') + stripped.count('[') + stripped.count('{')
        closes = stripped.count(')') + stripped.count(']') + stripped.count('}')
        if opens != closes:
            errors.append(
                f'<script> 块 #{idx + 1} 括号不平衡: '
                f'open={opens}, close={closes} — 可能缺少 ) ] }} 或多余'
            )
    return errors


# ── DOM id consistency (chart containers) ──────────────────────────────

def _check_dom_id_consistency(html):
    """All `echarts.init(document.getElementById('X'))` require `<... id="X">`."""
    errors = []
    init_id_pattern = re.compile(
        r"""echarts\.init\(\s*document\.getElementById\(\s*['"]([^'"]+)['"]\s*\)""",
        re.IGNORECASE,
    )
    init_ids = sorted(set(init_id_pattern.findall(html)))
    if not init_ids:
        return errors

    html_id_pattern = re.compile(r'\bid=["\']([^"\']+)["\']')
    html_ids = set(html_id_pattern.findall(html))
    missing = [i for i in init_ids if i not in html_ids]
    if missing:
        errors.append(
            f'echarts.init() 引用了 HTML 中不存在的容器 id: {missing}. '
            f'请确保每个被 init 的 id 都有对应的 <div id="..."> 元素'
        )
    return errors


# ── ECharts library availability ───────────────────────────────────────

def _check_echarts_available(html):
    """If HTML uses echarts, it must have either CDN script or inline lib."""
    errors = []
    warnings = []

    uses_echarts = bool(re.search(r'\becharts\.\w+', html))
    if not uses_echarts:
        return errors, warnings

    has_cdn = bool(re.search(
        r'<script[^>]+src=["\'][^"\']*echarts[^"\']*["\']',
        html, re.IGNORECASE,
    ))
    # Inline ECharts ~800KB minified — heuristic: either explicit marker
    # or very large HTML with typical ECharts identifiers.
    has_inline = (
        'echarts.min.js' in html
        or (len(html) > 500_000 and 'ZRender' in html)
    )
    if not has_cdn and not has_inline:
        errors.append(
            'HTML 调用了 echarts.* 但既没有 CDN <script src> 也没有内联 ECharts 库，'
            '图表将报 ReferenceError: echarts is not defined'
        )

    # CDN vs init order: CDN script must appear before first echarts.init
    if has_cdn:
        cdn_pos = html.lower().find('echarts.min')
        init_pos = html.find('echarts.init')
        if 0 <= cdn_pos and 0 <= init_pos and init_pos < cdn_pos:
            errors.append(
                'ECharts CDN <script> 出现在 echarts.init() 调用之后，'
                '浏览器会 ReferenceError — 请将 <script src="...echarts..."> 放到 <head> 或 init 调用之前'
            )

    return errors, warnings


# ── f-string residual detection ────────────────────────────────────────

def _check_fstring_residuals(html):
    """Detect Python f-string residuals in HTML text AND JS string literals.

    Returns (errors, warnings).
      errors:   JS 字符串字面量中含 {var:spec} — 浏览器一定显示字面量，运行时 bug
      warnings: HTML 文本中疑似 {var} — 可能是 mustache 模板未渲染（信号弱）

    两类检查：
      (A) HTML 可见文本（剔除 <script>/<style>）— 原逻辑，warning
      (B) <script> 中的字符串字面量含 ECharts 不合法的 `{var:spec}` —
          ECharts formatter 合法占位符只有 {a}/{b}/{c}/{c0..9}/{d}/{e}（均无冒号），
          含冒号的 {var:spec} 一定是 Python f-string spec 残留（如 `'¥{c:,.0f}'`）。
          这是 ECharts API 误用的典型 bug — 浏览器显示成字面量 ¥{c:,.0f}。
          升级为 error。
    """
    errors = []
    warnings = []
    text_only = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    text_only = re.sub(r'<style[\s\S]*?</style>', '', text_only, flags=re.IGNORECASE)
    text_only = re.sub(r'<[^>]+>', ' ', text_only)

    patterns = [
        # function call: {len(x)}, {round(df.mean(), 2)}
        re.compile(r"(?<!\{)\{[a-zA-Z_][\w]*\([^{}]*\)(?:\.[\w]+(?:\([^{}]*\))?|\[[^\]]+\])*(?::[^}]*)?\}(?!\})"),
        # attribute/subscript: {df.mean()}, {data['key']}, {obj.attr.sub}
        re.compile(r"(?<!\{)\{[a-zA-Z_][\w]*(?:\.[\w]+(?:\([^{}]*\))?|\[[^\]]+\])+(?::[^}]*)?\}(?!\})"),
        # var + format spec: {mean:.2f}, {val:,.0f}
        re.compile(r"(?<!\{)\{[a-zA-Z_][\w]*:[^}]+\}(?!\})"),
        # plain name (≥2 chars to avoid single-char conflicts): {subject}
        re.compile(r"(?<!\{)\{[a-zA-Z_][\w]{1,}\}(?!\})"),
    ]
    matches = []
    seen = set()
    for pat in patterns:
        for m in pat.findall(text_only):
            if m not in seen:
                matches.append(m)
                seen.add(m)
    if matches:
        samples = matches[:5]
        # 升级为 error：HTML 可见区出现 Python f-string 字面量 = 用户直接看到
        # `{title}`/`{date}`/`{val:.2f}` 残文，100% 产物失实。
        # ECharts string formatter 的合法占位符 `{a}/{b}/{c}/{d}/{e}` 是单字符，
        # 已被 pattern[3] `\w{1,}` 自动排除；且 ECharts formatter 只出现在 <script>
        # JS string literal 内，HTML 可见文本扫不到。
        errors.append(
            f'HTML 可见文本中含 Python 模板变量未渲染 (用户会看到字面占位符): '
            f'{", ".join(repr(s) for s in samples)}'
            f'{" （共" + str(len(matches)) + "处）" if len(matches) > 5 else ""}. '
            f'常见原因：三引号 """...""" 字符串用作模板但忘加 f 前缀'
        )

    # (B) JS string literal 含 Python format spec — ECharts API 误用的典型 bug
    # 合法 ECharts 占位符（{a}/{b}/{c}/{c0..9}/{d}/{e}）都不含冒号，
    # 一旦在 JS string literal 出现 {var:spec}，必然是 Python format spec 残留。
    # 典型例子: formatter: '¥{c:,.0f}' → 浏览器显示字面量 ¥{c:,.0f}
    js_blocks = re.findall(
        r'<script(?:\s[^>]*)?>([^<]*(?:<(?!/script>)[^<]*)*)</script>',
        html, re.IGNORECASE | re.DOTALL,
    )
    # 提取 JS 字符串字面量（'...' / "..." / `...`），跳过其中 escape
    js_str_pat = re.compile(
        r"""'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|`(?:\\.|[^`\\])*`"""
    )
    # Python format spec 模式：必须以典型 type 字符结尾（避免误伤 JS 对象）
    # Python type 字符: bcdoxXneEfFgGn% 等
    pyspec_pat = re.compile(
        r"\{[a-zA-Z_][\w]*:[><^=+\- 0,#]*\.?\d*[bcdoxXeEfFgGn%]\}"
    )
    js_hits = []
    js_seen = set()
    for js in js_blocks:
        for str_lit_match in js_str_pat.finditer(js):
            str_lit = str_lit_match.group()
            for spec_match in pyspec_pat.findall(str_lit):
                if spec_match not in js_seen:
                    js_hits.append((spec_match, str_lit[:80]))
                    js_seen.add(spec_match)
    if js_hits:
        sample_specs = [s for s, _ in js_hits[:5]]
        sample_ctx = js_hits[0][1] if js_hits else ''
        errors.append(
            f'JS 字符串字面量中含 Python format spec（ECharts 字符串 formatter '
            f'不支持 {{var:spec}} 语法，浏览器会显示字面量）: '
            f'{", ".join(repr(s) for s in sample_specs)}'
            f'{" （共" + str(len(js_hits)) + "处）" if len(js_hits) > 5 else ""}. '
            f'首例上下文: {sample_ctx!r}. '
            f'修复：把 ECharts string formatter 改为 function (params) {{ ... }} 形式，'
            f'或在 Python 端用 f-string 提前算好数值嵌入 series.data'
        )

    # (C) JS string literal 含 `{{var}}` 双花括号 — Python f-string 转义残留
    # `{{` 在 Python f-string 中表示输出字面量 `{`；模型用 Python 思维写 ECharts
    # formatter 时把 `{b}` 写成 `{{b}}` → ECharts 不解析双花括号，浏览器显示字面 `{b}`。
    # 检测信号同样精确：ECharts string formatter 不接受双花括号占位符。
    # 例：label: { formatter: '{{b}}\n{{d}}%' }  → 渲染成 "{b}\n{d}%" 字面
    double_brace_pat = re.compile(r"\{\{[a-zA-Z_]\w*\}\}")
    dbrace_hits = []
    dbrace_seen = set()
    for js in js_blocks:
        for str_lit_match in js_str_pat.finditer(js):
            str_lit = str_lit_match.group()
            for dbm in double_brace_pat.findall(str_lit):
                if dbm not in dbrace_seen:
                    dbrace_hits.append((dbm, str_lit[:80]))
                    dbrace_seen.add(dbm)
    if dbrace_hits:
        sample_dbs = [s for s, _ in dbrace_hits[:5]]
        sample_ctx = dbrace_hits[0][1] if dbrace_hits else ''
        errors.append(
            f'JS 字符串字面量中含双花括号 `{{{{var}}}}`（Python f-string 转义残留，'
            f'ECharts 不解析双花括号占位符，会显示字面 `{{var}}`）: '
            f'{", ".join(repr(s) for s in sample_dbs)}'
            f'{" （共" + str(len(dbrace_hits)) + "处）" if len(dbrace_hits) > 5 else ""}. '
            f'首例上下文: {sample_ctx!r}. '
            f'修复：ECharts formatter 用单花括号 `{{b}}`/`{{c}}`/`{{d}}`，不是 `{{{{b}}}}`'
        )

    # (D) <style> CSS 块含 `{{` / `}}` 双花括号 — Python f-string 模板转义残留未渲染。
    # 模型用 f-string 写 HTML 时把 CSS 的 `{` `}` 转义成 `{{` `}}`，但最终没让模板经过
    # f-string 求值 (用了普通字符串/.replace 拼数据), `{{ }}` 原样输出 → 浏览器 CSS 解析
    # 失败 → 整个 <style> 失效、页面零样式。CSS 合法语法不含 `{{` (即便 @media/@supports
    # 嵌套也是单花括号), 故 <style> 内任何 `{{` 必是残留, 信号精确。
    css_dbrace_total = 0
    css_sample = ''
    for css in re.findall(r'<style[^>]*>(.*?)</style>', html, re.S | re.I):
        # 先剥离 CSS 字符串值 (content:"..." 等引号内内容), 避免字面 `{{` 误报;
        # 合法 CSS 结构位置不会有连续 `{{` (嵌套开括号间总有选择器), 故剥离后任何 `{{` 必是残留。
        css_struct = re.sub(r'"[^"]*"|\'[^\']*\'', '', css)
        n = css_struct.count('{{')
        if n:
            css_dbrace_total += n
            if not css_sample:
                idx = css_struct.find('{{')
                css_sample = css_struct[max(0, idx - 30):idx + 40].replace('\n', ' ').strip()
    if css_dbrace_total:
        errors.append(
            f'<style> CSS 块含 `{{{{ }}}}` 双花括号（Python f-string 转义残留未渲染，'
            f'浏览器 CSS 解析失败 → 整个样式块失效、页面零样式）: 共 {css_dbrace_total} 处. '
            f'首例: {css_sample!r}. '
            f'修复：CSS 用单花括号 `selector {{ ... }}`；若用 f-string 生成 HTML 必须让模板'
            f'真正经过 f-string 求值，或改用 .replace()/拼接插数据、CSS 保持单花括号'
        )

    return errors, warnings


# ── 未渲染的 __XXX__ 占位符检测（模型用 .replace("__X__", val) 但漏写 .replace）──

def _check_unrendered_placeholders(html):
    """Detect unrendered `__XXX__` template placeholders in user-visible DOM text.

    场景: 模型用 `html.replace("__VAR__", value)` 渲染模板, 但漏写某些 .replace 调用,
    导致用户打开 HTML 看到字面量 `__MAX_SALES_MONTH__` 等占位符明文。

    设计原则（高精准, 零误报）:
      Pattern: __[A-Z][A-Z0-9_]{2,}__   (≥5 字符, 全大写)
        - 排除 Python lowercase 内置 (__init__/__main__/__name__/__doc__ etc.)
        - ≥5 字符门槛排除偶然短词 (__OK__/__NO__ 等)
      位置:    仅 HTML 可见区
        - 剥 <script>/<style>/<code>/<pre>/<template> 段 (代码/示例段, 合法 __XXX__ 允许)
        - 剥 HTML 注释 <!-- -->
        - 剥 HTML 标签 (含 attribute, 例如 <input placeholder="__X__"> 不算)
      JS 客户端替换豁免:
        - 模型可能在 <script> 里用 `html.split("__X__").join(value)` 等 JS 动态替换。
        - 若可见区出现的 __XXX__ 同时在 <script> 字面量内出现, 视为合规（JS 会在 DOM 加载后填值）,
          静态不报错。runtime 真渲染 (browser_check) 兜底 — 若 JS replace 也漏写, DOM walker
          会在浏览器渲染后扫到残留。

    Returns (errors, warnings).
      errors: HTML 可见区有 __XXX__ 且 <script> 字面量未出现该 token — 用户会直接看到字面占位符。
    """
    errors = []
    pattern = re.compile(r'__[A-Z][A-Z0-9_]{2,}__')

    # 1. 提取所有 <script> 块, 仅在 JS string literal 内 (双/单/反引号) 检查豁免。
    #    注释 // ... 或代码标识符内的 token 不算 — 必须是开发者明确写的字符串字面量
    #    (这样才能通过 split/replace/innerHTML 真的对 DOM 进行替换)。
    scripts = re.findall(r'<script[^>]*>([\s\S]*?)</script>', html, flags=re.IGNORECASE)
    js_text = '\n'.join(scripts)
    # JS string literal: "__X__" / '__X__' / `__X__` (容许 token 嵌在更长字符串中)
    str_lit_pattern = re.compile(r'''["'`][^"'`]*(__[A-Z][A-Z0-9_]{2,}__)[^"'`]*["'`]''')
    js_referenced = set(str_lit_pattern.findall(js_text))

    # 2. 剥 SKIP_TAGS — script/style/code/pre/template
    body = re.sub(r'<(script|style|code|pre|template)[\s\S]*?</\1>', '', html,
                  flags=re.IGNORECASE)
    # 3. 剥 HTML 注释
    body = re.sub(r'<!--[\s\S]*?-->', '', body)
    # 4. 剥 HTML 标签 (含 attribute, 把 attribute 中的占位符也剥掉)
    body = re.sub(r'<[^>]+>', ' ', body)

    visible_leaks = set(pattern.findall(body))
    # 真泄露 = 可见区出现但 JS 字面量未声明
    leaks = sorted(visible_leaks - js_referenced)
    if leaks:
        samples = leaks[:8]
        errors.append(
            f'HTML 可见文本中含未渲染的 `__XXX__` 模板占位符（模型 .replace 调用漏写, '
            f'用户会看到字面量）: {", ".join(samples)}'
            f'{" （共" + str(len(leaks)) + "种）" if len(leaks) > 8 else ""}. '
            f'修复：检查生成脚本中是否所有模板占位符都有对应的 `html.replace("__XXX__", value)` 调用. '
            f'排查方法：`grep -oE "__[A-Z][A-Z0-9_]+__" template.html | sort -u` 列模板内全部占位符, '
            f'再对比代码中 `.replace()` 调用列表, 补齐缺失的. '
            f'若是 JS 客户端动态替换 (e.g. `html.split("__X__").join(val)`), 请把 token 写在 <script> 内字面量中, 静态检测会自动豁免'
        )
    return errors


# ── inf / Infinity / NaN 字面量残留检测（防 ¥inf / [Infinity, 135] 类问题）──

def _check_numeric_literal_residuals(html):
    """Detect bare inf / Infinity / NaN literals in HTML text and JS data.

    HTML 可见文本中出现 'inf' / 'Infinity' / 'NaN' (作为单词) → 用户会看到 "¥inf" 这种残文（warning）。
    JS 代码中数组/对象字面量含裸 Infinity / -Infinity / NaN / nan / inf → 运行时 ReferenceError，
    整页 ECharts 不渲染（实测 case_054 因此整页空白）。这条**升级为 error**，让 validate 整体 fail。

    Returns (errors, warnings)。
    """
    errors = []
    warnings = []

    # 1. HTML 可见文本（剔除 script/style/comment）
    text_only = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    text_only = re.sub(r'<style[\s\S]*?</style>', '', text_only, flags=re.IGNORECASE)
    text_only = re.sub(r'<!--[\s\S]*?-->', '', text_only)
    text_only = re.sub(r'<[^>]+>', ' ', text_only)

    # 作为单词出现（避免误伤 "infrastructure" 等含 inf 的合法词）
    # 关键场景：¥inf / -inf% / >inf< / Infinity 数字位置
    # 全 case-insensitive：numpy/pandas 默认 repr 是小写 'nan'/'inf'，模型经常直接拼进 HTML/JS
    text_patterns = [
        (re.compile(r'[¥$€£]\s*-?(?:inf|Infinity)\b', re.IGNORECASE), 'currency-inf'),
        (re.compile(r'-?(?:inf|Infinity)\s*[%‰]', re.IGNORECASE), 'percentage-inf'),
        (re.compile(r'(?<![a-zA-Z])-?Infinity(?![a-zA-Z])', re.IGNORECASE), 'literal-Infinity'),
        (re.compile(r'(?<![a-zA-Z])-?NaN(?![a-zA-Z])', re.IGNORECASE), 'literal-NaN'),
    ]
    text_hits = []
    for pat, label in text_patterns:
        for m in pat.findall(text_only):
            text_hits.append((label, m))
    if text_hits:
        samples = text_hits[:5]
        # 升级为 error: 用户可见区域出现 ¥inf / NaN% 等字面量 = 报告内容错误
        errors.append(
            f'HTML 可见文本含裸 inf/Infinity/NaN 字面量（用户会看到错值, 报告失实）: '
            f'{", ".join(repr(s[1]) + " (" + s[0] + ")" for s in samples)}'
            f'{"；共 " + str(len(text_hits)) + " 处" if len(text_hits) > 5 else ""}. '
            f'修复：写 HTML 前用 pandas 处理 NaN/Inf：'
            f'df.replace([np.inf, -np.inf], np.nan).fillna(0) 或显式标注 "—" / "N/A"'
        )

    # 2. JS 代码（脚本块）内的数组/对象字面量含 Infinity / NaN / inf / nan
    js_blocks = re.findall(r'<script[^>]*>([\s\S]*?)</script>', html, flags=re.IGNORECASE)
    js_hits = []
    # 数组/对象里出现 Infinity / NaN / inf / nan（如 [Infinity, 135] / [nan, 13.14] / {x: NaN}）
    # 必须 IGNORECASE：numpy/pandas 默认 repr 是小写 'nan'/'inf'，模型容易直接 str() 拼接进 JS
    # 实测 case_054_yoy_mom_matrix 因 data: [nan, 13.14, ...] 整页空白，原 regex 仅匹配大写漏检
    js_pat_in_array = re.compile(
        r'[\[,{:]\s*-?(?:Infinity|NaN|inf|nan)(?=\s*[,\]}])',
        re.IGNORECASE,
    )
    for block in js_blocks:
        # 跳过纯注释/字符串内的（粗略判断：只看非 // 行）
        no_line_cmt = re.sub(r'//[^\n]*', '', block)
        no_block_cmt = re.sub(r'/\*[\s\S]*?\*/', '', no_line_cmt)
        for m in js_pat_in_array.findall(no_block_cmt):
            js_hits.append(m.strip(' ,[{:'))
    if js_hits:
        samples = js_hits[:5]
        errors.append(
            f'JS 代码中数据数组/对象含裸 Infinity/NaN/inf/nan 字面量: '
            f'{", ".join(repr(s) for s in samples)}'
            f'{"；共 " + str(len(js_hits)) + " 处" if len(js_hits) > 5 else ""}. '
            f'渲染时会触发 ReferenceError 或数据非法，ECharts 整图渲染失败. '
            f'修复：写 HTML 前用 pandas 处理：df.replace([np.inf, -np.inf], np.nan).fillna(None) '
            f'或 JSON 序列化时显式转 null（不要用 str(NaN) / repr(np.nan) 拼字符串）'
        )

    # 3. JS 代码中 Python 类型字面量泄漏（None / Timestamp(...) / Period(...) / datetime(...)）
    # 实测案例：
    #   case_032: data: [None, 12, ...] → 浏览器抛 "None is not defined"，整页空白
    #   case_t01: x: Timestamp('2024-01-01') → "Timestamp is not defined"
    #   case_066: x: Period('2024Q1') → "Period is not defined"
    # 严格限定上下文：必须在 JS 块内 + 数组/对象上下文（[,{:] 后），避免误伤合法 JS 标识符
    py_literal_hits = []
    # None: 数组/对象元素位置的裸 None（JS 应写 null）
    py_none_pat = re.compile(r'[\[,{:]\s*None(?=\s*[,\]}])')
    # Timestamp / Period / datetime / Decimal: 这些是 Python 类调用 repr，JS 中绝不会合法出现
    py_class_pat = re.compile(
        r'(?:Timestamp|Period|datetime|Decimal|numpy\.\w+|np\.\w+)\s*\('
    )
    for block in js_blocks:
        no_line_cmt = re.sub(r'//[^\n]*', '', block)
        no_block_cmt = re.sub(r'/\*[\s\S]*?\*/', '', no_line_cmt)
        # 去 JS 字符串字面量（避免误伤如 "Period from 2024"）
        no_str = re.sub(r"""'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|`(?:\\.|[^`\\])*`""",
                        '""', no_block_cmt)
        for m in py_none_pat.findall(no_str):
            py_literal_hits.append(('None', m.strip(' ,[{:')))
        for m in py_class_pat.findall(no_str):
            py_literal_hits.append(('python-class-call', m.strip()))
    if py_literal_hits:
        samples = py_literal_hits[:5]
        errors.append(
            f'JS 代码中含 Python 字面量/类调用残留（运行时 ReferenceError, 整页 ECharts 不渲染）: '
            f'{", ".join(f"{lbl}={repr(s)}" for lbl, s in samples)}'
            f'{"；共 " + str(len(py_literal_hits)) + " 处" if len(py_literal_hits) > 5 else ""}. '
            f'修复：序列化时用 json.dumps(default=str) 或显式 .isoformat() / None→null / Decimal→float'
        )

    return errors, warnings


def _check_echarts_empty_data(html):
    """Detect ECharts chart 配置中 data: [] / null / undefined — 典型白图根因。

    实测案例：case_076 series data: []（白图）, case_071 data: null（Top10 白图）。
    上下文限定：仅在含 'echarts' 标识的 <script> 块内检测，避免误伤普通 JS。

    升级为 error：静态空数组等价于"图表不会渲染"，是产物可交付性硬问题；
    真实"无数据" 场景应在 HTML 显示占位文案（"暂无数据" / "—"），而非留空 chart。
    精准率实测：217 HTML 全量 0 误报。

    Returns (errors, warnings)。
    """
    errors = []
    warnings = []
    js_blocks = re.findall(r'<script[^>]*>([\s\S]*?)</script>', html, flags=re.IGNORECASE)
    data_empty_pat = re.compile(r'\bdata\s*:\s*(\[\s*\]|null|undefined)(?!\w)')
    total_hits = 0
    contexts = []
    for block in js_blocks:
        if 'echarts' not in block.lower():
            continue
        no_cmt = re.sub(r'//[^\n]*', '', block)
        no_cmt = re.sub(r'/\*[\s\S]*?\*/', '', no_cmt)
        no_str = re.sub(
            r"""'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|`(?:\\.|[^`\\])*`""",
            '""', no_cmt
        )
        for m in data_empty_pat.finditer(no_str):
            total_hits += 1
            start = max(0, m.start() - 40)
            ctx = no_str[start:m.end() + 20].replace('\n', ' ').strip()
            if len(contexts) < 3:
                contexts.append(ctx)
    if total_hits > 0:
        errors.append(
            f'ECharts 配置含 data: [] / null / undefined（图表必然白图，{total_hits} 处）. '
            f'示例: {contexts[0] if contexts else ""!r}'
            f'{"…（还有 " + str(total_hits - 1) + " 处）" if total_hits > 1 else ""}. '
            f'修复：序列化前确保 series.data / xAxis.data 非空；若数据真为空，'
            f'应在 HTML 显示"无数据"占位文案而非空 chart'
        )
    return errors, warnings


# ── ECharts series.data 全 0 检测（模型幻觉, groupby/pivot 算错填全零）──

def _check_echarts_all_zero_data(html):
    """Detect ECharts series.data arrays full of zeros — indicates model hallucination.

    场景: 模型用 pandas groupby/pivot 算品类×季度销售透视, 但计算逻辑错 (key 没对上 /
    fillna(0) 后没重算 / 直接 mock 0), 导致整个 chart 的所有 series.data 都填 [0, 0, ..., 0]。
    ECharts 渲染时有 series + init + data 长度对, 看起来"正常", 但 bar 全部 0 高度 = 空白图。

    精准设计（避免误报）:
      - 阈值: ≥3 个 series.data 数组全 0 才报 (单 series 全 0 可能合法, 如某品类无销售)
      - data 数组长度 ≥3 才查 (避免 2 项偶然全 0 误报)
      - 仅查 series 内 data, 不查 xAxis/yAxis category data

    Returns errors (升级 error: 用户看到空白图, 完全数据失实).
    """
    errors = []
    # series 数组内 "data": [0, 0, ..., 0]  (≥3 个 0)
    # 注意: 必须是数字 0 (不能是 "0" 字符串, 不能是 -0)
    all_zero_pat = re.compile(r'"data"\s*:\s*\[\s*0(?:\s*,\s*0){2,}\s*\]')
    matches = all_zero_pat.findall(html)
    if len(matches) >= 3:
        errors.append(
            f'ECharts 检测到 {len(matches)} 个 series.data 数组全为 0 — '
            f'渲染出空白图表 (有 series + init + data 但 bar 高度全 0). '
            f'可能成因 (实战观察): 数据 access 错 (字典层级/变量名/key 不匹配)/transform/.replace() 填充时用了错变量/原始数据真为零. '
            f'排查: print 写入 .replace()/json.dump 前的 stack_data 等 dict, 确认非零; '
            f'spot check 时除了对账 sum/total, 也要抽对账每个 chart 的 data 数组至少 1 个非零 cell'
        )
    return errors


# ── HTML structural basics ─────────────────────────────────────────────

def _check_html_basics(html):
    """Minimal HTML sanity checks."""
    errors = []
    warnings = []

    if not html or len(html) < 100:
        errors.append('HTML 内容为空或过短 (< 100 字节)')
        return errors, warnings

    if not re.search(r'<!DOCTYPE\s+html', html, re.IGNORECASE):
        warnings.append('HTML 缺少 <!DOCTYPE html> 声明')
    if '</html>' not in html.lower():
        errors.append('HTML 缺少 </html> 闭合标签')
    # 升级为 error: 中文报告 + 缺 charset 几乎必然乱码 (¥XX → ?XX, 中文 → 锟斤拷)
    if not re.search(r'charset\s*=\s*["\']?utf-?8', html, re.IGNORECASE):
        errors.append('HTML 缺少 UTF-8 charset 声明 (中文内容会乱码)')

    size_kb = len(html.encode('utf-8')) / 1024
    if size_kb > 10_240:
        warnings.append(f'HTML 文件过大: {size_kb:.0f}KB（建议 < 10MB）')

    return errors, warnings


# ── Main validate ──────────────────────────────────────────────────────

def validate_html_file(html_path, runtime: str = 'best-effort', runtime_timeout: float = 30.0):
    """Run all technical checks on an HTML file. Returns full validation dict.

    runtime:
      - 'off': 只跑静态校验，约 50ms
      - 'best-effort' (默认): 静态校验后追加无头浏览器真渲染校验；浏览器不可用则跳过
      - 'required': 同 best-effort 但无头浏览器不可用时整体标 fail
    runtime_timeout: best-effort/required 模式下真渲染校验的硬截止（秒）
    """
    path = Path(html_path).resolve()
    if not path.is_file():
        return {
            'ok': False,
            'file': str(path),
            'error_class': 'file_not_found',
            'human_summary': f'文件不存在: {path}',
        }

    html = path.read_text(encoding='utf-8', errors='replace')
    size_kb = path.stat().st_size / 1024

    errors = []
    warnings = []
    info = []  # 校验过程诊断信息 (环境/降级类), 不计入 ok 判定, 不算产物问题
    checks = {}

    # 1. HTML basics
    e, w = _check_html_basics(html)
    errors.extend(e)
    warnings.extend(w)
    checks['html'] = 'fail' if e else 'pass'

    # 2. Embedded JSON parsability (must come before JS so NaN in CHART_SPECS
    #    surfaces as JSON error rather than a JS syntax issue)
    json_errs, json_details = _check_json_parsable_in_html(html)
    errors.extend(json_errs)
    checks['json'] = 'fail' if json_errs else 'pass'

    # 3. Inline JS syntax (node --check)
    js_blocks = _extract_js_blocks(html)
    js_err_list = []
    if js_blocks:
        node_errs, used_node = _check_js_node(js_blocks)
        if used_node:
            js_err_list = node_errs
        else:
            # 降级提示: 校验工具自身能力问题, 不是产物问题 → info 而非 warning
            info.append('node 不可用，JS 校验降级为括号匹配 (校验过程信息，非产物问题)')
            js_err_list = _check_js_brackets(js_blocks)
    errors.extend(js_err_list)
    checks['js'] = 'fail' if js_err_list else 'pass'

    # 4. ECharts library available
    ec_errs, ec_warns = _check_echarts_available(html)
    errors.extend(ec_errs)
    warnings.extend(ec_warns)
    checks['echarts'] = 'fail' if ec_errs else 'pass'

    # 5. Chart DOM id consistency
    dom_errs = _check_dom_id_consistency(html)
    errors.extend(dom_errs)
    checks['dom_ids'] = 'fail' if dom_errs else 'pass'

    # 6. f-string residuals
    fs_errs, fs_warns = _check_fstring_residuals(html)
    errors.extend(fs_errs)
    warnings.extend(fs_warns)
    checks['fstring'] = 'fail' if (fs_errs or fs_warns) else 'pass'

    # 7. inf/Infinity/NaN literal residuals（HTML 文本 + JS 数据）
    # JS 数组/对象内的裸字面量 → error（运行时崩）；HTML 文本 ¥inf → warning（用户可见）
    num_errs, num_warns = _check_numeric_literal_residuals(html)
    errors.extend(num_errs)
    warnings.extend(num_warns)
    checks['numeric_literal'] = 'fail' if (num_errs or num_warns) else 'pass'

    # 7.5 未渲染的 __XXX__ 模板占位符（.replace 漏写, 用户看到字面量）
    ph_errs = _check_unrendered_placeholders(html)
    errors.extend(ph_errs)
    checks['unrendered_placeholders'] = 'fail' if ph_errs else 'pass'

    # 8. ECharts empty data: [] / null / undefined（白图根因，升级 error）
    ec_empty_errs, ec_empty_warns = _check_echarts_empty_data(html)
    errors.extend(ec_empty_errs)
    warnings.extend(ec_empty_warns)
    checks['echarts_empty_data'] = 'fail' if (ec_empty_errs or ec_empty_warns) else 'pass'

    # 8.5 ECharts series.data 全 0（模型 pivot/groupby 算错填全零, 渲染空白图）
    ec_zero_errs = _check_echarts_all_zero_data(html)
    errors.extend(ec_zero_errs)
    checks['echarts_all_zero_data'] = 'fail' if ec_zero_errs else 'pass'

    static_ok = not errors

    # ── 9. 真渲染校验（runtime != 'off'）────────────────────────────────
    runtime_result = None
    if runtime in ('best-effort', 'required'):
        # 仅在静态通过时跑：静态已 fail 则真渲染加再多错也是噪声
        if static_ok:
            try:
                from browser_check import run_browser_check, get_locate_diag
            except ImportError as e:
                runtime_result = {'unavailable': True, 'reason': f'browser_check import 失败: {e}'}
            else:
                rt = run_browser_check(str(path), timeout=runtime_timeout)
                if rt is None:
                    # 降级:reason 给模型看的简短一句,详细诊断进 locate_diag (开发者看)
                    diag = get_locate_diag()
                    # 简短 reason:模型只需要知道"已降级",不需要看 candidate 细节
                    if any(d.get("status") == "browser_launch_failed" for d in diag):
                        reason = "无头浏览器启动失败,已降级为静态校验"
                    elif diag:
                        reason = "无头浏览器不可用,已降级为静态校验"
                    else:
                        reason = "无头浏览器不可用（playwright 未安装）,已降级为静态校验"
                    runtime_result = {
                        'unavailable': True,
                        'reason': reason,
                        'locate_diag': diag,  # 完整诊断保留,开发者排查时看
                    }
                else:
                    runtime_result = rt
                    # runtime errors（参与 ok 判定）和 warnings（仅提示）分开合并
                    for issue in rt.get('issues', []):
                        errors.append(f'[runtime] {issue}')
                    for w in rt.get('warnings', []):
                        warnings.append(f'[runtime] {w}')
                    checks['runtime_render'] = 'fail' if rt.get('issues') else 'pass'
        else:
            runtime_result = {'skipped': True, 'reason': '静态校验已 fail，跳过真渲染'}

        # required 模式下无头浏览器不可用 → 整体 fail
        if runtime == 'required' and runtime_result and runtime_result.get('unavailable'):
            errors.append(f"[runtime-required] {runtime_result['reason']}")
            checks['runtime_render'] = 'fail'

    ok = not errors
    result = {
        'ok': ok,
        'file': str(path),
        'file_size_kb': round(size_kb, 1),
        'validation': {
            'errors': errors,
            'warnings': warnings,
            'info': info,  # 校验过程诊断信息 (环境/降级), 不计 ok
            'checks': checks,
        },
        'human_summary': _summary_text(ok, errors, warnings, info, checks),
        'details': {
            'json_blocks_checked': json_details.get('json_blocks_checked', 0),
            'chart_specs_found': json_details.get('chart_specs_found', False),
            'js_blocks': len(js_blocks),
        },
    }
    if runtime_result is not None:
        result['runtime'] = runtime_result
    return result


def _summary_text(ok, errors, warnings, info, checks):
    pass_count = sum(1 for v in checks.values() if v == 'pass')
    total = len(checks)
    status = '校验通过' if ok else '校验失败'
    parts = [f'{status} ({pass_count}/{total} 项通过, {len(errors)} 错误, {len(warnings)} 警告)']
    if info:
        parts[0] = parts[0].rstrip(')') + f', {len(info)} 诊断)'
    if errors:
        parts.append(f'首个错误: {errors[0][:150]}')
    return ' — '.join(parts)


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='HTML report technical validator (lean)',
        epilog=(
            'Checks that the HTML report is technically sound:\n'
            '  - HTML basics (DOCTYPE, </html>, charset)\n'
            '  - Inline JS syntax via `node --check`\n'
            '  - Embedded JSON parsable (no NaN/Infinity)\n'
            '  - ECharts library available when echarts.* is called\n'
            '  - Chart DOM id consistency\n'
            '  - No Python f-string residuals in visible text\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--validate-html', required=True,
                        help='Path to the HTML file to validate')
    parser.add_argument('--strict', action='store_true',
                        help='Treat warnings as errors (ok=false if any warning)')
    parser.add_argument('--runtime', choices=['off', 'best-effort', 'required'],
                        default='best-effort',
                        help=('Append headless-browser real-render check after static checks. '
                              'off: static only (~50ms). '
                              'best-effort (default): try headless browser, skip if unavailable (~7s). '
                              'required: fail if headless browser unavailable.'))
    parser.add_argument('--runtime-timeout', type=float, default=30.0,
                        help='Hard deadline (seconds) for the runtime check (default 30)')
    args = parser.parse_args()

    result = validate_html_file(
        args.validate_html,
        runtime=args.runtime,
        runtime_timeout=args.runtime_timeout,
    )

    if args.strict and result.get('ok') and result.get('validation', {}).get('warnings'):
        result['ok'] = False
        result['human_summary'] += '（--strict 模式：warning 升级为 error）'

    _v = _skill_version()
    if _v: result['skill_version'] = _v
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get('ok') else 1)


if __name__ == '__main__':
    main()
