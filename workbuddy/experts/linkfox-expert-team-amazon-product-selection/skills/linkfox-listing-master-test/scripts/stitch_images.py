#!/usr/bin/env python3
"""
A+ 图片拼接脚本（v2）
支持两种拼接模式：
- vertical: 上下垂直拼接（默认，适合同一 ASIN 的 A+ 图）
- grid: 网格拼接（适合多来源参考图，自动计算最优行列数）

拼接后输出元数据 JSON，供 split_images.py 反向切割使用。
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow 未安装，请执行: pip install Pillow", file=sys.stderr)
    sys.exit(1)


def compute_grid(n: int) -> tuple[int, int]:
    """根据图片数量计算最优网格行列数，优先横向排列（列数 >= 行数）。"""
    if n <= 1:
        return 1, 1
    if n == 2:
        return 1, 2
    if n == 3:
        return 1, 3
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    return rows, cols


def stitch_vertical(images: list[Image.Image]) -> tuple[Image.Image, dict]:
    """垂直拼接，返回 (拼接图, 元数据)。"""
    max_width = max(img.width for img in images)

    resized = []
    for img in images:
        if img.width != max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        resized.append(img)

    total_height = sum(img.height for img in resized)
    canvas = Image.new("RGB", (max_width, total_height), (255, 255, 255))

    cells = []
    y_offset = 0
    for i, img in enumerate(resized):
        canvas.paste(img, (0, y_offset))
        cells.append({
            "index": i,
            "x": 0,
            "y": y_offset,
            "w": img.width,
            "h": img.height,
        })
        y_offset += img.height

    meta = {
        "layout": "vertical",
        "rows": len(images),
        "cols": 1,
        "original_count": len(images),
        "canvas_width": max_width,
        "canvas_height": total_height,
        "cells": cells,
    }
    return canvas, meta


def stitch_grid(images: list[Image.Image]) -> tuple[Image.Image, dict]:
    """网格拼接，返回 (拼接图, 元数据)。"""
    rows, cols = compute_grid(len(images))

    # 统一单元格尺寸：取所有图片缩放到统一宽度后的最大高度
    cell_width = max(img.width for img in images)
    # 先按宽度缩放，计算缩放后高度的最大值作为统一单元格高度
    scaled_heights = []
    for img in images:
        ratio = cell_width / img.width
        scaled_heights.append(int(img.height * ratio))
    cell_height = max(scaled_heights)

    canvas_width = cell_width * cols
    canvas_height = cell_height * rows
    canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))

    cells = []
    for i, img in enumerate(images):
        row = i // cols
        col = i % cols
        # 等比缩放到 cell_width
        ratio = cell_width / img.width
        new_h = int(img.height * ratio)
        resized = img.resize((cell_width, new_h), Image.LANCZOS)
        x = col * cell_width
        y = row * cell_height
        canvas.paste(resized, (x, y))
        cells.append({
            "index": i,
            "x": x,
            "y": y,
            "w": cell_width,
            "h": new_h,  # 实际图片高度（可能小于 cell_height）
            "cell_w": cell_width,
            "cell_h": cell_height,
        })
        resized.close()

    meta = {
        "layout": "grid",
        "rows": rows,
        "cols": cols,
        "original_count": len(images),
        "cell_width": cell_width,
        "cell_height": cell_height,
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "cells": cells,
    }
    return canvas, meta


def load_images(image_paths: list[str]) -> list[tuple[Image.Image, str]]:
    """加载图片列表，返回 (Image, 原始文件名) 列表。"""
    results = []
    for path in image_paths:
        if not os.path.exists(path):
            print(f"WARNING: 文件不存在，跳过: {path}", file=sys.stderr)
            continue
        try:
            img = Image.open(path).convert("RGB")
            results.append((img, os.path.basename(path)))
        except Exception as e:
            print(f"WARNING: 无法打开图片 {path}: {e}", file=sys.stderr)
    return results


def main():
    parser = argparse.ArgumentParser(description="拼接多张图片（支持垂直/网格模式）")
    parser.add_argument("--images", "-i", nargs="+", required=True, help="输入图片路径列表")
    parser.add_argument("--output", "-o", required=True, help="输出图片路径")
    parser.add_argument(
        "--layout", "-l",
        choices=["vertical", "grid", "auto"],
        default="auto",
        help="拼接模式：vertical=垂直, grid=网格, auto=自动选择（默认）"
    )

    args = parser.parse_args()

    loaded = load_images(args.images)
    if not loaded:
        print("ERROR: 没有有效的图片可以拼接", file=sys.stderr)
        sys.exit(1)

    images = [item[0] for item in loaded]
    filenames = [item[1] for item in loaded]

    # 自动选择：1张或来自同一来源的多张用 vertical，其他用 grid
    layout = args.layout
    if layout == "auto":
        layout = "vertical" if len(images) <= 3 else "grid"

    print(f"拼接模式: {layout}，共 {len(images)} 张图片", file=sys.stderr)

    if layout == "vertical":
        canvas, meta = stitch_vertical(images)
    else:
        canvas, meta = stitch_grid(images)

    # 记录原始文件名
    for i, cell in enumerate(meta["cells"]):
        if i < len(filenames):
            cell["original_file"] = filenames[i]

    # 保存拼接图
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    canvas.save(args.output, quality=95)

    # 保存元数据
    meta_path = args.output.rsplit(".", 1)[0] + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 输出关键信息
    w, h = meta["canvas_width"], meta["canvas_height"]
    ratio = h / w
    print(f"WIDTH={w} HEIGHT={h} RATIO={ratio:.2f}")
    print(f"LAYOUT={layout} ROWS={meta['rows']} COLS={meta['cols']}")
    print(f"META={meta_path}")

    print(f"拼接完成: {args.output}", file=sys.stderr)
    print(f"元数据: {meta_path}", file=sys.stderr)
    print(f"尺寸: {w} x {h}，高宽比: {ratio:.2f}", file=sys.stderr)

    # 释放内存
    for img in images:
        img.close()
    canvas.close()


if __name__ == "__main__":
    main()
