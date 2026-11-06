"""Resolve the current user's Skill Python using only the standard library.

The Agent may have started before the shared venv was installed. Its injected
CLAW_PYTHON_EXE is therefore a bootstrap hint, not a dependency-ready interpreter.
This launcher never installs packages or changes the Agent/framework environment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

SCRIPTS_DIR = Path(__file__).resolve().parent
CACHE_PATH = SCRIPTS_DIR / ".python_cmd"
ALLOWED_SCRIPTS = {"session_state.py", "submit_research.py", "wait_for_completion_and_download.py", "check_status.py"}
PROBE = "import requests, urllib3, json, sys; print(json.dumps({'executable': sys.executable, 'prefix': sys.prefix, 'base_prefix': sys.base_prefix}))"


def user_root(env: dict[str, str]) -> Path | None:
    # The desktop sets this per authenticated user; never search other users.
    for key in ("JIUWENSWARM_DATA_DIR", "JIUWENSWARM_HOME"):
        value = env.get(key, "").strip()
        if value and Path(value).name.lower() in {"jiuwenswarm", "xiaoyiwork"}:
            return Path(value).parent
    injected = Path(env.get("CLAW_PYTHON_EXE", ""))
    if injected.parent.name.lower() == "scripts" and injected.parent.parent.name == "py-venv":
        deps = injected.parent.parent.parent
        if deps.name == "skill-deps":
            return deps.parent
    # Compatibility with installed desktop skills whose old Agent lacks the env.
    skill = SCRIPTS_DIR.parent
    parents = list(skill.parents)
    if len(parents) > 4 and [p.name.lower() for p in parents[:3]] == ["skills", "workspace", "agent"]:
        if parents[3].name.lower() in {"jiuwenswarm", "xiaoyiwork"}:
            return parents[4]
    return None


def desktop_mode(env: dict[str, str], root: Path | None) -> bool:
    return root is not None or bool(env.get("CLAW_PYTHON_EXE") or env.get("CLAW_SKILL_TOKEN")) or env.get("JIUWENSWARM_DESKTOP") == "1"


def base_python(root: Path | None, env: dict[str, str], stamp: dict) -> Path | None:
    hints = [env.get("CLAW_PYTHON_EXE", ""), stamp.get("basePython", "")]
    if root is not None:
        hints.append(str(root / "runtime" / "python-win" / "python.exe"))
        if root.parent.name == "users":
            hints.append(str(root.parent.parent / "runtime" / "python-win" / "python.exe"))
    for value in hints:
        if not isinstance(value, str) or not value:
            continue
        path = Path(value)
        if path.parent.name.lower() == "python-win" and path.name.lower() == "python.exe" and path.is_file():
            return path
    return None


def candidates(env: dict[str, str]) -> list[tuple[Path, dict[str, str], Path]]:
    root = user_root(env)
    if not desktop_mode(env, root):
        return [(Path(sys.executable), dict(env), Path(sys.executable))]
    if root is None:
        return []
    try:
        record = json.loads((root / "skill-deps-stamp.json").read_text(encoding="utf-8-sig"))
        stamp = record.get("pyVenv", {})
        if not isinstance(stamp, dict):
            return []
    except FileNotFoundError:
        stamp = {}
    except (OSError, ValueError, AttributeError):
        # It may be in the middle of an atomic replacement by the installer.
        return []
    base = base_python(root, env, stamp)
    if base is None:
        return []
    venv = root / "skill-deps" / "py-venv" / "Scripts" / "python.exe"
    if stamp.get("installTarget") != "py-site" and venv.is_file():
        return [(venv, dict(env), base)]
    site = root / "skill-deps" / "py-site"
    if stamp.get("installTarget") == "py-site" and base is not None and site.is_dir():
        child_env = dict(env)
        child_env["PYTHONPATH"] = str(site) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return [(base, child_env, base)]
    return []


def no_window() -> dict:
    return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {}


def resolve_python(wait_seconds: float = 0) -> tuple[Path, dict[str, str], Path] | None:
    deadline = time.monotonic() + max(0, wait_seconds)
    while True:
        for candidate in candidates(dict(os.environ)):
            executable, child_env, _bootstrap = candidate
            try:
                completed = subprocess.run(
                    [str(executable), "-c", PROBE], env=child_env, capture_output=True,
                    text=True, encoding="utf-8", errors="replace",
                    timeout=min(5, max(0.1, deadline - time.monotonic())) if wait_seconds else 5,
                    **no_window(),
                )
                if completed.returncode == 0:
                    details = json.loads(completed.stdout)
                    if isinstance(details.get("executable"), str) and details["executable"]:
                        if _bootstrap.parent.name.lower() == "python-win":
                            expected = os.path.normcase(str(_bootstrap.parent.resolve()))
                            actual = os.path.normcase(str(Path(details.get("base_prefix", "")).resolve()))
                            if actual != expected:
                                continue
                        if executable.parent.name.lower() == "scripts":
                            expected_prefix = os.path.normcase(str(executable.parent.parent.resolve()))
                            actual_prefix = os.path.normcase(str(Path(details.get("prefix", "")).resolve()))
                            if actual_prefix != expected_prefix:
                                continue
                        return candidate
            except (OSError, subprocess.SubprocessError, ValueError, AttributeError):
                pass
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        time.sleep(min(2, remaining))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--wait-seconds", type=float, default=45)
    run = commands.add_parser("run")
    run.add_argument("script", choices=sorted(ALLOWED_SCRIPTS))
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    wait_seconds = args.wait_seconds if args.command == "prepare" else 0
    if not 0 <= wait_seconds <= 45:
        parser.error("--wait-seconds 必须在 0 到 45 之间")
    resolved = resolve_python(wait_seconds)
    if resolved is None:
        print("PREFLIGHT_PENDING: dependency_not_ready; 后台依赖尚未就绪，请稍后重试本准备步骤。",
              file=sys.stdout if args.command == "prepare" else sys.stderr, flush=True)
        return 0 if args.command == "prepare" else 3
    executable, child_env, bootstrap = resolved
    if args.command == "prepare":
        temp_cache = CACHE_PATH.with_name(CACHE_PATH.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            temp_cache.write_text(str(bootstrap), encoding="utf-8")
            os.replace(temp_cache, CACHE_PATH)
        finally:
            if temp_cache.exists():
                temp_cache.unlink()
        print("Skill Python: " + str(executable), flush=True)
        print("PREFLIGHT_OK", flush=True)
        return 0
    try:
        return subprocess.call([str(executable), str(SCRIPTS_DIR / args.script), *args.arguments], env=child_env,
                               stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr, **no_window())
    except OSError as exc:
        print("PREFLIGHT_FAILED: python_launch_failed: " + str(exc), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())