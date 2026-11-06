"""Offline DOCX fallback for an already completed cloud research report.

Uses only the standard library. Unknown Markdown is kept as text; images retain
their descriptions and URLs rather than making another external download.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import uuid
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("w", W)
ET.register_namespace("r", R)


def node(parent, name, **attributes):
    return ET.SubElement(parent, f"{{{W}}}{name}", {f"{{{W}}}{k}": str(v) for k, v in attributes.items()})


def xml_bytes(root):
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def safe_xml(value):
    # Preserve XML-illegal characters visibly instead of silently dropping data.
    return "".join(c if c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD
                   or 0x10000 <= ord(c) <= 0x10FFFF else f"\\u{ord(c):04x}" for c in value)


def run(parent, text, bold=False, italic=False, code=False):
    item = node(parent, "r")
    if bold or italic or code:
        props = node(item, "rPr")
        if bold:
            node(props, "b")
        if italic:
            node(props, "i")
        if code:
            node(props, "rFonts", ascii="Consolas", hAnsi="Consolas", eastAsia="Microsoft YaHei")
            node(props, "sz", val=19)
    for index, line in enumerate(text.split("\n")):
        if index:
            node(item, "br")
        node(item, "t").attrib["{http://www.w3.org/XML/1998/namespace}space"] = "preserve"
        item[-1].text = safe_xml(line)


class Report:
    def __init__(self):
        self.document = ET.Element(f"{{{W}}}document")
        self.body = node(self.document, "body")
        self.rels = ET.Element("Relationships", xmlns=PKG)
        ET.SubElement(self.rels, "Relationship", Id="rIdStyles", Type=R + "/styles", Target="styles.xml")
        self.link_count = 0

    def inline(self, parent, text):
        pattern = r"!?\[[^\]\n]*\]\([^\n)]*\)|`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|(?<!\w)\*[^*\n]+\*(?!\w)"
        offset = 0
        for match in re.finditer(pattern, text):
            run(parent, text[offset:match.start()])
            token = match.group()
            if token.startswith(("[", "![")):
                label, target = token[token.index("[") + 1:].split("](", 1)
                target = target[:-1]
                if token.startswith("!["):
                    run(parent, f"图片：{label}（{target}）")
                elif re.match(r"^(https?://|mailto:)", target, re.I):
                    self.link_count += 1
                    rid = f"rIdLink{self.link_count}"
                    ET.SubElement(self.rels, "Relationship", Id=rid, Type=R + "/hyperlink",
                                  Target=safe_xml(target), TargetMode="External")
                    link = node(parent, "hyperlink")
                    link.set(f"{{{R}}}id", rid)
                    run(link, label or target)
                else:
                    run(parent, token)
            elif token.startswith("`"):
                run(parent, token[1:-1], code=True)
            elif token.startswith(("**", "__")):
                run(parent, token[2:-2], bold=True)
            else:
                run(parent, token[1:-1], italic=True)
            offset = match.end()
        run(parent, text[offset:])

    def paragraph(self, text, style=None, indent=0, literal=False):
        paragraph = node(self.body, "p")
        if style or indent:
            props = node(paragraph, "pPr")
            if style:
                node(props, "pStyle", val=style)
            if indent:
                node(props, "ind", left=indent)
        if literal:
            run(paragraph, text, code=True)
        else:
            self.inline(paragraph, text)

    def table(self, rows):
        table = node(self.body, "tbl")
        props = node(table, "tblPr")
        node(props, "tblW", w=9638, type="dxa")
        node(props, "tblLayout", type="fixed")
        borders = node(props, "tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            node(borders, edge, val="single", sz=4, color="B0B0B0")
        columns = max(len(row) for row in rows)
        width = 9638 // columns
        grid = node(table, "tblGrid")
        for _ in range(columns):
            node(grid, "gridCol", w=width)
        for index, values in enumerate(rows):
            row = node(table, "tr")
            if index == 0:
                node(node(row, "trPr"), "tblHeader")
            for value in values + [""] * (columns - len(values)):
                cell = node(row, "tc")
                node(node(cell, "tcPr"), "tcW", w=width, type="dxa")
                self.inline(node(cell, "p"), value)
        node(self.body, "p")

    def markdown(self, text):
        lines = text.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            fence = re.match(r"^\s*(`{3,}|~{3,})", line)
            if fence:
                marker = fence.group(1)
                index += 1
                block = []
                while index < len(lines) and not re.match(r"^\s*" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$", lines[index]):
                    block.append(lines[index])
                    index += 1
                self.paragraph("\n".join(block), literal=True)
            elif "|" in line and index + 1 < len(lines) and table_separator(lines[index + 1]):
                rows = [table_cells(line)]
                index += 2
                while index < len(lines) and "|" in lines[index] and lines[index].strip():
                    rows.append(table_cells(lines[index]))
                    index += 1
                self.table(rows)
                continue
            elif line.strip():
                heading = re.match(r"^(#{1,6})\s+(.*)", line)
                listing = re.match(r"^(\s*)([-+*]|\d+[.)])\s+(.*)", line)
                if heading:
                    style = "Title" if index == 0 and len(heading[1]) == 1 else "Heading" + str(len(heading[1]))
                    self.paragraph(heading[2], style)
                elif listing:
                    prefix = "• " if listing[2] in "-+*" else listing[2] + " "
                    self.paragraph(prefix + listing[3], indent=360 + len(listing[1].expandtabs(4)) * 120)
                elif line.startswith(">"):
                    self.paragraph(line[1:].lstrip(), indent=360)
                else:
                    self.paragraph(line)
            index += 1

    def references(self, references):
        if references is None or references == "" or references == [] or references == {}:
            return
        if isinstance(references, str):
            try:
                references = json.loads(references)
            except ValueError:
                self.paragraph("云端参考资料", "Heading1")
                self.paragraph(references, literal=True)
                return
        self.paragraph("云端参考资料", "Heading1")
        items = references if isinstance(references, list) else [references]
        for index, item in enumerate(items, 1):
            self.paragraph(str(index), "Heading2")
            # Keep every key, value and reference id, including unknown schemas.
            if isinstance(item, dict):
                for key, value in item.items():
                    rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
                    self.paragraph(f"{key}：{rendered}", literal=True)
            else:
                self.paragraph(item if isinstance(item, str) else json.dumps(item, ensure_ascii=False), literal=True)


def table_cells(line):
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|") and not value.endswith("\\|"):
        value = value[:-1]
    cells, current, code_ticks, index = [], [], 0, 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value) and value[index + 1] == "|":
            current.append("|")
            index += 2
            continue
        if char == "`":
            end = index
            while end < len(value) and value[end] == "`":
                end += 1
            size = end - index
            code_ticks = 0 if code_ticks == size else size if not code_ticks else code_ticks
            current.append(value[index:end])
            index = end
            continue
        if char == "|" and not code_ticks:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    return cells + ["".join(current).strip()]


def table_separator(line):
    cells = table_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def styles_xml():
    styles = ET.Element(f"{{{W}}}styles")
    for name, size in [("Normal", 22), ("Title", 36)] + [(f"Heading{i}", max(22, 34 - i * 2)) for i in range(1, 7)]:
        style = node(styles, "style", type="paragraph", styleId=name)
        if name == "Normal":
            style.set(f"{{{W}}}default", "1")
        node(style, "name", val=name)
        if name != "Normal":
            node(style, "basedOn", val="Normal")
        props = node(style, "pPr")
        node(props, "spacing", after=120, line=300, lineRule="auto")
        if name != "Normal":
            node(props, "keepNext")
        text = node(style, "rPr")
        node(text, "rFonts", ascii="Arial", hAnsi="Arial", eastAsia="Microsoft YaHei")
        node(text, "sz", val=size)
        node(text, "color", val="000000")
        if name != "Normal":
            node(text, "b")
    return xml_bytes(styles)


def validate_docx(path):
    try:
        with ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError("DOCX 数据校验失败")
            ET.fromstring(archive.read("[Content_Types].xml"))
            document = ET.fromstring(archive.read("word/document.xml"))
            if document.tag != f"{{{W}}}document":
                raise ValueError("DOCX 正文格式错误")
    except (BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError("下载内容不是有效 DOCX") from exc


def generate_local_docx(answer_content, references, destination):
    if not isinstance(answer_content, str) or not answer_content.strip():
        raise ValueError("云端未返回完整报告正文，不能生成本地 DOCX")
    report = Report()
    report.markdown(answer_content)
    report.references(references)
    section = node(report.body, "sectPr")
    node(section, "pgSz", w=11906, h=16838)
    node(section, "pgMar", top=1134, right=1134, bottom=1134, left=1134, header=567, footer=567, gutter=0)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".part")
    types = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
             '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    root_rels = f'<Relationships xmlns="{PKG}"><Relationship Id="rId1" Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>'
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
            for name, content in {"[Content_Types].xml": types, "_rels/.rels": root_rels,
                                  "word/document.xml": xml_bytes(report.document), "word/styles.xml": styles_xml(),
                                  "word/_rels/document.xml.rels": xml_bytes(report.rels)}.items():
                archive.writestr(name, content)
        validate_docx(temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination
