#!/usr/bin/env python3
"""Internal helper: create a reader-facing markdown copy without internal markers.

Use finalize_report.py for delivery. The source markdown keeps fact bindings
for audit; this helper writes a separate display markdown for Feishu document
creation by converting {fact:...} to plain [n] source markers when facts.json
is available. It also tolerates legacy [^1] markers and converts legacy
footnote definitions to a numbered source list.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LEGACY_INLINE_CITATION_RE = re.compile(r"\[\^[0-9A-Za-z_-]+\]")
FOOTNOTE_DEF_RE = re.compile(r"^(\s*)\[\^([0-9A-Za-z_-]+)\]:\s*(.*)$")
SPACE_BEFORE_CN_PUNCT_RE = re.compile(r"\s+([，。；：！？、])")
FACT_REF_RE = re.compile(r"\{facts?:([^{}\n]*)\}")
FACT_ID_SPLIT_RE = re.compile(r"[,，、]")
CITATION_AFTER_PUNCT_RE = re.compile(r"([，。；：！？、])((?:\[\d+\])+)")
HEADING_RE = re.compile(r"^#{1,6}\s+")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")


def is_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def load_claims(facts_path: Path | None) -> dict[str, dict]:
    if facts_path is None:
        return {}
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    claims_raw = facts.get("claims")
    if not isinstance(claims_raw, list):
        return {}
    claims: dict[str, dict] = {}
    for item in claims_raw:
        if not isinstance(item, dict):
            continue
        claim_id = item.get("claim_id")
        if isinstance(claim_id, str) and claim_id.strip():
            claims[claim_id.strip()] = item
    return claims


def parse_fact_ids(raw_group: str) -> list[str]:
    ids: list[str] = []
    for raw in FACT_ID_SPLIT_RE.split(raw_group):
        fact_id = raw.strip()
        if fact_id and fact_id not in ids:
            ids.append(fact_id)
    return ids


def source_text(claim: dict, fact_id: str) -> str:
    source = str(claim.get("source") or "").strip()
    if source:
        return source
    metric = str(claim.get("metric") or "").strip()
    period = str(claim.get("period") or "").strip()
    if metric and period:
        return f"{metric}（{period}）"
    return fact_id


def source_url(claim: dict) -> str:
    return str(claim.get("url") or "").strip()


def format_source_entry(number: int, source: str, url: str) -> str:
    if url and not MARKDOWN_LINK_RE.search(source):
        label = source.replace("[", r"\[").replace("]", r"\]")
        return f"{number}. [{label}]({url})"
    return f"{number}. {source}"


class CitationRegistry:
    def __init__(self, claims: dict[str, dict]) -> None:
        self.claims = claims
        self.source_to_number: dict[tuple[str, str], int] = {}
        self.sources: list[tuple[int, str, str]] = []

    def marker_for_fact_group(self, raw_group: str) -> str:
        numbers: list[int] = []
        for fact_id in parse_fact_ids(raw_group):
            claim = self.claims.get(fact_id)
            if not claim:
                continue
            source = source_text(claim, fact_id)
            url = source_url(claim)
            key = (source, url)
            if key not in self.source_to_number:
                number = len(self.sources) + 1
                self.source_to_number[key] = number
                self.sources.append((number, source, url))
            number = self.source_to_number[key]
            if number not in numbers:
                numbers.append(number)
        return "".join(f"[{number}]" for number in sorted(numbers))

    def source_entries(self) -> list[str]:
        return [format_source_entry(number, source, url) for number, source, url in self.sources]


def strip_internal_markers(line: str, citations: CitationRegistry | None = None) -> str:
    line = LEGACY_INLINE_CITATION_RE.sub("", line)
    if citations is not None and citations.claims:
        line = FACT_REF_RE.sub(lambda match: citations.marker_for_fact_group(match.group(1)), line)
    else:
        line = FACT_REF_RE.sub("", line)
    line = CITATION_AFTER_PUNCT_RE.sub(r"\2\1", line)
    line = SPACE_BEFORE_CN_PUNCT_RE.sub(r"\1", line)
    return line.rstrip()


def is_source_heading(line: str) -> bool:
    return line.strip().startswith("## 数据来源")


def is_missing_list_start(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("**未获取清单**")
        or stripped.startswith("- **未获取清单**")
        or stripped.startswith("未获取清单")
    )


def rewrite_source_section(lines: list[str], source_entries: list[str]) -> list[str]:
    if not source_entries:
        return lines

    heading_idx = next((idx for idx, line in enumerate(lines) if is_source_heading(line)), None)
    marker_idx = next((idx for idx, line in enumerate(lines) if line.strip() == "文中引用对应以下来源："), None)

    if heading_idx is None and marker_idx is None:
        insert_at = next(
            (idx for idx, line in enumerate(lines) if line.strip().startswith("### 风险提示")),
            len(lines),
        )
        block = ["", "## 数据来源", "", "文中引用对应以下来源：", "", *source_entries]
        return lines[:insert_at] + block + [""] + lines[insert_at:]

    start_idx = heading_idx if heading_idx is not None else marker_idx
    assert start_idx is not None

    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        if HEADING_RE.match(lines[idx].strip()):
            end_idx = idx
            break

    missing_idx = next(
        (idx for idx in range(start_idx + 1, end_idx) if is_missing_list_start(lines[idx])),
        None,
    )
    preserved_tail: list[str] = []
    if missing_idx is not None:
        preserved_tail = lines[missing_idx:end_idx]
        while preserved_tail and not preserved_tail[0].strip():
            preserved_tail.pop(0)

    if heading_idx is not None:
        replacement = [lines[heading_idx], "", "文中引用对应以下来源：", "", *source_entries]
        prefix = lines[:heading_idx]
    else:
        replacement = [lines[marker_idx], "", *source_entries]  # type: ignore[index]
        prefix = lines[:marker_idx]  # type: ignore[index]

    if preserved_tail:
        replacement.extend(["", *preserved_tail])

    if lines[end_idx:] and replacement and replacement[-1].strip():
        replacement.append("")

    return prefix + replacement + lines[end_idx:]


def make_display_markdown(text: str, claims: dict[str, dict] | None = None) -> str:
    out: list[str] = []
    in_fence = False
    citations = CitationRegistry(claims or {})
    for raw in text.splitlines():
        if is_fence(raw):
            out.append(raw)
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(raw)
            continue

        footnote_def = FOOTNOTE_DEF_RE.match(raw)
        if footnote_def:
            indent, number, body = footnote_def.groups()
            out.append(f"{indent}{number}. {strip_internal_markers(body, citations)}")
            continue

        out.append(strip_internal_markers(raw, citations))

    out = rewrite_source_section(out, citations.source_entries())
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Internal helper. Prefer finalize_report.py for delivery; this only creates display markdown."
    )
    parser.add_argument("input", help="Input markdown file with internal fact bindings")
    parser.add_argument("output", nargs="?", default=None, help="Output display markdown path (default: <input-stem>-display.md)")
    parser.add_argument("--facts", default=None, help="Optional facts.json; used to convert {fact:claim_id} into [n] markers")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve() if args.output else input_path.with_name(f"{input_path.stem}-display.md")
    facts_path = Path(args.facts).resolve() if args.facts else None
    if output_path == input_path:
        raise SystemExit("[错误] display markdown 不能覆盖源 markdown；请运行 finalize_report.py 生成交付文件。")

    claims = load_claims(facts_path)
    display = make_display_markdown(input_path.read_text(encoding="utf-8"), claims)
    output_path.write_text(display, encoding="utf-8")
    print(f"Display markdown saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
