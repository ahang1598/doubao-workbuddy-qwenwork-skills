#!/usr/bin/env python3
"""组织清单校验降级的可见性与 schema 发现回归。

背景（2026-08-07 诊断）：`jsonschema` 缺失时校验会降级为 minimal_validate，
但输出与「完整校验且零错误」完全一样——属静默降级，与技能 D1-S5 断言
「禁止错误格式清单静默注入」冲突。追查时又发现两处叠加缺陷：
  1. schema 路径写死为出处技能的旧目录名，改名迁移后全部落空 → 完整校验成死代码；
  2. 该 schema 带 UTF-8 BOM，load_json 用 utf-8 读会抛错并被 except 吞掉。

运行：python3 tests/test_checklist_validation.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import checklist_schema  # noqa: E402
import load_org_checklist as loader  # noqa: E402


class LoadJsonBomTest(unittest.TestCase):
    def test_bom_file_loads(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "with_bom.json"
            target.write_text('{"a": 1}', encoding="utf-8-sig")
            self.assertEqual(loader.load_json(target), {"a": 1},
                             "带 BOM 的 JSON 必须能读（出处技能导出的 schema 即带 BOM）")

    def test_plain_utf8_still_loads(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "plain.json"
            target.write_text('{"a": 1}', encoding="utf-8")
            self.assertEqual(loader.load_json(target), {"a": 1})

    def test_non_object_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "arr.json"
            target.write_text("[1,2]", encoding="utf-8")
            with self.assertRaises(ValueError):
                loader.load_json(target)


class SchemaDiscoveryTest(unittest.TestCase):
    """schema 应按文件名发现，不依赖出处技能的目录名。"""

    def test_env_override_wins(self) -> None:
        import os
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            (d / "iterms-checklist-v2.json").write_text("{}", encoding="utf-8")
            old = os.environ.get("RICHEE_CHECKLIST_SCHEMA_DIR")
            os.environ["RICHEE_CHECKLIST_SCHEMA_DIR"] = str(d)
            try:
                found = loader.discover_schema("iterms")
                self.assertEqual(found, d / "iterms-checklist-v2.json")
            finally:
                os.environ.pop("RICHEE_CHECKLIST_SCHEMA_DIR", None)
                if old is not None:
                    os.environ["RICHEE_CHECKLIST_SCHEMA_DIR"] = old

    def test_unknown_format_returns_none(self) -> None:
        self.assertIsNone(loader.discover_schema("nonexistent-format"))


class ValidationModeVisibilityTest(unittest.TestCase):
    """降级必须显式可见，不能与完整校验返回同样结果。"""

    ITERMS = {
        "checklist_id": "CL-T-001", "schema_version": "iterms-2.0",
        "business_type": "采购合同", "position": "甲方（买方）",
        "scope": "library", "version": "1.0.0",
        "data": [{"group": "g", "review_items": []}],
    }

    def test_no_schema_reports_minimal_mode(self) -> None:
        errors, advisory, mode = loader.validate_payload(self.ITERMS, None, "iterms")
        self.assertEqual(errors, [])
        self.assertEqual(advisory, [])
        self.assertEqual(mode, "minimal_no_schema")

    def test_mode_distinguishes_reasons(self) -> None:
        """两种降级原因必须可区分——补 schema 与装依赖是不同的补救动作。"""
        self.assertNotEqual("minimal_no_schema", "minimal_no_jsonschema")

    def test_minimal_validate_does_not_check_rule_bodies(self) -> None:
        """记录 minimal 模式的真实覆盖面：data[] 内部结构不校验。"""
        payload = dict(self.ITERMS, data=[{"完全不合规的键": 123}])
        errors = loader.minimal_validate(payload, "iterms")
        self.assertEqual(errors, [],
                         "minimal 模式确实放过畸形规则体——故降级必须对外可见")

    def test_minimal_still_catches_top_level_breakage(self) -> None:
        for broken, why in (
            (dict(self.ITERMS, data=[]), "data 空数组"),
            ({k: v for k, v in self.ITERMS.items() if k != "checklist_id"}, "缺必填字段"),
            (dict(self.ITERMS, schema_version="iterms-9.9"), "schema_version 不符"),
        ):
            with self.subTest(why=why):
                self.assertTrue(loader.minimal_validate(broken, "iterms"))




SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["checklist_id", "data"],
    "properties": {
        "checklist_id": {"type": "string", "minLength": 3, "pattern": "^CL-"},
        "schema_version": {"const": "iterms-2.0"},
        "count": {"type": "integer", "minimum": 1},
        "kind": {"enum": ["a", "b"]},
        "source_meta": {"type": "object", "required": ["generator"],
                        "additionalProperties": False,
                        "properties": {"generator": {"type": "string"}}},
        "data": {"type": "array", "minItems": 1,
                 "items": {"$ref": "#/$defs/rule"}},
    },
    "additionalProperties": True,
    "$defs": {"rule": {"type": "object", "required": ["group"],
                       "properties": {"group": {"type": "string"}}}},
}

GOOD = {"checklist_id": "CL-1", "schema_version": "iterms-2.0", "count": 3,
        "kind": "a", "source_meta": {"generator": "g"},
        "data": [{"group": "G1"}]}


class NativeValidatorTest(unittest.TestCase):
    """零依赖校验器：覆盖本 schema 实际用到的 14 个关键字。"""

    def test_valid_payload_passes(self) -> None:
        errors, unsupported = checklist_schema.validate(GOOD, SCHEMA)
        self.assertEqual(errors, [])
        self.assertEqual(unsupported, [])

    def test_each_keyword_catches_its_violation(self) -> None:
        cases = [
            ({**GOOD, "checklist_id": 1}, "类型"),          # type
            ({**GOOD, "checklist_id": "X-1"}, "模式"),      # pattern
            ({**GOOD, "checklist_id": "CL"}, "长度"),       # minLength
            ({**GOOD, "schema_version": "iterms-9"}, "值应为"),  # const
            ({**GOOD, "kind": "z"}, "之一"),                # enum
            ({**GOOD, "count": 0}, "≥"),                    # minimum
            ({**GOOD, "data": []}, "元素数"),               # minItems
            ({k: v for k, v in GOOD.items() if k != "data"}, "必填"),  # required
            ({**GOOD, "source_meta": {"generator": "g", "x": 1}}, "额外字段"),  # addlProps
            ({**GOOD, "data": [{"noGroup": 1}]}, "必填"),   # $ref → $defs
        ]
        for payload, expect in cases:
            with self.subTest(expect=expect):
                errors, _ = checklist_schema.validate(payload, SCHEMA)
                self.assertTrue(errors, f"应报错但未报: {expect}")
                self.assertTrue(any(expect in e for e in errors),
                                f"错误信息应含「{expect}」，实际: {errors}")

    def test_bool_is_not_integer(self) -> None:
        """JSON Schema 中布尔不是数字；Python 里 bool 是 int 子类，易误放行。"""
        errors, _ = checklist_schema.validate({**GOOD, "count": True}, SCHEMA)
        self.assertTrue(errors)

    def test_unknown_keyword_is_reported_not_ignored(self) -> None:
        """能力边界必须可见——静默跳过就是本轮要消灭的那类缺陷。"""
        schema = {"type": "object", "oneOf": [{"required": ["a"]}]}
        _, unsupported = checklist_schema.validate({"a": 1}, schema)
        self.assertIn("oneOf", unsupported)

    def test_format_is_annotation_not_asserted(self) -> None:
        """format 按规范默认只作注解，不应计入 unsupported。"""
        schema = {"type": "string", "format": "date-time"}
        errors, unsupported = checklist_schema.validate("not-a-date", schema)
        self.assertEqual(errors, [])
        self.assertEqual(unsupported, [])


class ImpactSplitTest(unittest.TestCase):
    """按影响面分层：data[] 内错误阻断，元数据漂移只提示。

    实测 6 份真实清单中有 2 份仅因 source_meta 字段漂移而不合格；
    若一律阻断，会让在用清单加载失败（1/3 的回归）。
    """

    def test_data_errors_block(self) -> None:
        blocking, advisory = loader.split_by_impact(
            ["data/0/group: 类型应为 string", "source_meta: 缺少必填字段 generator"])
        self.assertEqual(len(blocking), 1)
        self.assertIn("data/0/group", blocking[0])
        self.assertEqual(len(advisory), 1)

    def test_metadata_only_does_not_block(self) -> None:
        blocking, advisory = loader.split_by_impact(
            ["source_meta: 不允许的额外字段 reviewer"])
        self.assertEqual(blocking, [])
        self.assertEqual(len(advisory), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
