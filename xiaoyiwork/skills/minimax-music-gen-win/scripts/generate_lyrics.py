import os
import requests
import urllib3
import argparse
import json
from datetime import datetime
import random
import string
import uuid
from pathlib import Path

urllib3.disable_warnings()

from config import Config
from claw_pipe_http import PipeHttpError
import hashlib
from datetime import datetime


def read_xiaoyienv():
    """
    读取 ~/.openclaw/.xiaoyienv 文件并返回键值对字典。
    """
    file_path = os.path.expanduser("~/.openclaw/.xiaoyienv")
    env_dict = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_dict[key.strip()] = value.strip()

    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"读取文件时发生错误: {e}")

    return env_dict


def _build_trace_id(cfg):
    uid = cfg.personal_uid
    if uid:
        return f"{hashlib.sha256(uid.encode('utf-8')).hexdigest()[:32]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return str(uuid.uuid4())


def generate_lyrics(prompt, mode: str = "write_full_song", lyrics: str = None, cfg=None):
    """
    使用MiniMax API生成歌词

    Args:
        prompt (str): 歌词生成的提示词，例如："Indie folk, melancholic, introspective, longing, solitary walk, coffee shop"
        mode (str): 生成模式，可选值：
            - "write_full_song": 写完整歌曲
            - "edit": 编辑/续写歌词
        lyrics (str, optional): 现有歌词内容，仅在 edit 模式下有效。可用于续写或修改已有歌词。

    Returns:
        dict: API响应结果
    """

    if cfg is None:
        cfg = Config.load()
    trace_id = _build_trace_id(cfg)

    # Build request headers (auth injected by skill_post)
    headers = {
        'x-skill-id': 'minimax_music_gen',
        'x-hag-trace-id': trace_id,
        'x-request-from': 'openclaw',
    }

    # 定义 content 字段，便于后续扩展
    content = {
        "prompt": prompt,
        "mode": mode
    }

    # edit 模式下添加 lyrics 参数
    if mode == "edit":
        if not lyrics:
            raise ValueError("edit 模式下必须提供 lyrics 参数（现有歌词内容）")
        content["lyrics"] = lyrics

    payload = {
        "actions": [
            {
                "actionExecutorTask": {
                    "actionName": "lyricsGeneration",
                    "content": content,
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

    # 发送POST请求 - 使用SSE流式接口
    response = cfg.skill_post('/celia-claw/v1/sse-api/skill/execute', payload, headers=headers, stream=True)
    response.raise_for_status()

    # 解析SSE流式响应
    final_result = None

    for line in response.iter_lines():
        if not line:
            continue

        line_str = line.decode('utf-8')

        # 跳过非数据行 (如 id: lines)
        if line_str.startswith('id:'):
            continue

        # 解析SSE格式: "data: {...}"
        if line_str.startswith('data:'):
            json_str = line_str[5:].strip()  # 去掉 "data:" 前缀

            try:
                result = json.loads(json_str)

                # 获取 abilityInfos
                ability_infos = result.get('abilityInfos', [])
                if not ability_infos:
                    continue

                action_executor_result = ability_infos[0].get('actionExecutorResult', {})

                # 检查响应码 (code为"0"表示成功)
                result_code = action_executor_result.get('code', '')
                if result_code != '0':
                    error_msg = action_executor_result.get('desc', 'Unknown error')
                    print(f"API Error: {error_msg}")
                    continue

                # 获取流信息
                reply = action_executor_result.get('reply', {})
                stream_info = reply.get('streamInfo', {})
                stream_type = stream_info.get('streamType', '')

                # 如果是最终结果，从 content 字段获取歌词数据
                if stream_type == 'final':
                    content = reply.get('content', {})
                    if content and 'lyrics' in content:
                        final_result = content
                        break

            except json.JSONDecodeError:
                # 跳过无法解析的行
                continue

    if final_result is None:
        raise Exception("未能从流式响应中获取有效的歌词数据")

    return final_result


def save_lyrics_to_file(lyrics: str, song_title: str, style_tags: str, prompt: str,
                        output_dir: str = "~/.openclaw/workspace/generated-musics"):
    """
    将生成的歌词保存为JSON格式文件

    Args:
        lyrics (str): 歌词内容
        song_title (str): 歌曲标题
        style_tags (str): 风格标签
        prompt (str): 生成提示词
        output_dir (str): 输出目录

    Returns:
        str: 保存的文件路径
    """
    # 确保输出目录存在
    output_dir = os.path.expanduser(output_dir)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 构建文件名：YYYYMMDD_HHMMSS_SSS_2位随机字符_lyrics.json
    now_time = datetime.now()
    ms = now_time.strftime('%f')[:3]
    base_time = now_time.strftime('%Y%m%d_%H%M%S')
    random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=2))
    timestamp = f"{base_time}_{ms}_{random_chars}"

    lyrics_filename = f"{timestamp}_lyrics.json"
    file_path = os.path.join(output_dir, lyrics_filename)

    # 构建JSON数据结构
    lyrics_data = {
        "song_title": song_title,
        "style_tags": style_tags,
        "prompt": prompt,
        "lyrics": lyrics,
        "generated_at": now_time.strftime('%Y-%m-%d %H:%M:%S')
    }

    # 写入JSON文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(lyrics_data, f, ensure_ascii=False, indent=2)

    return file_path


def main():
    """
    主函数：从命令行获取prompt，生成歌词并输出
    """
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='使用MiniMax API生成歌词')
    parser.add_argument('--prompt', type=str, help='歌词生成提示词')
    parser.add_argument('--mode', type=str, default='write_full_song',
                        choices=['write_full_song', 'edit'],
                        help='生成模式: write_full_song(写完整歌曲) 或 edit(编辑/续写歌词)')
    parser.add_argument('--lyrics', type=str, default=None,
                        help='现有歌词内容，仅在 edit 模式下有效。可用于续写或修改已有歌词。')
    parser.add_argument('--output-path', type=str, default=".",
                        help='歌词保存目录')

    # 解析命令行参数
    args = parser.parse_args()
    prompt = args.prompt
    mode = args.mode
    lyrics_input = args.lyrics

    # 处理歌词参数 - 支持从文件或直接传入
    lyrics_content = None
    if lyrics_input:
        if os.path.exists(lyrics_input):
            # 检查文件扩展名
            if lyrics_input.endswith('.json'):
                # 读取JSON格式歌词文件
                with open(lyrics_input, 'r', encoding='utf-8') as f:
                    lyrics_data = json.load(f)
                    lyrics_content = lyrics_data.get('lyrics', '')
                    print(f"已从JSON文件读取歌词: {lyrics_input}")
            else:
                # 读取纯文本歌词文件
                with open(lyrics_input, 'r', encoding='utf-8') as f:
                    lyrics_content = f.read()
                    print(f"已从文本文件读取歌词: {lyrics_input}")
        else:
            lyrics_content = lyrics_input
            print(f"使用命令行传入的歌词")

    try:
        # 生成歌词
        cfg = Config.load()
        if not cfg.pipe_mode and (not cfg.personal_uid or not cfg.personal_api_key):
            print("Sandbox mode requires PERSONAL_API_KEY / PERSONAL_UID in .xiaoyienv")
            exit(1)

        result = generate_lyrics(prompt, mode, lyrics_content,
                      cfg=cfg)

        # 检查响应是否成功
        if result.get('base_resp', {}).get('status_code') != 0:
            error_msg = result.get('base_resp', {}).get('status_msg', '未知错误')
            raise Exception(f"生成歌词失败: {error_msg}")

        # 提取并显示歌词相关信息
        try:
            song_title = result['song_title']
            style_tags = result['style_tags']
            lyrics_result = result['lyrics']
        except KeyError as e:
            raise Exception(f"响应数据格式异常，缺少必要字段: {e}")

        print(f"\n歌曲标题: {song_title}")
        print(f"风格标签: {style_tags}")
        print(f"\n歌词内容:\n")
        print(repr(lyrics_result))

        # 保存歌词到文件 - 保存为JSON格式，包含所有字段
        lyrics_file_path = save_lyrics_to_file(
            lyrics_result, song_title, style_tags, prompt, args.output_path
        )
        print(f"\n歌词已保存至: {lyrics_file_path}")

    except Exception as e:
        print(f"生成歌词时发生错误: {e}")
        exit(1)


if __name__ == "__main__":
    main()
