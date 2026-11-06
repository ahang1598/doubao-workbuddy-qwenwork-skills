#!/usr/bin/env python3
"""
DOCX -> Markdown 图片后处理脚本。

背景：MarkItDown 把 DOCX 内嵌图片以 data URI 形式写进 Markdown
（如 "![](data:image/png;base64,...)"）。当图片较大时，base64 内容会被
截断成 "...", 只留下 "data:image/png;base64..." 占位符，导致 Markdown
阅读器中图片无法显示。此外，内嵌超大 base64 对 Markdown 本身也不友好。

本脚本在 MarkItDown 输出 Markdown 之后执行：
  1. 用 zipfile 直接解析 DOCX：
       - 读取 word/document.xml，按文档顺序提取所有 r:embed 的 rId；
       - 读取 word/_rels/document.xml.rels，建立 rId -> media 文件映射；
       - 把 word/media/ 下对应文件按文档顺序（r:embed 真实出现顺序，而非
         文件名排序，避免图文错位）提取到 md 同目录的图片子文件夹。
  2. 把 md 里的 "![](data:image/xxx;base64...)" 占位符按位置顺序逐一替换
     为相对路径引用（如 "![](assets/<文档名>_media/image_01.png)"）。

仅依赖 Python 标准库（zipfile、re、os、argparse）。

用法：
  作为库调用：
      from extract_docx_images import postprocess_docx_images
      postprocess_docx_images("输入.docx", "输出.md")

  作为命令行：
      python scripts/extract_docx_images.py 输入.docx 输出.md
      python scripts/extract_docx_images.py 输入.docx 输出.md --media-dir 图片
"""

import argparse
import os
import re
import sys
import zipfile
from pathlib import Path

# 匹配 Markdown 中的 data-URI 图片占位符，例如：
#   ![](data:image/png;base64...)
#   ![Image](data:image/png;base64,XXXX)
# 同时覆盖：普通 http(s)/相对路径的图片不受影响（不属于 data:image）。
_DATA_IMG_PATTERN = re.compile(r'!\[[^\]]*\]\(data:image/[^)]*\)')


def _extract_embed_order_and_rels(docx_path):
    """
    解析 DOCX，返回 (embed_r_ids, rId_to_media)：
      - embed_r_ids: word/document.xml 中 r:embed 出现的顺序列表
      - rId_to_media: rId -> media 文件名（如 image1.png）
    只依赖 zipfile + re。
    """
    try:
        with zipfile.ZipFile(docx_path) as z:
            names = set(z.namelist())
            document_part = "word/document.xml"
            rels_part = "word/_rels/document.xml.rels"

            if document_part not in names:
                raise ValueError(
                    f"'{docx_path}' 不是有效的 DOCX（缺少 {document_part}）"
                )

            doc_xml = z.read(document_part).decode("utf-8", errors="replace")
            rels_xml = z.read(rels_part).decode("utf-8", errors="replace") \
                if rels_part in names else ""

    except zipfile.BadZipFile as e:
        raise ValueError(f"'{docx_path}' 不是有效的 ZIP/DOCX 文件: {e}") from e

    # 1) 按文档顺序提取所有 r:embed 的 rId
    embed_r_ids = re.findall(r'r:embed="(rId\d+)"', doc_xml)

    # 2) rId -> media 目标文件名
    #    rels 中的 Target 是相对 word/document.xml 所在目录（word/）的，
    #    需解析成压缩包内绝对路径（如 word/media/image1.png）。
    rel_map = {}
    for rid, target in re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels_xml):
        if not target:
            continue
        if target.startswith("/"):  # 绝对路径（罕见），去掉前导 /
            target = target.lstrip("/")
        else:  # 相对路径：以 document part 所在目录（word/）为基准
            doc_dir = Path(document_part).parent.as_posix()
            if doc_dir:
                target = f"{doc_dir}/{target}"
        rel_map[rid] = target

    return embed_r_ids, rel_map


def _ordered_media_files(embed_r_ids, rel_map):
    """
    按 r:embed 顺序返回 media 文件相对路径列表（如 word/media/image1.png）。
    若 docx 中某 rId 无对应目标，会跳过并打印警告。
    """
    ordered = []
    for rid in embed_r_ids:
        target = rel_map.get(rid)
        if not target:
            print(f"[extract_docx_images] 警告: 找不到 {rid} 对应的 media 文件", file=sys.stderr)
            continue
        ordered.append(target)
    return ordered


def _detect_placeholders(md_text):
    """
    找出 md 中所有 data-URI 图片占位符的位置。
    返回 list[(start, end, matched_text)]，按出现顺序排列。
    """
    return [(m.start(), m.end(), m.group(0)) for m in _DATA_IMG_PATTERN.finditer(md_text)]


def postprocess_docx_images(
    docx_path,
    md_path,
    media_dir=None,
    overwrite=False,
    in_place=True,
):
    """
    对 MarkItDown 生成的 md 执行 DOCX 图片后处理。

    参数：
        docx_path: 源 DOCX 路径
        md_path:   生成的 Markdown 路径
        media_dir: 图片子文件夹名（相对 md 所在目录）。
                   默认 "assets/<docx 文件名>_media/"。
        overwrite: 图片文件已存在时是否覆盖（默认 False，避免误覆盖已有文件）
        in_place:  为 True 时直接改写 md 文件；否则返回替换后的字符串而不写回。

    返回：
        若 in_place 为 False，返回 (替换后的 md 文本, 处理的图片数)；
        否则返回 (True/False 表示是否有占位符被处理, 处理的图片数)。
    """
    docx_path = Path(docx_path)
    md_path = Path(md_path)
    if not docx_path.exists():
        raise FileNotFoundError(f"DOCX 文件不存在: {docx_path}")
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown 文件不存在: {md_path}")

    # 读取 md（UTF-8，Windows 中文路径/内容安全）
    md_text = md_path.read_text(encoding="utf-8")
    placeholders = _detect_placeholders(md_text)

    if not placeholders:
        # 没有 data-URI 占位符，无需处理
        return (False, 0) if in_place else (md_text, 0)

    # 解析 DOCX，按文档顺序获取 media 文件
    embed_r_ids, rel_map = _extract_embed_order_and_rels(docx_path)
    ordered_media = _ordered_media_files(embed_r_ids, rel_map)

    if not ordered_media:
        raise RuntimeError("DOCX 中未解析到任何可用的 media 图片")

    # 图片子文件夹（相对 md 所在目录）
    if media_dir is None:
        media_dir = f"assets/{docx_path.stem}_media"
    img_dir_rel = Path(media_dir)
    img_dir_abs = md_path.parent / img_dir_rel
    img_dir_abs.mkdir(parents=True, exist_ok=True)

    # 逐个提取 media 文件，命名 image_01.png...
    extracted = []
    with zipfile.ZipFile(docx_path) as z:
        for idx, media_rel in enumerate(ordered_media, start=1):
            try:
                data = z.read(media_rel)
            except KeyError:
                print(
                    f"[extract_docx_images] 警告: 压缩包内不存在 {media_rel}",
                    file=sys.stderr,
                )
                continue
            ext = Path(media_rel).suffix or ".bin"
            img_name = f"image_{idx:02d}{ext}"
            img_path = img_dir_abs / img_name
            if overwrite or not img_path.exists():
                img_path.write_bytes(data)
            extracted.append(f"{img_dir_rel.as_posix()}/{img_name}")

    if not extracted:
        raise RuntimeError("图片提取失败，未写入任何图片文件")

    # 用相对路径逐一替换占位符（按 r:embed 顺序对应 md 中图片出现顺序）
    used = 0
    def _repl(m):
        nonlocal used
        if used >= len(extracted):
            return m.group(0)
        path = extracted[used]
        used += 1
        # 去掉旧 alt 文本里可能残留的字符，保留简单空 alt
        return f"![]({path})"

    new_md_text = _DATA_IMG_PATTERN.sub(_repl, md_text)

    # 占位符数量与图片数量不一致时给出提示
    if len(placeholders) != used:
        print(
            f"[extract_docx_images] 提示: md 中有 {len(placeholders)} 个占位符，"
            f"按顺序替换了 {used} 个，DOCX 中可提取 {len(extracted)} 张图",
            file=sys.stderr,
        )

    if not in_place:
        return new_md_text, used

    # 写回 md（UTF-8）
    md_path.write_text(new_md_text, encoding="utf-8")
    print(
        f"[extract_docx_images] 已提取 {used} 张图片 -> {img_dir_rel.as_posix()}/"
        f" 并更新 {md_path.name} 中的图片引用"
    )
    return True, used


def main():
    parser = argparse.ArgumentParser(
        description="DOCX 转 Markdown 后的图片后处理：把被截断的 data-URI 图片占位符"
                    "替换为从 DOCX 中提取的相对路径图片。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python scripts/extract_docx_images.py 输入.docx 输出.md

  # 自定义图片子文件夹名
  python scripts/extract_docx_images.py 输入.docx 输出.md --media-dir 图片
        """,
    )
    parser.add_argument("docx", type=Path, help="源 DOCX 文件路径")
    parser.add_argument("md", type=Path, help="生成的 Markdown 文件路径")
    parser.add_argument(
        "--media-dir",
        default=None,
        help="图片子文件夹名（相对 md 所在目录），默认 assets/<文档名>_media",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="已存在的图片文件也覆盖重写",
    )
    args = parser.parse_args()

    try:
        handled, count = postprocess_docx_images(
            docx_path=args.docx,
            md_path=args.md,
            media_dir=args.media_dir,
            overwrite=args.overwrite,
        )
    except Exception as e:
        print(f"[extract_docx_images] 错误: {e}", file=sys.stderr)
        sys.exit(1)

    if count:
        print(f"[extract_docx_images] 完成：处理了 {count} 张图片")
        sys.exit(0)
    else:
        print("[extract_docx_images] 未检测到需要处理的 data-URI 图片占位符，跳过。")
        sys.exit(0)


if __name__ == "__main__":
    main()
