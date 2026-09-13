#!/usr/bin/env python3
"""
主持手卡 HTML → PDF 转换脚本。

默认生成 A4 竖版拼版 PDF（每页上下两张 A5 横卡，中间有裁切线），与目标样例一致；
也支持 A5 单页 HTML（每页一张 A5 横卡）。脚本会自动尊重 HTML 中的 @page size 设置。

用法:
    python generate_pdf.py <输入.html> <输出.pdf>

依赖:
    系统安装有 Microsoft Edge 或 Google Chrome（无需额外 Python 库）。
    输入 HTML 需包含 @page size 设置（A4 portrait 或 A5 landscape），背面图与 HTML 同目录。

注意:
    必须使用旧版 --headless（非 --headless=new），新版 headless 不尊重 @page 尺寸，
    会导致 PDF 页面大小错误（内容只占页面上半，下方空白）。

示例:
    python generate_pdf.py 主持人手卡_A4拼版.html 主持人手卡.pdf
"""
import subprocess
import sys
import os

# 按优先级查找浏览器（Edge 优先，中文渲染更稳定）
BROWSER_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser():
    """返回第一个存在的浏览器路径，找不到返回 None。"""
    for p in BROWSER_PATHS:
        if os.path.exists(p):
            return p
    return None


def html_to_pdf(html_path, pdf_path):
    browser = find_browser()
    if not browser:
        print("错误：未找到 Edge 或 Chrome 浏览器。请安装 Edge 或 Chrome 后重试。", file=sys.stderr)
        sys.exit(1)

    html_abs = os.path.abspath(html_path)
    pdf_abs = os.path.abspath(pdf_path)

    if not os.path.exists(html_abs):
        print(f"错误：输入文件不存在: {html_abs}", file=sys.stderr)
        sys.exit(1)

    # 确保输出目录存在
    out_dir = os.path.dirname(pdf_abs)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # file:// URL，Windows 路径反斜杠转正斜杠
    url = "file:///" + html_abs.replace("\\", "/")

    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_abs}",
        url,
    ]

    print(f"浏览器 : {browser}")
    print(f"输入   : {html_abs}")
    print(f"输出   : {pdf_abs}")
    print("正在生成 PDF...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"浏览器返回错误码: {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(f"stderr: {result.stderr[:500]}", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(pdf_abs) and os.path.getsize(pdf_abs) > 0:
        size_kb = os.path.getsize(pdf_abs) / 1024
        print(f"成功！PDF 已生成: {pdf_abs} ({size_kb:.1f} KB)")
    else:
        print("错误：PDF 文件未生成或为空。", file=sys.stderr)
        print("提示：请检查 HTML 中引用的背面图是否与 HTML 在同一目录。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python generate_pdf.py <输入.html> <输出.pdf>")
        print("示例: python generate_pdf.py 主持人手卡_A5.html 主持人手卡.pdf")
        sys.exit(1)
    html_to_pdf(sys.argv[1], sys.argv[2])
