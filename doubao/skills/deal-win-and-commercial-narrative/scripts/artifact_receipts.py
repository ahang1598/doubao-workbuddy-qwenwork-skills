"""Strict file-backed artifact receipt validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_artifact_receipts(receipts: Any, required_artifacts: Iterable[str]) -> dict[str, Any]:
    required = set(required_artifacts)
    failures: list[str] = []
    validated: list[dict[str, Any]] = []
    if not isinstance(receipts, list):
        return {"passed": False, "required": sorted(required), "failures": ["artifact_receipts must be a list"], "validated": []}
    names = []
    manifests = []
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            failures.append(f"artifact_receipts[{index}] must be an object")
            continue
        if set(receipt) != {"artifact_name", "path", "expected_sha256"}:
            failures.append(f"artifact_receipts[{index}] fields must be artifact_name,path,expected_sha256")
            continue
        name = receipt["artifact_name"]
        names.append(name)
        path = Path(receipt["path"])
        expected = receipt["expected_sha256"]
        if not path.is_file():
            failures.append(f"{name}: artifact file missing")
            continue
        actual = file_sha256(path)
        if actual != expected:
            failures.append(f"{name}: sha256 mismatch")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            failures.append(f"{name}: artifact is not valid JSON")
            continue
        if payload.get("artifact_name") != name:
            failures.append(f"{name}: artifact_name mismatch")
            continue
        manifest = payload.get("manifest")
        if not isinstance(manifest, dict):
            failures.append(f"{name}: manifest missing")
            continue
        if set(manifest.get("required_artifacts") or []) != required:
            failures.append(f"{name}: required artifact set mismatch")
        if not isinstance(manifest.get("counts"), dict) or not manifest.get("artifact_state"):
            failures.append(f"{name}: manifest state/counts missing")
        manifests.append((name, manifest))
        validated.append({"artifact_name": name, "path": str(path), "actual_sha256": actual})
    if set(names) != required or len(names) != len(required):
        failures.append("receipt names must exactly equal runtime required artifacts")
    if manifests:
        baseline = manifests[0][1]
        for name, manifest in manifests[1:]:
            if manifest.get("artifact_state") != baseline.get("artifact_state"):
                failures.append(f"{name}: artifact_state inconsistent")
            if manifest.get("counts") != baseline.get("counts"):
                failures.append(f"{name}: counts inconsistent")
            if set(manifest.get("required_artifacts") or []) != set(baseline.get("required_artifacts") or []):
                failures.append(f"{name}: required artifact set inconsistent")
    return {"passed": not failures, "required": sorted(required), "failures": failures, "validated": validated}
