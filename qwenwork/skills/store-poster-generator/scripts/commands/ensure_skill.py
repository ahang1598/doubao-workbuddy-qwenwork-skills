"""
ensure-skill 命令

确保指定技能已安装：已安装则直接成功，未安装则自动安装。
安装完成后确保技能存在于本地 ../../skills 目录中。
"""

import shutil
import sys

from commands.skill_exists import (
    check_skill_exists,
    get_local_skills_dir,
    get_agent_skills_dir,
    _find_skill_in_directory,
)
from commands.install_skill import install_skill_by_id

def _ensure_skill_in_local(skillname: str) -> None:
    """确保技能存在于 ../../skills 中，不存在则从 AGENT_WORK_ROOT/.skills 复制。"""
    local_skills_dir = get_local_skills_dir()
    if _find_skill_in_directory(local_skills_dir, skillname):
        return

    agent_skills_dir = get_agent_skills_dir()
    if not agent_skills_dir:
        print("Warning: AGENT_WORK_ROOT not set, cannot copy skill to local", file=sys.stderr)
        return

    agent_skill_path = _find_skill_in_directory(agent_skills_dir, skillname)
    if not agent_skill_path:
        return

    local_skills_dir.mkdir(parents=True, exist_ok=True)
    destination = local_skills_dir / skillname

    if destination.exists():
        shutil.rmtree(destination)

    shutil.copytree(agent_skill_path, destination)
    print(f"Copied skill '{skillname}' to {destination}")

def register(subparsers) -> None:
    """Register the ensure-skill subcommand."""
    parser = subparsers.add_parser("ensure-skill", help="确保指定技能已安装，未安装则自动安装")
    parser.add_argument("--skillname", required=True, help="技能名称（用于检查是否已安装）")
    parser.add_argument("--skill-id", required=True, help="技能 ID（用于安装）")
    parser.set_defaults(handler=run)

def run(args) -> None:
    """Execute the ensure-skill command."""
    # 1. 判断技能是否已存在（../../skills 或 AGENT_WORK_ROOT/.skills）
    skill_path = check_skill_exists(args.skillname)
    if skill_path:
        print(f"Skill '{args.skillname}' is already installed at {skill_path}")
    else:
        # 2. 不存在则安装
        print(f"installing (skill-id: {args.skill_id})...")
        if not install_skill_by_id(args.skill_id):
            print(f"Error: Failed to install skill '{args.skillname}'", file=sys.stderr)
            sys.exit(1)
        print(f"Skill '{args.skillname}' installed successfully")

    # 3. 确保技能存在于 ../../skills 中，不存在则从 AGENT_WORK_ROOT/.skills 复制
    _ensure_skill_in_local(args.skillname)
    sys.exit(0)
