#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
amazon_image_post.py — Amazon 图片后处理

从 workflow 结果中的 images_raw（#ivThumbs .ivThumbImage 的 style 属性数组）
提取 background-url 并放大为指定尺寸，输出干净的 images 数组。

用法:
  python scripts/run_crawl.py scrape --site amazon-us --url ... | python scripts/amazon_image_post.py
  python scripts/amazon_image_post.py --file result.json
  python scripts/amazon_image_post.py --file result.json --size 1500
"""

import argparse
import json
import re
import sys

# ── UTF-8 ────────────────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Amazon 图片尺寸替换规则 ─────────────────────────────────────────
# 来源: parse-dom.ts ZOOM_RULES，新增规则 0 处理图像查看器缩略图 URL
ZOOM_RULES: list[tuple[re.Pattern, str]] = [
    #  0: 查看器缩略图 _AC_SR38,50_AA50_ → _AC_SL{s}_
    #      ⚠️ 必须在 Rule 8 之前：_AC_SR 无 _AA 后缀的 URL 会落入 Rule 8
    (re.compile(r"\._AC_SR\d{2,3},\d{2,3}_AA\d{2,3}_\."), "._AC_SL{}_."),
    #  0.5: 纯 AA 正方形缩略图 _AA50_ → _SL{s}_（无 _AC_SR 前缀的缩略图变体）
    #        Rule 0 处理复合 _AC_SR..._AA... 模式，本条匹配裸 _AA 模式
    (re.compile(r"\._AA\d{2,3}_\."), "._SL{}_."),
    #  1: _SS38_ → _SS{s}_
    (re.compile(r"\._?SS\d{2,3}_\."), "._SS{}_."),
    #  2: _SY38. → _SY{s}.
    (re.compile(r"\._SY\d{2,3}\."), "._SY{}."),
    #  3: _SX38_SY38_CR,0,0,38,38_ → _SX{s}_SY{s}_CR,0,0,{s},{s}_
    (re.compile(r"\._SX\d{2,3}_SY\d{2,3}_CR,0,0,\d{2,3},\d{2,3}_\."),
     "._SX{}_SY{}_CR,0,0,{},{}_."),
    #  4: _SR38,38_ → _SR{s},{s}_
    (re.compile(r"\._SR\d{2,3},\d{2,3}_\."), "._SR{},{}_."),
    #  5: _AC_SX38_CR,0,0,38,38_ → _AC_SX{s}_CR,0,0,{s},{s}_
    (re.compile(r"\._AC_SX\d{2,3}_CR,0,0,\d{2,3},\d{2,3}_\."),
     "._AC_SX{}_CR,0,0,{},{}_."),
    #  6: _AC_SX38_SY38_CR,0,0,38,38_ → _AC_SX{s}_SY{s}_CR,0,0,{s},{s}_
    (re.compile(r"\._AC_SX\d{2,3}_SY\d{2,3}_CR,0,0,\d{2,3},\d{2,3}_\."),
     "._AC_SX{}_SY{}_CR,0,0,{},{}_."),
    #  7: _US38_ → _US{s}_
    (re.compile(r"\._US\d{2,3}_\."), "._US{}_."),
    #  8: _AC_SR38,38_ → _AC_SR{s},{s}_
    (re.compile(r"\._AC_SR\d{2,3},\d{2,3}_\."), "._AC_SR{},{}_."),
    #  9: _AC_US38_ → _AC_US{s}_
    (re.compile(r"\._AC_US\d{2,3}_\."), "._AC_US{}_."),
    # 10: _AC_UL38_QL38_ → _AC_US{s}_
    (re.compile(r"\._AC_UL\d{2,3}_QL\d{2,3}_\."), "._AC_US{}_."),
    # 11: _AC_UL38_ → _AC_US{s}_
    (re.compile(r"\._AC_UL\d{2,3}_\."), "._AC_US{}_."),
    # 12: _MCnd_AC_UL38_FMwebp_QL38_ → _MCnd_AC_US{s}_
    (re.compile(r"\._MCnd_AC_UL\d{2,3}_FMwebp_QL\d{2,3}_\."),
     "._MCnd_AC_US{}_."),
    # 13: _MCnd_AC_UL38_ → _MCnd_AC_US{s}_
    (re.compile(r"\._MCnd_AC_UL\d{2,3}_\."), "._MCnd_AC_US{}_."),
    # 14: _AC_SL38_QL38_ → _AC_SS{s}_
    (re.compile(r"\._AC_SL\d{2,3}_QL\d{2,3}_\."), "._AC_SS{}_."),
    # 15: _AC_SL38_ → _AC_SS{s}_
    (re.compile(r"\._AC_SL\d{2,3}_\."), "._AC_SS{}_."),
    # 16: _SL38_ → _SL{s}_
    (re.compile(r"\._SL\d{2,3}_\."), "._SL{}_."),
]


def extract_url_from_style(style: str) -> str | None:
    """从 style="background: url(...)" 中提取 URL。"""
    m = re.search(r'url\("([^"]+)"\)', style)
    return m.group(1) if m else None


def upscale_url(url: str, size: int = 1500) -> str:
    """
    将 Amazon 缩略图 URL 放大到指定尺寸。
    依次匹配 ZOOM_RULES，命中则替换；无一命中返回原 URL。
    """
    s = str(size)
    for pattern, template in ZOOM_RULES:
        if pattern.search(url):
            return pattern.sub(template.format(s, s, s, s), url)
    return url


def process_images_raw(images_raw: list[str], size: int = 1500) -> list[str]:
    """处理 images_raw 数组，提取 URL 并放大。

    兼容两种格式：
    - viewer 数据：style="background: url(...); ..."  → 提取 url("...") 中的 URL
    - #altImages 兜底：裸 URL（如 https://..._SS40_.jpg）
    过滤空字符串和 placeholder。
    """
    result: list[str] = []
    for raw in images_raw:
        url = extract_url_from_style(raw)
        if not url and raw.startswith("http"):
            url = raw
        if url:
            result.append(upscale_url(url, size))
    return result


def post_process(data: dict, size: int = 1500) -> dict:
    """
    对 workflow 结果做图片后处理：
    1. images_raw → images（提取 URL + 尺寸放大）
    2. 保留原始 images_raw 为 images_raw（供调试）
    """
    inner = data.get("data", {})
    if isinstance(inner, str):
        try:
            inner = json.loads(inner)
        except (json.JSONDecodeError, TypeError):
            return data

    inner_data = inner.get("data", {}) if isinstance(inner, dict) else {}
    if not isinstance(inner_data, dict):
        return data

    images_raw = inner_data.get("images_raw")
    if images_raw and isinstance(images_raw, list):
        images = process_images_raw(images_raw, size)
        inner_data["images"] = images

        # 回写到嵌套结构中
        if isinstance(data.get("data"), str):
            inner["data"] = inner_data
            data["data"] = json.dumps(inner, ensure_ascii=False)
        else:
            data["data"] = inner

    return data


def main():
    parser = argparse.ArgumentParser(
        description="Amazon 图片后处理 — 从 images_raw 提取并放大图片 URL"
    )
    parser.add_argument("--file", "-f", help="输入 JSON 文件路径（默认从 stdin 读取）")
    parser.add_argument("--size", "-s", type=int, default=1500,
                        help="目标图片尺寸（默认 1500）")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    result = post_process(raw, args.size)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
