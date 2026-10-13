#!/usr/bin/env python3
"""
Run a Python script inside the prepared skill environment.
"""

import argparse
import subprocess
from pathlib import Path

from ensure_skill_env import ensure_skill_env


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare the generate-pptx skill environment and run a target script inside it.",
    )
    parser.add_argument("script", type=Path, help="Target Python script path")
    parser.add_argument("script_args", nargs=argparse.REMAINDER, help="Arguments for the target script")
    args = parser.parse_args()

    script_path = args.script.resolve()
    if not script_path.exists():
        raise SystemExit(f"target script not found: {script_path}")

    skill_env = ensure_skill_env()
    completed = subprocess.run([skill_env.python, str(script_path), *args.script_args], check=False)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
