from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from copy import deepcopy
from difflib import SequenceMatcher
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
import unicodedata
from zipfile import ZIP_DEFLATED, ZipFile

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
CONTENT_TYPE_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("w", WORD_NS)


@dataclass
class CommentPayload:
    paragraph_id: str
    excerpt: str
    body: str
    author: str
    comment_title: str


@dataclass
class CommentExportResult:
    output_path: Path
    applied_count: int
    skipped_count: int
    status: str
    message: str = ""


def export_docx_with_comments(source_path: Path, output_path: Path, comments: list[CommentPayload]) -> CommentExportResult:
    if not comments:
        return CommentExportResult(
            output_path=output_path,
            applied_count=0,
            skipped_count=0,
            status="no_annotation_needed",
            message="合同无风险，无需生成批注版。",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, output_path)

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        with ZipFile(output_path, "r") as archive:
            archive.extractall(temp_path)

        document_xml = temp_path / "word" / "document.xml"
        comments_xml = temp_path / "word" / "comments.xml"
        rels_xml = temp_path / "word" / "_rels" / "document.xml.rels"
        content_types_xml = temp_path / "[Content_Types].xml"

        _ensure_comments_part(comments_xml)
        _ensure_comments_relationship(rels_xml)
        _ensure_comments_content_type(content_types_xml)
        applied_count = _inject_comments(document_xml, comments_xml, comments)

        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
            for file_path in temp_path.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(temp_path).as_posix())

    if applied_count == 0:
        output_path.unlink(missing_ok=True)
        return CommentExportResult(
            output_path=output_path,
            applied_count=0,
            skipped_count=len(comments),
            status="failed",
            message="存在命中风险，但未能写入任何批注。",
        )

    return CommentExportResult(
        output_path=output_path,
        applied_count=applied_count,
        skipped_count=len(comments) - applied_count,
        status="deliverable",
    )


def _resolve_element_by_pid(document_root: ET.Element, pid: str) -> ET.Element | None:
    body = document_root.find(f"{{{WORD_NS}}}body")
    if body is None:
        return None

    p_index = None
    if pid.startswith("p") and pid[1:].isdigit():
        p_index = int(pid[1:]) - 1
    elif pid.isdigit():
        p_index = int(pid) - 1

    if p_index is not None:
        top_ps = body.findall(f"{{{WORD_NS}}}p")
        if 0 <= p_index < len(top_ps):
            return top_ps[p_index]
        return None

    if pid.startswith("t") and "r" in pid:
        try:
            cell_match = re.fullmatch(r"t(\d+)r(\d+)c(\d+)p(\d+)", pid)
            if cell_match:
                t_index = int(cell_match.group(1)) - 1
                r_index = int(cell_match.group(2)) - 1
                c_index = int(cell_match.group(3)) - 1
                p_index = int(cell_match.group(4)) - 1
                top_tbls = body.findall(f"{{{WORD_NS}}}tbl")
                if 0 <= t_index < len(top_tbls):
                    tbl = top_tbls[t_index]
                    rows = tbl.findall(f"./{{{WORD_NS}}}tr")
                    if 0 <= r_index < len(rows):
                        row = rows[r_index]
                        cells = row.findall(f"./{{{WORD_NS}}}tc")
                        if 0 <= c_index < len(cells):
                            cell = cells[c_index]
                            paragraphs = cell.findall(f"./{{{WORD_NS}}}p")
                            if 0 <= p_index < len(paragraphs):
                                return paragraphs[p_index]
                return None

            t_part, r_part = pid[1:].split("r")
            t_index = int(t_part) - 1
            r_index = int(r_part) - 1
            top_tbls = body.findall(f"{{{WORD_NS}}}tbl")
            if 0 <= t_index < len(top_tbls):
                tbl = top_tbls[t_index]
                trs = tbl.findall(f".//{{{WORD_NS}}}tr")
                if 0 <= r_index < len(trs):
                    tr = trs[r_index]
                    ps = tr.findall(f".//{{{WORD_NS}}}p")
                    if ps:
                        return ps[0]
        except ValueError:
            pass

    return None


def _ensure_comments_part(comments_xml: Path) -> None:
    if comments_xml.exists():
        return
    root = ET.Element(f"{{{WORD_NS}}}comments")
    ET.ElementTree(root).write(comments_xml, encoding="utf-8", xml_declaration=True)


def _ensure_comments_relationship(rels_xml: Path) -> None:
    tree = ET.parse(rels_xml)
    root = tree.getroot()
    for relationship in root.findall(f"{{{REL_NS}}}Relationship"):
        if relationship.attrib.get("Type") == DOC_REL_TYPE:
            tree.write(rels_xml, encoding="utf-8", xml_declaration=True)
            return
    existing_ids = [
        int(rel.attrib["Id"][3:])
        for rel in root.findall(f"{{{REL_NS}}}Relationship")
        if rel.attrib.get("Id", "").startswith("rId") and rel.attrib["Id"][3:].isdigit()
    ]
    next_id = max(existing_ids, default=0) + 1
    ET.SubElement(
        root,
        f"{{{REL_NS}}}Relationship",
        {"Id": f"rId{next_id}", "Type": DOC_REL_TYPE, "Target": "comments.xml"},
    )
    tree.write(rels_xml, encoding="utf-8", xml_declaration=True)


def _ensure_comments_content_type(content_types_xml: Path) -> None:
    tree = ET.parse(content_types_xml)
    root = tree.getroot()
    for override in root.findall(f"{{{CONTENT_TYPE_NS}}}Override"):
        if override.attrib.get("PartName") == "/word/comments.xml":
            tree.write(content_types_xml, encoding="utf-8", xml_declaration=True)
            return
    ET.SubElement(
        root,
        f"{{{CONTENT_TYPE_NS}}}Override",
        {
            "PartName": "/word/comments.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
        },
    )
    tree.write(content_types_xml, encoding="utf-8", xml_declaration=True)


def _inject_comments(document_xml: Path, comments_xml: Path, comments: list[CommentPayload]) -> int:
    document_tree = ET.parse(document_xml)
    document_root = document_tree.getroot()
    comments_tree = ET.parse(comments_xml)
    comments_root = comments_tree.getroot()

    existing_ids = [
        int(comment.attrib.get(f"{{{WORD_NS}}}id", "0"))
        for comment in comments_root.findall(f"{{{WORD_NS}}}comment")
        if comment.attrib.get(f"{{{WORD_NS}}}id", "0").isdigit()
    ]
    next_id = max(existing_ids, default=-1) + 1
    applied = 0

    for payload in comments:
        paragraph = _resolve_element_by_pid(document_root, payload.paragraph_id)
        if paragraph is None:
            continue

        comment_id = str(next_id)
        next_id += 1

        _attach_comment_range(paragraph, payload.excerpt, comment_id)
        _append_comment(comments_root, comment_id, payload)
        applied += 1

    document_tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    comments_tree.write(comments_xml, encoding="utf-8", xml_declaration=True)
    return applied


def _append_comment(comments_root: ET.Element, comment_id: str, payload: CommentPayload) -> None:
    attrs = {
        f"{{{WORD_NS}}}id": comment_id,
        f"{{{WORD_NS}}}author": payload.author,
        f"{{{WORD_NS}}}initials": "AI",
        f"{{{WORD_NS}}}date": datetime.now(timezone.utc).isoformat(),
    }
    comment = ET.SubElement(comments_root, f"{{{WORD_NS}}}comment", attrs)
    paragraph = ET.SubElement(comment, f"{{{WORD_NS}}}p")
    run = ET.SubElement(paragraph, f"{{{WORD_NS}}}r")
    _append_multiline_text(run, payload.body)


def _append_multiline_text(run: ET.Element, body: str) -> None:
    lines = body.split("\n")
    for index, line in enumerate(lines):
        if index > 0:
            ET.SubElement(run, f"{{{WORD_NS}}}br")
        text = ET.SubElement(run, f"{{{WORD_NS}}}t")
        if line.startswith(" ") or line.endswith(" "):
            text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        text.text = line


def _attach_comment_range(paragraph: ET.Element, excerpt: str, comment_id: str) -> None:
    span = _find_excerpt_span(_paragraph_text(paragraph), excerpt)
    if span is None:
        _attach_comment_to_whole_paragraph(paragraph, comment_id)
        return

    start_index, end_index = span
    target_runs = _resolve_target_runs(paragraph, start_index, end_index)
    if not target_runs:
        _attach_comment_to_whole_paragraph(paragraph, comment_id)
        return

    first_run, last_run = target_runs
    start = ET.Element(f"{{{WORD_NS}}}commentRangeStart", {f"{{{WORD_NS}}}id": comment_id})
    end = ET.Element(f"{{{WORD_NS}}}commentRangeEnd", {f"{{{WORD_NS}}}id": comment_id})
    ref_run = ET.Element(f"{{{WORD_NS}}}r")
    ET.SubElement(ref_run, f"{{{WORD_NS}}}commentReference", {f"{{{WORD_NS}}}id": comment_id})

    paragraph.insert(_child_index(paragraph, first_run), start)
    paragraph.insert(_child_index(paragraph, last_run) + 1, end)
    paragraph.insert(_child_index(paragraph, end) + 1, ref_run)


def _attach_comment_to_whole_paragraph(paragraph: ET.Element, comment_id: str) -> None:
    runs = paragraph.findall(f"{{{WORD_NS}}}r")
    if not runs:
        ET.SubElement(paragraph, f"{{{WORD_NS}}}r")
        runs = paragraph.findall(f"{{{WORD_NS}}}r")

    start = ET.Element(f"{{{WORD_NS}}}commentRangeStart", {f"{{{WORD_NS}}}id": comment_id})
    end = ET.Element(f"{{{WORD_NS}}}commentRangeEnd", {f"{{{WORD_NS}}}id": comment_id})
    ref_run = ET.Element(f"{{{WORD_NS}}}r")
    ET.SubElement(ref_run, f"{{{WORD_NS}}}commentReference", {f"{{{WORD_NS}}}id": comment_id})

    paragraph.insert(_child_index(paragraph, runs[0]), start)
    paragraph.append(end)
    paragraph.append(ref_run)


def _paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for run in paragraph.findall(f"{{{WORD_NS}}}r"):
        parts.append(_run_text(run))
    return "".join(parts)


def _run_text(run: ET.Element) -> str:
    parts: list[str] = []
    for child in run:
        if child.tag == f"{{{WORD_NS}}}t":
            parts.append(child.text or "")
        elif child.tag == f"{{{WORD_NS}}}tab":
            parts.append("\t")
        elif child.tag == f"{{{WORD_NS}}}br":
            parts.append("\n")
    return "".join(parts)


def _find_excerpt_span(paragraph_text: str, excerpt: str) -> tuple[int, int] | None:
    paragraph_text = paragraph_text or ""
    excerpt = (excerpt or "").strip()
    if not paragraph_text or not excerpt:
        return None

    direct = paragraph_text.find(excerpt)
    if direct >= 0:
        return direct, direct + len(excerpt)

    normalized_paragraph, paragraph_index_map = _normalize_with_index_map(paragraph_text)
    normalized_excerpt, _ = _normalize_with_index_map(excerpt)
    if not normalized_excerpt:
        return None

    normalized_start = normalized_paragraph.find(normalized_excerpt)
    if normalized_start < 0:
        fuzzy_span = _find_fuzzy_normalized_span(normalized_paragraph, normalized_excerpt)
        if fuzzy_span is None:
            return None
        normalized_start, normalized_end = fuzzy_span
    else:
        normalized_end = normalized_start + len(normalized_excerpt) - 1

    start_index = paragraph_index_map[normalized_start]
    end_index = paragraph_index_map[normalized_end] + 1
    return start_index, end_index


def _normalize_with_index_map(text: str) -> tuple[str, list[int]]:
    normalized_chars: list[str] = []
    index_map: list[int] = []
    for index, char in enumerate(text):
        normalized = _normalize_match_char(char)
        if not normalized:
            continue
        for normalized_char in normalized:
            normalized_chars.append(normalized_char)
            index_map.append(index)
    return "".join(normalized_chars), index_map


def _normalize_match_char(char: str) -> str:
    normalized = unicodedata.normalize("NFKC", char)
    normalized = normalized.translate(
        str.maketrans(
            {
                "，": ",",
                "。": ".",
                "；": ";",
                "：": ":",
                "（": "(",
                "）": ")",
                "【": "[",
                "】": "]",
                "“": "\"",
                "”": "\"",
                "‘": "'",
                "’": "'",
                "—": "-",
                "－": "-",
                "、": ",",
            }
        )
    )
    if not normalized or normalized.isspace():
        return ""
    return normalized.lower()


def _find_fuzzy_normalized_span(normalized_paragraph: str, normalized_excerpt: str) -> tuple[int, int] | None:
    if not normalized_paragraph or not normalized_excerpt:
        return None

    excerpt_len = len(normalized_excerpt)
    min_len = max(4, excerpt_len - 4)
    max_len = min(len(normalized_paragraph), excerpt_len + 4)
    best: tuple[float, int, int] | None = None

    for window_len in range(min_len, max_len + 1):
        for start in range(0, len(normalized_paragraph) - window_len + 1):
            candidate = normalized_paragraph[start : start + window_len]
            score = SequenceMatcher(None, candidate, normalized_excerpt).ratio()
            if score < 0.92:
                continue
            if best is None or score > best[0]:
                best = (score, start, start + window_len - 1)

    if best is None:
        return None
    return best[1], best[2]


def _resolve_target_runs(paragraph: ET.Element, start_index: int, end_index: int) -> tuple[ET.Element, ET.Element] | None:
    runs = paragraph.findall(f"{{{WORD_NS}}}r")
    if not runs:
        return None

    cursor = 0
    start_run: ET.Element | None = None
    end_run: ET.Element | None = None

    for run in list(runs):
        text = _run_text(run)
        length = len(text)
        run_start = cursor
        run_end = cursor + length
        cursor = run_end
        if length == 0:
            continue

        if start_run is None and run_start <= start_index < run_end:
            local_start = start_index - run_start
            if local_start > 0:
                run = _split_run_at(paragraph, run, local_start)
                text = _run_text(run)
                length = len(text)
                run_start = start_index
                run_end = run_start + length
            start_run = run

        if start_run is not None and run_start < end_index <= run_end:
            local_end = end_index - run_start
            if 0 < local_end < len(_run_text(run)):
                _split_run_at(paragraph, run, local_end)
            end_run = run
            break

    if start_run is None or end_run is None:
        return None
    return start_run, end_run


def _split_run_at(paragraph: ET.Element, run: ET.Element, split_index: int) -> ET.Element:
    text = _run_text(run)
    if split_index <= 0 or split_index >= len(text):
        return run

    left_text = text[:split_index]
    right_text = text[split_index:]
    _replace_run_text(run, left_text)

    new_run = deepcopy(run)
    _replace_run_text(new_run, right_text)

    insert_at = _child_index(paragraph, run) + 1
    paragraph.insert(insert_at, new_run)
    return new_run


def _replace_run_text(run: ET.Element, text: str) -> None:
    for child in list(run):
        if child.tag in {f"{{{WORD_NS}}}t", f"{{{WORD_NS}}}tab", f"{{{WORD_NS}}}br"}:
            run.remove(child)

    if not text:
        return

    text_element = ET.Element(f"{{{WORD_NS}}}t")
    if text.startswith(" ") or text.endswith(" "):
        text_element.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_element.text = text
    run.append(text_element)

def _child_index(parent: ET.Element, child: ET.Element) -> int:
    for index, current in enumerate(list(parent)):
        if current is child:
            return index
    raise ValueError("Child element not found in parent.")
