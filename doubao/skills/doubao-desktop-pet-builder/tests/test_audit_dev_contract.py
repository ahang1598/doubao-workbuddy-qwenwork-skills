from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "audit_project.py"


def write_project(root: Path, *, unsafe: bool) -> None:
    (root / "src").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "tools" / "run-dev.mjs").write_text("// audit fixture\n", encoding="utf-8")
    (root / "src" / "main.ts").write_text(
        "" if unsafe else "runtime:renderer-ready\nconsole-message\n",
        encoding="utf-8",
    )
    (root / "src" / "preload.ts").write_text(
        "" if unsafe else "runtime:renderer-ready\n",
        encoding="utf-8",
    )
    (root / "index.html").write_text(
        "<meta http-equiv=\"Content-Security-Policy\" content=\"script-src 'self'\">",
        encoding="utf-8",
    )
    (root / "webpack.renderer.config.js").write_text(
        "module.exports={devtool:'eval-source-map'};\n" if unsafe
        else "module.exports={devtool:'source-map'};\n",
        encoding="utf-8",
    )
    package = {
        "name": "audit-fixture",
        "version": "1.0.0",
        "scripts": {
            "dev": "electron-forge start" if unsafe else "node tools/run-dev.mjs",
        },
    }
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    (root / "package-lock.json").write_text("{}\n", encoding="utf-8")
    (root / ".doubao-pet-builder.json").write_text("{}\n", encoding="utf-8")


def audit(root: Path) -> tuple[int, set[str]]:
    result = subprocess.run(
        [sys.executable, str(AUDIT), str(root)],
        check=False,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    return result.returncode, {finding["rule"] for finding in report["findings"]}


class AuditDevelopmentContractTest(unittest.TestCase):
    def test_strict_csp_rejects_eval_devtool_and_uncontrolled_dev(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(root, unsafe=True)
            code, rules = audit(root)
            self.assertEqual(code, 1)
            self.assertIn("eval-renderer-devtool", rules)
            self.assertIn("csp-webpack-conflict", rules)
            self.assertIn("uncontrolled-dev-script", rules)
            self.assertIn("missing-three-renderer-ready", rules)

    def test_safe_source_dev_contract_has_no_high_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(root, unsafe=False)
            code, rules = audit(root)
            self.assertEqual(code, 0, rules)
            self.assertNotIn("eval-renderer-devtool", rules)
            self.assertNotIn("packaging-in-dev", rules)

    def test_electron_install_contract_rejects_unpinned_or_unsafe_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_project(root, unsafe=False)
            package = json.loads((root / "package.json").read_text(encoding="utf-8"))
            package["devDependencies"] = {"electron": "^37.10.3"}
            (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
            (root / ".npmrc").write_text("strict-ssl=false\n", encoding="utf-8")
            code, rules = audit(root)
            self.assertEqual(code, 1)
            self.assertIn("unpinned-electron", rules)
            self.assertIn("blocked-electron-postinstall", rules)
            self.assertIn("disabled-tls-verification", rules)


if __name__ == "__main__":
    unittest.main()
