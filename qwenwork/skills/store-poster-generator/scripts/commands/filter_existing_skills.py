"""
filter-existing-skills 命令

接收多个 skillname，返回其中已安装的 skillname 列表。
"""

import sys

from commands.skill_exists import check_skill_exists


def register(subparsers) -> None:
    """Register the filter-existing-skills subcommand."""
    parser = subparsers.add_parser(
        "filter-existing-skills",
        help="从多个技能名称中筛选出已安装的技能",
    )
    parser.add_argument(
        "--skillnames",
        required=True,
        nargs="+",
        help="一个或多个技能名称，用空格分隔",
    )
    parser.set_defaults(handler=run)


def run(args) -> None:
    """Execute the filter-existing-skills command."""
    existing_skills = []

    for skillname in args.skillnames:
        skill_path = check_skill_exists(skillname)
        if skill_path:
            existing_skills.append(skillname)

    if existing_skills:
        print(" ".join(existing_skills))
        sys.exit(0)
    else:
        print("No matching skills found", file=sys.stderr)
        sys.exit(1)
