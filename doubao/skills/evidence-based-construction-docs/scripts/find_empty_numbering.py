#!/usr/bin/env python3
"""列出 docx 中的空编号段落，并区分"真空段"与"序号/内容分段"。

用法: python3 find_empty_numbering.py <file.docx>

docx 本质是 ZIP，正文在 word/document.xml。空编号段落 = 带 <w:numPr>
但没有 <w:t> 文本的 <w:p>。若空编号段落紧跟一个无 numPr 的文本段落，
通常是 WPS/PDF 转换残留的"序号与内容分段"——删掉它会让后面的内容段
失去编号（真实事故：一次性删除 80 个空编号段落后，有内容的列表全部
失去编号，只能手工恢复）。所以分两类报告，只删第一类。
"""
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def para_info(p):
    ppr = p.find(f"{W}pPr")
    has_num = ppr is not None and ppr.find(f"{W}numPr") is not None
    text = "".join(t.text or "" for t in p.iter(f"{W}t")).strip()
    return has_num, text


def main(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    empty, split_src = [], []
    prev_empty = None
    for i, p in enumerate(root.iter(f"{W}p")):
        has_num, text = para_info(p)
        if has_num and not text:
            empty.append(i)
            prev_empty = i
        elif text and not has_num and prev_empty is not None:
            split_src.append(prev_empty)
            prev_empty = None
        elif text:
            prev_empty = None
    safe = [i for i in empty if i not in split_src]
    print(f"空编号段落共 {len(empty)} 个（段落序号从 0 起）")
    print(f"序号/内容分段 {len(split_src)} 个，删除前必须给内容段重建编号: {split_src}")
    print(f"真空段（可删候选）{len(safe)} 个: {safe}")
    print("提醒：修改前先备份 docx，删后全章核验编号连续性。")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("用法: python3 find_empty_numbering.py <file.docx>")
    main(sys.argv[1])
