#!/usr/bin/env python3
"""Generate a will DOCX by patching the approved template's OOXML text nodes."""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from validate_case import OUTPUT_GATE_STATUSES, TEMPLATE_SHA256, WILL_SECTION_KEYS, validate_case
from intake_runtime import AI_FILE_NOTICE


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
W = f"{{{W_NS}}}"
HEADINGS = {
    "declarations": "一、声明",
    "legal_heirs": "二、法定继承人",
    "estate_distribution": "三、财产继承",
    "executor": "四、遗嘱执行人",
    "guardianship": "五、监护人",
    "minor_guardianship": "六、未成年子女监护人",
    "other": "七、其他",
}
SIGNING_MARKER = "（以下为遗嘱签订部分，无正文）"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("case JSON root must be an object")
    return value


def _template_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "templates" / "will-template.docx"


def _namespaces(xml_bytes: bytes) -> None:
    for _, item in ET.iterparse(io.BytesIO(xml_bytes), events=("start-ns",)):
        prefix, uri = item
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            continue


def _text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.iter(f"{W}t"))


def _paragraphs(body: ET.Element) -> list[ET.Element]:
    return [child for child in list(body) if child.tag == f"{W}p"]


def _find_exact(body: ET.Element, value: str) -> ET.Element:
    for paragraph in _paragraphs(body):
        if _text(paragraph).strip() == value:
            return paragraph
    raise ValueError(f"template anchor not found: {value}")


def _find_contains(body: ET.Element, value: str, *, last: bool = False) -> ET.Element:
    matches = [paragraph for paragraph in _paragraphs(body) if value in _text(paragraph)]
    if not matches:
        raise ValueError(f"template anchor not found: {value}")
    return matches[-1] if last else matches[0]


def _replace_text(paragraph: ET.Element, value: str) -> None:
    nodes = list(paragraph.iter(f"{W}t"))
    if not nodes:
        run = ET.Element(f"{W}r")
        node = ET.SubElement(run, f"{W}t")
        paragraph.append(run)
        nodes = [node]
    target = next((node for node in nodes if (node.text or "").strip()), nodes[0])
    target.text = value
    if value[:1].isspace() or value[-1:].isspace():
        target.set(f"{{{XML_NS}}}space", "preserve")
    for node in nodes:
        if node is not target:
            node.text = ""


def _clean_clause(value: str) -> str:
    return re.sub(r"^\s*\d+\s*[\.．、]\s*", "", value).strip()


def _replace_clause_block(body: ET.Element, start: ET.Element, end: ET.Element, clauses: list[str]) -> None:
    children = list(body)
    start_index = children.index(start)
    end_index = children.index(end)
    old = [node for node in children[start_index + 1:end_index] if node.tag == f"{W}p" and _text(node).strip()]
    if not old:
        raise ValueError(f"template has no exemplar clause after {_text(start).strip()}")
    exemplar = old[0]
    for node in old:
        body.remove(node)
    insert_at = list(body).index(end)
    for index, clause in enumerate(clauses, start=1):
        clone = copy.deepcopy(exemplar)
        _replace_text(clone, f"{index}．{_clean_clause(clause)}")
        body.insert(insert_at, clone)
        insert_at += 1


def _insert_ai_notice(body: ET.Element, after: ET.Element) -> None:
    paragraph = ET.Element(f"{W}p")
    properties = ET.SubElement(paragraph, f"{W}pPr")
    alignment = ET.SubElement(properties, f"{W}jc")
    alignment.set(f"{W}val", "center")
    spacing = ET.SubElement(properties, f"{W}spacing")
    spacing.set(f"{W}before", "120")
    spacing.set(f"{W}after", "120")
    run = ET.SubElement(paragraph, f"{W}r")
    run_properties = ET.SubElement(run, f"{W}rPr")
    ET.SubElement(run_properties, f"{W}b")
    color = ET.SubElement(run_properties, f"{W}color")
    color.set(f"{W}val", "C00000")
    highlight = ET.SubElement(run_properties, f"{W}highlight")
    highlight.set(f"{W}val", "yellow")
    size = ET.SubElement(run_properties, f"{W}sz")
    size.set(f"{W}val", "28")
    text = ET.SubElement(run, f"{W}t")
    text.text = AI_FILE_NOTICE
    body.insert(list(body).index(after) + 1, paragraph)


def _patch_document(xml_bytes: bytes, will: dict[str, Any]) -> bytes:
    _namespaces(xml_bytes)
    root = ET.fromstring(xml_bytes)
    body = root.find(f".//{W}body")
    if body is None:
        raise ValueError("template body not found")

    metadata = will["metadata"]
    testator = will["testator"]
    signature = will["signature"]
    number_paragraph = _find_contains(body, "（遗嘱编号：")
    replacements = (
        (number_paragraph, f"（遗嘱编号：{metadata['will_number']}）"),
        (_find_contains(body, "立遗嘱地点：中国·浙江省"), f"立遗嘱地点：{metadata['execution_place']}"),
        (_find_contains(body, "立遗嘱时间："), f"立遗嘱时间：{metadata['execution_date']}"),
        (_find_contains(body, "立遗嘱人："), f"立遗嘱人：{testator['name']}"),
        (_find_contains(body, "性别："), f"性别：{testator['gender']}"),
        (_find_contains(body, "国籍："), f"国籍：{testator['nationality']}"),
        (_find_contains(body, "身份证号/护照号："), f"身份证号/护照号：{testator['identity_number']}"),
        (_find_contains(body, "联系电话："), f"联系电话：{testator['phone']}"),
        (_find_contains(body, "联系地址："), f"联系地址：{testator['address']}"),
        (_find_contains(body, "立遗嘱人（签名+捺印）："), f"立遗嘱人（签名+捺印）：{signature['signer_display']}"),
        (_find_contains(body, "立遗嘱日期：", last=True), f"立遗嘱日期：{signature['date_display']}"),
        (_find_contains(body, "立遗嘱地点：", last=True), f"立遗嘱地点：{signature['place_display']}"),
    )
    for paragraph, value in replacements:
        _replace_text(paragraph, value)
    _insert_ai_notice(body, number_paragraph)

    heading_nodes = {key: _find_exact(body, heading) for key, heading in HEADINGS.items()}
    end_nodes = list(heading_nodes.values())[1:] + [_find_exact(body, SIGNING_MARKER)]
    for key, end in reversed(list(zip(WILL_SECTION_KEYS, end_nodes))):
        _replace_clause_block(body, heading_nodes[key], end, will["sections"][key])

    result = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    _verify_document_xml(result)
    return result


def _verify_document_xml(xml_bytes: bytes) -> None:
    root = ET.fromstring(xml_bytes)
    body = root.find(f".//{W}body")
    if body is None:
        raise ValueError("generated document body missing")
    texts = [_text(paragraph).strip() for paragraph in _paragraphs(body)]
    positions = []
    for heading in HEADINGS.values():
        if texts.count(heading) != 1:
            raise ValueError(f"generated document heading mismatch: {heading}")
        positions.append(texts.index(heading))
    if positions != sorted(positions):
        raise ValueError("generated document headings are out of order")
    if texts.count(SIGNING_MARKER) != 1:
        raise ValueError("generated document signing marker missing")
    if texts.count(AI_FILE_NOTICE) != 1:
        raise ValueError("generated document AI notice missing or duplicated")
    if len(root.findall(f".//{W}sectPr")) != 2:
        raise ValueError("generated document must retain exactly two section properties")


def build_will_docx(case: dict[str, Any], output: Path, template: Path | None = None, force: bool = False) -> dict[str, Any]:
    report = validate_case(case)
    if not report["valid"]:
        raise ValueError("case validation has errors; will generation is closed")
    if case.get("will_document", {}).get("review_status") != "draft_pending_review":
        raise ValueError("only draft_pending_review AI drafts may be generated")
    if case.get("status") not in OUTPUT_GATE_STATUSES:
        raise ValueError("case status is not in the AI draft output gate")
    if case.get("legal_research", {}).get("status") != "verified":
        raise ValueError("legal research gate is not verified")
    template = template or _template_path()
    template_bytes = template.read_bytes()
    digest = hashlib.sha256(template_bytes).hexdigest()
    if digest != TEMPLATE_SHA256:
        raise ValueError(f"template SHA-256 mismatch: {digest}")
    if output.exists() and not force:
        raise FileExistsError(f"output already exists: {output}")

    input_buffer = io.BytesIO(template_bytes)
    output_buffer = io.BytesIO()
    with zipfile.ZipFile(input_buffer, "r") as source:
        names = source.namelist()
        if "word/document.xml" not in names:
            raise ValueError("template word/document.xml missing")
        patched = _patch_document(source.read("word/document.xml"), case["will_document"])
        with zipfile.ZipFile(output_buffer, "w") as target:
            for info in source.infolist():
                payload = patched if info.filename == "word/document.xml" else source.read(info.filename)
                target.writestr(info, payload)

    generated = output_buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(generated), "r") as package:
        headers = [name for name in package.namelist() if re.fullmatch(r"word/header\d+\.xml", name)]
        footers = [name for name in package.namelist() if re.fullmatch(r"word/footer\d+\.xml", name)]
        if len(headers) != 2 or len(footers) != 5:
            raise ValueError("generated package did not retain the template headers and footers")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(generated)
    return {
        "output": str(output),
        "template_sha256": digest,
        "output_sha256": hashlib.sha256(generated).hexdigest(),
        "review_status": case["will_document"]["review_status"],
        "ai_notice": AI_FILE_NOTICE,
        "template_parts_preserved": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_file", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_will_docx(_load_json(args.case_file), args.output, args.template, args.force)
    except (OSError, json.JSONDecodeError, ValueError, FileExistsError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
