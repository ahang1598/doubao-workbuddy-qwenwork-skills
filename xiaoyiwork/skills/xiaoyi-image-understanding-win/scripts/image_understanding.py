#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小艺图像理解 - 支持本地图片和公网 URL

用法:
  python3 image_understanding.py --image "图片URL或本地路径" --prompt "图中讲了什么"
  python3 image_understanding.py --image "图片路径" --prompt "描述图中人物的表情和动作"
  python3 image_understanding.py --image img1.jpg img2.jpg img3.jpg --prompt "描述这些图片"
  python3 image_understanding.py --image img1.jpg --image img2.jpg --prompt "对比这两张图"

桌面形态 SERVICE_URL=np://claw-skill（默认）：经主进程 skill API 代理转发，
businessCredential 鉴权由主进程注入，本进程零业务凭证；图片上传 phase2 的
预签名 URL 直传（URL 本身即一次性凭证）不经代理。
"""

import uuid
import json
import os
import sys
import ssl
import hashlib
import argparse
import tempfile
import requests
import urllib3
from PIL import Image
from datetime import datetime

from config import Config
from claw_pipe_http import PipeHttpError, PipeHttpTimeout

MAX_RESOLUTION = 2048  # 最大边长 2K
UPLOAD_TIMEOUT_SEC = 180

# 禁用 SSL 验证（华为内网需要；仅旧沙箱直连形态使用）
ssl._create_default_https_context = ssl._create_unverified_context

# 禁用 urllib3 的 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ── 文件上传 ──────────────────────────────────────────────────

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

    phase1/3 经主进程 skill API 代理（管道形态，鉴权主进程注入）；
    phase2 预签名 URL 直传（URL 本身即一次性凭证，不经代理）。

    Args:
        file_path: 本地文件路径
        cfg: Config 配置
        object_type: 文件类型（默认 TEMPORARY_MATERIAL_DOC）

    Returns:
        str: fileUrl，失败返回 None
    """
    try:
        if not os.path.isfile(file_path):
            print(f'❌ 文件不存在: {file_path}')
            return None

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_sha256 = calculate_sha256(file_path)

        # ── 阶段 1: Prepare（经主进程管道代理；旧沙箱形态 requests 直连）──
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
                print(f'❌ Prepare 失败: HTTP {prepare_resp.status_code}')
                return None
            prepare_data = prepare_resp.json()

        if 'code' in prepare_data and prepare_data['code'] != '0':
            print(f'❌ Prepare 失败: {prepare_data.get("desc", "未知错误")}')
            return None

        object_id = prepare_data.get('objectId')
        draft_id = prepare_data.get('draftId')
        upload_infos = prepare_data.get('uploadInfos', [])

        if not object_id or not draft_id or not upload_infos:
            print('❌ Prepare 响应缺少必要字段')
            return None

        upload_info = upload_infos[0]
        upload_url = upload_info['url']
        upload_method = upload_info.get('method', 'PUT').upper()
        upload_headers = upload_info.get('headers', {'Content-Type': 'application/octet-stream'})

        # ── 阶段 2: Upload —— 预签名 URL 直传（URL 本身即一次性凭证、无业务鉴权，不经主进程代理）──
        with open(file_path, 'rb') as f:
            file_data = f.read()

        upload_resp = requests.request(
            method=upload_method, url=upload_url, headers=upload_headers,
            data=file_data, timeout=(30, UPLOAD_TIMEOUT_SEC), verify=False
        )

        if upload_resp.status_code not in (200, 204):
            print(f'❌ 文件上传失败: HTTP {upload_resp.status_code}')
            return None

        # ── 阶段 3: Complete（经主进程管道代理）──
        complete_payload = {'objectId': object_id, 'draftId': draft_id}

        with cfg.skill_post('/osms/v1/file/manager/completeAndQuery', complete_payload) as complete_resp:
            if complete_resp.status_code != 200:
                print(f'❌ Complete 失败: HTTP {complete_resp.status_code}')
                return None
            complete_data = complete_resp.json()

        file_url = complete_data.get('fileDetailInfo', {}).get('url', '')

        if not file_url:
            print('❌ Complete 响应中未获取到文件 URL')
            return None

        print(f'✅ 图片上传成功 (objectId={object_id})')
        return file_url

    except requests.exceptions.Timeout:
        print('❌ 上传超时')
        return None
    except (requests.exceptions.ConnectionError, PipeHttpError) as e:
        print(f'❌ 连接失败: {e}')
        return None
    except Exception as e:
        print(f'❌ 上传异常: {e}')
        return None


# ── 图像理解核心逻辑 ──────────────────────────────────────────

def _resize_if_needed(file_path):
    """
    如果图片分辨率超过 MAX_RESOLUTION×MAX_RESOLUTION，等比例缩放并保存到临时文件

    Returns:
        str: 实际上传的文件路径（原文件或缩放后的临时文件）
    """
    try:
        img = Image.open(file_path)
        w, h = img.size
        if w <= MAX_RESOLUTION and h <= MAX_RESOLUTION:
            return file_path

        # 等比例缩放，长边对齐 MAX_RESOLUTION
        ratio = min(MAX_RESOLUTION / w, MAX_RESOLUTION / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img_resized = img.resize((new_w, new_h), Image.LANCZOS)

        # 保存到临时文件，保留原格式
        fmt = img.format or 'PNG'
        suffix = os.path.splitext(file_path)[1] or '.png'
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        save_kwargs = {'format': fmt}
        if fmt == 'JPEG':
            save_kwargs['quality'] = 95
        img_resized.save(tmp, **save_kwargs)
        tmp.close()

        print(f'📐 缩放: {w}×{h} → {new_w}×{new_h}')
        return tmp.name
    except Exception as e:
        print(f'⚠️ 缩放失败，使用原图: {e}')
        return file_path


def _resolve_image_url(image_path, cfg):
    """
    将图片路径解析为公网 URL
    - 已经是 http/https URL → 直接返回
    - 本地文件路径 → 缩放（如需）→ 上传后返回 URL

    Args:
        image_path: 图片路径
        cfg: Config 配置

    Returns:
        str: 公网 URL，失败返回 None
    """
    if image_path.startswith(('http://', 'https://')):
        return image_path

    if not os.path.isfile(image_path):
        print(f'❌ 文件不存在: {image_path}')
        return None

    upload_path = _resize_if_needed(image_path)
    file_url = upload_file(upload_path, cfg)

    # 清理临时文件
    if upload_path != image_path:
        try:
            os.unlink(upload_path)
        except OSError:
            pass

    return file_url


def _build_trace_id(cfg):
    """生成 x-hag-trace-id：管道形态无 uid，用随机串；旧沙箱形态沿用基于 uid 的稳定串。"""
    uid = cfg.personal_uid
    if uid:
        return f"{hashlib.sha256(uid.encode('utf-8')).hexdigest()[:32]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return uuid.uuid4().hex


def _failure(code, message, retryable):
    """构造供 main 和调用 Agent 判定的结构化失败结果。"""
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        }
    }


def image_understanding(image_urls, text, cfg):
    """
    执行图像理解

    Args:
        image_urls: 图片 URL 列表（公网地址）
        text: 提示文本
        cfg: Config 配置

    Returns:
        dict: {"caption": "图像描述文本"} 或 None
    """
    response = None
    last_caption = ""
    try:
        api_path = "/celia-claw/v1/sse-api/skill/execute"

        headers = {
            'Accept': 'text/event-stream',
            'x-hag-trace-id': _build_trace_id(cfg),
            'x-skill-id': 'xiaoyi_image_comprehension',
            'x-prd-pkg-name': 'com.huawei.hag',
            # 业务鉴权由主进程代理注入；旧沙箱形态 auth_headers 在 skill_post 内合并
        }

        # 单图用 imageUrl，多图用 imageUrls 数组
        if len(image_urls) == 1:
            content = {"imageUrl": image_urls[0], "text": text}
        else:
            content = {"imageUrls": image_urls, "text": text}

        payload = {
            "version": "1.0",
            "session": {
                "isNew": True,
                "sessionId": str(uuid.uuid4()),
                "interactionId": 0
            },
            "endpoint": {
                "device": {
                    "sid": uuid.uuid4().hex,
                    "prdVer": "99.0.64.303",
                    "phoneType": "WLZ-AL10",
                    "sysVer": "HarmonyOS_2.0.0",
                    "deviceType": 0,
                    "timezone": "GMT+08:00"
                },
                "locale": "zh-CN",
                "sysLocale": "zh",
                "countryCode": "CN"
            },
            "utterance": {
                "type": "text",
                "original": text
            },
            "actions": [
                {
                    "actionSn": str(uuid.uuid4()),
                    "actionExecutorTask": {
                        "agentState": "OnShelf",
                        "actionName": "imageComprehensionStream",
                        "content": content
                    }
                }
            ]
        }

        # 经主进程管道代理；旧沙箱形态 requests 直连
        response = cfg.skill_post(api_path, payload, headers=headers, stream=True)

        if response.status_code != 200:
            print(f'❌ 请求失败: HTTP {response.status_code}')
            print(f'🔍 响应: {response.text[:500]}')
            return _failure(
                "http_error",
                f"图像理解服务返回 HTTP {response.status_code}",
                response.status_code >= 500,
            )

        # 接收 SSE 流式数据
        print('📡 SSE 流已建立')

        # iter_lines 已按 \n 拆行并去掉 \r；直接处理每条 SSE 行
        for line in response.iter_lines(decode_unicode=True):
            if line is None:
                continue

            # 只处理 "data:" 开头的 SSE 事件行（忽略注释/事件名/空行）
            if not line.startswith("data:"):
                continue

            data_content = line[5:].strip()
            if not data_content:
                continue
            if data_content == "[DONE]":
                break

            try:
                data_json = json.loads(data_content)
                terminal_event = str(
                    data_json.get('event') or data_json.get('type') or ''
                ).lower() in {'done', 'finish', 'finished', 'complete', 'completed'}

                # 检查顶层错误响应（如 backendError）
                top_code = data_json.get('code')
                if top_code and str(top_code) != '200':
                    top_desc = data_json.get('desc', '未知错误')
                    print(f'❌ 服务端返回错误: [{top_code}] {top_desc}')
                    return _failure("service_error", f"[{top_code}] {top_desc}", False)

                if 'abilityInfos' in data_json:
                    for info in data_json['abilityInfos']:
                        result = info.get('actionExecutorResult', {})
                        # 检查 abilityInfos 内的错误
                        error_code = result.get('errorCode') or result.get('code')
                        if error_code and str(error_code) != '0':
                            error_desc = result.get('desc', '未知错误')
                            print(f'❌ 服务端返回错误: [{error_code}] {error_desc}')
                            return _failure(
                                "service_error",
                                f"[{error_code}] {error_desc}",
                                False,
                            )
                        stream_info = result.get('reply', {}).get('streamInfo', {})
                        stream_content = stream_info.get('streamContent', '')
                        if stream_content:
                            last_caption = stream_content
                        terminal_event = terminal_event or bool(
                            stream_info.get('isFinal') or stream_info.get('finished')
                        )
                if terminal_event:
                    break
            except json.JSONDecodeError:
                pass

        if last_caption:
            return {"caption": last_caption}
        return _failure("empty_response", "图像理解服务未返回有效内容", True)

    except PipeHttpTimeout as e:
        print(f'❌ 请求超时: {e}')
        return _failure("request_timeout", str(e), True)
    except requests.exceptions.Timeout:
        print('❌ 请求超时')
        return _failure("request_timeout", "等待图像理解服务响应超时", True)
    except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError, PipeHttpError):
        # 连接提前关闭，但可能已收到部分数据
        if last_caption:
            print(f'⚠️ 流中断，已收到 {len(last_caption)} 字')
            return {"caption": last_caption}
        return _failure("connection_error", "图像理解连接中断", True)
    except Exception as e:
        print(f'❌ 请求异常: {e}')
        return _failure("unexpected_error", str(e), False)
    finally:
        # 管道形态需显式关闭（fd 回收）；requests.Response.close() 同样无害
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description='小艺图像理解 - 支持本地图片和公网 URL'
    )
    parser.add_argument(
        '--image', '-i',
        nargs='+',
        action='append',
        required=True,
        metavar='PATH',
        help='图片路径（本地路径或 http/https URL），支持多张。'
             '可用空格分隔: --image a.jpg b.jpg，'
             '也可多次指定: --image a.jpg --image b.jpg'
    )
    parser.add_argument(
        '--prompt', '-p',
        required=True,
        metavar='TEXT',
        help='提示词（必填）'
    )
    args = parser.parse_args()
    text = args.prompt
    # action='append' + nargs='+' 产生嵌套列表 [[img1, img2], [img3]]，需展平
    image_paths = [p for group in args.image for p in group]

    if len(image_paths) > 10:
        print('❌ 最多支持 10 张图片')
        print(json.dumps(_failure("too_many_images", "最多支持 10 张图片", False), ensure_ascii=False))
        return 2

    cfg = Config.load()
    # 旧沙箱形态必须提供 uid/api_key；桌面管道形态由主进程注入，无需业务凭证
    if not cfg.pipe_mode and (not cfg.personal_uid or not cfg.personal_api_key):
        print('❌ 旧沙箱形态缺少 PERSONAL_API_KEY / PERSONAL_UID 配置（.xiaoyienv）')
        print(json.dumps(_failure("missing_config", "缺少旧沙箱鉴权配置", False), ensure_ascii=False))
        return 2

    # 解析所有图片 URL（本地文件自动上传）
    image_urls = []
    for img_path in image_paths:
        url = _resolve_image_url(img_path, cfg)
        if not url:
            print(f'❌ 失败: {img_path}')
            failure = _failure("upload_failed", f"图片上传失败: {img_path}", True)
            failure["images"] = image_paths
            print(json.dumps(failure, ensure_ascii=False))
            return 2
        image_urls.append(url)

    # 一次请求处理所有图片
    result = image_understanding(image_urls, text, cfg)
    if result and "caption" in result:
        result["images"] = image_paths
        print(json.dumps(result, ensure_ascii=False))
        return 0
    else:
        failure = result or _failure("empty_response", "图像理解服务未返回结果", True)
        failure["images"] = image_paths
        print(json.dumps(failure, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
