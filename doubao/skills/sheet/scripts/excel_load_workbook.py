"""Editable xlsx reader preserving rich runs and literal x005F_ text.

openpyxl 3.1.5 removes x005F_ unconditionally in its rich-text reader.
Read shared strings without that replacement, and restore affected inline
strings from the same source snapshot before returning the workbook. This
does not extend openpyxl's support for other workbook features.
"""
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from types import MethodType
import re
from zipfile import ZIP64_LIMIT, ZIP_DEFLATED, ZipFile

from openpyxl import LXML, Workbook
from openpyxl.cell.cell import Cell
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import Text
from openpyxl.reader.excel import ExcelReader
from openpyxl.utils.cell import coordinate_to_tuple
from openpyxl.worksheet._reader import WorkSheetParser
from openpyxl.writer.excel import ExcelWriter
from openpyxl.xml.constants import SHARED_STRINGS, SHEET_MAIN_NS
from openpyxl.xml.functions import iterparse

NS = "{" + SHEET_MAIN_NS + "}"
XSTRING_ESCAPE = re.compile(r"_[xX][0-9A-Fa-f]{4}_")


def _check_text(node):
    # Decoding escaped text requires a matching writer. Do not expose XML escape
    # spellings as business values, or silently change their meaning on save.
    texts = [t.text or "" for t in node.iter(NS + "t")]
    if any(XSTRING_ESCAPE.search(t) for t in texts + ["".join(texts)]):
        raise RuntimeError("源文本含 OOXML 特殊转义，此加载器不能保证无损编辑；"
                           "尚未保存，请保留源文件并说明未完成部分，不要改用有损加载方式")


def _read_text(node):
    """Retain the source XML text and run properties; do not strip substrings."""
    _check_text(node)
    text = Text.from_tree(node)
    if text.t is not None:
        return text.t
    runs = [TextBlock(run.rPr, run.t or "") if run.rPr else (run.t or "")
            for run in text.r]
    if not runs:
        return ""
    if len(runs) == 1 and isinstance(runs[0], str):
        return runs[0]
    return CellRichText(runs)


class _InlineTextParser(WorkSheetParser):
    def parse_cell(self, element):
        """Locate affected inline text without interpreting formulas or numbers."""
        # Reuse parse_row's row/cell counter semantics, including omitted r.
        coordinate = element.get("r")
        if coordinate:
            row, column = coordinate_to_tuple(coordinate)
            self.col_counter = column
        else:
            self.col_counter += 1
            row, column = self.row_counter, self.col_counter
        if element.get("t") != "inlineStr" or element.find(NS + "f") is not None:
            return None
        node = element.find(NS + "is")
        if node is not None:
            _check_text(node)
            if any("x005F_" in (t.text or "") for t in node.iter(NS + "t")):
                return row, column, _read_text(node)
        return None


class _LiteralTextReader(ExcelReader):
    def read_strings(self):
        """Read shared strings in index order without removing literal text."""
        part = self.package.find(SHARED_STRINGS)
        if part is not None:
            with self.archive.open(part.PartName.lstrip("/")) as source:
                for _, node in iterparse(source):
                    if node.tag == NS + "si":
                        self.shared_strings.append(_read_text(node))
                        node.clear()

    def read_worksheets(self):
        """Bind worksheets, then restore affected inline text before returning."""
        super().read_worksheets()
        for sheet, rel in self.parser.find_sheets():
            if not rel.Type.endswith("/worksheet"):
                continue
            ws = self.wb[sheet.name]
            with self.archive.open(rel.target) as source:
                parser = _InlineTextParser(source, self.shared_strings)
                for _, cells in parser.parse():
                    for item in cells:
                        if item is None:
                            continue
                        row, column, value = item
                        cell = ws._cells.get((row, column))
                        if not isinstance(cell, Cell) or cell.data_type != "s":
                            raise RuntimeError("无法无损恢复源单元格文本：{}!{}:{}".format(sheet.name, row, column))
                        # Avoid Cell.value's formula/error inference and truncation.
                        cell._value = value


class _WorksheetArchive(ZipFile):
    def write(self, filename, arcname=None, compress_type=None, compresslevel=None):
        if arcname and arcname.startswith("xl/worksheets/") and arcname.endswith(".xml"):
            # The standard library writer emits raw CR in XML text, which XML readers normalize.
            replacement = b"&#13;"
            needs_zip64 = Path(filename).stat().st_size * len(replacement) > ZIP64_LIMIT
            with open(filename, "rb") as source, self.open(arcname, "w", force_zip64=needs_zip64) as output:
                for chunk in iter(lambda: source.read(64 * 1024), b""):
                    output.write(chunk.replace(b"\r", replacement))
        else:
            super().write(filename, arcname, compress_type, compresslevel)


def _save_preserving_text(workbook, filename):
    """Keep explicit empty strings and carriage returns through serialization."""
    empty_cells = []
    try:
        for ws in workbook.worksheets:
            for cell in ws._cells.values():
                value = cell._value
                if cell.data_type == "s" and isinstance(value, str) and value == "":
                    empty_cells.append((cell, value))
                    # openpyxl otherwise writes a bare cell that reloads as None.
                    cell._value = CellRichText()
        if LXML:
            Workbook.save(workbook, filename)
        else:
            with _WorksheetArchive(filename, "w", ZIP_DEFLATED) as archive:
                workbook.properties.modified = datetime.now(timezone.utc).replace(tzinfo=None)
                ExcelWriter(workbook, archive).save()
    finally:
        for cell, value in empty_cells:
            cell._value = value


def load_workbook(filename):
    """Load an editable .xlsx with formulas, links, rich text and literal text.

    OOXML _xHHHH_ escape sequences are rejected before returning any workbook;
    they require a compatible decoder/writer pair beyond this narrow fix.
    The returned workbook's save method retains explicit empty strings and carriage returns.

    Usage from the skill directory:
        from scripts.excel_load_workbook import load_workbook
        wb = load_workbook('./source.xlsx')
        wb['明细'].column_dimensions['A'].width = 20
        wb.save('./edited.xlsx')
    """
    path = Path(filename)
    if path.suffix.lower() != ".xlsx":
        raise ValueError("此加载器只支持 .xlsx；.xls 请先完整转换为 .xlsx")
    # Both passes read the same bytes, even if the source path changes meanwhile.
    with BytesIO(path.read_bytes()) as snapshot:
        reader = _LiteralTextReader(snapshot, read_only=False, keep_vba=False,
                                    data_only=False, keep_links=True, rich_text=True)
        try:
            reader.read()
            reader.wb.save = MethodType(_save_preserving_text, reader.wb)
            return reader.wb
        finally:
            reader.archive.close()
