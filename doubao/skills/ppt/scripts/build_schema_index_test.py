# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_schema_index


SCRIPT_PATH = Path(__file__).resolve().with_name("build_schema_index.py")


class BuildSchemaIndexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_schema_index.SchemaIndex(build_schema_index.DEFAULT_SCHEMA)
        cls.content = build_schema_index.render_index(cls.index)

    def test_committed_index_is_in_sync(self) -> None:
        """The committed index must equal a fresh render — i.e. `--check` passes."""
        current = build_schema_index.DEFAULT_OUTPUT.read_text(encoding="utf-8")
        self.assertEqual(
            current,
            self.content,
            "slides_xml_schema_index.md 已过期，请运行 python3 scripts/build_schema_index.py",
        )

    def test_render_is_deterministic(self) -> None:
        again = build_schema_index.render_index(build_schema_index.SchemaIndex(build_schema_index.DEFAULT_SCHEMA))
        self.assertEqual(self.content, again)

    def test_inherited_attributes_are_expanded(self) -> None:
        shape = next(item for item in self.index.elements if item.name == "shape")
        attr_names = {a.name for a in self.index.attributes(shape.complex_type)}
        # topLeftX/width come from a base type via extension.
        self.assertIn("topLeftX", attr_names)
        self.assertIn("width", attr_names)

    def test_enum_values_are_inlined(self) -> None:
        self.assertIn("bent-connector3", self.content)
        self.assertIn("slides-full-round-rect", self.content)

    def test_chinese_aliases_are_present(self) -> None:
        self.assertIn("折线连接符", self.content)
        self.assertIn("中文检索词", self.content)

    def test_runtime_only_constraints_are_present(self) -> None:
        # These are not in the XSD; grep of the raw XSD would never find them.
        self.assertIn("不得越出 viewBox", self.content)

    def test_transition_index_exposes_only_supported_authoring_surface(self) -> None:
        transition = self.content.split("## `<transition>`", 1)[1].split("\n## `<", 1)[0]
        for value in ("fade", "cover", "pull", "push", "none"):
            self.assertIn(value, transition)
        for unsupported in (
            "cut",
            "slides-flip",
            "wipe",
            "orientation",
            "morphMode",
            "invX",
            "invY",
        ):
            self.assertNotIn(unsupported, transition)
        self.assertIn("生成页面可用属性", transition)

    def test_parent_elements_are_resolved(self) -> None:
        # `出现场景` gives the XSD lexical scope; `父元素` must give the real
        # parent tags that can contain the element (reverse content model).
        self.assertIn("data", self.index.parents_by_name["shape"])
        self.assertIn("content", self.index.parents_by_name["p"])
        # And it must surface in the rendered index as a `父元素` line.
        self.assertIn("- 父元素：", self.content)

    def test_content_model_preserves_repeatable_choice(self) -> None:
        # <p> inline children live in a choice maxOccurs="unbounded"; the index
        # must not flatten them into "每种一个", which would mislead the model.
        p = next(item for item in self.index.elements if item.name == "p")
        model = self.index.content_model(p.complex_type)
        self.assertIn("选择其一", model)
        self.assertIn("unbounded", model)

    def test_every_generated_example_is_well_formed_xml(self) -> None:
        for element in self.index.elements:
            with self.subTest(element=element.name, type=element.type_name):
                parsed = ET.fromstring(build_schema_index.example_for(self.index, element))
                self.assertEqual(parsed.tag, element.name)

    def test_check_mode_passes_against_committed_file(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--check"],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
