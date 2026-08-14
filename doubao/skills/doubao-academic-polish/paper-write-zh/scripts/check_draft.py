#!/usr/bin/env python3
"""写作阶段门卫：校验中文论文正文的确定性形态风险。

搬运自旧 check_paper_draft.py，改为从 meta.json 读取 mode/discipline_branch/
citation_style，并新增字数区间硬门禁。本脚本不判断学术质量与论证对错，只做
可确定性判定的形态检查：字数、文内引用与参考文献匹配、标题层级、禁用标记、
AI 腔、学科结构弱校验、Final 模式残留。

失败打印可执行修复指令。exit code: 0 通过 / 1 阻断 / 2 环境或参数错误。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SHARED_SKILL_DIR = Path(__file__).resolve().parents[2] / "paper-shape"
if str(SHARED_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_SKILL_DIR))

from revision_guard import validate_revision


# 高 AI 味模板词，命中只告警不阻断（正文可能合理使用少量）。
TEMPLATE_TERMS = (
    "首先",
    "其次",
    "最后",
    "第一",
    "第二",
    "第三",
    "此外",
    "总之",
    "综上所述",
    "值得注意的是",
    "需要指出的是",
    "具有重要意义",
)

# AI 提示词与过程说明残留，命中即阻断：正文不该出现这些痕迹。
AI_RESIDUES = (
    "部分内容由豆包生成",
    "由豆包生成",
    "内容由 AI 生成",
    "内容由AI生成",
    "请用户",
    "用户应",
    "待用户替换",
    "提示词",
    "下面我将",
    "本段将",
)

# Final 模式禁止残留的占位与模拟数据标记。
FINAL_FORBIDDEN = (
    "待补",
    "待核验",
    "TBD",
    "TODO",
    "mock",
    "模拟数据",
    "replace before submission",
    "PLANNING DATA",
)

# 各学科分支的典型材料/论证标记，用于弱校验是否套错结构。
BRANCH_MARKERS = {
    "technical": ("方法", "实验", "数据集", "指标", "模型", "算法"),
    "medical": ("伦理", "知情同意", "注册", "样本", "统计", "P值", "置信区间"),
    "law": ("法条", "司法解释", "裁判", "判决", "规范", "制度", "案例"),
    "hss_empirical": ("变量", "数据", "问卷", "访谈", "案例", "假设", "样本"),
    "hss_humanities": ("中心论点", "概念", "理论视角", "史料", "文本", "材料", "分论点"),
    "review": ("检索", "主题", "争议", "研究不足", "未来方向", "综述"),
}

NUMERIC_CITATION_STYLES = {"gbt7714_numeric"}
AUTHOR_YEAR_CITATION_STYLES = {"author_year", "apa", "chicago"}
CIRCLED_NUMBERS = {
    character: str(index)
    for index, character in enumerate("①②③④⑤⑥⑦⑧⑨⑩", start=1)
}
SCOPE_DEFAULT_MIN_CHARS = {
    "paragraph": 100,
    "section": 300,
    "chapter": 800,
    "revise": 100,
    "check": 1,
}
FULL_PAPER_DEFAULT_MIN_CHARS = {
    "journal": 800,
    "degree": 3000,
    "course": 800,
    "conference": 800,
    "review": 800,
    "proposal": 800,
    "other": 800,
}


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def load_json_optional(path: str | None) -> dict[str, Any]:
    """读取可选 JSON；缺失或非法时返回空 dict，不阻断（字段有默认值）。"""
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


def norm(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip().lower()


def count_occurrences(text: str, needles: tuple[str, ...]) -> dict[str, int]:
    return {needle: text.count(needle) for needle in needles if text.count(needle)}


def split_references(text: str) -> tuple[str, str]:
    """按参考文献标题把正文与参考文献段分开，便于分别检查引用。"""
    title = r"(?:参考文献|References|Works Cited|Bibliography|注释|Notes)"
    matches = [
        match
        for match in (
            re.search(rf"(?im)^#{{1,3}}\s*{title}\s*$", text),
            re.search(rf"(?is)<h[1-6]\b[^>]*>\s*{title}\s*</h[1-6]>", text),
            re.search(rf"(?im)^\s*{title}\s*$", text),
        )
        if match is not None
    ]
    if not matches:
        return text, ""
    match = min(matches, key=lambda item: item.start())
    return text[: match.start()], text[match.start() :]


def normalize_citation_text(value: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffa-z0-9]+", "", value.casefold())


def plain_citation_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(
        r"</(?:p|div|li|h[1-6]|paragraph|note)>|<br\s*/?>",
        "\n",
        value,
        flags=re.I,
    )
    return re.sub(r"<[^>]+>", "", value)


def extract_reference_entries(
    references: str,
    citation_style: str = "",
) -> list[str]:
    entries: list[str] = []
    style = norm(citation_style)
    for line in plain_citation_text(references).splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or re.fullmatch(
                r"(?:参考文献|references|works cited|bibliography|注释|notes)",
                stripped,
                flags=re.I,
            )
            or re.fullmatch(r"\|?[\s:|-]+\|?", stripped)
        ):
            continue
        if style == "footnote":
            is_entry = bool(
                re.match(r"^(?:\[\^[^\]]+\]:|[①②③④⑤⑥⑦⑧⑨⑩])", stripped)
            )
        elif style in NUMERIC_CITATION_STYLES:
            is_entry = bool(re.match(r"^(?:\[\d+\]|\d+[.)、])", stripped))
        elif style == "mla":
            is_entry = True
        elif style in AUTHOR_YEAR_CITATION_STYLES:
            is_entry = bool(re.search(r"(?:19|20)\d{2}[a-z]?", stripped, flags=re.I))
        else:
            is_entry = bool(
                re.match(
                    r"^(?:\[\d+\]|\d+[.)、]|\[\^[^\]]+\]:|[①②③④⑤⑥⑦⑧⑨⑩])",
                    stripped,
                )
                or re.search(r"(?:19|20)\d{2}", stripped)
            )
        if is_entry:
            entries.append(stripped)
    return entries


def citation_key(entry: str) -> str:
    book_title = re.search(r"《([^》]{2,})》", entry)
    if book_title:
        return normalize_citation_text(book_title.group(1))
    numeric = re.sub(
        r"^(?:\[\d+\]|\d+[.)、]|\[\^[^\]]+\]:|[①②③④⑤⑥⑦⑧⑨⑩])\s*",
        "",
        entry,
    )
    parts = re.split(r"[.。]", numeric)
    for part in parts[1:]:
        candidate = normalize_citation_text(part)
        if len(candidate) >= 4 and not re.fullmatch(r"(?:19|20)\d{2}[a-z]?", candidate):
            return candidate
    return normalize_citation_text(numeric)[:24]


def bibliographic_identity(entry: str) -> tuple[str, str, str]:
    year_match = re.search(r"((?:19|20)\d{2}[a-z]?)", entry, flags=re.I)
    return (
        reference_author(entry),
        citation_key(entry),
        year_match.group(1).casefold() if year_match else "",
    )


def expand_numeric_citations(body: str) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    errors: list[str] = []
    for marker in re.findall(r"\[([0-9,，;；\s\-–—－]+)\]", body):
        for part in re.split(r"[,，;；]\s*", marker):
            value = part.strip()
            if not value:
                continue
            range_match = re.fullmatch(r"(\d+)\s*[-–—－]\s*(\d+)", value)
            if range_match:
                start, end = map(int, range_match.groups())
                if end < start or end - start > 1000:
                    errors.append(f"无法安全展开数字引用区间 [{value}]")
                    continue
                keys.update(str(number) for number in range(start, end + 1))
            elif value.isdigit():
                keys.add(str(int(value)))
            else:
                errors.append(f"无法解析数字引用 [{value}]")
    return keys, errors


def canonical_author(value: str) -> str:
    value = re.sub(r"\[[A-Z][A-Z0-9.-]{1,15}\]", "", value)
    value = re.sub(r"\bet\s+al\.?", "", value, flags=re.I)
    value = re.sub(r"等\s*$", "", value)
    value = re.sub(r"^(?:see|参见|例如|如)\s*", "", value, flags=re.I)
    value = re.split(r"\s*&\s*|、|；|;", value, maxsplit=1)[0]
    if "," in value:
        value = value.split(",", 1)[0]
    return normalize_citation_text(value)


def reference_author(entry: str) -> str:
    value = re.sub(
        r"^(?:\[\d+\]|\d+[.)、]|\[\^[^\]]+\]:|[①②③④⑤⑥⑦⑧⑨⑩])\s*",
        "",
        plain_citation_text(entry),
    )
    first_segment = re.split(r"[.。]", value, maxsplit=1)[0]
    return canonical_author(first_segment)


def extract_author_year_body_keys(body: str) -> set[str]:
    keys: set[str] = set()
    plain = plain_citation_text(body)
    for group_match in re.finditer(
        r"[\(（]([^()（）\n]*?(?:19|20)\d{2}[a-z]?[^()（）\n]*)[\)）]",
        plain,
        flags=re.I,
    ):
        for segment in re.split(r"\s*[;；]\s*", group_match.group(1)):
            year_match = re.search(r"((?:19|20)\d{2}[a-z]?)", segment, flags=re.I)
            if not year_match:
                continue
            author = canonical_author(segment[: year_match.start()].rstrip(" ,，"))
            if author:
                keys.add(f"{author}|{year_match.group(1).casefold()}")

    narrative_patterns = (
        r"\b([A-Z][A-Za-z'’-]+(?:\s+et\s+al\.?)?)\s*[\(（]((?:19|20)\d{2}[a-z]?)[\)）]",
        r"(?:^|[，。；：、\s])([\u4e00-\u9fff]{2,20}?)(?:等)?\s*[\(（]((?:19|20)\d{2}[a-z]?)[\)）]",
    )
    for pattern in narrative_patterns:
        for match in re.finditer(pattern, plain, flags=re.I | re.M):
            author = canonical_author(match.group(1))
            if author:
                keys.add(f"{author}|{match.group(2).casefold()}")
    return keys


def extract_author_year_reference_keys(entries: list[str]) -> set[str]:
    keys: set[str] = set()
    for entry in entries:
        year_match = re.search(r"((?:19|20)\d{2}[a-z]?)", entry, flags=re.I)
        author = reference_author(entry)
        if year_match and author:
            keys.add(f"{author}|{year_match.group(1).casefold()}")
    return keys


def extract_mla_body_keys(body: str) -> set[str]:
    keys: set[str] = set()
    for match in re.finditer(
        r"[\(（]\s*([A-Z][A-Za-z'’-]+|[\u4e00-\u9fff]{2,20})"
        r"(?:\s+\d+(?:[-–]\d+)?)?\s*[\)）]",
        plain_citation_text(body),
    ):
        author = canonical_author(match.group(1))
        if author:
            keys.add(author)
    return keys


def extract_footnote_keys(value: str, definitions: bool) -> set[str]:
    plain = plain_citation_text(value)
    if definitions:
        keys = set(
            re.findall(r"(?m)^\s*\[\^([A-Za-z0-9_-]+)\]:", plain)
        )
    else:
        keys = set(re.findall(r"\[\^([A-Za-z0-9_-]+)\]", plain))
    for character, number in CIRCLED_NUMBERS.items():
        if character in plain:
            keys.add(number)
    return keys


def reference_key_list(references: str, family: str) -> list[str]:
    entries = extract_reference_entries(references, family)
    if family in NUMERIC_CITATION_STYLES:
        return [
            str(int(match.group(1)))
            for entry in entries
            if (match := re.match(r"^\s*\[(\d+)\]", entry))
        ]
    if family in AUTHOR_YEAR_CITATION_STYLES:
        keys: list[str] = []
        for entry in entries:
            year_match = re.search(r"((?:19|20)\d{2}[a-z]?)", entry, flags=re.I)
            author = reference_author(entry)
            if year_match and author:
                keys.append(f"{author}|{year_match.group(1).casefold()}")
        return keys
    if family == "mla":
        return [
            author
            for entry in entries
            if (author := reference_author(entry))
        ]
    if family == "footnote":
        plain = plain_citation_text(references)
        keys = re.findall(r"(?m)^\s*\[\^([A-Za-z0-9_-]+)\]:", plain)
        for character, number in CIRCLED_NUMBERS.items():
            keys.extend([number] * plain.count(character))
        return keys
    return []


def citation_key_sets(text: str, citation_style: str) -> dict[str, Any]:
    body, references = split_references(text)
    style = norm(citation_style)
    entries = extract_reference_entries(references, style)
    errors: list[str] = []
    family = style

    if style in NUMERIC_CITATION_STYLES:
        body_keys, errors = expand_numeric_citations(body)
        reference_keys = {
            str(int(match.group(1)))
            for entry in entries
            if (match := re.match(r"^\s*\[(\d+)\]", entry))
        }
    elif style in AUTHOR_YEAR_CITATION_STYLES:
        body_keys = extract_author_year_body_keys(body)
        reference_keys = extract_author_year_reference_keys(entries)
    elif style == "mla":
        body_keys = extract_mla_body_keys(body)
        reference_keys = {
            author for entry in entries if (author := reference_author(entry))
        }
    elif style == "footnote":
        body_keys = extract_footnote_keys(body, definitions=False)
        reference_keys = extract_footnote_keys(references, definitions=True)
    elif style == "template":
        numeric_body, numeric_errors = expand_numeric_citations(body)
        numeric_refs = {
            str(int(match.group(1)))
            for entry in extract_reference_entries(references, "gbt7714_numeric")
            if (match := re.match(r"^\s*\[(\d+)\]", entry))
        }
        if numeric_body or numeric_refs:
            family = "gbt7714_numeric"
            body_keys, reference_keys, errors = numeric_body, numeric_refs, numeric_errors
        else:
            footnote_body = extract_footnote_keys(body, definitions=False)
            footnote_refs = extract_footnote_keys(references, definitions=True)
            if footnote_body or footnote_refs:
                family = "footnote"
                body_keys, reference_keys = footnote_body, footnote_refs
            else:
                family = "author_year"
                body_keys = extract_author_year_body_keys(body)
                reference_keys = extract_author_year_reference_keys(
                    extract_reference_entries(references, "author_year")
                )
                if not body_keys and not reference_keys:
                    errors.append("template 体例未匹配到可确定解析的数字、脚注或作者-年份键")
    else:
        body_keys = set()
        reference_keys = set()
        errors.append(f"不支持的 citation_style：{citation_style}")

    duplicate_reference_keys = sorted(
        key
        for key, count in Counter(reference_key_list(references, family)).items()
        if count > 1
    )
    if duplicate_reference_keys:
        errors.append(
            "文末参考文献或注释存在重复引用键："
            + ", ".join(duplicate_reference_keys[:8])
        )

    return {
        "family": family,
        "body_keys": body_keys,
        "reference_keys": reference_keys,
        "parse_errors": errors,
    }


def check_citation_binding(
    text: str,
    citation_style: str,
    failures: list[str],
) -> dict[str, Any]:
    binding = citation_key_sets(text, citation_style)
    body_keys = binding["body_keys"]
    reference_keys = binding["reference_keys"]
    failures.extend(binding["parse_errors"])
    if not body_keys:
        failures.append(f"正文未检测到符合 {citation_style} 的可解析引用键。")
    if not reference_keys:
        failures.append(f"文末未检测到符合 {citation_style} 的可解析参考条目键。")
    missing_references = sorted(body_keys - reference_keys)
    uncited_references = sorted(reference_keys - body_keys)
    if missing_references:
        failures.append(
            f"正文引用键 {missing_references} 在文末参考文献或注释中无对应条目。"
        )
    if uncited_references:
        failures.append(
            f"文末参考条目键 {uncited_references} 未在正文引用。"
        )
    return binding


def check_source_traceability(
    body: str,
    references: str,
    source_pool_text: str,
    failures: list[str],
    citation_style: str = "",
) -> None:
    if not source_pool_text.strip():
        failures.append("需要引用但 source_pool.md 缺失或为空。")
        return
    entries = extract_reference_entries(references, citation_style)
    if not entries:
        failures.append("需要引用但参考文献章节没有可解析条目。")
        return
    pool_lines = [line.strip() for line in source_pool_text.splitlines() if line.strip()]
    header_index = next(
        (
            index
            for index, line in enumerate(pool_lines)
            if line.startswith("|") and "核验状态" in line and "来源" in line
        ),
        -1,
    )
    verified_sources: list[str] = []
    if header_index >= 0:
        headers = [
            normalize_citation_text(cell)
            for cell in pool_lines[header_index].strip("|").split("|")
        ]
        status_index = headers.index(normalize_citation_text("核验状态"))
        source_index = headers.index(normalize_citation_text("来源"))
        for line in pool_lines[header_index + 1:]:
            if not line.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|?", line):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            status = (
                re.sub(r"\s+", "", cells[status_index]).casefold()
                if status_index < len(cells)
                else ""
            )
            if status in {"已核验", "核验通过", "verified", "confirmed"}:
                if source_index < len(cells):
                    verified_sources.append(cells[source_index])
    if header_index >= 0:
        verified_identities = {
            identity
            for source in verified_sources
            if all(identity := bibliographic_identity(source))
        }
        unmatched = [
            entry[:120]
            for entry in entries
            if bibliographic_identity(entry) not in verified_identities
        ]
    else:
        pool_norm = normalize_citation_text(source_pool_text)
        unmatched = [
            entry[:120]
            for entry in entries
            if citation_key(entry) not in pool_norm
        ]
    if unmatched:
        failures.append(
            "参考文献含未进入 source_pool.md 的条目："
            + " | ".join(unmatched[:5])
        )


def has_in_text_citation(body: str, citation_style: str) -> bool:
    """按冻结体例检测正文是否有可解析的引用键。"""
    return bool(citation_key_sets(body, citation_style)["body_keys"])


def has_markdown_table(text: str) -> bool:
    return bool(re.search(r"(?m)^\|.+\|\s*$", text) and re.search(r"(?m)^\|?\s*[-:]+", text))


def find_bad_figure_placeholders(text: str) -> list[str]:
    """图占位必须含"内容要求"，否则视为不合格占位。"""
    bad: list[str] = []
    for line in text.splitlines():
        if re.search(r"图\s*\d", line) and "待绘制" in line and "内容要求" not in line:
            bad.append(line.strip())
    return bad


def emoji_count(text: str) -> int:
    count = 0
    for ch in text:
        code = ord(ch)
        if (
            0x1F300 <= code <= 0x1FAFF
            or 0x2600 <= code <= 0x27BF
            or 0xFE00 <= code <= 0xFE0F
        ):
            count += 1
    return count


def markdown_italic_matches(text: str) -> list[str]:
    pattern = re.compile(r"(?<![\\\w])_([^_\n]{1,80})_(?!\w)")
    matches: list[str] = []
    for match in pattern.finditer(text):
        inner = match.group(1).strip()
        if inner and not inner.startswith(("{", "}")):
            matches.append(match.group(0))
    return matches


def count_chinese(text: str) -> int:
    """统计中文字符数，作为正文篇幅的主口径（不含标点、空白、Markdown符号）。"""
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def resolve_char_range(
    meta: dict[str, Any],
    min_chars: int | None,
    max_chars: int | None,
) -> tuple[int | None, int | None, str, list[str]]:
    """解析正文范围：命令行优先，其次 meta，最后按任务规模选择默认下限。

    默认不设置统一上限。期刊、学校、模板或用户给出的明确上限应通过命令行
    或 meta.max_chars 传入，避免把段落和学位论文压进同一个固定区间。
    """
    failures: list[str] = []
    source = "cli"

    def parse_optional(value: Any, field: str) -> int | None:
        if value in (None, ""):
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            failures.append(f"{field} 必须是非负整数，当前为 {value!r}")
            return None
        if parsed < 0:
            failures.append(f"{field} 必须是非负整数，当前为 {parsed}")
            return None
        return parsed

    cli_min = parse_optional(min_chars, "min_chars")
    cli_max = parse_optional(max_chars, "max_chars")
    meta_min = parse_optional(meta.get("min_chars"), "meta.min_chars")
    meta_max = parse_optional(meta.get("max_chars"), "meta.max_chars")
    task_scope = norm(meta.get("task_scope", "full_paper")) or "full_paper"
    paper_type = norm(meta.get("paper_type", "other")) or "other"
    default_min = (
        FULL_PAPER_DEFAULT_MIN_CHARS.get(paper_type, 800)
        if task_scope == "full_paper"
        else SCOPE_DEFAULT_MIN_CHARS.get(task_scope, 800)
    )
    effective_min = (
        max(meta_min, cli_min)
        if meta_min is not None and cli_min is not None
        else meta_min
        if meta_min is not None
        else cli_min
        if cli_min is not None
        else default_min
    )
    effective_max = (
        min(meta_max, cli_max)
        if meta_max is not None and cli_max is not None
        else meta_max
        if meta_max is not None
        else cli_max
    )
    if meta_min is not None or meta_max is not None:
        source = "meta+cli" if cli_min is not None or cli_max is not None else "meta"
    elif cli_min is not None or cli_max is not None:
        source = "cli"
    else:
        source = "task_scope/paper_type"
    if (
        effective_min is not None
        and effective_max is not None
        and effective_min > effective_max
    ):
        failures.append(
            f"正文范围无效：下限 {effective_min} 大于上限 {effective_max}"
        )
    return effective_min, effective_max, source, failures


def find_deep_headings(text: str) -> list[str]:
    """检出第四层及以上标题（#### 起），学术正文标题层级不应超过三层。"""
    deep: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#{4,}\s+", line.strip()):
            deep.append(line.strip())
    return deep


def check_section_dependencies(text: str, failures: list[str]) -> None:
    headings = [
        match.group(1).strip()
        for match in re.finditer(r"(?m)^#{1,3}\s+(.+?)\s*$", text)
    ]

    def first(patterns: tuple[str, ...]) -> int:
        return next(
            (
                index
                for index, heading in enumerate(headings)
                if any(re.search(pattern, heading, flags=re.I) for pattern in patterns)
            ),
            -1,
        )

    method = first((r"研究方法", r"研究设计", r"方法$"))
    analysis = first((r"结果", r"分析", r"发现", r"实证检验"))
    discussion = first((r"讨论",))
    conclusion = first((r"结论", r"结语"))
    if method != -1 and analysis != -1 and method > analysis:
        failures.append("章节依赖错误：研究方法/研究设计不得位于结果或分析之后。")
    if analysis != -1 and discussion != -1 and analysis > discussion:
        failures.append("章节依赖错误：结果或分析不得位于讨论之后。")
    if discussion != -1 and conclusion != -1 and discussion > conclusion:
        failures.append("章节依赖错误：讨论不得位于结论之后。")
    if conclusion != -1:
        preceding = [index for index in (method, analysis, discussion) if index != -1]
        if preceding and conclusion < max(preceding):
            failures.append("章节依赖错误：结论不得位于方法、结果、分析或讨论之前。")


def check_branch(text: str, branch: str, mode: str) -> tuple[list[str], list[str], dict[str, Any]]:
    """按学科分支做结构弱校验，返回 (阻断项, 告警项, 指标)。"""
    failures: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}
    markers = BRANCH_MARKERS.get(branch, ())
    metrics["branch_marker_hits"] = [marker for marker in markers if marker in text]

    if branch == "law":
        suspicious_cases = re.findall(r"（\d{4}）[^，。\n]{0,30}号", text)
        law_articles = re.findall(r"第\s*\d+\s*条", text)
        metrics["case_number_like"] = suspicious_cases[:10]
        metrics["law_article_like"] = law_articles[:10]
        if (suspicious_cases or law_articles) and not re.search(
            r"来源|出处|裁判文书|法宝|威科|用户提供|已核验", text
        ):
            failures.append("法学正文出现法条或案号形态，但未见来源/出处/已核验说明。")

    if branch == "medical":
        if "伦理" in text and re.search(r"批准号|审批号|注册号", text) and "待补" not in text and "用户提供" not in text:
            warnings.append("医学正文含伦理或注册编号类表述，请确认来自用户材料或真实来源。")
        if "P=0.000" in text:
            failures.append("医学统计写法不得使用 P=0.000，应改为 P<0.001。")

    if branch == "technical":
        if mode == "draft" and "PLANNING DATA" in text and re.search(
            r"实验结果表明|结果验证了|显著优于|充分证明|全面验证", text
        ):
            failures.append("Draft Mode 中 PLANNING DATA 附近不得写成真实实验结论。")

    if branch in {"hss_empirical", "hss_humanities", "review"} and not metrics["branch_marker_hits"]:
        warnings.append(f"{branch} 分支未命中典型材料/论证标记，请人工确认没有套成通用论文。")

    return failures, warnings, metrics


def validate(
    text: str,
    meta: dict[str, Any],
    min_chars: int | None,
    max_chars: int | None,
    source_pool_text: str = "",
    original_path: Path | None = None,
    revision_contract_path: Path | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    body, references = split_references(text)
    branch = norm(meta.get("discipline_branch", "technical")) or "technical"
    mode = norm(meta.get("mode", "draft")) or "draft"
    citation_style = norm(meta.get("citation_style", "gbt7714_numeric")) or "gbt7714_numeric"
    needs_citation = norm(meta.get("needs_citation", "yes")) == "yes"
    effective_min, effective_max, range_source, range_failures = resolve_char_range(
        meta,
        min_chars,
        max_chars,
    )
    failures.extend(range_failures)
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

    # 字数硬门禁（新增）：低于下限视为未完成，高于上限提示精简。
    char_count = count_chinese(text)
    if effective_min is not None and char_count < effective_min:
        failures.append(
            f"正文中文字数 {char_count}，低于下限 {effective_min}；"
            f"还需补 {effective_min - char_count} 字，"
            f"补充实质内容而非凑字"
        )
    if effective_max is not None and char_count > effective_max:
        failures.append(
            f"正文中文字数 {char_count}，超过上限 {effective_max}；"
            f"需删 {char_count - effective_max} 字，"
            f"优先删冗余举例与重复表述"
        )

    # 标题层级：不超过三层。
    deep_headings = find_deep_headings(text)
    if deep_headings:
        failures.append(f"正文含第四层及以上标题，应压到三层内：{deep_headings[:5]}")
    check_section_dependencies(text, failures)

    markdown_counts = {
        "double_star": text.count("**"),
        "double_underscore": text.count("__"),
        "single_underscore_italic": len(markdown_italic_matches(text)),
        "emoji": emoji_count(text),
        "html_sub": len(re.findall(r"</?sub>", text, flags=re.I)),
        "html_sup": len(re.findall(r"</?sup>", text, flags=re.I)),
    }
    if markdown_counts["double_star"]:
        failures.append("正文残留 Markdown 加粗标记 **，请删除。")
    if markdown_counts["double_underscore"]:
        failures.append("正文残留 Markdown 加粗标记 __，请删除。")
    if markdown_counts["single_underscore_italic"]:
        failures.append("正文残留 Markdown 斜体标记 _..._，请删除。")
    if markdown_counts["emoji"]:
        failures.append("正文残留 emoji，请删除。")
    if markdown_counts["html_sub"] or markdown_counts["html_sup"]:
        failures.append("正文残留 HTML 上下标标签，请改用正常字符或公式。")

    template_counts = count_occurrences(body, TEMPLATE_TERMS)
    if template_counts:
        warnings.append(f"正文命中高 AI 味模板词：{template_counts}")

    ai_residue_counts = count_occurrences(text, AI_RESIDUES)
    if ai_residue_counts:
        failures.append(f"正文残留 AI 提示词或过程说明：{ai_residue_counts}")

    # 引用与参考文献匹配（仅在需要引用时强制）。
    citation_binding: dict[str, Any] = {
        "family": citation_style,
        "body_keys": set(),
        "reference_keys": set(),
        "parse_errors": [],
    }
    if needs_citation:
        if references:
            citation_binding = check_citation_binding(
                text,
                citation_style,
                failures,
            )
            check_source_traceability(
                body,
                references,
                source_pool_text,
                failures,
                citation_style,
            )
        else:
            failures.append("需要引用的任务缺少参考文献章节。")

    if mode == "final":
        final_hits = count_occurrences(text, FINAL_FORBIDDEN)
        if final_hits:
            failures.append(f"Final 模式不得保留待补、待核验或模拟数据残留：{final_hits}")
    if mode == "draft" and "PLANNING DATA" in text and "replace before submission" not in text:
        failures.append("Draft 模式使用 PLANNING DATA 时必须写明 replace before submission。")

    bad_figures = find_bad_figure_placeholders(text)
    if bad_figures:
        failures.append(f"图占位缺少内容要求：{bad_figures[:5]}")

    numbered_tables = re.findall(r"表\s*\d+(?:[-－]\d+)?", text)
    if numbered_tables and not has_markdown_table(text):
        warnings.append("正文提到表编号，但未检测到 Markdown 表格；若表格在飞书生成，交付阶段读回确认。")

    branch_failures, branch_warnings, branch_metrics = check_branch(text, branch, mode)
    failures.extend(branch_failures)
    warnings.extend(branch_warnings)

    result = {
        "mode": mode,
        "discipline_branch": branch,
        "citation_style": citation_style,
        "char_count": char_count,
        "min_chars": effective_min,
        "max_chars": effective_max,
        "char_range_source": range_source,
        "has_references_section": bool(references),
        "has_in_text_citation": has_in_text_citation(body, citation_style),
        "citation_family": citation_binding["family"],
        "body_citation_keys": sorted(citation_binding["body_keys"]),
        "reference_keys": sorted(citation_binding["reference_keys"]),
        "deep_headings": deep_headings[:10],
        "markdown_counts": markdown_counts,
        "template_counts": template_counts,
        "ai_residue_counts": ai_residue_counts,
        "numbered_tables": numbered_tables[:20],
        "bad_figure_placeholders": bad_figures[:20],
        "branch_metrics": branch_metrics,
        "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
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
    parser.add_argument("--discipline-branch", default=None)
    parser.add_argument("--mode", default=None, choices=("draft", "final"))
    parser.add_argument("--citation-style", default=None)
    parser.add_argument(
        "--min-chars",
        type=int,
        default=None,
        help="正文中文字数下限；未传时按 meta.task_scope/paper_type 选择默认值",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="正文中文字数上限；未传时仅使用 meta.max_chars，不设统一上限",
    )
    parser.add_argument("--source-pool", default=None, help="prepare 阶段的 source_pool.md")
    parser.add_argument("--original", default=None, help="revise任务的原稿 original_draft.md")
    parser.add_argument("--revision-contract", default=None, help="revise任务的保真与授权变更合同")
    parser.add_argument("--write-report", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    text = Path(args.input).read_text(encoding="utf-8-sig")
    meta = load_json_optional(args.meta)
    source_pool_text = ""
    if args.source_pool and Path(args.source_pool).exists():
        source_pool_text = Path(args.source_pool).read_text(encoding="utf-8-sig")
    for field, value in (
        ("discipline_branch", args.discipline_branch),
        ("mode", args.mode),
        ("citation_style", args.citation_style),
    ):
        if not value:
            continue
        if args.meta and meta.get(field) != value:
            emit(
                {
                    "status": "error",
                    "stage": "write",
                    "reason": f"命令行{field}不能覆盖meta.json中已冻结的{field}",
                },
                2,
            )
        meta[field] = value

    payload = validate(
        text,
        meta,
        args.min_chars,
        args.max_chars,
        source_pool_text,
        original_path=Path(args.original) if args.original else None,
        revision_contract_path=Path(args.revision_contract) if args.revision_contract else None,
    )
    result = payload["result"]
    result["meta_sha256"] = (
        hashlib.sha256(
            Path(args.meta).read_text(encoding="utf-8-sig").encode("utf-8")
        ).hexdigest()
        if args.meta and Path(args.meta).exists()
        else ""
    )
    result["source_pool_sha256"] = (
        hashlib.sha256(source_pool_text.encode("utf-8")).hexdigest()
        if args.source_pool and Path(args.source_pool).exists()
        else ""
    )
    if args.write_report:
        report = Path(args.write_report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emit(payload, 0 if payload["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
