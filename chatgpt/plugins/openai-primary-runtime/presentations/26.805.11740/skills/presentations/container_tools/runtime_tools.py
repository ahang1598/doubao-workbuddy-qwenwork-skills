#!/usr/bin/env python3
# Copyright (c) OpenAI. All rights reserved.
"""Helpers for public container_tools scripts to resolve Codex runtime dependencies."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _exe_names(name: str) -> list[str]:
    if os.name != "nt" or Path(name).suffix:
        return [name]
    return [name + ".cmd", name + ".exe", name]


def _candidate_dependency_roots() -> list[Path]:
    roots: list[Path] = []
    for env_name in (
        "CODEX_RUNTIME_DEPENDENCIES",
        "CODEX_WORKSPACE_DEPENDENCIES",
        "CODEX_DEPENDENCIES",
    ):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value).expanduser())

    executable = Path(sys.executable).resolve()
    for parent in executable.parents:
        if any((parent / "node" / "bin" / exe_name).exists() for exe_name in _exe_names("node")):
            roots.append(parent)
            break
        if (parent / "bin").exists() and (parent / "python").exists():
            roots.append(parent)
            break

    roots.append(
        Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies"
    )

    seen: set[Path] = set()
    unique: list[Path] = []
    for root in roots:
        resolved = root.resolve()
        if resolved not in seen:
            unique.append(resolved)
            seen.add(resolved)
    return unique


def dependency_root() -> Path:
    for root in _candidate_dependency_roots():
        if root.exists():
            return root
    return _candidate_dependency_roots()[0]


def _override_bin_dir(root: Path) -> Path:
    return root / "bin" / "override"


def _fallback_bin_dir(root: Path) -> Path:
    return root / "bin" / "fallback"


def runtime_bin_dir() -> str:
    root = dependency_root()
    for bin_dir in (_override_bin_dir(root), _fallback_bin_dir(root)):
        if bin_dir.is_dir():
            return str(bin_dir)
    return str(root / "bin" / "override")


def runtime_binary(name: str) -> str:
    for root in _candidate_dependency_roots():
        preferred_candidates = [_override_bin_dir(root) / exe_name for exe_name in _exe_names(name)]
        if name == "node":
            preferred_candidates = [
                root / "node" / "bin" / exe_name for exe_name in _exe_names(name)
            ] + preferred_candidates
        for candidate in preferred_candidates:
            if candidate.exists():
                return str(candidate)

    path_candidate = shutil.which(name)
    if path_candidate:
        return path_candidate

    for root in _candidate_dependency_roots():
        fallback_candidates = [_fallback_bin_dir(root) / exe_name for exe_name in _exe_names(name)]
        for candidate in fallback_candidates:
            if candidate.exists():
                return str(candidate)
    return name


def poppler_bin_dir() -> str | None:
    binaries = [Path(runtime_binary(name)) for name in ("pdfinfo", "pdftoppm")]
    if not all(binary.is_file() for binary in binaries):
        return None
    bin_dirs = {binary.resolve().parent for binary in binaries}
    return str(bin_dirs.pop()) if len(bin_dirs) == 1 else None


def node_binary() -> str:
    return runtime_binary("node")


def node_modules_dir() -> str:
    return str(dependency_root() / "node" / "node_modules")


def runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    root = dependency_root()
    path_entries = [entry for entry in env.get("PATH", "").split(os.pathsep) if entry]
    ordered_entries: list[str] = []
    override_bin = _override_bin_dir(root)
    if override_bin.is_dir():
        ordered_entries.append(str(override_bin))
    ordered_entries.extend(path_entries)
    fallback_bin = _fallback_bin_dir(root)
    if fallback_bin.is_dir():
        ordered_entries.append(str(fallback_bin))
    env["PATH"] = os.pathsep.join(dict.fromkeys(ordered_entries))
    env.setdefault("NODE_PATH", node_modules_dir())
    return env
