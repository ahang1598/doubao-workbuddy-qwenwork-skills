#!/usr/bin/env python3
"""Finalize an authored HTML report without converting Markdown to HTML.

The existing facts check and report lint still run. For lint, the visible HTML
text is extracted to a temporary file; the authored HTML layout stays intact.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from normalize_report import normalize_markdown


SCRIPT_DIR = Path(__file__).resolve().parent
FACT_RE = re.compile(r"\{fact:([^{}\n]+)\}")
FACT_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
BLOCK_TAGS = {"p", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "section", "article"}


def source_group(claim: dict) -> str:
    kind = str(claim.get("source_type") or "")
    tier = str(claim.get("tier") or "")
    if kind in {"company_report", "company_annual_report", "company_quarterly_report", "company_announcement", "exchange_filing"} or tier == "official":
        return "公司公告及定期报告"
    if kind in {"broker_research", "broker_consensus", "sellside_research"} or tier == "broker":
        return "机构研究报告"
    if kind in {"market_database", "market_data", "official_database"} or tier == "market":
        return "行情数据"
    return "说明会与新闻"


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden: list[str] = []
        self.parts: list[str] = []
        self.attribute_refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"head", "style", "script"}:
            self.hidden.append(tag)
        for _, value in attrs:
            if value and "{fact:" in value:
                self.attribute_refs.append(value)
        if not self.hidden and tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        if not self.hidden and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)

    def handle_comment(self, data: str) -> None:
        if "{fact:" in data:
            self.attribute_refs.append(data)

    def text(self) -> str:
        return re.sub(r"[ \t]+", " ", "".join(self.parts))


class LinkSources(HTMLParser):
    def __init__(self, claims: dict[str, dict]) -> None:
        super().__init__(convert_charrefs=False)
        self.claims = claims
        self.parts: list[str] = []
        self.sources: list[tuple[str, str]] = []
        self.source_numbers: dict[tuple[str, str], int] = {}
        self.categories: dict[tuple[str, str], str] = {}
        self.hidden: list[str] = []

    def handle_decl(self, decl: str) -> None:
        self.parts.append(f"<!{decl}>")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.parts.append(self.get_starttag_text())
        if tag in {"head", "style", "script"}:
            self.hidden.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag: str) -> None:
        self.parts.append(f"</{tag}>")
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()

    def handle_comment(self, data: str) -> None:
        self.parts.append(f"<!--{data}-->")

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def handle_data(self, data: str) -> None:
        if self.hidden:
            self.parts.append(data)
            return
        data = normalize_markdown(data)

        def replace(match: re.Match[str]) -> str:
            numbers: list[int] = []
            for raw_id in re.split(r"[,，、]", match.group(1)):
                claim = self.claims[raw_id.strip()]
                label = str(claim.get("source") or raw_id.strip()).strip()
                url = str(claim.get("url") or "").strip()
                key = (label, url)
                if key not in self.source_numbers:
                    self.source_numbers[key] = len(self.sources) + 1
                    self.sources.append(key)
                    self.categories[key] = source_group(claim)
                number = self.source_numbers[key]
                if number not in numbers:
                    numbers.append(number)
            return "".join(f'<a class="source-ref" href="#source-{n}" aria-label="来源 {n}">[{n}]</a>' for n in numbers)

        self.parts.append(FACT_RE.sub(replace, data))


def sources_html(sources: list[tuple[str, str]], categories: dict[tuple[str, str], str]) -> str:
    groups: dict[str, list[str]] = {}
    for number, (label, url) in enumerate(sources, 1):
        label_html = html.escape(label)
        if urlparse(url).scheme in {"http", "https"}:
            label_html = f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{label_html}</a>'
        category = categories.get((label, url), "说明会与新闻")
        groups.setdefault(category, []).append(f'<li id="source-{number}" value="{number}">{label_html}</li>')
    parts = ['<section id="sources" class="report-sources"><h2>数据来源</h2><p>文中引用对应以下来源：</p>']
    for category in ("公司公告及定期报告", "说明会与新闻", "机构研究报告", "行情数据"):
        rows = groups.get(category)
        if rows:
            parts.append(f'<h3>{category}</h3><ol>' + "".join(rows) + "</ol>")
    parts.append("</section>")
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check authored HTML and resolve fact sources")
    parser.add_argument("source", type=Path)
    parser.add_argument("facts", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    facts_path = args.facts.resolve()
    output = args.output.resolve()
    if output in {source, facts_path}:
        raise ValueError("最终 HTML 不能覆盖源稿或事实表")
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    claims = {item["claim_id"]: item for item in facts.get("claims", []) if isinstance(item, dict) and isinstance(item.get("claim_id"), str)}
    authored = source.read_text(encoding="utf-8")
    visible = VisibleText()
    visible.feed(authored)
    if visible.attribute_refs:
        raise ValueError("{fact:...} 只能放在页面可见文字中，不能放在属性或注释中")
    for group in FACT_RE.findall(visible.text()):
        for raw_id in re.split(r"[,，、]", group):
            fact_id = raw_id.strip()
            if not FACT_ID_RE.fullmatch(fact_id) or fact_id not in claims:
                raise ValueError(f"无效或未知事实绑定：{fact_id}")
    if len(FACT_RE.findall(authored)) != len(FACT_RE.findall(visible.text())):
        raise ValueError("HTML 的隐藏内容中含有事实绑定")
    subprocess.run([sys.executable, str(SCRIPT_DIR / "check_facts.py"), str(facts_path)], check=True)
    with tempfile.TemporaryDirectory() as folder:
        lint_input = Path(folder) / "visible-report.md"
        cited = [claims[raw_id.strip()] for group in FACT_RE.findall(visible.text()) for raw_id in re.split(r"[,，、]", group)]
        source_lines = [f'[{item.get("source", "来源")}]({item.get("url")})' for item in cited if item.get("url")]
        lint_text = visible.text() + "\n## 数据来源\n" + "\n".join(source_lines)
        lint_input.write_text(normalize_markdown(lint_text), encoding="utf-8")
        subprocess.run([sys.executable, str(SCRIPT_DIR / "lint_report.py"), str(lint_input), str(facts_path)], check=True)
    linker = LinkSources(claims)
    linker.feed(authored)
    final = "".join(linker.parts)
    source_list = sources_html(linker.sources, linker.categories)
    if "<!-- AUTO_SOURCES -->" in final:
        final = final.replace("<!-- AUTO_SOURCES -->", source_list, 1)
    else:
        closing = list(re.finditer(r"</main\s*>", final, re.I)) or list(re.finditer(r"</body\s*>", final, re.I))
        if closing:
            pos = closing[-1].start()
            final = final[:pos] + source_list + final[pos:]
        else:
            final += source_list
    if FACT_RE.search(final):
        raise ValueError("最终 HTML 仍有未处理的事实绑定")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(final, encoding="utf-8")
    print(f"Final HTML saved: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"[错误] {exc}") from exc
