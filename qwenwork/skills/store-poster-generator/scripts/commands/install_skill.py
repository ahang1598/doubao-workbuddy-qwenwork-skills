"""
install-skill 命令

通过调用 dws skill get 安装指定 ID 的技能。
"""

import subprocess
import sys
import time


def install_skill_by_id(skill_id: str) -> bool:
    """调用 dws skill get 安装技能，成功返回 True，失败返回 False。"""
    command = ["dws", "skill", "get", "--skill-id", skill_id]

    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout, end="")

        # 等待 3s
        time.sleep(3)

        return True
    except FileNotFoundError:
        print("Error: 'dws' command not found, please ensure it is installed and in PATH", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as error:
        print(f"Error: dws skill get failed with exit code {error.returncode}", file=sys.stderr)
        if error.stderr:
            print(error.stderr, end="", file=sys.stderr)
        return False


def register(subparsers) -> None:
    """Register the install-skill subcommand."""
    parser = subparsers.add_parser("install-skill", help="安装指定 ID 的技能")
    parser.add_argument("--skill-id", required=True, help="要安装的技能 ID")
    parser.set_defaults(handler=run)


def run(args) -> None:
    """Execute the install-skill command."""
    if install_skill_by_id(args.skill_id):
        sys.exit(0)
    else:
        sys.exit(1)
