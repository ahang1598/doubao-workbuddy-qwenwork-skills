#!/usr/bin/env python3
"""内部 helper：生成不含内部标记的读者可见 Markdown 副本。

交付请用 finalize_report.py。源稿保留 `{fact:claim_id}` 绑定用于审计；这个
helper 生成单独的 display markdown，用于创建飞书文档——当 facts.json 可用时，把
`{fact:claim_id}` 转换成普通文本 `[n]` 来源标记。也兼容遗留的 `[^1]` 角标写法，
并把遗留脚注定义转换成编号来源列表。

引用编号规则：按第一次出现的顺序编号；**同一 (来源文本, 链接) 组合去重**——同一
个来源被多个不同 claim_id 引用，或同一 claim 被多次引用，都只占一个编号。

来源列表的写入位置：脚本会在源稿里查找已经存在的「## 数据来源」标题或
「文中引用对应以下来源：」标记行，把生成的编号列表插入到那里。若源稿残留
「未获取清单」区块，会在生成 display markdown 时剥掉（成品不再展示缺口清单，
免责声明已覆盖信息缺漏）。如果源稿里完全没有这两个标记，才会在「### 风险提示」
之前（或文末）新插入一个「## 数据来源」区块。**这意味着源稿本身应该已经写好
「数据来源」骨架标题和风险提示区块**，脚本只负责填充编号列表，不负责生成免责
声明文字。
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


def strip_missing_list_section(lines: list[str]) -> list[str]:
    """成品不展示「未获取清单」：从该标题起删到下一个 Markdown 标题之前。"""
    start = next((idx for idx, line in enumerate(lines) if is_missing_list_start(line)), None)
    if start is None:
        return lines
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if HEADING_RE.match(lines[idx].strip()):
            end = idx
            break
    # 顺带清掉标题前多余空行
    while start > 0 and not lines[start - 1].strip():
        start -= 1
    return lines[:start] + lines[end:]


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

    # 源稿若残留「未获取清单」，落在 start_idx..end_idx 之间会被整段替换掉。
    if heading_idx is not None:
        replacement = [lines[heading_idx], "", "文中引用对应以下来源：", "", *source_entries]
        prefix = lines[:heading_idx]
    else:
        replacement = [lines[marker_idx], "", *source_entries]  # type: ignore[index]
        prefix = lines[:marker_idx]  # type: ignore[index]

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
    out = strip_missing_list_section(out)
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="内部 helper。交付请用 finalize_report.py；这里只生成 display markdown。"
    )
    parser.add_argument("input", help="含内部 fact 绑定的源 Markdown 文件")
    parser.add_argument("output", nargs="?", default=None, help="display markdown 输出路径（默认 <输入文件名>-display.md）")
    parser.add_argument("--facts", default=None, help="可选 facts.json；用于把 {fact:claim_id} 转换成 [n] 标记")
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
