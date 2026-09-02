#!/usr/bin/env python3
"""Extract and apply review operations using native WordprocessingML revisions."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import difflib
import json
import re
import zipfile
from pathlib import Path

from emoji_text import sanitize_text
from skill_paths import generated_path
from lxml import etree

from ooxml_engine import *  # shared OOXML revision engine (SSOT: _shared/contract-review-core)


REDLINE_MODES = ("revisions_only", "comments_only", "both")
TEXT_ACTIONS = {"replace", "replace_text"}
DECISION_VALUES = {
    "accept_proposed",
    "retain_original_accept_risk",
    "custom_text",
    "pending",
}
STYLES_NAME = "word/styles.xml"


def load_operations(path: Path) -> tuple[dict, list[dict]]:
    request = json.loads(path.read_text(encoding="utf-8"))
    operations = request.get("operations", [])
    if not operations:
        raise ValueError("operations list is empty")
    issue_ids: set[str] = set()
    for operation in operations:
        issue_id = str(operation.get("issue_id", "")).strip()
        if not issue_id:
            raise ValueError("every operation requires a stable issue_id")
        if issue_id in issue_ids:
            raise ValueError(f"duplicate issue_id: {issue_id}")
        issue_ids.add(issue_id)
        action = operation.get("action")
        if action not in TEXT_ACTIONS | {"comment"}:
            raise ValueError(f"{issue_id}: unsupported action: {action}")
    return request, operations


def requires_confirmation(operation: dict) -> bool:
    risk = str(operation.get("risk", "")).lower()
    return risk in {"high", "medium"} or operation.get("action") in TEXT_ACTIONS


def risk_label(value: str) -> str:
    return {
        "high": "高风险",
        "medium": "中风险",
        "low": "低风险",
    }.get(str(value).lower(), "待定")


def operation_comment(operation: dict) -> str:
    issue_id = operation["issue_id"]
    description = (
        operation.get("risk_description")
        or operation.get("comment")
        or "请结合交易背景复核该事项。"
    )
    recommendation = operation.get("recommended_action")
    suggested = operation.get("suggested_wording") or operation.get("new_text")
    if not recommendation:
        recommendation = (
            "建议采用下列英文修改措辞。"
            if suggested
            else "建议核实事实并在签署前作出明确决定。"
        )
    suggested = suggested or "不适用；该事项需通过事实确认或商业决策处理。"
    basis = operation.get("basis_tag", "[要点]")
    return sanitize_text(
        "\n".join(
            (
                f"风险编号：{issue_id}",
                f"风险等级：{risk_label(operation.get('risk', ''))}",
                f"风险说明：{description}",
                f"建议处理：{recommendation}",
                f"建议英文措辞：{suggested}",
                f"依据：{basis}",
            )
        )
    )


def initial_decision_state(
    input_path: Path,
    redline_path: Path,
    mode: str,
    operations: list[dict],
) -> dict:
    risk_decisions = []
    pending_issue_ids = []
    for operation in operations:
        blocking = requires_confirmation(operation)
        if blocking:
            pending_issue_ids.append(operation["issue_id"])
        risk_decisions.append(
            {
                "issue_id": operation["issue_id"],
                "target": operation.get("target"),
                "risk": operation.get("risk", "low"),
                "action": operation.get("action"),
                "requires_confirmation": blocking,
                "decision": "pending",
                "proposed_text": operation.get("new_text"),
            }
        )
    return {
        "schema_version": "1.0",
        "workflow_stage": "awaiting_risk_confirmation",
        "workflow_history": [
            "reviewing",
            "markup_ready",
            "awaiting_risk_confirmation",
        ],
        "source_file": input_path.name,
        "redline_file": redline_path.name,
        "redline_mode": mode,
        "risk_decisions": risk_decisions,
        "pending_issue_ids": pending_issue_ids,
        "clean_eligible": not pending_issue_ids,
    }


def write_json_output(path: Path, data: dict, label: str) -> None:
    path = generated_path(path, label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ensure_contract_page_format(root) -> None:
    for section in root.xpath(".//w:sectPr", namespaces=NS):
        page_size = section.find(W + "pgSz")
        if page_size is None:
            page_size = etree.SubElement(section, W + "pgSz")
        page_size.set(W + "w", "11906")
        page_size.set(W + "h", "16838")
        page_size.attrib.pop(W + "orient", None)
        margins = section.find(W + "pgMar")
        if margins is None:
            margins = etree.SubElement(section, W + "pgMar")
        margins.set(W + "top", "1304")
        margins.set(W + "bottom", "1304")
        margins.set(W + "left", "1474")
        margins.set(W + "right", "1474")


def ensure_black_heading_styles(package: dict[str, bytes]) -> None:
    if STYLES_NAME not in package:
        return
    styles = xml(package[STYLES_NAME])
    for style_id in ("Title", "Heading1", "Heading2"):
        matches = styles.xpath(
            ".//w:style[@w:styleId=$style_id]",
            namespaces=NS,
            style_id=style_id,
        )
        for style in matches:
            run_properties = style.find(W + "rPr")
            if run_properties is None:
                run_properties = etree.SubElement(style, W + "rPr")
            color = run_properties.find(W + "color")
            if color is None:
                color = etree.SubElement(run_properties, W + "color")
            color.set(W + "val", "000000")
    package[STYLES_NAME] = serialize(styles)


def prevent_signature_row_splits(root) -> None:
    signature_pattern = re.compile(
        r"\b(?:By|Signature|Signed by)\s*:|签署[：:]|签字[：:]|盖章[：:]",
        re.IGNORECASE,
    )
    for table in root.xpath(".//w:tbl", namespaces=NS):
        table_text = "".join(table.xpath(".//w:t/text()", namespaces=NS))
        if not signature_pattern.search(table_text):
            continue
        for row in table.xpath("./w:tr", namespaces=NS):
            row_properties = row.find(W + "trPr")
            if row_properties is None:
                row_properties = etree.Element(W + "trPr")
                row.insert(0, row_properties)
            if row_properties.find(W + "cantSplit") is None:
                etree.SubElement(row_properties, W + "cantSplit")


def revision_summary_table(summaries: list[dict]):
    widths = [900, 1000, 3800, 1000, 2100]
    table = etree.Element(W + "tbl")
    tbl_pr = etree.SubElement(table, W + "tblPr")
    tbl_w = etree.SubElement(tbl_pr, W + "tblW")
    tbl_w.set(W + "w", str(sum(widths)))
    tbl_w.set(W + "type", "dxa")
    borders = etree.SubElement(tbl_pr, W + "tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = etree.SubElement(borders, W + edge)
        border.set(W + "val", "single")
        border.set(W + "sz", "4")
        border.set(W + "color", "808080")
    grid = etree.SubElement(table, W + "tblGrid")
    for width in widths:
        grid_col = etree.SubElement(grid, W + "gridCol")
        grid_col.set(W + "w", str(width))

    header = etree.SubElement(table, W + "tr")
    header_pr = etree.SubElement(header, W + "trPr")
    etree.SubElement(header_pr, W + "tblHeader")
    etree.SubElement(header_pr, W + "cantSplit")
    for value, width in zip(
        ("风险编号", "条款", "审查说明", "风险等级", "依据来源"), widths
    ):
        header.append(table_cell(value, width, bold=True))
    for item in summaries:
        row = etree.SubElement(table, W + "tr")
        row_pr = etree.SubElement(row, W + "trPr")
        etree.SubElement(row_pr, W + "cantSplit")
        values = (
            item["issue_id"],
            item["target"],
            item["comment"],
            item["risk"],
            item["basis_tag"],
        )
        for value, width in zip(values, widths):
            row.append(table_cell(value, width))
    return table


def append_revision_summary(root, summaries: list[dict], mode: str) -> None:
    body = root.find(".//" + W + "body")
    append_plain_paragraph(
        body,
        "风险批注汇总" if mode == "comments_only" else "修订说明汇总",
        "Heading1",
        page_break_before=True,
    )
    insert_before_section(body, revision_summary_table(summaries))


def apply_replace_text_direct(
    paragraph,
    old_text: str,
    new_text: str,
    revision_id: int,
    timestamp: str,
) -> int:
    """Replace *old_text* with *new_text* as a single contiguous tracked-change
    block — one ``<w:del>`` wrapping the original phrase and one ``<w:ins>``
    carrying the replacement — avoiding word-by-word fragmentation from the
    SequenceMatcher-based full-paragraph diff."""

    # `visible_text` (extract) injects "\t" for <w:tab> and "\n" for <w:br>, so
    # old_text copied from extract output may carry them; but full_text below is
    # built from <w:t> nodes only and contains neither. Normalize old_text to the
    # <w:t>-only stream so matching aligns. The tab/break elements themselves
    # (indentation, line breaks) are left untouched — only <w:t> text is edited.
    old_text = old_text.replace("\t", "").replace("\n", "")
    if not old_text:
        raise ValueError(
            "old_text reduces to empty after removing tab/line-break markers; "
            "it must reference visible <w:t> text, not only \\t/\\n"
        )

    p_pr = paragraph.find(W + "pPr")
    rpr = first_run_properties(paragraph)

    # ---- 1. collect runs visible outside <w:del> ----
    visible_runs: list[tuple] = []  # (element, text_start, text)
    offset = 0
    for child in list(paragraph):
        if child is p_pr:
            continue
        if child.tag == W + "del":
            continue  # previously deleted text is invisible
        if child.tag == W + "ins":
            # recurse into <w:ins> — its <w:r> children are visible
            for r in child.xpath("./w:r", namespaces=NS):
                t_nodes = r.xpath("./w:t", namespaces=NS)
                if t_nodes and t_nodes[0].text:
                    txt = t_nodes[0].text
                    visible_runs.append((r, offset, txt))
                    offset += len(txt)
        elif child.tag == W + "r":
            t_nodes = child.xpath("./w:t", namespaces=NS)
            if t_nodes and t_nodes[0].text:
                txt = t_nodes[0].text
                visible_runs.append((child, offset, txt))
                offset += len(txt)

    full_text = "".join(r[2] for r in visible_runs)
    pos = full_text.find(old_text)
    if pos == -1:
        raise ValueError(f"old_text not found in paragraph: {old_text!r}")
    end_pos = pos + len(old_text)

    # ---- 2. locate the run span that covers old_text ----
    span = []
    for elem, start, txt in visible_runs:
        run_end = start + len(txt)
        if run_end <= pos or start >= end_pos:
            continue
        overlap_start = max(start, pos) - start
        overlap_end = min(run_end, end_pos) - start
        span.append((elem, start, txt, overlap_start, overlap_end))

    if not span:
        raise ValueError("internal: span is empty")

    # ---- 3. build a single <w:del> with the original phrase ----
    del_elem = revision_element("del", revision_id, timestamp)
    rev_id = revision_id + 1

    # Capture the insertion anchor BEFORE mutating the tree: when old_text
    # consumes the entire first run, that run gets removed and its getparent()
    # becomes None (whole-paragraph replacements crashed here).
    first_elem = span[0][0]
    first_parent = first_elem.getparent()
    anchor_idx = list(first_parent).index(first_elem)
    consumed_runs = []

    for elem, start, txt, o_start, o_end in span:
        prefix = txt[:o_start]
        middle = txt[o_start:o_end]
        suffix = txt[o_end:]

        # text before the match stays as-is
        if prefix:
            parent = elem.getparent()
            idx = list(parent).index(elem)
            prefix_run = make_text_run(prefix, rpr)
            parent.insert(idx, prefix_run)
            if elem is first_elem:
                # del/ins must land after the prefix run
                anchor_idx += 1

        # the matched portion goes into <w:del>
        if middle:
            del_elem.append(make_text_run(middle, rpr, deleted=True))

        # text after the match
        if suffix:
            t_node = elem.xpath("./w:t", namespaces=NS)
            if t_node:
                t_node[0].text = suffix
                if suffix.startswith((" ", "\t", "\n")) or suffix.endswith(
                    (" ", "\t", "\n")
                ):
                    t_node[0].set(XML_SPACE, "preserve")
                else:
                    t_node[0].attrib.pop(XML_SPACE, None)
            # keep the run; if it is now empty it will be cleaned later
        else:
            # entire run was consumed — defer removal until del/ins inserted
            consumed_runs.append(elem)

    first_parent.insert(anchor_idx, del_elem)

    # ---- 4. build a single <w:ins> with the replacement ----
    ins_elem = revision_element("ins", rev_id, timestamp)
    rev_id += 1
    ins_elem.append(make_text_run(new_text, rpr))
    # insert <w:ins> right after <w:del>
    del_idx = list(first_parent).index(del_elem)
    first_parent.insert(del_idx + 1, ins_elem)

    # remove fully-consumed runs now that the anchor is in place
    for elem in consumed_runs:
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)

    # ---- 5. clean up empty runs ----
    # Only remove runs that became truly empty. Runs holding non-text content
    # (<w:tab> indentation, <w:br> line breaks, <w:drawing>/<w:object> etc.)
    # must be preserved even though they have no <w:t>/<w:delText>.
    keep = "w:t or w:delText or w:tab or w:br or w:cr or w:drawing or w:object or w:pict or w:fldChar or w:instrText or w:sym or w:noBreakHyphen"
    for r in paragraph.xpath(f".//w:r[not({keep})]", namespaces=NS):
        p = r.getparent()
        if p is not None:
            p.remove(r)

    return rev_id


def apply_text_operations(
    document_root,
    operations: list[dict],
    revision_id: int,
    timestamp: str,
) -> int:
    paragraphs = body_paragraphs(document_root)
    paragraph_map = {f"p{index:04d}": value for index, value in enumerate(paragraphs, 1)}
    grouped: dict[str, list[dict]] = {}
    for operation in operations:
        if operation.get("action") not in TEXT_ACTIONS:
            continue
        target = operation.get("target")
        if target not in paragraph_map:
            raise ValueError(f"unknown target paragraph: {target}")
        grouped.setdefault(target, []).append(operation)

    for target, text_ops in grouped.items():
        paragraph = paragraph_map[target]
        flags = paragraph_flags(paragraph)
        original_text = visible_text(paragraph)
        if flags["has_drawing"] or flags["has_field"]:
            raise ValueError(
                f"{target} contains a drawing or field; use a comment operation"
            )
        # 一个条款只产出一处修订（真机 ffe8b7fb）：单个 replace_text 保留短语级定位
        # （只标出改动的短语，最清晰）；同一段落有多个操作、或含整段 replace 时，
        # 先归并出最终段文，再以条款级"整段改前→整段改后"产出单处修订，避免修订项过多。
        single_replace_text = (
            len(text_ops) == 1 and text_ops[0].get("action") == "replace_text"
        )
        if single_replace_text:
            operation = text_ops[0]
            revision_id = apply_replace_text_direct(
                paragraph,
                operation["old_text"],
                operation["new_text"],
                revision_id,
                timestamp,
            )
        else:
            current = original_text
            for operation in text_ops:
                current = replacement_for(operation, current)
            if current != original_text:
                revision_id = rebuild_with_revisions(
                    paragraph,
                    original_text,
                    current,
                    revision_id,
                    timestamp,
                )
    return revision_id


def apply_operations(
    input_path: Path,
    operations_path: Path,
    redline_path: Path,
    state_path: Path,
    mode: str,
) -> None:
    if mode not in REDLINE_MODES:
        raise ValueError(f"unsupported redline mode: {mode}")
    redline_path = generated_path(redline_path, "redline")
    package = read_package(input_path)
    document_root = xml(package["word/document.xml"])
    settings_root = xml(package["word/settings.xml"])
    _, operations = load_operations(operations_path)
    # DOCX hard rule (D3-S2): no emoji in model-authored comment text (also
    # feeds the revision summary table). Contract text (old_text/new_text)
    # is left untouched.
    for op in operations:
        if op.get("comment"):
            op["comment"] = sanitize_text(op["comment"])

    with_revisions = mode in {"revisions_only", "both"}
    with_comments = mode in {"comments_only", "both"}
    if mode == "comments_only":
        accept_revisions(document_root)
        remove_track_revisions(settings_root)
        remove_comments_plumbing(package)
    elif with_revisions:
        ensure_track_revisions(settings_root)
    if mode == "revisions_only":
        remove_comments_from_root(document_root)
        remove_comments_plumbing(package)

    comments = comments_root(package) if with_comments else None
    comment_id = (
        next_numeric_id(comments, ".//w:comment/@w:id") if comments is not None else 0
    )
    revision_id = next_numeric_id(document_root, ".//w:ins/@w:id | .//w:del/@w:id")
    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    summaries: list[dict] = []

    paragraphs = body_paragraphs(document_root)
    paragraph_map = {f"p{index:04d}": value for index, value in enumerate(paragraphs, 1)}
    for op in operations:
        target = op.get("target")
        if target not in paragraph_map:
            raise ValueError(f"unknown target paragraph: {target}")

    if with_revisions:
        revision_id = apply_text_operations(
            document_root,
            operations,
            revision_id,
            timestamp,
        )

    for operation in operations:
        target = operation["target"]
        comment_text = operation_comment(operation)
        if with_comments:
            add_comment(
                paragraph_map[target],
                comments,
                comment_id,
                comment_text,
                timestamp,
            )
            comment_id += 1
        summaries.append(
            {
                "issue_id": operation["issue_id"],
                "target": target,
                "risk": risk_label(operation.get("risk", "")),
                "basis_tag": operation.get("basis_tag", "[要点]"),
                "comment": (
                    operation.get("risk_description")
                    or operation.get("comment")
                    or "请复核。"
                ),
            }
        )

    ensure_contract_page_format(document_root)
    prevent_signature_row_splits(document_root)
    ensure_black_heading_styles(package)
    package["word/settings.xml"] = serialize(settings_root)
    if with_comments:
        ensure_comments_plumbing(package, comments)
    else:
        remove_comments_plumbing(package)

    append_revision_summary(document_root, summaries, mode)
    package["word/document.xml"] = serialize(document_root)
    write_package(redline_path, package)
    write_json_output(
        state_path,
        initial_decision_state(input_path, redline_path, mode, operations),
        "review decision state",
    )
    print(f"created {redline_path}")
    print(f"created {state_path}")


def load_decisions(path: Path) -> tuple[dict, dict[str, dict]]:
    request = json.loads(path.read_text(encoding="utf-8"))
    decision_rows = request.get("risk_decisions", request.get("decisions", []))
    decisions: dict[str, dict] = {}
    for row in decision_rows:
        issue_id = str(row.get("issue_id", "")).strip()
        if not issue_id:
            raise ValueError("every risk decision requires issue_id")
        if issue_id in decisions:
            raise ValueError(f"duplicate risk decision: {issue_id}")
        decision = row.get("decision", "pending")
        if decision not in DECISION_VALUES:
            raise ValueError(f"{issue_id}: unsupported decision: {decision}")
        decisions[issue_id] = row
    return request, decisions


def effective_decision(
    operation: dict,
    decisions: dict[str, dict],
    accept_all_proposed: bool,
) -> dict:
    issue_id = operation["issue_id"]
    if issue_id in decisions:
        return decisions[issue_id]
    if accept_all_proposed and operation.get("action") in TEXT_ACTIONS:
        return {"issue_id": issue_id, "decision": "accept_proposed"}
    return {"issue_id": issue_id, "decision": "pending"}


def revise_operations(
    operations_path: Path,
    decisions_path: Path,
    output_path: Path,
) -> None:
    request, operations = load_operations(operations_path)
    _, decisions = load_decisions(decisions_path)
    revised = copy.deepcopy(request)
    revised_by_id = {op["issue_id"]: op for op in revised["operations"]}
    changed = []
    for issue_id, row in decisions.items():
        if row.get("decision") != "custom_text":
            continue
        if issue_id not in revised_by_id:
            raise ValueError(f"unknown issue_id in decisions: {issue_id}")
        operation = revised_by_id[issue_id]
        if operation.get("action") not in TEXT_ACTIONS:
            raise ValueError(
                f"{issue_id}: custom_text requires replace or replace_text operation"
            )
        custom_text = str(row.get("custom_text", "")).strip()
        if not custom_text:
            raise ValueError(f"{issue_id}: custom_text decision requires custom_text")
        operation["new_text"] = custom_text
        operation["suggested_wording"] = custom_text
        operation["revision_note"] = "用户自定义措辞，需重新生成 Redline 并确认。"
        changed.append(issue_id)
    if not changed:
        raise ValueError("no custom_text decisions found")
    revised["supersedes"] = operations_path.name
    revised["customized_issue_ids"] = changed
    write_json_output(output_path, revised, "revised operations")
    print(f"created {output_path}")


def finalize_clean(
    input_path: Path,
    operations_path: Path,
    decisions_path: Path,
    output_path: Path,
    state_path: Path,
) -> None:
    _, operations = load_operations(operations_path)
    decision_request, decisions = load_decisions(decisions_path)
    accept_all = bool(decision_request.get("accept_all_proposed"))
    effective_rows = []
    selected_operations = []
    unresolved = []
    accepted_risks = []

    for operation in operations:
        row = effective_decision(operation, decisions, accept_all)
        decision = row.get("decision", "pending")
        blocking = requires_confirmation(operation)
        if decision == "custom_text":
            raise ValueError(
                f"{operation['issue_id']}: custom_text requires revise-operations "
                "and a newly confirmed Redline before Clean"
            )
        if blocking and decision == "pending":
            unresolved.append(operation["issue_id"])
        if decision == "accept_proposed":
            if operation.get("action") not in TEXT_ACTIONS:
                if blocking:
                    unresolved.append(operation["issue_id"])
            else:
                selected_operations.append(operation)
        elif decision == "retain_original_accept_risk":
            note = str(row.get("note", "")).strip()
            if not note:
                raise ValueError(
                    f"{operation['issue_id']}: retained risk requires a note"
                )
            accepted_risks.append(
                {
                    "issue_id": operation["issue_id"],
                    "risk": operation.get("risk", "low"),
                    "note": note,
                }
            )
        effective_rows.append(
            {
                "issue_id": operation["issue_id"],
                "target": operation.get("target"),
                "risk": operation.get("risk", "low"),
                "action": operation.get("action"),
                "requires_confirmation": blocking,
                "decision": decision,
                "note": row.get("note"),
            }
        )

    unresolved = sorted(set(unresolved))
    if unresolved:
        raise ValueError(
            "Clean is blocked by unresolved issues: " + ", ".join(unresolved)
        )

    output_path = generated_path(output_path, "confirmed clean")
    package = read_package(input_path)
    document_root = xml(package["word/document.xml"])
    settings_root = xml(package["word/settings.xml"])
    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    revision_id = next_numeric_id(document_root, ".//w:ins/@w:id | .//w:del/@w:id")
    if selected_operations:
        apply_text_operations(
            document_root,
            selected_operations,
            revision_id,
            timestamp,
        )
    accept_revisions(document_root)
    remove_track_revisions(settings_root)
    ensure_contract_page_format(document_root)
    prevent_signature_row_splits(document_root)
    ensure_black_heading_styles(package)
    package["word/document.xml"] = serialize(document_root)
    package["word/settings.xml"] = serialize(settings_root)
    remove_comments_plumbing(package)
    write_package(output_path, package)

    final_state = {
        "schema_version": "1.0",
        "workflow_stage": "clean_ready",
        "workflow_history": [
            "reviewing",
            "markup_ready",
            "awaiting_risk_confirmation",
            "clean_ready",
        ],
        "source_file": input_path.name,
        "clean_file": output_path.name,
        "risk_decisions": effective_rows,
        "accepted_risk_records": accepted_risks,
        "pending_issue_ids": [],
        "clean_eligible": True,
    }
    write_json_output(state_path, final_state, "final review decision state")
    print(f"created {output_path}")
    print(f"created {state_path}")


def complete_state(input_path: Path, output_path: Path) -> None:
    state = json.loads(input_path.read_text(encoding="utf-8"))
    if state.get("workflow_stage") != "clean_ready":
        raise ValueError("only clean_ready state can transition to completed")
    if state.get("pending_issue_ids"):
        raise ValueError("cannot complete while pending issues remain")
    completed = copy.deepcopy(state)
    completed["workflow_stage"] = "completed"
    history = list(completed.get("workflow_history", []))
    if not history or history[-1] != "completed":
        history.append("completed")
    completed["workflow_history"] = history
    write_json_output(output_path, completed, "completed review state")
    print(f"created {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("input", type=Path)
    extract_parser.add_argument("--out", required=True, type=Path)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("input", type=Path)
    apply_parser.add_argument("operations", type=Path)
    apply_parser.add_argument("--redline", required=True, type=Path)
    apply_parser.add_argument("--state-out", required=True, type=Path)
    apply_parser.add_argument(
        "--redline-mode",
        choices=REDLINE_MODES,
        default="both",
    )

    revise_parser = subparsers.add_parser("revise-operations")
    revise_parser.add_argument("operations", type=Path)
    revise_parser.add_argument("decisions", type=Path)
    revise_parser.add_argument("--out", required=True, type=Path)

    clean_parser = subparsers.add_parser("finalize-clean")
    clean_parser.add_argument("input", type=Path)
    clean_parser.add_argument("operations", type=Path)
    clean_parser.add_argument("decisions", type=Path)
    clean_parser.add_argument("--out", required=True, type=Path)
    clean_parser.add_argument("--state-out", required=True, type=Path)

    complete_parser = subparsers.add_parser("complete-state")
    complete_parser.add_argument("input", type=Path)
    complete_parser.add_argument("--out", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "extract":
        extract_document(args.input, args.out)
    elif args.command == "apply":
        apply_operations(
            args.input,
            args.operations,
            args.redline,
            args.state_out,
            args.redline_mode,
        )
    elif args.command == "revise-operations":
        revise_operations(args.operations, args.decisions, args.out)
    elif args.command == "finalize-clean":
        finalize_clean(
            args.input,
            args.operations,
            args.decisions,
            args.out,
            args.state_out,
        )
    elif args.command == "complete-state":
        complete_state(args.input, args.out)


if __name__ == "__main__":
    main()
