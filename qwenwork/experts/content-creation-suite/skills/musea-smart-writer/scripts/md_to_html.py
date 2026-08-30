#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 Markdown 文章转换为适合平台发布的 HTML 文件。
支持微信公众号和今日头条两种平台样式，图片以 base64 内嵌。

用法：
    python3 md_to_html.py --md <md文件路径> --html <html输出路径> --platform <wechat|toutiao> [--images <key1:path1> <key2:path2> ...]

示例（微信公众号）：
    python3 md_to_html.py --md article.md --html article_wechat.html --platform wechat \
        --images cover:封面图.png diagram:示意图.png

示例（今日头条）：
    python3 md_to_html.py --md article.md --html article_toutiao.html --platform toutiao
"""

import re
import os
import base64
import argparse
from pathlib import Path

# ============================================================
# 安全路径校验
# ============================================================

# 允许的输入文件扩展名
ALLOWED_INPUT_EXTENSIONS = {'.md', '.markdown', '.txt'}
# 允许的输出文件扩展名
ALLOWED_OUTPUT_EXTENSIONS = {'.html', '.htm'}
# 允许的图片文件扩展名
ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'}
# 图片文件最大大小（20MB）
MAX_IMAGE_SIZE = 20 * 1024 * 1024


def _get_allowed_dirs():
    """获取允许访问的目录列表（仅当前工作目录）"""
    return [os.path.realpath(os.getcwd())]


def validate_read_path(file_path, allowed_extensions=None, description="文件"):
    """校验读取文件路径的安全性

    Args:
        file_path: 待校验的文件路径
        allowed_extensions: 允许的文件扩展名集合
        description: 文件描述（用于错误提示）

    Returns:
        解析后的绝对路径

    Raises:
        ValueError: 路径不合法时抛出
    """
    if not file_path or not file_path.strip():
        raise ValueError(f"{description}路径不能为空")

    # 解析为绝对路径（消除 ../ 等相对路径）
    resolved = os.path.realpath(os.path.abspath(file_path))

    # 检查路径遍历：只允许在当前工作目录下
    allowed_dirs = _get_allowed_dirs()
    path_allowed = any(
        resolved.startswith(d + os.sep) or resolved == d
        for d in allowed_dirs
    )
    if not path_allowed:
        raise ValueError(
            f"{description}路径不安全：只允许访问当前工作目录下的文件。"
            f"路径：{file_path} -> {resolved}"
        )

    # 检查文件扩展名
    if allowed_extensions:
        ext = os.path.splitext(resolved)[1].lower()
        if ext not in allowed_extensions:
            raise ValueError(
                f"{description}扩展名不合法：'{ext}'，允许的扩展名：{allowed_extensions}"
            )

    # 检查文件是否存在
    if not os.path.exists(resolved):
        raise ValueError(f"{description}不存在：{resolved}")

    # 检查是否为符号链接指向外部（防止 symlink 攻击）
    if os.path.islink(file_path):
        link_target = os.path.realpath(file_path)
        if not any(link_target.startswith(d + os.sep) for d in allowed_dirs):
            raise ValueError(f"{description}路径不安全：符号链接指向不允许的位置")

    return resolved


def validate_write_path(file_path, allowed_extensions, input_file_path, description="输出文件"):
    """校验写入文件路径的安全性（严格限制写入范围）

    输出文件只允许写入到：输入文件所在目录 或 当前工作目录（二者取其一）。

    Args:
        file_path: 待校验的输出文件路径
        allowed_extensions: 允许的文件扩展名集合
        input_file_path: 已校验的输入文件绝对路径（用于确定允许写入的目录）
        description: 文件描述（用于错误提示）

    Returns:
        解析后的绝对路径

    Raises:
        ValueError: 路径不合法时抛出
    """
    if not file_path or not file_path.strip():
        raise ValueError(f"{description}路径不能为空")

    # 解析为绝对路径
    resolved = os.path.normpath(os.path.abspath(file_path))

    # 写入范围严格限制：只允许写入输入文件所在目录 或 当前工作目录
    cwd = os.path.realpath(os.getcwd())
    input_dir = os.path.dirname(os.path.realpath(input_file_path))
    allowed_write_dirs = [cwd, input_dir]

    output_dir = os.path.dirname(resolved)
    output_dir_real = os.path.realpath(output_dir)

    write_allowed = any(
        output_dir_real == d or output_dir_real.startswith(d + os.sep)
        for d in allowed_write_dirs
    )
    if not write_allowed:
        raise ValueError(
            f"{description}路径不安全：输出文件只允许写入当前工作目录或输入文件所在目录。"
            f"路径：{file_path}，允许的目录：{allowed_write_dirs}"
        )

    # 确保输出目录已存在（不允许创建任意目录）
    if not os.path.isdir(output_dir):
        raise ValueError(
            f"{description}的父目录不存在：{output_dir}。请先创建目录或指定已存在的目录。"
        )

    # 检查文件扩展名
    ext = os.path.splitext(resolved)[1].lower()
    if ext not in allowed_extensions:
        raise ValueError(
            f"{description}扩展名不合法：'{ext}'，允许的扩展名：{allowed_extensions}"
        )

    # 防止覆盖输入文件
    if os.path.realpath(resolved) == os.path.realpath(input_file_path):
        raise ValueError(f"{description}不能与输入文件相同")

    return resolved


# ============================================================
# 平台样式配置
# ============================================================

PLATFORM_STYLES = {
    "wechat": {
        "name": "微信公众号",
        "body": "max-width: 680px; margin: 0 auto; padding: 20px 16px; font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Microsoft YaHei', sans-serif; font-size: 15px; color: #3F3F3F; line-height: 1.75; background: #fff;",
        "h1": "font-size: 22px; font-weight: bold; color: #1a1a1a; text-align: center; margin: 0 0 20px 0; padding-bottom: 12px; border-bottom: 1px solid #eee;",
        "h2": "font-size: 17px; font-weight: bold; color: #1e6bb8; margin: 28px 0 12px 0; padding-left: 10px; border-left: 4px solid #1e6bb8;",
        "h3": "font-size: 16px; font-weight: bold; color: #333; margin: 20px 0 8px 0;",
        "paragraph": "margin: 0 0 16px 0; text-align: justify;",
        "blockquote": "margin: 16px 0; padding: 12px 16px; background: #f7f7f7; border-left: 3px solid #1e6bb8; color: #666; font-style: italic; font-size: 14px;",
        "list_item": "margin: 4px 0; padding-left: 4px;",
        "separator": "text-align: center; margin: 24px 0; color: #ccc; letter-spacing: 8px;",
        "image": "display: block; max-width: 100%; margin: 16px auto; border-radius: 4px;",
        "image_caption": "text-align: center; font-size: 12px; color: #999; margin: -8px 0 16px 0;",
        "bold": "font-weight: bold; color: #1e6bb8;",
        "code": "background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 13px; color: #c7254e;",
    },
    "toutiao": {
        "name": "今日头条",
        "body": "max-width: 750px; margin: 0 auto; padding: 20px 16px; font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Microsoft YaHei', sans-serif; font-size: 16px; color: #333; line-height: 1.75; background: #fff;",
        "h1": "font-size: 24px; font-weight: bold; color: #222; text-align: center; margin: 0 0 24px 0; padding-bottom: 16px; border-bottom: 2px solid #e74c3c;",
        "h2": "font-size: 18px; font-weight: bold; color: #222; margin: 28px 0 12px 0; padding-bottom: 6px; border-bottom: 1px solid #eee;",
        "h3": "font-size: 17px; font-weight: bold; color: #333; margin: 20px 0 8px 0;",
        "paragraph": "margin: 0 0 16px 0; text-align: justify;",
        "blockquote": "margin: 16px 0; padding: 12px 16px; background: #f9f9f9; border-left: 3px solid #ddd; color: #666; font-size: 15px;",
        "list_item": "margin: 4px 0; padding-left: 4px;",
        "separator": "text-align: center; margin: 24px 0; color: #ccc; letter-spacing: 8px;",
        "image": "display: block; max-width: 100%; margin: 16px auto; border-radius: 4px;",
        "image_caption": "text-align: center; font-size: 13px; color: #999; margin: -8px 0 16px 0;",
        "bold": "font-weight: bold; color: #e74c3c;",
        "code": "background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 14px; color: #c0392b;",
    },
}


def image_to_base64(image_path):
    """将图片文件转为 base64 data URI"""
    # 安全校验图片路径
    try:
        validated_path = validate_read_path(
            image_path,
            allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
            description="图片"
        )
    except ValueError as e:
        print(f"警告：图片路径校验失败 - {e}")
        return None

    # 检查文件大小，防止读取过大文件导致内存耗尽
    file_size = os.path.getsize(validated_path)
    if file_size > MAX_IMAGE_SIZE:
        print(f"警告：图片文件过大（{file_size / 1024 / 1024:.1f}MB），最大允许 {MAX_IMAGE_SIZE / 1024 / 1024:.0f}MB")
        return None

    extension = Path(validated_path).suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    mime_type = mime_map.get(extension, "image/png")

    with open(validated_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def is_separator_line(text):
    """判断是否为分隔线"""
    stripped = text.strip()
    if stripped.startswith("---"):
        return True
    if len(stripped) <= 10 and stripped and all(c == stripped[0] for c in stripped):
        return True
    if len(stripped) >= 2 and not any(c.isalnum() for c in stripped):
        return True
    return False


def process_inline_formatting(text, styles):
    """处理内联格式（加粗、行内代码、链接）"""
    # 去掉 markdown 链接，保留文字
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # 处理行内代码
    text = re.sub(
        r"`([^`]+)`",
        lambda m: f'<code style="{styles["code"]}">{m.group(1)}</code>',
        text,
    )

    # 处理加粗
    text = re.sub(
        r"\*\*([^*]+)\*\*",
        lambda m: f'<strong style="{styles["bold"]}">{m.group(1)}</strong>',
        text,
    )

    return text


def generate_image_html(data_uri, caption, styles):
    """生成图片 HTML（base64 内嵌）"""
    html = f'<img src="{data_uri}" style="{styles["image"]}" alt="{caption}">\n'
    html += f'<p style="{styles["image_caption"]}">{caption}</p>\n'
    return html


def convert_md_to_html(md_file, html_file, platform, images_dict=None):
    """将 Markdown 文件转换为平台适配的 HTML 文件

    Args:
        md_file: Markdown 文件路径
        html_file: 输出的 HTML 文件路径
        platform: 目标平台 (wechat / toutiao)
        images_dict: 图片映射字典 {关键词: 图片路径}
    """
    if images_dict is None:
        images_dict = {}

    if platform not in PLATFORM_STYLES:
        print(f"错误：不支持的平台 '{platform}'，支持的平台：{list(PLATFORM_STYLES.keys())}")
        return

    styles = PLATFORM_STYLES[platform]

    # 安全校验输入文件路径（必须存在且在工作目录下）
    validated_md = validate_read_path(
        md_file,
        allowed_extensions=ALLOWED_INPUT_EXTENSIONS,
        description="Markdown 输入文件"
    )

    # 安全校验输出文件路径（仅允许写入输入文件同目录或工作目录）
    validated_html = validate_write_path(
        html_file,
        allowed_extensions=ALLOWED_OUTPUT_EXTENSIONS,
        input_file_path=validated_md,
        description="HTML 输出文件"
    )

    # 安全校验所有图片路径（必须存在且在工作目录下）
    validated_images = {}
    for key, img_path in images_dict.items():
        try:
            validated_img = validate_read_path(
                img_path,
                allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
                description=f"图片({key})"
            )
            validated_images[key] = validated_img
        except ValueError as e:
            print(f"警告：跳过图片 '{key}' - {e}")

    with open(validated_md, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")

    # 构建 HTML
    body_content = []
    inserted_keys = set()  # 跟踪已插入的图片，每个 key 最多插入一次
    skip_image_suggestions = False
    prev_was_empty = False
    in_list = False
    list_type = None  # "ul" or "ol"

    for line in lines:
        line_stripped = line.rstrip()

        # 跳过"配图建议"和"元信息"部分（文末的辅助信息不写入 HTML）
        if (line_stripped.startswith("## 配图建议") or line_stripped.startswith("## 配图需求")
                or "【配图建议】" in line_stripped or "【配图需求】" in line_stripped
                or line_stripped.startswith("**元信息**") or line_stripped.startswith("## 元信息")):
            skip_image_suggestions = True
            continue
        if skip_image_suggestions:
            continue

        # 空行处理
        if not line_stripped.strip():
            if in_list:
                # 列表结束
                tag = "ul" if list_type == "ul" else "ol"
                body_content.append(f"</{tag}>")
                in_list = False
                list_type = None
            if not prev_was_empty:
                prev_was_empty = True
            continue
        prev_was_empty = False

        # 分隔线
        if is_separator_line(line_stripped):
            if in_list:
                tag = "ul" if list_type == "ul" else "ol"
                body_content.append(f"</{tag}>")
                in_list = False
                list_type = None
            body_content.append(f'<p style="{styles["separator"]}">— — —</p>')
            continue

        # 标题处理
        is_heading = False
        if line_stripped.startswith("### "):
            if in_list:
                tag = "ul" if list_type == "ul" else "ol"
                body_content.append(f"</{tag}>")
                in_list = False
                list_type = None
            text = process_inline_formatting(line_stripped[4:].strip(), styles)
            body_content.append(f'<h3 style="{styles["h3"]}">{text}</h3>')
            is_heading = True
        elif line_stripped.startswith("## "):
            if in_list:
                tag = "ul" if list_type == "ul" else "ol"
                body_content.append(f"</{tag}>")
                in_list = False
                list_type = None
            text = process_inline_formatting(line_stripped[3:].strip(), styles)
            body_content.append(f'<h2 style="{styles["h2"]}">{text}</h2>')
            is_heading = True
        elif line_stripped.startswith("# "):
            if in_list:
                tag = "ul" if list_type == "ul" else "ol"
                body_content.append(f"</{tag}>")
                in_list = False
                list_type = None
            text = process_inline_formatting(line_stripped[2:].strip(), styles)
            body_content.append(f'<h1 style="{styles["h1"]}">{text}</h1>')
            is_heading = True
            # 封面图插在主标题下方
            if "cover" in validated_images and "cover" not in inserted_keys:
                data_uri = image_to_base64(validated_images["cover"])
                if data_uri:
                    body_content.append(generate_image_html(data_uri, "封面图 | AI 生成", styles))
                    inserted_keys.add("cover")

        # 引用块
        elif line_stripped.startswith("> "):
            if in_list:
                tag = "ul" if list_type == "ul" else "ol"
                body_content.append(f"</{tag}>")
                in_list = False
                list_type = None
            text = process_inline_formatting(line_stripped[2:].strip(), styles)
            body_content.append(f'<blockquote style="{styles["blockquote"]}">{text}</blockquote>')

        # 无序列表
        elif line_stripped.startswith("- ") or line_stripped.startswith("* "):
            if not in_list or list_type != "ul":
                if in_list:
                    tag = "ul" if list_type == "ul" else "ol"
                    body_content.append(f"</{tag}>")
                body_content.append("<ul>")
                in_list = True
                list_type = "ul"
            text = process_inline_formatting(line_stripped[2:].strip(), styles)
            body_content.append(f'<li style="{styles["list_item"]}">{text}</li>')

        # 有序列表
        elif re.match(r"^\d+\.\s", line_stripped):
            if not in_list or list_type != "ol":
                if in_list:
                    tag = "ul" if list_type == "ul" else "ol"
                    body_content.append(f"</{tag}>")
                body_content.append("<ol>")
                in_list = True
                list_type = "ol"
            text = re.sub(r"^\d+\.\s", "", line_stripped).strip()
            text = process_inline_formatting(text, styles)
            body_content.append(f'<li style="{styles["list_item"]}">{text}</li>')

        # 普通段落
        else:
            if in_list:
                tag = "ul" if list_type == "ul" else "ol"
                body_content.append(f"</{tag}>")
                in_list = False
                list_type = None
            text = process_inline_formatting(line_stripped, styles)
            body_content.append(f'<p style="{styles["paragraph"]}">{text}</p>')

        # 在标题行后插入对应配图（仅匹配标题行，每个 key 最多插入一次）
        if is_heading:
            for key, img_path in validated_images.items():
                if key != "cover" and key not in inserted_keys and key.lower() in line_stripped.lower():
                    data_uri = image_to_base64(img_path)
                    if data_uri:
                        body_content.append(generate_image_html(data_uri, f"{key} | AI 生成", styles))
                        inserted_keys.add(key)

    # 关闭未结束的列表
    if in_list:
        tag = "ul" if list_type == "ul" else "ol"
        body_content.append(f"</{tag}>")

    # 组装完整 HTML
    platform_name = styles["name"]
    html_output = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{platform_name}文章</title>
</head>
<body style="{styles['body']}">
{chr(10).join(body_content)}
</body>
</html>"""

    with open(validated_html, "w", encoding="utf-8") as f:
        f.write(html_output)

    inserted_count = len(inserted_keys)
    print(f"✓ HTML 文件已生成：{validated_html}")
    print(f"✓ 平台样式：{platform_name}")
    print(f"✓ 已嵌入 {inserted_count} 张图片（base64）")
    print(f"💡 使用方式：浏览器打开 → Ctrl+A 全选 → Ctrl+C 复制 → 粘贴到{platform_name}编辑器")


def main():
    parser = argparse.ArgumentParser(description="将 Markdown 文章转换为平台适配的 HTML 文件")
    parser.add_argument("--md", required=True, help="Markdown 文件路径")
    parser.add_argument("--html", required=True, help="HTML 输出文件路径")
    parser.add_argument(
        "--platform",
        required=True,
        choices=["wechat", "toutiao"],
        help="目标平台：wechat（微信公众号）/ toutiao（今日头条）",
    )
    parser.add_argument(
        "--images",
        nargs="*",
        default=[],
        help="图片映射，格式为 key:path，例如 cover:封面图.png",
    )

    args = parser.parse_args()

    # 解析图片映射
    images_dict = {}
    for img_arg in args.images:
        if ":" in img_arg:
            key, path = img_arg.split(":", 1)
            images_dict[key.strip()] = path.strip()

    try:
        convert_md_to_html(args.md, args.html, args.platform, images_dict)
    except ValueError as e:
        print(f"错误：{e}")
        exit(1)


if __name__ == "__main__":
    main()
