#!/usr/bin/env python3
"""Apply sparse value/formula edits to an original xlsx, retaining its formatting.

Only for content edits with unchanged workbook geometry. Does not import/export
online sheets, reconstruct workbooks, evaluate formulas or modify source files.
Clears workbook formula caches and requests recalculation after content edits.
"""
from __future__ import annotations

import argparse
import hashlib
from bisect import bisect_right
import json
import math
import os
import re
import sys
import tempfile
import warnings
import zipfile
import posixpath
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree
from xml.parsers import expat
from xml.sax.saxutils import escape

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

from _edit_scope import _in_scope, parse_scope

MAX_EDITS = 200000
XSTRING_LITERAL_PREFIX_RE = re.compile(r"_(?=x[0-9A-Fa-f]{4})")
XML_INVALID_CHAR_RE = re.compile(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")
UNSUPPORTED_PARTS = (
    "xl/vbaProject", "xl/activeX/", "xl/embeddings/", "xl/slicer",
    "xl/timeline", "xl/ctrlProps/", "xl/threadedComments/", "xl/persons/",
    "xl/richData/", "customXml/", "_xmlsignatures/",
)


def validate_legacy_comments(package, names):
    """只放行传统批注的VML；控件、图片形状及其它VML对象仍拒绝。"""
    for name in names:
        if not name.lower().endswith(".vml"):
            continue
        raw = package.read(name)
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("不接受含DTD的VML")
        root = ElementTree.fromstring(raw)
        allowed = {"{urn:schemas-microsoft-com:office:office}shapelayout",
                   "{urn:schemas-microsoft-com:vml}shapetype",
                   "{urn:schemas-microsoft-com:vml}shape"}
        if any(child.tag not in allowed for child in root):
            raise ValueError("VML含非批注对象，不能保证保留：" + name)
        shapes = list(root.iter("{urn:schemas-microsoft-com:vml}shape"))
        if not shapes:
            raise ValueError("不能确认VML仅包含传统批注：" + name)
        for shape in shapes:
            clients = list(shape.iter("{urn:schemas-microsoft-com:office:excel}ClientData"))
            if len(clients) != 1 or clients[0].get("ObjectType") != "Note":
                raise ValueError("VML含非批注对象，不能保证保留：" + name)
        if any(e.tag in ("{urn:schemas-microsoft-com:vml}imagedata",
                         "{urn:schemas-microsoft-com:office:office}OLEObject") for e in root.iter()):
            raise ValueError("VML含图片或嵌入对象，不能保证保留：" + name)


def read_source(path):
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        if len(names) != len(set(names)):
            raise ValueError("源文件含重复ZIP成员，不能确定要保留的版本")
        blocked = [p for p in names if p.startswith(UNSUPPORTED_PARTS)]
        validate_legacy_comments(package, names)
    if blocked:
        raise ValueError("源文件包含本工具不能保证保留的元素：" + ", ".join(blocked[:5]))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        wb = load_workbook(path, data_only=False, keep_links=True, rich_text=True)
    if caught:
        wb.close()
        raise ValueError("读取源文件产生兼容性警告，拒绝有损保存：" + str(caught[0].message))
    return wb


def special_formula_ranges(wb):
    result = {}
    for ws in wb:
        result[ws.title] = [range_boundaries(c.value.ref) for c in ws._cells.values()
                            if type(c.value).__name__ in ("DataTableFormula", "ArrayFormula")]
    return result


def has_distinct_rich_style(cell):
    """只有所有显式run属性均等于单元格字体时，才允许按普通内容替换。"""
    if type(cell.value).__name__ != "CellRichText":
        return False
    for run in cell.value:
        font = getattr(run, "font", None)
        if font is None:
            continue
        for key in font.__attrs__ + font.__elements__:
            value = getattr(font, key, None)
            target = "name" if key == "rFont" else key
            if value is not None and value != getattr(cell.font, target, None):
                return True
    return False


def validate_edits(wb, items, scope_items):
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_EDITS:
        raise ValueError("changes必须是1至{}项的JSON数组".format(MAX_EDITS))
    scope = parse_scope(scope_items)
    if not scope:
        raise ValueError("必须声明允许改动的--scope")
    if set(scope) - set(wb.sheetnames):
        raise ValueError("scope包含不存在的子表")
    special = special_formula_ranges(wb)
    out, seen = [], set()
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict) or set(item) - {"sheet", "cell", "value", "formula"}:
            raise ValueError("第{}项只能包含sheet/cell及value或formula".format(i))
        sheet, address = item.get("sheet"), item.get("cell")
        if not isinstance(sheet, str) or sheet not in wb.sheetnames:
            raise ValueError("第{}项子表不存在".format(i))
        if not isinstance(address, str) or not re.fullmatch(r"[A-Za-z]{1,3}[1-9][0-9]*", address):
            raise ValueError("第{}项cell必须是单格A1坐标".format(i))
        address = address.upper()
        row, col = coordinate_to_tuple(address)
        if row > 1048576 or col > 16384:
            raise ValueError("第{}项坐标越界".format(i))
        key = (sheet, address)
        if key in seen:
            raise ValueError("重复目标：{}!{}".format(*key))
        seen.add(key)
        if not _in_scope(scope, sheet, address):
            raise ValueError("目标超出scope：{}!{}".format(*key))
        ws = wb[sheet]
        if row > ws.max_row or col > ws.max_column:
            raise ValueError("本工具只补已有区域，不扩展布局：{}!{}".format(*key))
        if isinstance(ws[address], MergedCell):
            raise ValueError("不能写合并区从属格：{}!{}".format(*key))
        if has_distinct_rich_style(ws[address]):
            raise ValueError("目标包含不同于单元格字体的富文本run，需单独维护：{}!{}".format(*key))
        if any(c1 <= col <= c2 and r1 <= row <= r2 for c1, r1, c2, r2 in special[sheet]):
            raise ValueError("目标位于数组公式或Data Table对象内，需按对象处理：{}!{}".format(*key))
        if ("value" in item) == ("formula" in item):
            raise ValueError("第{}项必须且只能给value或formula".format(i))
        mode = "formula" if "formula" in item else "value"
        value = item[mode]
        if mode == "formula":
            if not isinstance(value, str) or not value.startswith("=") or not value[1:].strip():
                raise ValueError("formula必须是以=开头的非空公式")
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            raise ValueError("value必须为JSON标量或null")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("不接受NaN或Infinity")
        if mode == "value" and type(value) in (int, float):
            digits = ''.join(map(str, Decimal(str(value)).as_tuple().digits)).rstrip('0')
            if len(digits) > 15:
                raise ValueError("数值超过Excel的15位有效数字，不能保证保真；长编号应作为文本值写入")
        if isinstance(value, str) and len(value) > 32767:
            raise ValueError("单元格文本超过Excel长度限制")
        out.append((sheet, address, mode, value))
    return out


def _tag_end(xml, start):
    quote = None
    for i in range(start, len(xml)):
        char = xml[i:i+1]
        if quote:
            if char == quote:
                quote = None
        elif char in (b"'", b'"'):
            quote = char
        elif char == b">":
            return i+1
    raise ValueError("不完整的XML标签")


def _cell_spans(xml, include_grid=False):
    """定位真实cell字节区间；只替换目标cell，其余XML逐字节保留。"""
    parser = expat.ParserCreate(namespace_separator="}")
    stack, cells, active = [], {}, []
    grid = {"rows": [], "data": None}

    def span(attrs):
        begin = parser.CurrentByteIndex
        opening_end = _tag_end(xml, begin)
        return dict(start=begin, opening_end=opening_end, attrs=attrs,
                    tag=re.match(br"<([^\s/>]+)", xml[begin:opening_end]).group(1))

    def finish(record):
        record["closing_start"] = parser.CurrentByteIndex
        record["self_closing"] = xml[record["opening_end"]-2:record["opening_end"]] == b"/>"
        record["end"] = (record["opening_end"] if record["self_closing"]
                         else _tag_end(xml, parser.CurrentByteIndex))

    def start(name, attrs):
        local = name.rsplit('}', 1)[-1]
        if include_grid and local == "sheetData" and stack == ["worksheet"]:
            if grid["data"] is not None:
                raise ValueError("源XML包含重复sheetData")
            grid["data"] = span(attrs)
        elif include_grid and local == "row" and stack == ["worksheet", "sheetData"]:
            grid["rows"].append(span(attrs))
        if local == "c" and stack[-2:] == ["sheetData", "row"]:
            addr = attrs.get("r", "").upper()
            if not addr or addr in cells:
                raise ValueError("源XML单元格坐标缺失或重复")
            begin = parser.CurrentByteIndex
            end = _tag_end(xml, begin)
            tag = re.match(br"<([^\s/>]+)", xml[begin:end]).group(1)
            record = dict(start=begin, opening_end=end, tag=tag,
                          depth=len(stack)+1, unsupported=False, children=[])
            cells[addr] = record
            active.append(record)
        elif active:
            if len(stack) == active[-1]["depth"]:
                begin = parser.CurrentByteIndex
                active[-1]["children"].append(dict(
                    name=local, attrs=attrs, start=begin, opening_end=_tag_end(xml, begin)))
            if (len(stack) == active[-1]["depth"] and local not in ("f", "v", "is")) or local == "rPh":
                active[-1]["unsupported"] = True
            if local == "f" and attrs.get("t") in ("shared", "array", "dataTable"):
                active[-1]["unsupported"] = True
        stack.append(local)

    def end(name):
        if include_grid and stack == ["worksheet", "sheetData", "row"]:
            finish(grid["rows"][-1])
        elif include_grid and stack == ["worksheet", "sheetData"]:
            finish(grid["data"])
        if active and len(stack) == active[-1]["depth"]+1:
            child = active[-1]["children"][-1]
            child["end"] = (child["opening_end"] if xml[child["opening_end"]-2:child["opening_end"]] == b"/>"
                            else _tag_end(xml, parser.CurrentByteIndex))
        if active and len(stack) == active[-1]["depth"]:
            record = active.pop()
            record["end"] = (record["opening_end"] if xml[record["opening_end"]-2:record["opening_end"]] == b"/>"
                             else _tag_end(xml, parser.CurrentByteIndex))
        stack.pop()

    def reject_doctype(*args):
        raise ValueError("不接受含DTD的工作表XML")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = reject_doctype
    parser.Parse(xml, True)
    return (cells, grid) if include_grid else cells


def _insert_blank_cells(xml, addresses, default_styles):
    """只在原布局内建立稀疏空格的XML节点，保留已有格和行属性。"""
    cells, grid = _cell_spans(xml, include_grid=True)
    data = grid["data"]
    if data is None:
        raise ValueError("工作表缺少sheetData，不能建立目标格")
    rows, row_cells = {}, {}
    previous = 0
    for record in grid["rows"]:
        number = int(record["attrs"].get("r", "0"))
        if number <= previous:
            raise ValueError("源XML行号缺失或顺序异常，不能建立目标格")
        previous = number
        rows[number] = record
        row_cells[number] = []
    for address, record in cells.items():
        row, col = coordinate_to_tuple(address)
        if row not in rows or not rows[row]["opening_end"] <= record["start"] < rows[row]["closing_start"]:
            raise ValueError("源XML单元格与所属行不一致")
        row_cells[row].append((col, record))
    if any([c for c, _ in cs] != sorted(c for c, _ in cs) for cs in row_cells.values()):
        raise ValueError("源XML列顺序异常，不能建立目标格")
    row_numbers = list(rows)
    column_numbers = {row: [col for col,_ in cs] for row,cs in row_cells.items()}
    needed = {}
    for address in addresses:
        row, col = coordinate_to_tuple(address)
        needed.setdefault(row, []).append((col, address))
    insertions, replacements = {}, []
    for row, targets in sorted(needed.items()):
        record = rows.get(row)
        tag = record["tag"] if record else data["tag"]
        prefix = tag.rsplit(b":", 1)[0]+b":" if b":" in tag else b""
        payloads = []
        for col, address in sorted(targets):
            style = default_styles.get(address, 0)
            style_attr = b' s="'+str(style).encode('ascii')+b'"' if style else b''
            payloads.append((col,b'<'+prefix+b'c r="'+address.encode('ascii')+b'"'+style_attr+b'/>'))
        if record and not record["self_closing"]:
            for col, payload in payloads:
                index = bisect_right(column_numbers[row], col)
                at = (row_cells[row][index][1]["start"] if index < len(row_cells[row])
                      else record["closing_start"])
                insertions.setdefault(at, []).append(payload)
            # spans仅是行内列界的优化提示；原值若过窄会遗漏刚建立的格。
            opening = xml[record["start"]:record["opening_end"]]
            patched = re.sub(br'''\s+spans\s*=\s*(["']).*?\1''', b"", opening)
            if patched != opening:
                replacements.append((record["start"], record["opening_end"], patched))
        elif record:
            opening = xml[record["start"]:record["opening_end"]]
            opening = re.sub(br'''\s+spans\s*=\s*(["']).*?\1''', b"", opening)
            payload = opening[:-2]+b">"+b"".join(p for _, p in payloads)+b"</"+tag+b">"
            replacements.append((record["start"], record["end"], payload))
        else:
            payload = b'<'+prefix+b'row r="'+str(row).encode('ascii')+b'">'+b"".join(p for _,p in payloads)+b'</'+prefix+b'row>'
            index = bisect_right(row_numbers, row)
            at = rows[row_numbers[index]]["start"] if index < len(row_numbers) else data["closing_start"]
            insertions.setdefault(at, []).append(payload)
    if data["self_closing"]:
        opening = xml[data["start"]:data["opening_end"]]
        payload = b"".join(p for ps in insertions.values() for p in ps)
        replacements.append((data["start"], data["end"], opening[:-2]+b">"+payload+b"</"+data["tag"]+b">"))
    else:
        replacements.extend((at,at,b"".join(parts)) for at,parts in insertions.items())
    chunks, cursor = [], 0
    for begin, end, payload in sorted(replacements):
        chunks.extend((xml[cursor:begin], payload))
        cursor = end
    chunks.append(xml[cursor:])
    return b"".join(chunks)


def _patch_cells(xml, edits, default_styles=None):
    spans = _cell_spans(xml)
    missing = [address for _sheet,address,_mode,_value in edits if address not in spans]
    if missing:
        xml = _insert_blank_cells(xml, missing, default_styles or {})
        spans = _cell_spans(xml)
    replacements = []
    for _sheet, addr, mode, value in edits:
        record = spans[addr]
        if record["unsupported"]:
            raise ValueError("目标含共享公式或不支持的单元格元信息：" + addr)
        tag = record["tag"]
        prefix = tag.rsplit(b":", 1)[0]+b":" if b":" in tag else b""
        opening = xml[record["start"]:record["opening_end"]]
        opening = opening[:-2] if opening.endswith(b"/>") else opening[:-1]
        opening = re.sub(br'''\s+t\s*=\s*(["']).*?\1''', b"", opening)
        def element(name, text):
            name = prefix+name
            return b"<"+name+b">"+escape(text, {"\r":"&#13;"}).encode("utf-8")+b"</"+name+b">"
        if mode == "formula":
            payload = element(b"f", value[1:])
        elif value is None:
            payload = b""
        elif isinstance(value, str):
            opening += b' t="inlineStr"'
            # 先保护每个字面 _xHHHH 前缀，防止它借用后续编码的起始下划线成为转义。
            # 只消费原文的起始下划线，共享下划线的相邻前缀也各自保护；解码仍只做一次。
            encoded = XSTRING_LITERAL_PREFIX_RE.sub("_x005F_", value)
            encoded = XML_INVALID_CHAR_RE.sub(lambda match: "_x{:04X}_".format(ord(match.group())), encoded)
            text = escape(encoded, {"\r":"&#13;"}).encode("utf-8")
            payload = b"<"+prefix+b'is><'+prefix+b't xml:space="preserve">'+text+b"</"+prefix+b"t></"+prefix+b"is>"
        else:
            opening += b' t="b"' if isinstance(value, bool) else b' t="n"'
            payload = element(b"v", ("1" if value else "0") if isinstance(value, bool) else str(value))
        replacement = opening+b">"+payload+b"</"+tag+b">"
        replacements.append((record["start"], record["end"], replacement))
    chunks, cursor = [], 0
    for begin, end, replacement in sorted(replacements):
        chunks.extend((xml[cursor:begin], replacement))
        cursor = end
    chunks.append(xml[cursor:])
    return b"".join(chunks)


def _invalidate_formula_caches(xml):
    """不猜依赖关系：清除各公式及数组 / Data Table 结果区的旧值，保留公式与格式。"""
    cells = _cell_spans(xml)
    formula_cells, regions = set(), []
    for addr, record in cells.items():
        for child in record["children"]:
            if child["name"] == "f":
                formula_cells.add(addr)
                attrs = child["attrs"]
                if attrs.get("t") in ("array", "dataTable"):
                    regions.append(range_boundaries(attrs["ref"]))
    removals, cleared = [], set()
    for addr, record in cells.items():
        row, col = coordinate_to_tuple(addr)
        if addr not in formula_cells and not any(
                c1 <= col <= c2 and r1 <= row <= r2 for c1, r1, c2, r2 in regions):
            continue
        for child in record["children"]:
            if child["name"] in ("v", "is"):
                removals.append((child["start"], child["end"]))
                cleared.add(addr)
    chunks, cursor = [], 0
    for begin, end in sorted(removals):
        chunks.append(xml[cursor:begin])
        cursor = end
    chunks.append(xml[cursor:])
    return b"".join(chunks), cleared


def _request_recalculation(xml):
    """只补丁 calcPr 的重算标志，不重序列化工作簿其它元信息。"""
    parser = expat.ParserCreate(namespace_separator="}")
    stack, calc_spans, insert_at = [], [], []
    prefix = b""
    # calcPr 在 workbook 的这些后续子元素之前；不存在时也保持 schema 顺序。
    after_calc = {"oleSize", "customWorkbookViews", "pivotCaches", "smartTagPr",
                  "smartTagTypes", "webPublishing", "fileRecoveryPr", "webPublishObjects", "extLst"}

    def start(name, attrs):
        nonlocal prefix
        local = name.rsplit('}', 1)[-1]
        begin = parser.CurrentByteIndex
        if not stack:
            tag = re.match(br"<([^\s/>]+)", xml[begin:]).group(1)
            prefix = tag.rsplit(b":", 1)[0]+b":" if b":" in tag else b""
        elif stack == ["workbook"]:
            if local == "calcPr":
                calc_spans.append((begin, _tag_end(xml, begin)))
            elif local in after_calc and not insert_at:
                insert_at.append(begin)
        stack.append(local)

    def end(name):
        if stack == ["workbook"] and not insert_at:
            insert_at.append(parser.CurrentByteIndex)
        stack.pop()

    def reject_doctype(*args):
        raise ValueError("不接受含DTD的工作簿XML")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = reject_doctype
    parser.Parse(xml, True)
    flags = b' fullCalcOnLoad="1" forceFullCalc="1" calcCompleted="0"'
    if len(calc_spans) > 1:
        raise ValueError("工作簿包含重复calcPr")
    if calc_spans:
        begin, end_at = calc_spans[0]
        tag = xml[begin:end_at]
        attrs = re.compile(br'''\s+([^\s=/>]+)\s*=\s*(?:"[^"]*"|'[^']*')''')
        recalc_attrs = (b"fullCalcOnLoad", b"forceFullCalc", b"calcCompleted")
        tag = attrs.sub(lambda m: b"" if m.group(1) in recalc_attrs else m.group(0), tag)
        tail = 2 if tag.endswith(b"/>") else 1
        return xml[:begin]+tag[:-tail]+flags+tag[-tail:]+xml[end_at:]
    at = insert_at[0]
    return xml[:at]+b"<"+prefix+b"calcPr"+flags+b"/>"+xml[at:]


def _sheet_parts(package):
    workbook = ElementTree.fromstring(package.read("xl/workbook.xml"))
    rels = ElementTree.fromstring(package.read("xl/_rels/workbook.xml.rels"))
    targets = {r.attrib['Id']: r.attrib for r in rels}
    parts = {}
    for sheet in workbook.iter():
        if sheet.tag.rsplit('}', 1)[-1] != 'sheet':
            continue
        rid = next((v for k,v in sheet.attrib.items() if k.endswith('}id')), None)
        rel = targets[rid]
        if rel.get('TargetMode') == 'External':
            raise ValueError("不支持外部工作表目标")
        target = rel['Target']
        parts[sheet.attrib['name']] = (
            target.lstrip('/') if target.startswith('/')
            else posixpath.normpath(posixpath.join('xl', target)))
    return parts


def write_package(source, temporary, edits, recalc_required, style_count):
    """读库验证源文件后，对原布局内目标cell做包内补丁，不重存整本书。"""
    with zipfile.ZipFile(source) as src:
        parts = _sheet_parts(src)
        grouped = {}
        for edit in edits:
            grouped.setdefault(parts[edit[0]], []).append(edit)
        # 只继承无冲突的行/列默认样式，不猜交叉默认样式的优先级。
        default_styles = {}
        for part, changes in grouped.items():
            raw = src.read(part)
            spans, grid = _cell_spans(raw, include_grid=True)
            styled_rows = {r['attrs'].get('r'):int(r['attrs']['s']) for r in grid['rows'] if 's' in r['attrs']}
            tree = ElementTree.fromstring(raw)
            styled_cols = [(int(e.get('min','0')),int(e.get('max','0')),int(e.get('style'))) for e in tree.iter()
                           if e.tag.rsplit('}',1)[-1] == 'col' and e.get('style') is not None]
            default_styles[part] = {}
            for sheet_name, address, _mode, _value in changes:
                if address in spans:
                    continue
                row, col = coordinate_to_tuple(address)
                styles = {style for lo,hi,style in styled_cols if lo <= col <= hi}
                if str(row) in styled_rows:
                    styles.add(styled_rows[str(row)])
                if len(styles) > 1:
                    raise ValueError("未定义目标格的行/列默认样式冲突，需明确样式后编辑：" + address)
                if styles:
                    style = styles.pop()
                    if style < 0 or style >= style_count:
                        raise ValueError("目标格的行/列默认样式索引无效")
                    default_styles[part][address] = style
        sheet_names = {part: name for name, part in parts.items()}
        cleared = set()
        with zipfile.ZipFile(temporary, 'w') as dst:
            dst.comment = src.comment
            for info in src.infolist():
                raw = src.read(info.filename)
                patched = (_patch_cells(raw, grouped[info.filename], default_styles[info.filename])
                           if info.filename in grouped else raw)
                if recalc_required and info.filename in sheet_names:
                    patched, addresses = _invalidate_formula_caches(patched)
                    cleared.update((sheet_names[info.filename], addr) for addr in addresses)
                elif recalc_required and info.filename == "xl/workbook.xml":
                    patched = _request_recalculation(patched)
                dst.writestr(info, patched)
        return cleared


def apply_edits(source, output, items, scope_items):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source.suffix.lower() != ".xlsx" or output.suffix.lower() != ".xlsx":
        raise ValueError("本工具只处理.xlsx，不能转换文件类型")
    if source == output or output.exists():
        raise ValueError("output必须是不同于源文件且尚不存在的新文件")
    if not output.parent.is_dir():
        raise ValueError("output父目录不存在")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    wb = read_source(source)
    temporary = None
    try:
        edits = validate_edits(wb, items, scope_items)
        fd, temporary = tempfile.mkstemp(prefix=".sheet-edits-", suffix=".xlsx", dir=str(output.parent))
        os.close(fd)
        recalc_required = (any(c.data_type == "f" for ws in wb for c in ws._cells.values())
                           or any(mode == "formula" for _s, _a, mode, _v in edits))
        cleared_caches = write_package(source, temporary, edits, recalc_required, len(wb._cell_styles))
        if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
            raise ValueError("执行期间源文件发生变化，未生成交付文件")
        # 同目录硬链接原子发布且不覆盖已存在的文件；源文件始终只读。
        os.link(temporary, output)
        return {"status": "applied", "output": str(output), "edits": len(edits),
                "source_sha256": source_hash,
                "cleared_formula_cache_cells": len(cleared_caches),
                "recalculation_required": recalc_required,
                "formula_execution_verified": False}
    finally:
        wb.close()
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='changes示例：[{"sheet":"明细","cell":"B2","value":"00123"}, '
               '{"sheet":"明细","cell":"D2","formula":"=B2*C2"}]。'
               'value保留JSON类型；formula才写公式。目标必须在原布局范围内；可补稀疏空格，'
               '未定义格继承无冲突的行/列默认样式。传统批注原样保留，控件VML不支持。'
               'output必须为新文件；编辑后清除全簿公式旧缓存并标记需重算，本脚本不计算公式值。')
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--changes", required=True, help="JSON数组文件路径（不加@）；每项sheet/cell加value或formula")
    parser.add_argument("--scope", action="append", required=True, help="允许改动范围，如'明细!B2'；可重复")
    args = parser.parse_args()
    try:
        items = json.loads(Path(args.changes).read_text(encoding="utf-8"))
        result = apply_edits(args.source, args.output, items, args.scope)
    except Exception as exc:
        print(json.dumps({"status": "not_applied", "error": str(exc)}, ensure_ascii=False))
        print("未生成交付文件，源文件未修改。按错误修正坐标/类型；兼容性或结构变更任务改用对应引擎，不重建源表或忽略警告。", file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False))
    print("已按源格式生成新文件；公式旧缓存已清除，未执行重算，按所选环境的保存和交付规则处理。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
