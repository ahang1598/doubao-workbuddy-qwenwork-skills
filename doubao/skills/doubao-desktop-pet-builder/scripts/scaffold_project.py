#!/usr/bin/env python3
"""Create an isolated Electron desktop-pet project from the bundled template."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from template_contract import (
    CRITICAL_TEMPLATE_FILES,
    SPEC_SCHEMA_VERSION,
    TEMPLATE_CONTRACT_VERSION,
    missing_contract_files,
)
from validate_pet_spec import validate


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "electron-template"
FIXTURE = ROOT / "assets" / "regression-fixture" / "synthetic-pet"


def npm_name(app_id: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", app_id.lower()).strip("-")
    return value[-80:] or "desktop-pet"


def image_format_error(path: Path) -> str | None:
    """Return an error string when the file is not a decodable PNG/JPEG/WebP.

    Failed downloads often leave a 2-byte ``{}`` JSON placeholder, an HTML error
    page, or an empty file. scaffold must reject these before they are copied
    into the project, otherwise process:assets fails later with a generic
    "unsupported image format" and the real cause (a broken source) is hidden.
    """
    try:
        head = path.read_bytes()[:16]
    except OSError as exc:
        return f"cannot read source: {exc}"
    size = path.stat().st_size
    is_png = head[:4] == b"\x89PNG"
    is_jpeg = head[:3] == b"\xff\xd8\xff"
    is_webp = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if size < 128 or not (is_png or is_jpeg or is_webp):
        preview = head.hex(" ")
        return f"not a PNG/JPEG/WebP image (bytes: {size}, header: {preview})"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--assets", type=Path)
    sources.add_argument("--use-regression-fixture", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read spec: {exc}", file=sys.stderr)
        return 2
    errors = validate(spec)
    if errors:
        print("Spec validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    output = args.output.resolve()
    if output.exists():
        print(f"Refusing to overwrite existing path: {output}", file=sys.stderr)
        return 3
    if not TEMPLATE.is_dir():
        print(f"Template missing: {TEMPLATE}", file=sys.stderr)
        return 4
    missing_contract = missing_contract_files(TEMPLATE)
    if missing_contract:
        print("Template contract is incomplete; reinstall or republish the Skill before scaffolding.", file=sys.stderr)
        print(f"- script: {Path(__file__).resolve()}", file=sys.stderr)
        print(f"- skill root: {ROOT}", file=sys.stderr)
        print(f"- template: {TEMPLATE}", file=sys.stderr)
        print(f"- contract: v{TEMPLATE_CONTRACT_VERSION}", file=sys.stderr)
        for relative in missing_contract:
            print(f"- missing: {relative}", file=sys.stderr)
        return 6
    if spec.get("schemaVersion") != SPEC_SCHEMA_VERSION:
        print(
            f"Template contract v{TEMPLATE_CONTRACT_VERSION} requires pet-spec schema v{SPEC_SCHEMA_VERSION}.",
            file=sys.stderr,
        )
        return 2

    asset_source = FIXTURE if args.use_regression_fixture else args.assets
    assert asset_source is not None
    asset_source = asset_source.resolve()
    required = {spec["character"]["coreAsset"], *(frame for state in spec["states"] for frame in state["frames"])}
    missing = sorted(name for name in required if not (asset_source / name).is_file())
    if missing:
        print(f"Asset directory is missing {len(missing)} file(s): {missing}", file=sys.stderr)
        return 5

    corrupt = []
    for name in sorted(required):
        error = image_format_error(asset_source / name)
        if error:
            corrupt.append(f"{name}: {error}")
    if corrupt:
        print(f"Asset directory has {len(corrupt)} invalid image(s):", file=sys.stderr)
        for entry in corrupt:
            print(f"- {entry}", file=sys.stderr)
        print("Re-download or regenerate these frames; do not copy failed-download placeholders into the project.", file=sys.stderr)
        return 5

    shutil.copytree(TEMPLATE, output, ignore=shutil.ignore_patterns(".gitkeep", "node_modules", "out", "release", ".webpack"))
    incoming_dir = output / "incoming-assets"
    incoming_dir.mkdir(parents=True, exist_ok=True)
    for name in sorted(required):
        source = asset_source / name
        target = incoming_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    (output / "pet-spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    package_path = output / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["name"] = npm_name(spec["app"]["appId"])
    package["productName"] = spec["app"]["name"]
    package["version"] = spec["app"]["version"]
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lock_path = output / "package-lock.json"
    if lock_path.is_file():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["name"] = package["name"]
        lock["version"] = package["version"]
        root_package = lock.get("packages", {}).get("")
        if isinstance(root_package, dict):
            root_package["name"] = package["name"]
            root_package["version"] = package["version"]
        lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.use_regression_fixture:
        marker = output / "REGRESSION_FIXTURE_ONLY.txt"
        marker.write_text("This project uses a synthetic regression fixture. Replace it before user delivery.\n", encoding="utf-8")

    copied_assets = []
    for name in sorted(required):
        target = incoming_dir / name
        copied_assets.append({
            "path": name,
            "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        })
    critical_hashes = {}
    for relative in CRITICAL_TEMPLATE_FILES:
        critical_path = output / relative
        if not critical_path.is_file():
            print(
                f"Template copy became incomplete after scaffolding: {relative}; "
                f"source template was {TEMPLATE}",
                file=sys.stderr,
            )
            return 6
        critical_hashes[relative] = hashlib.sha256(critical_path.read_bytes()).hexdigest()

    provenance = {
        "builder": "doubao-desktop-pet-builder",
        "templateContractVersion": TEMPLATE_CONTRACT_VERSION,
        "specSchemaVersion": spec["schemaVersion"],
        "criticalFileHashes": critical_hashes,
    }
    (output / ".doubao-pet-builder.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    scaffold_report = {
        "schemaVersion": spec["schemaVersion"],
        "appId": spec["app"]["appId"],
        "templateContractVersion": TEMPLATE_CONTRACT_VERSION,
        "specSha256": hashlib.sha256((output / "pet-spec.json").read_bytes()).hexdigest(),
        "assetCount": len(copied_assets),
        "assetStage": "incoming-assets; run npm run process:assets before check/dev",
        "assets": copied_assets,
    }
    qa_dir = output / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    (qa_dir / "scaffold-report.json").write_text(json.dumps(scaffold_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    roundtrip_spec = json.loads((output / "pet-spec.json").read_text(encoding="utf-8"))
    roundtrip_package = json.loads(package_path.read_text(encoding="utf-8"))
    if roundtrip_spec != spec or roundtrip_package.get("productName") != spec["app"]["name"]:
        print("UTF-8 round-trip verification failed after scaffolding", file=sys.stderr)
        return 6

    print(f"Created desktop-pet project: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
