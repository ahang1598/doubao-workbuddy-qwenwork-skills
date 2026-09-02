#!/usr/bin/env python3
"""
A+ 图片切割脚本
根据拼接时生成的元数据 JSON，将生成的图片按原始拼接方式反向切割为独立图片。
与 stitch_images.py 配合使用：拼什么格式，切什么格式。

核心原则：
- 按照拼接时的 rows×cols 网格切割，每块尺寸 = 原始输入图的尺寸
- 只输出有真实图片的 cell（跳过空白补位 cell）
- 支持生成图与拼接图尺寸不同（按比例缩放坐标）
"""

import argparse
import json
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow 未安装，请执行: pip install Pillow", file=sys.stderr)
    sys.exit(1)


def split_image(image_path: str, meta_path: str, output_dir: str) -> list[str]:
    """
    按元数据切割图片。

    切割逻辑：
    - vertical 模式：每个 cell 的 (x, y, w, h) 就是实际图片区域
    - grid 模式：每个 cell 占据 cell_w × cell_h 的格子，
      但实际图片只占 (x, y, w=cell_w, h=实际高度)，
      切割时按 cell_w × cell_h 整格切割（与拼接时一致）

    Args:
        image_path: 待切割的图片路径
        meta_path: stitch_images.py 生成的 .meta.json 路径
        output_dir: 切割后图片的输出目录

    Returns:
        输出文件路径列表
    """
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    img = Image.open(image_path).convert("RGB")
    gen_w, gen_h = img.size
    canvas_w = meta["canvas_width"]
    canvas_h = meta["canvas_height"]

    # 计算缩放比例（生成图和原始拼接图尺寸可能不同）
    scale_x = gen_w / canvas_w
    scale_y = gen_h / canvas_h

    # 真实图片数量（跳过补位的空白 cell）
    original_count = meta.get("original_count", len(meta["cells"]))

    os.makedirs(output_dir, exist_ok=True)
    output_paths = []

    layout = meta.get("layout", "vertical")

    for cell in meta["cells"]:
        idx = cell["index"]

        # 跳过超出原始图片数量的补位 cell
        if idx >= original_count:
            print(f"跳过补位 cell [{idx}]", file=sys.stderr)
            continue

        if layout == "grid":
            # grid 模式：按 cell_w × cell_h 整格切割
            # 这样每张切图尺寸完全一致，与原始输入图尺寸匹配
            cw = cell.get("cell_w", cell["w"])
            ch = cell.get("cell_h", cell["h"])
        else:
            # vertical 模式：按实际图片区域切割
            cw = cell["w"]
            ch = cell["h"]

        x = int(cell["x"] * scale_x)
        y = int(cell["y"] * scale_y)
        w = int(cw * scale_x)
        h = int(ch * scale_y)

        cropped = img.crop((x, y, x + w, y + h))

        # 使用原始文件名或序号命名
        original_name = cell.get("original_file", f"part_{idx:02d}.jpg")
        base, ext = os.path.splitext(original_name)
        if not ext:
            ext = ".jpg"
        output_name = f"{base}_generated{ext}"
        output_path = os.path.join(output_dir, output_name)

        cropped.save(output_path, quality=95)
        cropped.close()
        output_paths.append(output_path)

        print(f"切割 [{idx}]: ({x},{y}) {w}x{h} -> {output_path}", file=sys.stderr)

    img.close()

    print(f"共切割 {len(output_paths)} 张图片到 {output_dir}（原始 {original_count} 张，跳过 {len(meta['cells']) - original_count} 张补位）", file=sys.stderr)
    return output_paths


def main():
    parser = argparse.ArgumentParser(description="按元数据反向切割生成图片")
    parser.add_argument("--image", "-i", required=True, help="待切割的生成图片路径")
    parser.add_argument("--meta", "-m", required=True, help="拼接元数据 JSON 路径")
    parser.add_argument("--output-dir", "-o", required=True, help="输出目录")

    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"ERROR: 图片不存在: {args.image}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.meta):
        print(f"ERROR: 元数据不存在: {args.meta}", file=sys.stderr)
        sys.exit(1)

    output_paths = split_image(args.image, args.meta, args.output_dir)

    # 输出文件路径到 stdout，便于脚本解析
    for p in output_paths:
        print(p)


if __name__ == "__main__":
    main()
