#!/usr/bin/env python3
"""Shared OOXML revision engine for contract-review skills (SSOT).

零行为变更抽取：本模块的 26 个函数在 fadada-professional-contract-review 与
english-contract-review 的 review_docx.py 中字节级一致（make_text_run 仅
差一个 XML_SPACE 常量化，功能相同）。两技能的 review_docx.py 从本模块导入
这些 OOXML 原语，各自保留含设计/数据模型差异的高层算子（apply_operations、
apply_replace_text_direct、revision_summary_table 等）与子命令。

编辑真源：_shared/contract-review-core/scripts/ooxml_engine.py
物化同步：sync_shared.py（各技能包内保留副本，--check 防漂移）
"""

from __future__ import annotations

import copy
import datetime as dt
import difflib
import json
import re
import zipfile
from pathlib import Path

from skill_paths import generated_path
from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
NS = {"w": W_NS, "r": R_NS}
W = f"{{{W_NS}}}"
REVISION_AUTHOR = "法大大iTerms"
REVISION_INITIALS = "FDD"
COMMENTS_NAME = "word/comments.xml"
COMMENTS_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
)
TOKEN_RE = re.compile(r"\s+|[^\s]+")
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def xml(data: bytes):
    return etree.fromstring(data)


def visible_text(paragraph) -> str:
    values = paragraph.xpath(
        ".//w:t[not(ancestor::w:del)]/text() | "
        ".//w:tab[not(ancestor::w:del)] | "
        ".//w:br[not(ancestor::w:del)]",
        namespaces=NS,
    )
    parts: list[str] = []
    for value in values:
        if isinstance(value, str):
            parts.append(value)
        elif value.tag == W + "tab":
            parts.append("\t")
        elif value.tag == W + "br":
            parts.append("\n")
    return "".join(parts)


def paragraph_flags(paragraph) -> dict[str, bool]:
    return {
        "in_table": bool(paragraph.xpath("ancestor::w:tbl", namespaces=NS)),
        "has_revisions": bool(
            paragraph.xpath(".//w:ins | .//w:del | .//w:moveFrom | .//w:moveTo", namespaces=NS)
        ),
        "has_comments": bool(
            paragraph.xpath(
                ".//w:commentRangeStart | .//w:commentRangeEnd | .//w:commentReference",
                namespaces=NS,
            )
        ),
        "has_drawing": bool(paragraph.xpath(".//w:drawing | .//w:pict", namespaces=NS)),
        "has_field": bool(
            paragraph.xpath(".//w:fldChar | .//w:instrText | .//w:fldSimple", namespaces=NS)
        ),
    }


def body_paragraphs(root) -> list:
    return root.xpath(".//w:body//w:p", namespaces=NS)


def extract_document(input_path: Path, output_path: Path) -> None:
    output_path = generated_path(output_path, "extracted review data")
    with zipfile.ZipFile(input_path) as archive:
        root = xml(archive.read("word/document.xml"))
    records = []
    for index, paragraph in enumerate(body_paragraphs(root), start=1):
        records.append(
            {
                "id": f"p{index:04d}",
                "text": visible_text(paragraph),
                **paragraph_flags(paragraph),
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "source": input_path.name,
                "paragraph_count": len(records),
                "paragraphs": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"extracted {len(records)} paragraphs to {output_path}")


def first_run_properties(paragraph):
    values = paragraph.xpath(".//w:r/w:rPr", namespaces=NS)
    return copy.deepcopy(values[0]) if values else None


def make_text_run(text: str, run_properties=None, deleted: bool = False):
    run = etree.Element(W + "r")
    if run_properties is not None:
        run.append(copy.deepcopy(run_properties))
    text_node = etree.SubElement(run, W + ("delText" if deleted else "t"))
    if text.startswith((" ", "\t", "\n")) or text.endswith((" ", "\t", "\n")):
        text_node.set(XML_SPACE, "preserve")
    text_node.text = text
    return run


def revision_element(tag: str, revision_id: int, timestamp: str):
    element = etree.Element(W + tag)
    element.set(W + "id", str(revision_id))
    element.set(W + "author", REVISION_AUTHOR)
    element.set(W + "date", timestamp)
    return element


def rebuild_with_revisions(
    paragraph,
    original: str,
    replacement: str,
    revision_id: int,
    timestamp: str,
) -> int:
    p_pr = paragraph.find(W + "pPr")
    run_properties = first_run_properties(paragraph)
    for child in list(paragraph):
        if child is not p_pr:
            paragraph.remove(child)

    # 条款级修订（真机 ffe8b7fb 修复）：整段原文作单处删除、整段新文作单处插入，
    # 一个被改条款只产出一处"改前→改后"修订。旧版用 SequenceMatcher 逐 token 对齐，
    # 重改条款会拆成大量交错的 <w:del>/<w:ins> 词级碎片，审阅时修订项过多、难以通读。
    next_id = revision_id
    if original:
        deleted = revision_element("del", next_id, timestamp)
        next_id += 1
        deleted.append(make_text_run(original, run_properties, deleted=True))
        paragraph.append(deleted)
    if replacement:
        inserted = revision_element("ins", next_id, timestamp)
        next_id += 1
        inserted.append(make_text_run(replacement, run_properties))
        paragraph.append(inserted)
    return next_id


def insert_paragraph_revision(
    anchor_paragraph,
    text: str,
    revision_id: int,
    timestamp: str,
):
    """在 anchor 段落之后插入一个「整段新增」修订段（真机 a2c4fdd7 能力补全）。

    过去红线管线只有 replace/replace_text/comment，无法把缺失保护条款物理写进
    合同正文，只能批注——下游核验要求"物理插入"时修复无从下手，演变为整轮重做。
    本函数补上 `insert` 动作的底层能力：
      - 新段的段落标记本身打 `w:pPr/w:rPr/w:ins`（OOXML 整段插入的标准标法），
        Word 中拒绝该修订会删除整个段落而非留下空段；
      - 段内文本包在 `w:ins` 中，沿用 anchor 首个 run 的字符属性保持版式一致。
    返回 (新段元素, 下一个 revision_id)；新段元素供调用方锚定批注。
    """
    run_properties = first_run_properties(anchor_paragraph)
    paragraph = etree.Element(W + "p")
    p_pr = etree.SubElement(paragraph, W + "pPr")
    anchor_ppr = anchor_paragraph.find(W + "pPr")
    if anchor_ppr is not None:
        for child in anchor_ppr:
            if child.tag != W + "rPr":
                p_pr.append(copy.deepcopy(child))
    r_pr = etree.SubElement(p_pr, W + "rPr")
    r_pr.append(revision_element("ins", revision_id, timestamp))
    next_id = revision_id + 1

    inserted = revision_element("ins", next_id, timestamp)
    next_id += 1
    inserted.append(make_text_run(text, run_properties))
    paragraph.append(inserted)
    anchor_paragraph.addnext(paragraph)
    return paragraph, next_id


def ensure_track_revisions(settings_root) -> None:
    if settings_root.find(W + "trackRevisions") is None:
        settings_root.insert(0, etree.Element(W + "trackRevisions"))


def next_numeric_id(root, xpath: str) -> int:
    values = []
    for value in root.xpath(xpath, namespaces=NS):
        try:
            values.append(int(value))
        except (TypeError, ValueError):
            pass
    return max(values, default=-1) + 1


def comments_root(package: dict[str, bytes]):
    if COMMENTS_NAME in package:
        return xml(package[COMMENTS_NAME])
    return etree.Element(W + "comments", nsmap={"w": W_NS})


def ensure_comments_plumbing(package: dict[str, bytes], comments) -> None:
    content_types = xml(package["[Content_Types].xml"])
    override_path = f"{{{CT_NS}}}Override"
    found = content_types.xpath(
        "./ct:Override[@PartName='/word/comments.xml']",
        namespaces={"ct": CT_NS},
    )
    if not found:
        override = etree.SubElement(content_types, override_path)
        override.set("PartName", "/word/comments.xml")
        override.set(
            "ContentType",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
        )
    package["[Content_Types].xml"] = etree.tostring(
        content_types, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    rels_name = "word/_rels/document.xml.rels"
    rels = xml(package[rels_name])
    matching = rels.xpath(
        "./pr:Relationship[@Type=$relationship_type]",
        namespaces={"pr": PKG_REL_NS},
        relationship_type=COMMENTS_REL_TYPE,
    )
    if not matching:
        used = {
            item.get("Id")
            for item in rels.xpath("./pr:Relationship", namespaces={"pr": PKG_REL_NS})
        }
        number = 1
        while f"rId{number}" in used:
            number += 1
        relationship = etree.SubElement(rels, f"{{{PKG_REL_NS}}}Relationship")
        relationship.set("Id", f"rId{number}")
        relationship.set("Type", COMMENTS_REL_TYPE)
        relationship.set("Target", "comments.xml")
    package[rels_name] = etree.tostring(
        rels, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    package[COMMENTS_NAME] = etree.tostring(
        comments, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def add_comment(
    paragraph,
    comments,
    comment_id: int,
    text: str,
    timestamp: str,
) -> None:
    comment = etree.SubElement(comments, W + "comment")
    comment.set(W + "id", str(comment_id))
    comment.set(W + "author", REVISION_AUTHOR)
    comment.set(W + "initials", REVISION_INITIALS)
    comment.set(W + "date", timestamp)
    p = etree.SubElement(comment, W + "p")
    r = etree.SubElement(p, W + "r")
    # 按 \n 切分渲染，使批注按内容维度真正换行（单个 <w:t> 不渲染 \n）。
    for index, line in enumerate(str(text or "").split("\n")):
        if index:
            etree.SubElement(r, W + "br")
        t = etree.SubElement(r, W + "t")
        t.set(XML_SPACE, "preserve")
        t.text = line

    start = etree.Element(W + "commentRangeStart")
    start.set(W + "id", str(comment_id))
    end = etree.Element(W + "commentRangeEnd")
    end.set(W + "id", str(comment_id))
    reference_run = etree.Element(W + "r")
    reference = etree.SubElement(reference_run, W + "commentReference")
    reference.set(W + "id", str(comment_id))

    children = list(paragraph)
    insert_at = 1 if children and children[0].tag == W + "pPr" else 0
    paragraph.insert(insert_at, start)
    paragraph.append(end)
    paragraph.append(reference_run)


def remove_comments_from_root(root) -> None:
    for node in root.xpath(
        ".//w:commentRangeStart | .//w:commentRangeEnd | .//w:commentReference",
        namespaces=NS,
    ):
        parent = node.getparent()
        if parent is not None:
            if parent.tag == W + "r" and node.tag == W + "commentReference":
                grandparent = parent.getparent()
                if grandparent is not None:
                    grandparent.remove(parent)
            else:
                parent.remove(node)


def accept_revisions(root) -> None:
    for node in root.xpath(".//w:del | .//w:moveFrom", namespaces=NS):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    for node in root.xpath(".//w:ins | .//w:moveTo", namespaces=NS):
        parent = node.getparent()
        if parent is None:
            continue
        index = parent.index(node)
        for child in list(node):
            node.remove(child)
            parent.insert(index, child)
            index += 1
        parent.remove(node)
    remove_comments_from_root(root)


def reject_revisions(root) -> None:
    # 整段插入的段落（段落标记带 w:pPr/w:rPr/w:ins）拒绝时应整段删除，
    # 而非仅剥掉 w:ins 留下空段。
    for paragraph in root.xpath(".//w:p[w:pPr/w:rPr/w:ins]", namespaces=NS):
        parent = paragraph.getparent()
        if parent is not None:
            parent.remove(paragraph)
    for node in root.xpath(".//w:ins | .//w:moveTo", namespaces=NS):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    for node in root.xpath(".//w:del | .//w:moveFrom", namespaces=NS):
        parent = node.getparent()
        if parent is None:
            continue
        index = parent.index(node)
        for child in list(node):
            for deleted_text in child.xpath(".//w:delText", namespaces=NS):
                deleted_text.tag = W + "t"
            node.remove(child)
            parent.insert(index, child)
            index += 1
        parent.remove(node)
    remove_comments_from_root(root)


def remove_comments_plumbing(package: dict[str, bytes]) -> None:
    package.pop(COMMENTS_NAME, None)

    content_types = xml(package["[Content_Types].xml"])
    for node in content_types.xpath(
        "./ct:Override[@PartName='/word/comments.xml']",
        namespaces={"ct": CT_NS},
    ):
        content_types.remove(node)
    package["[Content_Types].xml"] = etree.tostring(
        content_types, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    rels_name = "word/_rels/document.xml.rels"
    rels = xml(package[rels_name])
    for node in rels.xpath(
        "./pr:Relationship[@Type=$relationship_type]",
        namespaces={"pr": PKG_REL_NS},
        relationship_type=COMMENTS_REL_TYPE,
    ):
        rels.remove(node)
    package[rels_name] = etree.tostring(
        rels, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def remove_track_revisions(settings_root) -> None:
    for node in settings_root.xpath("./w:trackRevisions", namespaces=NS):
        settings_root.remove(node)


def append_plain_paragraph(
    body,
    text: str,
    style: str | None = None,
    page_break_before: bool = False,
) -> None:
    paragraph = etree.Element(W + "p")
    if style or page_break_before:
        p_pr = etree.SubElement(paragraph, W + "pPr")
        if style:
            p_style = etree.SubElement(p_pr, W + "pStyle")
            p_style.set(W + "val", style)
        if page_break_before:
            etree.SubElement(p_pr, W + "pageBreakBefore")
    run = etree.SubElement(paragraph, W + "r")
    text_node = etree.SubElement(run, W + "t")
    text_node.text = text
    sect_pr = body.find(W + "sectPr")
    if sect_pr is None:
        body.append(paragraph)
    else:
        body.insert(body.index(sect_pr), paragraph)


def insert_before_section(body, element) -> None:
    sect_pr = body.find(W + "sectPr")
    if sect_pr is None:
        body.append(element)
    else:
        body.insert(body.index(sect_pr), element)


def table_cell(text: str, width: int, bold: bool = False):
    cell = etree.Element(W + "tc")
    tc_pr = etree.SubElement(cell, W + "tcPr")
    tc_w = etree.SubElement(tc_pr, W + "tcW")
    tc_w.set(W + "w", str(width))
    tc_w.set(W + "type", "dxa")
    paragraph = etree.SubElement(cell, W + "p")
    run = etree.SubElement(paragraph, W + "r")
    if bold:
        r_pr = etree.SubElement(run, W + "rPr")
        etree.SubElement(r_pr, W + "b")
    text_node = etree.SubElement(run, W + "t")
    text_node.text = text
    return cell


def serialize(root) -> bytes:
    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def read_package(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def write_package(path: Path, package: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in package.items():
            archive.writestr(name, data)


def replacement_for(operation: dict, current: str) -> str:
    action = operation.get("action")
    if action == "replace":
        replacement = operation.get("new_text")
        if not isinstance(replacement, str):
            raise ValueError("replace requires new_text")
        return replacement
    if action == "replace_text":
        old_text = operation.get("old_text")
        new_text = operation.get("new_text")
        if not isinstance(old_text, str) or not isinstance(new_text, str):
            raise ValueError("replace_text requires old_text and new_text")
        if old_text not in current:
            raise ValueError(f"old_text not found: {old_text!r}")
        return current.replace(old_text, new_text, 1)
    raise ValueError(f"unsupported replacement action: {action}")


__all__ = [
    "xml",
    "visible_text",
    "paragraph_flags",
    "body_paragraphs",
    "extract_document",
    "first_run_properties",
    "make_text_run",
    "revision_element",
    "rebuild_with_revisions",
    "insert_paragraph_revision",
    "ensure_track_revisions",
    "next_numeric_id",
    "comments_root",
    "ensure_comments_plumbing",
    "add_comment",
    "remove_comments_from_root",
    "accept_revisions",
    "reject_revisions",
    "remove_comments_plumbing",
    "remove_track_revisions",
    "append_plain_paragraph",
    "insert_before_section",
    "table_cell",
    "serialize",
    "read_package",
    "write_package",
    "replacement_for",
    "W_NS",
    "R_NS",
    "PKG_REL_NS",
    "CT_NS",
    "NS",
    "W",
    "REVISION_AUTHOR",
    "REVISION_INITIALS",
    "COMMENTS_NAME",
    "COMMENTS_REL_TYPE",
    "TOKEN_RE",
    "XML_SPACE",
    "generated_path",
    "etree",
]
