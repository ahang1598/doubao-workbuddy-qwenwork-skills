#!/usr/bin/env python3
"""Copy a generated PPTX from the session temp directory to the task workspace."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


def safe_pptx_name(raw_name: str) -> str:
    """Return a Windows-safe PPTX filename without allowing directory traversal."""
    name = Path(raw_name.strip()).name
    if name.lower().endswith(".pptx"):
        name = name[:-5]
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return f"{name or '演示文稿'}.pptx"


def available_target(output_dir: Path, filename: str) -> Path:
    target = output_dir / filename
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    index = 2
    while True:
        candidate = output_dir / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def deliver(source: Path, output_dir: Path, filename: str) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"PPTX 文件不存在: {source}")
    if source.suffix.lower() != ".pptx":
        raise ValueError(f"只支持交付 .pptx 文件: {source}")

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = available_target(output_dir, safe_pptx_name(filename))
    shutil.copy2(source, target)
    return target.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="将最终 PPTX 复制到任务工作空间")
    parser.add_argument("source", help="临时目录中的最终 PPTX")
    parser.add_argument("output_dir", help="当前任务工作空间")
    parser.add_argument("filename", help="建议的交付文件名")
    args = parser.parse_args()

    target = deliver(Path(args.source), Path(args.output_dir), args.filename)
    print(str(target).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
