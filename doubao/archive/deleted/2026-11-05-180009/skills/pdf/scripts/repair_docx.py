"""用 libreoffice 重写 DOCX 修 wml 结构错，输出到指定文件。

原理：libreoffice 打开时宽容解析、保存时按自己的 OOXML writer 输出符合规范的 XML，
所以能修 tblStyle/tcW/tblW 等 wml 子元素顺序错、清理不识别的私有扩展。

Warning: OMML 公式结构错乱时 libreoffice 可能把公式转成图片或丢弃，公式数据会损失。
使用前请先跑 audit_docx.py（配 --xsd-validate）确认无 OMML 结构错再来 repair。
"""

import argparse
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def locate_soffice():
    choices = [
        shutil.which("soffice"),
        shutil.which("libreoffice"),
    ]
    found = [item for item in choices if item and Path(item).exists()]
    return found[0] if found else None


def repair_docx(source, output):
    """用 libreoffice 重写 DOCX 到 output 路径，源文件保持不变。"""
    source = Path(source).resolve()
    output = Path(output).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"DOCX file does not exist: {source}")
    if source.suffix.lower() != ".docx":
        raise ValueError(f"Input file must have a .docx extension: {source}")
    if output.suffix.lower() != ".docx":
        raise ValueError(f"Output file must have a .docx extension: {output}")

    soffice = locate_soffice()
    if soffice is None:
        raise RuntimeError("LibreOffice is required to repair DOCX")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        profile = tmp / "libreoffice-profile"
        profile.mkdir()
        result = subprocess.run(
            [
                soffice,
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--convert-to",
                "docx",
                "--outdir",
                str(tmp),
                str(source),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        converted = tmp / f"{source.stem}.docx"
        if result.returncode != 0 or not converted.is_file():
            # libreoffice 加载失败时详细行可能落在 stdout 或 stderr 任一流，全给出以便定位：
            # 常见根因是 (1) DOCX 坏到 libreoffice 也打不开——先跑 audit_docx.py 排查
            # XML/OPC 层错误；(2) 文件被 Word/Preview/iCloud 锁；(3) 上次 libreoffice
            # 实例遗留的 .~lock.* 文件未清；(4) 内嵌对象的相对路径含非法 URI 字符。
            parts = [
                f"returncode={result.returncode}",
                f"stdout={result.stdout.strip() or '(empty)'}",
                f"stderr={result.stderr.strip() or '(empty)'}",
                f"expected_output={converted}",
                f"outdir_contents={sorted(p.name for p in tmp.iterdir())}",
            ]
            raise RuntimeError("LibreOffice repair failed: " + " | ".join(parts))
        orig_size = source.stat().st_size
        new_size = converted.stat().st_size
        LOGGER.info(
            "repaired %s -> %s: %d bytes -> %d bytes (%.1f%%)",
            source.name, output.name, orig_size, new_size,
            new_size * 100.0 / max(orig_size, 1),
        )
        shutil.copy2(converted, output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("docx_name", help="source DOCX file")
    parser.add_argument("--output", required=True, help="target DOCX file (repaired output)")
    args = parser.parse_args()

    try:
        output = repair_docx(args.docx_name, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        LOGGER.error("%s", error)
        return 1
    print(f"Repaired DOCX written to {output}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
