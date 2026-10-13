from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "electron-template"
SCAFFOLD = ROOT / "scripts" / "scaffold_project.py"
MIGRATE = ROOT / "scripts" / "migrate_project.py"
SPEC = TEMPLATE / "pet-spec.json"


class MigrateProjectTest(unittest.TestCase):
    def test_v3_project_requires_an_isolated_v5_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            scaffold = subprocess.run(
                [sys.executable, str(SCAFFOLD), "--spec", str(SPEC), "--use-regression-fixture", "--output", str(project)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            provenance_path = project / ".doubao-pet-builder.json"
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["templateContractVersion"] = 3
            provenance["criticalFileHashes"] = {
                relative: hashlib.sha256((project / relative).read_bytes()).hexdigest()
                for relative in list(provenance["criticalFileHashes"])[:13]
            }
            provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(MIGRATE), str(project)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("require a new isolated scaffold", result.stderr)
            self.assertFalse((project / ".doubao-pet-builder.v3.json").exists())


if __name__ == "__main__":
    unittest.main()
