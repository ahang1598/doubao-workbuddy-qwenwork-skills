#!/usr/bin/env python3
"""写作阶段门卫（英文侧）：校验英文论文正文的确定性形态风险。

判定逻辑搬自旧 literature-verification/validate_run.py 的引用格式与章节顺序
检查，去掉 workflow 状态机依赖，改为读 meta.json + 直接扫正文。覆盖：
词数区间、章节顺序、引用体例（APA7/MLA9/Chicago18）标题与形态、
验真中间痕迹残留、默认体例禁 note 标记、正文禁列表。

不判断学术质量与论证对错。失败一次报全 + 可执行修复。
exit code: 0 通过 / 1 阻断 / 2 环境或参数错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SHARED_SKILL_DIR = Path(__file__).resolve().parents[2] / "paper-shape"
if str(SHARED_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_SKILL_DIR))

from revision_guard import validate_revision


# 验真中间字段，不得出现在正式论文正文/References 里。
VERIFICATION_ARTIFACTS = (
    "scout_handoff",
    "scout_verification_report",
    "verified_refs",
    "code_trace",
    "quality_basis",
    "authority_signal",
    "rejected_literature",
    "reverification",
)

PLACEHOLDER_PATTERNS = (
    (r"\bTODO\b", "TODO"),
    (r"\bTBD\b", "TBD"),
    (r"\bTK\b", "TK"),
    (r"\[\s*insert(?:[^\]]*)\]", "[insert]"),
    (r"\[\s*placeholder(?:[^\]]*)\]", "[placeholder]"),
    (r"\binsert here\b", "insert here"),
    (r"\byour text here\b", "your text here"),
)

YEAR_PATTERN = r"(?:(?:19|20)\d{2}[a-z]?|\bn\.?\s*d\.?)"
REFERENCE_HEADING_PATTERN = (
    r"(?im)^#{1,3}\s*(references|works cited|bibliography|reference list)\s*$"
)


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def norm(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip().lower()


def load_json_optional(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def normalize_bibliographic_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def normalize_doi(value: str) -> str:
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value.rstrip(".,;").casefold()


def normalize_year(value: str) -> str:
    normalized = re.sub(r"[\s.]+", "", value.casefold())
    return "nd" if normalized == "nd" else normalized


def text_sha256_optional(path: str | None) -> str:
    if not path:
        return ""
    candidate = Path(path)
    if not candidate.exists():
        return ""
    text = candidate.read_text(encoding="utf-8-sig")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_reference_entries(text: str, style: str) -> list[str]:
    match = re.search(REFERENCE_HEADING_PATTERN, text)
    if not match:
        return []
    entries: list[str] = []
    for line in text[match.end():].splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(stripped)
    return entries


def extract_author_year_citations(text: str, style: str) -> list[tuple[str, str, str]]:
    citations: list[tuple[str, str, str]] = []
    group_pattern = rf"[\(（]([^()（）]*?{YEAR_PATTERN}[^()（）]*)[\)）]"
    for group_match in re.finditer(group_pattern, text, flags=re.I):
        raw_group = group_match.group(1)
        for segment in re.split(r"\s*;\s*", raw_group):
            if style == "apa7":
                match = re.match(
                    rf"\s*([A-Z][A-Za-z'& .-]+?(?:\s*\[[A-Z][A-Z0-9.-]+\])?),\s*({YEAR_PATTERN})",
                    segment,
                    flags=re.I,
                )
            else:
                match = re.match(
                    rf"\s*([A-Z][A-Za-z'& .-]+?)\s+({YEAR_PATTERN})",
                    segment,
                    flags=re.I,
                )
            if match:
                citations.append((match.group(1).strip(), match.group(2), group_match.group(0)))

    narrative = re.compile(
        r"\b([A-Z][A-Za-z'&.-]+"
        r"(?:\s+(?:[A-Z][A-Za-z'&.-]+|and|for|of|the|on|in|to)){0,11})"
        rf"(?:\s*\[[A-Z][A-Z0-9.-]+\])?(?:\s+et al\.?)?\s*[\(（]({YEAR_PATTERN})[\)）]",
    )
    for match in narrative.finditer(text):
        item = (match.group(1).strip(), match.group(2), match.group(0))
        if item not in citations:
            citations.append(item)
    return citations


def extract_mla_citations(text: str) -> list[tuple[str, str]]:
    citations: list[tuple[str, str]] = []
    for match in re.finditer(r"[\(（]([^()（）]{1,180})[\)）]", text):
        inner = match.group(1).strip()
        quoted = bool(re.match(r"^[\"'“‘]", inner))
        quoted_source = re.match(r"^[\"'“‘]([^\"'”’]+)[\"'”’]", inner)
        if quoted_source:
            key = quoted_source.group(1)
        else:
            key = re.sub(r"^qtd\.\s+in\s+", "", inner, flags=re.I)
            key = re.sub(
                r"\s+(?:p{1,2}\.\s*)?\d+(?:\s*[-\u2012\u2013\u2014]\s*\d+)?\s*$",
                "",
                key,
                flags=re.I,
            )
        key = key.strip(" \t.,;:\"'“”‘’")
        if not key or re.fullmatch(YEAR_PATTERN, key, flags=re.I):
            continue
        has_locator = bool(re.search(r"\d+\s*$", inner))
        is_qtd = bool(re.match(r"^qtd\.\s+in\s+", inner, flags=re.I))
        if quoted or has_locator or is_qtd or re.fullmatch(r"[A-Z][A-Za-z'-]+", key):
            citations.append((key, match.group(0)))
            continue
        parts = key.split()
        connectors = {"and", "for", "of", "the", "on", "in", "to"}
        if len(parts) >= 2 and all(
            part.casefold() in connectors or part[:1].isupper()
            for part in parts
            if part
        ):
            citations.append((key, match.group(0)))
    return citations


def extract_institutional_aliases(text: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    full_name_pattern = (
        r"([A-Z][A-Za-z'&.-]+"
        r"(?:\s+(?:[A-Z][A-Za-z'&.-]+|and|for|of|the|on|in|to)){1,11})"
    )
    alias_pattern = r"([A-Z][A-Z0-9.-]{1,15})"
    patterns = (
        rf"\b{full_name_pattern}\s*\[\s*{alias_pattern}\s*\]\s*[\(（]{YEAR_PATTERN}[\)）]",
        rf"\b{full_name_pattern}\s*[\(（]\s*{alias_pattern}\s*,\s*{YEAR_PATTERN}\s*[\)）]",
        rf"[\(（]\s*{full_name_pattern}\s*\[\s*{alias_pattern}\s*\]\s*,\s*{YEAR_PATTERN}",
    )
    for pattern in patterns:
        for full_name, alias in re.findall(pattern, text):
            normalized_name = re.sub(
                r"^the\s+",
                "",
                normalize_bibliographic_text(full_name),
            )
            aliases[normalize_bibliographic_text(alias)] = normalized_name
    return aliases


def is_institutional_author(author: str) -> bool:
    words = set(normalize_bibliographic_text(author).split())
    markers = {
        "administration", "agency", "association", "bank", "center", "centers",
        "centre", "committee", "council", "department", "foundation", "fund",
        "government", "institute", "ministry", "nations", "office",
        "organization", "society", "university",
    }
    return bool(words & markers)


def author_family_name(author: str) -> str:
    normalized = normalize_bibliographic_text(author)
    if not normalized:
        return ""
    if "," in author:
        return normalize_bibliographic_text(author.split(",", 1)[0]).split()[-1]
    return normalized.split()[-1]


def author_matches_reference(expected_author: str, entry: str) -> bool:
    expected_norm = re.sub(
        r"^the\s+",
        "",
        normalize_bibliographic_text(expected_author),
    )
    if not expected_norm:
        return False
    raw_entry = re.sub(
        r"^(?:\[\d+\]|\d+[.)])\s*",
        "",
        entry.strip(),
    )
    entry_norm = normalize_bibliographic_text(raw_entry)
    entry_norm = re.sub(r"^the\s+", "", entry_norm)
    if is_institutional_author(expected_author):
        return bool(
            re.match(rf"^{re.escape(expected_norm)}(?:\b|[,.])", entry_norm)
        )
    family = author_family_name(expected_author)
    if not family:
        return False
    leading_author = normalize_bibliographic_text(
        raw_entry.split(",", 1)[0]
        if "," in raw_entry
        else raw_entry.split(" ", 1)[0]
    )
    return leading_author == family or leading_author.endswith(f" {family}")


def reference_year(entry: str) -> str:
    match = re.search(YEAR_PATTERN, entry, flags=re.I)
    return normalize_year(match.group(0)) if match else ""


def reference_title(entry: str) -> str:
    without_url = re.sub(r"https?://\S+", "", entry)
    year_match = re.search(YEAR_PATTERN, without_url, flags=re.I)
    if year_match:
        tail = without_url[year_match.end():].lstrip(" ).,")
        return normalize_bibliographic_text(re.split(r"\.\s+", tail, maxsplit=1)[0])
    parts = [part.strip() for part in re.split(r"\.\s+", without_url) if part.strip()]
    return normalize_bibliographic_text(parts[1]) if len(parts) > 1 else ""


def reference_matches_verified(entry: str, item: dict[str, Any]) -> bool:
    title_norm = normalize_bibliographic_text(str(item.get("title") or ""))
    author = str(item.get("first_author") or "").strip()
    expected_year = normalize_year(str(item.get("year") or "n.d."))
    expected_doi = normalize_doi(str(item.get("doi") or ""))

    if not title_norm or reference_title(entry) != title_norm:
        return False
    if not author_matches_reference(author, entry):
        return False
    actual_year = reference_year(entry)
    if not actual_year or actual_year[:4] != expected_year[:4]:
        return False
    if expected_doi:
        dois = {
            normalize_doi(value)
            for value in re.findall(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", entry, flags=re.I)
        }
        if expected_doi not in dois:
            return False
    return True


def citation_author_matches(citation_author: str, expected_author: str) -> bool:
    citation_norm = normalize_bibliographic_text(
        re.sub(r"\bet\s+al\.?", "", citation_author, flags=re.I)
    )
    citation_norm = re.sub(r"^the\s+", "", citation_norm)
    expected_norm = re.sub(
        r"^the\s+",
        "",
        normalize_bibliographic_text(expected_author),
    )
    if citation_norm == expected_norm:
        return True
    if is_institutional_author(expected_author):
        return False
    family = author_family_name(expected_author)
    first_cited_author = re.split(r"\s+(?:and|&)\s+|,", citation_norm, maxsplit=1)[0].strip()
    return bool(
        family
        and (
            first_cited_author == family
            or first_cited_author.split(" ", 1)[0] == family
        )
    )


def mla_key_matches_record(key: str, record: dict[str, Any]) -> bool:
    item = record["item"]
    key_norm = normalize_bibliographic_text(key)
    expected_author = str(item.get("first_author") or "")
    expected_author_norm = re.sub(
        r"^the\s+",
        "",
        normalize_bibliographic_text(expected_author),
    )
    title_norm = normalize_bibliographic_text(str(item.get("title") or ""))
    if key_norm == expected_author_norm:
        return True
    if not is_institutional_author(expected_author):
        family = author_family_name(expected_author)
        if key_norm.split(" ", 1)[0] == family:
            return True
    return len(key_norm) >= 4 and key_norm in title_norm


def check_reference_traceability(
    text: str,
    verified_refs: dict[str, Any],
    failures: list[str],
    style: str,
) -> None:
    core = verified_refs.get("core_literature") if isinstance(verified_refs, dict) else None
    if not isinstance(core, list) or not core:
        failures.append("需要引用但 verified_refs.json 缺少非空 core_literature。")
        return

    entries = extract_reference_entries(text, style)
    if not entries:
        failures.append("需要引用但未检测到可解析的 References 条目。")
        return

    records: list[dict[str, Any]] = []
    unmatched: list[str] = []
    for entry in entries:
        matches = [
            item for item in core
            if isinstance(item, dict) and reference_matches_verified(entry, item)
        ]
        if len(matches) != 1:
            unmatched.append(entry[:160])
            continue
        records.append(
            {
                "entry": entry,
                "item": matches[0],
                "citation_year": reference_year(entry),
            }
        )
    if unmatched:
        failures.append(
            "References 条目未唯一绑定 verified_refs 的作者、标题、年份及 DOI（存在时）："
            + " | ".join(unmatched[:5])
        )

    body = re.split(REFERENCE_HEADING_PATTERN, text)[0]
    institutional_aliases = extract_institutional_aliases(body)
    missing_in_bibliography: list[str] = []
    cited_record_ids: set[int] = set()
    if style in {"apa7", "chicago18_author_date"}:
        for author_value, year_value, raw in extract_author_year_citations(body, style):
            author = normalize_bibliographic_text(re.sub(r"\s*\[[^\]]+\]", "", author_value))
            author = institutional_aliases.get(author, author)
            author = re.sub(r"^the\s+", "", author)
            year = normalize_year(year_value)
            matches = [
                index for index, record in enumerate(records)
                if record["citation_year"] == year
                and citation_author_matches(author, str(record["item"].get("first_author") or ""))
            ]
            if len(matches) != 1:
                missing_in_bibliography.append(raw)
            else:
                cited_record_ids.add(matches[0])
    elif style == "mla9":
        for key, raw in extract_mla_citations(body):
            matches = [
                index for index, record in enumerate(records)
                if mla_key_matches_record(key, record)
            ]
            if len(matches) != 1:
                missing_in_bibliography.append(raw)
            else:
                cited_record_ids.add(matches[0])
    if missing_in_bibliography:
        failures.append(
            "正文引用在 References 中无唯一对应条目："
            + ", ".join(sorted(set(missing_in_bibliography))[:10])
        )
    uncited_entries = [
        record["entry"][:160]
        for index, record in enumerate(records)
        if index not in cited_record_ids
    ]
    if uncited_entries:
        failures.append(
            "References 含未被正文引用的条目："
            + " | ".join(uncited_entries[:5])
        )


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def strip_markdown_heading(line: str) -> str:
    return re.sub(r"^#+\s*", "", line.strip()).strip()


def normalize_heading(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = strip_markdown_heading(value)
    value = re.sub(r"^[IVXLC]+\.\s+", "", value, flags=re.I)
    value = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", value)
    value = re.sub(r"\s+", " ", value).strip().casefold()
    return value


def extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for match in re.finditer(r"<h[1-6][^>]*>(.*?)</h[1-6]>", text, flags=re.I | re.S):
        heading = normalize_heading(match.group(1))
        if heading:
            headings.append(heading)
    if headings:
        return headings
    for line in text.splitlines():
        if re.match(r"^\s{0,3}#{1,6}\s+", line):
            heading = normalize_heading(line)
            if heading:
                headings.append(heading)
    return headings


def first_heading_index(headings: list[str], patterns: list[str]) -> int:
    for index, heading in enumerate(headings):
        for pattern in patterns:
            if re.search(pattern, heading, flags=re.I):
                return index
    return -1


def check_section_order(text: str, failures: list[str]) -> None:
    """只检查跨体例都成立的依赖，不强制单一期刊章节模板。"""
    headings = extract_headings(text)
    if not headings:
        return
    method_idx = first_heading_index(headings, [r"\bmethodology\b", r"\bresearch design\b", r"\bmethods?\b"])
    analysis_idx = first_heading_index(headings, [r"\banalysis\b", r"\bresults?\b", r"\bfindings?\b"])
    discussion_idx = first_heading_index(headings, [r"\bdiscussion\b"])
    conclusion_idx = first_heading_index(headings, [r"\bconclusion\b"])
    references_idx = first_heading_index(headings, [r"\breferences\b", r"\bworks cited\b", r"\bbibliography\b", r"\bnotes\b"])

    if method_idx != -1 and analysis_idx != -1 and method_idx > analysis_idx:
        failures.append("section dependency invalid: Methodology/Research Design appears after Results/Analysis.")
    if analysis_idx != -1 and discussion_idx != -1 and analysis_idx > discussion_idx:
        failures.append("section dependency invalid: Results/Analysis appears after Discussion.")
    if discussion_idx != -1 and conclusion_idx != -1 and discussion_idx > conclusion_idx:
        failures.append("section dependency invalid: Discussion appears after Conclusion.")
    if references_idx != -1:
        last_body_idx = max(method_idx, analysis_idx, discussion_idx, conclusion_idx)
        if references_idx < last_body_idx:
            failures.append("section dependency invalid: References appears before the final body section.")


def check_verification_artifacts(text: str, failures: list[str]) -> None:
    lowered = text.lower()
    for term in VERIFICATION_ARTIFACTS:
        if term in lowered:
            failures.append(f"正文残留验真中间字段：{term}（正式论文不得出现验真留痕）")


def check_placeholders(text: str, failures: list[str]) -> None:
    found = [
        label for pattern, label in PLACEHOLDER_PATTERNS
        if re.search(pattern, text, flags=re.I)
    ]
    if found:
        failures.append(f"正文存在占位或未完成标记：{sorted(set(found))}")


def check_forbidden_notes(lines: list[str], failures: list[str], style: str) -> None:
    """默认 APA/MLA/Chicago 作者-年份不得用编号脚注或 Id./Ibid./supra note。"""
    for pattern, name in ((r"\bId\.", "Id."), (r"\b[Ii]bid\.", "Ibid."), (r"\bsupra note\b", "supra note")):
        for idx, line in enumerate(lines, start=1):
            if re.search(pattern, line):
                failures.append(f"line {idx} contains forbidden notes marker for {style}: {name}")
                break


def check_references_title(lines: list[str], style: str, failures: list[str]) -> None:
    """References 段标题与形态按体例校验。"""
    ref_idx = next((i for i, l in enumerate(lines) if strip_markdown_heading(l).lower() in
                    {"references", "works cited", "bibliography", "notes", "reference list"}), -1)
    if ref_idx == -1:
        return  # 无 References 段由 needs_citation 逻辑另管
    title = strip_markdown_heading(lines[ref_idx]).lower()
    if style == "apa7" and title not in {"references"}:
        failures.append("APA 7 参考文献段标题必须是 'References'。")
    if style == "mla9" and title not in {"works cited"}:
        failures.append("MLA 9 参考文献段标题必须是 'Works Cited'。")
    if style == "chicago18_author_date" and title not in {"references", "reference list"}:
        failures.append("Chicago 18 author-date 参考文献段标题应为 References 或 Reference List。")
    entries = [l for l in lines[ref_idx + 1:] if l]
    if style in {"apa7", "chicago18_author_date"} and entries:
        if any(re.match(r"^\d+\.\s+", e) for e in entries):
            failures.append(f"{style} 参考文献不得为编号 notes 列表。")


def check_no_lists(text: str, failures: list[str]) -> None:
    """英文论文正文不得用有序/无序列表（主 SKILL 规则），References 段除外。"""
    body = re.split(r"(?im)^#{1,3}\s*(references|works cited|bibliography|notes)\s*$", text)[0]
    bullet = len(re.findall(r"(?m)^\s{0,3}[-*+]\s+\S", body))
    ordered = len(re.findall(r"(?m)^\s{0,3}\d+\.\s+\S", body))
    if bullet + ordered >= 3:
        failures.append(
            f"正文疑似使用列表拼凑（无序 {bullet} 项、有序 {ordered} 项）；"
            f"英文论文正文应为连贯论述，类别/变量/步骤改用表格"
        )


def count_words(text: str) -> int:
    body = re.split(r"(?im)^#{1,3}\s*references\s*$", text)[0]
    return len(re.findall(r"[A-Za-z][A-Za-z'-]*", body))


def resolve_word_limits(
    meta: dict[str, Any],
    explicit_min: int | None,
    explicit_max: int | None,
) -> tuple[int, int]:
    scope = norm(meta.get("task_scope", "full_paper")) or "full_paper"
    paper_type = norm(meta.get("paper_type", "other")) or "other"
    defaults = {
        "abstract": (100, 1200),
        "section": (150, 15000),
        "revise": (100, 100000),
    }
    default_min, default_max = defaults.get(scope, (800, 30000))
    if scope == "full_paper" and paper_type == "thesis":
        default_min, default_max = 1500, 100000
    elif scope == "full_paper" and paper_type == "proposal":
        default_min, default_max = 500, 30000
    meta_min = meta.get("min_words")
    meta_max = meta.get("max_words")
    if meta_min not in (None, ""):
        contract_min = int(meta_min)
        minimum = (
            max(contract_min, explicit_min)
            if explicit_min is not None
            else contract_min
        )
    else:
        minimum = explicit_min if explicit_min is not None else default_min
    if meta_max not in (None, ""):
        contract_max = int(meta_max)
        maximum = (
            min(contract_max, explicit_max)
            if explicit_max is not None
            else contract_max
        )
    else:
        maximum = explicit_max if explicit_max is not None else default_max
    if minimum < 0 or maximum < 1 or minimum > maximum:
        raise ValueError(f"invalid word limits: min={minimum}, max={maximum}")
    return minimum, maximum


def has_in_text_citation(text: str, style: str) -> bool:
    if style in {"apa7", "chicago18_author_date"}:
        return bool(extract_author_year_citations(text, style))
    if style == "mla9":
        return bool(extract_mla_citations(text))
    return False


def validate(
    text: str,
    meta: dict[str, Any],
    min_words: int,
    max_words: int,
    verified_refs: dict[str, Any] | None = None,
    meta_sha256: str = "",
    verified_refs_sha256: str = "",
    original_path: Path | None = None,
    revision_contract_path: Path | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    style = norm(meta.get("citation_style", "apa7")) or "apa7"
    mode = norm(meta.get("mode", "draft")) or "draft"
    needs_citation = norm(meta.get("needs_citation", "yes")) == "yes"

    if not text.strip():
        emit(
            {
                "status": "fail",
                "stage": "write",
                "failures": ["正文为空；请把论文正文写入 paper_draft.md"],
                "fix": "在 .workflow/paper_draft.md 写入正文后重跑 make write。",
            },
            1,
        )

    lines = nonempty_lines(text)
    word_count = count_words(text)
    if word_count < min_words:
        failures.append(f"正文词数 {word_count}，低于下限 {min_words}；还需补约 {min_words - word_count} 词的实质内容")
    if word_count > max_words:
        failures.append(f"正文词数 {word_count}，超过上限 {max_words}；需删约 {word_count - max_words} 词")

    check_section_order(text, failures)
    check_verification_artifacts(text, failures)
    check_placeholders(text, failures)
    if mode == "final" and re.search(
        r"\b(?:simulated|constructed|hypothetical|placeholder)\s+data\b"
        r"|\bfor demonstration purposes only\b",
        text,
        flags=re.I,
    ):
        failures.append("Final模式不得保留模拟、构造、假设或占位数据。")
    check_forbidden_notes(lines, failures, style)
    check_no_lists(text, failures)
    revision_result: dict[str, Any] = {}
    if norm(meta.get("task_scope", "")) == "revise":
        if original_path is None or revision_contract_path is None:
            failures.append("实质性修订必须提供 original_draft.md 与 revision_contract.json。")
        else:
            revision_failures, revision_result = validate_revision(
                text,
                original_path,
                revision_contract_path,
            )
            failures.extend(revision_failures)

    if needs_citation:
        has_ref_section = any(strip_markdown_heading(l).lower() in
                              {"references", "works cited", "bibliography", "notes", "reference list"} for l in lines)
        has_in_text = has_in_text_citation(text, style)
        if not has_ref_section:
            failures.append("需要引用但正文缺少 References 段。")
        if not has_in_text:
            failures.append(f"未检测到符合 {style} 的文内引用。")
        check_references_title(lines, style, failures)
        check_reference_traceability(text, verified_refs or {}, failures, style)

    result = {
        "mode": mode,
        "citation_style": style,
        "word_count": word_count,
        "min_words": min_words,
        "max_words": max_words,
        "headings": extract_headings(text)[:20],
        "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "meta_sha256": meta_sha256,
        "verified_refs_sha256": verified_refs_sha256,
    }
    result.update(revision_result)
    payload = {
        "status": "pass" if not failures else "fail",
        "stage": "write",
        "failures": failures,
        "warnings": warnings,
        "result": result,
    }
    if failures:
        payload["fix"] = "按 failures 修正 .workflow/paper_draft.md，再重跑 make write。"
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="正文 Markdown 文件")
    parser.add_argument("--meta", default=None, help="meta.json 路径")
    parser.add_argument("--citation-style", default=None, choices=("apa7", "mla9", "chicago18_author_date"))
    parser.add_argument("--min-words", type=int, default=None, help="用户明确要求的正文英文词数下限")
    parser.add_argument("--max-words", type=int, default=None, help="用户明确要求的正文英文词数上限")
    parser.add_argument("--verified-refs", default=None, help="prepare 阶段产出的 verified_refs.json")
    parser.add_argument("--original", default=None, help="revise任务的原稿 original_draft.md")
    parser.add_argument("--revision-contract", default=None, help="revise任务的保真与授权变更合同")
    parser.add_argument("--write-report", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    text = Path(args.input).read_text(encoding="utf-8-sig")
    meta = load_json_optional(args.meta)
    verified_refs = load_json_optional(args.verified_refs)
    if args.citation_style:
        if args.meta and meta.get("citation_style") != args.citation_style:
            emit(
                {
                    "status": "error",
                    "stage": "write",
                    "reason": "--citation-style不能覆盖meta.json中已冻结的citation_style",
                },
                2,
            )
        meta["citation_style"] = args.citation_style

    try:
        min_words, max_words = resolve_word_limits(meta, args.min_words, args.max_words)
    except ValueError as exc:
        emit({"status": "error", "stage": "write", "reason": str(exc)}, 2)
    payload = validate(
        text,
        meta,
        min_words,
        max_words,
        verified_refs,
        meta_sha256=text_sha256_optional(args.meta),
        verified_refs_sha256=text_sha256_optional(args.verified_refs),
        original_path=Path(args.original) if args.original else None,
        revision_contract_path=Path(args.revision_contract) if args.revision_contract else None,
    )
    if args.write_report:
        report = Path(args.write_report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emit(payload, 0 if payload["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
