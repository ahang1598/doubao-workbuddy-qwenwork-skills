"""
skill-context 命令

获取 skill 相关的各种上下文目录路径。
"""

import json
import os
import platform
import sys
from pathlib import Path

from commands.skill_exists import check_skill_exists


def _get_default_skillname() -> str:
    """从当前脚本的上三级目录名推断 skill 名称。

    目录结构: <skill_root>/scripts/commands/skill_context.py
    """
    return Path(__file__).resolve().parent.parent.parent.name


def _get_agent_work_root() -> Path | None:
    """从环境变量 AGENT_WORK_ROOT 获取用户数据根目录。"""
    agent_work_root = os.environ.get("AGENT_WORK_ROOT")
    if not agent_work_root:
        return None
    return Path(agent_work_root)


def _get_chrome_path(agent_work_root: Path) -> Path | None:
    """获取 Chrome 可执行文件路径。

    在 agent_work_root 的上两级目录的 .bin/ 下递归查找 Google Chrome 可执行文件。
    """
    bin_dir = agent_work_root.resolve().parent.parent / ".bin"
    if not bin_dir.is_dir():
        return None

    system_name = platform.system()

    if system_name == "Darwin":
        candidates = sorted(bin_dir.rglob("Google Chrome"), reverse=True)
    elif system_name == "Linux":
        candidates = sorted(bin_dir.rglob("chrome"), reverse=True)
    else:
        return None

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return candidates[0] if candidates else None


def get_skill_context() -> dict:
    """收集 skill 相关的所有上下文目录信息。

    skillname 自动从当前脚本的上三级目录名推断。
    """
    resolved_skillname = _get_default_skillname()

    context = {"current_skillname": resolved_skillname}

    agent_work_root = _get_agent_work_root()
    if agent_work_root:
        context["agent_work_root"] = str(agent_work_root)
    else:
        context["agent_work_root"] = None

    skill_dir = check_skill_exists(resolved_skillname)
    context["skill_dir"] = str(skill_dir) if skill_dir else None

    if agent_work_root:
        context["skills_dir"] = str(agent_work_root / ".skills")

        mcp_config_path = agent_work_root / ".mcp" / "mcpServerConfig.json"
        context["mcp_config"] = str(mcp_config_path)

        context["workspace_dir"] = str(agent_work_root / "workspace")

        chrome_path = _get_chrome_path(agent_work_root)
        context["chrome_path"] = str(chrome_path) if chrome_path else None
    else:
        context["skills_dir"] = None
        context["mcp_config"] = None
        context["workspace_dir"] = None
        context["chrome_path"] = None

    # output_dir: 优先 QoderWork 会话工作目录环境变量，其次旧运行时兼容值，
    # 再次 PWD（排除 /private/tmp），最后 fallback 到 workspace_dir
    # 位于技能目录下的路径视为无效，直接 fallback
    user_workdir = (
        os.environ.get("QODERWORK_USER_WORKDIR")
        or os.environ.get("QODER_WORKSPACE_DIR")
        or os.environ.get("WUKONG_USER_WORKDIR")  # 旧运行时兼容，可选保留
    )
    skills_dir = context.get("skills_dir")
    if user_workdir and user_workdir != "/private/tmp" and not (skills_dir and user_workdir.startswith(skills_dir)):
        context["output_dir"] = user_workdir
    else:
        context["output_dir"] = context.get("workspace_dir")

    return context


def register(subparsers) -> None:
    """Register the skill-context subcommand."""
    parser = subparsers.add_parser(
        "skill-context",
        help="获取 skill 相关的各种上下文目录路径",
    )
    parser.add_argument(
        "--key",
        choices=[
            "skill_dir",
            "skills_dir",
            "agent_work_root",
            "mcp_config",
            "workspace_dir",
            "chrome_path",
            "output_dir",
        ],
        default=None,
        help="仅输出指定 key 的值；不指定则输出全部",
    )
    parser.set_defaults(handler=run)


def run(args) -> None:
    """Execute the skill-context command."""
    context = get_skill_context()

    if args.key:
        value = context.get(args.key)
        if value is None:
            print(f"❌ {args.key} 未找到或未配置", file=sys.stderr)
            sys.exit(1)
        print(value)
    else:
        print(json.dumps(context, ensure_ascii=False, indent=2))
