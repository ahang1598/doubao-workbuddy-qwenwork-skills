#!/usr/bin/env python3
"""linkfox-report-generator · HTML 片段 → 模板注入 → 落盘。

读入调用方按 SKILL.md 产出的 HTML 片段文件，做机械替换：
  - 加载 assets/template-analysis.html
  - 从片段提取 ECHARTS_SCRIPTS / CANVAS_SCRIPTS 块 → 注入模板底部 marker
  - 主 content → CONTENT_START/END 之间
  - 替换 {{TITLE}} / {{LANG}}
  - report-meta 尾部追加"生成时间"
  - 写到 <root>/<YYYY-MM-DD>/<session>/reports/<slug>-<ts_us>.html
  - stdout: {"path", "bytes", "language", "title"}

CLI：
  python scripts/inject_report.py \
    --content-file <path>            # 必填。HTML 片段文件
    --language <zh|en|ja|ko>         # 必填。写入 <html lang=...>
    [--title <english-slug>]         # 可选。文件名前缀，仅 [a-zA-Z-]

退出码：0 成功；64 CLI 用法错；1 文件缺失；2 模板缺失；3 片段为空；4 写盘失败。
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
TEMPLATE_PATH = os.path.join(SKILL_ROOT, "assets", "template-analysis.html")

# --language 唯一取值
ALLOWED_LANGUAGES = {"zh", "en", "ja", "ko"}

# --title 只允许 26 英文字母和 -（跟旧脚本一致：数字/下划线/中文/空格都不行）
_TITLE_ALLOWED_RE = re.compile(r"^[a-zA-Z-]+$")

_ECHARTS_BLOCK_RE = re.compile(
    r"<!--\s*ECHARTS_SCRIPTS\s*-->([\s\S]*?)<!--\s*/ECHARTS_SCRIPTS\s*-->",
    re.IGNORECASE,
)
_CANVAS_BLOCK_RE = re.compile(
    r"<!--\s*CANVAS_SCRIPTS\s*-->([\s\S]*?)<!--\s*/CANVAS_SCRIPTS\s*-->",
    re.IGNORECASE,
)

# 去掉模型偶尔会给的 ```html / ```markdown 外围代码围栏
_OUTER_FENCE_RE = re.compile(r"^\s*```(?:html|md|markdown)?\s*\n([\s\S]*?)\n```\s*$", re.IGNORECASE)

_SCRIPT_OPEN_RE = re.compile(r"</?script[^>]*>", re.IGNORECASE)


USAGE_TEXT = (
    "Usage:\n"
    "  inject_report.py --content-file <path> --language <zh|en|ja|ko> [--title <english-slug>]\n"
    "\n"
    "  --content-file : HTML 片段文件（从 .report-header 到 .report-footer）\n"
    "  --language     : 报告主体阅读者语言，写入 <html lang=...>\n"
    "  --title        : 文件名前缀，仅 [a-zA-Z-]，不传用默认\n"
)


def _die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def _parse_cli() -> dict:
    args = sys.argv[1:]

    # 阻挡 stdin / argv 内联 JSON 之类的坏姿势（shell 转义 / argv 长度容易踩坑）
    if len(args) == 1 and (args[0] == "-" or args[0].lstrip().startswith(("{", "["))):
        print("ERROR: 不接受 stdin / argv 内联 JSON。请用 --content-file 传路径。\n", file=sys.stderr)
        print(USAGE_TEXT, file=sys.stderr)
        sys.exit(64)

    parsed = {"content_file": None, "language": None, "title": None}
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-h", "--help"):
            print(USAGE_TEXT)
            sys.exit(0)
        elif a == "--content-file":
            if i + 1 >= len(args):
                _die("--content-file 需要一个路径参数", 64)
            parsed["content_file"] = args[i + 1]; i += 2
        elif a == "--language":
            if i + 1 >= len(args):
                _die("--language 需要一个语言代码参数", 64)
            parsed["language"] = args[i + 1]; i += 2
        elif a == "--title":
            if i + 1 >= len(args):
                _die("--title 需要一个字符串参数", 64)
            parsed["title"] = args[i + 1]; i += 2
        else:
            print(f"ERROR: 未识别的参数：{a}\n", file=sys.stderr)
            print(USAGE_TEXT, file=sys.stderr)
            sys.exit(64)

    if not parsed["content_file"]:
        print("ERROR: --content-file 必填。\n", file=sys.stderr)
        print(USAGE_TEXT, file=sys.stderr)
        sys.exit(64)
    if not parsed["language"]:
        print(f"ERROR: --language 必填，取值 {sorted(ALLOWED_LANGUAGES)}。\n", file=sys.stderr)
        print(USAGE_TEXT, file=sys.stderr)
        sys.exit(64)
    if parsed["language"] not in ALLOWED_LANGUAGES:
        _die(f"--language 只允许 {sorted(ALLOWED_LANGUAGES)}，当前值：{parsed['language']!r}", 64)
    if parsed["title"] is not None and not _TITLE_ALLOWED_RE.match(parsed["title"]):
        _die(f"--title 只允许 26 个英文字母和 -（正则 ^[a-zA-Z-]+$），当前值：{parsed['title']!r}", 64)

    return parsed


def _read_content(path: str) -> str:
    if not os.path.isfile(path):
        _die(f"--content-file 指向的文件不存在：{path}", 1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        _die(f"读 --content-file 失败：{e}", 1)
    # 兜底：片段偶尔被 ```html ... ``` 代码围栏包一层，剥掉
    m = _OUTER_FENCE_RE.match(text)
    if m:
        text = m.group(1)
    text = text.strip()
    if not text:
        _die("--content-file 内容为空。", 3)
    return text


def _load_template() -> str:
    if not os.path.isfile(TEMPLATE_PATH):
        _die(f"模板缺失：{TEMPLATE_PATH}", 2)
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _resolve_out_path(title: str | None, ts: float) -> str:
    """落到 <root>/<YYYY-MM-DD>/<session>/reports/<slug>-<ts_us>.html。

    共享层 resolve_report_path 会做 mkdir + 四级根目录降级（ACPX_WORKSPACES /
    cwd / ~/linkfox / $TMPDIR/linkfox）+ 微秒时间戳避免同秒碰撞。title 空串时
    共享层用 fallback 'linkfox-report'。
    """
    sys.path.insert(0, os.path.join(SKILL_ROOT, "..", "_shared"))
    from linkfox_paths import resolve_report_path  # type: ignore
    return resolve_report_path((title or "").strip(), ts, "html")


def _inject(template: str, content: str, title: str | None, language: str) -> str:
    # 1. 提取 ECharts / Canvas 块（片段里可以有 0 或 1 段，多段会用第一段 —— 与旧脚本一致）
    echarts_code = ""
    m = _ECHARTS_BLOCK_RE.search(content)
    if m:
        echarts_code = m.group(1).strip()
        echarts_code = _SCRIPT_OPEN_RE.sub("", echarts_code)
        content = _ECHARTS_BLOCK_RE.sub("", content).strip()

    canvas_code = ""
    m = _CANVAS_BLOCK_RE.search(content)
    if m:
        canvas_code = m.group(1).strip()
        canvas_code = _SCRIPT_OPEN_RE.sub("", canvas_code)
        content = _CANVAS_BLOCK_RE.sub("", content).strip()

    # 2. 替换文档级占位符
    html = template.replace("{{TITLE}}", title or "LinkFox Analysis Report")
    html = html.replace("{{LANG}}", language)

    # 3. 主 content 注入 CONTENT_START/END 之间
    html = re.sub(
        r"<!--\s*CONTENT_START\s*-->.*?<!--\s*CONTENT_END\s*-->",
        "<!-- CONTENT_START -->\n" + content + "\n<!-- CONTENT_END -->",
        html,
        flags=re.DOTALL,
    )

    # 4. ECharts / Canvas 初始化代码分别塞进模板底部对应 marker
    if echarts_code:
        html = html.replace(
            "// ECHARTS_INIT_START\n    // ECHARTS_INIT_END",
            "// ECHARTS_INIT_START\n    " + echarts_code + "\n    // ECHARTS_INIT_END",
        )
    if canvas_code:
        html = html.replace(
            "// CANVAS_INIT_START\n    // CANVAS_INIT_END",
            "// CANVAS_INIT_START\n    " + canvas_code + "\n    // CANVAS_INIT_END",
        )

    # 5. 去片段里可能手写的"生成日期: YYYY-MM-DD"，报告 meta 尾部追加"生成时间：<北京时间>"
    beijing_tz = timezone(timedelta(hours=8))
    now_str = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    html = re.sub(r"生成日期\s*[:：]\s*[\d\-]+\s*[·\xb7]?\s*", "", html)
    html = re.sub(
        r'(class="report-meta"[^>]*>)([\s\S]*?)(</div>)',
        lambda m: m.group(1) + m.group(2).rstrip() + " · 生成时间：" + now_str + m.group(3),
        html,
        count=1,
    )

    return html


def main() -> None:
    # 行缓冲：run_in_background 时 stdout 被重定向到文件，块缓冲会让唯一那行结果 JSON 滞留
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    args = _parse_cli()
    content = _read_content(args["content_file"])
    template = _load_template()

    ts = time.time()
    out_path = os.path.abspath(_resolve_out_path(args["title"], ts))

    final_html = _inject(template, content, args["title"], args["language"])

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_html)
    except OSError as e:
        _die(f"写报告失败 {out_path}: {e}", 4)

    summary = {
        "path": out_path,
        "bytes": len(final_html.encode("utf-8")),
        "language": args["language"],
        "title": args["title"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved full response: {out_path} ({summary['bytes']} bytes)")


if __name__ == "__main__":
    main()
