#!/usr/bin/env python3
"""
P0 VIS 资产构建器
================
自动化执行 P0-1 ~ P0-4：
1. 渲染年报封面/目录/财务页（pdftocairo）
2. 提取 LOGO（pdfimages + Pillow）
3. 提取主色/辅色（Pillow 像素分析）
4. 固化 palette.json

用法::

    python vis_asset_builder.py --annual-report ~/RetailAnalysis/report_assets/annual_report/中信_2025_annual_report.pdf --bank 中信

"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image

# 优先使用同级 paths.py
sys.path.insert(0, str(Path(__file__).parent))
from paths import (
    ANNUAL_REPORT_DIR,
    REPORT_ASSETS_DIR,
    LOGO_BASE64,
    LOGO_DIR,
    LOGO_PNG,
    LOGO_SOURCE,
    PALETTE_JSON,
    VIS_DIR,
    ensure_dirs,
)


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """执行 shell 命令。"""
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def render_pages(pdf_path: str, output_dir: str) -> list[str]:
    """P0-2: 用 pdftocairo 渲染封面、目录、财务页。"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 渲染前 3 页（封面、目录、财务数据页）
    cmd = [
        "pdftocairo", "-png", "-r", "300",
        "-f", "1", "-l", "3",
        pdf_path, str(out_dir / "page")
    ]
    run(cmd)

    files = sorted(out_dir.glob("page-*.png"))
    # 重命名
    renamed = []
    mapping = {0: "cover", 1: "toc", 2: "finance"}
    for i, f in enumerate(files[:3]):
        name = mapping.get(i, f"page_{i}")
        dest = out_dir / f"{name}-300dpi.png"
        shutil.move(str(f), str(dest))
        renamed.append(str(dest))
    # 清理多余文件
    for f in files[3:]:
        f.unlink(missing_ok=True)

    return renamed


def extract_logo(pdf_path: str, output_dir: str) -> dict:
    """P0-3: 提取 LOGO。"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 尝试 pdfimages 提取第一页所有图片
    with tempfile.TemporaryDirectory() as tmpdir:
        run(["pdfimages", "-all", "-f", "1", "-l", "1", pdf_path, f"{tmpdir}/img"])
        imgs = sorted(Path(tmpdir).glob("img-*"))

        # 选择面积最大的图片作为 LOGO 候选
        best = None
        best_area = 0
        for img_path in imgs:
            try:
                with Image.open(img_path) as im:
                    area = im.width * im.height
                    if area > best_area:
                        best_area = area
                        best = img_path
            except Exception:
                continue

        if best is None:
            raise RuntimeError("无法从 PDF 中提取 LOGO 图片")

        # 处理透明背景
        with Image.open(best) as im:
            # 转为 RGBA
            if im.mode != "RGBA":
                im = im.convert("RGBA")
            # 简单透明化：如果四角是近似白色，则设为透明
            datas = im.getdata()
            new_data = []
            for item in datas:
                r, g, b, a = item
                # 近似白色（阈值 240）设为透明
                if r > 240 and g > 240 and b > 240:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            im.putdata(new_data)

            # 裁剪透明边
            bbox = im.getbbox()
            if bbox:
                im = im.crop(bbox)

            # 升采样至高度 >= 200px
            if im.height < 200:
                ratio = 200 / im.height
                new_size = (int(im.width * ratio), 200)
                im = im.resize(new_size, Image.LANCZOS)

            # 保存
            logo_path = out_dir / "logo.png"
            im.save(logo_path, "PNG")

            # 生成 base64
            with open(logo_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            with open(out_dir / "logo_base64.txt", "w") as f:
                f.write(b64)

            # 记录来源
            with open(out_dir / "logo_source.txt", "w") as f:
                f.write(f"来源: {pdf_path}\n提取工具: pdfimages -all\n原始尺寸: {im.width}x{im.height}\n")

    return {
        "logo_path": str(out_dir / "logo.png"),
        "base64_path": str(out_dir / "logo_base64.txt"),
        "source_path": str(out_dir / "logo_source.txt"),
    }


def extract_palette(pdf_path: str, output_dir: str) -> dict:
    """P0-4: 提取主色和辅色。"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 渲染第一页用于取色
    with tempfile.TemporaryDirectory() as tmpdir:
        run(["pdftocairo", "-png", "-r", "150", "-f", "1", "-l", "1", pdf_path, f"{tmpdir}/cover"])
        cover_png = Path(tmpdir) / "cover-1.png"
        if not cover_png.exists():
            cover_png = Path(tmpdir) / "cover.png"

        with Image.open(cover_png) as im:
            # 缩小以加速
            im_small = im.resize((200, int(200 * im.height / im.width)), Image.LANCZOS)
            pixels = list(im_small.getdata())

            # 过滤掉近白/近黑/低饱和像素
            def is_valid_color(r, g, b):
                brightness = (r + g + b) / 3
                if brightness > 240 or brightness < 20:
                    return False
                # 饱和度过滤
                max_c, min_c = max(r, g, b), min(r, g, b)
                if max_c == 0:
                    return False
                saturation = (max_c - min_c) / max_c
                return saturation > 0.3

            colors = [(r, g, b) for r, g, b in pixels if is_valid_color(r, g, b)]

            if len(colors) < 100:
                raise RuntimeError("有效颜色样本不足，无法提取 palette")

            # 简单聚类：按红色通道排序，取前 10% 作为"主红"，中间偏黄作为"辅金"
            colors_sorted = sorted(colors, key=lambda c: c[0], reverse=True)
            primary_candidates = colors_sorted[:max(10, len(colors_sorted) // 20)]
            primary = tuple(int(sum(c[i] for c in primary_candidates) / len(primary_candidates)) for i in range(3))

            # 辅色：找偏黄的（R 和 G 高，B 低）
            yellowish = [c for c in colors if c[0] > 150 and c[1] > 120 and c[2] < 100]
            if len(yellowish) < 10:
                #  fallback：用整体平均
                accent = tuple(int(sum(c[i] for c in colors) / len(colors)) for i in range(3))
            else:
                accent = tuple(int(sum(c[i] for c in yellowish) / len(yellowish)) for i in range(3))

            def to_hex(c):
                return f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}"

            palette = {
                "primary": to_hex(primary),
                "primary_dark": to_hex(tuple(max(0, int(c * 0.6)) for c in primary)),
                "primary_light": to_hex(tuple(min(255, int(c + (255 - c) * 0.85)) for c in primary)),
                "accent": to_hex(accent),
                "accent_light": to_hex(tuple(min(255, int(c + (255 - c) * 0.7)) for c in accent)),
                "text_primary": "#1A1A1A",
                "text_secondary": "#555555",
                "bg_white": "#FFFFFF",
                "bg_light": "#F7F7F7",
                "border": "#E0E0E0",
                "growth_green": "#2E7D32",
                "risk_red": "#C62828",
                "efficiency_blue": "#1565C0",
            }

            palette_path = out_dir / "palette.json"
            with open(palette_path, "w") as f:
                json.dump(palette, f, ensure_ascii=False, indent=2)

    return {"palette_path": str(palette_path), "palette": palette}


def verify_vis_assets(assets_dir: str) -> dict:
    """P0-5: 验收门禁。"""
    assets = Path(assets_dir)
    checks = []
    passed = True

    # LOGO 检查
    logo_png = assets / "logo" / "logo.png"
    if logo_png.exists():
        with Image.open(logo_png) as im:
            h = im.height
            has_alpha = im.mode == "RGBA"
            checks.append({"item": "LOGO 高度", "passed": h >= 200, "detail": f"{h}px"})
            checks.append({"item": "LOGO 透明背景", "passed": has_alpha, "detail": f"mode={im.mode}"})
    else:
        checks.append({"item": "LOGO 存在", "passed": False, "detail": "logo.png 缺失"})
        passed = False

    # palette 检查
    palette_path = assets / "vis" / "palette.json"
    if palette_path.exists():
        with open(palette_path) as f:
            pal = json.load(f)
        primary = pal.get("primary", "")
        accent = pal.get("accent", "")
        checks.append({"item": "palette 主色有效", "passed": primary not in ("#FFFFFF", "#000000", ""), "detail": primary})
        checks.append({"item": "palette 辅色有效", "passed": accent not in ("#FFFFFF", "#000000", ""), "detail": accent})
    else:
        checks.append({"item": "palette 存在", "passed": False, "detail": "palette.json 缺失"})
        passed = False

    # 年报检查
    annual_dir = assets / "annual_report"
    pdfs = list(annual_dir.glob("*.pdf")) if annual_dir.exists() else []
    checks.append({"item": "年报 PDF", "passed": len(pdfs) > 0, "detail": f"找到 {len(pdfs)} 个 PDF"})

    return {"passed": passed, "checks": checks}


def build_vis_assets(annual_report_pdf: str, output_dir: str, *, bank_name: str = "") -> dict:
    """执行 P0-1 ~ P0-4 完整流程。

    Args:
        bank_name: 银行名称（如 "光大银行"）。**必须指定**，无默认值。
    """
    ensure_dirs()

    pdf_path = Path(annual_report_pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"年报 PDF 不存在: {pdf_path}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # P0-2 渲染
    vis_dir = out / "vis"
    rendered = render_pages(str(pdf_path), str(vis_dir))

    # P0-3 提取 LOGO
    logo_dir = out / "logo"
    logo_result = extract_logo(str(pdf_path), str(logo_dir))

    # P0-4 提取 palette
    palette_result = extract_palette(str(pdf_path), str(vis_dir))

    # P0-5 验收
    verify_result = verify_vis_assets(str(out))

    return {
        "status": "ok" if verify_result["passed"] else "degraded",
        "logo": logo_result,
        "palette": palette_result,
        "rendered_pages": rendered,
        "verification": verify_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="P0 VIS 资产构建器")
    parser.add_argument("--annual-report", required=True, help="年报 PDF 路径")
    parser.add_argument("--bank", required=True, help="银行名称（必须指定，如 光大银行）")
    parser.add_argument("--output-dir", default=str(REPORT_ASSETS_DIR), help="输出目录")
    parser.add_argument("--verify-only", action="store_true", help="仅执行验收")
    args = parser.parse_args()

    if args.verify_only:
        result = verify_vis_assets(args.output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1

    result = build_vis_assets(args.annual_report, args.output_dir, bank_name=args.bank)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
