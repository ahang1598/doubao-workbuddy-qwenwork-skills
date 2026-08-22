# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Word 文档解包/打包工具：解包 .docx 为可编辑的 XML，编辑后打包回 .docx。

用法：
    uv run scripts/docx_edit.py unpack resume.docx unpacked/
    uv run scripts/docx_edit.py pack unpacked/ resume_updated.docx

解包后在 unpacked/word/document.xml 中用编辑工具替换文本，
保留 <w:rPr>（格式属性）不动，只改 <w:t> 中的文字。
"""

import argparse
import sys
import xml.dom.minidom
import zipfile
from pathlib import Path

SMART_QUOTES = {
    "\u201c": "&#x201C;",
    "\u201d": "&#x201D;",
    "\u2018": "&#x2018;",
    "\u2019": "&#x2019;",
}


def _pretty_print_xml(path: Path) -> None:
    try:
        raw = path.read_bytes()
        dom = xml.dom.minidom.parseString(raw)
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
        raw = path.read_bytes()
        dom = xml.dom.minidom.parseString(raw)
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

    print(f"已解包：{src} → {dst}（{len(xml_files)} 个 XML 文件）")
    print(f"编辑 {dst}/word/document.xml 中的文本，然后运行 pack 命令打包回去。")


def pack(input_dir: str, output_file: str) -> None:
    src = Path(input_dir)
    dst = Path(output_file)

    if not src.is_dir():
        print(f"错误：目录不存在：{src}", file=sys.stderr)
        sys.exit(1)

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
