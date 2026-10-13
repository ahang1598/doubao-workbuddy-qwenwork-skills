"""
generate-image 命令

文生图入口。

用法：
    python cli.py generate-image create --text "牛奶 5 折促销海报"
    python cli.py generate-image create --text "科技风产品发布海报" --image-size "960*1280"
"""

import argparse
import sys

from commands.generation_poster_by_text import run as run_text2img


def register(subparsers) -> None:
    """Register the generate-image subcommand into the CLI."""
    parser = subparsers.add_parser(
        "generate-image",
        help="文生图入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="sub_action", help="子命令")

    # ── create 子命令 ──
    create_parser = sub.add_parser(
        "create",
        help="根据文本描述生成图片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    create_parser.add_argument(
        "--text",
        required=True,
        help="图片描述文本 / 提示词",
    )
    create_parser.add_argument(
        "--image-size",
        default="960*1280",
        help="图片分辨率，默认 960*1280",
    )
    create_parser.set_defaults(handler=run_create)

    parser.set_defaults(handler=lambda args: parser.print_help() or sys.exit(2))


def run_create(args) -> None:
    """文生图。"""
    text2img_args = argparse.Namespace(
        text=args.text,
        image_size=args.image_size,
    )
    run_text2img(text2img_args)