"""Shared Electron template contract used by scaffold, audit, migration, and packaging."""

from __future__ import annotations

from pathlib import Path


SPEC_SCHEMA_VERSION = 5
TEMPLATE_CONTRACT_VERSION = 5

CONTRACT_V3_FILES = (
    "forge.config.js",
    "webpack.renderer.config.js",
    "src/main.ts",
    "src/preload.ts",
    "src/main/data-validation.ts",
    "src/renderer/pet/state-machine.ts",
    "tools/collect-release.mjs",
    "tools/process-assets.mjs",
    "tools/qa-assets.mjs",
    "tools/run-build.mjs",
    "tools/run-dev.mjs",
    "tools/dev-smoke-client.mjs",
    "tools/validate-dev-contract.mjs",
)

CONTRACT_V4_FILES = (
    *CONTRACT_V3_FILES,
    "tools/preflight.mjs",
    "tools/dev-ports.mjs",
    "tools/doctor.mjs",
    "tools/inspect-assets.mjs",
)

CONTRACT_V5_FILES = (
    *CONTRACT_V4_FILES,
    "package.json",
    "package-lock.json",
    "src/shared/contracts.ts",
    "src/renderer/pet/index.ts",
    "tests/e2e/app.e2e.ts",
    "tools/semantic-cutout.mjs",
    "tools/vision-cutout.swift",
    "tools/validate-spec.mjs",
    "tools/validate-asset-links.mjs",
    "tools/qa-ui.mjs",
    "tools/qa-experience.mjs",
)

CONTRACT_FILES_BY_VERSION = {
    3: CONTRACT_V3_FILES,
    4: CONTRACT_V4_FILES,
    5: CONTRACT_V5_FILES,
}

CRITICAL_TEMPLATE_FILES = CONTRACT_FILES_BY_VERSION[TEMPLATE_CONTRACT_VERSION]


def missing_contract_files(root: Path, version: int = TEMPLATE_CONTRACT_VERSION) -> list[str]:
    required = CONTRACT_FILES_BY_VERSION.get(version)
    if required is None:
        return [f"<unsupported-template-contract:{version}>"]
    return [relative for relative in required if not (root / relative).is_file()]
