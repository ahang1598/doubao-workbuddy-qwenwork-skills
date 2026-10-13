"""
generation-poster-by-text 命令

根据自然语言描述生成创意海报，内部调用 creative-poster-generator MCP 工具。

用法：
    python cli.py generation-poster-by-text --text "牛奶 5 折促销海报，竖版构图适合门店展示"
    python cli.py generation-poster-by-text --text "科技风产品发布海报" --image-size "960*1280"
"""

import argparse
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

from commands.call_mcp import (
    get_mcp_url_by_subskillname,
    resolve_url,
    send_mcp_request,
)
from commands.ensure_mcp_skill import ensure_mcp_skill
from commands.skill_context import get_skill_context

MCP_NAME = "visual-creator"
MCP_ID = "9436"
TOOL_NAME = "generation_poster_by_text"

# API 底部 "AI 生成" 水印的高度（像素）
AI_WATERMARK_HEIGHT = 40

DISABLED = True

def normalize_image_size(image_size: str) -> str:
    """将 image_size 中的 'x' 分隔符统一替换为 '*'。

    支持 '960x1280' → '960*1280'，已经是 '*' 的保持不变。
    """
    return re.sub(r"(\d+)\s*[xX]\s*(\d+)", r"\1*\2", image_size)


def inflate_height(image_size: str, extra_height: int) -> str:
    """将 '宽*高' 格式的尺寸中的高度增加 extra_height 像素。

    例如 inflate_height('960*1280', 40) → '960*1320'
    """
    match = re.match(r"(\d+)\*(\d+)", image_size)
    if not match:
        return image_size
    width, height = int(match.group(1)), int(match.group(2))
    return f"{width}*{height + extra_height}"


def extract_image_url_from_result(result: dict | None) -> str | None:
    """从 MCP 工具调用结果中提取第一张图片的 URL。

    API 返回格式示例（嵌套在 content[].text 中的 JSON）::

        {
          "images": ["https://...png?Expires=..."],
          "total": 1,
          "succeeded": 1
        }
    """
    if result is None:
        return None

    content_items = result.get("content", [])
    for item in content_items:
        item_type = item.get("type", "text")
        if item_type == "text":
            text = item.get("text", "")
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    # 优先匹配实际返回的 images 数组
                    images = parsed.get("images")
                    if isinstance(images, list) and images:
                        return images[0]
            except (json.JSONDecodeError, TypeError):
                stripped = text.strip()
                if stripped.startswith("http"):
                    return stripped
        elif item_type == "image":
            data = item.get("data", "")
            if data:
                return data
    return None


def download_image(url: str) -> Image.Image:
    """从 URL 下载图片并返回 PIL Image 对象。"""
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=60) as response:
        image_data = response.read()
    return Image.open(io.BytesIO(image_data))


def crop_bottom(image: Image.Image, pixels: int) -> Image.Image:
    """裁剪掉图片底部指定像素的区域。"""
    width, height = image.size
    if pixels >= height:
        print(f"⚠️  裁剪高度 ({pixels}px) 大于等于图片高度 ({height}px)，跳过裁剪", file=sys.stderr)
        return image
    return image.crop((0, 0, width, height - pixels))


def register(subparsers) -> None:
    """Register the generation-poster-by-text subcommand into the CLI."""
    parser = subparsers.add_parser(
        "generation-poster-by-text",
        help="根据自然语言描述生成创意海报",
        description="根据文字描述调用 creative-poster-generator MCP 生成海报",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--text",
        required=True,
        help="海报描述文本，详细描述主题、风格、元素、色调等",
    )
    parser.add_argument(
        "--image-size",
        default="960*1280",
        help='默认用928*1664 9:16, 生成的图片分辨率，默认分辨率为1664*928，可选的分辨率及其对应的图像宽高比例为：  1664*928（默认值）：16:9；1472*1104：4:3；1328*1328：1:1；1104*1472：3:4； 928*1664：9:16',
    )
    parser.set_defaults(handler=run)


def run(args) -> None:
    """Execute the generation-poster-by-text command."""
    if not ensure_mcp_skill(MCP_NAME, MCP_ID):
        print("❌ 无法确保 MCP 技能就绪，请检查网络或配置", file=sys.stderr)
        sys.exit(1)

    user_image_size = normalize_image_size(args.image_size)
    # 高度 +30px 以补偿 API 底部 "AI 生成" 水印
    inflated_image_size = inflate_height(user_image_size, AI_WATERMARK_HEIGHT)

    params = {
        "input": args.text,
        "image_size": inflated_image_size,
        "seed": 0,
        "watermark": False,
        "prompt_extend": True,
        "negative_prompt": "中文文字错误 / 四不像文字 / 中文乱码 / 文字严重错乱重叠 / 水印"
    }

    print("🎨 正在生成海报...")
    print(f"   描述: {args.text}")
    print(f"   期望尺寸: {user_image_size}")
    print(f"   请求尺寸: {inflated_image_size}（+{AI_WATERMARK_HEIGHT}px 补偿 AI 水印）")

    url = get_mcp_url_by_subskillname(MCP_NAME)
    resolved_url = resolve_url(url)

    # 直接调用 send_mcp_request 以获取原始结果
    call_params = {
        "name": TOOL_NAME,
        "arguments": params,
    }
    result = send_mcp_request(resolved_url, "tools/call", call_params)

    if result is None or result.get("isError", False):
        print("❌ 海报生成失败", file=sys.stderr)
        if result:
            for item in result.get("content", []):
                if item.get("type") == "text":
                    print(f"   {item.get('text', '')}", file=sys.stderr)
        sys.exit(1)

    image_url = extract_image_url_from_result(result)
    if not image_url:
        print("❌ 未能从生成结果中提取到图片 URL", file=sys.stderr)
        print(f"   原始结果: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)

    print("📥 正在下载生成的图片...")
    try:
        image = download_image(image_url)
    except Exception as download_error:
        print(f"❌ 图片下载失败: {download_error}", file=sys.stderr)
        sys.exit(1)

    print(f"原始图片链接: { image_url }")
    print(f"   原始图片尺寸: {image.size[0]}x{image.size[1]}")

    # 裁剪底部 AI 水印区域
    cropped_image = crop_bottom(image, AI_WATERMARK_HEIGHT)
    print(f"   裁剪后尺寸: {cropped_image.size[0]}x{cropped_image.size[1]}")

    # 保存到 output_dir/poster 目录
    context = get_skill_context()
    poster_dir = Path(context.get("output_dir")) / "poster"
    poster_dir.mkdir(parents=True, exist_ok=True)

    filename = f"poster_{int(time.time())}.png"
    output_path = poster_dir / filename
    cropped_image.save(str(output_path), format="PNG")

    print()
    print(f"✅ 海报已生成：{output_path}")
    print(json.dumps({"url": str(output_path)}, ensure_ascii=False))
    sys.exit(0)