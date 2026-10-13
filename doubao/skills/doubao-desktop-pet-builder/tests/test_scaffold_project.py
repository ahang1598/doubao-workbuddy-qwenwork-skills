from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "scripts" / "scaffold_project.py"
SPEC = ROOT / "assets" / "electron-template" / "pet-spec.json"


class ScaffoldProjectTest(unittest.TestCase):
    def test_regression_fixture_creates_complete_contract_v5_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "generated"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCAFFOLD),
                    "--spec",
                    str(SPEC),
                    "--use-regression-fixture",
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            provenance = json.loads((output / ".doubao-pet-builder.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["builder"], "doubao-desktop-pet-builder")
            self.assertEqual(provenance["templateContractVersion"], 5)
            self.assertEqual(provenance["specSchemaVersion"], 5)
            self.assertEqual(len(list((output / "incoming-assets").rglob("*.png"))), 40)
            self.assertTrue((output / "incoming-assets/core-ip/core-ip.png").is_file())
            self.assertTrue({
                "package.json",
                "package-lock.json",
                "tools/semantic-cutout.mjs",
                "tools/vision-cutout.swift",
                "tools/qa-assets.mjs",
            }.issubset(provenance["criticalFileHashes"]))
            for relative, expected in provenance["criticalFileHashes"].items():
                self.assertEqual(hashlib.sha256((output / relative).read_bytes()).hexdigest(), expected)
            self.assertTrue((output / "tests/unit/state-machine.test.ts").is_file())
            self.assertTrue((output / "tests/e2e/soak.e2e.ts").is_file())
            self.assertTrue((output / "tests/unit/dev-ports.test.mjs").is_file())

    def test_scaffold_refuses_to_overwrite_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCAFFOLD),
                    "--spec",
                    str(SPEC),
                    "--use-regression-fixture",
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 3)

    def test_incomplete_template_fails_before_output_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root = Path(directory) / "skill"
            shutil.copytree(ROOT, skill_root, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
            (skill_root / "assets" / "electron-template" / "src" / "main" / "data-validation.ts").unlink()
            output = Path(directory) / "generated"
            result = subprocess.run(
                [
                    sys.executable,
                    str(skill_root / "scripts" / "scaffold_project.py"),
                    "--spec",
                    str(skill_root / "assets" / "electron-template" / "pet-spec.json"),
                    "--use-regression-fixture",
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 6)
            self.assertIn("Template contract is incomplete", result.stderr)
            self.assertIn("src/main/data-validation.ts", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
