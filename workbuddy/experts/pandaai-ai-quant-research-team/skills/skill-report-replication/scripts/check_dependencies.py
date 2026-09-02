#!/usr/bin/env python
"""Check and optionally install dependencies for report-replication."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as metadata
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Dependency:
    name: str
    import_name: str
    min_version: str | None = None
    install_specs: tuple[str, ...] = ()


DEPENDENCIES = [
    Dependency("pandas", "pandas", min_version="2.0.0", install_specs=("pandas>=2.0.0",)),
    Dependency("numpy", "numpy", min_version="1.22.0", install_specs=("numpy>=1.22,<2.0",)),
    Dependency("matplotlib", "matplotlib", install_specs=("matplotlib",)),
    Dependency("scipy", "scipy", install_specs=("scipy",)),
    Dependency("statsmodels", "statsmodels", install_specs=("statsmodels",)),
    Dependency("PyMuPDF", "fitz", install_specs=("PyMuPDF",)),
    Dependency("pdfplumber", "pdfplumber", install_specs=("pdfplumber",)),
    Dependency("openpyxl", "openpyxl", install_specs=("openpyxl",)),
    Dependency("pyarrow", "pyarrow", install_specs=("pyarrow",)),
    Dependency("requests", "requests", install_specs=("requests",)),
]


def parse_version(value: str | None) -> tuple[int, ...]:
    if not value:
        return (0,)
    parts = []
    for part in value.split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits or 0))
    return tuple(parts)


def version_ok(version: str | None, min_version: str | None) -> bool:
    if min_version is None:
        return True
    return parse_version(version) >= parse_version(min_version)


def inspect_dependency(dep: Dependency) -> dict:
    info = {
        "name": dep.name,
        "import_name": dep.import_name,
        "min_version": dep.min_version,
        "installed": False,
        "version": None,
        "module_file": None,
        "ok": False,
        "error": None,
    }
    try:
        module = importlib.import_module(dep.import_name)
        info["installed"] = True
        module_file = getattr(module, "__file__", None)
        info["module_file"] = str(Path(module_file).resolve()) if module_file else None
    except Exception as exc:
        info["error"] = f"import failed: {exc}"
        return info

    try:
        info["version"] = metadata.version(dep.name)
    except metadata.PackageNotFoundError:
        info["version"] = getattr(module, "__version__", None)

    if version_ok(info["version"], dep.min_version):
        info["ok"] = True
    else:
        info["error"] = f"expected {dep.name}>={dep.min_version}, got {info['version']}"
    return info


def run_pip_install(spec: str, upgrade: bool) -> dict:
    cmd = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(spec)
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return {
        "spec": spec,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "ok": proc.returncode == 0,
    }


def install_dependency(dep: Dependency, upgrade: bool) -> list[dict]:
    attempts = []
    specs = dep.install_specs or (dep.name,)
    for spec in specs:
        attempt = run_pip_install(spec, upgrade=upgrade)
        attempts.append(attempt)
        if attempt["ok"]:
            break
    return attempts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install missing or too-old Python dependencies.",
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Pass --upgrade to pip when installing dependencies.",
    )
    args = parser.parse_args()

    report = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "python_min_version": "3.10",
        "python_ok": sys.version_info >= (3, 10),
        "dependencies": [],
        "install_attempts": {},
        "ok": False,
    }

    if not report["python_ok"]:
        report["error"] = "Pandadata production mode requires Python 3.10 or newer."
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    for dep in DEPENDENCIES:
        info = inspect_dependency(dep)
        if not info["ok"] and args.install:
            attempts = install_dependency(dep, upgrade=args.upgrade)
            report["install_attempts"][dep.name] = attempts
            info = inspect_dependency(dep)
        report["dependencies"].append(info)

    report["ok"] = all(item["ok"] for item in report["dependencies"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
