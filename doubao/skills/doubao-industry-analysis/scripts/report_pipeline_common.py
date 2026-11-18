from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable


WORK_ROOT = Path.cwd()
DEFAULT_PARTS_DIR = WORK_ROOT / "parts"
DEFAULT_OUTPUT_PATH = WORK_ROOT / "output" / "report.md"


FINAL_REQUIRED_SECTIONS: tuple[str, ...] = (
    "## 核心观点",
    "## 一、行业定义、规模测算与历史坐标",
    "## 二、行业结构、竞争格局与格局演变",
    "## 三、核心驱动力与制约因素",
    "## 四、趋势研判与结构性机会",
    "## 五、商业化路径、盈利质量与落地建议",
    "## 风险提示",
    "## 结语",
    "## 参考文献",
)


REFERENCE_HEADING = "## 参考文献"
DISCLAIMER_MARKER = "风险提示与免责声明："
RECAP_HEADING = "### 回扣主线"
TITLE_PATTERN = re.compile(r"^\s*#\s+\S", re.MULTILINE)
CITATION_PATTERN = re.compile(r"(?<!\!)\[(\d+)\](?!\()")
BRACKET_REFERENCE_PATTERN = re.compile(r"^\s*\[(\d+)\]\s+", re.MULTILINE)
TABLE_SEPARATOR_PATTERN = re.compile(
    r"^\s*\|.*\|\s*$\n^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$",
    re.MULTILINE,
)
RAW_TAG_PATTERN = re.compile(r"<[A-Za-z/][^>]*>")
OLD_PIPELINE_PATTERN = re.compile(
    r"Docx\x58ML|docs\s+\+(?:create|update|fetch)|block_insert\x5fafter",
    re.IGNORECASE,
)


class ValidationError(Exception):
    pass


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def normalize_trailing_newline(text: str) -> str:
    return text.rstrip() + "\n"


def has_markdown_table(text: str) -> bool:
    return bool(TABLE_SEPARATOR_PATTERN.search(text))


def has_forbidden_markup(text: str) -> bool:
    return bool(RAW_TAG_PATTERN.search(text) or OLD_PIPELINE_PATTERN.search(text))


def extract_citations(text: str) -> list[int]:
    return [int(match) for match in CITATION_PATTERN.findall(text)]


def extract_reference_numbers(text: str) -> list[int]:
    return [int(match) for match in BRACKET_REFERENCE_PATTERN.findall(text)]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def check_contiguous_numbers(numbers: Iterable[int], label: str) -> None:
    unique_numbers = sorted(set(numbers))
    if not unique_numbers:
        return
    expected = list(range(1, unique_numbers[-1] + 1))
    require(
        unique_numbers == expected,
        f"{label} 编号不连续，当前为 {unique_numbers}，期望为 {expected}",
    )


def check_first_appearance_order(text: str, label: str, hint: str = "") -> None:
    """新来源编号必须按正文首次出现顺序 1,2,3… 递增；允许后文复用旧编号。

    这是 SKILL.md 与 lark-doc-report-standard.md 已声明、但 check_contiguous_numbers
    检不出来的规则：后者只查集合等于 {1..max}，[3][11][14]… 这类首现乱序会被放行。
    """
    seen: list[int] = []
    for match in CITATION_PATTERN.finditer(text):
        number = int(match.group(1))
        if number not in seen:
            expected = len(seen) + 1
            require(
                number == expected,
                f"{label} 首现顺序错乱：期望新来源编号为 [{expected}]，实际出现 [{number}]，"
                f"当前首现序列 {seen + [number]}。{hint}",
            )
            seen.append(number)


def split_reference_section(text: str) -> tuple[str, str, str]:
    reference_index = text.find(REFERENCE_HEADING)
    require(reference_index != -1, "缺少 `## 参考文献` 标题")

    body = text[:reference_index]
    after_reference = text[reference_index + len(REFERENCE_HEADING) :]
    disclaimer_index = after_reference.find(DISCLAIMER_MARKER)
    if disclaimer_index == -1:
        return body, after_reference, ""
    return (
        body,
        after_reference[:disclaimer_index],
        after_reference[disclaimer_index:],
    )


def expected_part_paths(parts_dir: Path) -> list[Path]:
    return sorted(parts_dir.glob("*.md"))
