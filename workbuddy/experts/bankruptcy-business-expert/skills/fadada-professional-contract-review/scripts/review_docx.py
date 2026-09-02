#!/usr/bin/env python3
"""Extract and apply review operations using native WordprocessingML revisions."""

from __future__ import annotations

# 同目录模块（emoji_text / skill_paths / ooxml_engine）在部分宿主环境下不会自动
# 进入 sys.path，显式注入脚本所在目录。
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

from ooxml_engine import *  # shared OOXML revision engine (SSOT: ../../../_shared/contract-review-core)

RISK_ZH = {"high": "高", "medium": "中", "low": "低", "高": "高", "中": "中", "低": "低"}
_EMPTY_TAG_RE = re.compile(r"^\s*[\[【]?(用规|要点|法规|惯例)[\]】]?\s*[:：]\s*/?\s*$")


def _risk_zh(value: str) -> str:
    return RISK_ZH.get(str(value).strip().lower(), str(value).strip())


def clean_comment(text: str) -> str:
    """批注气泡归一化：剥离无内容的依据标签行（如 [用规]：/），只保留真实触发的依据；保持按维度换行。"""
    lines = [ln for ln in str(text or "").split("\n") if not _EMPTY_TAG_RE.match(ln)]
    return "\n".join(lines).strip()


_FIELD_RE = re.compile(r"【([^】]+)】\s*([^【]*)")


def merge_field_comments(comments: list[str]) -> str:
    """按【标签】字段归并多条批注，同一标签只出现一次，内容去重后合并。

    同一段落有多个 replace/replace_text 操作时，过去用「；」裸拼接各自的完整模板批注，
    导致【修改依据】等标签整套重复出现（真机 R-06 缺陷）。此函数把所有批注拆成
    【标签】→内容，按首次出现顺序每个标签只保留一行，多条不同内容用「；」合并、相同内容去重。
    """
    order: list[str] = []
    contents: dict[str, list[str]] = {}
    leading: list[str] = []
    for raw in comments:
        text = (raw or "").strip()
        if not text:
            continue
        first = _FIELD_RE.search(text)
        if first and first.start() > 0:
            lead = text[: first.start()].strip(" ；;\n")
            if lead and lead not in leading:
                leading.append(lead)
        for match in _FIELD_RE.finditer(text):
            label = match.group(1).strip()
            content = match.group(2).strip().strip("；;").strip()
            if label not in contents:
                contents[label] = []
                order.append(label)
            if not content:
                continue
            existing = contents[label]
            # 近似重复（一条是另一条子串）只保留更完整的那条，避免冗余重复；
            # 内容确有差异才并列，用「；」连接。
            if any(content in item for item in existing):
                continue
            existing[:] = [item for item in existing if item not in content]
            existing.append(content)
    lines: list[str] = []
    if leading:
        lines.append("；".join(leading))
    for label in order:
        lines.append(f"【{label}】{'；'.join(contents[label])}")
    return "\n".join(lines)


def revision_summary_table(summaries: list[dict]):
    widths = [480, 1050, 4050, 1050, 2170]
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
        ("#", "条款", "修改原因", "风险等级", "依据来源"), widths
    ):
        header.append(table_cell(value, width, bold=True))
    for index, item in enumerate(summaries, start=1):
        row = etree.SubElement(table, W + "tr")
        row_pr = etree.SubElement(row, W + "trPr")
        etree.SubElement(row_pr, W + "cantSplit")
        values = (
            str(index),
            item["target"],
            item["comment"],
            item["risk"],
            item["basis_tag"],
        )
        for value, width in zip(values, widths):
            row.append(table_cell(value, width))
    return table


def append_revision_summary(root, summaries: list[dict]) -> None:
    body = root.find(".//" + W + "body")
    append_plain_paragraph(
        body,
        "修订说明汇总",
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
    for r in paragraph.xpath(".//w:r[not(w:t) and not(w:delText)]", namespaces=NS):
        p = r.getparent()
        if p is not None:
            p.remove(r)

    return rev_id


# Common wrong field/action names → correct ones. Callers (including LLM-driven
# agents) frequently invent aliases; failing with an explicit mapping saves a
# full regeneration round-trip.
FIELD_ALIASES = {
    "para_id": "target",
    "paragraph_id": "target",
    "paraId": "target",
    "id": "target",
    "op": "action",
    "operation": "action",
    "type": "action",
    "old": "old_text",
    "new": "new_text",
    "original_text": "old_text",
    "replacement": "new_text",
    "text": "new_text",
    "note": "comment",
    "annotation": "comment",
    "level": "risk",
    "risk_level": "risk",
}

# insert：在 target 段之后物理插入新条款（整段 w:ins），用于补缺失保护条款。
# 真机 a2c4fdd7：过去 insert 被降级为 comment、管线无插入能力，"补4条款"演变为28分钟重做。
VALID_ACTIONS = {"replace", "replace_text", "comment", "insert"}

ACTION_ALIASES = {
    "insert_after": "insert",
    "add_clause": "insert",
    "new_clause": "insert",
    "insert_paragraph": "insert",
    "add_comment": "comment",
    "annotate": "comment",
    "replace_paragraph": "replace",
    "replace_all": "replace",
    "modify": "replace_text",
    "edit": "replace_text",
}


def validate_operations_schema(operations: list[dict], paragraph_map: dict) -> None:
    """Pre-flight schema check with actionable field-name guidance.

    Runs before any mutation so that a malformed operations.json fails fast
    with the correct field names, instead of surfacing mid-apply as an opaque
    ``unknown target paragraph`` error.
    """
    errors: list[str] = []
    for index, op in enumerate(operations, 1):
        if not isinstance(op, dict):
            errors.append(f"operations[{index}] 不是对象")
            continue
        loc = f"operations[{index}]"

        # 1) wrong field names
        for wrong, right in FIELD_ALIASES.items():
            if wrong in op and right not in op:
                errors.append(f"{loc} 字段名 `{wrong}` 无效，应为 `{right}`")

        # 2) required: target
        if "target" not in op:
            errors.append(
                f"{loc} 缺少必填字段 `target`（extract 产出的段落 ID，形如 p0012）"
            )
        elif op["target"] not in paragraph_map:
            sample = ", ".join(list(paragraph_map)[:3])
            errors.append(
                f"{loc} target={op['target']!r} 不在本合同段落中；"
                f"须使用 extract 产出的段落 ID（如 {sample} …）"
            )

        # 3) required: action
        action = op.get("action")
        if action is None:
            errors.append(
                f"{loc} 缺少必填字段 `action`，取值须为 replace / replace_text / comment / insert"
            )
        elif action in ACTION_ALIASES:
            errors.append(
                f"{loc} action={action!r} 无效，应为 `{ACTION_ALIASES[action]}`"
            )
        elif action not in VALID_ACTIONS:
            errors.append(
                f"{loc} action={action!r} 无效，取值须为 replace / replace_text / comment / insert"
            )

        # 4) replace_text needs both texts
        if action == "replace_text":
            for field in ("old_text", "new_text"):
                if not op.get(field):
                    errors.append(f"{loc} action=replace_text 时必填 `{field}`")

        # 5) insert needs the full new-clause wording
        if action == "insert" and not str(op.get("new_text", "")).strip():
            errors.append(f"{loc} action=insert 时必填 `new_text`（新条款完整措辞）")

        # 6) old_text 必须真的能在目标段落里定位到
        #    过去这条在 apply 中途才抛（`old_text not found in paragraph`），
        #    此时部分操作已改了内存文档，且一次只报一条——N 处写错就要 N 次往返。
        paragraph = paragraph_map.get(op.get("target"))
        if action == "replace_text" and paragraph is not None and op.get("old_text"):
            actual = visible_text(paragraph)
            if op["old_text"] not in actual:
                preview = actual[:60] + ("…" if len(actual) > 60 else "")
                errors.append(
                    f"{loc} old_text 在 {op['target']} 中不存在；"
                    f"该段实际文本为「{preview}」——old_text 必须逐字取自 extract 产出的段落原文"
                )

        # 7) 含图形/域的段落不能做文本修订，只能改批注
        if paragraph is not None and action in {"replace", "replace_text"}:
            flags = paragraph_flags(paragraph)
            if flags["has_drawing"] or flags["has_field"]:
                errors.append(
                    f"{loc} {op.get('target')} 含图形或域，无法做文本修订；"
                    f"请把该项改为 action=comment 并在 comment 中给出完整建议措辞"
                )

    if errors:
        raise ValueError(
            "operations.json 字段校验失败，请修正后重跑 apply（未对文档做任何修改）：\n  - "
            + "\n  - ".join(errors)
            + "\n\n正确接口示例：\n"
            '  {"operations": [\n'
            '    {"target": "p0012", "action": "replace_text",\n'
            '     "old_text": "原文片段", "new_text": "修改后文本",\n'
            '     "risk": "high", "basis_tag": "[法规]", "comment": "【风险等级】高\\n..."},\n'
            '    {"target": "p0020", "action": "comment",\n'
            '     "risk": "low", "basis_tag": "[惯例]", "comment": "批注内容"}\n'
            "  ]}\n"
            "字段说明见 references/local-output-playbook.md §2.3。"
        )


def apply_operations(
    input_path: Path,
    operations_path: Path,
    redline_path: Path,
    clean_path: Path,
) -> None:
    redline_path = generated_path(redline_path, "redline")
    clean_path = generated_path(clean_path, "internal clean")
    package = read_package(input_path)
    document_root = xml(package["word/document.xml"])
    settings_root = xml(package["word/settings.xml"])
    ensure_track_revisions(settings_root)

    paragraphs = body_paragraphs(document_root)
    paragraph_map = {f"p{index:04d}": value for index, value in enumerate(paragraphs, 1)}
    request = json.loads(operations_path.read_text(encoding="utf-8"))
    operations = request.get("operations", [])
    if not operations:
        raise ValueError(
            "operations list is empty. "
            'operations.json 顶层须为 {"operations": [...]}，每项含 target/action 字段。'
        )
    validate_operations_schema(operations, paragraph_map)
    # DOCX hard rule (D3-S2): no emoji in model-authored comment text (also
    # feeds the revision summary table). Contract text (old_text/new_text)
    # is left untouched.
    for op in operations:
        if op.get("comment"):
            op["comment"] = sanitize_text(op["comment"])

    comments = comments_root(package)
    comment_id = next_numeric_id(comments, ".//w:comment/@w:id")
    revision_id = next_numeric_id(document_root, ".//w:ins/@w:id | .//w:del/@w:id")
    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    summaries: list[dict] = []

    # Group operations by target paragraph so that multiple changes to the
    # same clause produce a single coherent revision with one merged comment,
    # rather than one comment per word.
    grouped: dict[str, list[dict]] = {}
    for op in operations:
        target = op.get("target")
        if target not in paragraph_map:
            raise ValueError(f"unknown target paragraph: {target}")
        grouped.setdefault(target, []).append(op)

    for target, ops in grouped.items():
        paragraph = paragraph_map[target]
        flags = paragraph_flags(paragraph)
        original_text = visible_text(paragraph)

        text_ops = [o for o in ops if o.get("action") in {"replace", "replace_text"}]
        comment_ops = [o for o in ops if o.get("action") == "comment"]
        insert_ops = [o for o in ops if o.get("action") == "insert"]

        # Apply text changes.  When every text operation is a replace_text
        # (old_text → new_text is known), use direct phrase-level replacement
        # so each changed phrase appears as one contiguous <w:del>/<w:ins>
        # block rather than word-by-word fragments.
        if text_ops:
            if flags["has_drawing"] or flags["has_field"]:
                raise ValueError(
                    f"{target} contains a drawing or field; use a comment operation"
                )
            # 一个条款只产出一处修订（真机 ffe8b7fb）：单个 replace_text 保留短语级
            # 定位（只标改动短语，最清晰）；多操作或含整段 replace 时，先归并出最终
            # 段文再以条款级"整段改前→整段改后"产出单处修订，避免词级碎片、修订项过多。
            single_replace_text = (
                len(text_ops) == 1 and text_ops[0].get("action") == "replace_text"
            )
            if single_replace_text:
                op = text_ops[0]
                revision_id = apply_replace_text_direct(
                    paragraph,
                    op["old_text"],
                    op["new_text"],
                    revision_id,
                    timestamp,
                )
            else:
                current = original_text
                for op in text_ops:
                    current = replacement_for(op, current)
                if current != original_text:
                    revision_id = rebuild_with_revisions(
                        paragraph, original_text, current, revision_id, timestamp
                    )

            # Merge all text-op comments into a single paragraph-level comment
            risks = {o.get("risk", "medium") for o in text_ops}
            tags = {o.get("basis_tag", "[要点]") for o in text_ops}
            merged_comment = merge_field_comments([o.get("comment", "") for o in text_ops])
            highest = "high" if "high" in risks else ("medium" if "medium" in risks else "low")
            merged_basis = "、".join(sorted(tags))
            # 去英文风险/冗余前缀，只留正文模板（已含【风险等级】【修改依据】），并剥离空标签行
            full_comment = clean_comment(merged_comment) or f"【风险等级】{_risk_zh(highest)}"
            add_comment(paragraph, comments, comment_id, full_comment, timestamp)
            comment_id += 1
            summaries.append(
                {
                    "target": target,
                    "risk": _risk_zh(highest),
                    "basis_tag": merged_basis,
                    "comment": merged_comment,
                }
            )

        # insert 动作：在本段之后物理插入新条款段（整段 w:ins），批注锚到新条款段。
        # 同一 target 上的多个 insert 按列出顺序链式锚定，保持条款顺序。
        insert_anchor = paragraph
        for op in insert_ops:
            new_paragraph, revision_id = insert_paragraph_revision(
                insert_anchor,
                op["new_text"],
                revision_id,
                timestamp,
            )
            insert_anchor = new_paragraph
            risk = op.get("risk", "medium")
            basis_tag = op.get("basis_tag", "[要点]")
            comment_text = op.get("comment", "")
            full_comment = clean_comment(comment_text) or (
                f"【风险等级】{_risk_zh(risk)}\n【建议】新增本条款"
            )
            add_comment(new_paragraph, comments, comment_id, full_comment, timestamp)
            comment_id += 1
            summaries.append(
                {
                    "target": target,
                    "risk": _risk_zh(risk),
                    "basis_tag": basis_tag,
                    "comment": comment_text or "新增条款",
                }
            )

        # Comment-only operations each keep their own comment bubble
        for op in comment_ops:
            risk = op.get("risk", "low")
            basis_tag = op.get("basis_tag", "[要点]")
            comment_text = op.get("comment", "请复核。")
            full_comment = clean_comment(comment_text) or f"【风险等级】{_risk_zh(risk)} {comment_text}"
            add_comment(paragraph, comments, comment_id, full_comment, timestamp)
            comment_id += 1
            summaries.append(
                {
                    "target": target,
                    "risk": _risk_zh(risk),
                    "basis_tag": basis_tag,
                    "comment": comment_text,
                }
            )

    package["word/settings.xml"] = serialize(settings_root)
    ensure_comments_plumbing(package, comments)

    clean_package = dict(package)
    clean_root = copy.deepcopy(document_root)
    clean_settings = copy.deepcopy(settings_root)
    accept_revisions(clean_root)
    remove_track_revisions(clean_settings)
    clean_package["word/document.xml"] = serialize(clean_root)
    clean_package["word/settings.xml"] = serialize(clean_settings)
    remove_comments_plumbing(clean_package)
    write_package(clean_path, clean_package)

    append_revision_summary(document_root, summaries)
    package["word/document.xml"] = serialize(document_root)
    ensure_comments_plumbing(package, comments)
    write_package(redline_path, package)
    print(f"created {redline_path}")
    print(f"created {clean_path}")


def resolve_revisions(
    input_path: Path,
    output_path: Path,
    mode: str,
) -> None:
    output_path = generated_path(output_path, "resolved contract")
    package = read_package(input_path)
    root = xml(package["word/document.xml"])
    settings_root = xml(package["word/settings.xml"])
    if mode == "accept":
        accept_revisions(root)
    else:
        reject_revisions(root)
    remove_track_revisions(settings_root)
    package["word/document.xml"] = serialize(root)
    package["word/settings.xml"] = serialize(settings_root)
    remove_comments_plumbing(package)
    write_package(output_path, package)
    print(f"created {output_path}")


NOT_OOXML_HINT = (
    "该文件不是 OOXML (.docx) 包——常见于旧版 Word (.doc)、WPS (.wps)、"
    "被改名的文件，或已加密/损坏的文档。\n"
    "补救：用 Word/WPS 打开后另存为 .docx 重新提交；"
    "或在本机安装 LibreOffice，由 review_intake.py 自动转换。\n"
    "注意：不要把读到的合同正文重打成新文件来绕开本限制——"
    "审查对象必须是用户提供的原文件。"
)


class _Parser(argparse.ArgumentParser):
    """参数错误时连同示例一起打印。

    argparse 默认只在 --help 里显示 epilog，出错时仅给一行 invalid choice，
    真机诊断中调用方据此开始逐条试错。这里让错误信息自带正确用法。
    """

    def error(self, message: str):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"\n参数错误: {message}\n\n{self.epilog}\n")
        raise SystemExit(2)


def main() -> None:
    parser = _Parser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "子命令只有 extract | apply | resolve，示例：\n"
            "  python review_docx.py extract 合同.docx --out <tmp>/paras.json\n"
            "  python review_docx.py apply 合同.docx ops.json "
            "--redline <tmp>/rl.docx --clean <tmp>/cl.docx\n"
            "  python review_docx.py resolve 合同.docx --mode accept "
            "--out <tmp>/resolved.docx\n"
            "\n正常流程请走 review_intake.py / review_build.py 两个驱动脚本，"
            "不要逐条编排本脚本。"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("input", type=Path)
    extract_parser.add_argument("--out", required=True, type=Path)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("input", type=Path)
    apply_parser.add_argument("operations", type=Path)
    apply_parser.add_argument("--redline", required=True, type=Path)
    apply_parser.add_argument("--clean", required=True, type=Path)

    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.add_argument("input", type=Path)
    resolve_parser.add_argument("--mode", choices=("accept", "reject"), required=True)
    resolve_parser.add_argument("--out", required=True, type=Path)

    args = parser.parse_args()
    try:
        if args.command == "extract":
            extract_document(args.input, args.out)
        elif args.command == "apply":
            apply_operations(args.input, args.operations, args.redline, args.clean)
        else:
            resolve_revisions(args.input, args.out, args.mode)
    except ValueError as exc:
        # operations 预检/应用期的可修错误：直接给可读消息，不要抛 traceback——
        # 上游 review_build 只能从 traceback 末行取因，会丢掉逐条列表。
        raise SystemExit(f"[ERROR] {exc}")
    except zipfile.BadZipFile:
        raise SystemExit(f"[ERROR] 无法读取 {args.input}：{NOT_OOXML_HINT}")
    except KeyError as exc:
        # docx 包缺少 word/document.xml 等必需部件
        raise SystemExit(
            f"[ERROR] {args.input} 的 docx 包结构不完整（缺少 {exc}）：{NOT_OOXML_HINT}")


if __name__ == "__main__":
    main()
