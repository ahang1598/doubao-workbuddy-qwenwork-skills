#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
素材上传工具（平台关联模式）

⚠️  平台关联模式：
- 不再自行管理凭证，授权由平台统一管理
- 素材查询直接使用平台工具 file_image_ad_search
- 素材上传通过平台动态调度器 tool_execute 调用 /file/video/ad/upload/ 等接口
- 文件上传需要 multipart/form-data，具体执行由 Agent 通过平台工具完成

使用方式：
  python3 upload_assets.py --list --advertiser-id 99999
  python3 upload_assets.py --video /path/to/video.mp4 --advertiser-id 99999
  python3 upload_assets.py --image /path/to/image.jpg --advertiser-id 99999
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tiktok_mcp_client import TikTokAdsMCPClient


def mask_id(entity_id: str) -> str:
    if not entity_id:
        return "N/A"
    s = str(entity_id)
    return s if len(s) <= 4 else f"****{s[-4:]}"


def upload_video(video_path: str, advertiser_id: str, file_name: str = "") -> dict:
    """生成视频素材上传的平台调用指令"""
    if not os.path.exists(video_path):
        return {"success": False, "error": f"文件不存在: {video_path}"}

    file_size = os.path.getsize(video_path)
    if not file_name:
        file_name = os.path.basename(video_path)

    print(f"📹 视频素材: {file_name} ({file_size / 1024 / 1024:.2f} MB)")

    client = TikTokAdsMCPClient(advertiser_id=advertiser_id)
    # 文件上传通过动态调度器调用
    call = client.call_tool("file_video_ad_upload", {
        "advertiser_id": advertiser_id,
        "file_name": file_name,
        "file_path": video_path,
    })

    return {
        "success": True,
        "mode": "platform",
        "action": "upload_video",
        "file_name": file_name,
        "file_size": file_size,
        "platform_call": call,
        "note": "Agent 需通过平台 tool_execute 执行文件上传，文件上传需 multipart/form-data 支持",
    }


def upload_image(image_path: str, advertiser_id: str, file_name: str = "") -> dict:
    """生成图片素材上传的平台调用指令"""
    if not os.path.exists(image_path):
        return {"success": False, "error": f"文件不存在: {image_path}"}

    file_size = os.path.getsize(image_path)
    if not file_name:
        file_name = os.path.basename(image_path)

    print(f"🖼️  图片素材: {file_name} ({file_size / 1024:.2f} KB)")

    client = TikTokAdsMCPClient(advertiser_id=advertiser_id)
    call = client.call_tool("file_image_ad_upload", {
        "advertiser_id": advertiser_id,
        "file_name": file_name,
        "file_path": image_path,
    })

    return {
        "success": True,
        "mode": "platform",
        "action": "upload_image",
        "file_name": file_name,
        "file_size": file_size,
        "platform_call": call,
        "note": "Agent 需通过平台 tool_execute 执行文件上传",
    }


def list_creatives(advertiser_id: str, filtering: dict = None) -> dict:
    """生成素材库查询指令（使用平台直接注册的 file_image_ad_search）"""
    client = TikTokAdsMCPClient(advertiser_id=advertiser_id)
    arguments = {"advertiser_id": advertiser_id, "page": 1, "page_size": 100}
    if filtering:
        arguments.update(filtering)

    call = client._make_call("file_image_ad_search", arguments, "查询素材库")
    return {
        "success": True,
        "mode": "platform",
        "action": "list_creatives",
        "platform_call": call,
        "note": "Agent 调用此平台工具获取素材库列表",
    }


def main():
    parser = argparse.ArgumentParser(
        description="素材上传工具（平台关联模式）",
        epilog="⚠️  平台关联模式：授权由平台统一管理，上传通过平台工具执行"
    )
    parser.add_argument("--video", type=str, help="上传视频文件路径")
    parser.add_argument("--image", type=str, help="上传图片文件路径")
    parser.add_argument("--name", type=str, help="素材文件名（可选）")
    parser.add_argument("--advertiser-id", type=str, default="", help="广告主 ID")
    parser.add_argument("--list", action="store_true", help="列出素材库（生成查询指令）")
    parser.add_argument("--output", type=str, help="结果输出文件路径")
    args = parser.parse_args()

    if not args.advertiser_id and (args.list or args.video or args.image):
        print("❌ 需要 --advertiser-id 参数", file=sys.stderr)
        sys.exit(1)

    result = None

    if args.list:
        result = list_creatives(args.advertiser_id)
        print("📋 素材库查询指令（平台关联模式）")
        print(f"   平台工具: {result['platform_call']['platform_tool']}")
        print(f"   广告主: {mask_id(args.advertiser_id)}")
        print("💡 Agent 将调用此平台工具获取素材列表")

    elif args.video:
        result = upload_video(args.video, args.advertiser_id, args.name)
        if result.get("success"):
            print(f"   平台工具: {result['platform_call']['platform_tool']}")
            print("💡 Agent 将通过平台工具执行上传")

    elif args.image:
        result = upload_image(args.image, args.advertiser_id, args.name)
        if result.get("success"):
            print(f"   平台工具: {result['platform_call']['platform_tool']}")
            print("💡 Agent 将通过平台工具执行上传")

    else:
        parser.print_help()
        return

    if result and args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n📄 结果已保存到: {args.output}")
    elif result:
        print("\n--- RESULT JSON ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
