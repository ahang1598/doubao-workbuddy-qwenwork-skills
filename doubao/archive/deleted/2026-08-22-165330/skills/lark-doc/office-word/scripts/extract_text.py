# /// script
# requires-python = ">=3.10"
# dependencies = ["python-docx"]
# ///

"""
从各种格式文件中提取纯文本。

用法：
    uv run scripts/extract_text.py 技术交底书.docx
    uv run scripts/extract_text.py 审查意见.pdf -o content.txt

支持格式：.docx、.doc、.pdf、.txt、.md、.html
    - .docx: pandoc 优先，python-docx 备选，XML 正则兜底
    - .doc:  LibreOffice 转 .docx 再提取
    - .pdf:  pdftotext 或 pandoc
    - .txt/.md: 直接读取，自动检测编码（UTF-8/GBK 等）
    - .html: pandoc 或正则去标签
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _read_docx(path: Path) -> str:
    if shutil.which("pandoc"):
        r = subprocess.run(
            ["pandoc", str(path), "-t", "plain", "--wrap=none"],
            capture_output=True, text=True
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout

    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        pass

    return _read_docx_xml_fallback(path)


def _read_docx_xml_fallback(path: Path) -> str:
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', xml)
        return "\n".join(texts)
    except Exception:
        return ""


def _read_doc(path: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        if shutil.which("soffice"):
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "docx",
                 "--outdir", tmp, str(path)],
                capture_output=True, text=True
            )
        else:
            print("错误：需要 LibreOffice 来转换 .doc 文件", file=sys.stderr)
            return ""

        docx_path = Path(tmp) / (path.stem + ".docx")
        if docx_path.exists():
            return _read_docx(docx_path)
    return ""


def _read_pdf(path: Path) -> str:
    if shutil.which("pdftotext"):
        r = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            return r.stdout
    if shutil.which("pandoc"):
        r = subprocess.run(
            ["pandoc", str(path), "-t", "plain", "--wrap=none"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            return r.stdout
    print("错误：需要 pdftotext 或 pandoc 来处理 PDF", file=sys.stderr)
    return ""


def _read_text(path: Path) -> str:
    for enc in ("utf-8", "gbk", "gb2312", "gb18030", "big5", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _read_html(path: Path) -> str:
    if shutil.which("pandoc"):
        r = subprocess.run(
            ["pandoc", str(path), "-f", "html", "-t", "plain", "--wrap=none"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            return r.stdout
    text = _read_text(path)
    if text:
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', text)).strip()
    return ""


READERS = {
    ".docx": _read_docx,
    ".doc": _read_doc,
    ".pdf": _read_pdf,
    ".txt": _read_text,
    ".md": _read_text,
    ".html": _read_html,
    ".htm": _read_html,
}


def main():
    parser = argparse.ArgumentParser(description="从各种格式文件中提取纯文本")
    parser.add_argument("input", type=Path, help="输入文件")
    parser.add_argument("-o", "--output", type=Path, help="输出文件（默认输出到终端）")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"错误：文件不存在：{args.input}", file=sys.stderr)
        sys.exit(1)

    suffix = args.input.suffix.lower()
    reader = READERS.get(suffix)
    if not reader:
        print(f"错误：不支持的格式：{suffix}", file=sys.stderr)
        print(f"支持：{', '.join(sorted(READERS.keys()))}", file=sys.stderr)
        sys.exit(1)

    text = reader(args.input)
    if not text:
        print("警告：未提取到文本内容", file=sys.stderr)

    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"已写入：{args.output}（{len(text)} 字符）", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
