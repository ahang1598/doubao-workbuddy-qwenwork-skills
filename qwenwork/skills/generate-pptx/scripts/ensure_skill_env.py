#!/usr/bin/env python3
"""
Prepare a Python environment for the generate-pptx skill.
"""

import argparse
import json
import os
import subprocess
import sys
import venv
from dataclasses import asdict, dataclass
from pathlib import Path

REQUIRED_PACKAGE = "python-pptx>=1.0.2,<1.1.0"
IMPORT_CHECK = "import pptx"


@dataclass
class SkillEnv:
    python: str
    venv_dir: str
    reused_active_venv: bool
    created_venv: bool
    installed_dependency: bool


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_active_virtualenv() -> bool:
    return bool(os.environ.get("VIRTUAL_ENV")) or sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _has_python_pptx(python_executable: Path) -> bool:
    result = subprocess.run(
        [str(python_executable), "-c", IMPORT_CHECK],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _install_dependency(python_executable: Path) -> None:
    subprocess.run([str(python_executable), "-m", "pip", "install", REQUIRED_PACKAGE], check=True)


def ensure_skill_env() -> SkillEnv:
    created_venv = False
    reused_active_venv = _is_active_virtualenv()

    if reused_active_venv:
        venv_dir = Path(os.environ.get("VIRTUAL_ENV", sys.prefix)).resolve()
        python_executable = _venv_python(venv_dir)
        if not python_executable.exists():
            python_executable = Path(sys.executable).resolve()
    else:
        venv_dir = _skill_root() / ".venv"
        python_executable = _venv_python(venv_dir)
        if not python_executable.exists():
            venv.EnvBuilder(with_pip=True).create(venv_dir)
            created_venv = True

    installed_dependency = False
    if not _has_python_pptx(python_executable):
        _install_dependency(python_executable)
        installed_dependency = True

    return SkillEnv(
        python=str(python_executable),
        venv_dir=str(venv_dir),
        reused_active_venv=reused_active_venv,
        created_venv=created_venv,
        installed_dependency=installed_dependency,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a Python environment for the generate-pptx skill.",
    )
    parser.add_argument("--json", action="store_true", help="Print environment details as JSON")
    parser.add_argument(
        "--print-python",
        action="store_true",
        help="Print only the selected Python interpreter path",
    )
    args = parser.parse_args()

    skill_env = ensure_skill_env()

    if args.print_python:
        print(skill_env.python)
        return

    if args.json:
        print(json.dumps(asdict(skill_env), ensure_ascii=False))
        return

    print(f"python={skill_env.python}")
    print(f"venv_dir={skill_env.venv_dir}")
    print(f"reused_active_venv={skill_env.reused_active_venv}")
    print(f"created_venv={skill_env.created_venv}")
    print(f"installed_dependency={skill_env.installed_dependency}")


if __name__ == "__main__":
    main()
