#!/usr/bin/env python3
"""内容提取技能 CLI 入口。

浏览器操作由 Agent 通过 browser_use 完成，本脚本只负责：
下载媒体 → ASR/OCR → 输出结果。

用法：
  python scripts/cli.py extract-douyin --metadata-json '{"play_url":"...","title":"...","subtitle_infos":[...]}'
  python scripts/cli.py extract-xhs --metadata-json '{"feed_id":"...","title":"...","image_urls":[...]}'
  python scripts/cli.py extract-bilibili --url "https://www.bilibili.com/video/BVxxx" --cookie "SESSDATA=xxx;..."
  python scripts/cli.py extract-wechat --url "https://mp.weixin.qq.com/s/xxx"
  python scripts/cli.py extract-xiaoyuzhou --url "https://www.xiaoyuzhoufm.com/episode/xxx"
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import urllib.parse as urlparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("content-breakdown")

_DEFAULT_OUTPUT_DIR = str(Path.home() / ".content-breakdown" / "output")

# ──────────────────────────────── 路径安全校验 ────────────────────────────────

# 允许写入的基目录白名单：用户 home 目录和 /tmp
_ALLOWED_BASE_DIRS = [
    Path.home().resolve(),
    Path("/tmp").resolve(),
]


def _sanitize_output_dir(output_dir: str) -> str:
    """校验并规范化输出目录路径，防止任意文件写入（path traversal）。

    规则：
    1. 拒绝包含 '..' 的路径片段
    2. 使用 resolve() 规范化为绝对路径
    3. 确保路径位于允许的基目录白名单内（用户 home 或 /tmp）
    """
    segments = output_dir.replace("\\", "/").split("/")
    if ".." in segments:
        raise ValueError(f"输出目录路径不安全，不允许包含 '..'：{output_dir}")

    resolved = Path(output_dir).resolve()
    resolved_str = str(resolved)

    for base in _ALLOWED_BASE_DIRS:
        if resolved_str == str(base) or resolved_str.startswith(str(base) + "/"):
            return resolved_str

    allowed_list = ", ".join(str(b) for b in _ALLOWED_BASE_DIRS)
    raise ValueError(
        f"输出目录路径不在允许范围内：{resolved}\n允许的基目录：{allowed_list}"
    )


def _sanitize_input_file(file_path: str) -> str:
    """校验并规范化输入文件路径，防止任意文件读取（path traversal）。

    规则：
    1. 拒绝包含 '..' 的路径片段
    2. 使用 resolve() 规范化为绝对路径
    3. 确保路径位于允许的基目录白名单内（用户 home 或 /tmp）
    """
    segments = file_path.replace("\\", "/").split("/")
    if ".." in segments:
        raise ValueError(f"输入文件路径不安全，不允许包含 '..'：{file_path}")

    resolved = Path(file_path).resolve()
    resolved_str = str(resolved)

    for base in _ALLOWED_BASE_DIRS:
        if resolved_str == str(base) or resolved_str.startswith(str(base) + "/"):
            return resolved_str

    allowed_list = ", ".join(str(b) for b in _ALLOWED_BASE_DIRS)
    raise ValueError(
        f"输入文件路径不在允许范围内：{resolved}\n允许的基目录：{allowed_list}"
    )


# ──────────────────────────────── URL 安全校验 ────────────────────────────────

def _validate_url(url: str) -> str:
    """校验 URL 仅允许 http/https 协议，防止通过 file:// 等协议读取本地文件。"""
    if not url or not isinstance(url, str):
        raise ValueError("URL 不能为空")
    stripped = url.strip()
    if stripped.startswith(("http://", "https://")):
        return stripped
    if "://" not in stripped:
        return "https://" + stripped
    raise ValueError(f"不支持的 URL 协议，仅允许 http/https：{url}")


def _validate_urls(urls: list[str]) -> list[str]:
    """批量校验 URL 列表，仅允许 http/https 协议。"""
    return [_validate_url(u) for u in urls]


def _sanitize_metadata_urls(metadata: dict) -> dict:
    """校验 metadata 中的 URL 字段，仅允许 http/https 协议。"""
    url_keys = ["play_url", "audio_url", "video_url", "cover_url"]
    for key in url_keys:
        if key in metadata and metadata[key]:
            metadata[key] = _validate_url(metadata[key])
    # image_urls 列表
    if "image_urls" in metadata and metadata["image_urls"]:
        metadata["image_urls"] = _validate_urls(metadata["image_urls"])
    return metadata


# ──────────────────────────────── 链接解析工具 ────────────────────────────────
def _parse_xhs_url(url: str) -> tuple[str, str]:
    """从小红书完整链接中解析 feed_id 和 xsec_token。

    支持格式：
    - https://www.xiaohongshu.com/discovery/item/{feed_id}?xsec_token=xxx
    - https://www.xiaohongshu.com/explore/{feed_id}?xsec_token=xxx
    """
    parsed = urlparse.urlparse(url)
    params = urlparse.parse_qs(parsed.query)

    feed_id_match = re.search(r"/(discovery/item|explore)/([a-f0-9]{24})", parsed.path)
    if not feed_id_match:
        raise ValueError(
            f"无法从链接中解析笔记 ID，请确认链接格式正确：\n"
            f"  支持：xiaohongshu.com/explore/{{feed_id}}?xsec_token=xxx\n"
            f"  支持：xiaohongshu.com/discovery/item/{{feed_id}}?xsec_token=xxx\n"
            f"  当前链接：{url}"
        )
    feed_id = feed_id_match.group(2)

    xsec_token = params.get("xsec_token", [None])[0]
    if not xsec_token:
        raise ValueError(
            f"链接中未找到 xsec_token 参数，请使用从小红书分享的完整链接：\n"
            f"  当前链接：{url}"
        )

    return feed_id, xsec_token



# ──────────────────────────────── 内容提取命令 ────────────────────────────────

def cmd_extract_douyin(args: argparse.Namespace) -> None:
    """提取抖音视频内容（字幕/转录）。"""
    from extractor.douyin_extractor import (
        extract_from_play_url,
        extract_from_audio_url,
        extract_from_video_file,
        extract_from_subtitle_infos,
        extract_from_metadata,
    )

    output_dir = _sanitize_output_dir(args.output_dir or _DEFAULT_OUTPUT_DIR)

    if args.metadata_json:
        logger.info("从元数据 JSON 提取内容（browser_use 模式）")
        metadata = _sanitize_metadata_urls(json.loads(args.metadata_json))
        result = extract_from_metadata(
            metadata=metadata,
            output_dir=output_dir,
            whisper_model=args.whisper_model,
            skip_transcript=args.no_transcript,
            extract_keyframes=args.extract_keyframes,
        )
    elif getattr(args, "audio_url", None):
        sanitized_audio_url = _validate_url(args.audio_url)
        logger.info("从音频轨直链提取内容（DASH 分离模式）: %s...", sanitized_audio_url[:60])
        result = extract_from_audio_url(
            audio_url=sanitized_audio_url,
            output_dir=output_dir,
        )
    elif args.play_url:
        sanitized_play_url = _validate_url(args.play_url)
        logger.info("从视频直链提取内容: %s...", sanitized_play_url[:60])
        result = extract_from_play_url(
            play_url=sanitized_play_url,
            output_dir=output_dir,
            whisper_model=args.whisper_model,
            skip_transcript=args.no_transcript,
            extract_keyframes=args.extract_keyframes,
        )
    elif args.video_file:
        sanitized_video_file = _sanitize_input_file(args.video_file)
        logger.info("从本地视频文件提取内容: %s", sanitized_video_file)
        result = extract_from_video_file(
            video_file=sanitized_video_file,
            output_dir=output_dir,
            whisper_model=args.whisper_model,
            skip_transcript=args.no_transcript,
            extract_keyframes=args.extract_keyframes,
        )
    elif args.subtitle_infos_file:
        sanitized_subtitle_file = _sanitize_input_file(args.subtitle_infos_file)
        logger.info("从 API 字幕文件提取内容: %s", sanitized_subtitle_file)
        with open(sanitized_subtitle_file, encoding="utf-8") as subtitle_file:
            subtitle_infos = json.load(subtitle_file)
        result = extract_from_subtitle_infos(
            subtitle_infos=subtitle_infos,
            video_id=args.video_id or "unknown",
            output_dir=output_dir,
        )
    else:
        print(json.dumps({
            "success": False,
            "error": "请提供 --metadata-json、--audio-url、--play-url、--video-file 或 --subtitle-infos-file 之一",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    _print_douyin_result(result)


def cmd_extract_xhs(args: argparse.Namespace) -> None:
    """提取小红书笔记内容（正文 + 图片）。"""
    from extractor.xhs_extractor import extract_from_metadata

    if not args.metadata_json:
        print(json.dumps({
            "success": False,
            "error": "请提供 --metadata-json（Agent 通过 browser_use 从 __INITIAL_STATE__ 提取的元数据 JSON）",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    metadata = _sanitize_metadata_urls(json.loads(args.metadata_json))
    output_dir = _sanitize_output_dir(args.output_dir or _DEFAULT_OUTPUT_DIR)
    feed_id = metadata.get("feed_id", "unknown")
    logger.info("提取小红书笔记: feed_id=%s", feed_id)

    result = extract_from_metadata(
        metadata=metadata,
        output_dir=output_dir,
        download_images_flag=not args.no_download_images,
        extract_keyframes=args.extract_keyframes,
    )

    _print_xhs_result(result)


def cmd_extract_xhs_image_texts(args: argparse.Namespace) -> None:
    """对已下载的小红书笔记图片执行 OCR 识别文字。"""
    from extractor.xhs_extractor import extract_image_texts_from_dir

    if not args.image_dir:
        print(json.dumps({
            "success": False,
            "error": "请提供 --image-dir（已下载图片的本地目录路径）",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    output_dir = _sanitize_output_dir(args.output_dir or _DEFAULT_OUTPUT_DIR)
    sanitized_image_dir = _sanitize_input_file(args.image_dir)
    logger.info("对图片目录执行 OCR: %s", sanitized_image_dir)

    result = extract_image_texts_from_dir(
        image_dir=sanitized_image_dir,
        output_dir=output_dir,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        image_texts = result.get("image_texts", [])
        successful = [item for item in image_texts if item.get("text")]
        print(f"\n✅ OCR 完成：{len(successful)}/{len(image_texts)} 张图片识别到文字")
        for item in image_texts:
            index = item.get("index", 0) + 1
            text = item.get("text", "")
            if text:
                preview = text[:80] + ("..." if len(text) > 80 else "")
                print(f"   🖼️  图片 {index}（{len(text)} 字）: {preview}")
            else:
                error = item.get("error", "无文字内容")
                print(f"   🖼️  图片 {index}: ⚠️  {error}")
        if result.get("combined_text"):
            print(f"\n📝 合并文字共 {len(result['combined_text'])} 字")
    else:
        print(f"\n❌ OCR 失败: {result.get('error', '未知错误')}")
        sys.exit(1)


def cmd_download_images(args: argparse.Namespace) -> None:
    """批量下载图片到本地（无需浏览器）。"""
    from extractor.xhs_extractor import download_images

    if not args.urls:
        print(json.dumps({
            "success": False,
            "error": "请提供 --urls 图片 URL 列表",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    output_dir = _sanitize_output_dir(args.output_dir or str(Path(_DEFAULT_OUTPUT_DIR) / "images"))
    sanitized_urls = _validate_urls(args.urls)
    logger.info("批量下载 %d 张图片到: %s", len(sanitized_urls), output_dir)

    result = download_images(image_urls=sanitized_urls, output_dir=output_dir)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print(f"\n✅ 下载完成：{len(result['downloaded'])}/{result['total']} 张")
        for local_path in result["downloaded"]:
            print(f"   📷 {local_path}")
        if result["failed"]:
            print(f"\n⚠️  失败 {len(result['failed'])} 张：")
            for failed_url in result["failed"]:
                print(f"   ❌ {failed_url[:80]}")
    else:
        print(f"\n❌ 下载失败: {result['error']}")
        sys.exit(1)


def cmd_extract_bilibili(args: argparse.Namespace) -> None:
    """提取 B 站视频内容（字幕或语音转录）。"""
    from extractor.bilibili_extractor import extract_video, extract_from_url

    output_dir = _sanitize_output_dir(args.output_dir or _DEFAULT_OUTPUT_DIR)

    if args.url:
        sanitized_url = _validate_url(args.url)
        logger.info("从 B 站视频链接提取内容: %s", sanitized_url)
        result = extract_from_url(
            video_url=sanitized_url,
            output_dir=output_dir,
            cookie=args.cookie,
            skip_transcript=args.skip_transcript,
            extract_keyframes=args.extract_keyframes,
            no_cookie=args.no_cookie,
        )
    elif args.bvid:
        logger.info("从 BV 号提取内容: %s", args.bvid)
        result = extract_video(
            bvid=args.bvid,
            output_dir=output_dir,
            cookie=args.cookie,
            skip_transcript=args.skip_transcript,
            extract_keyframes=args.extract_keyframes,
            no_cookie=args.no_cookie,
        )
    else:
        print(json.dumps({
            "success": False,
            "error": "请提供 --url 或 --bvid",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    _print_bilibili_result(result)

def cmd_extract_wechat(args: argparse.Namespace) -> None:
    """提取微信公众号图文内容（正文 + 图片 + OCR）。"""
    from extractor.wechat_extractor import extract_article

    if not args.url:
        print(json.dumps({
            "success": False,
            "error": "请提供 --url 公众号文章链接",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    output_dir = _sanitize_output_dir(args.output_dir or _DEFAULT_OUTPUT_DIR)
    sanitized_url = _validate_url(args.url)
    logger.info("提取微信公众号文章: %s", sanitized_url)

    result = extract_article(
        article_url=sanitized_url,
        output_dir=output_dir,
        download_images=not args.no_download_images,
        ocr_images=not args.no_ocr,
    )

    _print_wechat_result(result)

def cmd_extract_xiaoyuzhou(args: argparse.Namespace) -> None:
    """提取小宇宙播客单集内容（音频转录，无需登录，无需浏览器）。"""
    from extractor.xiaoyuzhou_extractor import extract_episode

    if not args.url:
        print(json.dumps({
            "success": False,
            "error": "请提供 --url 小宇宙 episode 链接",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    output_dir = _sanitize_output_dir(args.output_dir or _DEFAULT_OUTPUT_DIR)
    sanitized_url = _validate_url(args.url)
    logger.info("提取小宇宙播客单集: %s", sanitized_url)

    result = extract_episode(
        url_or_id=sanitized_url,
        output_dir=output_dir,
        skip_transcript=args.skip_transcript,
    )

    _print_xiaoyuzhou_result(result)

def cmd_extract_baijiahao(args: argparse.Namespace) -> None:
    """提取百家号图文内容（正文 + 图片 + OCR）。"""
    from extractor.baijiahao_extractor import extract_article

    if not args.url:
        print(json.dumps({
            "success": False,
            "error": "请提供 --url 百家号文章链接",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    output_dir = _sanitize_output_dir(args.output_dir or _DEFAULT_OUTPUT_DIR)
    sanitized_url = _validate_url(args.url)
    logger.info("提取百家号文章: %s", sanitized_url)

    # 读取 Agent 通过 browser_use 保存的页面 HTML
    page_html = None
    page_html_file = getattr(args, "page_html_file", None)
    if page_html_file:
        sanitized_html_file = _sanitize_input_file(page_html_file)
        try:
            with open(sanitized_html_file, "r", encoding="utf-8") as fh:
                page_html = fh.read()
            logger.info("从文件加载页面 HTML: %s（%d 字符）", sanitized_html_file, len(page_html))
        except Exception as read_err:
            logger.warning("读取 HTML 文件失败: %s", read_err)

    result = extract_article(
        article_url=sanitized_url,
        output_dir=output_dir,
        download_images=not args.no_download_images,
        ocr_images=not args.no_ocr,
        page_html=page_html,
    )

    _print_baijiahao_result(result)

def cmd_extract_weibo(args: argparse.Namespace) -> None:
    """提取微博图文内容（正文 + 图片 + OCR）。"""
    from extractor.weibo_extractor import extract_weibo

    if not args.url:
        print(json.dumps({
            "success": False,
            "error": "请提供 --url 微博链接",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    output_dir = _sanitize_output_dir(args.output_dir or _DEFAULT_OUTPUT_DIR)
    sanitized_url = _validate_url(args.url)
    logger.info("提取微博内容: %s", sanitized_url)

    result = extract_weibo(
        weibo_url=sanitized_url,
        output_dir=output_dir,
        download_images=not args.no_download_images,
        ocr_images=not args.no_ocr,
    )

    _print_weibo_result(result)

def cmd_extract_toutiao(args: argparse.Namespace) -> None:
    """提取今日头条图文内容（正文 + 图片 + OCR）。"""
    from extractor.toutiao_extractor import extract_article

    if not args.url:
        print(json.dumps({
            "success": False,
            "error": "请提供 --url 头条文章链接",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    output_dir = _sanitize_output_dir(args.output_dir or _DEFAULT_OUTPUT_DIR)
    sanitized_url = _validate_url(args.url)
    logger.info("提取头条文章: %s", sanitized_url)

    # 读取 Agent 通过 browser_use 保存的页面 HTML
    page_html = None
    page_html_file = getattr(args, "page_html_file", None)
    if page_html_file:
        sanitized_html_file = _sanitize_input_file(page_html_file)
        try:
            with open(sanitized_html_file, "r", encoding="utf-8") as fh:
                page_html = fh.read()
            logger.info("从文件加载页面 HTML: %s（%d 字符）", sanitized_html_file, len(page_html))
        except Exception as read_err:
            logger.warning("读取 HTML 文件失败: %s", read_err)

    result = extract_article(
        article_url=sanitized_url,
        output_dir=output_dir,
        download_images=not args.no_download_images,
        ocr_images=not args.no_ocr,
        page_html=page_html,
    )

    _print_toutiao_result(result)

# ──────────────────────────────── 结果输出 ────────────────────────────────

def _print_douyin_result(result: dict) -> None:
    """格式化输出抖音提取结果。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        method_labels = {
            "api_subtitle": "API 字幕",
            "bcut_asr": "必剪云端 ASR",
            "play_url_only": "视频直链（已获取，可用于 ASR 转录）",
            "whisper_tiny": "Whisper (tiny)",
            "whisper_base": "Whisper (base)",
            "whisper_small": "Whisper (small)",
        }
        method = result.get("method", "")
        method_label = method_labels.get(method, method)
        print(f"\n✅ 提取成功（方法：{method_label}）")

        if result.get("title"):
            print(f"   📌 标题：{result['title']}")
        if result.get("subtitle_text"):
            print(f"   📝 字幕文本：{len(result['subtitle_text'])} 字")
            if result.get("subtitle_file"):
                print(f"   💾 已保存至：{result['subtitle_file']}")
        if result.get("transcript_text"):
            print(f"   🎙️  转录文本：{len(result['transcript_text'])} 字")
            if result.get("transcript_file"):
                print(f"   💾 已保存至：{result['transcript_file']}")
        if result.get("play_url") and method == "play_url_only":
            print(f"   🔗 视频直链已获取（可用 --play-url 参数直接转录）")
        keyframes = result.get("keyframes")
        if keyframes is not None:
            successful_frames = [frame for frame in keyframes if frame.get("screenshot")]
            print(f"   🎞️  关键帧截图：{len(successful_frames)}/{len(keyframes)} 帧")

        if result.get("report_file"):
            print(f"\n📄 Markdown 报告已生成：{result['report_file']}")

        preview_text = result.get("subtitle_text") or result.get("transcript_text", "")
        if preview_text:
            preview = preview_text[:200] + ("..." if len(preview_text) > 200 else "")
            print(f"\n📖 内容预览：\n{preview}")

        if keyframes:
            print("\n🎞️  关键帧时间轴：")
            for frame in keyframes[:5]:
                ts = frame.get("timestamp_str", "")
                text = frame.get("transcript", "")[:30]
                screenshot = frame.get("screenshot", "")
                print(f"   [{ts}] {text} → {screenshot}")
            if len(keyframes) > 5:
                print(f"   ... 共 {len(keyframes)} 帧，详见截图目录")
    else:
        print(f"\n❌ 提取失败: {result.get('error', '未知错误')}")
        sys.exit(1)

def _print_xhs_result(result: dict) -> None:
    """格式化输出小红书提取结果。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print("\n✅ 提取成功")
        if result.get("title"):
            print(f"   📌 标题：{result['title']}")
        if result.get("content"):
            print(f"   📝 正文：{len(result['content'])} 字")
        if result.get("image_urls"):
            print(f"   🖼️  图片：{len(result['image_urls'])} 张")
            if result.get("image_files"):
                print(f"   💾 已下载：{len(result['image_files'])} 张")

        image_texts = result.get("image_texts", [])
        if image_texts:
            successful_ocr = [item for item in image_texts if item.get("text")]
            print(f"   🔍 图片 OCR：{len(successful_ocr)}/{len(image_texts)} 张识别到文字")

        print(f"   ❤️  点赞：{result.get('like_count', 0)}  "
              f"⭐ 收藏：{result.get('collect_count', 0)}  "
              f"💬 评论：{result.get('comment_count', 0)}")

        if result.get("transcript_text"):
            print(f"   🎙️  转录文本：{len(result['transcript_text'])} 字")

        keyframes = result.get("keyframes")
        if keyframes is not None:
            successful_frames = [frame for frame in keyframes if frame.get("screenshot")]
            print(f"   🎞️  关键帧截图：{len(successful_frames)}/{len(keyframes)} 帧")

        if result.get("report_file"):
            print(f"\n📄 Markdown 报告已生成：{result['report_file']}")

        content = result.get("content", "")
        if content:
            preview = content[:200] + ("..." if len(content) > 200 else "")
            print(f"\n📖 正文预览：\n{preview}")

        if keyframes:
            print("\n🎞️  关键帧时间轴：")
            for frame in keyframes[:5]:
                ts = frame.get("timestamp_str", "")
                text = frame.get("transcript", "")[:30]
                screenshot = frame.get("screenshot", "")
                print(f"   [{ts}] {text} → {screenshot}")
            if len(keyframes) > 5:
                print(f"   ... 共 {len(keyframes)} 帧，详见截图目录")
    else:
        print(f"\n❌ 提取失败: {result.get('error', '未知错误')}")
        sys.exit(1)

def _print_wechat_result(result: dict) -> None:
    """格式化输出微信公众号提取结果。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print("\n✅ 提取成功")
        if result.get("account_name"):
            print(f"   📣 公众号：{result['account_name']}")
        if result.get("title"):
            print(f"   📌 标题：{result['title']}")
        if result.get("author"):
            print(f"   ✍️  作者：{result['author']}")
        if result.get("publish_time"):
            print(f"   🕐 发布时间：{result['publish_time']}")
        if result.get("content"):
            print(f"   📝 正文：{len(result['content'])} 字")
        if result.get("image_urls"):
            print(f"   🖼️  图片：{len(result['image_urls'])} 张")
            if result.get("image_files"):
                print(f"   💾 已下载：{len(result['image_files'])} 张")

        image_texts = result.get("image_texts", [])
        if image_texts:
            successful_ocr = [item for item in image_texts if item.get("text")]
            print(f"   🔍 图片 OCR：{len(successful_ocr)}/{len(image_texts)} 张识别到文字")

        if result.get("report_file"):
            print(f"\n📄 Markdown 报告已生成：{result['report_file']}")

        content = result.get("content", "")
        if content:
            preview = content[:200] + ("..." if len(content) > 200 else "")
            print(f"\n📖 正文预览：\n{preview}")
    else:
        print(f"\n❌ 提取失败: {result.get('error', '未知错误')}")
        sys.exit(1)


def _print_bilibili_result(result: dict) -> None:
    """格式化输出 B 站提取结果。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        method_labels = {
            "api_subtitle": "API 字幕",
            "bcut_asr": "必剪云端 ASR",
        }
        method = result.get("method", "")
        method_label = method_labels.get(method, method)
        print(f"\n✅ 提取成功（方法：{method_label}）")

        if result.get("title"):
            print(f"   📌 标题：{result['title']}")
        if result.get("author"):
            print(f"   👤 UP 主：{result['author']}")
        duration = result.get("duration", 0)
        if duration:
            minutes, seconds = divmod(duration, 60)
            print(f"   ⏱️  时长：{minutes}:{seconds:02d}")
        print(f"   👁️  播放：{result.get('view_count', 0):,}  "
              f"❤️  点赞：{result.get('like_count', 0):,}  "
              f"🪙 投币：{result.get('coin_count', 0):,}")

        if result.get("subtitle_text"):
            print(f"   📝 字幕文本：{len(result['subtitle_text'])} 字")
            if result.get("subtitle_file"):
                print(f"   💾 已保存至：{result['subtitle_file']}")
        if result.get("transcript_text"):
            print(f"   🎙️  转录文本：{len(result['transcript_text'])} 字")
            if result.get("transcript_file"):
                print(f"   💾 已保存至：{result['transcript_file']}")

        keyframes = result.get("keyframes")
        if keyframes is not None:
            successful_frames = [frame for frame in keyframes if frame.get("screenshot")]
            print(f"   🎞️  关键帧截图：{len(successful_frames)}/{len(keyframes)} 帧")

        if result.get("report_file"):
            print(f"\n📄 Markdown 报告已生成：{result['report_file']}")

        preview_text = result.get("subtitle_text") or result.get("transcript_text", "")
        if preview_text:
            preview = preview_text[:200] + ("..." if len(preview_text) > 200 else "")
            print(f"\n📖 内容预览：\n{preview}")

        if keyframes:
            print("\n🎞️  关键帧时间轴：")
            for frame in keyframes[:5]:
                ts = frame.get("timestamp_str", "")
                text = frame.get("transcript", "")[:30]
                screenshot = frame.get("screenshot", "")
                print(f"   [{ts}] {text} → {screenshot}")
            if len(keyframes) > 5:
                print(f"   ... 共 {len(keyframes)} 帧，详见截图目录")
    else:
        print(f"\n❌ 提取失败: {result.get('error', '未知错误')}")
        sys.exit(1)

def _print_xiaoyuzhou_result(result: dict) -> None:
    """格式化输出小宇宙提取结果。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print("\n✅ 提取成功")
        if result.get("podcast_title"):
            print(f"   🎙️  播客：{result['podcast_title']}")
        if result.get("title"):
            print(f"   📌 标题：{result['title']}")
        duration = result.get("duration", 0)
        if duration:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            duration_str = f"{hours}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes}:{seconds:02d}"
            print(f"   ⏱️  时长：{duration_str}")
        if result.get("audio_path"):
            print(f"   💾 音频文件：{result['audio_path']}")
        if result.get("transcript"):
            print(f"   📝 转录文本：{len(result['transcript'])} 字")
        if result.get("report_path"):
            print(f"\n📄 Markdown 报告已生成：{result['report_path']}")

        transcript = result.get("transcript", "")
        if transcript:
            preview = transcript[:200] + ("..." if len(transcript) > 200 else "")
            print(f"\n📖 转录预览：\n{preview}")
        elif result.get("description"):
            preview = result["description"][:200] + ("..." if len(result["description"]) > 200 else "")
            print(f"\n📖 节目简介预览：\n{preview}")
    else:
        print(f"\n❌ 提取失败: {result.get('error', '未知错误')}")
        sys.exit(1)

def _print_baijiahao_result(result: dict) -> None:
    """格式化输出百家号提取结果。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print("\n✅ 提取成功")
        if result.get("title"):
            print(f"   📌 标题：{result['title']}")
        if result.get("author"):
            print(f"   ✍️  作者：{result['author']}")
        if result.get("publish_time"):
            print(f"   🕐 发布时间：{result['publish_time']}")
        if result.get("content"):
            print(f"   📝 正文：{len(result['content'])} 字")
        if result.get("image_urls"):
            print(f"   🖼️  图片：{len(result['image_urls'])} 张")
            if result.get("image_files"):
                print(f"   💾 已下载：{len(result['image_files'])} 张")

        image_texts = result.get("image_texts", [])
        if image_texts:
            successful_ocr = [item for item in image_texts if item.get("text")]
            print(f"   🔍 图片 OCR：{len(successful_ocr)}/{len(image_texts)} 张识别到文字")

        if result.get("report_file"):
            print(f"\n📄 Markdown 报告已生成：{result['report_file']}")

        content = result.get("content", "")
        if content:
            preview = content[:200] + ("..." if len(content) > 200 else "")
            print(f"\n📖 正文预览：\n{preview}")
    else:
        print(f"\n❌ 提取失败: {result.get('error', '未知错误')}")
        sys.exit(1)

def _print_weibo_result(result: dict) -> None:
    """格式化输出微博提取结果。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print("\n✅ 提取成功")
        if result.get("author"):
            print(f"   👤 作者：@{result['author']}")
        if result.get("publish_time"):
            print(f"   🕐 发布时间：{result['publish_time']}")
        if result.get("content"):
            print(f"   📝 正文：{len(result['content'])} 字")
        if result.get("image_urls"):
            print(f"   🖼️  图片：{len(result['image_urls'])} 张")
            if result.get("image_files"):
                print(f"   💾 已下载：{len(result['image_files'])} 张")

        print(f"   🔄 转发：{result.get('reposts_count', 0)}  "
              f"💬 评论：{result.get('comments_count', 0)}  "
              f"❤️  点赞：{result.get('likes_count', 0)}")

        image_texts = result.get("image_texts", [])
        if image_texts:
            successful_ocr = [item for item in image_texts if item.get("text")]
            print(f"   🔍 图片 OCR：{len(successful_ocr)}/{len(image_texts)} 张识别到文字")

        if result.get("report_file"):
            print(f"\n📄 Markdown 报告已生成：{result['report_file']}")

        content = result.get("content", "")
        if content:
            preview = content[:200] + ("..." if len(content) > 200 else "")
            print(f"\n📖 正文预览：\n{preview}")
    else:
        print(f"\n❌ 提取失败: {result.get('error', '未知错误')}")
        sys.exit(1)

def _print_toutiao_result(result: dict) -> None:
    """格式化输出今日头条提取结果。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print("\n✅ 提取成功")
        if result.get("title"):
            print(f"   📌 标题：{result['title']}")
        if result.get("author"):
            print(f"   ✍️  作者：{result['author']}")
        if result.get("publish_time"):
            print(f"   🕐 发布时间：{result['publish_time']}")
        if result.get("content"):
            print(f"   📝 正文：{len(result['content'])} 字")
        if result.get("image_urls"):
            print(f"   🖼️  图片：{len(result['image_urls'])} 张")
            if result.get("image_files"):
                print(f"   💾 已下载：{len(result['image_files'])} 张")

        stats_parts = []
        if result.get("read_count"):
            stats_parts.append(f"👁️  阅读：{result['read_count']}")
        if result.get("comment_count"):
            stats_parts.append(f"💬 评论：{result['comment_count']}")
        if result.get("like_count"):
            stats_parts.append(f"❤️  点赞：{result['like_count']}")
        if stats_parts:
            print(f"   {'  '.join(stats_parts)}")

        image_texts = result.get("image_texts", [])
        if image_texts:
            successful_ocr = [item for item in image_texts if item.get("text")]
            print(f"   🔍 图片 OCR：{len(successful_ocr)}/{len(image_texts)} 张识别到文字")

        if result.get("report_file"):
            print(f"\n📄 Markdown 报告已生成：{result['report_file']}")

        content = result.get("content", "")
        if content:
            preview = content[:200] + ("..." if len(content) > 200 else "")
            print(f"\n📖 正文预览：\n{preview}")
    else:
        print(f"\n❌ 提取失败: {result.get('error', '未知错误')}")
        sys.exit(1)

# ──────────────────────────────── 参数解析 ────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="内容提取技能：从抖音、小红书、微信公众号、B站、小宇宙、百家号、微博、今日头条提取内容",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── extract-douyin ──
    p_douyin = subparsers.add_parser(
        "extract-douyin",
        help="提取抖音视频内容（字幕/转录）。支持：短链接(v.douyin.com)、标准链接、精选链接(modal_id)",
    )
    douyin_input = p_douyin.add_mutually_exclusive_group()
    douyin_input.add_argument("--metadata-json", help="元数据 JSON 字符串（Agent 通过 browser_use 获取，含 play_url/title/subtitle_infos）")
    douyin_input.add_argument("--play-url", help="视频直链（play_url），无需浏览器")
    douyin_input.add_argument("--audio-url", help="音频轨直链（DASH 分离场景，直接下载音频进行 ASR，比 --play-url 更快）")
    douyin_input.add_argument("--video-file", help="本地视频文件路径，无需浏览器")
    douyin_input.add_argument("--subtitle-infos-file", help="包含 subtitle_infos 的 JSON 文件路径")
    p_douyin.add_argument("--video-id", help="视频 ID（配合 --subtitle-infos-file 使用）")
    p_douyin.add_argument("--output-dir", help=f"输出目录（默认：{_DEFAULT_OUTPUT_DIR}）")
    p_douyin.add_argument(
        "--whisper-model",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper 模型（必剪 ASR 失败时使用，默认：medium；base 中文效果差）",
    )
    p_douyin.add_argument("--no-transcript", action="store_true", help="跳过 ASR 转录，只提取视频信息和直链")
    p_douyin.add_argument("--extract-keyframes", action="store_true", help="提取关键帧截图（按 ASR 时间戳截帧，需要 ffmpeg；需要 ffmpeg）")
    p_douyin.set_defaults(func=cmd_extract_douyin)

    # ── extract-xhs ──
    p_xhs = subparsers.add_parser(
        "extract-xhs",
        help="提取小红书笔记内容（正文 + 图片）",
    )
    p_xhs.add_argument("--metadata-json", help="笔记元数据 JSON 字符串（Agent 通过 browser_use 从 __INITIAL_STATE__ 提取）")
    p_xhs.add_argument("--output-dir", help=f"输出目录（默认：{_DEFAULT_OUTPUT_DIR}）")
    p_xhs.add_argument("--no-download-images", action="store_true", help="不下载图片，只返回图片 URL")
    p_xhs.add_argument("--extract-keyframes", action="store_true", help="提取视频关键帧（仅视频笔记有效，需要 ffmpeg）")
    p_xhs.set_defaults(func=cmd_extract_xhs)

    # ── extract-xhs-image-texts ──
    p_xhs_ocr = subparsers.add_parser(
        "extract-xhs-image-texts",
        help="截取小红书笔记每张图片并用 OCR 识别文字（需要浏览器）",
    )
    p_xhs_ocr.add_argument("--image-dir", help="已下载图片的本地目录路径")
    p_xhs_ocr.add_argument("--output-dir", help=f"输出目录（默认：{_DEFAULT_OUTPUT_DIR}）")
    p_xhs_ocr.set_defaults(func=cmd_extract_xhs_image_texts)

    # ── download-images ──
    p_images = subparsers.add_parser("download-images", help="批量下载图片到本地（无需浏览器）")
    p_images.add_argument("--urls", nargs="+", required=True, help="图片 URL 列表（空格分隔）")
    p_images.add_argument("--output-dir", help="保存目录")
    p_images.set_defaults(func=cmd_download_images)

    # ── extract-bilibili ──
    p_bili = subparsers.add_parser(
        "extract-bilibili",
        help="提取 B 站视频内容（字幕或语音转录，需要已登录 B 站的 Chrome）",
    )
    bili_input = p_bili.add_mutually_exclusive_group(required=True)
    bili_input.add_argument("--url", help="B 站视频链接（如 https://www.bilibili.com/video/BV1xxx）")
    bili_input.add_argument("--bvid", help="B 站视频 BV 号（如 BV1GJ411x7h7）")
    p_bili.add_argument("--output-dir", help=f"输出目录（默认：{_DEFAULT_OUTPUT_DIR}/bilibili）")
    p_bili.add_argument("--cookie", default="", help="B 站登录 Cookie 字符串（由 Agent 通过 browser_use 获取）")
    p_bili.add_argument("--no-cookie", action="store_true", help="无 Cookie 模式：跳过字幕 API，直接通过公开 API 下载视频走 ASR（360P）")
    p_bili.add_argument("--skip-transcript", action="store_true", help="无字幕时跳过 ASR 转录")
    p_bili.add_argument("--extract-keyframes", action="store_true", help="提取视频关键帧（需要 ffmpeg，与 --skip-transcript 不兼容）")
    p_bili.set_defaults(func=cmd_extract_bilibili)

    # ── extract-wechat ──
    p_wechat = subparsers.add_parser(
        "extract-wechat",
        help="提取微信公众号图文内容（正文 + 图片 + OCR，无需登录，无需浏览器）",
    )
    p_wechat.add_argument("--url", required=True, help="公众号文章链接（mp.weixin.qq.com/s/xxxxx）")
    p_wechat.add_argument("--output-dir", help=f"输出目录（默认：{_DEFAULT_OUTPUT_DIR}/wechat）")
    p_wechat.add_argument("--no-download-images", action="store_true", help="不下载图片，只返回图片 URL")
    p_wechat.add_argument("--no-ocr", action="store_true", help="跳过图片 OCR 识别")
    p_wechat.set_defaults(func=cmd_extract_wechat)

    # ── extract-xiaoyuzhou ──
    p_xyz = subparsers.add_parser(
        "extract-xiaoyuzhou",
        help="提取小宇宙播客单集内容（音频转录，无需登录，无需浏览器）",
    )
    p_xyz.add_argument("--url", required=True, help="小宇宙 episode 链接（如 https://www.xiaoyuzhoufm.com/episode/xxx）")
    p_xyz.add_argument("--output-dir", help=f"输出目录（默认：{_DEFAULT_OUTPUT_DIR}）")
    p_xyz.add_argument("--skip-transcript", action="store_true", help="跳过音频下载和 ASR 转录，仅提取文字信息")
    p_xyz.set_defaults(func=cmd_extract_xiaoyuzhou)

    # ── extract-baijiahao ──
    p_bjh = subparsers.add_parser(
        "extract-baijiahao",
        help="提取百家号图文内容（正文 + 图片 + OCR，需要 browser_use 获取页面 HTML）",
    )
    p_bjh.add_argument("--url", required=True, help="百家号文章链接（baijiahao.baidu.com/s?id=xxxxx）")
    p_bjh.add_argument("--page-html-file", help="页面 HTML 文件路径（Agent 通过 browser_use 获取后保存）")
    p_bjh.add_argument("--output-dir", help=f"输出目录（默认：{_DEFAULT_OUTPUT_DIR}/baijiahao）")
    p_bjh.add_argument("--no-download-images", action="store_true", help="不下载图片，只返回图片 URL")
    p_bjh.add_argument("--no-ocr", action="store_true", help="跳过图片 OCR 识别")
    p_bjh.set_defaults(func=cmd_extract_baijiahao)

    # ── extract-weibo ──
    p_weibo = subparsers.add_parser(
        "extract-weibo",
        help="提取微博图文内容（正文 + 图片 + OCR，无需登录，无需浏览器）",
    )
    p_weibo.add_argument("--url", required=True, help="微博链接（m.weibo.cn/detail/xxx 或 weibo.com/uid/mid）")
    p_weibo.add_argument("--output-dir", help=f"输出目录（默认：{_DEFAULT_OUTPUT_DIR}/weibo）")
    p_weibo.add_argument("--no-download-images", action="store_true", help="不下载图片，只返回图片 URL")
    p_weibo.add_argument("--no-ocr", action="store_true", help="跳过图片 OCR 识别")
    p_weibo.set_defaults(func=cmd_extract_weibo)

    # ── extract-toutiao ──
    p_toutiao = subparsers.add_parser(
        "extract-toutiao",
        help="提取今日头条图文内容（正文 + 图片 + OCR，需要 browser_use 获取页面 HTML）",
    )
    p_toutiao.add_argument("--url", required=True, help="头条文章链接（toutiao.com/article/xxx）")
    p_toutiao.add_argument("--page-html-file", help="页面 HTML 文件路径（Agent 通过 browser_use 获取后保存）")
    p_toutiao.add_argument("--output-dir", help=f"输出目录（默认：{_DEFAULT_OUTPUT_DIR}/toutiao）")
    p_toutiao.add_argument("--no-download-images", action="store_true", help="不下载图片，只返回图片 URL")
    p_toutiao.add_argument("--no-ocr", action="store_true", help="跳过图片 OCR 识别")
    p_toutiao.set_defaults(func=cmd_extract_toutiao)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
