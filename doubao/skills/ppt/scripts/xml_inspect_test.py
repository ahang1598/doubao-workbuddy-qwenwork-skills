from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import xml_inspect


NAMESPACE = "https://www.larkoffice.com/sml/2.0"


class XmlInspectCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.input_path = Path(self.temp_dir.name) / "presentation.xml"

    def write_slides(self, slides: str) -> None:
        self.input_path.write_text(
            f'<presentation xmlns="{NAMESPACE}" width="960" height="540">'
            f"{slides}</presentation>",
            encoding="utf-8",
        )

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(Path(xml_inspect.__file__).resolve()),
             "--input", str(self.input_path), *args],
            capture_output=True,
            check=False,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def content(self, *args: str) -> str:
        completed = self.run_cli("--mode", "content", *args)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout

    def test_content_without_selection_returns_all_pages_in_document_order(self) -> None:
        self.write_slides(
            '<slide id="p2"><data><shape id="b2"><p>Second</p></shape></data></slide>'
            '<slide id="p1"><data><shape id="b1"><p>First</p></shape></data></slide>'
        )
        output = self.content()
        self.assertIn('## slide 1 id="p2"', output)
        self.assertIn('## slide 2 id="p1"', output)
        self.assertLess(output.index('id="p2"'), output.index('id="p1"'))
        self.assertIn('Second', output)
        self.assertIn('First', output)

    def test_selection_follows_requested_order_and_deduplicates_arguments(self) -> None:
        self.write_slides(
            '<slide id="p1"><data><shape><p>First</p></shape></data></slide>'
            '<slide id="p2"><data><shape><p>Second</p></shape></data></slide>'
            '<slide id="p3"><data><shape><p>Excluded</p></shape></data></slide>'
        )
        output = self.content("--slide-id", "p2", "p1", "--slide-id", "p2")
        self.assertLess(output.index('id="p2"'), output.index('id="p1"'))
        self.assertEqual(output.count('## slide 2 id="p2"'), 1)
        self.assertNotIn("Excluded", output)

    def test_missing_or_ambiguous_selection_fails_without_partial_content(self) -> None:
        self.write_slides(
            '<slide id="p1"><data><shape><p>First</p></shape></data></slide>'
            '<slide id="dup"><data/></slide><slide id="dup"><data/></slide>'
        )
        for mode in ("content", "raw"):
            for selected in ("missing", "dup"):
                with self.subTest(mode=mode, selected=selected):
                    completed = self.run_cli("--mode", mode, "--slide-id", "p1", selected)
                    self.assertEqual(completed.returncode, 2)
                    self.assertIn(selected, completed.stderr)
                    self.assertEqual(completed.stdout, "")

    def test_content_mode_with_single_slide_root(self) -> None:
        self.input_path.write_text(
            f'<slide xmlns="{NAMESPACE}" id="single"><data>'
            '<shape id="body"><p>Only page</p></shape></data></slide>', encoding="utf-8"
        )
        output = self.content()
        completed = self.run_cli("--mode", "content", "--slide-id", "single")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, output)
        self.assertIn('## slide 1 id="single"', output)

    def test_long_text_is_complete_and_speaker_notes_are_excluded(self) -> None:
        body = "正文" * 2000 + "正文最后指标40%"
        note = "演讲者备注" * 600 + "讲稿最后指标20%"
        self.write_slides(
            f'<slide id="p1"><data><shape id="body"><p>{body}</p></shape></data>'
            f'<note><p>{note}</p></note></slide>'
        )
        for args in ((), ("--slide-id", "p1")):
            output = self.content(*args)
            self.assertIn(body, output)
            self.assertNotIn("讲稿最后指标20%", output)
            self.assertNotIn("[note]", output)
            self.assertNotIn("…", output)
        raw = self.run_cli("--mode", "raw", "--slide-id", "p1")
        self.assertEqual(raw.returncode, 0, raw.stderr)
        self.assertIn(note, json.loads(raw.stdout)["slides"][0]["raw_xml"])

    def test_mixed_text_and_line_breaks_keep_all_text_in_order(self) -> None:
        self.write_slides(
            '<slide id="p1"><data><shape id="mixed"><content>'
            '前缀<p>Q1<br/>40% <span>营收</span></p>中间'
            '<p>次段 &quot;引号&quot;</p>后缀'
            '</content></shape></data></slide>'
        )
        output = self.content()
        self.assertIn('[shape id="mixed"]', output)
        ordered = ["前缀", "Q1", "40%", "营收", "中间", "次段", "后缀"]
        positions = [output.index(item) for item in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("Q140%", output)
        self.assertIn(r"Q1\n40%", output)
        self.assertIn(r'\"引号\"', output)

    def test_table_keeps_empty_cells_merges_and_explicit_colors(self) -> None:
        self.write_slides(
            '<slide id="p1"><data><table id="table1"><tr>'
            '<td id="cell1" colSpan="2" rowSpan="2">'
            '<fill><fillColor color="rgb(10,20,30)"/></fill>'
            '<content color="rgb(200,210,220)"><p>  A  B  </p></content></td>'
            '<td id="empty"><content><p/></content></td></tr>'
            '<tr><td id="cell2"><content><p>40%</p></content></td></tr>'
            '</table></data></slide>'
        )
        output = self.content()
        self.assertIn('[table id="table1"]', output)
        first = next(line for line in output.splitlines() if "r1c1" in line)
        self.assertIn('id="cell1"', first)
        self.assertIn('colSpan="2"', first)
        self.assertIn('rowSpan="2"', first)
        self.assertIn("rgb(10,20,30)", first)
        self.assertIn("rgb(200,210,220)", first)
        self.assertIn("A  B", first)
        empty = next(line for line in output.splitlines() if 'id="empty"' in line)
        self.assertIn('""', empty)
        self.assertIn("40%", output)

    def test_chart_preserves_field_names_values_units_and_formats(self) -> None:
        self.write_slides(
            '<slide id="p1"><data><chart id="c1">'
            '<chartTitle>季度营收</chartTitle><chartPlotArea>'
            '<chartPlot type="column"><chartLabels format="0%"/></chartPlot>'
            '</chartPlotArea><chartData><dim1>'
            '<chartField name="季度" valueType="string">Q1,Q2,Q3,Q4</chartField>'
            '</dim1><dim2><chartField name="营收" valueType="number" unit="万元">'
            '52,48,55,68<chartParsedValues>52,48,55,68</chartParsedValues>'
            '</chartField></dim2></chartData></chart></data></slide>'
        )
        output = self.content()
        self.assertIn('[chart id="c1"]', output)
        for expected in ("季度营收", "季度", "Q1,Q2,Q3,Q4", "营收", "52,48,55,68", "万元", "0%"):
            self.assertIn(expected, output)
        self.assertEqual(output.count("52,48,55,68"), 1)

    def test_nontext_objects_remain_visible_without_svg_path_or_decoration_styles(self) -> None:
        self.write_slides(
            '<slide id="p1"><data>'
            '<embed id="svg1"><svg xmlns="http://www.w3.org/2000/svg">'
            '<style>.hiddenCss{fill:red;}</style><defs><text>hidden legend</text></defs>'
            '<path d="M0 0H48V48H0Z"/></svg></embed>'
            '<undefined id="unknown1" type="chart_refer_host_perm"/>'
            '<img id="image1"/><icon id="icon1"/><line id="line1"/>'
            '<shape id="decor" type="rect" width="123.456" fontSize="22">'
            '<fill><fillColor color="rgb(91,92,93)"/></fill></shape>'
            '<customObject id="custom1"/></data></slide>'
        )
        output = self.content()
        for tag, block_id in (("embed", "svg1"), ("undefined", "unknown1"), ("img", "image1"),
                              ("icon", "icon1"), ("line", "line1"), ("shape", "decor"),
                              ("customObject", "custom1")):
            self.assertRegex(output, rf'\[{tag} id="{block_id}"(?:\s[^\]\n]*)?\]')
        self.assertIn('type="chart_refer_host_perm"', output)
        self.assertIn("raw", output.lower())
        self.assertNotIn("M0 0H48V48H0Z", output)
        self.assertNotIn("rgb(91,92,93)", output)
        self.assertNotIn("123.456", output)
        self.assertNotIn("hiddenCss", output)
        self.assertNotIn("hidden legend", output)

    def test_unrecognized_table_and_chart_are_not_silently_empty(self) -> None:
        self.write_slides(
            '<slide id="p1"><data><table id="t1"><rows><cell>表格数据40%</cell></rows></table>'
            '<chart id="c1"><data>图表数据20%</data></chart></data></slide>'
        )
        output = self.content()
        for expected in ('[table id="t1"]', '[chart id="c1"]', '表格数据40%', '图表数据20%', 'raw XML'):
            self.assertIn(expected, output)

    def test_content_output_saves_text_and_reports_success_json(self) -> None:
        self.write_slides('<slide id="p1"><data><shape><p>保存正文</p></shape></data></slide>')
        output_path = Path(self.temp_dir.name) / "subdir" / "content.txt"
        completed = self.run_cli("--mode", "content", "--output", str(output_path))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["mode"], "content")
        self.assertEqual(report["output_slide_count"], 1)
        self.assertIn("保存正文", output_path.read_text(encoding="utf-8"))

    def test_summary_keeps_json_interface_and_marks_truncated_previews(self) -> None:
        self.write_slides(
            '<slide id="p1"><data><shape id="b1"><p>' + "长文" * 300 + '</p></shape>'
            '<embed id="svg1"/><undefined id="u1"/></data><note>' + "备注" * 300 + '</note></slide>'
            '<slide id="p2"><data><shape><p>短文</p></shape></data></slide>'
        )
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["mode"], "summary")
        self.assertEqual(result["presentation"]["slide_count"], 2)
        self.assertEqual(set(result["usage_hints"]), {"content", "raw"})
        self.assertTrue(all("usage_hints" not in slide for slide in result["slides"]))
        page = result["slides"][0]
        self.assertEqual(page["counts"]["embeds"], 1)
        self.assertEqual(page["tag_counts"]["undefined"], 1)
        self.assertTrue(page["text_preview_truncated"])
        self.assertTrue(page["note_preview_truncated"])
        self.assertFalse(result["slides"][1]["text_preview_truncated"])
        self.assertLessEqual(len(page["text_preview"]), xml_inspect.PREVIEW_LENGTH)

    def test_speaker_note_preview_warning_points_to_raw_xml(self) -> None:
        self.write_slides(
            '<slide id="p1"><data><shape><p>短文</p></shape></data><note>'
            + "演讲者备注" * 300 + '</note></slide>'
        )
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result['slides'][0]['note_preview_truncated'])
        self.assertFalse(result['slides'][0]['text_preview_truncated'])
        warning = next(w for w in result['summary']['warnings'] if '演讲者备注' in w)
        self.assertIn('--mode raw', warning)
        self.assertNotIn('--content', warning)

    def test_all_modes_support_output_and_only_content_raw_support_selection(self) -> None:
        self.write_slides(
            '<slide id="p1"><data><shape><p>First</p></shape></data></slide>'
            '<slide id="p2"><data><shape><p>Second</p></shape></data></slide>'
            '<slide id="p3"><data><shape><p>Excluded</p></shape><undefined id="u3"/></data></slide>'
        )
        for mode in ("summary", "content", "raw"):
            for select in ((False,) if mode == "summary" else (False, True)):
                for save in (False, True):
                    with self.subTest(mode=mode, select=select, save=save):
                        args = ["--mode", mode]
                        expected = [(2, "p2"), (1, "p1")] if select else [(1, "p1"), (2, "p2"), (3, "p3")]
                        if select:
                            args += ["--slide-id", "p2", "p1", "--slide-id", "p2"]
                        output_path = Path(self.temp_dir.name) / "saved" / f"{mode}-{select}.out"
                        if save:
                            args += ["--output", str(output_path)]
                        completed = self.run_cli(*args)
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        output = completed.stdout
                        if save:
                            status = json.loads(output)
                            self.assertEqual(status["mode"], mode)
                            self.assertEqual(status["presentation_slide_count"], 3)
                            self.assertEqual(status["output_slide_count"], len(expected))
                            output = output_path.read_text(encoding="utf-8")
                        if mode == "content":
                            actual = [(int(i), json.loads(sid)) for i, sid in
                                      re.findall(r'^## slide (\d+) id=(.+)$', output, re.MULTILINE)]
                        else:
                            report = json.loads(output)
                            self.assertEqual(report["mode"], mode)
                            self.assertEqual(report["presentation"]["slide_count"], 3)
                            self.assertEqual(report["selection"]["output_slide_count"], len(expected))
                            actual = [(s["index"], s["slide_id"]) for s in report["slides"]]
                            if mode == "summary":
                                self.assertEqual(report["summary"]["blocks"], 4)
                                self.assertEqual(report["summary"]["undefined"], 1)
                            else:
                                self.assertTrue(all("<slide" in s["raw_xml"] for s in report["slides"]))
                        self.assertEqual(actual, expected)

    def test_summary_is_default_and_rejects_page_selection(self) -> None:
        self.write_slides('<slide id="p1"><data/></slide><slide id="p2"><data/></slide>')
        default = self.run_cli()
        explicit = self.run_cli("--mode", "summary")
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(default.stdout, explicit.stdout)
        report = json.loads(default.stdout)
        self.assertEqual(report["mode"], "summary")
        self.assertEqual([s["slide_id"] for s in report["slides"]], ["p1", "p2"])
        output_path = Path(self.temp_dir.name) / "rejected.json"
        for mode_args in ((), ("--mode", "summary")):
            with self.subTest(mode_args=mode_args):
                completed = self.run_cli(*mode_args, "--slide-id", "p2", "--output", str(output_path))
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertIn("--slide-id", completed.stderr)
                self.assertIn("--mode content", completed.stderr)
                self.assertIn("--mode raw", completed.stderr)
                self.assertFalse(output_path.exists())

    def test_invalid_modes_and_removed_content_flags_fail_clearly(self) -> None:
        self.write_slides('<slide id="p1"><data/></slide>')
        for args in (("--mode", "invalid"), ("--content",), ("--content-only",)):
            with self.subTest(args=args):
                completed = self.run_cli(*args)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertIn("--mode", completed.stderr)


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
                [sys.executable, str(script_path), "--input", str(input_path), "--mode", "raw", "--slide-id", "p01"],
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
