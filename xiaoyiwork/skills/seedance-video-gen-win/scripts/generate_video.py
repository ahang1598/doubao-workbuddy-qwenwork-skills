#!/usr/bin/env python3
"""
基于 Seedance 的视频生成工具

使用 Celia Claw API 调用
"""

import os
import sys
import json
import time
import argparse
import hashlib
import subprocess
import io
import requests
from pathlib import Path
from typing import List, Dict, Optional, Literal, Tuple
from datetime import datetime, timedelta
import random
import string
import warnings
warnings.filterwarnings("ignore")

from config import Config
from claw_pipe_http import PipeHttpError
import uuid

FOLDER_PREFIX = "seedance_"


DEFAULT_RATIO = "adaptive"
DEFAULT_RESOLUTION = "480p"
DEFAULT_DURATION = 6
DEFAULT_AUDIO = True

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


def process_local_file(file_path, cfg):
    if not file_path:
        return None
    elif file_path.startswith("http"):
        return file_path
    elif os.path.isfile(file_path):
        print(f"📤 上传本地文件: {file_path}")
        uploaded_url = upload_file(file_path, cfg)
        if uploaded_url:
            print(f"✅ 文件上传成功: {uploaded_url}")
            return uploaded_url
        else:
            raise ValueError(f"❌ 文件上传失败: {file_path}")
    else:
        raise FileNotFoundError(f"❌ 输入无效：{file_path} 既不是有效的本地文件路径也不是有效的HTTP(S) URL")


def download_video(video_url: str, output_file: str):
    """
    下载视频到本地

    Args:
        video_url: 视频URL
        output_file: 输出文件路径
    """
    print(f"📥 下载视频...")
    download_response = requests.get(video_url, timeout=100, verify=False)
    download_response.raise_for_status()
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(download_response.content)
    print(f"✅ 视频已保存")

# ============================================================================
# 媒体文件校验函数
# ============================================================================

# 支持的图片格式（按模型系列区分）
IMAGE_FORMATS = {'.jpeg', '.jpg', '.png', '.webp', '.bmp', '.tiff','.tif', '.gif', '.heic', '.heif'}

# 支持的视频格式
VIDEO_FORMATS = {'.mp4', '.mov'}

# 支持的音频格式
AUDIO_FORMATS = {'.wav', '.mp3'}


def get_media_info(file_path: str) -> dict:
    """
    使用 ffprobe 获取媒体文件的元信息

    Returns:
        {
            "width": int,
            "height": int,
            "duration": float,   # 秒
            "fps": float,
            "codec_name": str,
            "codec_long_name": str
        }
        如果获取失败，返回空字典
    """
    info = {}
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"⚠️  ffprobe 无法解析文件: {file_path}")
            return info

        data = json.loads(result.stdout)

        # 获取时长（优先从 format 获取）
        if "format" in data and "duration" in data["format"]:
            info["duration"] = float(data["format"]["duration"])

        # 获取视频流信息
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                info["width"] = stream.get("width", 0)
                info["height"] = stream.get("height", 0)
                info["codec_name"] = stream.get("codec_name", "")
                info["codec_long_name"] = stream.get("codec_long_name", "")
                # 帧率：可能是 "30/1" 或 "30000/1001" 等形式
                r_frame_rate = stream.get("r_frame_rate", "")
                if r_frame_rate and "/" in r_frame_rate:
                    try:
                        num, den = r_frame_rate.split("/")
                        info["fps"] = float(num) / float(den) if float(den) != 0 else 0
                    except (ValueError, ZeroDivisionError):
                        info["fps"] = 0
                break  # 只取第一个视频流

        # 获取音频流信息
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                info["audio_codec"] = stream.get("codec_name", "")
                info["audio_duration"] = info.get("duration", 0)
                break

    except FileNotFoundError:
        print("⚠️  未找到 ffprobe，请安装 ffmpeg 以启用媒体文件校验")
    except subprocess.TimeoutExpired:
        print(f"⚠️  ffprobe 解析超时: {file_path}")
    except Exception as e:
        print(f"⚠️  获取媒体信息异常: {e}")

    return info


def validate_image(file_path: str) -> Tuple[bool, str]:
    """
    校验图片文件是否符合要求

    Args:
        file_path: 图片文件路径

    Returns:
        (is_valid, error_message)
    """
    if not os.path.isfile(file_path):
        return False, f"文件不存在: {file_path}"

    # 1. 格式校验
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in IMAGE_FORMATS:
        return False, (
            f"不支持的图片格式: {ext}。"
            f"当前支持: jpeg, jpg, png, webp, bmp, tiff, tif, gif, heic, heif"
        )

    # 2. 文件大小校验（单张 < 30MB）
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb >= 30:
        return False, f"图片文件过大: {file_size_mb:.1f}MB，单张图片应小于 30MB，提示用户重新上传"

    # 3. 分辨率校验（宽、高均须在 [300, 6000] px 内）
    media_info = get_media_info(file_path)
    width = media_info.get("width", 0)
    height = media_info.get("height", 0)
    if width > 0 and height > 0:
        if width < 300 or width > 6000 or height < 300 or height > 6000:
            return False, (
                f"图片分辨率 {width}x{height} 超出范围，宽、高均须在 "
                f"[300, 6000] px 内，提示用户重新上传"
            )
        # 4. 宽高比校验（width / height ∈ [0.4, 2.5]）
        aspect_ratio = width / height
        if aspect_ratio < 0.4 or aspect_ratio > 2.5:
            return False, (
                f"图片宽高比 {aspect_ratio:.2f}（{width}x{height}）超出范围 "
                f"[0.4, 2.5]，提示用户重新上传"
            )
    else:
        print(f"⚠️  无法获取图片分辨率: {file_path}，跳过分辨率/宽高比校验")

    return True, ""


def validate_video(file_path: str) -> Tuple[bool, str]:
    """
    校验视频文件是否符合要求

    Returns:
        (is_valid, error_message)
    """
    if not os.path.isfile(file_path):
        return False, f"文件不存在: {file_path}"

    # 1. 格式校验
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in VIDEO_FORMATS:
        return False, f"不支持的视频格式: {ext}，支持: mp4, mov"

    # 2. 文件大小校验（单个 ≤ 200MB）
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 200:
        return False, f"视频文件过大: {file_size_mb:.1f}MB，单个视频应不超过 200MB，提示用户重新上传"

    # 3. 获取视频元信息
    media_info = get_media_info(file_path)
    duration = media_info.get("duration", 0)

    if duration > 0:
        if duration < 2 or duration > 15:
            return False, f"视频时长 {duration:.1f}s 超出范围 [2s, 15s]，提示用户重新上传"
    else:
        print(f"⚠️  无法获取视频时长: {file_path}，跳过时长校验")

    # 4. 总像素数校验（width × height ∈ [409600, 8295044]）
    width = media_info.get("width", 0)
    height = media_info.get("height", 0)
    if width > 0 and height > 0:
        total_pixels = width * height
        if total_pixels < 409600 or total_pixels > 8295044:
            return False, (
                f"视频分辨率 {width}x{height}（总像素 {total_pixels}）超出范围 "
                f"[409600, 8295044]，提示用户重新上传"
            )
        # 5. 宽高比校验（width / height ∈ [0.4, 2.5]）
        aspect_ratio = width / height
        if aspect_ratio < 0.4 or aspect_ratio > 2.5:
            return False, (
                f"视频宽高比 {aspect_ratio:.2f}（{width}x{height}）超出范围 "
                f"[0.4, 2.5]，提示用户重新上传"
            )
    else:
        print(f"⚠️  无法获取视频分辨率: {file_path}，跳过总像素/宽高比校验")

    return True, ""


def validate_audio(file_path: str) -> Tuple[bool, str]:
    """
    校验音频文件是否符合要求

    Returns:
        (is_valid, error_message)
    """
    if not os.path.isfile(file_path):
        return False, f"文件不存在: {file_path}"

    # 1. 格式校验
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in AUDIO_FORMATS:
        return False, f"不支持的音频格式: {ext}，支持: wav, mp3"

    # 2. 文件大小校验（单个 ≤ 15MB）
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 15:
        return False, f"音频文件过大: {file_size_mb:.1f}MB，单个音频应不超过 15MB，提示用户重新上传"

    # 3. 获取音频时长
    media_info = get_media_info(file_path)
    duration = media_info.get("duration", 0)

    if duration > 0:
        # 时长校验 [2, 15]s
        if duration < 2 or duration > 15:
            return False, f"音频时长 {duration:.1f}s 超出范围 [2s, 15s]，提示用户重新上传"
    else:
        print(f"⚠️  无法获取音频时长: {file_path}，跳过时长校验")

    return True, ""
# ============================================================================
# 核心视频生成函数
# ============================================================================


def _build_trace_id(cfg):
    """Generate x-hag-trace-id: pipe mode uses random; sandbox mode uses uid-based."""
    uid = cfg.personal_uid
    if uid:
        return f"{hashlib.sha256(uid.encode('utf-8')).hexdigest()[:32]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return uuid.uuid4().hex


def create_video_generation_task(
    prompt: str,
    first_frame_path: str = None,
    last_frame_path: str = None,
    duration: int = 5,
    ratio: str = "adaptive",
    resolution: str = "720p",
    generate_audio: bool = True,
    watermark: bool = True,
    web_search: bool = False,
    reference_images: Optional[List[str]] = None,
    reference_videos: Optional[List[str]] = None,
    reference_audios: Optional[List[str]] = None,
    cfg: Config = None,
) -> str:
    """
    创建视频生成任务，返回任务ID

    Args:
        prompt: 文本提示词
        first_frame_path: 首帧图片URL
        last_frame_path: 尾帧图片URL
        duration: 视频时长（秒）
        ratio: 视频比例
        resolution: 视频分辨率
        watermark: 是否添加水印
        generate_audio: 是否生成同步音频
        reference_images: 参考图片URL列表
        reference_videos: 参考视频URL列表
        reference_audios: 参考音频URL列表

    Returns:
        任务ID (str)
    """
    if cfg is None:
        cfg = Config.load()
    trace_id = _build_trace_id(cfg)

    first_frame_url = process_local_file(first_frame_path, cfg)
    last_frame_url = process_local_file(last_frame_path, cfg)
    reference_image_urls = [process_local_file(p, cfg) for p in (reference_images or [])]
    reference_video_urls = [process_local_file(p, cfg) for p in (reference_videos or [])]
    reference_audio_urls = [process_local_file(p, cfg) for p in (reference_audios or [])]

    # 构建content数组
    content = [{"type": "text", "text": prompt}]

    if first_frame_url:
        content.append({"type": "image_url", "image_url": {"url": first_frame_url}, "role": "first_frame"})

    for img_url in reference_image_urls:
        content.append({"type": "image_url", "image_url": {"url": img_url}, "role": "reference_image"})

    if last_frame_url:
        content.append({"type": "image_url", "image_url": {"url": last_frame_url}, "role": "last_frame"})

    for vid_url in reference_video_urls:
        content.append({"type": "video_url", "video_url": {"url": vid_url}, "role": "reference_video"})

    for aud_url in reference_audio_urls:
        content.append({"type": "audio_url", "audio_url": {"url": aud_url}, "role": "reference_audio"})

    # 构建content_data对象，包含content列表和其他参数
    content_data = {
        "actionName": "seedanceMiniTask",
        "content": content,
        "duration": duration,
        "ratio": ratio,
        "resolution": resolution,
        "generate_audio": generate_audio,
        "watermark": watermark
    }

    # 构建完整的请求体
    payload = {
        "endpoint": {
            "device": {
                "prdVer": "13.0.12.100",
                "phoneType": "CDY-AN00",
                "sysVer": "HarmonyOS_3.0.0",
                "deviceType": 0,
                "timezone": "GMT+08:00",
            },
            "privacyOption": {
                "personalizedRecommend": 1
            },
            "locale": "zh-CN",
            "sysLocale": "zh-CN",
            "countryCode": "CN"
        },
        "actions": [
            {
                "actionSn": "1",
                "actionExecutorTask": {
                    "actionName": "seedanceMiniTask",
                    "pluginId": "2c6c2cf21cb34a87bf114929c0d9c1f8",
                    "content": content_data,
                }
            }
        ],
        "utterance": {
            "type": "string",
            "original": "string"
        },
        "version": "1.0",
        "session": {
            "isNew": True,
            "sessionId": "string",
            "attributes": "string"
        }
    }

    # 业务请求头（鉴权头由 skill_post 自动注入）
    headers = {
        'x-request-from': 'openclaw',
        'x-prd-pkg-name': 'com.huawei.hmos.vassistant',
        'x-skill-id': 'seedance15pro',
        'x-hag-trace-id': trace_id
    }

    print(f"🎬 创建视频生成任务...")

    try:
        resp = cfg.skill_post('/celia-claw/v1/rest-api/skill/execute', payload, headers=headers)

        if resp.status_code != 200:
            raise RuntimeError(f"创建任务失败: HTTP {resp.status_code}: {resp.text}")

        result = resp.json()

    except requests.exceptions.Timeout:
        raise RuntimeError("创建任务失败: 请求超时")
    except (requests.exceptions.HTTPError, PipeHttpError) as e:
        raise RuntimeError(f"创建任务失败: HTTP错误: {e}")
    except Exception as e:
        raise RuntimeError(f"创建任务失败: {e}") from e

    # 检查actionExecutorResult中的code字段（业务层，"0"表示成功）
    ability_infos = result.get('abilityInfos', [])
    if ability_infos:
        action_executor_result = ability_infos[0].get('actionExecutorResult', {})
        if action_executor_result:
            business_code = action_executor_result.get('code')
            if business_code and business_code != '0':
                # 业务逻辑失败，如用户权益校验失败等
                error_msg = action_executor_result.get('desc', '未知错误')
                print(f"❌ 创建任务失败: {error_msg}")
                print(f"   业务错误码: {business_code}")
                raise RuntimeError(f"创建任务失败: {error_msg}")

    # 从响应中提取任务ID
    task_id = None
    try:
        if ability_infos:
            action_executor_result = ability_infos[0].get('actionExecutorResult', {})
            reply = action_executor_result.get('reply', {})
            items = reply.get('items', [])
            if items:
                # 响应中字段名为 'id' 而不是 'taskId'
                task_id = items[0].get('id')
    except Exception as e:
        print(f"⚠️  解析任务ID时出现警告: {e}")

    if not task_id:
        raise RuntimeError(f"创建任务失败: 未返回任务ID。响应: {result}")

    print(f"✅ 任务创建成功，任务ID: {task_id}")
    return task_id


def query_video_generation_task(
    task_id: str,
    output_file: str = None,
    poll_interval_s: int = 5,
    max_wait_time: int = 600,
    cfg: Config = None,
) -> dict:
    """
    查询视频生成任务状态，完成后下载视频

    Args:
        task_id: 任务ID
        output_file: 输出文件路径（可选）
        poll_interval_s: 轮询间隔（秒）
        max_wait_time: 最大等待时间（秒）

    Returns:
        {
            "video_path": "视频路径",
            "task_id": "任务ID"
        }
    """
    if cfg is None:
        cfg = Config.load()
    trace_id = _build_trace_id(cfg)

    # 确保输出目录存在
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        timestamp = int(time.time())
        output_file = Path.cwd() / f"scene_{timestamp}.mp4"

    headers = {
        'x-request-from': 'openclaw',
        'x-prd-pkg-name': 'com.huawei.hmos.vassistant',
        'x-skill-id': 'seedance15pro',
        'x-hag-trace-id': trace_id
    }

    # ──────────────────────────────────────────────
    # 轮询查询任务状态
    # ──────────────────────────────────────────────

    print(f"\n⏳ 等待视频生成[{task_id}]...")
    started = time.time()
    last_status = None

    query_payload = {
        "endpoint": {
            "device": {
                "prdVer": "13.0.12.100",
                "phoneType": "CDY-AN00",
                "sysVer": "HarmonyOS_3.0.0",
                "deviceType": 0,
                "timezone": "GMT+08:00",
            },
            "privacyOption": {
                "personalizedRecommend": 1
            },
            "locale": "zh-CN",
            "sysLocale": "zh-CN",
            "countryCode": "CN"
        },
        "actions": [
            {
                "actionSn": "1",
                "actionExecutorTask": {
                    "actionName": "seedanceMiniTaskQuery",
                    "pluginId": "2c6c2cf21cb34a87bf114929c0d9c1f8",
                    "content": {
                        "id": task_id,
                        "actionName": "seedanceMiniTaskQuery"
                    }
                }
            }
        ],
        "utterance": {
            "type": "string",
            "original": "string"
        },
        "version": "1.0",
        "session": {
            "isNew": True,
            "sessionId": "string",
            "attributes": "string"
        }
    }

    video_url=None
    while True:
        if time.time() - started > max_wait_time:
            print(f"❌ 任务超时({max_wait_time}s): {task_id}")
            return {}

        time.sleep(max(1, poll_interval_s))

        # 查询任务状态
        try:
            query_resp = cfg.skill_post('/celia-claw/v1/rest-api/skill/execute', query_payload, headers=headers)

            query_result = query_resp.json()

            # 检查actionExecutorResult中的code字段（业务层，"0"表示成功）
            ability_infos = query_result.get('abilityInfos', [])
            if ability_infos:
                action_executor_result = ability_infos[0].get('actionExecutorResult', {})
                if action_executor_result:
                    business_code = action_executor_result.get('code')
                    if business_code and business_code != '0':
                        # 业务逻辑失败，如用户权益校验失败等
                        error_msg = action_executor_result.get('desc', '未知错误')
                        print(f"❌ 查询任务失败: {error_msg}")
                        print(f"   业务错误码: {business_code}")
                        raise RuntimeError(f"查询任务失败: {error_msg}")

        except requests.exceptions.Timeout:
            print(f"⚠️  查询任务超时")
            time.sleep(poll_interval_s)
            continue
        except requests.exceptions.HTTPError as e:
            print(f"⚠️  查询任务失败: HTTP错误: {e}")
            time.sleep(poll_interval_s)
            continue
        except Exception as e:
            print(f"⚠️  查询任务异常: {e}")
            time.sleep(poll_interval_s)
            continue

        # 解析查询结果
        try:
            ability_infos = query_result.get('abilityInfos', [])
            if not ability_infos:
                print(f"⚠️  查询响应格式异常: {query_result}")
                time.sleep(poll_interval_s)
                continue

            action_executor_result = ability_infos[0].get('actionExecutorResult', {})
            reply = action_executor_result.get('reply', {})
            items = reply.get('items', [])

            if not items:
                print(f"⚠️  未找到任务结果")
                time.sleep(poll_interval_s)
                continue

            task_info = items[0]
            status = task_info.get('status', '')

            # 根据实际API返回，status字段判断任务状态
            if status == 'succeeded':
                # 任务成功
                content = task_info.get('content', {})
                video_url = content.get('video_url', '')

                if not video_url:
                    print(f"❌ 任务成功但未返回视频URL: {task_info}")
                    return {}
                print(f"✅ 任务完成，视频URL: {video_url}")
                break

            elif status == 'running':
                # 任务进行中
                if status != last_status:
                    print(f"   状态: {status}... (任务进行中)")
                    last_status = status
            else:
                # 任务失败或其他异常状态
                error_msg = task_info.get('message', '') or task_info.get('desc', status)
                print(f"❌ 视频生成失败: {error_msg}")
                return {}

        except Exception as e:
            print(f"⚠️  解析查询结果时出现错误: {e}")
            time.sleep(poll_interval_s)
            continue

    # 下载视频
    try:
        download_video(video_url, str(output_file))
    except Exception as e:
        print(f"❌ 下载视频失败: {e}")
        return {}

    return {
        "video_path": str(output_file),
        "task_id": task_id
    }


# ============================================================================
# 任务管理工具函数
# ============================================================================

def create_task_folder(base_dir: str) -> Path:
    """
    为每次任务创建独立的文件夹

    Args:
        base_dir: 基础输出目录
        task_name: 任务名称（可选）

    Returns:
        任务文件夹路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{FOLDER_PREFIX}{timestamp}"

    task_folder = Path(base_dir).expanduser() / folder_name
    task_folder.mkdir(parents=True, exist_ok=True)

    print(f"📁 创建任务文件夹: {task_folder}")
    return task_folder


def check_recent_tasks(base_dir: str, minutes: int = 2) -> Optional[Path]:
    """
    检查指定分钟内是否创建过任务文件夹

    Args:
        base_dir: 基础输出目录
        minutes: 检查的分钟数（默认2分钟）

    Returns:
        如果2分钟内创建过任务，返回最新的任务文件夹路径；否则返回None
    """
    base_dir = Path(base_dir).expanduser()

    if not base_dir.exists():
        return None

    # 获取截止时间（2分钟前）
    cutoff_time = datetime.now() - timedelta(minutes=minutes)

    # 遍历所有匹配的视频任务文件夹
    task_folders = []
    for item in base_dir.iterdir():
        if item.is_dir() and item.name.startswith(FOLDER_PREFIX):
            # 解析时间戳：video_YYYYMMDD_HHMMSS
            try:
                timestamp_str = item.name[len(FOLDER_PREFIX):]   # 取时间戳部分
                folder_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                # 检查是否在2分钟内
                if folder_time >= cutoff_time:
                    task_folders.append((folder_time, item))
            except (ValueError, IndexError):
                continue

    # 按时间排序，返回最新的一个
    if task_folders:
        task_folders.sort(reverse=True)
        latest_folder = task_folders[0][1]

        elapsed = datetime.now() - task_folders[0][0]
        print(f"⚠️  检测到 {elapsed.seconds//60} 分钟前创建过任务文件夹: {latest_folder}")
        print(f"🛑 跳过本次视频生成")
        return latest_folder

    return None


def generate_script_videos(
    script_file: str,
    first_frame_path: Optional[str] = None,
    last_frame_path: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    reference_videos: Optional[List[str]] = None,
    reference_audios: Optional[List[str]] = None,
    output_dir: str = ".",
    watermark: bool = True,
    cfg: Config = None,
) -> List[Dict]:
    """
    根据脚本生成视频

    支持模式：
    - 文生视频：仅文本提示词
    - 图生视频-首帧：首帧图片 + 文本提示词
    - 图生视频-首尾帧：首帧图片 + 尾帧图片 + 文本提示词
    - 多模态参考：参考图/视频/音频 + 文本提示词

    Args:
        script_file: JSON 脚本文件路径
        first_frame_path: 首帧图片路径
        last_frame_path: 尾帧图片路径
        reference_images: 参考图片路径列表
        reference_videos: 参考视频路径列表
        reference_audios: 参考音频路径列表
        output_dir: 输出目录
        model: 模型 ID

    Returns:
        生成的视频信息列表 [{"video_path": ...}]
    """
    if reference_audios and not reference_videos and not reference_images:
        raise ValueError("❌ 不可单独输入音频，应至少包含1个参考视频或图片")

    if reference_images and len(reference_images) > 9:
        raise ValueError("❌ 参考图片最多9张")

    if reference_videos and len(reference_videos) > 3:
        raise ValueError("❌ 参考视频最多3个")

    if reference_audios and len(reference_audios) > 3:
        raise ValueError("❌ 参考音频最多3个")

    # 读取脚本
    with open(script_file, "r", encoding="utf-8") as f:
        script = json.load(f)

    # 新格式：直接从顶层获取字段
    prompt = script.get("prompt")
    duration = script.get("duration", DEFAULT_DURATION)
    ratio = script.get("ratio", DEFAULT_RATIO)
    resolution = script.get("resolution", DEFAULT_RESOLUTION)
    generate_audio = script.get("generate_audio", DEFAULT_AUDIO)
    web_search = script.get("web_search", False)

    if not prompt:
        raise ValueError("❌ 脚本中没有 prompt 字段")

    if duration < 4 or duration > 15:
        raise ValueError(f"⚠️  视频时长 {duration} 秒超出限制 (4-15秒)，暂时不支持")

    print(f"\n{'='*60}")
    print(f"开始生成视频")
    print(f"{'='*60}")
    print(f"提示词: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"时长: {duration}秒")
    print(f"比例: {ratio}")
    print(f"分辨率: {resolution}")
    print(f"音频: {'是' if generate_audio else '否'}")
        # ============================================================
    # 媒体文件校验
    # ============================================================

    # 校验首帧图片
    if first_frame_path:
        valid, err_msg = validate_image(first_frame_path)
        if not valid:
            raise ValueError(f"❌ 首帧图片校验失败: {err_msg}")

    # 校验尾帧图片
    if last_frame_path:
        valid, err_msg = validate_image(last_frame_path)
        if not valid:
            raise ValueError(f"❌ 尾帧图片校验失败: {err_msg}")

    # 校验参考图片
    for img_path in (reference_images or []):
        valid, err_msg = validate_image(img_path)
        if not valid:
            raise ValueError(f"❌ 参考图片校验失败 ({img_path}): {err_msg}")

    # 校验参考视频
    total_video_duration = 0.0
    for vid_path in (reference_videos or []):
        valid, err_msg = validate_video(vid_path)
        if not valid:
            raise ValueError(f"❌ 参考视频校验失败 ({vid_path}): {err_msg}")
        # 累计视频总时长
        media_info = get_media_info(vid_path)
        total_video_duration += media_info.get("duration", 0)

    if reference_videos and total_video_duration > 15:
        raise ValueError(
            f"❌ 所有参考视频总时长 {total_video_duration:.1f}s 超过限制 15s，提示用户重新上传"
        )

    # 校验参考音频
    total_audio_duration = 0.0
    for aud_path in (reference_audios or []):
        valid, err_msg = validate_audio(aud_path)
        if not valid:
            raise ValueError(f"❌ 参考音频校验失败 ({aud_path}): {err_msg}")
        # 累计音频总时长
        media_info = get_media_info(aud_path)
        total_audio_duration += media_info.get("duration", 0)

    if reference_audios and total_audio_duration > 15:
        raise ValueError(
            f"❌ 所有参考音频总时长 {total_audio_duration:.1f}s 超过限制 15s，提示用户重新上传"
        )
    # ============================================================

    if first_frame_path:
        print(f"首帧图: {first_frame_path}")
    if last_frame_path:
        print(f"尾帧图: {last_frame_path}")
    if reference_images:
        print(f"参考图片: {reference_images}")
    if reference_videos:
        print(f"参考视频: {reference_videos}")
    if reference_audios:
        print(f"参考音频: {reference_audios}")
    print()

    # 创建任务文件夹
    task_folder = create_task_folder(output_dir)

    # 保存脚本副本到任务文件夹
    script_copy_path = task_folder / "script.json"
    with open(script_copy_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    # 生成视频
    try:
        # 构建输出文件路径
        now_time = datetime.now()
        ms = now_time.strftime('%f')[:3]
        base_time = now_time.strftime('%Y%m%d_%H%M%S')

        # 2 位随机字符
        random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=2))

        timestamp = f"{base_time}_{ms}_{random_chars}"
        scene_filename = f"{timestamp}_generated.mp4"

        output_file = str(task_folder / scene_filename)

        task_id = create_video_generation_task(
            prompt=prompt,
            first_frame_path=first_frame_path,
            last_frame_path=last_frame_path,
            duration=duration,
            ratio=ratio,
            resolution=resolution,
            generate_audio=generate_audio,
            watermark=watermark,
            web_search=web_search,
            reference_images=reference_images,
            reference_videos=reference_videos,
            reference_audios=reference_audios,
            cfg=cfg,
        )
        # 查询任务并等待完成
        video_result = query_video_generation_task(
            task_id=task_id,
            output_file=output_file,
            cfg=cfg,
        )
    except Exception as e:
        print(f"❌ 视频生成失败: {e}")
        import traceback
        traceback.print_exc()
        try:
            import shutil
            shutil.rmtree(task_folder, ignore_errors=True)
            print(f"🧹 已清理失败的任务文件夹：{task_folder}")
        except Exception as clean_err:
            print(f"⚠️ 清理失败：{clean_err}")
        raise

    # 生成摘要
    print(f"视频生成完成！视频路径:\n{video_result.get('video_path', 'N/A')}")
    return video_result


def main():
    parser = argparse.ArgumentParser(
        description="基于 Seedance 的视频生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 纯文生视频
  python3 generate_video.py --script script.json

  # 首帧图生视频
  python3 generate_video.py --script script.json --first-frame first.png

  # 首尾帧图生视频
  python3 generate_video.py --script script.json --first-frame first.png --last-frame last.png

  # 多模态参考（参考图+参考视频+参考音频）
  python3 generate_video.py --script script.json --reference-images img1.jpg img2.jpg --reference-videos vid1.mp4 --reference-audios audio1.mp3

  # 参考图片（最多9张）
  python3 generate_video.py --script script.json --reference-images img1.jpg img2.jpg img3.jpg

支持模式:
  - 文生视频：仅文本提示词
  - 图生视频-首帧：首帧图片 + 文本提示词
  - 图生视频-首尾帧：首帧图片 + 尾帧图片 + 文本提示词
  - 多模态参考：参考图/视频/音频 + 文本提示词

注意:
  - 不可单独输入音频，需至少1个参考视频或图片
  - 参考图片最多9张，参考视频最多3个，参考音频最多3个
  - 2分钟内创建过任务则跳过本次生成
        """,
    )

    parser.add_argument(
        "--script",
        required=True,
        help="JSON 脚本文件路径",
    )
    parser.add_argument(
        "--first-frame",
        default=None,
        help="首帧图片路径，用于首帧图生视频模式或首尾帧图生视频模式",
    )
    parser.add_argument(
        "--last-frame",
        default=None,
        help="尾帧图片路径，用于首尾帧图生视频模式",
    )
    parser.add_argument(
        "--reference-images",
        nargs="*",
        default=[],
        help="参考图片路径列表（最多9张）",
    )
    parser.add_argument(
        "--reference-videos",
        nargs="*",
        default=[],
        help="参考视频路径列表（最多3个）",
    )
    parser.add_argument(
        "--reference-audios",
        nargs="*",
        default=[],
        help="参考音频路径列表（最多3个）",
    )
    parser.add_argument(
        "--output-path",
        default=".",
        help="输出目录（绝对路径，支持 ~ 展开）",
    )
    parser.add_argument("--watermark", action=argparse.BooleanOptionalAction, default=True,
        help="Add watermark to generated video (default: True)")

    args = parser.parse_args()

    # 校验脚本文件（必须是本地文件）
    if not os.path.exists(args.script):
        print(f"❌ 脚本文件不存在: {args.script}", file=sys.stderr)
        sys.exit(1)

    # 校验首尾帧组合
    if args.last_frame and not args.first_frame:
        print(
            f"❌ 参数错误：传入了 --last-frame 但未传入 --first-frame。\n"
            f"首尾帧图生视频需要同时提供首帧和尾帧图片。",
            file=sys.stderr,
        )
        sys.exit(1)

    # 校验首帧/首尾帧与参考图片互斥
    has_frame = bool(args.first_frame) or bool(args.last_frame)
    has_ref_images = bool(args.reference_images)
    has_ref_videos = bool(args.reference_videos)
    has_ref_audios = bool(args.reference_audios)

    if has_frame and (has_ref_images or has_ref_videos or has_ref_audios):
        print(
            f"❌ 参数错误：首帧/首尾帧图片（--first-frame / --last-frame）不能与参考图片/视频/音频（--reference-images、--reference-videos、--reference-audios）同时使用。\n"
            f"请选择其中一种模式：\n"
            f"  - 首帧/首尾帧模式：使用 --first-frame [和 --last-frame] 控制视频首尾画面\n"
            f"  - 多模态参考模式：使用 --reference-images、--reference-videos、--reference-audios 指定参考图片、视频、音频",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        # 检查2分钟内是否创建过任务
        recent_task = check_recent_tasks(args.output_path)
        if recent_task:
            raise ValueError(f"⚠️  2分钟内创建过视频生成任务，跳过当前视频生成任务。最近的任务文件夹: {recent_task}")

        cfg = Config.load()
        if not cfg.pipe_mode and (not cfg.personal_uid or not cfg.personal_api_key):
            print("Sandbox mode requires PERSONAL_API_KEY / PERSONAL_UID in .xiaoyienv")
            sys.exit(1)

        video_result = generate_script_videos(
            script_file=args.script,
            first_frame_path=args.first_frame,
            last_frame_path=args.last_frame,
            reference_images=args.reference_images,
            reference_videos=args.reference_videos,
            reference_audios=args.reference_audios,
            output_dir=args.output_path,
            watermark=args.watermark,
            cfg=cfg,
        )

    except Exception as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
