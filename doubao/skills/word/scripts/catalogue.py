"""Update a DOCX table of contents when the document contains a TOC field."""

import argparse
import contextlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree


TOC_INSTRUCTION = re.compile(r"^\s*TOC(?:\s|\\|$)", re.IGNORECASE)
UNSUPPORTED_MESSAGE = "当前环境不支持更新目录域，跳过此步骤"


def _attribute(element: ElementTree.Element, name: str) -> str:
    return next(
        (value for key, value in element.attrib.items() if key.endswith(f"}}{name}")),
        "",
    )


def has_toc_field(filename: Path) -> bool:
    with zipfile.ZipFile(filename) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))

    fields: list[list[str]] = []
    for element in root.iter():
        name = element.tag.rsplit("}", 1)[-1]
        if name == "fldSimple" and TOC_INSTRUCTION.match(_attribute(element, "instr")):
            return True
        if name == "fldChar":
            field_type = _attribute(element, "fldCharType")
            if field_type == "begin":
                fields.append([])
            elif field_type == "end" and fields:
                if TOC_INSTRUCTION.match("".join(fields.pop())):
                    return True
        elif name == "instrText" and fields:
            fields[-1].append(element.text or "")
    return any(TOC_INSTRUCTION.match("".join(field)) for field in fields)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        dest="filename",
        type=Path,
        required=True,
        help="DOCX file to inspect and update",
    )
    args = parser.parse_args()

    if not args.filename.is_file():
        parser.error(f"文件不存在: {args.filename}")
    if args.filename.suffix.lower() != ".docx":
        parser.error("请输入一个 .docx文件")

    source = args.filename.resolve()
    if not has_toc_field(source):
        print("文件中没有 TOC 域，无需更新")
        return 0

    if shutil.which("lark-cli") is None:
        print(UNSUPPORTED_MESSAGE, file=sys.stderr)
        return 0

    with tempfile.TemporaryDirectory(prefix="catalogue-", dir=Path.home()) as directory:
        staged = Path(directory) / source.name
        shutil.copy2(source, staged)
        result = subprocess.run(
            ["lark-cli", "docs", "+word-post-process", "--file", staged.name],
            check=False,
            cwd=directory,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            print(UNSUPPORTED_MESSAGE, file=sys.stderr)
            return 0
        shutil.copy2(staged, source)
        staged.unlink()
    print("目录成功生成")
    return 0


if __name__ == "__main__":
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        raise SystemExit(main())
    print(UNSUPPORTED_MESSAGE, file=sys.stderr)
