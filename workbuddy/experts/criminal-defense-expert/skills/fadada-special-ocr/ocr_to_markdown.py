#!/usr/bin/env python3
"""
将 OCR 结果确定性写入 Markdown。

职责：
1. 调用内部 OCR API 获取 full_text_raw
2. 生成 full_text_cleaned 和 full_text_formatted
3. 在写文件时生成真实时间戳文件名
4. 将 Markdown 写入输出目录并返回真实绝对路径

默认只输出紧凑 JSON 摘要，避免超长文本挤占上下文。
可通过命令行参数选择额外输出 sidecar JSON 或完整文本。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 确保同目录下的 parse_contract_file.py 可以被找到（Windows 兼容）
sys.path.insert(0, str(Path(__file__).parent))

from parse_contract_file import get_file_type, parse_file
from split_ocr_input import DEFAULT_MAX_BYTES, split_ocr_input


CHINESE_NUMERALS = "零〇一二三四五六七八九十百千万两0123456789"
CHAPTER_RE = re.compile(rf"^第[{CHINESE_NUMERALS}]+章.*$")
SECTION_RE = re.compile(rf"^第[{CHINESE_NUMERALS}]+节.*$")
ARTICLE_RE = re.compile(rf"^(第[{CHINESE_NUMERALS}]+条)(.*)$")
CHINESE_LIST_RE = re.compile(rf"^(?:[{CHINESE_NUMERALS}]+、|（[{CHINESE_NUMERALS}]+）).*$")
DIGIT_LIST_RE = re.compile(r"^(?:\d+[.)、]|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]).*$")
PAGE_FOOTER_RE = re.compile(r"^第\s*\d+\s*页(?:\s*共\s*\d+\s*页)?$")
TRAILING_PUNCTUATION_RE = re.compile(r"[。！？!?；;：:]$")
SIGNATURE_LABELS = (
    "甲方",
    "乙方",
    "丙方",
    "丁方",
    "申请人",
    "被申请人",
    "原告",
    "被告",
    "法定代表人",
    "负责人",
    "委托代理人",
    "授权代表",
    "联系人",
    "联系电话",
    "联系地址",
    "地址",
    "签署日期",
    "签订日期",
    "日期",
    "盖章",
    "签字",
)
SIGNATURE_RE = re.compile(
    rf"^({'|'.join(re.escape(label) for label in SIGNATURE_LABELS)})\s*([：:])\s*(.*)$"
)
UNCERTAIN_TAG_RE = re.compile(r"【识别不确定：([^】]+)】")
INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
MULTI_BLANK_RE = re.compile(r"\n{3,}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="调用 OCR 并生成 Markdown 文件")
    parser.add_argument("files", nargs="+", help="待识别的 PDF 或图片文件路径")
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Markdown 输出目录，默认当前工作目录",
    )
    parser.add_argument(
        "--write-sidecar",
        action="store_true",
        help="同时写出 .ocr.json sidecar 文件",
    )
    parser.add_argument(
        "--include-texts",
        action="store_true",
        help="在 stdout JSON 中包含 full_text_* 字段",
    )
    return parser


def sanitize_stem(file_name: str) -> str:
    stem = Path(file_name).stem
    stem = INVALID_FILENAME_CHARS_RE.sub("_", stem)
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    return stem or "ocr_output"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "")
    return text


def collapse_blank_lines(text: str) -> str:
    text = MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip("\n")


def source_kind_for_path(file_path: str) -> str:
    return "pdf" if Path(file_path).suffix.lower() == ".pdf" else "image"


def is_signature_line(line: str) -> bool:
    return SIGNATURE_RE.match(line) is not None


def is_structural_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return any(
        (
            CHAPTER_RE.match(stripped),
            SECTION_RE.match(stripped),
            ARTICLE_RE.match(stripped),
            CHINESE_LIST_RE.match(stripped),
            DIGIT_LIST_RE.match(stripped),
            is_signature_line(stripped),
            PAGE_FOOTER_RE.match(stripped),
        )
    )


def join_fragments(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    if left[-1].isascii() and left[-1].isalnum() and right[0].isascii() and right[0].isalnum():
        return f"{left} {right}"
    return f"{left}{right}"


def should_merge_lines(previous: str, current: str) -> bool:
    if not previous or not current:
        return False
    if is_structural_line(previous) or is_structural_line(current):
        return False
    if TRAILING_PUNCTUATION_RE.search(previous):
        return False
    if len(previous) <= 2 or len(current) <= 1:
        return False
    return True


def clean_text(raw_text: str) -> str:
    lines = normalize_text(raw_text).split("\n")
    cleaned_lines: list[str] = []
    buffer = ""

    def flush_buffer() -> None:
        nonlocal buffer
        if buffer:
            cleaned_lines.append(buffer.strip())
            buffer = ""

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if PAGE_FOOTER_RE.match(stripped):
            continue

        if not stripped:
            flush_buffer()
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue

        if buffer and should_merge_lines(buffer, stripped):
            buffer = join_fragments(buffer, stripped)
        else:
            flush_buffer()
            buffer = stripped

    flush_buffer()
    return collapse_blank_lines("\n".join(cleaned_lines))


def format_signature_line(line: str) -> str:
    match = SIGNATURE_RE.match(line)
    if not match:
        return line

    key, colon, value = match.groups()
    if value:
        return f"**{key}**{colon} {value}"
    return f"**{key}**{colon}"


def remove_blank_lines_between_list_items(lines: list[str]) -> list[str]:
    compacted: list[str] = []

    def is_list_line(value: str) -> bool:
        stripped = value.strip()
        return stripped.startswith("- ") or DIGIT_LIST_RE.match(stripped) is not None

    for index, line in enumerate(lines):
        if line != "":
            compacted.append(line)
            continue

        prev_line = compacted[-1] if compacted else ""
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if is_list_line(prev_line) and is_list_line(next_line):
            continue
        if compacted and compacted[-1] == "":
            continue
        compacted.append("")

    while compacted and compacted[-1] == "":
        compacted.pop()
    return compacted


def format_markdown_text(cleaned_text: str) -> str:
    formatted_lines: list[str] = []

    for raw_line in cleaned_text.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            formatted_lines.append("")
            continue

        if CHAPTER_RE.match(stripped):
            formatted_lines.append(f"## {stripped}")
            continue

        if SECTION_RE.match(stripped):
            formatted_lines.append(f"### {stripped}")
            continue

        article_match = ARTICLE_RE.match(stripped)
        if article_match:
            article_no, remainder = article_match.groups()
            remainder = remainder.strip()
            formatted_lines.append(
                f"**{article_no}** {remainder}".rstrip() if remainder else f"**{article_no}**"
            )
            continue

        if CHINESE_LIST_RE.match(stripped):
            formatted_lines.append(f"- {stripped}")
            continue

        if DIGIT_LIST_RE.match(stripped):
            formatted_lines.append(stripped)
            continue

        if is_signature_line(stripped):
            formatted_lines.append(format_signature_line(stripped))
            continue

        formatted_lines.append(stripped)

    compacted = remove_blank_lines_between_list_items(formatted_lines)
    return collapse_blank_lines("\n".join(compacted))


def detect_global_warnings(raw_text: str) -> list[str]:
    warnings: list[str] = []
    if not raw_text.strip():
        warnings.append("识别结果为空")

    seen_uncertain = set()
    for match in UNCERTAIN_TAG_RE.finditer(raw_text):
        value = f"识别不确定：{match.group(1).strip()}"
        if value not in seen_uncertain:
            seen_uncertain.add(value)
            warnings.append(value)

    return warnings


def build_markdown(source_file: str, source_kind: str, generated_at: datetime, formatted_text: str, warnings: list[str]) -> str:
    lines = [
        f"# {sanitize_stem(source_file)}",
        "",
        f"- **来源文件**：{source_file}",
        f"- **识别时间**：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **材料类型**：{source_kind}",
        "",
        "---",
        "",
        formatted_text,
    ]

    if warnings:
        lines.extend(["", "---", "", "## 识别警告", ""])
        lines.extend([f"- {warning}" for warning in warnings])

    return "\n".join(lines).rstrip() + "\n"


def build_output_path(output_dir: Path, source_file: str, generated_at: datetime) -> Path:
    stem = sanitize_stem(source_file)
    timestamp = generated_at.strftime("%y%m%d_%H%M%S")
    base_name = f"{stem}_{timestamp}"
    candidate = output_dir / f"{base_name}.md"
    index = 1

    while candidate.exists():
        candidate = output_dir / f"{base_name}_{index:02d}.md"
        index += 1

    return candidate


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def extract_api_payload(parse_result: dict) -> tuple[str, str]:
    if not parse_result.get("success"):
        raise ValueError(parse_result.get("error") or "OCR 请求失败")

    payload = parse_result.get("data")
    if not isinstance(payload, dict):
        raise ValueError("OCR 响应缺少 data 对象")

    if payload.get("success") is not True or payload.get("code") != "000000":
        message = payload.get("message") or "OCR 接口返回失败"
        raise ValueError(str(message))

    data_items = payload.get("data")
    if not isinstance(data_items, list) or not data_items:
        raise ValueError("OCR 响应缺少识别结果")

    item = data_items[0]
    if not isinstance(item, dict):
        raise ValueError("OCR 识别结果格式异常")

    source_file = str(item.get("fileName") or "")
    full_text_raw = str(item.get("content") or "")
    if not source_file:
        raise ValueError("OCR 响应缺少 fileName")

    return source_file, full_text_raw


def maybe_write_sidecar(
    markdown_path: Path,
    payload: dict,
) -> Path:
    sidecar_path = markdown_path.with_suffix(".ocr.json")
    write_text_atomic(sidecar_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return sidecar_path


def process_file(file_path: str, output_dir: Path, write_sidecar: bool, include_texts: bool) -> dict:
    absolute_input = str(Path(file_path).expanduser().resolve())
    input_path = Path(absolute_input)
    output_dir.mkdir(parents=True, exist_ok=True)
    split_applied = input_path.stat().st_size > DEFAULT_MAX_BYTES
    part_receipts = []

    if split_applied:
        with tempfile.TemporaryDirectory(prefix="ocr-parts-", dir=output_dir) as temporary:
            split_result = split_ocr_input(input_path, Path(temporary), DEFAULT_MAX_BYTES)
            if split_result.get("status") != "PASS":
                raise ValueError(split_result.get("message") or "OCR 大文件拆分失败")
            page_texts = []
            for part in split_result["parts"]:
                parse_result = parse_file(part["path"])
                _, page_text = extract_api_payload(parse_result)
                page_number = part["page_number"]
                page_texts.append(f"【第 {page_number} 页】\n{page_text}")
                part_receipts.append({
                    "page_number": page_number,
                    "bytes": part["bytes"],
                    "success": True,
                })
            source_file = input_path.name
            full_text_raw = "\n\n".join(page_texts)
    else:
        parse_result = parse_file(absolute_input)
        source_file, full_text_raw = extract_api_payload(parse_result)

    full_text_cleaned = clean_text(full_text_raw)
    full_text_formatted = format_markdown_text(full_text_cleaned)
    global_warnings = detect_global_warnings(full_text_raw)
    generated_at = datetime.now().astimezone()
    source_kind = source_kind_for_path(absolute_input)

    markdown_path = build_output_path(output_dir, source_file, generated_at)
    markdown_text = build_markdown(
        source_file=source_file,
        source_kind=source_kind,
        generated_at=generated_at,
        formatted_text=full_text_formatted,
        warnings=global_warnings,
    )
    write_text_atomic(markdown_path, markdown_text)

    result = {
        "success": True,
        "input_file": absolute_input,
        "source_file": source_file,
        "source_kind": source_kind,
        "generated_at": generated_at.isoformat(),
        "output_file": str(markdown_path.resolve()),
        "global_warnings": global_warnings,
        "raw_chars": len(full_text_raw),
        "cleaned_chars": len(full_text_cleaned),
        "formatted_chars": len(full_text_formatted),
        "material_type": get_file_type(absolute_input),
        "split_applied": split_applied,
        "part_count": len(part_receipts) if split_applied else 1,
    }
    if part_receipts:
        result["part_receipts"] = part_receipts

    sidecar_payload = {
        "doc_type": "scanned_ocr",
        "source_kind": source_kind,
        "source_file": source_file,
        "generated_at": generated_at.isoformat(),
        "full_text_raw": full_text_raw,
        "full_text_cleaned": full_text_cleaned,
        "full_text_formatted": full_text_formatted,
        "global_warnings": global_warnings,
        "output_file": str(markdown_path.resolve()),
        "split_applied": split_applied,
        "part_receipts": part_receipts,
    }

    if write_sidecar:
        sidecar_path = maybe_write_sidecar(markdown_path, sidecar_payload)
        result["sidecar_file"] = str(sidecar_path.resolve())

    if include_texts:
        result.update(
            {
                "full_text_raw": full_text_raw,
                "full_text_cleaned": full_text_cleaned,
                "full_text_formatted": full_text_formatted,
            }
        )

    return result


def build_error_result(file_path: str, error: Exception) -> dict:
    return {
        "success": False,
        "input_file": str(Path(file_path).expanduser().resolve()),
        "error": str(error),
    }


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not os.environ.get("RICHEEAI_TOKEN"):
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "未找到认证 Token。请确保在 RicheeAI cowork 会话中运行此脚本。",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)

    output_dir = Path(args.output_dir).expanduser().resolve()

    results = []
    all_success = True
    for file_path in args.files:
        try:
            result = process_file(
                file_path=file_path,
                output_dir=output_dir,
                write_sidecar=args.write_sidecar,
                include_texts=args.include_texts,
            )
        except Exception as error:  # noqa: BLE001
            result = build_error_result(file_path, error)
            all_success = False
        results.append(result)

    payload = {
        "success": all_success,
        "total": len(results),
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not all_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
