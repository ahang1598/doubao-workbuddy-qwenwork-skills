import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from text_fit import fit_text_boxes, text_height
import tempfile

LINT = Path(__file__).resolve().parents[1] / "xml_lint.py"
PAGE = (
    '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
    '<shape type="text" topLeftX="56" topLeftY="226" width="300" height="76"><content fontSize="11.5" '
    'lineSpacing="multiple:1.5" verticalAlign="top"><p>A 位　有机或无机阳离子，决定容忍因子与热稳定性。</p>'
    "<p>B 位　Pb²⁺/Sn²⁺ 金属阳离子，Sn 易氧化为 Sn⁴⁺。</p><p>X 位　I⁻/Br⁻/Cl⁻ 卤素决定带隙，混合卤素在光照下易相分离。</p>"
    "<p>容忍因子 t 介于 0.8–1.0 时稳定。</p></content></shape>"
    '<shape type="text" topLeftX="40" topLeftY="20" width="400" height="30"><content fontSize="20" wrap="false"><p>标题</p></content></shape>'
    "</data></slide>"
)


def overflow_count(xml, tmp):
    path = Path(tmp) / "p.xml"
    path.write_text(xml, encoding="utf-8")
    out = subprocess.run([sys.executable, str(LINT), "--input", str(path)], capture_output=True, text=True).stdout
    report = json.loads(out)
    return sum(e["code"] == "text_may_overflow_shape" for s in report["slides"] for e in s["errors"])


class TextFitTest(unittest.TestCase):
    def test_fit_removes_overflow_and_keeps_other_boxes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(overflow_count(PAGE, tmp), 1)
            fitted, warnings = fit_text_boxes(PAGE)
            self.assertEqual(overflow_count(fitted, tmp), 0)
        self.assertEqual(warnings, [])
        self.assertIn('width="400" height="30"', fitted)
        self.assertIn('topLeftX="56" topLeftY="226" width="300"', fitted)

    def test_text_height_grows_with_text(self):
        short = text_height("一行", width=300, font_size=14)
        long = text_height("很长的说明文字" * 20, width=300, font_size=14)
        self.assertGreater(long, short * 3)
