# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///

"""
Word 文档解包/打包工具：解包 .docx 为可编辑的 XML，编辑后打包回 .docx。

用法：
    uv run scripts/docx_edit.py unpack template.docx unpacked/
    uv run scripts/docx_edit.py pack unpacked/ filled.docx

解包后在 unpacked/word/document.xml 中用编辑工具替换文本，
保留 <w:rPr>（格式属性）不动，只改 <w:t> 中的文字。
"""

from __future__ import annotations

import argparse
import sys
import xml.dom.minidom
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

SMART_QUOTES = {
    "\u201c": "&#x201C;",
    "\u201d": "&#x201D;",
    "\u2018": "&#x2018;",
    "\u2019": "&#x2019;",
}

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def _pretty_print_xml(path: Path) -> None:
    try:
        dom = xml.dom.minidom.parseString(path.read_bytes())
        path.write_bytes(dom.toprettyxml(indent="  ", encoding="utf-8"))
    except Exception:
        pass


def _escape_smart_quotes(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
        for char, entity in SMART_QUOTES.items():
            text = text.replace(char, entity)
        path.write_text(text, encoding="utf-8")
    except Exception:
        pass


def _condense_xml(path: Path) -> None:
    try:
        dom = xml.dom.minidom.parseString(path.read_bytes())
        for elem in dom.getElementsByTagName("*"):
            if elem.tagName.endswith(":t"):
                continue
            for child in list(elem.childNodes):
                if (
                    child.nodeType == child.TEXT_NODE
                    and child.nodeValue
                    and child.nodeValue.strip() == ""
                ) or child.nodeType == child.COMMENT_NODE:
                    elem.removeChild(child)
        path.write_bytes(dom.toxml(encoding="UTF-8"))
    except Exception as e:
        print(f"警告：压缩 {path.name} 时出错：{e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Merge runs — 合并相邻的相同格式文本节点，减少 XML 碎片
# ---------------------------------------------------------------------------

def _merge_runs(doc_xml: Path) -> int:
    """合并 document.xml 中相邻且格式相同的 <w:r> 元素。"""
    if not doc_xml.exists():
        return 0

    try:
        dom = xml.dom.minidom.parseString(doc_xml.read_text(encoding="utf-8"))
    except Exception:
        return 0

    # 移除 proofErr 和 rsid 属性（这些会阻止合并）
    for elem in _find_dom_elements(dom.documentElement, "proofErr"):
        if elem.parentNode:
            elem.parentNode.removeChild(elem)
    for run in _find_dom_elements(dom.documentElement, "r"):
        for attr in list(run.attributes.values()):
            if "rsid" in attr.name.lower():
                run.removeAttribute(attr.name)

    containers = {run.parentNode for run in _find_dom_elements(dom.documentElement, "r")}
    count = 0
    for container in containers:
        count += _merge_runs_in(container)

    doc_xml.write_bytes(dom.toxml(encoding="UTF-8"))
    return count


def _find_dom_elements(root, tag: str) -> list:
    results = []
    def walk(node):
        if node.nodeType == node.ELEMENT_NODE:
            name = node.localName or node.tagName
            if name == tag or name.endswith(f":{tag}"):
                results.append(node)
            for child in node.childNodes:
                walk(child)
    walk(root)
    return results


def _get_dom_child(parent, tag: str):
    for child in parent.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            name = child.localName or child.tagName
            if name == tag or name.endswith(f":{tag}"):
                return child
    return None


def _merge_runs_in(container) -> int:
    count = 0
    run = None
    for child in container.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            name = child.localName or child.tagName
            if name == "r" or name.endswith(":r"):
                run = child
                break
    if not run:
        return 0

    while run:
        nxt = run.nextSibling
        while nxt and nxt.nodeType != nxt.ELEMENT_NODE:
            nxt = nxt.nextSibling
        if nxt and ((nxt.localName or nxt.tagName) == "r" or (nxt.localName or nxt.tagName).endswith(":r")):
            rpr1 = _get_dom_child(run, "rPr")
            rpr2 = _get_dom_child(nxt, "rPr")
            same = (rpr1 is None and rpr2 is None) or (
                rpr1 is not None and rpr2 is not None and rpr1.toxml() == rpr2.toxml()
            )
            if same:
                for child in list(nxt.childNodes):
                    if child.nodeType == child.ELEMENT_NODE:
                        cname = child.localName or child.tagName
                        if cname != "rPr" and not cname.endswith(":rPr"):
                            run.appendChild(child)
                container.removeChild(nxt)
                count += 1
                continue
        # 合并 run 内的多个 <w:t>
        t_elems = [c for c in run.childNodes
                    if c.nodeType == c.ELEMENT_NODE
                    and ((c.localName or c.tagName) == "t" or (c.localName or c.tagName).endswith(":t"))]
        for i in range(len(t_elems) - 1, 0, -1):
            curr, prev = t_elems[i], t_elems[i - 1]
            prev_text = prev.firstChild.data if prev.firstChild else ""
            curr_text = curr.firstChild.data if curr.firstChild else ""
            merged = prev_text + curr_text
            if prev.firstChild:
                prev.firstChild.data = merged
            else:
                prev.appendChild(run.ownerDocument.createTextNode(merged))
            if merged.startswith(" ") or merged.endswith(" "):
                prev.setAttribute("xml:space", "preserve")
            run.removeChild(curr)

        # 前进到下一个 run
        nxt = run.nextSibling
        while nxt and nxt.nodeType != nxt.ELEMENT_NODE:
            nxt = nxt.nextSibling
        if nxt and ((nxt.localName or nxt.tagName) == "r" or (nxt.localName or nxt.tagName).endswith(":r")):
            run = nxt
        else:
            run = None

    return count


# ---------------------------------------------------------------------------
# Whitespace repair — 自动给含前导/尾随空格的 <w:t> 加 xml:space="preserve"
# ---------------------------------------------------------------------------

def _repair_whitespace(unpacked_dir: Path) -> int:
    repairs = 0
    for xml_file in list(unpacked_dir.rglob("*.xml")):
        try:
            dom = xml.dom.minidom.parseString(xml_file.read_text(encoding="utf-8"))
            modified = False
            for elem in dom.getElementsByTagName("*"):
                if elem.tagName.endswith(":t") and elem.firstChild:
                    text = elem.firstChild.nodeValue
                    if text and (text.startswith((" ", "\t")) or text.endswith((" ", "\t"))):
                        if elem.getAttribute("xml:space") != "preserve":
                            elem.setAttribute("xml:space", "preserve")
                            repairs += 1
                            modified = True
            if modified:
                xml_file.write_bytes(dom.toxml(encoding="UTF-8"))
        except Exception:
            pass
    return repairs


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def unpack(docx_path: str, output_dir: str) -> None:
    src = Path(docx_path)
    dst = Path(output_dir)

    if not src.exists():
        print(f"错误：文件不存在：{src}", file=sys.stderr)
        sys.exit(1)

    dst.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(src, "r") as zf:
        zf.extractall(dst)

    xml_files = list(dst.rglob("*.xml")) + list(dst.rglob("*.rels"))

    for f in xml_files:
        _pretty_print_xml(f)
        _escape_smart_quotes(f)

    doc_xml = dst / "word" / "document.xml"
    merge_count = _merge_runs(doc_xml)

    print(f"已解包：{src} → {dst}（{len(xml_files)} 个 XML 文件，合并 {merge_count} 个文本节点）")
    print(f"编辑 {dst}/word/document.xml 中的文本，然后运行 pack 命令打包回去。")


def pack(input_dir: str, output_file: str) -> None:
    src = Path(input_dir)
    dst = Path(output_file)

    if not src.is_dir():
        print(f"错误：目录不存在：{src}", file=sys.stderr)
        sys.exit(1)

    repairs = _repair_whitespace(src)
    if repairs:
        print(f"自动修复 {repairs} 个空格问题")

    for pattern in ["*.xml", "*.rels"]:
        for f in src.rglob(pattern):
            _condense_xml(f)

    dst.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in src.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(src))

    print(f"已打包：{src} → {dst}")


def main():
    parser = argparse.ArgumentParser(description="Word 文档解包/打包工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p_unpack = sub.add_parser("unpack", help="将 .docx 解包为 XML 目录")
    p_unpack.add_argument("docx_file", help=".docx 文件路径")
    p_unpack.add_argument("output_dir", help="输出目录")

    p_pack = sub.add_parser("pack", help="将 XML 目录打包为 .docx")
    p_pack.add_argument("input_dir", help="已解包的目录")
    p_pack.add_argument("output_file", help="输出 .docx 文件路径")

    args = parser.parse_args()

    if args.command == "unpack":
        unpack(args.docx_file, args.output_dir)
    elif args.command == "pack":
        pack(args.input_dir, args.output_file)


if __name__ == "__main__":
    main()
