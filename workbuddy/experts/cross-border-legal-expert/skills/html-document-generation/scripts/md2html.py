#!/usr/bin/env python3
"""Markdown → HTML 标准转换流程（Richee 设计系统）。

6 个模板按场景选择：
  report   — 全面报告（法律研究/尽调/案件分析）  默认
  opinion  — 意见书/备忘录
  brief    — 简报/快讯
  letter   — 律师函/催告函
  pleading — 法定文书（起诉状/申请书/答辩状）
  form     — 法定表格（官方表格填充）

用法：
    python md2html.py input.md                                   # 默认 report 模板
    python md2html.py input.md --template opinion --title "法律意见书"
    python md2html.py input.md --template pleading --title "民事起诉状" --court "杭州市中级人民法院" --signer "张三"
    python md2html.py input.md --template form --title "企业登记申请表" --signer "李四" --date "2026-07-28"
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR
SHARED_CSS = TEMPLATES_DIR / "shared.css"

# 模板别名 → 文件名
TEMPLATE_MAP = {
    "report": "template-report.html",
    "opinion": "template-opinion.html",
    "brief": "template-brief.html",
    "letter": "template-letter.html",
    "pleading": "template-pleading.html",
    "form": "template-form.html",
}
DEFAULT_TEMPLATE = TEMPLATE_MAP["report"]
DEFAULT_FILTER = SCRIPT_DIR / "markdown-to-html.lua"


def resolve_template(name_or_path: str) -> Path:
    """支持别名（report/opinion/brief/letter）或文件路径。"""
    if name_or_path in TEMPLATE_MAP:
        return TEMPLATES_DIR / TEMPLATE_MAP[name_or_path]
    path = Path(name_or_path).expanduser()
    for candidate in (path, TEMPLATES_DIR / name_or_path):
        if candidate.is_file():
            return candidate
    return path


def run_pandoc(input_path: Path, output_path: Path, template: Path,
               lua_filter: Path | None, metadata: dict[str, str],
               toc: bool, standalone: bool) -> None:
    cmd = [
        "pandoc",
        str(input_path),
        "-t", "html",
        "-s",
        "--template", str(template),
        "-o", str(output_path),
    ]

    # 注入共享 CSS
    if SHARED_CSS.is_file():
        cmd += ["--include-in-header", str(SHARED_CSS)]

    if lua_filter and lua_filter.is_file():
        cmd += ["--lua-filter", str(lua_filter)]

    if toc:
        cmd += ["--toc", "--toc-depth=3"]

    if standalone:
        cmd += ["--embed-resources", "--standalone"]

    for key, value in metadata.items():
        if value:
            cmd += ["--metadata", f"{key}={value}"]

    cmd += ["--metadata", "lang=zh-CN"]

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("Pandoc 未找到，请安装或加入 PATH。", file=sys.stderr)
        raise SystemExit(127)
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Markdown → HTML 标准转换（Richee 设计系统，4 模板）",
    )
    parser.add_argument("input", help="输入 Markdown 文件")
    parser.add_argument("-o", "--output", help="输出 HTML 路径，默认同输入文件名")
    parser.add_argument("--template", default="report",
                        help="模板：report(默认)/opinion/brief/letter 或自定义路径")
    # 通用元数据
    parser.add_argument("--title", default="", help="报告标题")
    parser.add_argument("--report-no", default="", help="报告编号")
    parser.add_argument("--date", default="", help="日期")
    parser.add_argument("--disclaimer", action="store_true", help="追加 AI 免责声明")
    parser.add_argument("--toc", action="store_true", help="生成目录（仅 report 模板有效）")
    parser.add_argument("--standalone", action="store_true",
                        help="内联 CSS/图片为单文件")
    parser.add_argument("--filter", dest="lua_filter", default=str(DEFAULT_FILTER),
                        help="Lua 过滤器（传 none 跳过）")
    # report 专用
    parser.add_argument("--subtitle", default="", help="副标题（report）")
    parser.add_argument("--status", default="", help="顶栏状态（report）")
    parser.add_argument("--pills", default="", help="元数据标签 HTML（report）")
    parser.add_argument("--footer", default="", help="页脚文字（report）")
    # opinion/letter 专用
    parser.add_argument("--addressee", default="", help="致/收件人（opinion/letter）")
    parser.add_argument("--firm", default="", help="律所名称（opinion/letter）")
    parser.add_argument("--lawyer", default="", help="经办律师（opinion）")
    parser.add_argument("--cc", default="", help="抄送（letter）")
    # pleading/form 专用
    parser.add_argument("--court", default="", help="受理法院（pleading）")
    parser.add_argument("--signer", default="", help="具状人/填表人（pleading/form）")
    parser.add_argument("--parties", default="", help="当事人信息 HTML（pleading）")
    parser.add_argument("--form-no", default="", help="表格编号（form）")
    parser.add_argument("--form-note", default="", help="填表说明（form）")
    # 通用
    parser.add_argument("--author", default="", help="作者（brief）")
    args = parser.parse_args(argv)

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        print(f"输入文件不存在: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output).expanduser() if args.output else input_path.with_suffix(".html")
    template_path = resolve_template(args.template)
    lua_filter_path = None if args.lua_filter == "none" else Path(args.lua_filter).expanduser()

    # 构建元数据
    metadata: dict[str, str] = {"title": args.title or input_path.stem}
    for key in ("subtitle", "report_no", "status", "pills", "footer",
                "date", "addressee", "firm", "lawyer", "cc", "author",
                "court", "signer", "parties", "form_no", "form_note"):
        val = getattr(args, key.replace("-", "_"), "")
        if val:
            metadata[key.replace("_", "-")] = val
    if args.disclaimer:
        metadata["disclaimer"] = "true"

    run_pandoc(input_path, output_path, template_path, lua_filter_path,
               metadata, args.toc, args.standalone)

    print(f"已生成: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
