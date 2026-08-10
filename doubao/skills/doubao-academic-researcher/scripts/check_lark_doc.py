#!/usr/bin/env python3
"""Validate fetched Lark doc XML and optionally write doc_handoff.json.

This script is intentionally heuristic but deterministic. It checks the final
delivery layer after `lark-cli docs +fetch --doc-format xml` has been saved to a
local file.

Delivery form (ported baseline):
- 正文 uses author-year citations; numbered `[1]` citations are banned.
- 正文 must not carry source hyperlinks; links live only in the reference list.
- Each reference entry should end with a clickable source link.
- The core logic graph (核心逻辑/架构梳理图) replaces the old development timeline;
  no PNG fallback path.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PLACEHOLDER_PATTERNS = (
    "研究发展脉络图将在此处插入",
    "核心逻辑梳理图将在此处插入",
    "核心逻辑图将在此处插入",
    "文献主题覆盖矩阵将在此处插入",
    "文献多维地图将在此处插入",
    "将在此处插入",
    "TODO",
    "占位",
)

AUTHOR_YEAR_PATTERNS = (
    # 中文叙述式：张三（2021）/ 张三和李四（2021）/ 张三等（2021）
    re.compile(r"[\u4e00-\u9fff]{1,8}(?:[和与、][\u4e00-\u9fff]{1,8})?(?:等)?[（(]\d{4}[）)]"),
    # 英文叙述式：Smith（2020）/ Smith and Jones（2020）/ Smith & Jones（2020）/ Smith et al.（2020）
    re.compile(r"[A-Z][A-Za-z'’-]+(?:\s*(?:&|and)\s*[A-Z][A-Za-z'’-]+)?(?:\s+et al\.)?[（(]\d{4}[）)]"),
    # 括注式（中英通用）：（张三，2021）/（张三和李四，2021）/（Smith et al.，2020）
    re.compile(r"[（(][^（）()\n]{0,120}(?:等|et al\.|[\u4e00-\u9fff]|[A-Za-z])[^（）()\n]{0,20}[,，]\s*\d{4}[^（）()\n]{0,120}[）)]"),
)
# 负向校验：英文双作者错误使用中文“和”连接（如 “Smith 和 Jones（2020）”）。
# 英文姓氏之间应使用 and（叙述式）或 &（括注式），不得夹中文“和”。
# 用紧跟的年份约束把“引用”与普通英文术语并列（Python 和 Java）区分开，避免误伤。
EN_CONNECTOR_ERROR_RE = re.compile(
    r"[A-Z][A-Za-z'’\-]+\s*和\s*[A-Z][A-Za-z'’\-]+(?:\s+et al\.)?\s*[，,]?\s*[（(]?\s*\d{4}"
)
NUMBERED_CITATION_RE = re.compile(r"\[\d+(?:\s*[-,–]\s*\d+)?\]")
HREF_RE = re.compile(r"<a\b[^>]*\bhref=[\"']https?://", re.IGNORECASE)
REFERENCE_HEADING_RE = re.compile(r"(参考文献|References)", re.IGNORECASE)
MAX_CITATIONS_PER_CLUSTER = 4
REQUIRED_MAIN_SECTION_TITLES = (
    "核心结论",
    "研究范围与方法",
    "文献多维地图",
    "研究视角与本文结构",
    "核心逻辑图",
    "主题章节",
    "争议与开放问题",
    "可研究的方向",
    "局限性",
    "完整文献综述参考稿",
    "参考文献",
)
TOPIC_CONTAINER_TITLE = "主题章节"
MAIN_HEADING_RE = re.compile(
    r"(?m)^[ \t\u3000]*(?:#{1,6}[ \t\u3000]*)?([一二三四五六七八九十百]+)、[ \t\u3000]*(\S[^\r\n]*)"
)
# 分主题标题：括号中文序号（如 “（一）”“（二）”）。飞书 XML 经
# strip_tags 后通常只剩标题文本；本地 Markdown 回归样例会保留 ###。
TOPIC_HEADING_RE = re.compile(
    r"(?m)^[ \t\u3000]*(?:#{1,6}[ \t\u3000]*)?[（(]([一二三四五六七八九十百]+)[）)][ \t\u3000]*\S[^\r\n]*"
)
FIXED_SECTION_TITLES = REQUIRED_MAIN_SECTION_TITLES
FIXED_HEADING_RE = re.compile(
    r"(?m)^[ \t\u3000]*(?:#{1,6}[ \t\u3000]*)?(?:([一二三四五六七八九十百]+)、[ \t\u3000]*)?"
    + r"("
    + "|".join(re.escape(title) for title in FIXED_SECTION_TITLES)
    + r")[^\r\n]*"
)
# 本节文献索引与标题之间允许的最大间隔（字符）；超过说明索引没有紧接标题。
SECTION_LIT_MAX_GAP = 200


def norm_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def find_any(text: str, needles: tuple[str, ...]) -> int:
    positions = [text.find(needle) for needle in needles if text.find(needle) >= 0]
    return min(positions) if positions else -1


def whiteboard_blocks(text: str) -> list[re.Match[str]]:
    return list(re.finditer(r"<whiteboard\b[^>]*>.*?</whiteboard>", text, flags=re.IGNORECASE | re.DOTALL))


def blank_whiteboards(text: str) -> str:
    return re.sub(
        r"<whiteboard\b[^>]*>.*?</whiteboard>",
        lambda match: " " * (match.end() - match.start()),
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )


def status(value: bool) -> str:
    return "pass" if value else "fail"


def clean_heading(text: str) -> str:
    return re.sub(r"^[ \t\u3000]*(?:#{1,6}[ \t\u3000]*)?", "", text.strip())


def int_to_chinese(number: int) -> str:
    """Return Chinese section numerals for positive integers up to 99."""
    digits = "零一二三四五六七八九"
    if not 0 < number < 100:
        return str(number)
    if number < 10:
        return digits[number]
    tens, ones = divmod(number, 10)
    if number == 10:
        return "十"
    if tens == 1:
        return "十" + (digits[ones] if ones else "")
    return digits[tens] + "十" + (digits[ones] if ones else "")


def known_main_title(raw_title: str) -> str | None:
    """Map a heading title line to a required section title if it starts with one."""
    title = raw_title.strip()
    for required in REQUIRED_MAIN_SECTION_TITLES:
        if title == required or title.startswith(required):
            return required
    return None


def main_heading_entries(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for match in MAIN_HEADING_RE.finditer(text):
        raw_title = match.group(2).strip()
        entries.append(
            {
                "match": match,
                "number": match.group(1),
                "title": raw_title,
                "known_title": known_main_title(raw_title),
                "heading": clean_heading(match.group(0)),
            }
        )
    return entries


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "\n", text)


def split_reference_sections(xml_text: str, plain_text: str) -> tuple[str, str, str, str]:
    plain_match = REFERENCE_HEADING_RE.search(plain_text)
    xml_match = REFERENCE_HEADING_RE.search(xml_text)
    plain_index = plain_match.start() if plain_match else len(plain_text)
    xml_index = xml_match.start() if xml_match else len(xml_text)
    return (
        plain_text[:plain_index],
        plain_text[plain_index:],
        xml_text[:xml_index],
        xml_text[xml_index:],
    )


def citation_cluster_failures(text: str) -> list[str]:
    failures: list[str] = []
    for match in re.finditer(r"[（(]([^（）()\n]{0,300}\d{4}[^（）()\n]{0,300})[）)]", text):
        if not any(pattern.search(match.group(0)) for pattern in AUTHOR_YEAR_PATTERNS):
            continue
        years = re.findall(r"\b(?:19|20)\d{2}\b", match.group(1))
        if len(years) > MAX_CITATIONS_PER_CLUSTER:
            failures.append(
                f"citation cluster contains {len(years)} citations; max is {MAX_CITATIONS_PER_CLUSTER}"
            )
    return failures


def en_connector_error_failures(text: str) -> list[str]:
    """英文双作者不得用中文“和”连接（应为 and / &）。"""
    failures: list[str] = []
    for match in EN_CONNECTOR_ERROR_RE.finditer(text):
        snippet = match.group(0).strip()
        failures.append(
            f"英文双作者引用误用中文“和”：“{snippet}”；英文叙述式用 and、括注式用 &"
        )
    return failures


def section_lit_index_failures(body_plain: str) -> tuple[int, int, list[str]]:
    """检查每个主题章节标题下是否紧接 “本节文献 + 作者-年份” 索引。

    返回 (主题章节数, 合格章节数, 失败信息列表)。飞书 XML 经 strip_tags 后
    标题与其下的斜体索引会落在相邻文本；这里在标题后 SECTION_LIT_MAX_GAP
    字符窗口内查找 “本节文献” 字样，并要求同窗口出现作者-年份引用。
    """
    failures: list[str] = []
    all_numbered = list(TOPIC_HEADING_RE.finditer(body_plain))
    fixed_lines = {match.group(0).strip() for match in FIXED_HEADING_RE.finditer(body_plain)}
    headings = [match for match in all_numbered if match.group(0).strip() not in fixed_lines]
    main_heading_starts = [entry["match"].start() for entry in main_heading_entries(body_plain)]
    total = len(headings)
    passed = 0
    for idx, match in enumerate(headings):
        window_start = match.end()
        next_topic = headings[idx + 1].start() if idx + 1 < total else len(body_plain)
        next_main = next((pos for pos in main_heading_starts if pos > match.start()), len(body_plain))
        window_end = min(next_topic, next_main)
        window = body_plain[window_start : min(window_end, window_start + SECTION_LIT_MAX_GAP)]
        heading_label = clean_heading(match.group(0))[:20]
        if "本节文献" not in window:
            failures.append(f"主题章节 “{heading_label}” 标题下缺少“本节文献”索引")
            continue
        lit_scope = window[window.find("本节文献"):]
        if not any(pattern.search(lit_scope) for pattern in AUTHOR_YEAR_PATTERNS):
            failures.append(f"主题章节 “{heading_label}” 的本节文献索引缺少作者-年份格式")
            continue
        passed += 1
    return total, passed, failures


def fixed_section_lit_failures(body_plain: str) -> list[str]:
    """一级章节不得出现“本节文献”。"""
    failures: list[str] = []
    main_entries = main_heading_entries(body_plain)
    heading_starts = sorted(
        {entry["match"].start() for entry in main_entries}
        | {match.start() for match in TOPIC_HEADING_RE.finditer(body_plain)}
    )
    for entry in main_entries:
        match = entry["match"]
        title = entry["known_title"] or entry["title"]
        next_heading = next((pos for pos in heading_starts if pos > match.start()), len(body_plain))
        window = body_plain[match.end() : min(next_heading, match.end() + SECTION_LIT_MAX_GAP)]
        if "本节文献" in window:
            failures.append(f"一级章节 “{title}” 下不得出现“本节文献”；本节文献只属于分主题章节")
    return failures


def main_section_heading_failures(body_plain: str) -> tuple[bool, list[str]]:
    """一级章节按实际出现顺序自动校验一、二、三……编号。"""
    failures: list[str] = []
    entries = main_heading_entries(body_plain)
    found_titles: set[str] = set()
    topic_container_start: int | None = None
    last_required_index = -1
    for idx, entry in enumerate(entries, start=1):
        number = entry["number"]
        title = entry["known_title"]
        expected = int_to_chinese(idx)
        heading = entry["heading"]
        if number != expected:
            failures.append(f"一级章节第 {idx} 个应使用 “{expected}、”，当前为 “{heading}”")
        if not title:
            continue
        if title in found_titles:
            failures.append(f"一级章节 “{title}” 重复出现")
        found_titles.add(title)
        required_index = REQUIRED_MAIN_SECTION_TITLES.index(title)
        if required_index < last_required_index:
            failures.append("默认一级章节相对顺序被打乱；新增章节只能插入其间，不能调换默认章节顺序")
        last_required_index = max(last_required_index, required_index)
        if title == TOPIC_CONTAINER_TITLE:
            topic_container_start = entry["match"].start()

    for title in REQUIRED_MAIN_SECTION_TITLES:
        if title not in found_titles:
            failures.append(f"缺少一级章节 “{title}”")
    if entries and entries[0]["known_title"] != "核心结论":
        failures.append("文档第一个一级章节必须是 “一、核心结论”")
    if entries and entries[-1]["known_title"] != "参考文献":
        failures.append("文档最后一个一级章节必须是 “参考文献”")

    topic_matches = list(TOPIC_HEADING_RE.finditer(body_plain))
    if topic_container_start is not None and topic_matches:
        next_main_after_topic = next(
            (entry["match"].start() for entry in entries if entry["match"].start() > topic_container_start),
            len(body_plain),
        )
        for topic_match in topic_matches:
            if topic_match.start() < topic_container_start or topic_match.start() >= next_main_after_topic:
                failures.append("分主题章节必须放在 “主题章节” 一级章节内部")
                break
    return not failures, failures


def topic_heading_sequence_failures(body_plain: str) -> tuple[bool, list[str]]:
    """分主题按实际出现顺序自动校验（一）（二）（三）……编号。"""
    failures: list[str] = []
    topic_matches = list(TOPIC_HEADING_RE.finditer(body_plain))
    for idx, match in enumerate(topic_matches, start=1):
        expected = int_to_chinese(idx)
        actual = match.group(1)
        heading = clean_heading(match.group(0))
        if actual != expected:
            failures.append(f"分主题第 {idx} 个应使用 “（{expected}）”，当前为 “{heading}”")
    return not failures, failures


def logic_graph_block(blocks: list[re.Match[str]]) -> str:
    for block in blocks:
        block_text = block.group(0)
        lowered = block_text.lower()
        if "flowchart" in lowered or any(
            marker in block_text for marker in ("核心逻辑", "逻辑梳理", "核心架构", "logic_graph", "研究问题")
        ):
            return block_text
    return ""


def reference_entry_link_stats(reference_xml: str) -> tuple[int, int]:
    """Return (entry_count, linked_entry_count) from the reference XML.

    Entries are detected on block boundaries so href URLs survive tag
    stripping: each <p>/<li>/<tr> block that looks like a citation (contains a
    year) counts as one entry, and it is 'linked' if the block carries an
    <a href> or a raw http URL.
    """
    entries = 0
    linked = 0
    candidates = re.findall(r"<(?:p|li|tr)\b[^>]*>.*?</(?:p|li|tr)>", reference_xml, flags=re.IGNORECASE | re.DOTALL)
    if candidates:
        for block in candidates:
            plain = re.sub(r"<[^>]+>", " ", block)
            if not (re.search(r"\b(?:19|20)\d{2}\b", plain) and len(plain.strip()) > 12):
                continue
            entries += 1
            if HREF_RE.search(block) or re.search(r"https?://", block):
                linked += 1
        return entries, linked
    # Fallback: no block tags, split by lines on the plain text.
    plain_all = re.sub(r"<[^>]+>", " ", reference_xml)
    for line in plain_all.splitlines():
        line = line.strip()
        if not (re.search(r"\b(?:19|20)\d{2}\b", line) and len(line) > 12):
            continue
        entries += 1
        if re.search(r"https?://", line):
            linked += 1
    return entries, linked


def validate_doc(xml_text: str) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    plain_text = strip_tags(xml_text)
    body_plain, reference_plain, body_xml, reference_xml = split_reference_sections(xml_text, plain_text)
    anchor_text = blank_whiteboards(xml_text)
    blocks = whiteboard_blocks(xml_text)

    method_idx = find_any(anchor_text, ("研究范围与方法", "研究方法"))
    literature_map_idx = find_any(anchor_text, ("文献多维地图",))
    view_idx = find_any(anchor_text, ("研究视角与本文结构", "研究视角"))

    whiteboard_count = len(blocks)
    has_callout = "<callout" in xml_text.lower()
    has_placeholder = any(pattern in xml_text for pattern in PLACEHOLDER_PATTERNS)

    # Citation form: author-year required, numbered citations banned, no body links.
    has_numbered_refs = bool(NUMBERED_CITATION_RE.search(body_plain))
    has_author_year = any(pattern.search(body_plain) for pattern in AUTHOR_YEAR_PATTERNS)
    body_has_links = bool(HREF_RE.search(body_xml))
    references_have_links = bool(HREF_RE.search(reference_xml) or re.search(r"https?://", reference_plain))

    # Every reference entry should carry its own link.
    entries_count, entries_with_links = reference_entry_link_stats(reference_xml)
    all_entries_linked = bool(entries_count) and entries_with_links == entries_count

    # 每个主题章节标题下必须紧接 “本节文献 + 作者-年份” 索引。
    section_lit_total, section_lit_passed, section_lit_failures = section_lit_index_failures(body_plain)
    fixed_section_failures = fixed_section_lit_failures(body_plain)
    main_section_heading_ok, main_section_heading_failures_list = main_section_heading_failures(plain_text)
    topic_heading_sequence_ok, topic_heading_sequence_failures_list = topic_heading_sequence_failures(body_plain)
    section_lit_index_ok = section_lit_total > 0 and not section_lit_failures

    # Core logic graph replaces the old timeline.
    logic_block = logic_graph_block(blocks)
    logic_renderable = bool(logic_block) and (
        "flowchart" in logic_block.lower()
        or ("<svg" in logic_block.lower() and "viewbox=" in logic_block.lower())
    )
    logic_has_edge_label = bool(re.search(r"-->\|[^|]+?\|", logic_block))
    logic_has_lineage_edge = bool(
        re.search(r"\bN\d+(?:\s*(?:\[\[.*?\]\]|\[.*?\]|\(\(.*?\)\)|\(.*?\)|\{\{.*?\}\}))?\s*-->\|[^|]+?\|\s*N\d+\b", logic_block)
    )
    logic_has_evidence = bool(re.search(r"\[[A-Za-z]*\d+\]|\b[A-Z]{1,3}\d+\b", logic_block))

    # Literature map table (kept from baseline).
    literature_map_position_correct = False
    if literature_map_idx >= 0 and method_idx >= 0:
        if view_idx >= 0:
            literature_map_position_correct = method_idx < literature_map_idx < view_idx
        else:
            literature_map_position_correct = method_idx < literature_map_idx

    map_segment_end = view_idx if view_idx >= 0 else len(xml_text)
    map_segment = xml_text[literature_map_idx:map_segment_end] if literature_map_idx >= 0 else ""
    table_match = re.search(r"<table\b[^>]*>.*?</table>", map_segment, flags=re.IGNORECASE | re.DOTALL)
    table_plain = strip_tags(table_match.group(0)) if table_match else ""
    table_compact = re.sub(r"\s+", "", table_plain)
    support_count_cell_count = len(re.findall(r"\d+\s*篇(?:\s*[（(][^）)]*[）)])?", table_plain))
    has_table_tag = bool(table_match)
    has_topic_header = "主题" in table_compact
    has_support_count_header = "支持文献数" in table_compact
    has_representative_refs_header = "代表文献" in table_compact
    has_dispute_header = any(header in table_compact for header in ("争议/反对", "争议／反对"))
    has_gap_header = any(header in table_compact for header in ("研究空白/后续价值", "研究空白／后续价值"))
    has_support_count_cell = support_count_cell_count > 0
    has_reference_cell = bool(re.search(r"\[[A-Za-z]*\d+\]|\b[A-Z]{1,3}\d+\b", table_plain))
    has_literature_map_table = all(
        (
            has_table_tag,
            has_topic_header,
            has_support_count_header,
            has_representative_refs_header,
            has_dispute_header,
            has_gap_header,
            has_support_count_cell,
        )
    )

    if not logic_block:
        failures.append("missing core logic graph whiteboard (flowchart)")
    else:
        if not logic_renderable:
            failures.append("core logic graph exists but is not a renderable flowchart/SVG")
        if not logic_has_edge_label:
            failures.append("core logic graph must contain labeled edges like -->|关系|")
        if not logic_has_lineage_edge:
            failures.append("core logic graph must contain at least one node-to-node lineage edge like N1 -->|扩展| N2")
        if not logic_has_evidence:
            failures.append("core logic graph nodes must be traceable to evidence ids")
    if literature_map_idx < 0:
        failures.append("missing 文献多维地图 section")
    if not literature_map_position_correct:
        failures.append("文献多维地图 must be after 研究范围与方法 and before 研究视角与本文结构")
    if not has_table_tag:
        failures.append("文献多维地图 section must contain a <table>")
    if not has_topic_header:
        failures.append("文献多维地图 table must contain 主题 header")
    if not has_support_count_header:
        failures.append("文献多维地图 table must contain 支持文献数 header")
    if not has_representative_refs_header:
        failures.append("文献多维地图 table must contain 代表文献 header")
    if not has_dispute_header:
        failures.append("文献多维地图 table must contain 争议 / 反对 header")
    if not has_gap_header:
        failures.append("文献多维地图 table must contain 研究空白 / 后续价值 header")
    if not has_support_count_cell:
        failures.append("文献多维地图 table must contain support-count cells like 5 篇")
    if has_placeholder:
        failures.append("document still contains figure placeholder text")
    if has_callout:
        failures.append("document contains callout blocks")
    if has_numbered_refs:
        failures.append("document contains numbered citations like [1]; use author-year citations")
    if not has_author_year:
        failures.append("document does not contain author-year citations")
    if body_has_links:
        failures.append("document body contains hyperlinks; literature links must be confined to references")
    if not references_have_links:
        failures.append("references section must contain clickable source links")
    if entries_count and not all_entries_linked:
        failures.append(
            f"each reference entry must end with a clickable link; {entries_with_links}/{entries_count} linked"
        )
    if section_lit_total == 0:
        failures.append("未找到带括号编号的分主题章节（如 “（一）”“（二）”），无法校验本节文献索引")
    failures.extend(main_section_heading_failures_list)
    failures.extend(topic_heading_sequence_failures_list)
    failures.extend(fixed_section_failures)
    failures.extend(section_lit_failures)
    failures.extend(citation_cluster_failures(body_plain))
    en_connector_failures = en_connector_error_failures(body_plain)
    failures.extend(en_connector_failures)

    citation_format_pass = (
        not has_numbered_refs
        and has_author_year
        and not body_has_links
        and not citation_cluster_failures(body_plain)
        and not en_connector_failures
    )

    result = {
        "logic_graph_inserted": "yes" if logic_block else "no",
        "logic_graph_checked": status(
            bool(logic_block)
            and logic_renderable
            and logic_has_edge_label
            and logic_has_lineage_edge
            and logic_has_evidence
        ),
        "logic_graph_lineage_checked": status(logic_has_lineage_edge),
        "literature_map_table": "pass" if has_literature_map_table else "fail",
        "literature_map_position": "correct" if literature_map_position_correct else "wrong",
        "placeholder_removed": "yes" if not has_placeholder else "no",
        "fetched_back": "pass" if not failures else "fail",
        "rich_block_ban_checked": status(not has_callout),
        "citation_format_checked": status(citation_format_pass),
        "reference_links_checked": status(references_have_links and (not entries_count or all_entries_linked)),
        "main_section_heading_checked": status(main_section_heading_ok),
        "topic_heading_sequence_checked": status(topic_heading_sequence_ok),
        "section_lit_index_checked": status(section_lit_index_ok),
        "fixed_section_lit_checked": status(not fixed_section_failures),
        "section_lit_topic_count": section_lit_total,
        "section_lit_passed_count": section_lit_passed,
        "whiteboard_count": whiteboard_count,
        "reference_entry_count": entries_count,
        "reference_entries_linked": entries_with_links,
        "indexes": {
            "method": method_idx,
            "literature_map": literature_map_idx,
            "view": view_idx,
        },
    }
    return result, failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check fetched Lark doc XML for doubao-academic-researcher delivery")
    parser.add_argument("--xml", required=True, help="fetched Lark doc XML path")
    parser.add_argument("--doc-id", default="", help="Lark doc id")
    parser.add_argument("--doc-url", default="", help="Lark doc URL")
    parser.add_argument("--write-handoff", help="optional doc_handoff.json output path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    xml_path = Path(args.xml)
    xml_text = xml_path.read_text(encoding="utf-8-sig")
    result, failures = validate_doc(xml_text)
    payload: dict[str, Any] = {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "result": result,
    }
    if args.write_handoff:
        handoff = {
            "stage": "document-delivery",
            "doc_created": "yes",
            "doc_id": args.doc_id,
            "doc_url": args.doc_url,
            "ready_for_final": "yes" if not failures else "no",
            **{k: v for k, v in result.items() if k not in {"whiteboard_count", "indexes"}},
        }
        out = Path(args.write_handoff)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        payload["handoff"] = str(out)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not failures else 1)


if __name__ == "__main__":
    main()
