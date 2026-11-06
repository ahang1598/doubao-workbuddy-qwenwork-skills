#!/usr/bin/env python3
"""
Xiaoyi Image Generator - Helper Script

This is a helper script for batch generation or CLI usage.
The main skill workflow is defined in SKILL.md and executed by Claude.

桌面形态 SERVICE_URL=np://claw-skill（默认）：云端调用经主进程 skill API 代理
转发，businessCredential 鉴权由主进程注入，本进程零业务凭证；预签名 URL 的
上传/下载（无业务鉴权）直连。

Usage:
    python generate_seedream.py "prompt" --image https://example.com/photo.png --max-images 3
"""

import requests
import json
import os
import sys
import uuid
import hashlib
import random
import string
import base64
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import argparse
from config import Config, ppt_session_dir

# MIME类型映射
_MIME_TYPE_MAP = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
}


def _is_remote_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_local_file(value):
    """Check if value is a local file path."""
    try:
        return Path(value).is_file()
    except (OSError, TypeError):
        return False
    

def validate_image_input(value):
    """Validate that the image parameter is a remote URL or local file path."""
    if not (_is_remote_url(value) or _is_local_file(value)):
        raise argparse.ArgumentTypeError(
            f"Image must be a remote HTTP/HTTPS URL or a local file path, not: {value}"
        )
    return value


def _image_to_base64(image_path):
    """将本地图片文件转为base64字符串（带data URI前缀）。"""
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
            b64_string = base64.b64encode(image_data).decode('utf-8')
            
            # 根据文件扩展名确定MIME类型
            ext = Path(image_path).suffix.lower()
            mime_type = _MIME_TYPE_MAP.get(ext, 'image/png')
            return f"data:{mime_type};base64,{b64_string}"
    except Exception as e:
        raise ValueError(f"Failed to convert image to base64: {e}")


def calculate_sha256(file_path):
    """计算文件的 SHA256 哈希值"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def upload_file(file_path, object_type="TEMPORARY_MATERIAL_DOC", cfg: Config | None = None):
    """
    将本地文件上传到小艺文件存储服务（三阶段上传：prepare → upload → complete）

    phase1/3 经主进程 skill API 代理（管道形态，鉴权主进程注入）；
    phase2 预签名 URL 直传（URL 本身即一次性凭证，不经代理）。

    Args:
        file_path: 本地文件路径
        object_type: 文件类型（默认 TEMPORARY_MATERIAL_DOC）
        cfg: 配置（缺省内部加载）

    Returns:
        fileUrl
    """
    try:
        # 校验文件存在
        if not os.path.isfile(file_path):
            print(f'❌ 文件不存在：{file_path}')
            return None

        if cfg is None:
            cfg = Config.load()

        # 准备文件信息
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_sha256 = calculate_sha256(file_path)

        # ── 阶段 1: Prepare ──────────────────────────────────────────────────────
        prepare_payload = {
            'objectType': object_type,
            'fileName': file_name,
            'fileSha256': file_sha256,
            'fileSize': file_size,
            # 管道形态下 uid 由主进程经 x-uid 头注入，skill 侧无 uid 概念
            **({'fileOwnerInfo': {'uid': cfg.personal_uid, 'teamId': cfg.personal_uid}}
               if cfg.personal_uid else {}),
            'useEdge': False,
        }

        with cfg.skill_post('/osms/v1/file/manager/prepare', prepare_payload) as prepare_resp:
            if prepare_resp.status_code != 200:
                print(f'❌ Prepare 请求失败: HTTP {prepare_resp.status_code}')
                print(f'❌ 响应内容: {prepare_resp.text}')
                return None
            prepare_data = prepare_resp.json()

        # 部分服务器返回 code 字段，"0" 为成功
        if 'code' in prepare_data and prepare_data['code'] != '0':
            print(f'❌ Prepare 失败: {prepare_data.get("desc", "未知错误")}')
            return None

        object_id = prepare_data.get('objectId')
        draft_id = prepare_data.get('draftId')
        upload_infos = prepare_data.get('uploadInfos', [])

        if not object_id or not draft_id or not upload_infos:
            print(f'❌ Prepare 响应缺少必要字段: objectId={object_id}, draftId={draft_id}')
            return None

        # ── 阶段 2: 预签名 URL 直传（不经代理）────────────────────────────────────
        upload_info = upload_infos[0]
        upload_url = upload_info['url']
        upload_method = upload_info.get('method', 'PUT').upper()
        upload_headers = upload_info.get('headers', {'Content-Type': 'application/octet-stream'})

        with open(file_path, 'rb') as f:
            file_data = f.read()

        upload_resp = requests.request(
            method=upload_method,
            url=upload_url,
            headers=upload_headers,
            data=file_data,
            timeout=120
        )

        if upload_resp.status_code not in (200, 204):
            print(f'❌ 文件上传失败: HTTP {upload_resp.status_code}')
            return None

        # ── 阶段 3: Complete（经主进程管道代理）──────────────────────────────────
        complete_payload = {
            'objectId': object_id,
            'draftId': draft_id,
        }

        with cfg.skill_post('/osms/v1/file/manager/completeAndQuery', complete_payload) as complete_resp:
            if complete_resp.status_code != 200:
                print(f'❌ Complete 请求失败: HTTP {complete_resp.status_code}')
                return None
            complete_data = complete_resp.json()

        # 从 completeAndQuery 响应中直接获取文件下载 URL
        file_url = complete_data.get('fileDetailInfo', {}).get('url', '')

        return file_url

    except requests.exceptions.Timeout:
        print('❌ 请求超时')
        return None
    except requests.exceptions.ConnectionError as e:
        print(f'❌ 连接失败: {e}')
        return None
    except Exception as e:
        print(f'❌ 上传异常: {e}')
        import traceback
        traceback.print_exc()
        return None


def _process_image_input(image):
    """处理图片输入：验证并转换本地文件为base64，远程URL保持不变。"""
    def _validate_and_convert(item):
        """验证单个图片项并返回处理后的结果。"""
        if _is_remote_url(item):
            return item
        elif _is_local_file(item):
            return upload_file(item)
        raise ValueError(f"Invalid image input: {item}")

    if isinstance(image, str):
        return _validate_and_convert(image)
    elif isinstance(image, list):
        if not image:
            raise ValueError("Image list cannot be empty.")
        return [_validate_and_convert(item) for item in image]
    raise ValueError("Image input must be a remote URL, local file path, or list of URLs/paths.")


def generate_image(
    prompt,
    input_image=None,
    size="2K",
    watermark=True,
    max_images=None,
    cfg: Config | None = None):
    """Call the Xiaoyi image generation API."""

    if cfg is None:
        cfg = Config.load()

    # Configuration
    trace_id = str(uuid.uuid4())
    api_path = '/celia-claw/v1/sse-api/skill/execute'

    # Build request（业务鉴权由主进程代理注入；旧沙箱形态 auth_headers 在 skill_post 内合并）
    headers = {
        'x-skill-id': 'seedream',
        'x-hag-trace-id': trace_id,
    }
    
    # 定义 content 字段，便于后续扩展
    content = {
        "prompt": prompt,
        "size": size,
        "watermark": watermark,
        "response_format": "url"
    }
    
    # 处理图片输入并添加到 content 中
    if input_image is not None:
        input_image = _process_image_input(input_image, cfg)
        content["reference_images"] = input_image

    if max_images is not None:
        content["max_images"] = max_images
    
    payload = {
        "actions": [
            {
                "actionExecutorTask": {
                    "actionName": "seedreamBatch5",
                    "content": content,
                    "pluginId": "abf9388fed6b4df89daac71be85fc62c",
                    "replyCard": False
                },
                "actionSn": "81ef5ac1b5e74e85b90832503ea34a07"
            }
        ],
        "endpoint": {
            "countryCode": "",
            "device": {
                "deviceId": "5682d99dbb90973b775b7e9bf774ff9f",
                "phoneType": "2in1",
                "prdVer": "11.6.2.202"
            }
        },
        "session": {
            "interactionId": "0",
            "isNew": True,
            "sessionId": str(uuid.uuid4())
        },
        "utterance": {
            "original": "",
            "type": "text"
        },
        "version": "1.0"
    }
    
    # Call API（经主进程管道代理；旧沙箱形态 requests 直连）
    print(f"📡 Generating image...")
    print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

    response = None
    try:
        # Use stream to handle multiple responses (heartbeat packets)
        response = cfg.skill_post(api_path, payload, headers=headers, stream=True)
        response.raise_for_status()
        
        # Read streaming responses until we get the final result
        image_urls = None
        
        print(f"⏳ Waiting for image generation to complete...")
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                try:
                    # Parse SSE (Server-Sent Events) format
                    # Skip id: lines and other non-data lines
                    if line_str.startswith('data:'):
                        # Extract JSON data from "data: {...}" line
                        json_str = line_str[5:].strip()  # Remove "data:" prefix
                        result = json.loads(json_str)
                    elif line_str.startswith('id:'):
                        # Skip id lines
                        continue
                    else:
                        # Skip empty or other non-data lines
                        continue
                    
                    # Extract image URL from new JSON structure
                    ability_infos = result.get('abilityInfos', [])
                    if not ability_infos:
                        continue
                    
                    action_executor_result = ability_infos[0].get('actionExecutorResult', {})
                    if action_executor_result.get('code') != '0':
                        error_msg = action_executor_result.get('desc', 'Unknown error')
                        print(f"❌ API Error: {error_msg}")
                        continue
                    
                    reply = action_executor_result.get('reply', {})
                    stream_info = reply.get('streamInfo', {})
                    stream_type = stream_info.get('streamType', '')
                    
                    # Check if this is a heartbeat packet or final response
                    if stream_type == 'final':
                        # This is the final response with image URLs
                        items = reply.get('items', [])
                        if items:
                            image_urls = items
                            print(f"✅ Final response received, {len(image_urls)} image(s) generated")
                            break
                
                except json.JSONDecodeError:
                    # Skip lines that are not valid JSON
                    continue
        
        # Return the image URLs or None if not found
        return image_urls
        
    except requests.exceptions.Timeout:
        print("❌ Error: Request timed out (120s)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        # 管道形态需显式关闭（fd 回收）；requests.Response.close() 同样无害
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def download_image(url, output_dir):
    """Download image and save to file."""
    
    print(f"⬇️  Downloading...")
    
    try:
        response = requests.get(url, timeout=60, verify=False)
        response.raise_for_status()
        
        # Determine extension
        path_lower = url.lower().split('?')[0]
        if path_lower.endswith('.jpg') or path_lower.endswith('.jpeg'):
            ext = '.jpg'
        elif path_lower.endswith('.webp'):
            ext = '.webp'
        elif path_lower.endswith('.gif'):
            ext = '.gif'
        else:
            ext = '.png'
        
        # Generate filename
        now_time = datetime.now()
        ms = now_time.strftime('%f')[:3]
        base_time = now_time.strftime('%Y%m%d_%H%M%S')

        # 2 位随机字符
        random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=2))

        timestamp = f"{base_time}_{ms}_{random_chars}"
        filename = f"{timestamp}_generated{ext}"
        output_path = Path(output_dir) / filename
        
        # Save
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"💾 Saved to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None

STYLE_PROMPT_MAP = {
    "CreamInk": "适配的页面背景色：#faf9f7，图片里无需包含页面背景",
    "PlatinumExecutive": "适配的页面背景色：#FFFFFF，图片里无需包含页面背景",
    "WarmPaper": "适配的页面背景色：#f5f3ee，图片里无需包含页面背景"
}


def call_seedream(
    prompt: str,
    theme: str = "",
    style: str | None = None,
    output_dir: Path | None = None,
) -> list[str]:
    style_prefix = ""
    if style and style in STYLE_PROMPT_MAP:
        style_prefix = STYLE_PROMPT_MAP[style]

    # 构建主题语境片段
    theme_clause = f"{theme}。" if theme else ""

    cfg = Config.load()
    image_urls = generate_image(
        prompt=(
            f"生成一张商业专业级的PPT背景图，16：9比例。"
            f"画面包含必要的留白，背景极简干净，{style_prefix}。核心呼应主题：{theme_clause}。"
            f"具体画面元素参考：{prompt}。"
            f"绝对禁止：图片中绝不允许包含任何形式的文字、字母、单词或乱码！忽略具体画面描述中的颜色描述，页面背景色为第一优先级。"
        ),
        size="2K",
        watermark=False,
        cfg=cfg
    )

    if not image_urls:
        raise RuntimeError("Seedream 未返回图片")

    # Determine output directory
    if output_dir is None:
        output_dir = ppt_session_dir(os.getenv("PPT_SESSION_ID", "") or "default") / "generated-images"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download all images
    saved_paths = []
    for i, url in enumerate(image_urls, 1):
        print(f"\n[{i}/{len(image_urls)}] Processing image...")
        saved_path = download_image(url, output_dir)
        if saved_path:
            saved_paths.append(saved_path)
    
    # Check if all downloads succeeded
    if len(saved_paths) < len(image_urls):
        print(f"\n⚠️  Warning: Only {len(saved_paths)} out of {len(image_urls)} images were successfully downloaded")
        return saved_paths
    return saved_paths