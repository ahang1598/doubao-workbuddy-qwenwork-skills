from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class ReportValidationError(ValueError):
    """Raised when generated Markdown does not satisfy delivery constraints."""


MINIMUM_ANNOTATION_FIELDS = (
    "risk_message",
    "risk_analysis",
    "revision_suggestion",
)

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "rule_id": ("rule_id", "ruleId", "ruleNo", "rule_no", "规则编号"),
    "clause_title": ("clause_title", "clauseTitle", "title", "clause", "条款标题", "风险点"),
    "clause_position": ("clause_position", "clausePosition", "position", "location", "原文位置", "位置"),
    "paragraph_id": ("paragraph_id", "paragraphId", "anchor_paragraph_id"),
    "risk_level": ("risk_level", "riskLevel", "level", "风险等级"),
    "risk_type": ("risk_type", "riskType", "type", "风险类型"),
    "original_excerpt": ("original_excerpt", "originalExcerpt", "excerpt", "original_text", "source_text", "quote_text", "原文摘要", "原文"),
    "risk_message": ("risk_message", "riskMessage", "description", "remark", "comment", "风险提示"),
    "risk_analysis": ("risk_analysis", "riskAnalysis", "analysis", "legal_basis", "reasoning", "风险分析"),
    "revision_suggestion": ("revision_suggestion", "revisionSuggestion", "suggestion", "advice", "proposal", "修改建议"),
    "revised_text_example": ("revised_text_example", "revisedTextExample", "new_text", "revised_text", "replacement_text", "修改后文本示例"),
    "comment_title": ("comment_title", "commentTitle", "批注标题"),
    "comment_author": ("comment_author", "commentAuthor", "批注作者"),
}

REPORT_KEYS = (
    "report_markdown",
    "reportMarkdown",
    "markdown",
    "reviewMarkdown",
    "review_report",
    "reviewReport",
    "report",
    "content",
    "resultContent",
)

ISSUE_KEYS = (
    "issues",
    "riskItems",
    "risk_items",
    "risks",
    "reviewIssues",
    "review_issue_list",
    "problemList",
    "details",
)

REQUIRED_SECTION_HEADINGS = (
    "## 一、核心结论",
    "## 二、关键风险（精简版）",
    "## 三、针对行业的特别说明（自动生成）",
    "## 四、完整审查明细",
    "## 五、其他合规提示",
    "## 六、附件下载",
)

REQUIRED_DETAIL_SUBHEADINGS = (
    "### 7. 整体修改建议",
    "### 8. 谈判与签署建议",
)

DEFAULT_COMMENT_AUTHOR = "劳动合同审查助手"

FORBIDDEN_ATTACHMENT_PLACEHOLDERS = (
    "尝试生成",
    "待生成",
    "正在生成",
    "report_path",
    "下载地址待补充",
    "直接附上的 docx 文件",
)

HTML_BREAK_RE = re.compile(r"\s*<br\s*/?>\s*", flags=re.IGNORECASE)
ESCAPED_LINEBREAK_RE = re.compile(r"\\r\\n|\\n|\\r")
RISK_LEVEL_GROUP_HEADING_RE = re.compile(r"^###\s+\d+[.、]\s*(高风险问题|中风险问题|低风险问题)\s*$", re.MULTILINE)
BLANK_PLACEHOLDER_RE = re.compile(r"_{2,}|＿{2,}|□+|[　 ]{4,}|（\s*）|\(\s*\)")
BLANK_TEMPLATE_TERMS = (
    "空白",
    "留白",
    "待填",
    "待填写",
    "手工填写",
    "未填写",
)
BLANK_TEMPLATE_FIELDS = (
    "主体信息",
    "姓名",
    "身份证",
    "证件",
    "住址",
    "地址",
    "通讯地址",
    "电话",
    "联系方式",
    "联系人",
    "电子邮箱",
    "邮箱",
    "乙方",
    "甲方",
    "合同期限",
    "岗位地点",
    "工作地点",
    "工时制度",
    "工资",
    "劳动报酬",
    "试用期",
    "发薪",
    "支付日期",
    "签署日期",
    "签字",
    "盖章",
)


def load_raw_result(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_report_markdown(raw: Any) -> str:
    direct = _find_report_string(raw)
    if direct:
        return direct.strip()
    return "```json\n" + json.dumps(raw, ensure_ascii=False, indent=2) + "\n```"


def extract_issues(raw: Any, report_markdown: str | None = None) -> list[dict[str, str]]:
    issues = [_normalize_issue(item) for item in _find_issue_dicts(raw)]
    issues = [issue for issue in issues if _has_issue_signal(issue)]
    issues = [issue for issue in issues if not _is_blank_template_issue(issue)]
    if issues:
        return _dedupe_issues(issues)
    if report_markdown:
        parsed = [issue for issue in _parse_issues_from_markdown(report_markdown) if not _is_blank_template_issue(issue)]
        return _dedupe_issues(parsed)
    return []


def write_outputs(raw: Any, output_dir: Path, stem: str = "review") -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_markdown = normalize_report_markdown(extract_report_markdown(raw))
    validate_report_markdown(report_markdown)
    issues = extract_issues(raw, report_markdown)

    report_path = output_dir / f"{stem}.md"
    issues_path = output_dir / f"{stem}_issues.json"
    report_path.write_text(report_markdown.rstrip() + "\n", encoding="utf-8")
    issues_path.write_text(json.dumps({"issues": issues}, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path, issues_path


def normalize_report_markdown(report_markdown: str) -> str:
    lines = []
    for line in report_markdown.splitlines():
        if line.strip().startswith("|"):
            line = ESCAPED_LINEBREAK_RE.sub(" ", line)
            line = HTML_BREAK_RE.sub(" ", line)
        else:
            line = ESCAPED_LINEBREAK_RE.sub("\n", line)
            line = HTML_BREAK_RE.sub("\n", line)
        lines.append(line)
    return "\n".join(lines).strip()


def normalize_issue_for_annotation(item: dict[str, Any]) -> dict[str, str]:
    issue = _normalize_issue(item)
    if _is_blank_template_issue(issue):
        raise ValueError("空白模板待填栏位不生成批注。")
    if not issue.get("risk_message"):
        issue["risk_message"] = issue.get("risk_type") or issue.get("clause_title") or "请关注该条款风险。"
    missing = [field for field in MINIMUM_ANNOTATION_FIELDS if not issue.get(field)]
    if missing:
        raise ValueError(f"风险项缺少生成批注所需字段: {', '.join(missing)}")
    return issue


def validate_report_markdown(report_markdown: str) -> None:
    text = report_markdown.strip()
    if not text.startswith("# 劳动合同审查报告"):
        raise ReportValidationError("报告必须从 `# 劳动合同审查报告` 开始。")
    if HTML_BREAK_RE.search(text):
        raise ReportValidationError("报告不得包含 HTML 换行标签 `<br>`，请使用纯 Markdown 内容。")
    if ESCAPED_LINEBREAK_RE.search(text):
        raise ReportValidationError("报告不得包含字面量 `\\n` 换行符，请使用纯 Markdown 内容。")

    for heading in REQUIRED_SECTION_HEADINGS:
        if heading not in text:
            raise ReportValidationError(f"报告缺少必备章节：`{heading}`。")

    for heading in REQUIRED_DETAIL_SUBHEADINGS:
        if heading not in text:
            raise ReportValidationError(f"报告缺少必备小节：`{heading}`。")

    attachment_section = _extract_section(text, "## 六、附件下载")
    if not _contains_markdown_table(attachment_section):
        raise ReportValidationError("`## 六、附件下载` 下必须包含 Markdown 表格。")
    for placeholder in FORBIDDEN_ATTACHMENT_PLACEHOLDERS:
        if placeholder in attachment_section:
            raise ReportValidationError(f"附件表格包含非法占位词：`{placeholder}`。")

    negotiation_section = _extract_section(text, "### 8. 谈判与签署建议")
    if _count_actionable_suggestions(negotiation_section) < 2:
        raise ReportValidationError("`### 8. 谈判与签署建议` 至少需要 2 条实际建议。")

    detail_section = _extract_section(text, "## 四、完整审查明细", "## 五、其他合规提示")
    if RISK_LEVEL_GROUP_HEADING_RE.search(detail_section):
        raise ReportValidationError("`## 四、完整审查明细` 中的风险卡片必须按合同条款顺序排列，不得按高/中/低风险分组。")
    if _contains_misheaded_risk_card(detail_section):
        raise ReportValidationError("风险卡片应使用 `| 项目 | 内容 |` 表头；需确认事项应使用 `| 审查项 | 注意事项 |`。")
    if "| 审查项 | 发现问题 |" in detail_section:
        raise ReportValidationError("报告中不得使用 `| 审查项 | 发现问题 |` 表头；需确认事项应使用 `| 审查项 | 注意事项 |`。")
    if _report_declares_actionable_risk(text) and not _contains_valid_risk_card(detail_section):
        raise ReportValidationError(
            "`### 2. 按合同条款顺序的风险问题` 下至少需要 1 个 `####` 风险卡片，且风险卡片必须使用 `| 项目 | 内容 |` 表头。"
        )
    if _contains_blank_template_risk_card(detail_section):
        raise ReportValidationError("打印空白模板中的待填写栏位不得作为高/中/低风险卡片输出，应写入需确认事项或签署动作。")


def _find_report_string(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        if _is_report_markdown(text):
            return text
        return None
    if isinstance(value, dict):
        for key in REPORT_KEYS:
            candidate = value.get(key)
            if isinstance(candidate, str) and _is_report_markdown(candidate.strip()):
                return candidate.strip()
        for candidate in value.values():
            found = _find_report_string(candidate)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_report_string(item)
            if found:
                return found
    return None


def _is_report_markdown(text: str) -> bool:
    return "# 劳动合同审查报告" in text or "## 一、核心结论" in text


def _extract_section(text: str, start_heading: str, end_heading: str | None = None) -> str:
    start = text.find(start_heading)
    if start < 0:
        return ""

    if end_heading:
        end = text.find(end_heading, start + len(start_heading))
        if end >= 0:
            return text[start:end]

    next_section = re.search(r"^##\s+", text[start + len(start_heading) :], flags=re.MULTILINE)
    if next_section:
        end = start + len(start_heading) + next_section.start()
        return text[start:end]
    return text[start:]


def _contains_markdown_table(section: str) -> bool:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    for index in range(len(lines) - 1):
        if lines[index].startswith("|") and lines[index + 1].startswith("|"):
            return True
    return False


def _contains_risk_card_table(section: str) -> bool:
    lines = [line.strip() for line in section.splitlines()]
    for index in range(len(lines) - 1):
        header = lines[index]
        separator = lines[index + 1]
        if header == "| 项目 | 内容 |" and separator.startswith("| ---"):
            return True
    return False


def _report_declares_actionable_risk(text: str) -> bool:
    if "无明确命中风险" in text and "必须修改（不改会出事） | 无明确命中风险" in text:
        return False
    core_sections = "\n".join(
        [
            _extract_section(text, "## 一、核心结论", "## 二、关键风险（精简版）"),
            _extract_section(text, "## 二、关键风险（精简版）", "## 三、针对行业的特别说明（自动生成）"),
        ]
    )
    return bool(re.search(r"🔴\s*高风险|🟡\s*中风险|\|\s*(高风险|中风险)\s*\|", core_sections))


def _risk_problem_sections(detail_section: str) -> list[str]:
    return [
        _extract_section(detail_section, "### 2. 按合同条款顺序的风险问题", "### 6. 需用户确认或文本无法确定事项"),
        _extract_section(detail_section, "### 2. 风险问题", "### 6. 需用户确认或文本无法确定事项"),
    ]


def _contains_valid_risk_card(detail_section: str) -> bool:
    for section in _risk_problem_sections(detail_section):
        for block in re.split(r"(?=^####\s+)", section, flags=re.MULTILINE):
            if not block.strip().startswith("####"):
                continue
            if not _contains_risk_card_table(block):
                continue
            if "| 风险等级 |" in block and "| 风险类型 |" in block and "| 修改建议 |" in block:
                return True
    return False


def _contains_blank_template_risk_card(detail_section: str) -> bool:
    for section in _risk_problem_sections(detail_section):
        for block in re.split(r"(?=^####\s+)", section, flags=re.MULTILINE):
            if not block.strip().startswith("####"):
                continue
            source_text = _risk_card_source_text(block)
            if _looks_like_blank_template_text(source_text):
                return True
    return False


def _contains_misheaded_risk_card(detail_section: str) -> bool:
    for section in _risk_problem_sections(detail_section):
        for block in re.split(r"(?=^####\s+)", section, flags=re.MULTILINE):
            if not block.strip().startswith("####"):
                continue
            if "| 审查项 | 发现问题 |" in block or "| 审查项 | 注意事项 |" in block:
                return True
    return False


def _risk_card_source_text(block: str) -> str:
    lines = [line.strip() for line in block.splitlines()]
    heading = lines[0] if lines else ""
    source_parts = [heading]
    for line in lines:
        if not line.startswith("|") or line.count("|") < 3:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0] in {"原文位置及摘要", "原文位置", "原文摘要"}:
            source_parts.append(cells[1])
    return " ".join(source_parts)


def _count_actionable_suggestions(section: str) -> int:
    count = 0
    for line in section.splitlines():
        stripped = line.strip()
        if re.match(r"^\d+[.)、]\s+\S+", stripped):
            count += 1

    if count:
        return count

    rows = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    data_rows = 0
    for row in rows:
        if row in {"| 审查项 | 发现问题 |", "| 审查项 | 注意事项 |", "| 项目 | 内容 |"}:
            continue
        if re.fullmatch(r"\|?[\s:\-]+\|[\s\|:\-]*", row):
            continue
        data_rows += 1
    return data_rows


def _find_issue_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key in ISSUE_KEYS:
            candidate = value.get(key)
            if isinstance(candidate, list):
                found.extend(item for item in candidate if isinstance(item, dict))
        for candidate in value.values():
            found.extend(_find_issue_dicts(candidate))
    elif isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            issue_like = [item for item in value if _looks_like_issue(item)]
            if issue_like:
                found.extend(issue_like)
        for item in value:
            found.extend(_find_issue_dicts(item))
    return found


def _looks_like_issue(item: dict[str, Any]) -> bool:
    keys = set(item)
    alias_hits = 0
    for aliases in FIELD_ALIASES.values():
        if keys.intersection(aliases):
            alias_hits += 1
    return alias_hits >= 3


def _normalize_issue(item: dict[str, Any]) -> dict[str, str]:
    issue = {field: _first_text(item, aliases) for field, aliases in FIELD_ALIASES.items()}
    issue["risk_level"] = issue.get("risk_level", "").replace("风险", "").strip() or "中"
    issue["risk_type"] = issue.get("risk_type", "").strip() or _default_risk_type(issue["risk_level"])
    issue["rule_id"] = issue.get("rule_id", "").strip() or "EXTENDED"
    issue["clause_title"] = issue.get("clause_title", "").strip() or "风险条款"
    issue["clause_position"] = issue.get("clause_position", "").strip() or "未明确位置"
    issue["comment_title"] = issue.get("comment_title", "").strip() or "风险提示"
    issue["comment_author"] = DEFAULT_COMMENT_AUTHOR
    return issue


def _has_issue_signal(issue: dict[str, str]) -> bool:
    return bool(issue.get("risk_message") or issue.get("risk_analysis") or issue.get("revision_suggestion"))


def _is_blank_template_issue(issue: dict[str, str]) -> bool:
    issue_text = " ".join(
        str(issue.get(field, ""))
        for field in (
            "rule_id",
            "clause_title",
            "clause_position",
            "original_excerpt",
            "risk_type",
            "risk_message",
            "risk_analysis",
            "revision_suggestion",
        )
    )
    return _looks_like_blank_template_text(issue_text)


def _looks_like_blank_template_text(text: str) -> bool:
    compact = text.strip()
    if not compact:
        return False
    has_blank_signal = bool(BLANK_PLACEHOLDER_RE.search(compact)) or any(term in compact for term in BLANK_TEMPLATE_TERMS)
    has_field_signal = any(field in compact for field in BLANK_TEMPLATE_FIELDS)
    return has_blank_signal and has_field_signal


def _first_text(item: dict[str, Any], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        value = item.get(alias)
        if value is None:
            continue
        text = HTML_BREAK_RE.sub(" ", ESCAPED_LINEBREAK_RE.sub(" ", str(value))).strip()
        if text:
            return text
    return ""


def _default_risk_type(risk_level: str) -> str:
    if risk_level == "高":
        return "高争议风险"
    if risk_level == "低":
        return "合规但不优"
    return "中争议风险"


def _parse_issues_from_markdown(markdown: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    current_title = ""
    current_rule = ""
    current_rows: dict[str, str] = {}

    def flush() -> None:
        nonlocal current_rows, current_title, current_rule
        if not current_rows:
            return
        clause_position = current_rows.get("原文位置", current_rows.get("位置", ""))
        original_excerpt = current_rows.get("原文摘要", "")
        combined_location = current_rows.get("原文位置及摘要", "")
        if combined_location and (not clause_position or not original_excerpt):
            clause_position, original_excerpt = _split_combined_location_and_excerpt(combined_location)

        risk_message = current_rows.get("风险提示", "")
        risk_analysis = current_rows.get("风险分析", "")
        combined_risk_note = current_rows.get("风险说明", "")
        if combined_risk_note and not risk_message:
            risk_message = combined_risk_note
        if combined_risk_note and not risk_analysis:
            risk_analysis = combined_risk_note

        issue = {
            "rule_id": current_rule or current_rows.get("规则编号", "EXTENDED"),
            "clause_title": current_title or current_rows.get("条款标题", "风险条款"),
            "clause_position": clause_position or "未明确位置",
            "paragraph_id": "",
            "risk_level": current_rows.get("风险等级", "中").replace("风险", "").replace("🔴", "").replace("🟡", "").replace("🟢", "").strip() or "中",
            "risk_type": current_rows.get("风险类型", ""),
            "original_excerpt": original_excerpt,
            "risk_message": risk_message,
            "risk_analysis": risk_analysis,
            "revision_suggestion": current_rows.get("修改建议", ""),
            "revised_text_example": current_rows.get("修改后文本示例", ""),
            "comment_title": current_title or "风险提示",
            "comment_author": DEFAULT_COMMENT_AUTHOR,
        }
        issue["risk_type"] = issue["risk_type"] or _default_risk_type(issue["risk_level"])
        if _has_issue_signal(issue):
            issues.append(issue)
        current_rows = {}

    heading_re = re.compile(r"^####\s*\d*[.、]?\s*(?P<title>.+?)(?:（规则编号：(?P<rule>[^）]+)）)?\s*$")
    for line in markdown.splitlines():
        heading = heading_re.match(line.strip())
        if heading:
            flush()
            current_title = heading.group("title").strip()
            current_rule = (heading.group("rule") or "").strip()
            continue
        if line.startswith("|") and line.count("|") >= 3:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] not in {"---", "审查项", "项目"}:
                current_rows[cells[0]] = cells[1]
    flush()
    return issues


def _split_combined_location_and_excerpt(value: str) -> tuple[str, str]:
    text = value.strip()
    if not text:
        return "未明确位置", ""

    for separator in ("：", ":"):
        if separator in text:
            left, right = text.split(separator, 1)
            left = left.strip()
            right = right.strip()
            if left and right:
                return left, right

    return "未明确位置", text


def _dedupe_issues(issues: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()
    for issue in issues:
        key = (
            issue.get("rule_id", ""),
            issue.get("clause_title", ""),
            issue.get("clause_position", ""),
            issue.get("original_excerpt", ""),
            issue.get("risk_message", ""),
            issue.get("revision_suggestion", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped
