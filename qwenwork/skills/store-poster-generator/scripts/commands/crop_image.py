"""
crop-image 命令

对本地图片进行裁剪，通过 --box 指定要保留的区域坐标。

用法：
    # 裁剪底部 100px（图片 960x1280）：保留上方区域
    python cli.py crop-image --input /path/to/image.png --box 0 0 960 1180

    # 裁剪顶部 50px：保留下方区域
    python cli.py crop-image --input /path/to/image.png --box 0 50 960 1280

    # 指定输出路径（默认覆盖原图）
    python cli.py crop-image --input /path/to/image.png --box 0 0 960 1000 --output /path/to/cropped.png
"""

import argparse
import sys
from pathlib import Path

from PIL import Image


def register(subparsers) -> None:
    """Register the crop-image subcommand into the CLI."""
    parser = subparsers.add_parser(
        "crop-image",
        help="图片裁剪工具，通过坐标指定保留区域",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", required=True, help="输入图片路径",
    )
    parser.add_argument(
        "--box", required=True, type=int, nargs=4,
        metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
        help="保留区域的坐标：left top right bottom",
    )
    parser.add_argument(
        "--output", default=None,
        help="输出图片路径，不指定则覆盖原图",
    )
    parser.set_defaults(handler=run)


def run(args) -> None:
    """执行图片裁剪。"""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 输入图片不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        image = Image.open(input_path)
    except Exception as error:
        print(f"❌ 无法打开图片: {error}", file=sys.stderr)
        sys.exit(1)

    width, height = image.size
    left, top, right, bottom = args.box

    if left < 0 or top < 0 or right > width or bottom > height:
        print(
            f"❌ 坐标超出图片范围（图片: {width}x{height}，"
            f"区域: [{left}, {top}, {right}, {bottom}]）",
            file=sys.stderr,
        )
        sys.exit(1)
    if left >= right or top >= bottom:
        print(
            f"❌ 坐标无效：left({left}) 必须小于 right({right})，"
            f"top({top}) 必须小于 bottom({bottom})",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"✂️  裁剪 [{left}, {top}, {right}, {bottom}]（原始尺寸: {width}x{height}）")
    cropped = image.crop((left, top, right, bottom))

    output_path = Path(args.output) if args.output else input_path
    if args.output:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        cropped.save(output_path)
        cropped_width, cropped_height = cropped.size
        print(f"✅ 裁剪完成: {output_path}")
        print(f"   尺寸: {cropped_width} x {cropped_height}")
    except Exception as error:
        print(f"❌ 保存图片失败: {error}", file=sys.stderr)
        sys.exit(1)