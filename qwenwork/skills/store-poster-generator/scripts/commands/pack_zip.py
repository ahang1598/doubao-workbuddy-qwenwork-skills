"""
pack-zip 命令

将项目根目录（cli.py 的上上级目录）打包为 zip 文件，排除隐藏文件/目录，
按 skills/MM-DD 文件夹组织格式放在桌面中。
"""

import sys
import zipfile
from datetime import datetime
from pathlib import Path

from commands.skill_exists import extract_skill_name
from utils.envs import IS_IN_DWS

DISABLED = IS_IN_DWS

def _get_zip_name() -> str:
    """从项目根目录的 SKILL.md 中读取 name 字段作为 zip 名称。"""
    skill_file = _get_project_root() / "SKILL.md"
    if not skill_file.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {skill_file}")
    name = extract_skill_name(skill_file)
    if not name:
        raise ValueError(f"Failed to extract 'name' from {skill_file}")
    return name


# ── 打包时需要排除的目录/文件名，集中维护，方便更新 ──
EXCLUDED_NAMES: set[str] = {
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "package-lock.json",
    "reset_to_debug.sh"
}

def _should_exclude(path: Path) -> bool:
    """判断路径是否应被排除：隐藏文件/目录（以 . 开头）或在 EXCLUDED_NAMES 中。"""
    return any(
        part.startswith(".") or part in EXCLUDED_NAMES
        for part in path.parts
    )


def _get_project_root() -> Path:
    """获取项目根目录：当前脚本的上上级目录。"""
    return Path(__file__).resolve().parent.parent.parent


def _get_desktop_dir() -> Path:
    """获取用户桌面路径。"""
    return Path.home() / "Desktop"


def pack_zip(single_file: str | None = None) -> tuple[Path, int]:
    """将项目根目录（或单个文件）打包为 zip，返回 (zip路径, 文件数)。"""
    project_root = _get_project_root()
    desktop = _get_desktop_dir()
    date_folder = datetime.now().strftime("%m-%d")

    output_dir = desktop / "skills" / date_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_name = _get_zip_name()
    zip_path = output_dir / f"{zip_name}.zip"

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if single_file:
            target = Path(single_file)
            if not target.is_absolute():
                target = project_root / target
            target = target.resolve()
            if not target.is_file():
                raise FileNotFoundError(f"File not found: {target}")
            try:
                arcname = str(target.relative_to(project_root))
            except ValueError:
                arcname = target.name
            zf.write(target, arcname=arcname)
            file_count = 1
        else:
            for file_path in sorted(project_root.rglob("*")):
                if not file_path.is_file():
                    continue

                relative = file_path.relative_to(project_root)
                if _should_exclude(relative):
                    continue

                zf.write(file_path, arcname=str(relative))
                file_count += 1

    return zip_path, file_count


def register(subparsers) -> None:
    """Register the pack-zip subcommand."""
    parser = subparsers.add_parser(
        "pack-zip",
        help="Pack the project into a zip file on the Desktop under skills/MM-DD/",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Only pack a single file (path relative to project root or absolute)",
    )
    parser.set_defaults(handler=run)

def run(args) -> None:
    """Execute the pack-zip command."""
    try:
        zip_path, file_count = pack_zip(single_file=args.file)
        print(f"Packed {file_count} files into {zip_path}")
        sys.exit(0)
    except Exception as error:
        print(f"Failed to pack zip: {error}", file=sys.stderr)
        sys.exit(1)
