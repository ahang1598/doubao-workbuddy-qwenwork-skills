#!/usr/bin/env python3
"""Inspect local Lark Slides XML.

With no ``--slide-id``, emit a compact presentation summary. With one or more
``--slide-id`` arguments, emit those slides' complete raw XML for immediate use.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    from lxml import etree as LET
except ImportError:  # pragma: no cover - exercised only in stripped runtimes.
    LET = None


SML_NAMESPACE_SUFFIX = "/sml/2.0"
PREVIEW_LENGTH = 240


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def namespace_of(tag: str) -> str:
    if not tag.startswith("{") or "}" not in tag:
        return ""
    return tag[1:].split("}", 1)[0]


def normalize_text(parts: Iterable[str]) -> str:
    return " ".join("".join(parts).split())


def element_text(element: ET.Element) -> str:
    return normalize_text(element.itertext())


def preview(text: str | None) -> str | None:
    if not text:
        return None
    if len(text) <= PREVIEW_LENGTH:
        return text
    return text[: PREVIEW_LENGTH - 1].rstrip() + "…"


def parse_document(input_path: Path) -> tuple[ET.Element, str, str, list[ET.Element]]:
    try:
        root = ET.parse(input_path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ValueError(f"无法解析 XML：{error}") from error

    namespace = namespace_of(root.tag)
    if not namespace or not namespace.endswith(SML_NAMESPACE_SUFFIX):
        raise ValueError(
            "根元素没有有效的 SML 2.0 namespace；必须从 XML 根元素读取 namespace，"
            "不能自行猜测 http 或 https"
        )

    root_name = local_name(root.tag)
    if root_name == "presentation":
        slides = root.findall(f"./{{{namespace}}}slide")
    elif root_name == "slide":
        slides = [root]
    else:
        raise ValueError(f"不支持的根元素：{root_name!r}，预期 presentation 或 slide")
    if not slides:
        raise ValueError("XML 中没有找到根级 <slide>；请确认回读文件和 namespace 是否正确")
    return root, root_name, namespace, slides


def count_ids(root: ET.Element) -> Counter[str]:
    return Counter(element_id for item in root.iter() if (element_id := item.get("id")))


def inspect_slide(slide: ET.Element, index: int, namespace: str) -> dict[str, Any]:
    data = slide.find(f"./{{{namespace}}}data")
    blocks = list(data) if data is not None else []
    types = Counter(local_name(block.tag) for block in blocks)
    texts = [element_text(block) for block in blocks]
    texts = [text for text in texts if text]
    note = slide.find(f"./{{{namespace}}}note")
    return {
        "index": index,
        "slide_id": slide.get("id"),
        "counts": {
            "blocks": len(blocks),
            "text_blocks": len(texts),
            "images": types.get("img", 0),
            "shapes": types.get("shape", 0),
            "tables": types.get("table", 0),
            "charts": types.get("chart", 0),
            "icons": types.get("icon", 0),
            "lines": types.get("line", 0) + types.get("polyline", 0),
            "undefined": types.get("undefined", 0),
        },
        "text_preview": preview(" | ".join(texts)),
        "note_preview": preview(element_text(note) if note is not None else None),
    }


def presentation_info(
    root: ET.Element,
    root_name: str,
    namespace: str,
    slides: list[ET.Element],
) -> dict[str, Any]:
    title = root.find(f"./{{{namespace}}}title") if root_name == "presentation" else None
    return {
        "root": root_name,
        "namespace": namespace,
        "presentation_id": root.get("id") if root_name == "presentation" else None,
        "revision_id": root.get("revision_id") or root.get("revisionId"),
        "title": element_text(title) if title is not None else None,
        "width": root.get("width"),
        "height": root.get("height"),
        "slide_count": len(slides),
        "slide_ids": [slide.get("id") for slide in slides],
    }


def build_summary(
    input_path: Path,
    root: ET.Element,
    root_name: str,
    namespace: str,
    slides: list[ET.Element],
) -> dict[str, Any]:
    inspected = [inspect_slide(slide, index, namespace) for index, slide in enumerate(slides, 1)]
    total_counts: Counter[str] = Counter()
    for slide in inspected:
        total_counts.update(slide["counts"])

    warnings: list[str] = []
    missing_ids = [slide["index"] for slide in inspected if not slide["slide_id"]]
    empty_slides = [slide["index"] for slide in inspected if not slide["counts"]["blocks"]]
    undefined_slides = [slide["index"] for slide in inspected if slide["counts"]["undefined"]]
    duplicate_ids = sorted(item_id for item_id, count in count_ids(root).items() if count > 1)
    if missing_ids:
        warnings.append(f"以下页面缺少 slide_id：{missing_ids}")
    if empty_slides:
        warnings.append(f"以下页面的 <data> 中没有可见元素：{empty_slides}")
    if not any(slide["counts"]["text_blocks"] for slide in inspected):
        warnings.append(
            "全部页面均未提取到 XML 文字；这可能是图片化模板，也可能需要人工检查 XML 结构，"
            "不得仅凭该结果断言页面没有可见文字"
        )
    if undefined_slides:
        warnings.append(f"以下页面包含服务端导出的 <undefined> 元素：{undefined_slides}")
    if duplicate_ids:
        warnings.append(f"XML 中存在重复 id：{duplicate_ids}")

    return {
        "schema_version": "1.0",
        "source_file": str(input_path),
        "mode": "summary",
        "selection": {
            "slide_numbers": [],
            "slide_ids": [],
            "block_ids": [],
            "raw_xml": False,
            "output_slide_count": len(inspected),
        },
        "presentation": presentation_info(root, root_name, namespace, slides),
        "summary": {**dict(total_counts), "media_usage": None, "warnings": warnings},
        "slides": inspected,
        "selected_blocks": [],
    }


def lxml_namespace_of(tag: str) -> str:
    if not tag.startswith("{") or "}" not in tag:
        return ""
    return tag[1:].split("}", 1)[0]


def parse_raw_document(input_path: Path) -> tuple[Any, str, str, list[Any]]:
    if LET is None:
        raise ValueError("raw XML 模式需要 lxml；请安装 lxml ")
    try:
        parser = LET.XMLParser(remove_blank_text=False, recover=False)
        root = LET.parse(str(input_path), parser).getroot()
    except (OSError, LET.XMLSyntaxError) as error:
        raise ValueError(f"无法解析 XML：{error}") from error

    namespace = lxml_namespace_of(root.tag)
    if not namespace or not namespace.endswith(SML_NAMESPACE_SUFFIX):
        raise ValueError(
            "根元素没有有效的 SML 2.0 namespace；必须从 XML 根元素读取 namespace，"
            "不能自行猜测 http 或 https"
        )

    root_name = LET.QName(root).localname
    if root_name == "presentation":
        slides = root.xpath("./*[local-name()='slide']")
    elif root_name == "slide":
        slides = [root]
    else:
        raise ValueError(f"不支持的根元素：{root_name!r}，预期 presentation 或 slide")
    if not slides:
        raise ValueError("XML 中没有找到根级 <slide>；请确认回读文件和 namespace 是否正确")
    return root, root_name, namespace, slides


def select_raw_slides(
    slides: list[Any], requested_ids: list[str]
) -> list[tuple[int, str, Any]]:
    matches: dict[str, list[tuple[int, Any]]] = {slide_id: [] for slide_id in requested_ids}
    for index, slide in enumerate(slides, 1):
        if (slide_id := slide.get("id")) in matches:
            matches[slide_id].append((index, slide))

    missing = [slide_id for slide_id in requested_ids if not matches[slide_id]]
    ambiguous = {
        slide_id: [index for index, _ in items]
        for slide_id, items in matches.items()
        if len(items) > 1
    }
    if missing:
        raise ValueError(f"没有找到以下 slide_id：{missing}")
    if ambiguous:
        raise ValueError(f"以下 slide_id 在 XML 中重复，无法唯一定位：{ambiguous}")

    return [
        (matches[slide_id][0][0], slide_id, matches[slide_id][0][1])
        for slide_id in requested_ids
    ]


def build_raw_slides_lxml(input_path: Path, requested_ids: list[str]) -> dict[str, Any]:
    root, root_name, namespace, slides = parse_raw_document(input_path)
    selected = select_raw_slides(slides, requested_ids)
    entries = []
    for index, slide_id, slide in selected:
        entries.append(
            {
                "index": index,
                "slide_id": slide_id,
                "raw_xml": LET.tostring(slide, encoding="unicode"),
            }
        )
    return {
        "schema_version": "1.0",
        "source_file": str(input_path),
        "mode": "raw_xml",
        "selection": {
            "slide_numbers": [],
            "slide_ids": requested_ids,
            "block_ids": [],
            "raw_xml": True,
            "output_slide_count": len(entries),
        },
        "presentation": {
            "root": root_name,
            "namespace": namespace,
            "presentation_id": root.get("id") if root_name == "presentation" else None,
            "revision_id": root.get("revision_id") or root.get("revisionId"),
            "title": None,
            "width": root.get("width"),
            "height": root.get("height"),
            "slide_count": len(slides),
            "slide_ids": [slide.get("id") for slide in slides],
        },
        "slides": entries,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="不传 --slide-id 时输出摘要；传入后直接返回指定页面的完整 raw XML"
    )
    parser.add_argument("--input", required=True, type=Path, help="slides +xml-get 保存的 XML 文件")
    parser.add_argument("--output", type=Path, help="摘要模式的 JSON 输出文件；不传时写到标准输出")
    parser.add_argument(
        "--slide-id",
        action="extend",
        nargs="+",
        default=[],
        help="返回指定页面的完整 raw XML；一次传多个值或重复使用该参数均可",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    requested_ids = list(dict.fromkeys(args.slide_id))
    try:
        if requested_ids and args.output:
            raise ValueError("raw XML 模式直接写到标准输出，不使用 --output")
        if requested_ids:
            report = build_raw_slides_lxml(args.input, requested_ids)
        else:
            root, root_name, namespace, slides = parse_document(args.input)
            report = build_summary(args.input, root, root_name, namespace, slides)
    except (ValueError, OSError) as error:
        print(f"xml_inspect: error: {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "ok",
                    "mode": report["mode"],
                    "output": str(args.output),
                    "presentation_slide_count": report["presentation"]["slide_count"],
                    "output_slide_count": len(report["slides"]),
                },
                ensure_ascii=False,
            )
        )
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
