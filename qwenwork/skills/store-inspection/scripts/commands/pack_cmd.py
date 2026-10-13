"""pack 命令 —— 生成合规 SKILL 压缩包。

将 SKILL 根目录打包为 zip 文件，自动排除非发布内容：
- .git/ 及所有 git 相关文件
- __pycache__/ 及 *.pyc 文件
- tests/ 目录
- dist/ 目录
- venv / .venv 目录
- .DS_Store 等系统文件
- pack.py（旧版打包脚本）
- pyproject.toml / uv.lock（开发依赖管理文件）

打包前自动从 pyproject.toml 生成 requirements.txt（需要 uv）。

用法::

    uv run python scripts/cli.py pack
    uv run python scripts/cli.py pack --output dist/release.zip
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command

if TYPE_CHECKING:  # pragma: no cover
    from scripts.app import AppContext

# SKILL 根目录（scripts/ 的上一级）
_SKILL_ROOT = Path(__file__).resolve().parent.parent.parent

# 技能发布名称（与 pyproject.toml 中的 project.name 一致，用于压缩包命名）
_SKILL_NAME = "store-inspection"

# ------------------------------------------------------------------
# 排除规则
# ------------------------------------------------------------------

_EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "tests",
    ".store-inspection-skills-group",
    ".store-inspection",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

_EXCLUDED_DIR_SUFFIXES = (".egg-info",)

_EXCLUDED_FILES = {
    ".gitignore",
    ".gitattributes",
    ".gitmodules",
    ".DS_Store",
    "pack.py",
    "pyproject.toml",
    "uv.lock",
    "sync_to_skill.py",
}

_EXCLUDED_PREFIXES = ("~$",)
_EXCLUDED_SUFFIXES = (".pyc", ".pyo")


def _should_exclude(relative_path: Path) -> bool:
    """判断某个相对路径是否应被排除。"""
    for part in relative_path.parts:
        if part in _EXCLUDED_DIRS:
            return True
        if part.startswith(".git"):
            return True
        if any(part.endswith(suffix) for suffix in _EXCLUDED_DIR_SUFFIXES):
            return True

    filename = relative_path.name

    if filename in _EXCLUDED_FILES:
        return True
    if any(filename.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
        return True
    if any(filename.endswith(suffix) for suffix in _EXCLUDED_SUFFIXES):
        return True

    return False


# ------------------------------------------------------------------
# requirements.txt 生成
# ------------------------------------------------------------------

def _generate_requirements(skill_root: Path) -> bool:
    """从 pyproject.toml 生成 requirements.txt。

    Returns:
        True 表示生成成功或已存在，False 表示生成失败。
    """
    pyproject_path = skill_root / "pyproject.toml"
    requirements_path = skill_root / "requirements.txt"

    if not pyproject_path.exists():
        if requirements_path.exists():
            return True
        print("  ⚠️ 未找到 pyproject.toml 且 requirements.txt 不存在，跳过依赖生成")
        return False

    uv_path = shutil.which("uv")
    if not uv_path:
        if requirements_path.exists():
            print("  ⚠️ 未找到 uv，使用已有 requirements.txt")
            return True
        print("  ⚠️ 未找到 uv 且 requirements.txt 不存在，跳过依赖生成")
        return False

    print("📋 从 pyproject.toml 生成 requirements.txt ...")
    try:
        subprocess.run(
            [uv_path, "pip", "compile", str(pyproject_path), "-o", str(requirements_path)],
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(skill_root),
        )
        print(f"  ✅ 已生成 requirements.txt")
        return True
    except subprocess.CalledProcessError as error:
        stderr_message = (error.stderr or "").strip()
        print(f"  ❌ 生成 requirements.txt 失败: {stderr_message}")
        return requirements_path.exists()


# ------------------------------------------------------------------
# 打包核心逻辑
# ------------------------------------------------------------------

def _build_archive(skill_root: Path, output_path: Path) -> tuple:
    """构建 zip 压缩包，返回 (已打包文件数, 已排除文件数)。"""
    archive_root_name = _SKILL_NAME
    packed_count = 0
    excluded_count = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for dirpath, dirnames, filenames in os.walk(skill_root):
            current_dir = Path(dirpath)
            relative_dir = current_dir.relative_to(skill_root)

            # 就地修改 dirnames 以跳过排除目录
            dirnames[:] = [
                dirname for dirname in dirnames
                if not _should_exclude(relative_dir / dirname)
            ]

            for filename in filenames:
                relative_file = relative_dir / filename

                if _should_exclude(relative_file):
                    excluded_count += 1
                    continue

                full_path = current_dir / filename
                arcname = str(Path(archive_root_name) / relative_file)
                archive.write(full_path, arcname)
                packed_count += 1

    return packed_count, excluded_count


# ------------------------------------------------------------------
# 命令注册
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# 版本号自动递增 + git tag
# ------------------------------------------------------------------

_SKILL_MD_PATH = _SKILL_ROOT / "SKILL.md"


def _read_current_version() -> str:
    """从 SKILL.md front matter 中读取 version 字段，默认 0.0.0。"""
    if not _SKILL_MD_PATH.exists():
        return "0.0.0"
    content = _SKILL_MD_PATH.read_text(encoding="utf-8")
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("version:"):
            return stripped.split(":", 1)[1].strip().lstrip("v")
    return "0.0.0"


def _bump_patch(version: str) -> str:
    """递增 patch 版本号：0.0.1 → 0.0.2。"""
    parts = version.split(".")
    if len(parts) != 3:
        parts = ["0", "0", "0"]
    parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


def _update_skill_version(new_version: str) -> None:
    """将 SKILL.md 中的 version 字段更新为新版本号。"""
    content = _SKILL_MD_PATH.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("version:"):
            lines[i] = f"version: {new_version}\n"
            updated = True
            break
    if not updated:
        # 在 front matter 第二行插入 version
        for i, line in enumerate(lines):
            if i > 0 and line.strip().startswith("description:"):
                lines.insert(i, f"version: {new_version}\n")
                break
    _SKILL_MD_PATH.write_text("".join(lines), encoding="utf-8")


def _git_commit_and_tag(new_version: str, skill_root: Path) -> bool:
    """提交 version 变更并打 tag。返回是否成功。"""
    tag_name = f"v{new_version}"
    try:
        subprocess.run(
            ["git", "add", "SKILL.md"],
            check=True, capture_output=True, cwd=str(skill_root),
        )
        subprocess.run(
            ["git", "commit", "-m", f"chore(release): bump version to {tag_name}"],
            check=True, capture_output=True, cwd=str(skill_root),
        )
        subprocess.run(
            ["git", "tag", tag_name],
            check=True, capture_output=True, cwd=str(skill_root),
        )
        print(f"🏷️  版本: {tag_name}（已 commit + tag）")
        return True
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode(errors="replace").strip()
        print(f"  ⚠️ git commit/tag 失败: {stderr}")
        return False


# ------------------------------------------------------------------
# 命令入口
# ------------------------------------------------------------------

def _handle_pack(args: argparse.Namespace, ctx: "AppContext") -> int:
    """执行 pack 命令。

    流程：递增版本号 → 更新 SKILL.md → git commit + tag → 打包 zip。
    使用 --pack-only 可跳过版本递增，仅打包。
    """
    skill_root = _SKILL_ROOT

    # ── 版本号递增（除非 --pack-only）──
    if getattr(args, "pack_only", False):
        new_version = _read_current_version()
        print(f"📦 仅打包模式（跳过版本递增），当前版本: v{new_version}")
    else:
        current_version = _read_current_version()
        new_version = _bump_patch(current_version)
        _update_skill_version(new_version)
        print(f"🔖 版本递增: v{current_version} → v{new_version}")
        _git_commit_and_tag(new_version, skill_root)
    print()

    # ── 确定输出路径 ──
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = skill_root / "dist" / f"{_SKILL_NAME}_{timestamp}.zip"

    if output_path.exists():
        output_path.unlink()

    print(f"📦 正在打包 SKILL: {_SKILL_NAME}")
    print(f"   源目录: {skill_root}")
    print(f"   输出到: {output_path}")
    print()

    # 打包前生成 requirements.txt
    _generate_requirements(skill_root)
    print()

    packed_count, excluded_count = _build_archive(skill_root, output_path)

    if packed_count == 0:
        print("❌ 没有找到任何需要打包的文件")
        return 1

    file_size_kb = output_path.stat().st_size / 1024

    print(f"✅ 打包完成")
    print(f"   已打包: {packed_count} 个文件")
    print(f"   已排除: {excluded_count} 个文件")
    print(f"   包大小: {file_size_kb:.1f} KB")
    print(f"   输出路径: {output_path}")
    print(f"   版本: v{new_version}")

    # 生成固定名称的副本
    fixed_name_path = output_path.parent / f"{_SKILL_NAME}.zip"
    if fixed_name_path != output_path:
        shutil.copy2(output_path, fixed_name_path)
        print(f"   固定名称副本: {fixed_name_path}")

    return 0


@register_command
class PackCommand(BaseCommand):
    """打包发布命令。"""

    name = "pack"
    help = "生成合规 SKILL 压缩包（排除 .git、tests、__pycache__ 等非发布内容）"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--output", "-o",
            help="输出 zip 文件路径（默认：dist/<skill-name>_<timestamp>.zip）",
            default=None,
        )
        parser.add_argument(
            "--pack-only",
            action="store_true",
            default=False,
            help="仅打包，不递增版本号、不 git commit/tag",
        )
        parser.set_defaults(func=_handle_pack)
