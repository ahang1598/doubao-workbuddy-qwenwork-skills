#!/usr/bin/env python3
"""
Celia find skills search - Helper Script

This is a helper script for batch generation or CLI usage.
The main skill workflow is defined in SKILL.md and executed by Claude.

Usage:
    python search.py "query"

桌面形态（默认）：SERVICE_URL=np://claw-skill —— 请求经主进程 skill API 代理
（Windows 命名管道）转发，businessCredential 鉴权由主进程注入，本脚本零业务
凭证，仅需 CLAW_SKILL_TOKEN 本机防借用令牌（主进程经 AgentServer 环境注入）。

旧沙箱形态（兼容）：SERVICE_URL=http(s)://... 时直连云端，鉴权头
（x-uid/x-api-key）从 .xiaoyienv 读取（ACP2SERVICE_ENV 可指定路径）。
"""
import os
import uuid
import json
import argparse

from config import Config


# 已安装技能目录：可用 SKILLS_DIR 环境变量覆盖；缺省 ~/.openclaw/workspace/skills
# （旧沙箱保留原默认；桌面形态可经 SKILLS_DIR 注入小艺 Work 的实际技能目录）
DEFAULT_SKILLS_DIR = os.path.expanduser("~/.openclaw/workspace/skills")


def get_installed_skills():
    """
    扫描已安装技能目录（SKILLS_DIR 可覆盖，缺省 ~/.openclaw/workspace/skills），
    返回文件夹名称列表。
    """
    skills_dir = os.getenv("SKILLS_DIR", "").strip() or DEFAULT_SKILLS_DIR
    installed_skills = []

    try:
        # 检查目录是否存在
        if os.path.exists(skills_dir) and os.path.isdir(skills_dir):
            # 遍历目录下的所有条目
            for entry in os.listdir(skills_dir):
                entry_path = os.path.join(skills_dir, entry)
                # 只添加文件夹
                if os.path.isdir(entry_path):
                    installed_skills.append(entry)
        else:
            print(f"提示: 技能目录 {skills_dir} 不存在或不是目录")
    except Exception as e:
        print(f"读取技能目录时发生错误: {e}")

    return installed_skills


def format_skill_data(raw_skills, installed_skills):
    """
    格式化技能数据，添加安装状态标识，调整字段名称
    """
    formatted_skills = []

    for skill in raw_skills:
        # 检查是否已安装
        status = "已安装" if skill.get("skillId") in installed_skills else "未安装"

        # 构建格式化后的技能字典
        formatted_skill = {
            "skillId": skill.get("skillId", ""),
            "skillName": skill.get("skillName", ""),
            "skillDesc": skill.get("skillDesc", ""),
            "downloadPath": skill.get("packUrl", ""),  # 将packUrl重命名为downloadPath
            "status": status
        }

        formatted_skills.append(formatted_skill)

    return formatted_skills


def search_skills(query):
    # 统一配置：桌面形态默认走命名管道（主进程注入鉴权）；旧沙箱形态直连云端
    cfg = Config.load()

    if not cfg.pipe_mode:
        # 旧沙箱形态校验
        missing = [k for k, v in (("PERSONAL_UID", cfg.personal_uid), ("PERSONAL_API_KEY", cfg.personal_api_key), ("SERVICE_URL", cfg.service_url)) if not v]
        if missing:
            print(f"Missing environment variables: {', '.join(missing)}")
            return None

    # Configuration
    trace_id = str(uuid.uuid4())
    path = '/celia-claw/v1/rest-api/skill/execute'

    # Build request（业务鉴权在管道形态由主进程注入；x-hag-trace-id 每请求随机，不硬编码）
    headers = {
        'Content-Type': 'application/json',
        'x-skill-id': 'celia_find_skills',
        'x-hag-trace-id': trace_id,
        'x-request-from': 'openclaw',
    }
    headers.update(cfg.auth_headers())  # 管道形态返回空

    payload = {
        "query": query,
        "customFilterItem":
        {
            "filterItem": "CLAW_TYPE",
            "filterValue": "xiaoyiWork"
        }
    }

    try:
        # 用 with 包裹，确保管道响应（命名管道 fd）在读取后关闭，避免 Windows 下 fd 泄漏
        with cfg.skill_post(path, payload, headers=headers) as response:
            # 尝试解析JSON，增加异常捕获
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                print(f"\nJSON解析失败: {e}")
                print(f"无法解析的原始内容: {response.text}")
                return None

            # 获取已安装的技能列表
            installed_skills = get_installed_skills()

            # 格式化技能数据
            if response_data.get("errorCode") == "0" and "content" in response_data and "skills" in response_data["content"]:
                formatted_data = format_skill_data(response_data["content"]["skills"], installed_skills)

                # 打印格式化后的JSON数据
                print("skill列表:")
                print(json.dumps(formatted_data, indent=2, ensure_ascii=False))
                return formatted_data
            else:
                print("\n响应数据格式异常，未找到skill列表")
                print(f"原始响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                return None

    except Exception as e:
        print(f"请求异常: {e}")
        return None


def parse_args():
    """解析命令行参数（移除skillId参数）"""
    parser = argparse.ArgumentParser(description="查找技能")
    parser.add_argument("--query", required=True, help="查找技能的关键词")
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    search_skills(query=args.query)


if __name__ == '__main__':
    main()
