#!/usr/bin/env python3
"""Validate review DOCX deliverables and their separation rules."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from lxml import etree

from producer_evidence import build_review_evidence, write_review_evidence


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
NS = {"w": W_NS, "cp": CP_NS, "dc": DC_NS}
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]", re.UNICODE)
DISCLAIMER_TEXT = "不构成正式法律意见"
BLACK_COLORS = {"000000", "1A1A1A", "AUTO"}
REDLINE_MODES = ("revisions_only", "comments_only", "both")
TEXT_ACTIONS = {"replace", "replace_text"}
REPORT_STYLE_SIZES = {
    "Normal": "24",
    "Title": "44",
    "Heading1": "36",
    "Heading2": "32",
    "Heading3": "28",
}
TABLE_FONT_SIZE = "21"


def read_docx(path: Path) -> tuple[set[str], object, object | None, object | None, str]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        root = etree.fromstring(archive.read("word/document.xml"))
        styles = (
            etree.fromstring(archive.read("word/styles.xml"))
            if "word/styles.xml" in names
            else None
        )
        core = (
            etree.fromstring(archive.read("docProps/core.xml"))
            if "docProps/core.xml" in names
            else None
        )
    text = "".join(root.xpath(".//w:t/text()", namespaces=NS))
    return names, root, styles, core, text


def read_comments_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        if "word/comments.xml" not in archive.namelist():
            return ""
        comments = etree.fromstring(archive.read("word/comments.xml"))
    return "\n".join(comments.xpath(".//w:t/text()", namespaces=NS))


def visible_text(paragraph) -> str:
    return "".join(
        paragraph.xpath(
            ".//w:t[not(ancestor::w:del)]/text()",
            namespaces=NS,
        )
    )


def paragraph_map(root) -> dict[str, str]:
    paragraphs = root.xpath(".//w:body//w:p", namespaces=NS)
    return {
        f"p{index:04d}": visible_text(paragraph)
        for index, paragraph in enumerate(paragraphs, start=1)
    }


def table_widths_of(root) -> list[int]:
    result = []
    for table in root.xpath(".//w:tbl", namespaces=NS):
        widths = [
            int(value)
            for value in table.xpath("./w:tblGrid/w:gridCol/@w:w", namespaces=NS)
        ]
        result.append(sum(widths) if widths else 0)
    return result


def common_checks(
    path: Path, errors: list[str], inherited_table_widths: set[int] | None = None
) -> tuple[set[str], object, object | None, object | None, str]:
    """inherited_table_widths: table widths present in the source contract.
    Oversized tables inherited from the original (or a converted working copy,
    e.g. PDF input) are layout we must preserve, not generated content — they
    downgrade to a warning instead of failing the gate."""
    try:
        names, root, styles, core, text = read_docx(path)
    except Exception as exc:
        errors.append(f"{path.name}: invalid DOCX package: {exc}")
        return set(), None, None, None, ""
    if EMOJI_RE.search(text):
        errors.append(f"{path.name}: contains emoji")
    page = root.find(".//w:sectPr/w:pgSz", namespaces=NS)
    if page is None:
        errors.append(f"{path.name}: missing page size")
    else:
        width = int(page.get(f"{{{W_NS}}}w", "0"))
        height = int(page.get(f"{{{W_NS}}}h", "0"))
        if not (11850 <= width <= 11950 and 16750 <= height <= 16900):
            errors.append(f"{path.name}: page is not A4")
    for index, total in enumerate(table_widths_of(root), start=1):
        if total > 9026:
            if inherited_table_widths and total in inherited_table_widths:
                print(
                    f"warning: {path.name}: table {index} exceeds content width "
                    "(inherited from source layout, preserved as-is)"
                )
            else:
                errors.append(f"{path.name}: table {index} exceeds content width")
    return names, root, styles, core, text


def read_language_mode(core) -> str | None:
    if core is None:
        return None
    subject = "".join(core.xpath(".//dc:subject/text()", namespaces=NS))
    match = re.search(r"language_mode=(en_zh|zh_en)", subject)
    return match.group(1) if match else None


def check_black_heading_styles(styles, label: str, errors: list[str]) -> None:
    if styles is None:
        errors.append(f"{label}: missing styles.xml")
        return
    for style_id in ("Title", "Heading1", "Heading2"):
        matches = styles.xpath(
            ".//w:style[@w:styleId=$style_id]",
            namespaces=NS,
            style_id=style_id,
        )
        if not matches:
            continue
        colors = matches[0].xpath("./w:rPr/w:color/@w:val", namespaces=NS)
        if not colors or colors[0].upper() not in BLACK_COLORS:
            errors.append(f"{label}: {style_id} is not explicitly black")


def check_report_profile(root, styles, errors: list[str]) -> None:
    """Enforce the executable word-report subset of Output Standard 1.1.0."""
    if root is None or styles is None:
        return
    title_paragraphs = root.xpath(
        ".//w:body/w:p[w:pPr/w:pStyle/@w:val='Title']", namespaces=NS
    )
    if not title_paragraphs:
        errors.append("report: document title does not use semantic Title style")
    normal = styles.xpath(
        ".//w:style[@w:type='paragraph' and @w:styleId='Normal']", namespaces=NS
    )
    if not normal:
        errors.append("report: missing Normal paragraph style")
    else:
        spacing = normal[0].xpath("./w:pPr/w:spacing", namespaces=NS)
        line = spacing[0].get(f"{{{W_NS}}}line", "") if spacing else ""
        rule = spacing[0].get(f"{{{W_NS}}}lineRule", "") if spacing else ""
        if line != "360" or rule != "auto":
            errors.append("report: Normal style is not 1.5 line spacing")
    for style_id, expected_size in REPORT_STYLE_SIZES.items():
        matches = styles.xpath(
            ".//w:style[@w:type='paragraph' and @w:styleId=$style_id]",
            namespaces=NS,
            style_id=style_id,
        )
        if not matches:
            errors.append(f"report: missing {style_id} paragraph style")
            continue
        sizes = matches[0].xpath("./w:rPr/w:sz/@w:val", namespaces=NS)
        if not sizes or sizes[0] != expected_size:
            errors.append(
                f"report: {style_id} must use {int(expected_size) / 2:g} pt"
            )
    section = root.find(".//w:sectPr", namespaces=NS)
    if section is not None:
        page = section.find("w:pgSz", namespaces=NS)
        margins = section.find("w:pgMar", namespaces=NS)
        if page is not None and margins is not None:
            safe_width = (
                int(page.get(f"{{{W_NS}}}w", "0"))
                - int(margins.get(f"{{{W_NS}}}left", "0"))
                - int(margins.get(f"{{{W_NS}}}right", "0"))
                - 113
            )
            for index, table in enumerate(root.xpath(".//w:tbl", namespaces=NS), 1):
                widths = [
                    int(value)
                    for value in table.xpath(
                        "./w:tblGrid/w:gridCol/@w:w", namespaces=NS
                    )
                ]
                if widths and sum(widths) > safe_width:
                    errors.append(
                        f"report: table {index} does not keep the 2mm width safety margin"
                    )
    for index, table in enumerate(root.xpath(".//w:tbl", namespaces=NS), 1):
        first_row = table.xpath("./w:tr[1]", namespaces=NS)
        if not first_row:
            continue
        widths = [
            int(value)
            for value in table.xpath(
                "./w:tblGrid/w:gridCol/@w:w", namespaces=NS
            )
        ]
        headers = [
            normalize("".join(cell.xpath(".//w:t/text()", namespaces=NS)))
            for cell in first_row[0].xpath("./w:tc", namespaces=NS)
        ]
        kinds = []
        for header in headers:
            compact_header = re.sub(r"[\s：:()\uff08\uff09【】\[\]]+", "", header).lower()
            if re.fullmatch(r"(?:序号|编号|no\.?|id)", compact_header, re.IGNORECASE):
                kinds.append("index")
            elif any(
                marker in compact_header
                for marker in ("等级", "标识", "重要性", "优先级", "状态", "是否", "结果")
            ):
                kinds.append("compact")
            else:
                kinds.append("narrative")
        total_width = sum(widths)
        if len(widths) == len(kinds) and "narrative" in kinds and total_width:
            for column, (kind, width) in enumerate(zip(kinds, widths), 1):
                limit = 0.09 if kind == "index" else 0.20
                if kind in {"index", "compact"} and width > round(total_width * limit) + 1:
                    errors.append(
                        f"report: table {index} compact column {column} exceeds {limit:.0%}"
                    )
        for cell in first_row[0].xpath("./w:tc", namespaces=NS):
            fills = cell.xpath("./w:tcPr/w:shd/@w:fill", namespaces=NS)
            if not fills or fills[0].upper() not in {"000000", "1A1A1A"}:
                errors.append(f"report: table {index} header is not black-filled")
                break
        for run in table.xpath(".//w:r", namespaces=NS):
            sizes = run.xpath("./w:rPr/w:sz/@w:val", namespaces=NS)
            if not sizes or sizes[0] != TABLE_FONT_SIZE:
                errors.append(
                    f"report: table {index} text must use {int(TABLE_FONT_SIZE) / 2:g} pt"
                )
                break


def check_signature_rows(root, label: str, errors: list[str]) -> None:
    signature_pattern = re.compile(
        r"\b(?:By|Signature|Signed by)\s*:|签署[：:]|签字[：:]|盖章[：:]",
        re.IGNORECASE,
    )
    for table_index, table in enumerate(
        root.xpath(".//w:tbl", namespaces=NS),
        start=1,
    ):
        table_text = "".join(table.xpath(".//w:t/text()", namespaces=NS))
        if not signature_pattern.search(table_text):
            continue
        for row_index, row in enumerate(
            table.xpath("./w:tr", namespaces=NS),
            start=1,
        ):
            if not row.xpath("./w:trPr/w:cantSplit", namespaces=NS):
                errors.append(
                    f"{label}: signature table {table_index} row {row_index} "
                    "may split across pages"
                )


def check_bilingual(
    root, core, text: str, expected_mode: str | None, errors: list[str]
) -> None:
    mode = expected_mode or read_language_mode(core)
    if mode not in {"en_zh", "zh_en"}:
        errors.append("bilingual: missing or invalid language_mode metadata")
        mode = "en_zh"
    embedded = read_language_mode(core)
    if expected_mode and embedded and expected_mode != embedded:
        errors.append(
            f"bilingual: expected {expected_mode}, document metadata says {embedded}"
        )
    if text.count("Language priority:") != 1:
        errors.append("bilingual: requires exactly one English priority field")
    if text.count("语言优先规则：") != 1:
        errors.append("bilingual: requires exactly one Chinese priority field")
    for paragraph in root.xpath(".//w:body/w:p", namespaces=NS):
        value = "".join(paragraph.xpath(".//w:t/text()", namespaces=NS)).strip()
        if value.startswith("Language priority:") and re.search(
            r"[\u4e00-\u9fff]", value
        ):
            errors.append("bilingual: English priority field contains Chinese text")
        if value.startswith("语言优先规则：") and re.search(r"[A-Za-z]{4,}", value):
            errors.append("bilingual: Chinese priority field contains English text")

    language_paragraphs: list[str] = []
    for paragraph in root.xpath(".//w:body/w:p", namespaces=NS):
        value = "".join(paragraph.xpath(".//w:t/text()", namespaces=NS)).strip()
        has_en = bool(re.search(r"[A-Za-z]{4,}", value))
        has_zh = bool(re.search(r"[\u4e00-\u9fff]{2,}", value))
        if has_en and not has_zh:
            language_paragraphs.append("en")
        elif has_zh and not has_en:
            language_paragraphs.append("zh")
    if language_paragraphs:
        expected_first = "en" if mode == "en_zh" else "zh"
        if language_paragraphs[0] != expected_first:
            errors.append(
                f"bilingual: first language is {language_paragraphs[0]}, "
                f"expected {expected_first}"
            )

    for index, table in enumerate(root.xpath(".//w:tbl", namespaces=NS), start=1):
        table_text = "".join(table.xpath(".//w:t/text()", namespaces=NS))
        if "By:" in table_text or "签署：" in table_text:
            for row_index, row in enumerate(
                table.xpath("./w:tr", namespaces=NS), start=1
            ):
                if not row.xpath("./w:trPr/w:cantSplit", namespaces=NS):
                    errors.append(
                        f"bilingual: signature table {index} row {row_index} "
                        "may split across pages"
                    )
    for run in root.xpath(".//w:body//w:r[w:t]", namespaces=NS):
        colors = run.xpath("./w:rPr/w:color/@w:val", namespaces=NS)
        if colors and colors[0].upper() not in BLACK_COLORS:
            value = "".join(run.xpath("./w:t/text()", namespaces=NS)).strip()
            errors.append(
                f"bilingual: contract text is not black: {value[:40]}"
            )
            break


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def check_operations_coverage(
    operations_path: Path,
    red_root,
    red_text: str,
    comments_text: str,
    redline_mode: str,
    errors: list[str],
) -> list[dict]:
    try:
        operations = json.loads(operations_path.read_text(encoding="utf-8"))[
            "operations"
        ]
    except Exception as exc:
        errors.append(f"operations: cannot load {operations_path.name}: {exc}")
        return []
    issue_ids = [str(op.get("issue_id", "")).strip() for op in operations]
    if any(not issue_id for issue_id in issue_ids):
        errors.append("operations: every item requires issue_id")
    if len(issue_ids) != len(set(issue_ids)):
        errors.append("operations: issue_id values must be unique")
    replace_ops = [
        op for op in operations if op.get("action") in TEXT_ACTIONS
    ]
    if redline_mode in {"revisions_only", "both"} and not replace_ops:
        errors.append(
            "operations: no replace operations — redline carries no clause-text edits"
        )
    normalized_red = normalize(red_text)
    for op in operations:
        issue_id = op.get("issue_id", "?")
        target = op.get("target", "?")
        risk = str(op.get("risk", "")).lower()
        action = op.get("action")
        if risk in {"high", "medium"} and action == "comment" and not op.get(
            "comment_only_reason"
        ):
            errors.append(
                f"operations: {target} ({risk}) is comment-only without "
                "comment_only_reason — recommendation not applied to clause text"
            )
        if action in TEXT_ACTIONS and redline_mode in {"revisions_only", "both"}:
            new_text = normalize(op.get("new_text", ""))
            if new_text and new_text not in normalized_red:
                errors.append(
                    f"operations: {target} new_text not found in redline body: "
                    f"{new_text[:60]}…"
                )
        if redline_mode in {"comments_only", "both"}:
            if issue_id not in comments_text:
                errors.append(f"redline comments: missing issue_id {issue_id}")
    if red_root is not None:
        del_count = len(red_root.xpath(".//w:del", namespaces=NS))
        ins_count = len(red_root.xpath(".//w:ins", namespaces=NS))
        if (
            redline_mode in {"revisions_only", "both"}
            and replace_ops
            and (del_count + ins_count) < len(replace_ops)
        ):
            errors.append(
                f"operations: {len(replace_ops)} replace ops but only "
                f"{ins_count} w:ins / {del_count} w:del in redline"
            )
    return operations


def check_comment_format(comments_text: str, errors: list[str]) -> None:
    required = (
        "风险编号：",
        "风险等级：",
        "风险说明：",
        "建议处理：",
        "建议英文措辞：",
        "依据：",
    )
    for label in required:
        if label not in comments_text:
            errors.append(f"redline comments: missing Chinese field {label}")
    if comments_text and not re.search(r"[\u4e00-\u9fff]{4,}", comments_text):
        errors.append("redline comments: missing Chinese risk explanation")


def check_decision_state(
    state_path: Path,
    operations: list[dict],
    clean_root,
    source_path: Path | None,
    errors: list[str],
) -> None:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"decision state: cannot load {state_path.name}: {exc}")
        return
    stage = state.get("workflow_stage")
    if stage not in {
        "reviewing",
        "markup_ready",
        "awaiting_risk_confirmation",
        "clean_ready",
        "completed",
    }:
        errors.append(f"decision state: invalid workflow_stage {stage}")
    rows = state.get("risk_decisions", [])
    decisions = {row.get("issue_id"): row for row in rows}
    operation_ids = {op.get("issue_id") for op in operations}
    if set(decisions) != operation_ids:
        errors.append("decision state: issue_ids do not match operations")
    expected_pending = {
        op["issue_id"]
        for op in operations
        if (
            str(op.get("risk", "")).lower() in {"high", "medium"}
            or op.get("action") in TEXT_ACTIONS
        )
        and decisions.get(op["issue_id"], {}).get("decision") == "pending"
    }
    actual_pending = set(state.get("pending_issue_ids", []))
    if expected_pending != actual_pending:
        errors.append("decision state: pending_issue_ids are inconsistent")

    if clean_root is None:
        if stage != "awaiting_risk_confirmation":
            errors.append("decision state: initial review must await risk confirmation")
        return
    if stage not in {"clean_ready", "completed"}:
        errors.append("decision state: Clean requires clean_ready or completed stage")
    if expected_pending:
        errors.append("decision state: Clean exists while blocking issues remain")
    for issue_id, row in decisions.items():
        decision = row.get("decision")
        if decision == "custom_text":
            errors.append(
                f"decision state: {issue_id} custom_text was not re-redlined"
            )
        if decision == "retain_original_accept_risk" and not str(
            row.get("note", "")
        ).strip():
            errors.append(
                f"decision state: {issue_id} retained risk has no record note"
            )

    if source_path is None:
        errors.append("decision state: --source is required to verify Clean text")
        return
    try:
        _, source_root, _, _, _ = read_docx(source_path)
    except Exception as exc:
        errors.append(f"decision state: cannot read source contract: {exc}")
        return
    expected = paragraph_map(source_root)
    for operation in operations:
        row = decisions.get(operation["issue_id"], {})
        if row.get("decision") != "accept_proposed":
            continue
        target = operation.get("target")
        if target not in expected:
            errors.append(f"decision state: unknown target {target}")
            continue
        if operation.get("action") == "replace":
            expected[target] = operation.get("new_text", "")
        elif operation.get("action") == "replace_text":
            old_text = operation.get("old_text", "")
            if old_text not in expected[target]:
                errors.append(
                    f"decision state: {operation['issue_id']} old_text missing in source"
                )
            else:
                expected[target] = expected[target].replace(
                    old_text,
                    operation.get("new_text", ""),
                    1,
                )
    actual = paragraph_map(clean_root)
    for target, expected_text in expected.items():
        if target in actual and normalize(actual[target]) != normalize(expected_text):
            errors.append(f"clean: text does not match final decisions at {target}")


# ---- 源合同交叉核验（#3/#4/#5）：报告 ↔ 源合同文本对照 ----

_SECTION_CITE_RE = re.compile(r"(?:Section|Sec\.?|§)\s*(\d+)(?:\.(\d+))?", re.IGNORECASE)
_SECTION_CITE_CN_RE = re.compile(r"第\s*(\d+)(?:\.(\d+))?\s*条")


def _source_section_numbers(source_text: str) -> set[str]:
    """源合同存在的章节号集合（基础号与 X.Y 子条款分别收集）。"""
    nums: set[str] = set()
    for rx in (_SECTION_CITE_RE, _SECTION_CITE_CN_RE):
        for m in rx.finditer(source_text):
            nums.add(m.group(1))
            if m.group(2):
                nums.add(f"{m.group(1)}.{m.group(2)}")
    # 源合同里常见「30. Governing Law」「19.1」等裸编号行
    for m in re.finditer(r"(?m)^\s*(\d+)(?:\.(\d+))?[\s\.、]", source_text):
        nums.add(m.group(1))
        if m.group(2):
            nums.add(f"{m.group(1)}.{m.group(2)}")
    return nums


def check_clause_citations(report_text: str, source_text: str, errors: list[str]) -> None:
    """#5 条款号引用核验：基础 Section 号在源中不存在→FAIL；子条款缺失→WARN。"""
    src = _source_section_numbers(source_text)
    if not src:
        return
    missing_base: set[str] = set()
    missing_sub: set[str] = set()
    for rx in (_SECTION_CITE_RE, _SECTION_CITE_CN_RE):
        for m in rx.finditer(report_text):
            base, sub = m.group(1), m.group(2)
            if base not in src:
                missing_base.add(m.group(0).strip())
            elif sub and f"{base}.{sub}" not in src:
                missing_sub.add(m.group(0).strip())
    if missing_base:
        errors.append(
            "report: cited clause number(s) not found in source contract — "
            + ", ".join(sorted(missing_base))
        )
    if missing_sub:
        print(
            "[警告] 报告引用的子条款在源合同中未精确匹配（基础条存在），请核对: "
            + ", ".join(sorted(missing_sub))
        )


# 主题 → (报告该主题关键词, 源合同该主题关键词)
_PROTECTION_TOPICS = {
    "数据保护": (("数据保护", "个人信息", "个人数据", "data protection", "personal data"),
               ("数据保护", "个人信息", "个人数据", "protection of personal data", "personal data", "data protection")),
    "反贿赂反腐": (("反贿赂", "反腐", "贿赂", "anti-corruption", "anti-bribery", "bribery"),
                ("反贿赂", "反腐", "贿赂", "anti-corruption", "anti-bribery", "bribery", "corruption")),
    "保密": (("保密义务缺失", "无保密", "缺少保密", "confidentiality", "缺保密"),
           ("保密", "confidential information", "confidentiality")),
    "不可抗力": (("不可抗力", "force majeure"), ("不可抗力", "force majeure")),
    "责任限制": (("责任上限", "责任限制", "limitation of liability", "liability cap"),
              ("责任", "liability", "limited to", "shall not exceed")),
    "知识产权": (("知识产权", "intellectual property"), ("知识产权", "intellectual property")),
    "争议解决": (("争议解决", "仲裁", "dispute resolution", "arbitration"),
              ("仲裁", "arbitration", "dispute", "jurisdiction", "courts")),
}


def _missing_section_text(report_text: str) -> str:
    """切出报告「缺失保护与系统性不一致」节文本（标题到下一个一级标题前）。"""
    start = report_text.find("缺失保护")
    if start < 0:
        return ""
    rest = report_text[start:]
    nxt = re.search(r"[一二三四五六七八九十]+、", rest[4:])
    return rest[: nxt.start() + 4] if nxt else rest


def check_false_missing(report_text: str, source_text: str) -> None:
    """#3 误判缺失：缺失保护节声称某主题缺失，但源合同含该主题→WARN。"""
    section = _missing_section_text(report_text)
    if not section:
        return
    src_low = source_text.lower()
    sec_low = section.lower()
    hits = []
    for topic, (report_kw, source_kw) in _PROTECTION_TOPICS.items():
        if any(k.lower() in sec_low for k in report_kw) and any(k.lower() in src_low for k in source_kw):
            hits.append(topic)
    if hits:
        print(
            "[警告] 「缺失保护」节声称下列主题缺失，但源合同疑似含对应条款，请核对是否误判: "
            + "、".join(hits)
        )


def check_absence_claims(report_text: str, source_text: str) -> None:
    """#4 绝对化缺失断言：报告称"无最低限额/无上限/无下限"等，而源含相反措辞→WARN。"""
    claim_re = re.compile(r"无(?:任何)?(?:最低限额|下限|上限|限额)|未(?:设|约定)(?:最低|上限|下限|限额)")
    if not claim_re.search(report_text):
        return
    src_low = source_text.lower()
    contradictions = [
        kw for kw in ("less than", "不低于", "最低", "at least", "minimum",
                      "shall not exceed", "不超过", "上限", "no more than")
        if kw.lower() in src_low
    ]
    if contradictions:
        print(
            "[警告] 报告含「无限额/无上限/无下限」类断言，而源合同存在相反措辞（"
            + "、".join(contradictions[:4])
            + "），请对照条款原文核对该事实认定。"
        )


def check_report_no_empty_section(report_root, errors: list[str]) -> None:
    """每个一级标题（章节）下必须有实质内容；标题后紧跟下一标题=空节（内容空缺）。
    '本节不适用…' / '无。' 算作内容（已交代），裸空才判 FAIL。"""
    HEADING = ("Heading 1", "Heading1")
    body = report_root.find(f"{{{W_NS}}}body")
    if body is None:
        return
    heads = []  # (index, title)
    children = list(body)
    for i, el in enumerate(children):
        if el.tag != f"{{{W_NS}}}p":
            continue
        sty = el.find(f"{{{W_NS}}}pPr/{{{W_NS}}}pStyle")
        if sty is not None and sty.get(f"{{{W_NS}}}val") in HEADING:
            title = "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()
            heads.append((i, title))
    empty = []
    for k, (idx, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(children)
        has_content = False
        for el in children[idx + 1:end]:
            if el.tag == f"{{{W_NS}}}tbl":
                has_content = True; break
            if el.tag == f"{{{W_NS}}}p":
                if "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip():
                    has_content = True; break
        if not has_content:
            empty.append(title or f"(第{k+1}节)")
    if empty:
        errors.append("report: 以下章节为空节（无实质内容，审查未完成）: " + "、".join(empty))


def check_no_dict_repr(text: str, label: str, errors: list[str]) -> None:
    """检测 Python 字典/列表被当字符串渲染进文档（如 {'zh': '…'} 残留）=排版错乱。"""
    if re.search(r"\{['\"](?:zh|en|item|status|issue|parameter)['\"]\s*:", text) or "': '" in text:
        errors.append(f"{label}: 文档残留 Python 字典/列表字面量（结构化字段未正确渲染）")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--redline", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--clean", type=Path)
    parser.add_argument("--bilingual", type=Path)
    parser.add_argument("--bilingual-mode", choices=("en_zh", "zh_en"))
    parser.add_argument(
        "--redline-mode",
        choices=REDLINE_MODES,
        default="both",
    )
    parser.add_argument("--decision-state", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument(
        "--operations",
        type=Path,
        help="operations.json used by apply; verifies that high/medium-risk "
        "recommendations landed as real clause-text edits",
    )
    parser.add_argument(
        "--result-json",
        type=Path,
        help="write machine-readable producer self-check evidence; this is not "
        "trusted platform validation",
    )
    args = parser.parse_args()
    errors: list[str] = []

    inherited_widths: set[int] = set()
    source_text = ""
    source_lines = ""
    if args.source:
        try:
            _, source_root, _, _, source_text = read_docx(args.source)
            inherited_widths = {w for w in table_widths_of(source_root) if w > 9026}
            # 段落保留换行（read_docx 的 source_text 无换行，无法按行抽取裸编号条款号）
            source_lines = "\n".join(
                "".join(p.xpath(".//w:t/text()", namespaces=NS))
                for p in source_root.xpath(".//w:body//w:p", namespaces=NS)
            )
        except Exception:
            pass

    red_names, red_root, red_styles, _, red_text = common_checks(
        args.redline, errors, inherited_widths
    )
    comments_text = read_comments_text(args.redline) if red_names else ""
    if red_root is not None:
        has_insertions = bool(red_root.xpath(".//w:ins", namespaces=NS))
        has_deletions = bool(red_root.xpath(".//w:del", namespaces=NS))
        has_comments = "word/comments.xml" in red_names
        if args.redline_mode in {"revisions_only", "both"}:
            if not has_insertions:
                errors.append("redline: missing w:ins")
            if not has_deletions:
                errors.append("redline: missing w:del")
            if "修订说明汇总" not in red_text:
                errors.append("redline: missing revision summary")
        else:
            if has_insertions or has_deletions:
                errors.append("redline: comments_only contains tracked revisions")
            if "风险批注汇总" not in red_text:
                errors.append("redline: missing risk-comment summary")
        if args.redline_mode in {"comments_only", "both"}:
            if not has_comments:
                errors.append("redline: missing comments.xml")
            else:
                check_comment_format(comments_text, errors)
        elif has_comments:
            errors.append("redline: revisions_only contains comments.xml")
        if not any(tag in red_text for tag in ("[用规]", "[要点]", "[法规]", "[惯例]")):
            errors.append("redline: missing basis label")
        if DISCLAIMER_TEXT in red_text:
            errors.append("redline: contains report disclaimer")
        check_black_heading_styles(red_styles, "redline", errors)
        check_signature_rows(red_root, "redline", errors)

    operations = []
    if args.operations:
        operations = check_operations_coverage(
            args.operations,
            red_root,
            red_text,
            comments_text,
            args.redline_mode,
            errors,
        )

    clean_names, clean_root, clean_styles, _, clean_text = (
        common_checks(args.clean, errors, inherited_widths)
        if args.clean
        else (set(), None, None, None, "")
    )
    if clean_root is not None:
        if clean_root.xpath(
            ".//w:ins | .//w:del | .//w:commentRangeStart | "
            ".//w:commentRangeEnd | .//w:commentReference",
            namespaces=NS,
        ):
            errors.append("clean: revisions or comment markers remain")
        if "word/comments.xml" in clean_names:
            errors.append("clean: comments.xml remains")
        if DISCLAIMER_TEXT in clean_text:
            errors.append("clean: contains report disclaimer")
        if "修订说明汇总" in clean_text or "风险批注汇总" in clean_text:
            errors.append("clean: review summary remains")
        check_black_heading_styles(clean_styles, "clean", errors)
        check_signature_rows(clean_root, "clean", errors)

    if args.decision_state:
        if not operations:
            errors.append("decision state: --operations is required")
        else:
            check_decision_state(
                args.decision_state,
                operations,
                clean_root,
                args.source,
                errors,
            )

    _, bilingual_root, bilingual_styles, bilingual_core, bilingual_text = (
        common_checks(args.bilingual, errors, inherited_widths)
        if args.bilingual
        else (set(), None, None, None, "")
    )
    if bilingual_root is not None:
        if DISCLAIMER_TEXT in bilingual_text:
            errors.append("bilingual: contains report disclaimer")
        if not re.search(r"[A-Za-z]{4,}", bilingual_text):
            errors.append("bilingual: missing English text")
        if not re.search(r"[\u4e00-\u9fff]{2,}", bilingual_text):
            errors.append("bilingual: missing Chinese text")
        check_bilingual(
            bilingual_root,
            bilingual_core,
            bilingual_text,
            args.bilingual_mode,
            errors,
        )
        check_black_heading_styles(bilingual_styles, "bilingual", errors)

    _, report_root, report_styles, _, report_text = common_checks(args.report, errors)
    if report_root is not None and DISCLAIMER_TEXT not in report_text[:500]:
        errors.append("report: disclaimer missing from opening text")
    if report_root is not None:
        check_black_heading_styles(report_styles, "report", errors)
        check_report_profile(report_root, report_styles, errors)
        # 原始 Markdown 记号泄漏（## 标题、**加粗**）= 渲染管线失守
        for token, label in (("**", "**bold**"), ("## ", "## heading"), ("```", "code fence")):
            if token in report_text:
                errors.append(
                    f"report: raw markdown markup leaked into document ({label})"
                )
        # 输出物 QC 网：空节 / 字典残留（排版错乱、内容空缺）
        check_report_no_empty_section(report_root, errors)
        check_no_dict_repr(report_text, "report", errors)
        # 源合同交叉核验（#3/#4/#5）——需 --source
        if source_text:
            check_clause_citations(report_text, source_lines or source_text, errors)
            check_false_missing(report_text, source_text)
            check_absence_claims(report_text, source_text)
        else:
            print("[提示] 未提供 --source，跳过源合同交叉核验（缺失保护/条款号/缺失断言）")

    artifacts = [(args.report, "review_report"), (args.redline, "redline")]
    if args.clean:
        artifacts.append((args.clean, "clean_contract"))
    if args.bilingual:
        artifacts.append((args.bilingual, "bilingual_contract"))
    evidence = build_review_evidence(
        producer_skill_id="english-contract-review",
        artifacts=artifacts,
        errors=errors,
    )
    if args.result_json:
        write_review_evidence(args.result_json, evidence)

    if errors:
        raise SystemExit("\n".join(errors))
    print("review output validation passed")


if __name__ == "__main__":
    main()
