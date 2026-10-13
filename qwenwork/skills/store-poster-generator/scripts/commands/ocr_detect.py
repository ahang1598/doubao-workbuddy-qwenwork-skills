"""
ocr-detect 命令

通用 OCR 文字检测工具，使用 EasyOCR 识别图片指定区域内是否包含目标文字。
检测区域和目标关键词均由调用者指定。

用法：
    # 检测图片指定区域内是否包含某关键词（通过坐标指定区域）
    python cli.py ocr-detect --input /path/to/image.png --box 0 1240 480 1280 --keyword "AI"

    # 检测整张图片是否包含某关键词
    python cli.py ocr-detect --input /path/to/image.png --keyword "watermark"

    # 多个关键词（任一匹配即算命中）
    python cli.py ocr-detect --input /path/to/image.png --keyword "AI" --keyword "generated"

    # 指定 OCR 语言（默认英文）
    python cli.py ocr-detect --input /path/to/image.png --keyword "水印" --languages ch_sim en

返回：
    输出 JSON 格式的检测结果。
    检测到目标关键词时退出码为 0，未检测到时退出码为 1。
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image


def register(subparsers) -> None:
    """Register the ocr-detect subcommand into the CLI."""
    parser = subparsers.add_parser(
        "ocr-detect",
        help="通用 OCR 文字检测，检测图片指定区域内是否包含目标文字",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", required=True, help="输入图片路径",
    )
    parser.add_argument(
        "--box", type=int, nargs=4, default=None,
        metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
        help="检测区域坐标（left top right bottom），不指定则检测整张图片",
    )
    parser.add_argument(
        "--keyword", required=True, action="append", dest="keywords",
        help="要检测的关键词（不区分大小写），可多次指定",
    )
    parser.add_argument(
        "--languages", nargs="+", default=["en"],
        help="OCR 识别语言列表，默认 en。中文用 ch_sim，日文用 ja 等",
    )
    parser.set_defaults(handler=run)


def run(args) -> None:
    """执行 OCR 检测。"""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 输入图片不存在: {input_path}", file=sys.stderr)
        sys.exit(2)

    image = Image.open(input_path)
    image_width, image_height = image.size

    # 确定检测区域
    if args.box:
        left, top, right, bottom = args.box
        if left < 0 or top < 0 or right > image_width or bottom > image_height:
            print(
                f"❌ 检测区域超出图片范围（图片: {image_width}x{image_height}，"
                f"区域: [{left}, {top}, {right}, {bottom}]）",
                file=sys.stderr,
            )
            sys.exit(2)
        if left >= right or top >= bottom:
            print(
                f"❌ 检测区域无效：left({left}) < right({right})，top({top}) < bottom({bottom})",
                file=sys.stderr,
            )
            sys.exit(2)
        region = image.crop((left, top, right, bottom))
        region_desc = f"[{left}, {top}, {right}, {bottom}]"
    else:
        region = image
        region_desc = f"整张图片 {image_width}x{image_height}"

    keywords_display = ", ".join(args.keywords)
    print(f"🔍 检测区域: {region_desc}（原图 {image_width}x{image_height}）")
    print(f"🔑 目标关键词: {keywords_display}")

    # 保存检测区域到临时文件用于 OCR
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        region.save(tmp_path)

    try:
        import easyocr
        reader = easyocr.Reader(args.languages, gpu=False, verbose=False)
        results = reader.readtext(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # 检查是否包含目标关键词
    keywords_upper = [kw.upper() for kw in args.keywords]
    matched_texts = []
    for _, text, confidence in results:
        text_upper = text.upper()
        hitting_keywords = [kw for kw in args.keywords if kw.upper() in text_upper]
        if hitting_keywords:
            matched_texts.append({
                "text": text,
                "confidence": round(confidence, 4),
                "matched_keywords": hitting_keywords,
            })

    has_match = len(matched_texts) > 0

    result = {
        "found": has_match,
        "keywords": args.keywords,
        "detect_region": {
            "left": args.box[0] if args.box else 0,
            "top": args.box[1] if args.box else 0,
            "right": args.box[2] if args.box else image_width,
            "bottom": args.box[3] if args.box else image_height,
        },
        "matched_texts": matched_texts,
        "all_ocr_texts": [
            {"text": text, "confidence": round(conf, 4)}
            for _, text, conf in results
        ],
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if has_match:
        print(f"\n⚠️  检测到关键词: {[m['text'] for m in matched_texts]}")
    else:
        print(f"\n✅ 未检测到关键词: [{keywords_display}]")

    sys.exit(0 if has_match else 1)