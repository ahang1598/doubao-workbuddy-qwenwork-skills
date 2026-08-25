from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import xml_inspect


class XmlInspectRawXmlTest(unittest.TestCase):
    def test_raw_xml_preserves_embed_inner_svg_namespace(self) -> None:
        script_path = Path(xml_inspect.__file__).resolve()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "presentation.xml"
            input_path.write_text(
                """
                <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
                  <slide id="p01">
                    <data>
                      <embed id="b01" width="48" height="48" topLeftX="10" topLeftY="10">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
                          <path d="M0 0H48V48H0Z"/>
                        </svg>
                      </embed>
                    </data>
                  </slide>
                </presentation>
                """,
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(script_path), "--input", str(input_path), "--slide-id", "p01"],
                capture_output=True,
                check=False,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        raw_xml = result["slides"][0]["raw_xml"]
        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', raw_xml)
        self.assertIn("<path ", raw_xml)
        self.assertNotIn("<ns", raw_xml)
        self.assertNotIn(":svg", raw_xml)


if __name__ == "__main__":
    unittest.main()
