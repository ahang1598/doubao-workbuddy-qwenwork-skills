"""校验专用读包：文本解码一次，可保留数值原文，公式与单元格类型不变。"""
from __future__ import annotations

import posixpath
import re
import zipfile
from decimal import Decimal
from xml.etree import ElementTree as ET

from openpyxl import load_workbook as _load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.utils.cell import coordinate_to_tuple

XSTRING_RE = re.compile(r"_x([0-9A-Fa-f]{4})_")
SURROGATE_RE = re.compile(r"[\ud800-\udfff]")


def decode_xstring(text):
    """保护下划线的序列不递归解码；UTF-16 代理对合成原字符。"""
    result = XSTRING_RE.sub(lambda match: chr(int(match.group(1), 16)), text)
    if SURROGATE_RE.search(result):
        result = result.encode("utf-16-le", "surrogatepass").decode("utf-16-le")
    return result


def _text_content(element, ns):
    # 每个 t 独立解码再拼接，不把跨 run 的普通文本拼成新的转义；忽略 rPh 注音。
    parts = []
    needs_override = False
    for child in element:
        text_node = child if child.tag == ns + "t" else child.find(ns + "t") if child.tag == ns + "r" else None
        if text_node is None:
            continue
        raw = text_node.text or ""
        needs_override |= bool(XSTRING_RE.search(raw) or "x005F_" in raw)
        parts.append(decode_xstring(raw))
    value = "".join(parts)
    # openpyxl 会在拼接后的 shared string 上删除 x005F_，该片段也可能跨 run。
    return value, needs_override or "x005F_" in value


def _part(base, target):
    return target.lstrip("/") if target.startswith("/") else posixpath.normpath(
        posixpath.join(posixpath.dirname(base), target))


def _parts(package):
    book_part = "xl/workbook.xml"
    if "_rels/.rels" in package.namelist():
        for rel in ET.fromstring(package.read("_rels/.rels")):
            if rel.get("Type", "").endswith("/officeDocument"):
                book_part = _part("", rel.attrib["Target"])
                break
    rel_path = posixpath.join(posixpath.dirname(book_part), "_rels", posixpath.basename(book_part) + ".rels")
    rels = {rel.attrib["Id"]: rel.attrib for rel in ET.fromstring(package.read(rel_path))}
    shared = next((_part(book_part, rel["Target"]) for rel in rels.values()
                   if rel.get("Type", "").endswith("/sharedStrings") and rel.get("TargetMode") != "External"), None)
    workbook = ET.fromstring(package.read(book_part))
    ns = workbook.tag.rpartition("}")[0] + "}"
    sheets = {}
    for sheet in workbook.findall(ns + "sheets/" + ns + "sheet"):
        rid = next(value for key, value in sheet.attrib.items() if key.endswith("}id"))
        rel = rels[rid]
        if rel.get("Type", "").endswith("/worksheet") and rel.get("TargetMode") != "External":
            sheets[sheet.attrib["name"]] = _part(book_part, rel["Target"])
    return shared, sheets


def _shared_overrides(package, part):
    overrides = {}
    if part is None:
        return overrides
    with package.open(part) as stream:
        events = ET.iterparse(stream, events=("start", "end"))
        _event, root = next(events)
        ns = root.tag.rpartition("}")[0] + "}"
        index = 0
        for event, node in events:
            if event == "end" and node.tag == ns + "si":
                value, needed = _text_content(node, ns)
                if needed:
                    overrides[index] = value
                index += 1
                root.clear()
    return overrides


def _cell_text_override(node, ns, shared):
    kind = node.get("t")
    if kind == "s":
        raw_index = node.findtext(ns + "v")
        if raw_index:
            index = int(raw_index)
            return shared.get(index), index in shared
    elif kind == "inlineStr":
        inline = node.find(ns + "is")
        if inline is not None:
            return _text_content(inline, ns)
    elif kind == "str":
        raw = node.findtext(ns + "v", "")
        if XSTRING_RE.search(raw):
            return decode_xstring(raw), True
    return None, False


def _record_number(node, ns, coord, numbers):
    if numbers is None or node.get("t", "n") != "n":
        return
    raw = node.findtext(ns + "v")
    if not raw:
        return
    value = Decimal(raw)
    if not value.is_finite():
        raise ValueError("non-finite stored number at {}".format(coord))
    numbers[coord] = value


def _cell_overrides(package, part, shared, stored_numbers=None):
    with package.open(part) as stream:
        events = ET.iterparse(stream, events=("start", "end"))
        _event, root = next(events)
        ns = root.tag.rpartition("}")[0] + "}"
        stack = [root.tag]
        row = col = 0
        data = None
        for event, node in events:
            if event == "start":
                stack.append(node.tag)
                if stack == [ns + "worksheet", ns + "sheetData"]:
                    data = node
                elif stack == [ns + "worksheet", ns + "sheetData", ns + "row"]:
                    row = int(node.get("r", row + 1))
                    col = 0
                continue
            if stack == [ns + "worksheet", ns + "sheetData", ns + "row", ns + "c"]:
                coord = node.get("r")
                if coord:
                    cell_row, col = coordinate_to_tuple(coord)
                else:
                    cell_row = row
                    col += 1
                _record_number(node, ns, (cell_row, col), stored_numbers)
                value, needed = _cell_text_override(node, ns, shared)
                if needed:
                    yield (cell_row, col), value
                node.clear()
            elif stack == [ns + "worksheet", ns + "sheetData", ns + "row"] and data is not None:
                data.clear()
            stack.pop()


def load_workbook(filename, *, data_only=False, raw_numbers=False):
    """校验读取，不用于保存；文本解码一次，可另取原包数值（含缓存）以避开日期量化。"""
    workbook = _load_workbook(filename, data_only=data_only)
    if raw_numbers:
        workbook._stored_numbers = {}
    try:
        with zipfile.ZipFile(filename) as package:
            shared_part, sheets = _parts(package)
            shared = _shared_overrides(package, shared_part)
            for name, part in sheets.items():
                if name not in workbook.sheetnames:
                    continue
                ws = workbook[name]
                numbers = {} if raw_numbers else None
                for coord, value in _cell_overrides(package, part, shared, numbers):
                    cell = ws._cells.get(coord)
                    if cell is not None and not isinstance(cell, MergedCell) and cell.data_type != "f":
                        # value 的 setter 会把 '=literal' 或 '#N/A' 重新判型；原包类型保持不变。
                        cell._value = value
                if raw_numbers:
                    workbook._stored_numbers[name] = numbers
        return workbook
    except Exception:
        workbook.close()
        raise
