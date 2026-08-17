#!/usr/bin/env python3
"""强制执行申请书轻量交付门禁；不计算利息，也不判断法律正确性。

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
TOTAL_RE = re.compile(
    r"(?:执行标的总额|申请执行总额|申请执行金额|请求执行金额|执行请求总额)\s*[：:]?\s*"
    r"(?:人民币\s*|[￥¥]\s*)?([0-9][0-9,]*(?:\.\d+)?)\s*(万)?\s*元"
)


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


def to_amount(raw: str, unit: str = "") -> Decimal:
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation as exc:
        raise InputError(f"无法识别金额参数：{raw}") from exc
    return value * (Decimal("10000") if unit else Decimal("1"))


def parse_amount(raw: str) -> Decimal:
    match = re.fullmatch(r"\s*(?:人民币\s*|[￥¥]\s*)?([0-9][0-9,]*(?:\.\d+)?)\s*(万)?\s*(?:元)?\s*", raw)
    if not match:
        raise InputError(f"无法识别金额参数：{raw}")
    return to_amount(match.group(1), match.group(2))


def check(args: argparse.Namespace, text: str) -> list[str]:
    errors: list[str] = []
    dense = compact(text)
    required = [
        ("标题“强制执行申请书”", r"强制执行申请书"),
        ("申请执行人信息", r"申请执行人[：:]"),
        ("被执行人信息", r"被执行人[：:]"),
        ("执行请求/申请事项章节", r"(?:执行请求|申请事项|请求事项)"),
        ("事实与理由章节", r"事实\s*[与和]\s*理由"),
        ("执行依据类型", r"(?:判决书|民事判决|裁定书|民事裁定|调解书|仲裁裁决书|公证债权文书|支付令)"),
        ("尾部“此致”", r"此\s*致"),
        ("附件/附项", r"(?:附件(?:清单)?|附[：:])"),
        ("AI辅助与非法律意见声明", r"(?:AI\s*辅助生成|人工智能辅助生成)[\s\S]{0,160}(?:不构成正式法律意见|金额计算仅供参考)"),
    ]
    for label, pattern in required:
        if not re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE):
            errors.append(f"缺少{label}")
    request = re.search(r"(?:执行请求|申请事项|请求事项)(.*?)(?:事实\s*[与和]\s*理由)", text, re.DOTALL)
    if request and len(compact(request.group(1))) < 20:
        errors.append("执行请求章节内容过短，疑似空壳")
    if not CASE_NO_RE.search(text):
        errors.append("缺少格式完整的执行依据案号")
    tail_start = text.rfind("此致")
    tail = text[tail_start:] if tail_start >= 0 else ""
    tail_dense = compact(tail)
    if tail:
        if not COURT_RE.search(tail_dense):
            errors.append("“此致”后缺少完整执行法院名称")
        if not re.search(r"申请执行人(?:（[^）]{0,20}）)?[：:]", tail):
            errors.append("“此致”后缺少申请执行人落款")
    if not DATE_RE.search(tail):
        errors.append("缺少完整落款日期")
    placeholders = sorted(set(match.group(0) for match in PLACEHOLDER_RE.finditer(text)))
    if placeholders:
        errors.append("仍含占位符：" + "、".join(placeholders[:8]))

    for role, values in (("申请执行人", args.applicant), ("被执行人", args.respondent)):
        for value in values:
            if compact(value) not in dense:
                errors.append(f"已确认的{role}名称未出现在成稿：{value}")
    for case_no in args.case_no:
        if compact(case_no) not in dense:
            errors.append(f"已确认的执行依据案号未出现在成稿：{case_no}")

    present_amounts = {to_amount(raw, unit) for raw, unit in AMOUNT_RE.findall(text)}
    for raw in args.amount:
        if parse_amount(raw) not in present_amounts:
            errors.append(f"已确认金额未出现在成稿：{raw}")
    labelled_totals = {to_amount(raw, unit) for raw, unit in TOTAL_RE.findall(text)}
    if len(labelled_totals) > 1:
        values = "、".join(str(value) + "元" for value in sorted(labelled_totals))
        errors.append(f"执行总额前后不一致：{values}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="强制执行申请书轻量交付门禁（不计算利息，不判断法律正确性）")
    parser.add_argument("file", type=Path, help="待检查的 md/txt/docx 文件")
    parser.add_argument("--applicant", action="append", default=[], help="已确认的申请执行人名称；可重复")
    parser.add_argument("--respondent", action="append", default=[], help="已确认的被执行人名称；可重复")
    parser.add_argument("--case-no", action="append", default=[], help="已确认的执行依据案号；可重复")
    parser.add_argument("--amount", action="append", default=[], help="必须与成稿一致的关键金额；可重复")
    args = parser.parse_args()
    try:
        errors = check(args, load_text(args.file))
    except InputError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("GATE FAILED：强制执行申请书未通过机械检查", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("GATE PASSED：强制执行申请书通过机械检查；不代表事实、法律、金额或利息计算正确。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
