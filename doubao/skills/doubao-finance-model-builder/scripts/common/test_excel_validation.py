#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from portable_workbook_audit import inspect_workbook_structure, lint_formula


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


if __name__ == "__main__":
    unittest.main()
