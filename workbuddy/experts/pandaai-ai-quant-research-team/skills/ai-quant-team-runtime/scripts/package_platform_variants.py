#!/usr/bin/env python3
"""Build individually installable platform archives for the portable team."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Iterable


VERSION = "0.4.2"
IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".runtime", "node_modules"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
ROOT_FILES = ("AGENTS.md", "README.md", "README.en.md", "LICENSE", ".gitignore")
CORE_DIRS = ("agents", "references", "scripts")
ADAPTER_SHARED = (
    "adapters/__init__.py",
    "adapters/README.md",
    "adapters/host-capability-contract.json",
    "adapters/common",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def allowed(path: Path, root: Path, *, lean: bool) -> bool:
    relative = path.relative_to(root)
    if any(part in IGNORED_PARTS for part in relative.parts):
        return False
    if path.suffix.lower() in IGNORED_SUFFIXES:
        return False
    if lean and relative.as_posix() in {
        "scripts/validate_agent.py",
        "scripts/package_platform_variants.py",
    }:
        return False
    return True


def collect(root: Path, includes: Iterable[str], *, lean: bool) -> list[Path]:
    files: set[Path] = set()
    for relative in includes:
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"include escapes source root: {relative}") from exc
        if not target.exists():
            raise FileNotFoundError(f"missing package input: {relative}")
        candidates = target.rglob("*") if target.is_dir() else (target,)
        for candidate in candidates:
            if candidate.is_symlink():
                raise ValueError(f"symlink cannot be packaged: {candidate}")
            if candidate.is_file() and allowed(candidate, root, lean=lean):
                files.add(candidate)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def add_file(archive: zipfile.ZipFile, source: Path, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname, date_time=(2026, 8, 24, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, source.read_bytes())


def add_text(archive: zipfile.ZipFile, text: str, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname, date_time=(2026, 8, 24, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, text.encode("utf-8"))


def build_agent_archive(
    source_root: Path,
    output: Path,
    *,
    variant: str,
    adapter_dir: str | None,
    extra_root_files: tuple[str, ...] = (),
    requirements: str | None = None,
    full: bool = False,
) -> dict[str, object]:
    top = f"agent-ai-quant-research-team-{variant}-v{VERSION}"
    if full:
        includes = (*ROOT_FILES, "CLAUDE.md", ".cursor", "agents", "references", "scripts", "adapters", "tests")
    else:
        includes = (*ROOT_FILES, *extra_root_files, *CORE_DIRS, *ADAPTER_SHARED)
        if adapter_dir:
            includes += (f"adapters/{adapter_dir}",)
    files = collect(source_root, includes, lean=not full)
    package_readme = (
        f"# {variant} package\n\n"
        f"Version: {VERSION}\n\n"
        "The root `AGENTS.md` is the canonical expert-team entry point. "
        "This archive contains only the selected host adapter plus the shared loader. "
        "Run the adapter-specific README under `adapters/` before starting a task.\n"
    )
    with zipfile.ZipFile(output, "w") as archive:
        for source in files:
            relative = source.relative_to(source_root).as_posix()
            add_file(archive, source, f"{top}/{relative}")
        add_text(archive, package_readme, f"{top}/README-PACKAGE.md")
        if requirements:
            add_text(archive, requirements.rstrip() + "\n", f"{top}/requirements.txt")
    return {
        "variant": variant,
        "archive": output.name,
        "sha256": sha256(output),
        "bytes": output.stat().st_size,
        "files": len(files) + 1 + int(requirements is not None),
        "top_level": top,
    }


def build_workbuddy_archive(package_root: Path, output: Path) -> dict[str, object]:
    top = f"pandaai-ai-quant-research-team-workbuddy-v{VERSION}"
    files = collect(package_root, (".",), lean=False)
    with zipfile.ZipFile(output, "w") as archive:
        for source in files:
            relative = source.relative_to(package_root).as_posix()
            add_file(archive, source, f"{top}/{relative}")
    return {
        "variant": "workbuddy",
        "archive": output.name,
        "sha256": sha256(output),
        "bytes": output.stat().st_size,
        "files": len(files),
        "top_level": top,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workbuddy-package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    workbuddy = args.workbuddy_package.resolve()
    output = args.output.resolve()
    if not (root / "AGENTS.md").is_file():
        raise SystemExit(f"invalid portable source root: {root}")
    team = json.loads((root / "agents" / "team.json").read_text(encoding="utf-8-sig"))
    if team.get("package_version") != VERSION:
        raise SystemExit(
            f"package version mismatch: script={VERSION}, team={team.get('package_version')}"
        )
    if not (workbuddy / ".codebuddy-plugin" / "plugin.json").is_file():
        raise SystemExit(f"invalid WorkBuddy package root: {workbuddy}")
    if output.exists():
        raise SystemExit(f"output directory already exists: {output}")
    output.mkdir(parents=True)
    specs = (
        ("portable", None, (), None, True),
        ("codex", "codex", (), None, False),
        ("claude-code", "claude_code", ("CLAUDE.md",), None, False),
        ("openai-agents-sdk", "openai_agents", (), "openai-agents", False),
        ("langgraph", "langgraph", (), "langgraph", False),
    )
    manifest: list[dict[str, object]] = []
    for variant, adapter, roots, requirements, full in specs:
        archive = output / f"agent-ai-quant-research-team-{variant}-v{VERSION}.zip"
        manifest.append(build_agent_archive(
            root,
            archive,
            variant=variant,
            adapter_dir=adapter,
            extra_root_files=roots,
            requirements=requirements,
            full=full,
        ))
    workbuddy_archive = output / f"pandaai-ai-quant-research-team-workbuddy-v{VERSION}.zip"
    manifest.append(build_workbuddy_archive(workbuddy, workbuddy_archive))
    payload = {
        "schema_version": 1,
        "package_version": VERSION,
        "source_root": str(root),
        "archives": manifest,
    }
    (output / "SHA256SUMS.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["# AI Quant Research Team platform packages", ""]
    for item in manifest:
        lines.append(
            f"- `{item['archive']}` — {item['variant']}; SHA-256 `{item['sha256']}`"
        )
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
