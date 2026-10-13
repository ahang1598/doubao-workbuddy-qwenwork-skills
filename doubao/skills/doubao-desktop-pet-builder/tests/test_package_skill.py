from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "scripts" / "package_skill.py"


class PackageSkillTest(unittest.TestCase):
    def test_package_zip_is_clean_and_root_matches_frontmatter_name(self) -> None:
        skill_name = next(
            line.split(":", 1)[1].strip()
            for line in (ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
            if line.startswith("name:")
        )
        prefix = f"{skill_name}/"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "skill.zip"
            result = subprocess.run(
                [sys.executable, str(PACKAGE), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
            self.assertTrue(names)
            self.assertTrue(all(name.startswith(prefix) for name in names))
            for name in names:
                parts = Path(name).parts
                self.assertFalse(any(part in {"__MACOSX", "__pycache__", ".git", ".DS_Store"} for part in parts), name)
                self.assertFalse(any(part.startswith("._") for part in parts), name)
                self.assertFalse(name.endswith((".pyc", ".pyo")), name)
            required = f"{prefix}assets/electron-template/src/main/data-validation.ts"
            self.assertIn(required, names)
            self.assertIn(f"{prefix}agents/openai.yaml", names)
            with zipfile.ZipFile(output) as archive:
                contract_source = archive.read(f"{prefix}scripts/template_contract.py").decode("utf-8")
                agent_source = archive.read(f"{prefix}agents/openai.yaml").decode("utf-8")
            self.assertIn("TEMPLATE_CONTRACT_VERSION = 5", contract_source)
            self.assertIn(f"${skill_name}", agent_source)


if __name__ == "__main__":
    unittest.main()
