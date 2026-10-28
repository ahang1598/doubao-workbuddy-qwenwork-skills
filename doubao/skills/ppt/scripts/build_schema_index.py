# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
"""Compile the Slides XML XSD into a flat, grep-friendly schema index.

Why this exists
---------------
`slides_xml_schema_definition.xml` is hard to grep: the words a model reaches for
(中文意图词、枚举值) rarely match the English attribute names, inherited
attributes live on base types elsewhere in the file, and a hit returns raw XML
rather than usable semantics. This script摊平 the XSD —— expanding inheritance,
inlining enums/constraints, attaching Chinese aliases and the runtime-only
constraints the XSD cannot express —— into one Markdown document that a plain
`grep` lands on first try and shows in a single screen.

Usage
-----
    python3 scripts/build_schema_index.py            # regenerate the index
    python3 scripts/build_schema_index.py --check     # fail if index is stale (CI)

The committed output is `references/xml/slides_xml_schema_index.md`.
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


XS_NS = "http://www.w3.org/2001/XMLSchema"
XS = f"{{{XS_NS}}}"

SCRIPTS_DIR = Path(__file__).resolve().parent
XML_DIR = SCRIPTS_DIR.parent / "references" / "xml"
DEFAULT_SCHEMA = XML_DIR / "slides_xml_schema_definition.xml"
DEFAULT_OUTPUT = XML_DIR / "slides_xml_schema_index.md"

BUILTIN_CONSTRAINTS = {
    "boolean": "布尔值：true / false / 1 / 0",
    "decimal": "十进制数",
    "double": "浮点数",
    "integer": "整数",
    "nonNegativeInteger": "非负整数（>= 0）",
    "positiveInteger": "正整数（> 0）",
    "string": "字符串",
    "anyURI": "URI 字符串",
}

# 中文意图词 / 同义词 → 真实元素或属性名。写进索引的每个元素行里，让 grep
# 中文也能命中。只收录"写出来会被查"的词，避免噪音。
INTENT_ALIASES = {
    "shape": ("形状", "文本框", "矩形", "圆角矩形"),
    "line": ("直线", "线条"),
    "polyline": ("折线", "连接符", "折线连接符", "弯折连接符"),
    "img": ("图片", "图像"),
    "fillImg": ("平铺图片", "填充图片", "背景图"),
    "icon": ("图标",),
    "table": ("表格",),
    "chart": ("图表", "原生图表"),
    "embed": ("内嵌", "svg", "矢量图"),
    "fill": ("填充", "背景色", "渐变"),
    "border": ("边框", "描边", "虚线"),
    "shadow": ("阴影",),
    "content": ("正文", "文本内容"),
    "p": ("段落",),
    "theme": ("主题", "配色"),
}

# 属性级别的中文别名：挂在"完整可用属性"表的说明里。
ATTRIBUTE_ALIASES = {
    "width": ("宽", "宽度"),
    "height": ("高", "高度"),
    "topLeftX": ("左上角 X", "横坐标", "位置"),
    "topLeftY": ("左上角 Y", "纵坐标", "位置"),
    "align": ("对齐",),
    "anchor": ("锚点", "对齐"),
    "alpha": ("透明度", "不透明度"),
    "rotation": ("旋转", "角度"),
    "fontSize": ("字号", "字体大小"),
    "fontFamily": ("字体",),
    "dashArray": ("虚线", "边框样式"),
    "color": ("颜色",),
}

# XSD 完全表达不了、grep XSD 永远搜不到的运行时约束。这是本索引相对裸 XSD
# 唯一的"独有知识"，必须随元素一起写进静态文本。
HIGH_PRIORITY_NOTES = {
    "embed": (
        "内层必须恰好有一个 SVG 命名空间元素：`<svg xmlns=\"http://www.w3.org/2000/svg\">`。",
        "SVG 必须声明 `viewBox`，且所有图形、描边和文字边界都不得越出 viewBox；XSD 以 `xs:any` 接收 SVG，无法替你检查这条运行时约束。",
        "`embed` 的 width:height 应与 SVG viewBox 的 W:H 一致，避免服务端等比缩放后产生变形或留白。",
    ),
    "polyline": (
        "`bent-connector2`…`bent-connector5` 和 `curved-connector2`…`curved-connector5` 是 `<polyline>` 的 `type`，不是 `<shape>` 的 `type`。",
    ),
    "fillImg": (
        "平铺图片的 `align` 使用 `left-top` / `right-top` / `left-bottom` / `right-bottom`；不要写成效果对齐使用的 `top-left` 等值。",
        "拉伸属性与平铺属性不能同时使用。",
    ),
}

# The XSD keeps the full transition vocabulary so existing documents can still
# be read and linted. The generated index is the authoring surface, so expose
# only the effects and attributes currently supported for new pages.
INDEX_ATTRIBUTE_NAMES = {
    "transition": frozenset({"type", "durationMs", "style", "direction"}),
}
INDEX_DOCUMENTATION_OVERRIDES = {
    "transition": (
        "页面切换节点。生成页面时仅使用 fade / cover / pull / push 四种效果；"
        "none 用于显式关闭切换。"
    ),
}
INDEX_ATTRIBUTE_CONSTRAINTS = {
    "transition": {
        "type": "字符串；枚举：none | fade | cover | pull | push",
        "durationMs": "整数；限制：>= 0，<= 86399999；默认 1000 毫秒",
        "style": "字符串；枚举：smoothly | through-black；仅 fade 使用",
        "direction": (
            "字符串；枚举：from-bottom | from-top | from-left | from-right；"
            "仅 push / cover / pull 使用"
        ),
    },
}

# 高频元素的手写最小示例：比自动合成更保真，直接照抄即可。
CURATED_EXAMPLES = {
    "chart": '<chart topLeftX="0" topLeftY="0" width="320" height="180">\n  <chartPlotArea><chartPlot type="pie"/></chartPlotArea>\n  <chartData>\n    <dim1><chartField name="category" valueType="string">A,B</chartField></dim1>\n    <dim2><chartField name="series" valueType="number">1,2</chartField></dim2>\n  </chartData>\n</chart>',
    "embed": '<embed topLeftX="0" topLeftY="0" width="200" height="100">\n  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">\n    <rect x="0" y="0" width="200" height="100" fill="#FFFFFF"/>\n  </svg>\n</embed>',
    "polyline": '<polyline type="bent-connector3" topLeftX="0" topLeftY="0" width="100" height="60">\n  <border color="rgb(0,0,0)" width="1"/>\n</polyline>',
    "line": '<line startX="0" startY="0" endX="100" endY="60">\n  <border color="rgb(0,0,0)" width="1"/>\n</line>',
    "shape": '<shape type="rect" topLeftX="0" topLeftY="0" width="100" height="60"/>',
    "img": '<img src="file_token" topLeftX="0" topLeftY="0" width="160" height="90"/>',
    "content": '<content textType="body"><p>文本</p></content>',
    "p": "<p>文本</p>",
    "fillImg": '<fillImg src="file_token" align="left-top"/>',
    "border": '<border color="rgb(0,0,0)" width="1" dashArray="solid"/>',
}


def local_name(value: str | None) -> str:
    return (value or "").rsplit(":", 1)[-1]


def documentation(node: ET.Element | None) -> str:
    if node is None:
        return ""
    parts = []
    for item in node.findall(f"{XS}annotation/{XS}documentation"):
        text = " ".join("".join(item.itertext()).split())
        if text:
            parts.append(text)
    return " ".join(parts)


def occurs(node: ET.Element) -> str:
    minimum = node.get("minOccurs", "1")
    maximum = node.get("maxOccurs", "1")
    if minimum == maximum == "1":
        return "1"
    return f"{minimum}..{maximum}"


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        compact = " ".join(value.split())
        if compact and compact not in seen:
            seen.add(compact)
            result.append(compact)
    return result


@dataclass
class AttributeInfo:
    name: str
    type_name: str
    use: str
    default: str | None
    fixed: str | None
    simple_type: ET.Element | None
    documentation: str


@dataclass
class ElementInfo:
    name: str
    type_name: str
    node: ET.Element
    complex_type: ET.Element | None
    contexts: list[str] = field(default_factory=list)


class SchemaIndex:
    """Parses the XSD and resolves inheritance so each element is self-contained."""

    def __init__(self, schema_path: Path) -> None:
        self.schema_path = schema_path
        self.root = ET.parse(schema_path).getroot()
        self.simple_types = {
            node.get("name", ""): node
            for node in self.root.findall(f"{XS}simpleType")
            if node.get("name")
        }
        self.complex_types = {
            node.get("name", ""): node
            for node in self.root.findall(f"{XS}complexType")
            if node.get("name")
        }
        self.global_elements = {
            node.get("name", ""): node
            for node in self.root.findall(f"{XS}element")
            if node.get("name")
        }
        self.elements = self._collect_elements()
        self.parents_by_name = self._build_parent_map()

    def _build_parent_map(self) -> dict[str, list[str]]:
        """反向内容模型：对每个元素，记录哪些真实父标签能直接包含它。

        `出现场景` 给的是 XSD 的词法声明作用域（如 `ThemeType`、`全局`），不是
        实际父标签；模型想知道"我能放进谁"时只能全文反查。这里遍历每个元素的
        子元素粒子，反向聚合出真实父标签名，直接写进索引。
        """
        parents: dict[str, set[str]] = {}
        for element in self.elements:
            if element.complex_type is None:
                continue
            for child in self._direct_children(element.complex_type):
                child_name = local_name(child.get("name") or child.get("ref"))
                if child_name:
                    parents.setdefault(child_name, set()).add(element.name)
        return {name: sorted(values) for name, values in parents.items()}

    def _complex_type_for(self, element: ET.Element) -> ET.Element | None:
        inline = element.find(f"{XS}complexType")
        if inline is not None:
            return inline
        return self.complex_types.get(local_name(element.get("type")))

    def _collect_elements(self) -> list[ElementInfo]:
        grouped: dict[tuple[str, str, bytes], ElementInfo] = {}
        parents = {child: parent for parent in self.root.iter() for child in parent}

        def context_for(element: ET.Element) -> str:
            current = parents.get(element)
            while current is not None and current is not self.root:
                if current.tag == f"{XS}element" and current.get("name"):
                    return f"<{current.get('name')}>"
                if current.tag == f"{XS}complexType" and current.get("name"):
                    return current.get("name", "")
                current = parents.get(current)
            return "全局"

        for declaration in self.root.iter(f"{XS}element"):
            if declaration.get("ref") or not declaration.get("name"):
                continue
            name = declaration.get("name", "")
            type_name = local_name(declaration.get("type"))
            complex_type = self._complex_type_for(declaration)
            inline_key = (
                ET.tostring(complex_type) if complex_type is not None and not type_name else b""
            )
            key = (name, type_name, inline_key)
            item = grouped.get(key)
            if item is None:
                item = ElementInfo(name, type_name, declaration, complex_type)
                grouped[key] = item
            context = context_for(declaration)
            if context not in item.contexts:
                item.contexts.append(context)
        return sorted(grouped.values(), key=lambda item: (item.name.casefold(), item.type_name))

    def _extension(self, complex_type: ET.Element) -> ET.Element | None:
        extension = complex_type.find(f"{XS}complexContent/{XS}extension")
        if extension is not None:
            return extension
        return complex_type.find(f"{XS}simpleContent/{XS}extension")

    def _direct_children(self, complex_type: ET.Element) -> list[ET.Element]:
        result: list[ET.Element] = []
        extension = self._extension(complex_type)
        containers = [complex_type]
        if extension is not None:
            base = self.complex_types.get(local_name(extension.get("base")))
            if base is not None:
                result.extend(self._direct_children(base))
            containers = [extension]

        def walk(node: ET.Element) -> None:
            for child in node:
                if child.tag in {f"{XS}element", f"{XS}any"}:
                    result.append(child)
                elif child.tag in {f"{XS}sequence", f"{XS}choice", f"{XS}all"}:
                    walk(child)

        for container in containers:
            walk(container)
        return result

    def attributes(self, complex_type: ET.Element | None) -> list[AttributeInfo]:
        if complex_type is None:
            return []
        nodes: list[ET.Element] = []
        extension = self._extension(complex_type)
        if extension is not None:
            base = self.complex_types.get(local_name(extension.get("base")))
            if base is not None:
                nodes.extend(self._attribute_nodes(base))
            nodes.extend(extension.findall(f"{XS}attribute"))
        else:
            nodes.extend(complex_type.findall(f"{XS}attribute"))
        return [self._attribute_info(node) for node in nodes]

    def _attribute_nodes(self, complex_type: ET.Element) -> list[ET.Element]:
        extension = self._extension(complex_type)
        if extension is None:
            return list(complex_type.findall(f"{XS}attribute"))
        result: list[ET.Element] = []
        base = self.complex_types.get(local_name(extension.get("base")))
        if base is not None:
            result.extend(self._attribute_nodes(base))
        result.extend(extension.findall(f"{XS}attribute"))
        return result

    def _attribute_info(self, node: ET.Element) -> AttributeInfo:
        type_name = local_name(node.get("type"))
        simple_type = node.find(f"{XS}simpleType")
        if simple_type is None:
            simple_type = self.simple_types.get(type_name)
        return AttributeInfo(
            name=node.get("name", "?"),
            type_name=type_name or "匿名简单类型",
            use=node.get("use", "optional"),
            default=node.get("default"),
            fixed=node.get("fixed"),
            simple_type=simple_type,
            documentation=documentation(node),
        )

    def content_model(self, complex_type: ET.Element | None) -> str:
        """忠实还原内容模型：区分 choice/sequence/all 并标出每层的重复次数。

        不能把子元素压平成一串 `[1]`：例如 `<p>` 的内联子元素在一个
        `choice maxOccurs="unbounded"` 里（任选、可重复任意次），压平后会让模型
        误以为每种只能放一个。
        """
        if complex_type is None:
            return "无。"
        extension = self._extension(complex_type)
        containers: list[ET.Element] = [complex_type]
        prefix = ""
        if extension is not None:
            base = self.complex_types.get(local_name(extension.get("base")))
            if base is not None:
                base_model = self.content_model(base)
                if base_model != "无。":
                    prefix = base_model
            containers = [extension]
        parts: list[str] = []
        for container in containers:
            for child in container:
                if child.tag in {
                    f"{XS}sequence",
                    f"{XS}choice",
                    f"{XS}all",
                    f"{XS}element",
                    f"{XS}any",
                }:
                    rendered = self._render_particle(child)
                    if rendered:
                        parts.append(rendered)
        body = "；".join(parts)
        if prefix:
            body = prefix + ("；" + body if body else "")
        return body or "无。"

    def _render_particle(self, node: ET.Element) -> str:
        suffix = "" if occurs(node) == "1" else f"（{occurs(node)}）"
        if node.tag == f"{XS}element":
            name = local_name(node.get("name") or node.get("ref"))
            return f"`{name}`{suffix}" if name else ""
        if node.tag == f"{XS}any":
            return f"任意元素（namespace={node.get('namespace', 'any')}）{suffix}"
        label = {
            f"{XS}sequence": "按顺序",
            f"{XS}choice": "选择其一",
            f"{XS}all": "任意顺序各一次",
        }.get(node.tag, "")
        inner = [self._render_particle(child) for child in node]
        inner = [item for item in inner if item]
        if not inner:
            return ""
        joiner = " | " if node.tag == f"{XS}choice" else "，"
        return f"{label}[{joiner.join(inner)}]{suffix}"

    def simple_constraints(self, type_name: str, inline: ET.Element | None = None) -> list[str]:
        seen: set[str] = set()

        def resolve(name: str, node: ET.Element | None) -> list[str]:
            if name in seen:
                return []
            if name:
                seen.add(name)
            if node is None:
                node = self.simple_types.get(name)
            if node is None:
                builtin = BUILTIN_CONSTRAINTS.get(name)
                return [builtin] if builtin else ([f"类型：{name}"] if name else [])
            result: list[str] = []
            doc = documentation(node)
            if doc:
                result.append(doc)
            restriction = node.find(f"{XS}restriction")
            if restriction is not None:
                base = local_name(restriction.get("base"))
                result.extend(resolve(base, None))
                enums = [item.get("value", "") for item in restriction.findall(f"{XS}enumeration")]
                if enums:
                    result.append("枚举：" + " | ".join(enums))
                patterns = [item.get("value", "") for item in restriction.findall(f"{XS}pattern")]
                if patterns:
                    result.append("格式正则：" + " 或 ".join(patterns))
                labels = {
                    "minInclusive": ">=",
                    "minExclusive": ">",
                    "maxInclusive": "<=",
                    "maxExclusive": "<",
                    "minLength": "最短长度",
                    "maxLength": "最长长度",
                    "length": "长度",
                }
                facets = []
                for facet, label in labels.items():
                    facets.extend(
                        f"{label} {item.get('value')}"
                        for item in restriction.findall(f"{XS}{facet}")
                    )
                if facets:
                    result.append("限制：" + "，".join(facets))
            union = node.find(f"{XS}union")
            if union is not None:
                members = []
                for member in union.get("memberTypes", "").split():
                    member_name = local_name(member)
                    detail = "；".join(resolve(member_name, None))
                    members.append(f"{member_name}（{detail}）")
                for member in union.findall(f"{XS}simpleType"):
                    members.append("；".join(resolve("", member)))
                result.append("联合类型：" + " / ".join(members))
            list_node = node.find(f"{XS}list")
            if list_node is not None:
                item_type = local_name(list_node.get("itemType"))
                item_constraints = "；".join(resolve(item_type, None))
                result.append(
                    f"空格分隔列表，单项类型：{item_type}"
                    + (f"（{item_constraints}）" if item_constraints else "")
                )
            return result

        return dedupe(resolve(type_name, inline))


# --------------------------------------------------------------------------- #
# Minimal-example synthesis (curated first, auto-generated骨架 as fallback).
# --------------------------------------------------------------------------- #


def sample_value(index: SchemaIndex, attribute: AttributeInfo) -> str:
    constraints = index.simple_constraints(attribute.type_name, attribute.simple_type)
    enum_line = next((line for line in constraints if line.startswith("枚举：")), "")
    if enum_line:
        return enum_line.removeprefix("枚举：").split(" | ", 1)[0]
    overrides = {
        "src": "file_token",
        "iconType": "iconpark/Base/setting.svg",
        "topLeftX": "0",
        "topLeftY": "0",
        "width": "100",
        "height": "100",
        "type": "value",
        "textType": "body",
        "color": "rgb(0,0,0)",
        "fontSize": "18",
    }
    if attribute.name in overrides:
        return overrides[attribute.name]
    if attribute.type_name == "boolean":
        return "true"
    if attribute.type_name in {
        "decimal",
        "double",
        "integer",
        "nonNegativeInteger",
        "positiveInteger",
        "NonNegativeInt",
        "NonNegativeDouble",
        "PositiveSize",
        "XType",
        "YType",
    }:
        return "1"
    return "value"


def required_particles(index: SchemaIndex, complex_type: ET.Element | None) -> list[ET.Element]:
    if complex_type is None:
        return []
    result: list[ET.Element] = []
    extension = index._extension(complex_type)
    containers = [complex_type]
    if extension is not None:
        base = index.complex_types.get(local_name(extension.get("base")))
        if base is not None:
            result.extend(required_particles(index, base))
        containers = [extension]

    def visit(node: ET.Element, required: bool = True) -> None:
        for child in node:
            if child.tag in {f"{XS}sequence", f"{XS}all"}:
                if child.get("minOccurs", "1") != "0":
                    visit(child)
            elif child.tag == f"{XS}choice":
                if child.get("minOccurs", "1") != "0":
                    candidates = [
                        item
                        for item in child
                        if item.tag in {f"{XS}element", f"{XS}any", f"{XS}sequence"}
                    ]
                    if candidates:
                        chosen = candidates[0]
                        if chosen.tag == f"{XS}sequence":
                            visit(chosen)
                        else:
                            result.append(chosen)
            elif child.tag in {f"{XS}element", f"{XS}any"} and required:
                if child.get("minOccurs", "1") != "0":
                    result.append(child)

    for container in containers:
        visit(container)
    return result


def declaration_for(index: SchemaIndex, particle: ET.Element) -> ET.Element | None:
    reference = local_name(particle.get("ref"))
    return index.global_elements.get(reference) if reference else particle


def build_example(index: SchemaIndex, declaration: ET.Element, seen: frozenset[int]) -> str:
    name = local_name(declaration.get("name") or declaration.get("ref"))
    if not name:
        return ""
    target = declaration_for(index, declaration)
    if target is None:
        return f"<{name}/>"
    complex_type = index._complex_type_for(target)
    attributes = index.attributes(complex_type)
    rendered_attrs = "".join(
        f' {attr.name}="{sample_value(index, attr)}"'
        for attr in attributes
        if attr.use == "required"
    )
    identity = id(target)
    if identity in seen:
        return f"<{name}{rendered_attrs}/>"
    children = []
    for particle in required_particles(index, complex_type):
        if particle.tag == f"{XS}any":
            if particle.get("namespace") == "http://www.w3.org/2000/svg":
                children.append(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
                    '<rect x="0" y="0" width="100" height="100" fill="#FFFFFF"/>'
                    "</svg>"
                )
            continue
        child = declaration_for(index, particle)
        if child is not None:
            children.append(build_example(index, child, seen | {identity}))
    type_name = local_name(target.get("type"))
    simple_type = target.find(f"{XS}simpleType")
    if simple_type is None:
        simple_type = index.simple_types.get(type_name)
    if not children and (simple_type is not None or type_name in BUILTIN_CONSTRAINTS):
        children.append("value")
    if not children:
        return f"<{name}{rendered_attrs}/>"
    if all("\n" not in child for child in children) and sum(map(len, children)) < 80:
        return f"<{name}{rendered_attrs}>{''.join(children)}</{name}>"
    body = "\n".join(textwrap.indent(child, "  ") for child in children)
    return f"<{name}{rendered_attrs}>\n{body}\n</{name}>"


def example_for(index: SchemaIndex, element: ElementInfo) -> str:
    if element.name in CURATED_EXAMPLES:
        return CURATED_EXAMPLES[element.name]
    return build_example(index, element.node, frozenset())


# --------------------------------------------------------------------------- #
# Flat Markdown rendering.
# --------------------------------------------------------------------------- #


def format_constraint(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def aliases_for_element(name: str) -> list[str]:
    return list(INTENT_ALIASES.get(name, ()))


def aliases_for_attribute(name: str) -> list[str]:
    return list(ATTRIBUTE_ALIASES.get(name, ()))


def index_attributes(index: SchemaIndex, element: ElementInfo) -> list[AttributeInfo]:
    attributes = index.attributes(element.complex_type)
    allowed = INDEX_ATTRIBUTE_NAMES.get(element.name)
    if allowed is None:
        return attributes
    return [attribute for attribute in attributes if attribute.name in allowed]


def index_constraints(
    index: SchemaIndex, element: ElementInfo, attribute: AttributeInfo
) -> list[str]:
    override = INDEX_ATTRIBUTE_CONSTRAINTS.get(element.name, {}).get(attribute.name)
    if override is not None:
        return [override]
    return index.simple_constraints(attribute.type_name, attribute.simple_type)


def render_element(index: SchemaIndex, element: ElementInfo) -> str:
    attributes = index_attributes(index, element)
    doc = INDEX_DOCUMENTATION_OVERRIDES.get(element.name) or (
        documentation(element.node) or documentation(element.complex_type)
    )
    notes = list(HIGH_PRIORITY_NOTES.get(element.name, ()))
    if doc:
        notes.append(doc)

    alias_terms = aliases_for_element(element.name)
    for attr in attributes:
        alias_terms.extend(aliases_for_attribute(attr.name))
    alias_terms = dedupe(alias_terms)

    lines = [
        f"## `<{element.name}>`",
        "",
        f"- 声明类型：`{element.type_name or '匿名 complexType'}`",
        f"- 出现场景：{'; '.join(element.contexts)}",
    ]
    parent_tags = index.parents_by_name.get(element.name, [])
    if parent_tags:
        lines.append(f"- 父元素：{', '.join(f'`<{tag}>`' for tag in parent_tags)}")
    if alias_terms:
        lines.append(f"- 中文检索词：{', '.join(alias_terms)}")
    lines.append("")

    lines.extend(["### 高优先级约束", ""])
    if notes:
        lines.extend(f"- {item}" for item in dedupe(notes))
    else:
        lines.append("- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。")

    attribute_heading = (
        "### 生成页面可用属性"
        if element.name in INDEX_ATTRIBUTE_NAMES
        else "### 完整可用属性"
    )
    lines.extend(["", attribute_heading, ""])
    if attributes:
        lines.extend(
            [
                "| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |",
                "|---|---|---|---|---|",
            ]
        )
        for attr in attributes:
            default = ""
            if attr.default is not None:
                default = f"默认 `{attr.default}`"
            if attr.fixed is not None:
                default = f"固定 `{attr.fixed}`"
            constraints = "；".join(index_constraints(index, element, attr)) or "无额外限制"
            lines.append(
                f"| `{attr.name}` | {'是' if attr.use == 'required' else '否'} | "
                f"{default or '-'} | `{attr.type_name}` | {format_constraint(constraints)} |"
            )
    else:
        lines.append("无属性。")

    children = index.content_model(element.complex_type)
    lines.extend(["", "### 子元素（内容模型）", "", children])
    lines.extend(["", "### 最小可用 XML", "", "```xml", example_for(index, element), "```", ""])
    return "\n".join(lines)


def render_index(index: SchemaIndex) -> str:
    return "\n".join(render_element(index, element) for element in index.elements).rstrip("\n") + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把 Slides XML XSD 编译成扁平、可 grep 的 Markdown 索引。",
    )
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="XSD 路径")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="索引输出路径")
    parser.add_argument(
        "--check",
        action="store_true",
        help="只校验现有索引是否与 XSD 同步，不写文件；不一致时返回码 1（供 CI 使用）。",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        index = SchemaIndex(args.schema)
    except (OSError, ET.ParseError) as exc:
        print(f"build-schema-index error: {exc}", file=sys.stderr)
        return 2
    content = render_index(index)

    if args.check:
        if not args.output.exists():
            print(f"索引缺失：{args.output}，请运行 python3 scripts/build_schema_index.py", file=sys.stderr)
            return 1
        current = args.output.read_text(encoding="utf-8")
        if current != content:
            print(
                f"索引已过期：{args.output} 与 XSD 不同步，请运行 "
                "python3 scripts/build_schema_index.py 重新生成。",
                file=sys.stderr,
            )
            return 1
        print(f"索引已同步：{args.output}")
        return 0

    args.output.write_text(content, encoding="utf-8")
    print(f"已生成 {args.output}（{len(index.elements)} 个元素）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
