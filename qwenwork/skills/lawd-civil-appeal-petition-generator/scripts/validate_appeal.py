#!/usr/bin/env python3
"""民事上诉状轻量交付门禁；只做机械检查，不判断法律正确性。

退出码：0=通过；1=门禁拦截；2=输入错误。支持 md/txt/docx。
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
DATE_RE = re.compile(r"(?:20\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日|20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})")
COURT_RE = re.compile(r"[\u4e00-\u9fa5]{2,30}(?:人民法院|海事法院|知识产权法院|金融法院)")
CASE_NO_RE = re.compile(r"[（(]\s*\d{4}\s*[）)]\s*[^\s，,。；;]{1,30}?号")
AMOUNT_RE = re.compile(r"(?:人民币\s*|[￥¥]\s*)?([0-9][0-9,]*(?:\.\d+)?)\s*(万)?\s*元")


class InputError(Exception):
    pass


def load_text(path: Path) -> str:
    if not path.exists():
        raise InputError(f"文件不存在：{path}")
    if path.suffix.lower() in TEXT_SUFFIXES:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise InputError("文本编码无法识别，请转换为 UTF-8")
    if path.suffix.lower() != ".docx" or not zipfile.is_zipfile(path):
        raise InputError("仅支持 md/markdown/txt/合法 docx")
    parts: list[str] = []
    try:
        with zipfile.ZipFile(path) as package:
            for name in package.namelist():
                if name.startswith("word/") and name.endswith(".xml"):
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


def parse_amount(raw: str) -> Decimal:
    match = re.fullmatch(r"\s*(?:人民币\s*|[￥¥]\s*)?([0-9][0-9,]*(?:\.\d+)?)\s*(万)?\s*(?:元)?\s*", raw)
    if not match:
        raise InputError(f"无法识别金额参数：{raw}")
    value = Decimal(match.group(1).replace(",", ""))
    return value * (Decimal("10000") if match.group(2) else Decimal("1"))


def check(args: argparse.Namespace, text: str) -> list[str]:
    errors: list[str] = []
    dense = compact(text)
    required = [
        ("标题“民事上诉状”", r"民事上诉状"),
        ("上诉人信息", r"上诉人(?:（[^）]{0,20}）)?[：:]"),
        ("被上诉人信息", r"被上诉人(?:（[^）]{0,20}）)?[：:]"),
        ("上诉请求章节", r"上诉请求"),
        ("上诉理由章节", r"(?:事实\s*[与和]\s*理由|上诉理由)"),
        ("不服原审裁判的起因表述", r"不服[^。；;]{0,180}(?:判决|裁定)"),
        ("尾部“此致”", r"此\s*致"),
    ]
    for label, pattern in required:
        if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
            errors.append(f"缺少{label}")
    request = re.search(r"上诉请求(.*?)(?:事实\s*[与和]\s*理由|上诉理由)", text, re.DOTALL)
    if request and len(compact(request.group(1))) < 15:
        errors.append("上诉请求章节内容过短，疑似空壳")
    if not CASE_NO_RE.search(text):
        errors.append("缺少格式完整的一审案号")
    tail_start = text.rfind("此致")
    tail = text[tail_start:] if tail_start >= 0 else ""
    tail_dense = compact(tail)
    if tail:
        if not COURT_RE.search(tail_dense):
            errors.append("“此致”后缺少完整二审法院名称")
        if not re.search(r"上诉人(?:（[^）]{0,20}）)?[：:]", tail):
            errors.append("“此致”后缺少上诉人落款")
    if not DATE_RE.search(tail):
        errors.append("缺少完整落款日期")
    placeholders = sorted(set(match.group(0) for match in PLACEHOLDER_RE.finditer(text)))
    if placeholders:
        errors.append("仍含占位符：" + "、".join(placeholders[:8]))
    if re.search(r"【/?(?:居中|右对齐)】|</?(?:div|p|span)\b", text, re.IGNORECASE):
        errors.append("仍含排版标记或 HTML 标签")
    for role, values in (("上诉人", args.appellant), ("被上诉人", args.appellee)):
        for value in values:
            if compact(value) not in dense:
                errors.append(f"已确认的{role}名称未出现在成稿：{value}")
    for case_no in args.case_no:
        if compact(case_no) not in dense:
            errors.append(f"已确认的一审案号未出现在成稿：{case_no}")
    present_amounts = amounts(text)
    for raw in args.amount:
        if parse_amount(raw) not in present_amounts:
            errors.append(f"已确认金额未出现在成稿：{raw}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="民事上诉状轻量交付门禁（机械检查，不判断法律正确性）")
    parser.add_argument("file", type=Path, help="待检查的 md/txt/docx 文件")
    parser.add_argument("--appellant", action="append", default=[], help="已确认的上诉人名称；可重复")
    parser.add_argument("--appellee", action="append", default=[], help="已确认的被上诉人名称；可重复")
    parser.add_argument("--case-no", action="append", default=[], help="已确认的一审案号；可重复")
    parser.add_argument("--amount", action="append", default=[], help="必须与成稿一致的关键金额；可重复")
    args = parser.parse_args()
    try:
        errors = check(args, load_text(args.file))
    except InputError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("GATE FAILED：民事上诉状未通过机械检查", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("GATE PASSED：民事上诉状通过机械检查；不代表事实、法律或上诉策略正确。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
