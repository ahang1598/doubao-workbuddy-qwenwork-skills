"""
skill-exists 命令
"""

import os
import sys
import re
from pathlib import Path


def extract_skill_name(skill_file_path: Path) -> str | None:
    """Extract the 'name' field from the YAML front matter of a SKILL.md file."""
    try:
        content = skill_file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    front_matter_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not front_matter_match:
        return None

    for line in front_matter_match.group(1).splitlines():
        name_match = re.match(r"^name:\s*(.+)$", line)
        if name_match:
            return name_match.group(1).strip()

    return None


def _find_skill_in_directory(skills_dir: Path, skillname: str) -> Path | None:
    """Search for a skill by name in the given .skills directory.

    Returns the skill directory path if found, None otherwise.
    """
    if not skills_dir.is_dir():
        return None

    for skill_file in skills_dir.glob("*/SKILL.md"):
        if not skill_file.is_file():
            continue

        skill_name = extract_skill_name(skill_file)
        if skill_name == skillname:
            return skill_file.parent

    return None

def get_local_skills_dir() -> Path:
    """获取当前脚本 ../../skills 目录路径。"""
    current_script_dir = Path(__file__).resolve().parent
    return current_script_dir.parent.parent / "skills"

def get_agent_skills_dir() -> Path | None:
    """获取 AGENT_WORK_ROOT/.skills 目录路径。"""
    agent_work_root = os.environ.get("AGENT_WORK_ROOT")
    if not agent_work_root:
        return None
    skills_dir = Path(agent_work_root) / ".skills"
    if skills_dir.is_dir():
        return skills_dir
    return None

def check_skill_exists(skillname: str) -> Path | None:
    """Check if a skill with the given name is installed.

    Returns the skill directory path if found, None otherwise.

    Search order:
    2. AGENT_WORK_ROOT/.skills (from environment variable)
    """
    agent_skills_dir = get_agent_skills_dir()
    if agent_skills_dir:
        found = _find_skill_in_directory(agent_skills_dir, skillname)
        if found:
            return found

    return None


def register(subparsers) -> None:
    """Register the skill-exists subcommand."""
    parser = subparsers.add_parser("skill-exists", help="Check if a skill with the specified name exists")
    parser.add_argument("--skillname", required=True, help="The name of the skill to look for")
    parser.set_defaults(handler=run)


def run(args) -> None:
    """Execute the skill-exists command."""
    skill_path = check_skill_exists(args.skillname)
    if skill_path:
        print(f"Skill '{args.skillname}' exists at {skill_path}")
        sys.exit(0)
    else:
        print(f"Skill '{args.skillname}' does not exist")
        sys.exit(1)
