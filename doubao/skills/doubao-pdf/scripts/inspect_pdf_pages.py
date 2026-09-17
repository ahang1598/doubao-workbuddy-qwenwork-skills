#!/usr/bin/env python3
"""Render source PDF (and optionally the DOCX-rendered PDF) side-by-side for
visual QA. Inspired by kimi-pdf/scripts/cmd_inspect.py, adapted for the
PDF -> Word fidelity check flow.

Usage:
  # Source-only contact sheet — always works, even when libreoffice cannot render
  python3 inspect_pdf_pages.py --source input.pdf --output-dir work/qa

  # Side-by-side comparison — libreoffice converted DOCX -> PDF first
  python3 inspect_pdf_pages.py --source input.pdf --target work/rendered.pdf \\
    --output-dir work/qa

Outputs under --output-dir:
  source-page-NN.png        (per-page rendered PNG of source PDF, 120 dpi)
  target-page-NN.png        (per-page rendered PNG of target PDF, when --target given)
  contact-sheet-source.png  (grid of source pages with page numbers)
  contact-sheet-side.png    (2-column grid: source | target, when --target given)
  metrics.json              (per-page ink_ratio, content_bbox_area_ratio, warnings)

Exit codes:
  0  contact sheet rendered
  1  arg error (source missing, etc.)
  2  source pdf unreadable
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


LOW_INK_THRESHOLD = 0.003
LOW_CONTENT_HEIGHT = 0.08
# 工作流硬约束：每页内容位置对齐——内容 bbox 中心偏移 < 20% 视为对齐；
# 现由本脚本落地检测，超阈值即视为"保真核心失败"。
BBOX_CENTER_OFFSET_THRESHOLD = 0.20
WHITE = 245


def _render_pdf_pages(pdf_path: Path, out_dir: Path, prefix: str, dpi: int = 120):
    """Render each page to <prefix>-page-NN.png. Returns list of (page_number, png_path)."""
    import pymupdf
    out = []
    with pymupdf.open(str(pdf_path)) as doc:
        scale = dpi / 72.0
        m = pymupdf.Matrix(scale, scale)
        for i in range(doc.page_count):
            page = doc[i]
            pix = page.get_pixmap(matrix=m, alpha=False)
            fname = out_dir / f"{prefix}-page-{i + 1:02d}.png"
            pix.save(str(fname))
            out.append((i + 1, fname))
    return out


def _ink_metrics(png_path: Path):
    """kimi-style ink ratio + content bbox + 归一化内容中心。

    content_center_norm 使得源和目标即使渲染分辨率或页面像素尺寸不同，
    也能在 [0,1] 空间对比每页内容的位置——工作流保真核心「内容 bbox 偏移 < 20%」
    需要一个不依赖绝对像素的坐标才能落地检测。
    """
    from PIL import Image
    img = Image.open(png_path).convert("L")
    ink = img.point(lambda v: 255 if v < WHITE else 0)
    total = max(1, img.width * img.height)
    ink_pixels = ink.histogram()[255]
    bbox = ink.getbbox()
    if bbox is None:
        return {"ink_ratio": 0.0, "content_bbox": None,
                "content_width_ratio": 0.0, "content_height_ratio": 0.0, "content_area_ratio": 0.0,
                "content_center_norm": None,
                "warnings": ["blank_page"]}
    l, t, r, b = bbox
    m = {
        "ink_ratio": round(ink_pixels / total, 6),
        "content_bbox": [l, t, r, b],
        "content_width_ratio": round((r - l) / img.width, 4),
        "content_height_ratio": round((b - t) / img.height, 4),
        "content_area_ratio": round(((r - l) * (b - t)) / total, 4),
        "content_center_norm": [
            round((l + r) / (2 * img.width), 4),
            round((t + b) / (2 * img.height), 4),
        ],
        "warnings": [],
    }
    if m["ink_ratio"] < LOW_INK_THRESHOLD:
        m["warnings"].append(f"low_ink_ratio<{LOW_INK_THRESHOLD}")
    if m["content_height_ratio"] < LOW_CONTENT_HEIGHT:
        m["warnings"].append(f"low_content_height<{LOW_CONTENT_HEIGHT}")
    return m


def _build_contact_sheet(cells, output_path: Path, columns=3, thumb_w=360, thumb_h=480,
                         padding=16, label_h=28, tile_bg="white", sheet_bg="#d9dde3"):
    """cells: list of (label_str, image_path). Produces a grid PNG."""
    from PIL import Image, ImageDraw
    if not cells:
        return
    columns = min(columns, len(cells))
    rows = math.ceil(len(cells) / columns)
    W = padding + columns * (thumb_w + padding)
    H = padding + rows * (thumb_h + label_h + padding)
    sheet = Image.new("RGB", (W, H), sheet_bg)
    draw = ImageDraw.Draw(sheet)
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    for index, (label, path) in enumerate(cells):
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((thumb_w, thumb_h), resampling)
        col = index % columns
        row = index // columns
        x = padding + col * (thumb_w + padding)
        y = padding + row * (thumb_h + label_h + padding)
        tile = Image.new("RGB", (thumb_w, thumb_h), tile_bg)
        tile.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
        sheet.paste(tile, (x, y))
        draw.text((x, y + thumb_h + 6), label, fill="black")
    sheet.save(output_path)


def _build_side_by_side_sheet(source_cells, target_cells, output_path: Path,
                              thumb_w=360, thumb_h=480, padding=16, label_h=28):
    """2-column: source[i] | target[i]. Uses len = max(both) with blank tiles for missing pages."""
    from PIL import Image, ImageDraw
    n = max(len(source_cells), len(target_cells))
    if n == 0:
        return
    W = padding + 2 * (thumb_w + padding)
    H = padding + n * (thumb_h + label_h + padding)
    sheet = Image.new("RGB", (W, H), "#d9dde3")
    draw = ImageDraw.Draw(sheet)
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    def _paste(cell, col_index, row_index):
        x = padding + col_index * (thumb_w + padding)
        y = padding + row_index * (thumb_h + label_h + padding)
        tile = Image.new("RGB", (thumb_w, thumb_h), "white")
        if cell:
            label, path = cell
            try:
                with Image.open(path) as img:
                    img = img.convert("RGB")
                    img.thumbnail((thumb_w, thumb_h), resampling)
                tile.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
                draw.text((x, y + thumb_h + 6), label, fill="black")
            except Exception:
                draw.text((x + 20, y + thumb_h // 2), f"[missing] {label}", fill="red")
        else:
            draw.text((x + 20, y + thumb_h // 2), "[missing page]", fill="red")
        sheet.paste(tile, (x, y))

    for i in range(n):
        s = source_cells[i] if i < len(source_cells) else None
        t = target_cells[i] if i < len(target_cells) else None
        _paste(s, 0, i)
        _paste(t, 1, i)
    sheet.save(output_path)


def inspect(source_pdf: Path, target_pdf: Path | None, output_dir: Path,
            dpi: int) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    source_pages = _render_pdf_pages(source_pdf, output_dir, "source", dpi=dpi)
    source_metrics = []
    source_cells = []
    for pn, path in source_pages:
        m = _ink_metrics(path)
        source_metrics.append({"page": pn, **m})
        source_cells.append((f"Source p{pn}", path))

    target_metrics = []
    target_cells = []
    if target_pdf is not None and target_pdf.is_file():
        target_pages = _render_pdf_pages(target_pdf, output_dir, "target", dpi=dpi)
        for pn, path in target_pages:
            m = _ink_metrics(path)
            target_metrics.append({"page": pn, **m})
            target_cells.append((f"Target p{pn}", path))

    # Source-only contact sheet always
    contact_source = output_dir / "contact-sheet-source.png"
    _build_contact_sheet(source_cells, contact_source)

    contact_side = None
    if target_cells:
        contact_side = output_dir / "contact-sheet-side.png"
        _build_side_by_side_sheet(source_cells, target_cells, contact_side)

    # Page count check
    page_count_report = {
        "source_pages": len(source_pages),
        "target_pages": len(target_metrics) if target_metrics else None,
        "match_source_target": (
            (len(target_metrics) == len(source_pages)) if target_metrics else None
        ),
    }

    warnings = []
    if target_metrics and len(target_metrics) != len(source_pages):
        warnings.append(
            f"target PDF has {len(target_metrics)} pages, source has {len(source_pages)}"
            f" — page-count fidelity failed"
        )
    if target_metrics:
        for s, t in zip(source_metrics, target_metrics):
            # Large ink-ratio drop suggests missing content on that page
            ratio_delta = t["ink_ratio"] - s["ink_ratio"]
            if s["ink_ratio"] > 0 and abs(ratio_delta) > 0.3 * s["ink_ratio"]:
                warnings.append(
                    f"page {s['page']}: ink ratio changed a lot "
                    f"(source={s['ink_ratio']:.4f} target={t['ink_ratio']:.4f}); "
                    f"look at contact-sheet-side.png for what's missing"
                )
            # 内容中心偏移——工作流保真核心（8/15 case 报视觉-分页错误，14/15 报视觉-元素错位）
            sc = s.get("content_center_norm")
            tc = t.get("content_center_norm")
            if sc and tc:
                dx = abs(sc[0] - tc[0])
                dy = abs(sc[1] - tc[1])
                if dx > BBOX_CENTER_OFFSET_THRESHOLD or dy > BBOX_CENTER_OFFSET_THRESHOLD:
                    warnings.append(
                        f"page {s['page']}: 内容中心偏移超阈值 "
                        f"(dx={dx:.1%}, dy={dy:.1%}, 阈值 {BBOX_CENTER_OFFSET_THRESHOLD:.0%})；"
                        f"工作流保真核心失败——分页错误或整体错位"
                    )
            for w in t.get("warnings", []):
                warnings.append(f"page {s['page']} target: {w}")

    report = {
        "source_pdf": str(source_pdf.resolve()),
        "target_pdf": str(target_pdf.resolve()) if target_pdf else None,
        "output_dir": str(output_dir.resolve()),
        "contact_sheet_source": str(contact_source.resolve()),
        "contact_sheet_side": str(contact_side.resolve()) if contact_side else None,
        "page_count": page_count_report,
        "source_metrics": source_metrics,
        "target_metrics": target_metrics if target_metrics else None,
        "warnings": warnings,
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="源 PDF 路径")
    parser.add_argument("--target", type=Path, default=None,
                        help="目标 PDF（TARGET_DOCX 用 libreoffice 渲染后的 PDF）；不传就只出源侧对照表")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出目录")
    parser.add_argument("--dpi", type=int, default=120)
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"error: source pdf not found: {args.source}", file=sys.stderr)
        return 1

    try:
        report = inspect(args.source, args.target, args.output_dir, args.dpi)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"contact-sheet (source): {report['contact_sheet_source']}")
    if report.get("contact_sheet_side"):
        print(f"contact-sheet (side): {report['contact_sheet_side']}")
    if report["warnings"]:
        print(f"WARNINGS ({len(report['warnings'])}):", file=sys.stderr)
        for w in report["warnings"]:
            print(f"  - {w}", file=sys.stderr)
    print(f"metrics: {(args.output_dir / 'metrics.json').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
