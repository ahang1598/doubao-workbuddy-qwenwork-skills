#!/usr/bin/env python3
"""Validate lecture-note, pre-class, and visual-OCR Markdown artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ARTIFACT_RULES = {
    "postclass": {
        "title": re.compile(r"(?m)^#\s+课程笔记｜.+"),
        "title_hint": "# 课程笔记｜课程｜主题",
        "headings": [
            "## 课程信息",
            "## 一、核心结论",
            "## 二、知识结构",
            "## 三、详细笔记",
            "## 六、课堂任务与 DDL",
            "## 七、待核对与疑问",
            "## 八、复习与主动回忆",
        ],
        "min_length": 800,
    },
    "preclass": {
        "title": re.compile(r"(?m)^#\s+课前预习卡｜.+"),
        "title_hint": "# 课前预习卡｜课程｜主题",
        "headings": [
            "## 预习依据与置信度",
            "## 本次预习目标",
            "## 必备前置知识",
            "## 概念地图",
            "## 预习重点与难点",
            "## 带着这些问题上课",
            "## 15 分钟预习安排",
            "## 课前诊断",
            "## 待确认与补充材料",
        ],
        "min_length": 500,
    },
    "visual": {
        "title": re.compile(r"(?m)^#\s+视觉识别稿｜.+"),
        "title_hint": "# 视觉识别稿｜课程或主题",
        "headings": [
            "## 材料与页面",
            "## 分区转写",
            "## 公式、图表与版式",
            "## 待核对",
            "## 识别审计",
        ],
        "min_length": 300,
    },
}

PLACEHOLDER_PATTERNS = [
    re.compile(r"\b(?:TODO|TBD|FIXME)\b", re.IGNORECASE),
    re.compile(r"<课程名称>|<本讲主题>|<下一讲主题>|<课程或主题>|<知识点>"),
    re.compile(r"\[待填写\]"),
]

POSTCLASS_SOURCE_PATTERN = re.compile(
    r"\[(?:课件|录音|截图|图片|扫描页|板书|手写笔记|用户补充|外部补充|教材|课程大纲|推断|待核对)[^\]]*\]"
)
PRECLASS_SOURCE_PATTERN = re.compile(r"\[(?:课程材料|外部补充|推断|待确认)\]")
VISUAL_LOCATION_PATTERN = re.compile(
    r"\[(?:截图|图片|扫描页|板书|手写笔记|课件)\s*[^\]]*(?:-R\d+)?\]"
)
VISUAL_STATUS_PATTERN = re.compile(r"\[(?:已确认|待核对|无法辨认)\]")
QUESTION_PATTERN = re.compile(r"(?m)^\s*\d+[\.、]\s*.+[？?]\s*$")
NUMBERED_ITEM_PATTERN = re.compile(r"(?m)^\s*\d+[\.、]\s*\S.+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a lecture-learning Markdown artifact."
    )
    parser.add_argument("--note", required=True, help="Path to the Markdown artifact")
    parser.add_argument(
        "--artifact",
        choices=sorted(ARTIFACT_RULES),
        default="postclass",
        help="Artifact contract to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require stronger source, question, and audit coverage",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit a machine-readable JSON report"
    )
    return parser.parse_args()


def section_text(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    body_start = start + len(heading)
    next_heading = re.search(r"(?m)^##\s+", text[body_start:])
    end = body_start + next_heading.start() if next_heading else len(text)
    return text[body_start:end].strip()


def validate_common(text: str, artifact: str, strict: bool) -> tuple[list[str], list[str]]:
    rules = ARTIFACT_RULES[artifact]
    errors: list[str] = []
    warnings: list[str] = []

    if not rules["title"].search(text):
        errors.append(f"缺少形如“{rules['title_hint']}”的主标题")

    for heading in rules["headings"]:
        if heading not in text:
            errors.append(f"缺少必需标题：{heading}")
        elif not section_text(text, heading):
            errors.append(f"必需章节为空：{heading}")

    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(text):
            errors.append(f"存在未清理占位符：{pattern.pattern}")

    minimum = int(rules["min_length"])
    if strict and len(text.strip()) < minimum:
        errors.append(f"严格模式下正文少于 {minimum} 字符，可能未覆盖完整闭环")
    elif len(text.strip()) < max(200, minimum // 2):
        warnings.append("正文较短，请确认没有过度压缩")

    return errors, warnings


def validate(text: str, strict: bool, artifact: str = "postclass") -> dict[str, object]:
    if artifact not in ARTIFACT_RULES:
        raise ValueError(f"unsupported artifact: {artifact}")

    errors, warnings = validate_common(text, artifact, strict)
    metrics: dict[str, int | str | bool] = {
        "character_count": len(text.strip()),
    }

    if artifact == "postclass":
        source_count = len(POSTCLASS_SOURCE_PATTERN.findall(text))
        recall_section = section_text(text, "## 八、复习与主动回忆")
        review_count = len(NUMBERED_ITEM_PATTERN.findall(recall_section))
        if source_count == 0:
            errors.append("没有检测到来源、推断或待核对标记")
        elif strict and source_count < 3:
            errors.append("严格模式至少需要 3 个来源/不确定性标记")
        if strict and review_count < 3:
            errors.append("严格模式至少需要 3 条复习任务或主动回忆题")
        if "本次材料未明确" not in text and "截止" not in text and "DDL" in text:
            warnings.append("课堂任务与 DDL 章节应明确任务，或写明材料未提供")
        metrics.update(source_marker_count=source_count, numbered_review_item_count=review_count)

    elif artifact == "preclass":
        source_count = len(PRECLASS_SOURCE_PATTERN.findall(text))
        question_count = len(QUESTION_PATTERN.findall(section_text(text, "## 带着这些问题上课")))
        plan_count = len(NUMBERED_ITEM_PATTERN.findall(section_text(text, "## 15 分钟预习安排")))
        level_match = re.search(r"材料等级\s*[：:]\s*([ABC])\b", text)
        if not level_match:
            errors.append("没有检测到 A/B/C 材料等级")
        if source_count == 0:
            errors.append("没有区分课程材料、外部补充、推断或待确认")
        elif strict and source_count < 2:
            errors.append("严格模式至少需要 2 个预习来源层级标记")
        if strict and question_count < 3:
            errors.append("严格模式至少需要 3 个可在课堂验证的问题")
        if strict and plan_count < 3:
            errors.append("严格模式的 15 分钟计划至少需要 3 个步骤")
        metrics.update(
            source_marker_count=source_count,
            question_count=question_count,
            plan_item_count=plan_count,
            material_level=level_match.group(1) if level_match else "",
        )

    else:
        location_count = len(VISUAL_LOCATION_PATTERN.findall(text))
        status_count = len(VISUAL_STATUS_PATTERN.findall(text))
        audit_text = section_text(text, "## 识别审计")
        if location_count == 0:
            errors.append("没有检测到图片/页面/区域定位标记")
        elif strict and location_count < 2:
            errors.append("严格模式至少需要 2 个视觉定位标记")
        if status_count == 0:
            errors.append("没有检测到已确认、待核对或无法辨认状态")
        elif strict and status_count < 2:
            errors.append("严格模式至少需要 2 个视觉识别状态标记")
        if strict and not re.search(r"复核|无法辨认|交叉来源", audit_text):
            errors.append("识别审计未记录复核、无法辨认或交叉来源")
        metrics.update(location_marker_count=location_count, status_marker_count=status_count)

    return {
        "ok": not errors,
        "artifact": artifact,
        "strict": strict,
        **metrics,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    args = parse_args()
    note_path = Path(args.note)
    if not note_path.is_file():
        print(f"ERROR: file not found: {note_path}", file=sys.stderr)
        return 2

    try:
        text = note_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print("ERROR: note must be UTF-8 encoded", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: cannot read note: {exc}", file=sys.stderr)
        return 2

    report = validate(text, args.strict, args.artifact)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("PASS" if report["ok"] else "FAIL")
        for error in report["errors"]:
            print(f"ERROR: {error}")
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
        print(f"SUMMARY: artifact={args.artifact} characters={report['character_count']}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
