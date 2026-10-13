from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class Paragraph:
    paragraph_id: str
    text: str
    source: str
    location_hint: str


def resolve_annotation_paragraph_id(
    paragraph_id: str | None,
    original_excerpt: str,
    clause_position: str,
    paragraph_id_map: dict[str, Paragraph],
    additional_clues: list[str] | None = None,
) -> str | None:
    if paragraph_id and paragraph_id in paragraph_id_map:
        return paragraph_id

    for candidate in _build_anchor_candidates(original_excerpt, clause_position, additional_clues or []):
        matched = match_paragraph_id_by_excerpt(candidate, paragraph_id_map, clause_position)
        if matched:
            return matched

    if clause_position and clause_position != "未明确位置":
        return match_paragraph_id_by_clause_position(clause_position, paragraph_id_map)

    return None


def match_paragraph_id_by_excerpt(
    excerpt: str,
    paragraph_id_map: dict[str, Paragraph],
    clause_position: str = "",
) -> str | None:
    normalized_excerpt = "".join(excerpt.split())
    if not normalized_excerpt:
        return None

    exact_matches: list[str] = []
    for paragraph_id, paragraph in paragraph_id_map.items():
        paragraph_text = "".join(paragraph.text.split())
        if normalized_excerpt in paragraph_text:
            exact_matches.append(paragraph_id)
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        preferred = _prefer_precise_table_anchor(exact_matches, paragraph_id_map)
        if len(preferred) == 1:
            return preferred[0]
        exact_matches = preferred
        return _tie_break_by_clause_position(exact_matches, clause_position, paragraph_id_map)

    fragments = build_match_fragments(normalized_excerpt)
    if not fragments:
        return None

    best_paragraph_id: str | None = None
    best_score = 0
    second_score = 0

    for paragraph_id, paragraph in paragraph_id_map.items():
        paragraph_text = "".join(paragraph.text.split())
        score = sum(len(fragment) for fragment in fragments if fragment in paragraph_text)
        if score > best_score:
            second_score = best_score
            best_score = score
            best_paragraph_id = paragraph_id
        elif score > second_score:
            second_score = score

    minimum_score = max(12, min(len(normalized_excerpt), 40) // 2)
    if best_paragraph_id and best_score >= minimum_score and best_score >= second_score + 6:
        return best_paragraph_id

    matched = _match_paragraph_id_by_partial_similarity(normalized_excerpt, paragraph_id_map)
    if matched:
        return matched

    return _match_paragraph_id_by_similarity(normalized_excerpt, paragraph_id_map)


def match_paragraph_id_by_clause_position(
    clause_position: str,
    paragraph_id_map: dict[str, Paragraph],
) -> str | None:
    normalized_position = "".join(clause_position.split())
    if not normalized_position or normalized_position == "未明确位置":
        return None

    matches = [
        paragraph_id
        for paragraph_id, paragraph in paragraph_id_map.items()
        if normalized_position in "".join(paragraph.text.split())
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        preferred = _prefer_precise_table_anchor(matches, paragraph_id_map)
        if len(preferred) == 1:
            return preferred[0]
    return _match_paragraph_id_by_heading_number(normalized_position, paragraph_id_map)


def _tie_break_by_clause_position(
    paragraph_ids: list[str],
    clause_position: str,
    paragraph_id_map: dict[str, Paragraph],
) -> str | None:
    normalized_position = "".join((clause_position or "").split())
    if not normalized_position or normalized_position == "未明确位置":
        return None

    matches = [
        paragraph_id
        for paragraph_id in paragraph_ids
        if normalized_position in "".join(paragraph_id_map[paragraph_id].text.split())
    ]
    matches = _prefer_precise_table_anchor(matches, paragraph_id_map)
    if len(matches) == 1:
        return matches[0]
    return None


def build_match_fragments(normalized_excerpt: str) -> list[str]:
    parts = re.split(r"[，。；：、,.!?（）()“”‘’《》【】\[\]\-——\s]+", normalized_excerpt)
    threshold = max(2, min(8, len(normalized_excerpt) // 2))
    fragments = [part for part in parts if len(part) >= threshold]
    fragments.sort(key=len, reverse=True)
    return fragments[:6]


def _build_anchor_candidates(original_excerpt: str, clause_position: str, additional_clues: list[str]) -> list[str]:
    candidates = [original_excerpt, clause_position, *additional_clues]
    cleaned: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        text = _strip_non_anchor_noise(candidate)
        normalized = "".join(text.split())
        if len(normalized) < 3 or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(text)
    return cleaned


def _strip_non_anchor_noise(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"^(风险提示|风险分析|修改建议|原文位置及摘要|原文摘要|位置)[：:]\s*", "", value)
    value = re.sub(r"^(高|中|低)风险[：:，,]?\s*", "", value)
    value = re.sub(r"^(建议|应当|需要|可以|删除|改为)\s*", "", value)
    return value.strip()


def _match_paragraph_id_by_heading_number(
    normalized_position: str,
    paragraph_id_map: dict[str, Paragraph],
) -> str | None:
    article = re.search(r"第([一二三四五六七八九十百零〇\d]+)条", normalized_position)
    if not article:
        return None

    article_label = f"第{article.group(1)}条"
    matches = [
        paragraph_id
        for paragraph_id, paragraph in paragraph_id_map.items()
        if article_label in "".join(paragraph.text.split())
    ]
    matches = _prefer_precise_table_anchor(matches, paragraph_id_map)
    if len(matches) == 1:
        return matches[0]
    return None


def _match_paragraph_id_by_similarity(
    normalized_excerpt: str,
    paragraph_id_map: dict[str, Paragraph],
) -> str | None:
    if len(normalized_excerpt) < 8:
        return None

    best_paragraph_id: str | None = None
    best_score = 0.0
    second_score = 0.0

    for paragraph_id, paragraph in paragraph_id_map.items():
        paragraph_text = "".join(paragraph.text.split())
        if len(paragraph_text) < 8:
            continue
        score = SequenceMatcher(None, normalized_excerpt, paragraph_text).ratio()
        if score > best_score:
            second_score = best_score
            best_score = score
            best_paragraph_id = paragraph_id
        elif score > second_score:
            second_score = score

    if best_paragraph_id and best_score >= 0.58 and best_score >= second_score + 0.08:
        return best_paragraph_id
    return None


def _match_paragraph_id_by_partial_similarity(
    normalized_excerpt: str,
    paragraph_id_map: dict[str, Paragraph],
) -> str | None:
    if len(normalized_excerpt) < 6:
        return None

    best_paragraph_id: str | None = None
    best_score = 0.0
    second_score = 0.0
    excerpt_len = len(normalized_excerpt)

    for paragraph_id, paragraph in paragraph_id_map.items():
        paragraph_text = "".join(paragraph.text.split())
        if len(paragraph_text) < 6:
            continue
        window_min = max(4, excerpt_len - 4)
        window_max = min(len(paragraph_text), excerpt_len + 8)
        paragraph_best = 0.0
        for window_len in range(window_min, window_max + 1):
            for start in range(0, len(paragraph_text) - window_len + 1):
                candidate = paragraph_text[start : start + window_len]
                paragraph_best = max(paragraph_best, SequenceMatcher(None, normalized_excerpt, candidate).ratio())
        if paragraph_best > best_score:
            second_score = best_score
            best_score = paragraph_best
            best_paragraph_id = paragraph_id
        elif paragraph_best > second_score:
            second_score = paragraph_best

    if best_paragraph_id and best_score >= 0.62 and best_score >= second_score + 0.08:
        return best_paragraph_id
    return None


def _prefer_precise_table_anchor(paragraph_ids: list[str], paragraph_id_map: dict[str, Paragraph]) -> list[str]:
    if len(paragraph_ids) <= 1:
        return paragraph_ids

    cell_level = [pid for pid in paragraph_ids if paragraph_id_map[pid].source == "docx-table-cell"]
    if cell_level:
        return cell_level
    return paragraph_ids
