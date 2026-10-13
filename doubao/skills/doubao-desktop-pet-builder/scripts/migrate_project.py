#!/usr/bin/env python3
"""Migrate an untouched generated project to the current template contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from template_contract import CRITICAL_TEMPLATE_FILES, TEMPLATE_CONTRACT_VERSION, missing_contract_files


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "electron-template"
ADDED_TEMPLATE_FILES = (
    "tests/unit/dev-ports.test.mjs",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    provenance_path = project / ".doubao-pet-builder.json"
    if not project.is_dir() or not provenance_path.is_file():
        print("Migration requires a scaffolded desktop-pet project.", file=sys.stderr)
        return 2
    missing = missing_contract_files(TEMPLATE)
    if missing:
        print(f"Current Skill template is incomplete: {missing}", file=sys.stderr)
        return 2
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read builder provenance: {exc}", file=sys.stderr)
        return 2
    source_version = provenance.get("templateContractVersion")
    if source_version == TEMPLATE_CONTRACT_VERSION:
        print(f"Project already uses template contract v{TEMPLATE_CONTRACT_VERSION}.")
        return 0
    print(
        f"No automatic migration from template contract v{source_version} to v{TEMPLATE_CONTRACT_VERSION}. "
        "The independent core asset and semantic cutout pipeline require a new isolated scaffold.",
        file=sys.stderr,
    )
    return 3
    hashes = provenance.get("criticalFileHashes")
    if not isinstance(hashes, dict) or not hashes:
        print("Source contract has no critical file hashes.", file=sys.stderr)
        return 3
    drift = []
    for relative, expected in hashes.items():
        target = project / relative
        if not target.is_file() or sha256(target) != expected:
            drift.append(relative)
    if drift:
        print(
            "Refusing migration because protected project files changed: "
            + ", ".join(sorted(drift)),
            file=sys.stderr,
        )
        return 4

    backup = project / ".doubao-pet-builder.v3.json"
    if backup.exists():
        print(f"Migration backup already exists: {backup}", file=sys.stderr)
        return 4
    shutil.copy2(provenance_path, backup)
    for relative in CRITICAL_TEMPLATE_FILES:
        source = TEMPLATE / relative
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for relative in ADDED_TEMPLATE_FILES:
        source = TEMPLATE / relative
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    package_path = project / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    template_package = json.loads((TEMPLATE / "package.json").read_text(encoding="utf-8"))
    for name in ("dev", "start", "check", "test", "test:dev-smoke", "qa:assets", "process:assets", "inspect:assets", "preflight", "doctor"):
        if name in template_package.get("scripts", {}):
            package.setdefault("scripts", {})[name] = template_package["scripts"][name]
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    new_hashes = {relative: sha256(project / relative) for relative in CRITICAL_TEMPLATE_FILES}
    provenance.update({
        "templateContractVersion": TEMPLATE_CONTRACT_VERSION,
        "criticalFileHashes": new_hashes,
        "migratedFrom": source_version,
        "migratedAt": datetime.now(timezone.utc).isoformat(),
    })
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_dir = project / "qa"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "template-migration-report.json").write_text(
        json.dumps({
            "from": source_version,
            "to": TEMPLATE_CONTRACT_VERSION,
            "backup": backup.name,
            "updatedFiles": [*CRITICAL_TEMPLATE_FILES, *ADDED_TEMPLATE_FILES],
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Migrated {project} from template contract v{source_version} to v{TEMPLATE_CONTRACT_VERSION}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
