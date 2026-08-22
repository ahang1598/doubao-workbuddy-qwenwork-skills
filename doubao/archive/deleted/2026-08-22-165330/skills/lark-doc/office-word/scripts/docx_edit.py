# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Word 文档解包/打包/替换工具：在 .docx 上修改内容，保留原始格式。

用法：
    # 解包：将 .docx 解压为可编辑的 XML 目录
    uv run scripts/docx_edit.py unpack 模板.docx unpacked/

    # 打包：将编辑后的 XML 目录重新打包为 .docx
    uv run scripts/docx_edit.py pack unpacked/ 输出.docx

    # 替换：直接在 .docx 中做文本替换（一步完成解包→替换→打包）
    uv run scripts/docx_edit.py replace 原文件.docx 输出.docx replacements.json

解包后在 unpacked/word/document.xml 中用编辑工具替换文本，
保留 <w:rPr>（格式属性）不动，只改 <w:t> 中的文字。

replacements.json 格式：
    {
      "replacements": [
        {"find": "{{发明名称}}", "replace": "一种智能停车管理方法"},
        {"find": "旧文本", "replace": "新文本"}
      ],
      "track_changes": false,
      "author": "patent-assistant"
    }

当 track_changes 为 true 时，替换以修订标记形式体现，方便审查员对比。
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
import xml.dom.minidom
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SMART_QUOTES = {
    "\u201c": "&#x201C;",
    "\u201d": "&#x201D;",
    "\u2018": "&#x2018;",
    "\u2019": "&#x2019;",
}


# ──────────────────────────────────────────────
#  unpack / pack
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
#  replace — 自动 unpack → 替换 → pack
# ──────────────────────────────────────────────

def replace(input_path: str, output_path: str, replacements_path: str) -> None:
    inp = Path(input_path)
    out = Path(output_path)
    rep = Path(replacements_path)

    if not inp.exists():
        print(f"错误：输入文件不存在：{inp}", file=sys.stderr)
        sys.exit(1)
    if not rep.exists():
        print(f"错误：替换规则文件不存在：{rep}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(rep.read_text(encoding="utf-8"))
    replacements = data.get("replacements", [])
    track_changes = data.get("track_changes", False)
    author = data.get("author", "patent-assistant")

    if not replacements:
        print("警告：没有替换规则", file=sys.stderr)
        shutil.copy2(inp, out)
        return

    with tempfile.TemporaryDirectory() as tmp:
        unpacked = Path(tmp) / "unpacked"
        unpacked.mkdir()
        with zipfile.ZipFile(inp) as z:
            z.extractall(unpacked)

        doc_xml = unpacked / "word" / "document.xml"
        if not doc_xml.exists():
            print("错误：文件结构异常，找不到 word/document.xml", file=sys.stderr)
            sys.exit(1)

        xml_content = doc_xml.read_text(encoding="utf-8")
        total_count = 0

        for rule in replacements:
            find_text = rule["find"]
            replace_text = rule["replace"]

            if track_changes:
                xml_content, count = _replace_with_tracking(
                    xml_content, find_text, replace_text, author
                )
            else:
                xml_content, count = _replace_in_xml(xml_content, find_text, replace_text)

            total_count += count
            if count > 0:
                find_preview = find_text[:30] + ("..." if len(find_text) > 30 else "")
                replace_preview = replace_text[:30] + ("..." if len(replace_text) > 30 else "")
                print(f"  替换: \"{find_preview}\" → \"{replace_preview}\" ({count} 处)")

        doc_xml.write_text(xml_content, encoding="utf-8")

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in unpacked.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(unpacked))

    print(f"完成：{out}（共替换 {total_count} 处）")


def _replace_in_xml(xml_content: str, find: str, replace: str) -> tuple[str, int]:
    """在 XML 中替换文本，处理文本可能被拆分到多个 <w:t> 标签的情况。"""
    result = re.sub(
        r'(<w:t[^>]*>)(.*?)(</w:t>)',
        lambda m: m.group(1) + m.group(2).replace(find, replace) + m.group(3)
        if find in m.group(2) else m.group(0),
        xml_content, flags=re.DOTALL
    )

    count = xml_content.count(find) - result.count(find) if result != xml_content else 0
    if count > 0:
        return result, count

    return _replace_across_runs(xml_content, find, replace)


def _replace_across_runs(xml_content: str, find: str, replace: str) -> tuple[str, int]:
    """处理文本被拆分到多个 <w:r> 中的情况——在段落级别拼接所有文本后匹配替换。"""
    count = 0
    para_pattern = re.compile(r'(<w:p[ >].*?</w:p>)', re.DOTALL)
    t_pattern = re.compile(r'(<w:t[^>]*>)(.*?)(</w:t>)', re.DOTALL)

    def process_paragraph(para_match):
        nonlocal count
        para_xml = para_match.group(0)
        t_matches = list(t_pattern.finditer(para_xml))
        if not t_matches:
            return para_xml

        full_text = "".join(m.group(2) for m in t_matches)
        if find not in full_text:
            return para_xml

        new_text = full_text.replace(find, replace)
        count += full_text.count(find)

        rebuilt = para_xml
        for i, m in enumerate(reversed(t_matches)):
            idx = len(t_matches) - 1 - i
            if idx == 0:
                rebuilt = rebuilt[:m.start(2)] + new_text + rebuilt[m.end(2):]
            else:
                rebuilt = rebuilt[:m.start(2)] + rebuilt[m.end(2):]

        return rebuilt

    return para_pattern.sub(process_paragraph, xml_content), count


def _replace_with_tracking(xml_content: str, find: str, replace: str, author: str) -> tuple[str, int]:
    """用修订标记替换文本（删除旧 + 插入新）。"""
    count = 0
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    ids = [int(x) for x in re.findall(r'w:id="(\d+)"', xml_content)]
    next_id = max(ids) + 1 if ids else 100

    def make_tracked_replace(match):
        nonlocal count, next_id
        original_text = match.group(2)
        if find not in original_text:
            return match.group(0)

        count += original_text.count(find)
        parts = original_text.split(find)
        result_parts = []

        for i, part in enumerate(parts):
            if part:
                result_parts.append(f'{match.group(1)}{part}{match.group(3)}')
            if i < len(parts) - 1:
                del_id = next_id
                ins_id = next_id + 1
                next_id += 2
                result_parts.append(
                    f'<w:del w:id="{del_id}" w:author="{author}" w:date="{ts}">'
                    f'<w:r><w:delText>{find}</w:delText></w:r></w:del>'
                    f'<w:ins w:id="{ins_id}" w:author="{author}" w:date="{ts}">'
                    f'<w:r><w:t>{replace}</w:t></w:r></w:ins>'
                )

        return "".join(result_parts)

    t_pattern = re.compile(r'(<w:t[^>]*>)(.*?)(</w:t>)', re.DOTALL)
    result = t_pattern.sub(make_tracked_replace, xml_content)
    return result, count


# ──────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Word 文档解包/打包/替换工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p_unpack = sub.add_parser("unpack", help="将 .docx 解包为 XML 目录")
    p_unpack.add_argument("docx_file", help=".docx 文件路径")
    p_unpack.add_argument("output_dir", help="输出目录")

    p_pack = sub.add_parser("pack", help="将 XML 目录打包为 .docx")
    p_pack.add_argument("input_dir", help="已解包的目录")
    p_pack.add_argument("output_file", help="输出 .docx 文件路径")

    p_replace = sub.add_parser("replace", help="在 .docx 中替换文本（保留原格式）")
    p_replace.add_argument("input", help="输入 .docx 文件")
    p_replace.add_argument("output", help="输出 .docx 文件")
    p_replace.add_argument("replacements", help="替换规则 JSON 文件")

    args = parser.parse_args()

    if args.command == "unpack":
        unpack(args.docx_file, args.output_dir)
    elif args.command == "pack":
        pack(args.input_dir, args.output_file)
    elif args.command == "replace":
        replace(args.input, args.output, args.replacements)


if __name__ == "__main__":
    main()
