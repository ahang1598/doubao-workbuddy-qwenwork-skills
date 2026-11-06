#!/usr/bin/env python3
"""Copy a generated research report into the current task workspace."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


def deliver_file(source: Path, output_dir: Path, filename: str) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"报告文件不存在: {source}")

    safe_name = Path(filename.strip()).name
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", safe_name).strip(" .")
    safe_name = safe_name or "深度研究报告.docx"
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / safe_name
    index = 2
    while target.exists():
        target = output_dir / f"{Path(safe_name).stem} ({index}){Path(safe_name).suffix}"
        index += 1
    shutil.copy2(source, target)
    return target.resolve()
