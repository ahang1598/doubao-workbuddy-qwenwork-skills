#!/usr/bin/env python3
"""二维码生成脚本。

将试衣间链接生成二维码图片，保存到本地文件。

用法：
  python scripts/gen_qrcode.py --url <试衣间链接> [--output <输出路径>]

输出: JSON（ensure_ascii=False）
退出码: 0=成功, 1=生成失败, 2=参数错误
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import qrcode
from qrcode.image.pure import PyPNGImage


def print_json(data: dict) -> None:
    """将字典以格式化 JSON 输出到 stdout。"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def exit_with_error(message: str, code: int = 1) -> None:
    """输出错误 JSON 并以指定退出码退出。"""
    print_json({"success": False, "error": message})
    sys.exit(code)


def generate_qrcode(url: str, output_path: Path) -> None:
    """生成二维码图片并保存到指定路径。"""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # 优先使用 Pillow 生成 PNG（支持彩色）
        from PIL import Image
        image = qr.make_image(fill_color="black", back_color="white")
        image.save(str(output_path))
    except ImportError:
        # 降级使用纯 Python PNG 生成（无需 Pillow）
        image = qr.make_image(image_factory=PyPNGImage)
        image.save(str(output_path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gen_qrcode.py",
        description="将试衣间链接生成二维码图片",
    )
    parser.add_argument(
        "--url",
        required=True,
        help="要生成二维码的店铺链接，如：https://ai.teambition.net/api/opt/store/xxx",
    )
    parser.add_argument(
        "--output",
        default="qrcode.png",
        help="输出图片路径（默认：qrcode.png）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output).resolve()

    try:
        generate_qrcode(url=args.url, output_path=output_path)
    except Exception as error:
        exit_with_error(f"二维码生成失败: {error}")

    print_json({
        "success": True,
        "url": args.url,
        "qrcode_path": str(output_path),
    })


if __name__ == "__main__":
    main()
