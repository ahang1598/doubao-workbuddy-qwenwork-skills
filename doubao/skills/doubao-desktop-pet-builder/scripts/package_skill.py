from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from template_contract import CRITICAL_TEMPLATE_FILES, TEMPLATE_CONTRACT_VERSION, missing_contract_files

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INCLUDE = ("SKILL.md", "agents", "references", "scripts", "assets", "tests")
FORBIDDEN_NAMES = {".git", "__MACOSX", "__pycache__", ".DS_Store"}


def skill_name() -> str:
    for line in (ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    raise ValueError("SKILL.md frontmatter must include name")


def is_forbidden(path: Path) -> bool:
    if path.name in FORBIDDEN_NAMES or path.name.startswith("._"):
        return True
    return path.suffix in {".pyc", ".pyo"}


def iter_publish_files() -> list[Path]:
    files: list[Path] = []
    for item in DEFAULT_INCLUDE:
        source = ROOT / item
        if not source.exists():
            continue
        if source.is_file():
            candidates = [source]
        else:
            candidates = [path for path in source.rglob("*") if path.is_file()]
        for path in candidates:
            relative = path.relative_to(ROOT)
            if any(is_forbidden(part) for part in relative.parents):
                continue
            if is_forbidden(path):
                continue
            files.append(path)
    return sorted(files, key=lambda path: path.as_posix())


def stage_files(files: list[Path], staging_root: Path, root_name: str) -> Path:
    package_root = staging_root / root_name
    package_root.mkdir(parents=True)
    for path in files:
        target = package_root / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return package_root


def assert_clean_archive(zip_path: Path, root_name: str) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
    if not names:
        raise ValueError("archive is empty")
    prefix = f"{root_name}/"
    for name in names:
        if not name.startswith(prefix):
            raise ValueError(f"archive entry must be under {root_name}/: {name}")
        parts = Path(name).parts
        if any(part in FORBIDDEN_NAMES or part.startswith("._") for part in parts):
            raise ValueError(f"forbidden archive entry: {name}")
        if name.endswith((".pyc", ".pyo")):
            raise ValueError(f"forbidden archive entry: {name}")


def assert_complete_skill(root: Path) -> None:
    template = root / "assets" / "electron-template"
    missing = missing_contract_files(template)
    if missing:
        raise ValueError(
            f"template contract v{TEMPLATE_CONTRACT_VERSION} is incomplete: {', '.join(missing)}"
        )
    required = (
        "SKILL.md",
        "scripts/scaffold_project.py",
        "scripts/template_contract.py",
        "references/pet-spec.schema.json",
        "assets/electron-template/pet-spec.json",
        "assets/regression-fixture/synthetic-pet",
        *tuple(f"assets/electron-template/{relative}" for relative in CRITICAL_TEMPLATE_FILES),
    )
    absent = [relative for relative in required if not (root / relative).exists()]
    if absent:
        raise ValueError(f"published Skill is missing required content: {', '.join(absent)}")


def verify_archive_can_scaffold(zip_path: Path, root_name: str, verification_root: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(verification_root)
    skill_root = verification_root / root_name
    assert_complete_skill(skill_root)
    output = verification_root / "generated-project"
    command = [
        sys.executable,
        str(skill_root / "scripts" / "scaffold_project.py"),
        "--spec",
        str(skill_root / "assets" / "electron-template" / "pet-spec.json"),
        "--use-regression-fixture",
        "--output",
        str(output),
    ]
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(command, check=False, capture_output=True, text=True, env=environment)
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"packaged Skill failed scaffold verification: {details}")
    provenance = json.loads((output / ".doubao-pet-builder.json").read_text(encoding="utf-8"))
    if provenance.get("templateContractVersion") != TEMPLATE_CONTRACT_VERSION:
        raise ValueError("packaged Skill scaffold produced the wrong template contract version")


def build_zip(output: Path) -> Path:
    root_name = skill_name()
    assert_complete_skill(ROOT)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="doubao-skill-package-") as directory:
        staging = Path(directory)
        package_root = stage_files(iter_publish_files(), staging, root_name)
        temporary_zip = output.with_suffix(output.suffix + ".tmp")
        if temporary_zip.exists():
            temporary_zip.unlink()
        with zipfile.ZipFile(
            temporary_zip,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            strict_timestamps=False,
        ) as archive:
            for path in sorted(package_root.rglob("*"), key=lambda item: item.as_posix()):
                if path.is_file():
                    archive.write(path, path.relative_to(staging).as_posix())
        assert_clean_archive(temporary_zip, root_name)
        verify_archive_can_scaffold(temporary_zip, root_name, staging / "verification")
        temporary_zip.replace(output)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a clean ActionHub Skill ZIP.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT.parent / f"{skill_name()}.zip",
        help="Target ZIP path. Defaults to ../<skill-name>.zip.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        archive = build_zip(args.output)
    except Exception as exc:
        print(f"package failed: {exc}", file=sys.stderr)
        return 1
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
