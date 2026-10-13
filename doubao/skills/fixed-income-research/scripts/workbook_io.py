"""Passive OOXML subset: bounded parsing, explicit formulas and result reconciliation."""

import ast
from decimal import Decimal, InvalidOperation, localcontext
import io
from pathlib import Path, PurePosixPath
import re
import stat
import xml.etree.ElementTree as ET
import zipfile

from workflow_inputs import digest, private_file

S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P = "http://schemas.openxmlformats.org/package/2006/relationships"
C = "http://schemas.openxmlformats.org/package/2006/content-types"
MAIN = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
SHEET = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
RELS = "application/vnd.openxmlformats-package.relationships+xml"
MAX_ZIP = 16 * 1024 * 1024
MAX_MEMBER = 4 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_CELLS = 100000
CELL = re.compile(r"[A-Z]{1,3}[1-9][0-9]{0,6}\Z")
GRID_COLUMNS = 16384
GRID_ROWS = 1048576


def row_number(value):
    if (not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,6}", value)
            or int(value) > GRID_ROWS):
        raise ValueError("invalid worksheet row coordinate")
    return int(value)


def cell_address(value):
    if not isinstance(value, str) or not CELL.fullmatch(value):
        raise ValueError("invalid cell address")
    letters, digits = re.fullmatch(r"([A-Z]+)([0-9]+)", value).groups()
    column = 0
    for letter in letters:
        column = column * 26 + ord(letter) - ord("A") + 1
    if column > GRID_COLUMNS or int(digits) > GRID_ROWS:
        raise ValueError("cell address outside supported worksheet grid")
    return column, int(digits)


def sheet_name(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 31
            or any(c in "[]:*?/\\" for c in value) or value.startswith("'") or value.endswith("'")
            or value.casefold() == "history" or any(
                ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF
                or ord(c) in (0xFFFE, 0xFFFF) for c in value)):
        raise ValueError("invalid or reserved worksheet name")
    return value


def sheet_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
        raise ValueError("sheetId must be an ASCII unsigned integer")
    significant = value.lstrip("0")
    if not significant or len(significant) > 5 or int(significant) > 65534:
        raise ValueError("sheetId outside supported Office range")
    return int(significant)


def raw_number(value):
    if len(str(value)) > 512:
        raise ValueError("workbook numeric representation safety limit")
    try:
        value = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid workbook number") from exc
    if not value.is_finite() or (value and abs(value.adjusted()) > 100):
        raise ValueError("workbook numeric value outside supported finite range")
    return value


def rounded(value):
    value = raw_number(value)
    with localcontext() as context:
        context.prec = 15
        return +value


def col(index):
    if type(index) is not int or not 1 <= index <= GRID_COLUMNS:
        raise ValueError("cell address column outside supported worksheet grid")
    result = ""
    while index:
        index, remainder = divmod(index-1, 26)
        result = chr(65+remainder) + result
    return result


def formula_value(formula, cells):
    return _formula_value(formula, cells, precision=50, project=True)


def _formula_value(formula, cells, *, precision, project):
    if not isinstance(formula, str) or len(formula) > 512 or not re.fullmatch(r"[A-Z0-9.+*/() \-]+", formula):
        raise ValueError("unsupported or unsafe formula")
    try:
        tree = ast.parse(formula, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("invalid formula") from exc
    if sum(1 for _ in ast.walk(tree)) > 128:
        raise ValueError("formula complexity limit")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = raw_number(ast.get_source_segment(formula, node))
            return rounded(value) if project else value
        if isinstance(node, ast.Name):
            cell_address(node.id)
            cell = cells.get(node.id)
            if cell is None or cell["kind"] != "number" or cell["value"] is None or "formula" in cell:
                raise ValueError("formula must reference existing numeric input cells, not other formulas")
            return cell["value"]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left+right
            if isinstance(node.op, ast.Sub):
                return left-right
            if isinstance(node.op, ast.Mult):
                return left*right
            if right == 0:
                raise ValueError("division by zero in workbook")
            return left/right
        raise ValueError("unsupported formula construct")

    with localcontext() as context:
        context.prec = precision
        value = visit(tree)
        return rounded(value) if project else value


def cell(value):
    if type(value) in (int, Decimal):
        return {"kind": "number", "value": rounded(value)}
    if value is None:
        value = "unknown"
    elif type(value) is bool:
        value = "true" if value else "false"
    else:
        value = str(value)
    if len(value) > 32767 or any(ord(c) < 32 and c not in "\t\n\r" for c in value):
        raise ValueError("unsupported spreadsheet text")
    return {"kind": "text", "value": value}


def table(rows):
    cells = {}
    for i, row in enumerate(rows, 1):
        row_number(str(i))
        for j, value in enumerate(row, 1):
            if len(cells) >= MAX_CELLS:
                raise ValueError("excessive generated cells")
            cells[f"{col(j)}{i}"] = cell(value)
    return cells


def flatten(value, path=""):
    if isinstance(value, dict):
        if not value:
            yield [path, "{}"]
        for key, item in sorted(value.items()):
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from flatten(item, path + "/" + escaped)
    elif isinstance(value, list):
        if not value:
            yield [path, "[]"]
        for i, item in enumerate(value):
            yield from flatten(item, path + "/" + str(i))
    else:
        yield [path, value]


def specification(data, result):
    sheets = {"Input": table([["JSON path", "Task-derived value"], *flatten(data)]),
              "Result": table([["JSON path", "Computed value / unknown"], *flatten(result)])}
    debt_rows = [["Scenario", "Owner", "Date", "Opening", "Inflows", "Covered", "Expired",
                  "Model closing", "Projected closing", "Projected minus model"]]
    interest_rows = [["Scenario", "Payment", "Start", "End", "Principal", "Rate", "Days",
                      "Year days", "Model interest", "Projected interest", "Segment status",
                      "Missing dependencies", "Projected minus model"]]
    for scenario in (result.get("debt_analysis") or {}).get("scenarios", []):
        for row in scenario["cashflow"]:
            debt_rows.append([scenario["id"], row["owner"], row["date"], row["opening"],
                              row["inflows"], row["covered"], row["expired_unavailable"], row["closing"], None])
        for pay in scenario["payments"]:
            calc = pay.get("calculation")
            if calc:
                for seg in calc["segments"]:
                    interest_rows.append([scenario["id"], pay["id"], seg["start"], seg["end"],
                                          seg["principal"], calc["annual_rate"], seg["days"],
                                          calc["year_days"], seg["interest"], None, seg["status"],
                                          "; ".join(d["location"] + ": " + d["reason"]
                                                    for d in seg["missing_dependencies"])])
    cash_rows = [["Allocation", "Date", "Opening", "Principal", "Interest", "Fees",
                  "Withdrawal", "Model closing", "Projected closing", "Projected minus model"]]
    cash = result.get("cash_analysis") or {}
    for label in ("proposed", "witness"):
        if cash.get(label):
            for row in cash[label]["cashflow"]:
                cash_rows.append([label, row["date"], row["opening"], row["principal"], row["interest"],
                                  row["fees"], row["withdrawal"], row["closing"], None])
    for name, data_rows, column, formula, expected, delta, precision in (
        ("DebtCash", debt_rows, "I", "D{r}+E{r}-F{r}-G{r}", "H", "J", 512),
        ("Interest", interest_rows, "J", "E{r}*F{r}*G{r}/H{r}", "I", "M", 50),
        ("CashProducts", cash_rows, "I", "C{r}+D{r}+E{r}-F{r}-G{r}", "H", "J", 512),
    ):
        if len(data_rows) <= 1:
            continue
        cells = table(data_rows)
        model_cells = {
            f"{col(j)}{i}": {"kind": "number", "value": raw_number(value)}
            for i, row in enumerate(data_rows, 1) for j, value in enumerate(row, 1)
            if type(value) in (int, Decimal)
        }
        for i in range(2, len(data_rows)+1):
            expression = formula.format(r=i)
            if f"{expected}{i}" not in model_cells:
                row = data_rows[i - 1]
                if (name != "Interest" or row[8] is not None
                        or row[10] != "unknown" or not row[11]):
                    raise ValueError(f"missing or invalid model result: {name}/{i}")
                cells[f"{delta}{i}"] = cell(None)
                continue
            exact = _formula_value(expression, model_cells, precision=precision, project=False)
            if exact != model_cells[f"{expected}{i}"]["value"]:
                raise ValueError(f"computed result and workbook formula disagree: {name}/{i}")
            calculated = formula_value(expression, cells)
            cells[f"{column}{i}"] = {"kind": "number", "value": calculated, "formula": expression}
            with localcontext() as context:
                context.prec = 512
                cells[f"{delta}{i}"] = cell(calculated - cells[f"{expected}{i}"]["value"])
        sheets[name] = cells
    return sheets


def xml(root):
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write(path, sheets):
    if not isinstance(sheets, dict) or not sheets or len(sheets) > 252:
        raise ValueError("empty or excessive workbook sheets")
    types = ET.Element(f"{{{C}}}Types")
    ET.SubElement(types, f"{{{C}}}Default", Extension="rels", ContentType=RELS)
    ET.SubElement(types, f"{{{C}}}Default", Extension="xml", ContentType="application/xml")
    ET.SubElement(types, f"{{{C}}}Override", PartName="/xl/workbook.xml", ContentType=MAIN)
    root_rels = ET.Element(f"{{{P}}}Relationships")
    ET.SubElement(root_rels, f"{{{P}}}Relationship", Id="rId1", Type=R+"/officeDocument",
                  Target="xl/workbook.xml")
    workbook = ET.Element(f"{{{S}}}workbook")
    sheet_list = ET.SubElement(workbook, f"{{{S}}}sheets")
    relationships = ET.Element(f"{{{P}}}Relationships")
    parts, names = {}, set()
    for index, (name, cells) in enumerate(sheets.items(), 1):
        sheet_name(name)
        sheet_id(str(index))
        if name.casefold() in names:
            raise ValueError("duplicate worksheet name")
        names.add(name.casefold())
        if not isinstance(cells, dict) or len(cells) > MAX_CELLS:
            raise ValueError("invalid or excessive generated cells")
        target = f"worksheets/sheet{index}.xml"
        ET.SubElement(sheet_list, f"{{{S}}}sheet", name=name, sheetId=str(index),
                      attrib={f"{{{R}}}id": f"rId{index}"})
        ET.SubElement(relationships, f"{{{P}}}Relationship", Id=f"rId{index}",
                      Type=R+"/worksheet", Target=target)
        ET.SubElement(types, f"{{{C}}}Override", PartName="/xl/"+target, ContentType=SHEET)
        worksheet = ET.Element(f"{{{S}}}worksheet")
        sheet_data = ET.SubElement(worksheet, f"{{{S}}}sheetData")
        row_nodes = {}
        ordered = sorted(cells, key=lambda address: cell_address(address)[::-1])
        for address in ordered:
            value = cells[address]
            row = str(cell_address(address)[1])
            if "formula" in value:
                if value["kind"] != "number":
                    raise ValueError("formula must be in a numeric cell")
                formula_value(value["formula"], cells)
            if row not in row_nodes:
                row_nodes[row] = ET.SubElement(sheet_data, f"{{{S}}}row", r=row)
            node = ET.SubElement(row_nodes[row], f"{{{S}}}c", r=address)
            if value["kind"] == "text":
                node.set("t", "inlineStr")
                text = ET.SubElement(ET.SubElement(node, f"{{{S}}}is"), f"{{{S}}}t")
                text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                text.text = value["value"]
            else:
                if "formula" in value:
                    ET.SubElement(node, f"{{{S}}}f").text = value["formula"]
                ET.SubElement(node, f"{{{S}}}v").text = str(value["value"])
        parts["xl/"+target] = xml(worksheet)
    parts.update({"[Content_Types].xml": xml(types), "_rels/.rels": xml(root_rels),
                  "xl/workbook.xml": xml(workbook), "xl/_rels/workbook.xml.rels": xml(relationships)})
    if Path(path).exists():
        raise ValueError("refusing to overwrite workbook")
    with private_file(path) as stream, zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(parts.items()):
            info = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)


def parse_xml(raw):
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("only UTF-8 passive XML is supported") from exc
    if "\x00" in content or "<!" in content or "<?" in re.sub(r"^<\?xml[^?]*\?>", "", content):
        raise ValueError("DTD, entities and processing instructions are forbidden")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError("invalid passive XML") from exc
    pending, count = [(root, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if depth > 32 or count > 200000 or len(node.attrib) > 32:
            raise ValueError("XML complexity safety limit exceeded")
        pending.extend((child, depth+1) for child in node)
    return root


def relations(node, kind, prefix, parts):
    if node.tag != f"{{{P}}}Relationships":
        raise ValueError("invalid OPC relationship namespace")
    mapping, seen = {}, set()
    for row in node:
        if (row.tag != f"{{{P}}}Relationship" or set(row.attrib) != {"Id", "Type", "Target"}
                or row.get("Type") != R+"/"+kind):
            raise ValueError("external, active or unsupported relationship")
        key, target = row.get("Id"), prefix + row.get("Target", "")
        if not key or key in mapping or target in seen or target not in parts:
            raise ValueError("duplicate or dangling relationship")
        mapping[key] = target
        seen.add(target)
    return mapping


def inspect(path, required_sheets=(), require_formulas=False, expected=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".xlsx":
        raise ValueError("expected a real regular .xlsx file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_ZIP+1)
    if not raw or len(raw) > MAX_ZIP:
        raise ValueError("workbook ZIP safety limit or empty file")
    parts, total = {}, 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len(infos) > 256:
            raise ValueError("too many ZIP parts")
        for info in infos:
            name, mode = info.filename, info.external_attr >> 16
            if (name in parts or info.orig_filename != name or "\\" in name or
                    PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts or
                    name != str(PurePosixPath(name)) or info.is_dir() or info.flag_bits & 1 or
                    (stat.S_IFMT(mode) not in (0, stat.S_IFREG)) or
                    info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ValueError("unsafe or duplicate ZIP part")
            if (info.file_size > MAX_MEMBER or info.file_size < 0 or
                    info.file_size > max(1, info.compress_size)*2000):
                raise ValueError("ZIP expansion safety limit")
            total += info.file_size
            if total > MAX_EXPANDED:
                raise ValueError("ZIP total expansion safety limit")
            with archive.open(info) as stream:
                content = stream.read(MAX_MEMBER+1)
            if len(content) != info.file_size or len(content) > MAX_MEMBER:
                raise ValueError("ZIP size or integrity mismatch")
            parts[name] = parse_xml(content)
    core = {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels"}
    if not core <= parts.keys() or any(n not in core and not re.fullmatch(
            r"xl/worksheets/sheet[1-9][0-9]*\.xml", n) for n in parts):
        raise ValueError("missing OPC part or unsupported active/extra part")
    types = parts["[Content_Types].xml"]
    if types.tag != f"{{{C}}}Types":
        raise ValueError("invalid OPC content types")
    defaults, overrides = {}, {}
    for node in types:
        if node.tag == f"{{{C}}}Default" and set(node.attrib) == {"Extension", "ContentType"}:
            key = node.get("Extension")
            if key in defaults:
                raise ValueError("duplicate content default")
            defaults[key] = node.get("ContentType")
        elif node.tag == f"{{{C}}}Override" and set(node.attrib) == {"PartName", "ContentType"}:
            key = node.get("PartName")
            if key in overrides:
                raise ValueError("duplicate content override")
            overrides[key] = node.get("ContentType")
        else:
            raise ValueError("unsupported content type")
    expected_types = {"/xl/workbook.xml": MAIN, **{
        "/"+n: SHEET for n in parts if n.startswith("xl/worksheets/")}}
    if defaults != {"rels": RELS, "xml": "application/xml"} or overrides != expected_types:
        raise ValueError("missing, active or incorrect content types")
    if list(relations(parts["_rels/.rels"], "officeDocument", "", parts).values()) != ["xl/workbook.xml"]:
        raise ValueError("invalid root workbook relationship")
    mapping = relations(parts["xl/_rels/workbook.xml.rels"], "worksheet", "xl/", parts)
    workbook = parts["xl/workbook.xml"]
    if workbook.tag != f"{{{S}}}workbook" or [n.tag for n in workbook] != [f"{{{S}}}sheets"]:
        raise ValueError("unsupported workbook metadata, defined names or active content")
    books, sheet_ids, names, targets = {}, set(), set(), set()
    errors, warnings, stats = [], [], []
    for sheet in workbook[0]:
        name, sid, target = sheet.get("name"), sheet.get("sheetId"), mapping.get(sheet.get(f"{{{R}}}id"))
        sheet_name(name)
        numeric_sid = sheet_id(sid)
        if (sheet.tag != f"{{{S}}}sheet" or set(sheet.attrib) - {"name", "sheetId", f"{{{R}}}id", "state"} or
                name.casefold() in names or numeric_sid in sheet_ids or target is None or target in targets or
                sheet.get("state", "visible") != "visible"):
            raise ValueError("invalid, duplicate or hidden worksheet")
        sheet_ids.add(numeric_sid)
        names.add(name.casefold())
        targets.add(target)
        root = parts[target]
        if root.tag != f"{{{S}}}worksheet" or [n.tag for n in root] != [f"{{{S}}}sheetData"]:
            raise ValueError("unsupported worksheet features")
        cells, row_ids, formulas = {}, set(), 0
        for row in root[0]:
            rid = row.get("r")
            row_number(rid)
            if row.tag != f"{{{S}}}row" or rid in row_ids or set(row.attrib) != {"r"}:
                raise ValueError("invalid worksheet row")
            row_ids.add(rid)
            for node in row:
                address, kind = node.get("r", ""), node.get("t", "n")
                _, address_row = cell_address(address)
                if (node.tag != f"{{{S}}}c" or set(node.attrib) - {"r", "t"} or
                        str(address_row) != rid or
                        address in cells or len(cells) >= MAX_CELLS):
                    raise ValueError("invalid, duplicate or excessive cells")
                children = [n.tag for n in node]
                if kind == "inlineStr" and children == [f"{{{S}}}is"] and [
                        n.tag for n in node[0]] == [f"{{{S}}}t"]:
                    if len(node[0][0]):
                        raise ValueError("unsupported rich text")
                    cells[address] = cell(node[0][0].text or "")
                elif kind == "n" and children in ([f"{{{S}}}v"], [f"{{{S}}}f", f"{{{S}}}v"], [f"{{{S}}}f"]):
                    value = node.find(f"{{{S}}}v")
                    expression = node.find(f"{{{S}}}f")
                    if any(n.attrib or len(n) for n in node):
                        raise ValueError("unsupported shared/array formula or nested value")
                    if value is None or not value.text:
                        cells[address] = {"kind": "number", "value": None}
                        warnings.append({"sheet": name, "uncached_formula_cells": [address]})
                    else:
                        raw_value = raw_number(value.text)
                        if expression is None and raw_value != rounded(raw_value):
                            raise ValueError("numeric input precision exceeds supported 15 significant digits")
                        cells[address] = {"kind": "number", "value": raw_value}
                    if expression is not None:
                        cells[address]["formula"] = expression.text or ""
                        formulas += 1
                elif kind == "e":
                    errors.append(f"{name}!{address}:cell_error")
                    cells[address] = {"kind": "error", "value": "cell_error"}
                else:
                    raise ValueError("unsupported cell representation")
        for address, item in cells.items():
            if "formula" in item:
                calculated = formula_value(item["formula"], cells)
                if item["value"] is not None and calculated != item["value"]:
                    errors.append(f"{name}!{address}:formula_cache_mismatch")
        books[name] = cells
        stats.append({"name": name, "nonempty_cells": len(cells), "formula_cells": formulas, "state": "visible"})
    if not books or targets != set(mapping.values()) or targets != set(parts)-core:
        raise ValueError("orphan worksheet or empty workbook")
    for required in required_sheets:
        if required not in books:
            errors.append(f"missing_sheet:{required}")
        elif not books[required]:
            errors.append(f"empty_sheet:{required}")
    if require_formulas and not any(s["formula_cells"] for s in stats):
        errors.append("no_formulas")
    if expected is not None and books != expected:
        errors.append("workbook_does_not_match_computed_result")
    formula_count = sum(sheet["formula_cells"] for sheet in stats)
    return {"status": "failed" if errors else ("reconciled" if expected is not None and not warnings else "structure_checked"),
            "path": str(path.resolve()), "sha256": digest(raw), "bytes": len(raw),
            "sheets": stats, "errors": errors, "warnings": warnings,
            "formula_cells_checked": formula_count,
            "recalculated": formula_count > 0 and not errors and not warnings,
            "financial_content_verified": expected is not None and not errors and not warnings,
            "host_delivery_confirmed": False,
            "next_check": "This is a passive supported-subset check, not source-semantic or host-delivery certification."}
