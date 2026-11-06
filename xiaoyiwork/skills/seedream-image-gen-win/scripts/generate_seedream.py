#!/usr/bin/env python3
"""
Xiaoyi Image Generator - Helper Script

This is a script for batch generation or CLI usage.
The main skill workflow is defined in SKILL.md.

Usage:
    python generate_seedream.py "prompt" --image https://example.com/photo.png
"""

import argparse
import base64
import hashlib
import json
import os
import random
import string
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import Config
from claw_pipe_http import PipeHttpError

# MIME类型映射
_MIME_TYPE_MAP = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
}

def read_xiaoyienv():
    """
    读取 ~/.openclaw/.xiaoyienv 文件并返回键值对字典。
    """
    file_path = os.path.expanduser("~/.openclaw/.xiaoyienv")
    env_dict = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                # 去除行首尾的空白字符和换行符
                line = line.strip()
                # 跳过空行和以 # 开头的注释行
                if not line or line.startswith('#'):
                    continue
                # 确保行中包含等号
                if '=' in line:
                    # 只在第一个等号处分割，防止 value 中包含等号
                    key, value = line.split('=', 1)
                    env_dict[key.strip()] = value.strip()

    except FileNotFoundError:
        print(f"提示: 未找到文件 {file_path}")
    except Exception as e:
        print(f"读取文件时发生错误: {e}")

    return env_dict


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


def calculate_sha256(file_path):
    """计算文件的 SHA256 哈希值"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def upload_file(file_path, cfg, object_type="TEMPORARY_MATERIAL_DOC"):
    """
    将本地文件上传到小艺文件存储服务（三阶段上传：prepare → upload → complete）

    Args:
        file_path: 本地文件路径
        object_type: 文件类型（默认 TEMPORARY_MATERIAL_DOC）

    Returns:
        fileUrl
    """
    try:
        # 校验文件存在
        if not os.path.isfile(file_path):
            print(f'❌ 文件不存在：{file_path}')
            return None

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
            **({'fileOwnerInfo': {'uid': cfg.personal_uid, 'teamId': cfg.personal_uid}}
               if cfg.personal_uid else {}),
            'useEdge': False,
        }

        with cfg.skill_post('/osms/v1/file/manager/prepare', prepare_payload, headers={'x-request-from': 'openclaw'}) as prepare_resp:
            if prepare_resp.status_code != 200:
                print(f'\u274c Prepare \u8bf7\u6c42\u5931\u8d25: HTTP {prepare_resp.status_code}')
                print(f'\u274c \u54cd\u5e94\u5185\u5bb9: {prepare_resp.text}')
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
            timeout=120,
            verify=False
        )

        if upload_resp.status_code not in (200, 204):
            print(f'❌ 文件上传失败: HTTP {upload_resp.status_code}')
            return None

        # ── 阶段 3: Complete ─────────────────────────────────────────────────────
        complete_payload = {
            'objectId': object_id,
            'draftId': draft_id,
        }

        with cfg.skill_post('/osms/v1/file/manager/completeAndQuery', complete_payload, headers={'x-request-from': 'openclaw'}) as complete_resp:
            if complete_resp.status_code != 200:
                print(f'\u274c Complete \u8bf7\u6c42\u5931\u8d25: HTTP {complete_resp.status_code}')
                return None
            complete_data = complete_resp.json()

        # 从 completeAndQuery 响应中直接获取文件下载 URL
        file_url = complete_data.get('fileDetailInfo', {}).get('url', '')

        return file_url

    except requests.exceptions.Timeout:
        print('❌ 请求超时')
        return None
    except (requests.exceptions.ConnectionError, PipeHttpError) as e:
        print(f'❌ 连接失败: {e}')
        return None
    except Exception as e:
        print(f'❌ 上传异常: {e}')
        import traceback
        traceback.print_exc()
        return None


def _process_image_input(image, cfg):
    """处理图片输入：验证并转换本地文件为URL，远程URL保持不变。"""
    def _validate_and_convert(item):
        """验证单个图片项并返回处理后的结果。"""
        if _is_remote_url(item):
            return item
        elif _is_local_file(item):
            result = upload_file(item, cfg)
            if result is None:
                raise ValueError(f"Failed to upload local file: {item}")
            return result
        raise ValueError(f"Invalid image input: {item}")

    if isinstance(image, str):
        return [_validate_and_convert(image)]
    elif isinstance(image, list):
        if not image:
            raise ValueError("Image list cannot be empty.")
        return [_validate_and_convert(item) for item in image]
    raise ValueError("Image input must be a remote URL, local file path, or list of URLs/paths.")


def calculate_cost(model, size, input_image_count=0, output_image_count=1):
    """计算单次调用的扣点数。

    Args:
        model: "Flash" 或 "Pro"
        size: "1K" 或 "2K"
        input_image_count: 输入参考图数量
        output_image_count: 输出图片数量（两个模型均仅单图, 恒为 1）

    Returns:
        (cost, detail_str): 扣点数和计算明细字符串
    """
    if model == "Flash":
        cost = 2.5 * output_image_count
        detail = f"Flash {output_image_count}张 × 2.5点/张 = {cost}点"
        return cost, detail
    else:  # Pro
        input_cost = 0.4 * max(input_image_count - 1, 0)  # 首张0点, 第二张起每张0.4点
        output_cost = 12 if size == "2K" else 6
        cost = input_cost + output_cost
        detail = f"Pro 输入{input_cost}点({input_image_count}张) + 输出{output_cost}点({size}) = {cost}点"
        return cost, detail



def _build_trace_id(cfg):
    """Generate x-hag-trace-id."""
    uid = cfg.personal_uid
    if uid:
        return f"{hashlib.sha256(uid.encode('utf-8')).hexdigest()[:32]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return str(uuid.uuid4())


def generate_image(
    prompt,
    input_image=None,
    size=None,
    watermark=True,
    model="Flash",
    optimize_prompt_mode="fast",
    cfg: Config = None):
    """Call the Xiaoyi image generation API.

    Args:
        model: "Flash" or "Pro". Both only support single-image-generation(单图生成);
               "Pro" has higher quality but is slower, "Flash" is faster and cheaper.
        optimize_prompt_mode: Prompt optimization mode, "fast" (default, Flash auto-maps to "disabled" internally), or "standard".
    """

    if cfg is None:
        cfg = Config.load()
    trace_id = _build_trace_id(cfg)

    # Build request headers (auth injected by skill_post)
    headers = {
        'x-skill-id': 'seedream',
        'x-hag-trace-id': trace_id,
        'x-request-from': 'openclaw',
    }

    # ── Model capability conflict detection and auto-switch ────────────────────
    # Flash/Pro both support at most 10 reference images
    if model == "Pro":
        if input_image is not None and len(input_image) > 10:
            print(f"⚠️  模型冲突：pro 最多仅支持10张参考图（当前 {len(input_image)} 张），已自动切换到 Flash")
            model = "Flash"

    # ── Resolution default based on model ─────────────────────────────────────
    # Flash defaults to 2K, Pro defaults to 1K; user-specified --size takes precedence
    # fast 模式下 size 参数无效，强制使用默认值
    if optimize_prompt_mode == "fast":
        size = "1K" if model == "Pro" else "2K"
        print(f"ℹ️  fast 模式下指定 size 无效，使用默认尺寸 {size}")
    elif size is None:
        size = "1K" if model == "Pro" else "2K"

    # ── Flash 不支持 fast 模式，自动映射为 disabled ────────────────────────────
    if model == "Flash" and optimize_prompt_mode == "fast":
        print(f"ℹ️  Flash 不支持 fast 模式，已自动切换为 disabled")

    # ── Set skillId and actionName based on model ──────────────────────────────
    # Flash: skillId=seedream, actionName=seedreamBatch5
    # Pro:   skillId=seedreamPro, actionName=SeedreamPro_5
    if model == "Pro":
        headers['x-skill-id'] = 'seedreamPro'
        action_name = 'SeedreamPro_5'
    else:
        headers['x-skill-id'] = 'seedream'
        action_name = 'seedreamBatch5'

    # 定义 content 字段，便于后续扩展
    # Flash 不支持 fast 模式，已映射为 disabled
    _effective_mode = "disabled" if (model == "Flash" and optimize_prompt_mode == "fast") else optimize_prompt_mode
    content = {
        "prompt": prompt,
        "size": size,
        "watermark": watermark,
        "response_format": "url",
    }
    if _effective_mode == "standard":
        content["optimize_prompt_options"] = {"mode": "standard"}

        # {"mode":"fast","thinking":"disabled"} 和 {"mode":"fast"}, {"thinking":"disabled"}区别不大
        # if _effective_mode == "fast":
        #     content["optimize_prompt_options"] = {"mode": "fast"}
    
    # 处理图片输入并添加到 content 中
    if input_image is not None:
        input_image = _process_image_input(input_image, cfg)
        content["reference_images"] = input_image

    payload = {
        "actions": [
            {
                "actionExecutorTask": {
                    "actionName": action_name,
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
            "isNew": False,
            "sessionId": "xxx"
        },
        "utterance": {
            "original": "",
            "type": "text"
        },
        "version": "1.0"
    }
    
    # Call API
    print(f"Generating image...")
    print(f"Prompt: {prompt[:30]}{'...' if len(prompt) > 30 else ''}")
    if optimize_prompt_mode == "standard":
        print(f"⚙️  提示词优化模式为 standard，生成时间可能较长，请耐心等待...")
    
    try:
        start_time = time.time()
        # Use stream to handle multiple responses (heartbeat packets)
        response = cfg.skill_post('/celia-claw/v1/sse-api/skill/execute', payload, headers=headers, stream=True)
        response.raise_for_status()
        
        # Read streaming responses until we get the final result
        image_urls = None
        
        print(f"⏳ Waiting for image generation API to complete...")
        
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
                    
                    # Check for top-level business error (e.g. InputImageSensitiveContentDetected)
                    # Numeric codes like 200 are HTTP-style status codes from heartbeat, skip them
                    top_level_code = result.get('code', '')
                    if top_level_code and str(top_level_code) not in ('0', '200'):
                        error_msg = result.get('desc', 'Unknown error')
                        print(f"❌ API Error: [{top_level_code}] {error_msg}")
                        continue

                    # Extract image URL from nested structure
                    ability_infos = result.get('abilityInfos', [])
                    if not ability_infos:
                        continue
                    
                    action_executor_result = ability_infos[0].get('actionExecutorResult', {})
                    if action_executor_result.get('code') != '0':
                        error_msg = action_executor_result.get('desc', 'Unknown error')
                        print(f"❌ API Error: {error_msg}")
                        continue
                    
                    reply = action_executor_result.get('reply', {})
                    
                    # Check for error inside reply (e.g. InputImageSensitiveContentDetected)
                    reply_code = reply.get('code', '')
                    if reply_code and str(reply_code) != '0':
                        if str(reply_code) == 'InputImageSensitiveContentDetected':
                            print("❌ API检测到输入的参考图包含敏感信息，请提示用户更换上传新的参考图后重试，禁止任何无参考图的替代生成。")
                        else:
                            reply_desc = reply.get('desc', 'Unknown error')
                            print(f"❌ API Error: [{reply_code}] {reply_desc}")
                        continue
                    
                    stream_info = reply.get('streamInfo', {})
                    stream_type = stream_info.get('streamType', '')
                    
                    # Check if this is a heartbeat packet or final response
                    if stream_type == 'final':
                        # This is the final response with image URLs
                        items = reply.get('items', [])
                        if items:
                            image_urls = items
                            elapsed = time.time() - start_time
                            print(f"✅ {len(image_urls)} image(s) generated in {elapsed:.1f}s")
                            # ── Cost calculation (for agent to read, not shown to user unless asked) ──
                            _input_count = len(input_image) if input_image else 0
                            _cost, _detail = calculate_cost(model, size, _input_count, len(image_urls))
                            print(f"📊 本次扣点: {_detail}")
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


def download_image(url, output_dir):
    """Download image and save to file."""
    
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
        
        print(f"💾 Images Saved to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate images with Seedream 5.0")
    parser.add_argument("--prompt", help="Text prompt for image generation")
    parser.add_argument(
        "--image",
        action="append",
        type=validate_image_input,
        help="Remote image URL (HTTP/HTTPS) or local file path. Repeat for multiple images."
    )
    parser.add_argument("--size", default=None, choices=["1K", "2K"], help="Output image size (default: Flash=2K, Pro=1K)")
    parser.add_argument("--output-path", default='.', help="Output file path")
    parser.add_argument("--watermark", action=argparse.BooleanOptionalAction, default=True,
                    help="Add watermark to generated image")
    parser.add_argument("--model", default="Flash", choices=["Flash", "Pro"],
                    help="Model to use: 'Flash' (faster, cheaper, single image only) or 'Pro' (higher quality, single image only). Default: Flash")
    parser.add_argument("--optimize-prompt-mode", default="fast", choices=["fast", "standard"],
                    help="Prompt optimization mode: 'fast' (default, Flash auto-maps to 'disabled'), or 'standard' (higher quality)")
    
    args = parser.parse_args()
    
    # Generate images
    cfg = Config.load()
    if not cfg.pipe_mode and (not cfg.personal_uid or not cfg.personal_api_key):
        print("Sandbox mode requires PERSONAL_API_KEY / PERSONAL_UID in .xiaoyienv")
        sys.exit(1)

    image_urls = generate_image(
        prompt=args.prompt,
        input_image=args.image,
        size=args.size,
        watermark=args.watermark,
        model=args.model,
        optimize_prompt_mode=args.optimize_prompt_mode,
        cfg=cfg,
    )
    
    if not image_urls:
        sys.exit(1)
    
    # Determine output directory
    output_dir = Path(args.output_path).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download all images
    print(f"\nDownloading {len(image_urls)} image(s)...")
    saved_paths = []
    for i, url in enumerate(image_urls, 1):
        saved_path = download_image(url, output_dir)
        if saved_path:
            saved_paths.append(saved_path)
    
    # Check if all downloads succeeded
    if len(saved_paths) < len(image_urls):
        print(f"\n⚠️  Warning: Only {len(saved_paths)} out of {len(image_urls)} images were successfully downloaded")
        sys.exit(1)
    

if __name__ == "__main__":
    main()
