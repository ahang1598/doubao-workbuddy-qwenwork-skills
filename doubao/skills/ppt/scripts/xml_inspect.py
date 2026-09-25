#!/usr/bin/env python3
"""Inspect local Lark Slides XML.

Choose ``--mode summary|content|raw`` (default: summary).
Summary covers the full deck; content/raw support optional ``--slide-id`` selection.
All modes support ``--output`` files.
Content emits compact page text/data without speaker notes; summary/raw emit JSON.
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
    text = " | ".join(texts)
    note_text = element_text(note) if note is not None else ""
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
            "embeds": types.get("embed", 0),
        },
        "tag_counts": dict(types),
        "text_preview": preview(text),
        "text_preview_truncated": len(text) > PREVIEW_LENGTH,
        "note_preview": preview(note_text),
        "note_preview_truncated": len(note_text) > PREVIEW_LENGTH,
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
    if any(slide["text_preview_truncated"] for slide in inspected):
        warnings.append("页面文字预览有截断；请用 --mode content 读取完整页面内容，编辑对象前再读 raw XML")
    if any(slide["note_preview_truncated"] for slide in inspected):
        warnings.append("演讲者备注预览有截断；需要查看全文时请用 --mode raw，content 模式不包含演讲者备注")
    if any(set(slide["tag_counts"]) - {"shape", "img", "icon", "line", "polyline", "table", "chart"} for slide in inspected):
        warnings.append("计数只统计 <data> 直属对象；embed 或其它对象也可能承载图形，不能把 images/icons 为 0 当作没有图形")
    if duplicate_ids:
        warnings.append(f"XML 中存在重复 id：{duplicate_ids}")

    return {
        "schema_version": "1.0",
        "source_file": str(input_path),
        "mode": "summary",
        "usage_hints": {
            "content": "沿用同一 --input，用 --mode content 读取页面文字和数据（不含演讲者备注）；默认全稿，可加 --slide-id ID... 选页、--output content.txt 保存。",
            "raw": "沿用同一 --input，用 --mode raw 读取完整 XML；默认全稿，可加 --slide-id ID... 选页、--output raw.json 保存。XML 在 JSON 的 slides[].raw_xml 中，用于查看详细对象结构、布局和样式属性，以及精确编辑页面。",
        },
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


def select_slides(
    slides: list[Any], requested_ids: list[str]
) -> list[tuple[int, str | None, Any]]:
    if not requested_ids:
        return [(index, slide.get("id"), slide) for index, slide in enumerate(slides, 1)]
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
    selected = select_slides(slides, requested_ids)
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
        "mode": "raw",
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


def full_text(element: ET.Element) -> str:
    """Keep all XML text and internal spaces, separating paragraphs and breaks."""
    parts: list[str] = []

    def walk(node: ET.Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            if local_name(child.tag) == "p":
                parts.append("\n")
            walk(child)
            if local_name(child.tag) in {"p", "br"}:
                parts.append("\n")
            if child.tail:
                parts.append(child.tail)

    walk(element)
    return "\n".join(line.strip() for line in "".join(parts).splitlines() if line.strip())

def explicit_colors(element: ET.Element) -> list[dict[str, str]]:
    """Expose source colors, without guessing their meaning or inherited styles."""
    colors = []
    for node in element.iter():
        tag = local_name(node.tag)
        attrs = {key: value for key, value in node.attrib.items() if "color" in key.lower()}
        if tag == "color" and node.get("value") is not None:
            attrs["value"] = node.get("value")
        if attrs and (entry := {"tag": tag, **attrs}) not in colors:
            colors.append(entry)
    return colors


def quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def attributes(element: ET.Element) -> str:
    return " ".join(f"{local_name(key)}={quoted(value)}" for key, value in element.attrib.items())


def data_lines(element: ET.Element, path: str = "") -> list[str]:
    """Keep field names, attributes and CSV values without a verbose JSON tree."""
    tag = local_name(element.tag)
    path = f"{path}/{tag}" if path else tag
    text = (element.text or "").strip()
    lines = []
    if text or element.attrib:
        label = f"{path} {attributes(element)}".rstrip()
        lines.append(f"  {label}" + (f": {quoted(text)}" if text else ""))
    for child in element:
        # Readback repeats the CSV field text as parsed values; keep the original once.
        if not (tag == "chartField" and text and local_name(child.tag) == "chartParsedValues"):
            lines.extend(data_lines(child, path))
        if child.tail and child.tail.strip():
            lines.append(f"  {path} text: {quoted(child.tail.strip())}")
    return lines


def block_content_lines(block: ET.Element, namespace: str) -> list[str]:
    tag = local_name(block.tag)
    label = tag + (f" id={quoted(block.get('id'))}" if block.get("id") else "")
    if tag not in {"shape", "table", "chart"} and block.get("type"):
        label += f" type={quoted(block.get('type'))}"
    lines = [f"[{label}]"]
    if tag == "table":
        rows = block.findall(f"./{{{namespace}}}tr")
        for row_number, row in enumerate(rows, 1):
            for cell_number, cell in enumerate(row.findall(f"./{{{namespace}}}td"), 1):
                details = [f"{key}={quoted(value)}" for key, value in cell.attrib.items()
                           if key == "id" or "span" in key.lower()]
                for color in explicit_colors(cell):
                    details.extend(f"{color['tag']}.{key}={quoted(value)}"
                                   for key, value in color.items() if key != "tag")
                cell_label = f"r{row_number}c{cell_number}" + (" " + " ".join(details) if details else "")
                lines.append(f"  {cell_label}: {quoted(full_text(cell))}")
        if (not rows or any(not row.findall(f"./{{{namespace}}}td") for row in rows)
                or any(local_name(child.tag) not in {"tr", "colgroup"} for child in block)
                or any(local_name(child.tag) != "td" or namespace_of(child.tag) != namespace
                       for row in rows for child in row)):
            lines.append(f"  未完整展开表格，请读 raw XML；可读文字: {quoted(full_text(block))}")
    elif tag == "chart":
        datasets = block.findall(f"./{{{namespace}}}chartData")
        for dataset in datasets:
            lines.extend(data_lines(dataset))
        context_tags = {"chartTitle", "chartSubTitle", "chartLegend", "chartTooltip", "chartPlot", "chartSeries", "chartLabels", "chartAxis", "chartLabel"}
        style_attrs = {"color", "width", "height", "topLeftX", "topLeftY", "opacity"}
        for node in block.iter():
            if local_name(node.tag) in context_tags:
                attrs = " ".join(f"{key}={quoted(value)}" for key, value in node.attrib.items()
                                 if key not in style_attrs and not key.lower().startswith("font"))
                text = full_text(node) if local_name(node.tag) in {"chartTitle", "chartSubTitle", "chartLabel"} else (node.text or "").strip()
                if attrs or text:
                    label = f"{local_name(node.tag)} {attrs}".rstrip()
                    lines.append(f"  {label}" + (f": {quoted(text)}" if text else ""))
        if not datasets or any(local_name(child.tag) not in {"chartPlotArea", "chartData", "chartTitle", "chartSubTitle", "chartStyle", "chartLegend", "chartTooltip"} for child in block):
            lines.append(f"  未完整展开图表，请读 raw XML；可读文字: {quoted(full_text(block))}")
    else:
        # Embedded graphics can contain CSS/metadata; they are listed, not parsed as prose.
        if tag not in {"embed", "img", "icon"} and (text := full_text(block)):
            lines[0] += " " + quoted(text)
        if tag not in {"shape", "line", "polyline"}:
            lines[0] += " (未展开对象，请读 raw XML/截图)"
    return lines


def build_content(input_path: Path, requested_ids: list[str]) -> tuple[str, int, int]:
    _, _, namespace, slides = parse_document(input_path)
    selected = select_slides(slides, requested_ids)
    lines = ["# content：页面文字/数据不截断，不含演讲者备注；图片及嵌入对象未解析，样式不完整，修改时仍须读 raw XML。",
             "# 表格 r/c 表示 XML 行/格顺序，跨行跨列另标 span；字符串中的 \\n 表示原文换行。"]
    for index, slide_id, slide in selected:
        lines.extend(["", f"## slide {index} id={quoted(slide_id or '')}"])
        data = slide.find(f"./{{{namespace}}}data")
        for block in data if data is not None else []:
            lines.extend(block_content_lines(block, namespace))
    return "\n".join(lines) + "\n", len(slides), len(selected)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="--mode 选择输出模式（默认 summary）；summary 读取全稿，content/raw 可选页，三种模式均可保存输出"
    )
    parser.add_argument("--input", required=True, type=Path, help="slides +xml-get 保存的 XML 文件")
    parser.add_argument("--mode", choices=("summary", "content", "raw"), default="summary",
                        help="summary：摘要 JSON；content：页面文字/数据，不含演讲者备注；raw：含完整 XML 的 JSON")
    parser.add_argument("--output", type=Path, help="保存当前模式的输出；不传时写到标准输出")
    parser.add_argument(
        "--slide-id",
        action="extend",
        nargs="+",
        default=[],
        help="仅用于 content/raw 选页；省略时读取全部页；可传多个 ID 或重复使用该参数",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    requested_ids = list(dict.fromkeys(args.slide_id))
    try:
        if args.mode == "summary" and requested_ids:
            raise ValueError("summary 模式用于全稿摘要，不能与 --slide-id 同用；按页读取请用 --mode content 或 --mode raw")
        if args.mode == "content":
            rendered, total, count = build_content(args.input, requested_ids)
        else:
            if args.mode == "raw":
                report = build_raw_slides_lxml(args.input, requested_ids)
            else:
                root, root_name, namespace, slides = parse_document(args.input)
                report = build_summary(args.input, root, root_name, namespace, slides)
            rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            total = report["presentation"]["slide_count"]
            count = len(report["slides"])
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(json.dumps({"status": "ok", "mode": args.mode, "output": str(args.output),
                              "presentation_slide_count": total, "output_slide_count": count}, ensure_ascii=False))
        else:
            print(rendered, end="")
    except (ValueError, OSError) as error:
        print(f"xml_inspect: error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
