#!/usr/bin/env python3

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from portable_workbook_audit import Recalculation, audit_contract, inspect_workbook_structure, lint_formula, sha256_file


class ExcelValidationTests(unittest.TestCase):
    def test_lint_rejects_non_excel_assignment_operators(self):
        errors, warnings = lint_formula(
            "=A1+=B1-=C1",
            sheet_names=["Sheet1"],
            forbidden_functions=[],
            warn_functions=[],
        )
        self.assertTrue(any("非Excel运算符" in item for item in errors))
        self.assertEqual(warnings, [])

    def test_lint_checks_sheet_and_function_policy(self):
        errors, warnings = lint_formula(
            "=WEBSERVICE('Missing Sheet'!A1)+OFFSET(A1,1,0)",
            sheet_names=["Sheet1"],
            forbidden_functions=["WEBSERVICE"],
            warn_functions=["OFFSET"],
        )
        self.assertTrue(any("不存在的工作表" in item for item in errors))
        self.assertTrue(any("禁用函数" in item for item in errors))
        self.assertTrue(any("难审计函数" in item for item in warnings))

    def test_structure_profile_captures_hidden_and_validation_metadata(self):
        from openpyxl.worksheet.datavalidation import DataValidation

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "模型"
            sheet["A1"] = 1
            sheet["B1"] = "=A1+1"
            sheet.row_dimensions[2].hidden = True
            sheet.column_dimensions["C"].hidden = True
            validation = DataValidation(type="list", formula1='"PASS,FAIL"')
            sheet.add_data_validation(validation)
            validation.add("D1")
            workbook.save(path)
            workbook.close()

            profile = inspect_workbook_structure(path)
            model = profile["sheets"][0]
            self.assertEqual(profile["formula_count"], 1)
            self.assertEqual(model["formula_cells"], ["B1"])
            self.assertEqual(model["hidden_rows"], [2])
            self.assertEqual(model["hidden_columns"], ["C"])
            self.assertEqual(model["data_validations"][0]["type"], "list")

    def test_reuses_supplied_recalculation_and_exports_original_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            original = root / "model.xlsx"
            cached = root / "recalculated.xlsx"
            workbook = Workbook()
            workbook.active["A1"] = 1
            workbook.active["B1"] = "=A1+1"
            workbook.save(original)
            workbook.active["A1"] = 2
            workbook.save(cached)
            workbook.close()
            recalculation = Recalculation("SUCCESS", "test", cached, temp_root=root)
            contract = {"workflow": "test", "required_sheets": ["Sheet"], "formula_ranges": [], "key_outputs": []}
            snapshot = root / "workbook-inspect.json"

            with patch("portable_workbook_audit.recalculate_with_libreoffice") as recalculate:
                result = audit_contract(original, contract, recalculation=recalculation, inspect_output=snapshot)
                recalculate.assert_not_called()

            self.assertEqual(result["status"], "PASS")
            self.assertTrue(cached.is_file())
            self.assertEqual(
                json.loads(snapshot.read_text(encoding="utf-8"))["artifact_sha256"], sha256_file(original),
            )
            self.assertNotEqual(sha256_file(original), sha256_file(cached))

    def test_three_statement_checks_share_recalculation_and_reject_bad_dividend(self):
        script = Path(__file__).resolve().parents[1] / "three-statements" / "audit_three_statements_workbook.py"
        spec = importlib.util.spec_from_file_location("three_statements_audit", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            original = root / "model.xlsx"
            workbook = Workbook()
            workbook.remove(workbook.active)
            for name in module.REQUIRED_SHEETS:
                workbook.create_sheet(name)
            workbook["检查"]["B2"] = '=IF(COUNTIF(G4:G4,"失败")=0,"PASS","FAIL")'
            workbook["现金流量表"]["A1"] = "cfs.dividends"
            workbook["现金流量表"]["B1"] = 1
            workbook.save(original)
            workbook.close()
            scratch = root / "recalculation"
            scratch.mkdir()
            recalculation = Recalculation("SUCCESS", "test", original, temp_root=scratch)
            output = root / "artifact-audit.json"
            snapshot = root / "workbook-inspect.json"

            with (
                patch.object(module, "recalculate_with_libreoffice", return_value=recalculation) as recalculate,
                patch("portable_workbook_audit.recalculate_with_libreoffice") as duplicate_recalculate,
                patch.object(sys, "argv", [str(script), str(original), str(output), "--recalculate", "required",
                                          "--inspect-output", str(snapshot)]),
                patch("builtins.print"),
                self.assertRaises(SystemExit) as exit_result,
            ):
                module.main()

            self.assertEqual(exit_result.exception.code, 1)
            recalculate.assert_called_once()
            duplicate_recalculate.assert_not_called()
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(any("支付股利为正现金流" in error for error in result["errors"]))
            self.assertTrue(snapshot.is_file())
            self.assertFalse(scratch.exists())


if __name__ == "__main__":
    unittest.main()
