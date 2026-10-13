#!/usr/bin/env python3
"""民事起诉状轻量交付门禁。

只检查文书结构、占位符及用户已确认的关键名称/金额是否落入成稿，不判断事实、
法律适用、诉讼策略或金额计算是否正确。

退出码：0=通过；1=门禁拦截；2=输入错误。
支持：.md / .markdown / .txt / .docx（DOCX 使用标准库读取，无额外依赖）。
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

PLACEHOLDER_RE = re.compile(
    r"待补充|待填写|待确认|待核实|TBD|TODO|X{2,}|x{2,}|×{2,}|_{3,}"
    r"|【[^】]{0,50}(?:待|假设|填写|补充|确认|核实)[^】]{0,50}】",
    re.IGNORECASE,
)
DATE_RE = re.compile(
    r"(?:20\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日|20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})"
)
COURT_RE = re.compile(r"[\u4e00-\u9fa5]{2,30}(?:人民法院|海事法院|知识产权法院|金融法院)")
AMOUNT_RE = re.compile(r"(?:人民币\s*|[￥¥]\s*)?([0-9][0-9,]*(?:\.\d+)?)\s*(万)?\s*元")


class InputError(Exception):
    pass


def load_text(path: Path) -> str:
    if not path.exists():
        raise InputError(f"文件不存在：{path}")
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise InputError("文本编码无法识别，请转换为 UTF-8")
    if suffix != ".docx":
        raise InputError("仅支持 md/markdown/txt/docx")
    if not zipfile.is_zipfile(path):
        raise InputError("文件不是合法 DOCX")
    parts: list[str] = []
    try:
        with zipfile.ZipFile(path) as package:
            names = [n for n in package.namelist() if n.startswith("word/") and n.endswith(".xml")]
            for name in names:
                root = ET.fromstring(package.read(name))
                for paragraph in root.iter(W + "p"):
                    line = "".join(node.text or "" for node in paragraph.iter(W + "t")).strip()
                    if line:
                        parts.append(line)
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise InputError(f"DOCX 读取失败：{exc}") from exc
    return "\n".join(parts)


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def amounts(text: str) -> set[Decimal]:
    found: set[Decimal] = set()
    for raw, unit in AMOUNT_RE.findall(text):
        try:
            value = Decimal(raw.replace(",", ""))
            found.add(value * (Decimal("10000") if unit else Decimal("1")))
        except InvalidOperation:
            continue
    return found


def parse_expected_amount(raw: str) -> Decimal:
    match = re.fullmatch(r"\s*(?:人民币\s*|[￥¥]\s*)?([0-9][0-9,]*(?:\.\d+)?)\s*(万)?\s*(?:元)?\s*", raw)
    if not match:
        raise InputError(f"无法识别金额参数：{raw}")
    value = Decimal(match.group(1).replace(",", ""))
    return value * (Decimal("10000") if match.group(2) else Decimal("1"))


def check(args: argparse.Namespace, text: str) -> list[str]:
    errors: list[str] = []
    dense = compact(text)

    required = [
        ("标题“民事起诉状”", r"民事起诉状"),
        ("原告信息", r"原告(?:（[^）]{0,20}）)?[：:]"),
        ("被告信息", r"被告(?:（[^）]{0,20}）)?[：:]"),
        ("诉讼请求章节", r"诉讼请求"),
        ("事实与理由章节", r"事实\s*[与和]\s*理由"),
        ("尾部“此致”", r"此\s*致"),
    ]
    for label, pattern in required:
        if not re.search(pattern, text, re.MULTILINE):
            errors.append(f"缺少{label}")

    request = re.search(r"诉讼请求(.*?)(?:事实\s*[与和]\s*理由)", text, re.DOTALL)
    if request and len(compact(request.group(1))) < 15:
        errors.append("诉讼请求章节内容过短，疑似空壳")
    tail_start = text.rfind("此致")
    tail = text[tail_start:] if tail_start >= 0 else ""
    tail_dense = compact(tail)
    if tail:
        if not COURT_RE.search(tail_dense):
            errors.append("“此致”后缺少完整法院名称")
        if not re.search(r"(?:具状人|原告)(?:（[^）]{0,20}）)?[：:]", tail):
            errors.append("“此致”后缺少原告/具状人落款")
    if not DATE_RE.search(tail):
        errors.append("缺少完整落款日期")

    placeholders = sorted(set(match.group(0) for match in PLACEHOLDER_RE.finditer(text)))
    if placeholders:
        errors.append("仍含占位符：" + "、".join(placeholders[:8]))
    if re.search(r"【/?(?:居中|右对齐)】|</?(?:div|p|span)\b", text, re.IGNORECASE):
        errors.append("仍含排版标记或 HTML 标签")

    for role, values in (("原告", args.plaintiff), ("被告", args.defendant)):
        for value in values:
            if compact(value) not in dense:
                errors.append(f"已确认的{role}名称未出现在成稿：{value}")
    present_amounts = amounts(text)
    for raw in args.amount:
        expected = parse_expected_amount(raw)
        if expected not in present_amounts:
            errors.append(f"已确认金额未出现在成稿：{raw}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="民事起诉状轻量交付门禁（机械检查，不判断法律正确性）")
    parser.add_argument("file", type=Path, help="待检查的 md/txt/docx 文件")
    parser.add_argument("--plaintiff", action="append", default=[], help="已确认的原告名称；多名可重复传入")
    parser.add_argument("--defendant", action="append", default=[], help="已确认的被告名称；多名可重复传入")
    parser.add_argument("--amount", action="append", default=[], help="必须与成稿一致的关键金额；可重复传入")
    args = parser.parse_args()
    try:
        errors = check(args, load_text(args.file))
    except InputError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("GATE FAILED：民事起诉状未通过机械检查", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("GATE PASSED：民事起诉状通过机械检查；不代表事实、法律或诉讼策略正确。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
