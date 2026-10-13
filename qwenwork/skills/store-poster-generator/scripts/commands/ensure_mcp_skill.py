"""
ensure-mcp-skill 命令

确保当前技能目录下的 skills/{skillname}/ 中存在 mcp-config.json。

流程：
1. 检查 mcp-config.json 是否已存在，存在则直接成功。
2. 不存在时，通过 `dws mcp url get <skillname>` 获取 MCP 配置，
   将返回结果中的 result.mcpJSON 写入目标文件。
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def _get_local_skill_mcp_config_path(skillname: str) -> Path:
    """获取 AGENT_WORK_ROOT/workspace/.runtime-config/{skillname}/mcp-config.json 的路径。"""
    agent_work_root = os.environ.get("AGENT_WORK_ROOT")
    if not agent_work_root:
        raise EnvironmentError("AGENT_WORK_ROOT environment variable is not set")
    return Path(agent_work_root) / "workspace" / ".runtime-config" / skillname / "mcp-config.json"


def _fetch_mcp_config_via_dws(skillname: str, skillid: str) -> bool:
    """通过 dws mcp url get 获取 MCP 配置并写入目标文件。

    Returns True if succeeded, False otherwise.
    """
    try:
        result = subprocess.run(
            ["dws", "mcp", "url", "get", skillid],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        print("Error: 'dws' command not found", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("Error: 'dws mcp url get' timed out", file=sys.stderr)
        return False

    if result.returncode != 0:
        print(
            f"Error: 'dws mcp url get {skillname}' failed (exit {result.returncode}): "
            f"{result.stderr.strip()}",
            file=sys.stderr,
        )
        return False

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"Error: Failed to parse dws output as JSON: {exc}", file=sys.stderr)
        return False

    if not response.get("success"):
        print(f"Error: dws returned success=false: {result.stdout.strip()}", file=sys.stderr)
        return False

    mcp_json_str = json.dumps(json.loads(response.get("result", {}).get("mcpJSON", "{}")).get("mcpServers", {}))
    if not mcp_json_str:
        print("Error: result.mcpJSON.mcpServers is empty in dws response", file=sys.stderr)
        return False

    destination = _get_local_skill_mcp_config_path(skillname)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(mcp_json_str, encoding="utf-8")
    print(f"Written mcp-config.json to {destination}")
    return True


def ensure_mcp_skill(skillname: str, skillid: str) -> bool:
    """确保 mcp-config.json 存在。

    Returns True on success, False on failure.
    """
    # 1. 检查本地是否已存在 mcp-config.json
    local_mcp_config = _get_local_skill_mcp_config_path(skillname)
    if local_mcp_config.is_file():
        return True

    # 2. 通过 dws mcp url get 获取配置并写入
    if _fetch_mcp_config_via_dws(skillname, skillid):
        return True

    print(
        f"Error: Failed to obtain mcp-config.json for skill '{skillname}'",
        file=sys.stderr,
    )
    return False


def register(subparsers) -> None:
    """Register the ensure-mcp-skill subcommand."""
    parser = subparsers.add_parser(
        "ensure-mcp-skill",
        help="确保指定技能的 mcp-config.json 存在于本地 skills 目录中",
    )
    parser.add_argument("--skillname", required=True, help="技能名称")
    parser.set_defaults(handler=run)


def run(args) -> None:
    """Execute the ensure-mcp-skill command."""
    if ensure_mcp_skill(args.skillname):
        sys.exit(0)
    else:
        sys.exit(1)
