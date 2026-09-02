#!/usr/bin/env python3
"""
PDF 校验器
==========
执行 5 项校验：
1. LOGO 校验（封面 + 正文页眉）
2. 分页校验（页数合理区间）
3. 布局校验（无空页）
4. 承接页页眉校验
5. 封面干净度校验

用法::

    from pdf_validator import validate_pdf
    result = validate_pdf("~/RetailAnalysis/output/报告.pdf", logo_base64="...")
    assert result["passed"]
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PIL import Image


def pdf_to_images(pdf_path: str, dpi: int = 150) -> list[Image.Image]:
    """将 PDF 转为 PIL Image 列表（使用 pdftoppm）。"""
    import tempfile

    pdf_path = Path(pdf_path).expanduser()
    with tempfile.TemporaryDirectory() as tmpdir:
        # pdftoppm -png -r 150 input.pdf output_prefix
        prefix = f"{tmpdir}/page"
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), prefix],
            check=True,
            capture_output=True,
        )
        pages = []
        for f in sorted(Path(tmpdir).glob("page-*.png")):
            pages.append(Image.open(f))
        return pages


def non_white_ratio(img: Image.Image, region: Optional[tuple] = None) -> float:
    """计算非白像素比例。region=(left, top, right, bottom)"""
    if region:
        left, top, right, bottom = region
        img = img.crop((left, top, right, bottom))

    # 转为 RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    pixels = list(img.getdata())
    if not pixels:
        return 0.0

    non_white = 0
    for r, g, b in pixels:
        # 近似白色阈值
        if r < 250 or g < 250 or b < 250:
            non_white += 1

    return non_white / len(pixels)


def get_pdf_info(pdf_path: str) -> dict:
    """使用 pdfinfo 获取 PDF 信息。"""
    try:
        result = subprocess.run(
            ["pdfinfo", str(Path(pdf_path).expanduser())],
            capture_output=True,
            text=True,
            check=True,
        )
        info = {}
        for line in result.stdout.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip()
        return info
    except Exception as e:
        return {"error": str(e)}


def validate_pdf(
    pdf_path: str,
    *,
    logo_base64: str = "",
    min_pages: int = 8,
    max_pages: int = 30,
    output_check_dir: Optional[str] = None,
) -> dict:
    """
    执行 5 项校验。

    参数:
        pdf_path: PDF 文件路径
        logo_base64: LOGO base64（用于页眉校验）
        min_pages: 最小页数
        max_pages: 最大页数
        output_check_dir: 校验截图输出目录

    返回:
        {"passed": bool, "checks": [{"name": str, "passed": bool, "detail": str}, ...]}
    """
    pdf_path = Path(pdf_path).expanduser()
    checks = []
    all_passed = True

    # 准备截图目录
    if output_check_dir:
        check_dir = Path(output_check_dir).expanduser()
        check_dir.mkdir(parents=True, exist_ok=True)
    else:
        check_dir = None

    # 转为图片
    try:
        pages = pdf_to_images(str(pdf_path))
    except Exception as e:
        return {
            "passed": False,
            "checks": [{"name": "PDF 转图片", "passed": False, "detail": str(e)}],
        }

    if not pages:
        return {
            "passed": False,
            "checks": [{"name": "PDF 页数", "passed": False, "detail": "无法提取页面"}],
        }

    # ① LOGO 校验
    # 封面顶部偏中区 (0, 10%H, 60%W, 30%H)
    cover = pages[0]
    w, h = cover.size
    cover_region = (0, int(h * 0.1), int(w * 0.6), int(h * 0.4))
    cover_ratio = non_white_ratio(cover, cover_region)
    cover_logo_pass = cover_ratio >= 0.01
    checks.append({
        "name": "① 封面 LOGO",
        "passed": cover_logo_pass,
        "detail": f"非白像素比例: {cover_ratio:.2%} (阈值 1%)",
    })
    if not cover_logo_pass:
        all_passed = False

    # 正文首页页眉左上 (0, 0, 300px, 100px) —— 按 DPI 150，约 2in = 300px
    if len(pages) > 1:
        body_first = pages[1]
        header_region = (0, 0, min(300, body_first.width), min(100, body_first.height))
        header_ratio = non_white_ratio(body_first, header_region)
        header_logo_pass = header_ratio >= 0.005
        checks.append({
            "name": "① 正文页眉 LOGO",
            "passed": header_logo_pass,
            "detail": f"非白像素比例: {header_ratio:.2%} (阈值 0.5%)",
        })
        if not header_logo_pass:
            all_passed = False
    else:
        checks.append({"name": "① 正文页眉 LOGO", "passed": False, "detail": "无正文页"})
        all_passed = False

    # ② 分页校验
    info = get_pdf_info(str(pdf_path))
    try:
        page_count = int(info.get("Pages", len(pages)))
    except ValueError:
        page_count = len(pages)

    page_pass = min_pages <= page_count <= max_pages
    checks.append({
        "name": "② 分页校验",
        "passed": page_pass,
        "detail": f"页数: {page_count} (期望 [{min_pages}, {max_pages}])",
    })
    if not page_pass:
        all_passed = False

    # ③ 布局校验（逐页非白像素 < 0.5% 视为空页）
    empty_pages = []
    for i, page in enumerate(pages):
        ratio = non_white_ratio(page)
        if ratio < 0.005:
            empty_pages.append(i + 1)

    layout_pass = len(empty_pages) == 0
    checks.append({
        "name": "③ 布局校验（空页检测）",
        "passed": layout_pass,
        "detail": f"空页: {empty_pages if empty_pages else '无'}",
    })
    if not layout_pass:
        all_passed = False

    # ④ 承接页页眉校验（跳过封面，每页顶部 0~130px 非全白）
    header_missing_pages = []
    for i, page in enumerate(pages[1:], start=2):  # 从第 2 页开始
        header_h = min(130, page.height)
        ratio = non_white_ratio(page, (0, 0, page.width, header_h))
        if ratio < 0.005:
            header_missing_pages.append(i)

    header_pass = len(header_missing_pages) == 0
    checks.append({
        "name": "④ 承接页页眉校验",
        "passed": header_pass,
        "detail": f"缺失页眉页: {header_missing_pages if header_missing_pages else '无'}",
    })
    if not header_pass:
        all_passed = False

    # ⑤ 封面干净度校验（顶部 0~80px 中部 20%~70% 非白像素 ≤ 5%）
    clean_region = (
        int(w * 0.2), 0,
        int(w * 0.7), min(80, h)
    )
    clean_ratio = non_white_ratio(cover, clean_region)
    clean_pass = clean_ratio <= 0.05
    checks.append({
        "name": "⑤ 封面干净度",
        "passed": clean_pass,
        "detail": f"非白像素比例: {clean_ratio:.2%} (阈值 5%)",
    })
    if not clean_pass:
        all_passed = False

    # 保存校验截图
    if check_dir:
        # 封面区域截图
        cover.crop(cover_region).save(check_dir / "check_cover_logo.png")
        if len(pages) > 1:
            body_first.crop(header_region).save(check_dir / "check_header_logo.png")

    return {"passed": all_passed, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="PDF 校验器")
    parser.add_argument("pdf", help="PDF 文件路径")
    parser.add_argument("--min-pages", type=int, default=8, help="最小页数")
    parser.add_argument("--max-pages", type=int, default=30, help="最大页数")
    parser.add_argument("--output-check-dir", help="校验截图输出目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    result = validate_pdf(
        args.pdf,
        min_pages=args.min_pages,
        max_pages=args.max_pages,
        output_check_dir=args.output_check_dir,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"校验结果: {'通过' if result['passed'] else '未通过'}")
        for check in result["checks"]:
            status = "✓" if check["passed"] else "✗"
            print(f"  {status} {check['name']}: {check['detail']}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
