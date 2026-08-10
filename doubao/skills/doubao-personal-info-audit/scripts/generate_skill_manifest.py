#!/usr/bin/env python3
"""Generate a deterministic SHA-256 manifest for a skill directory."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="生成Skill文件SHA-256清单")
    parser.add_argument("directory", help="Skill目录")
    parser.add_argument("--output", default="MANIFEST.sha256", help="清单文件名或路径")
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.is_dir():
        raise SystemExit(f"目录不存在：{root}")
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output = output.resolve()

    lines: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or path.resolve() == output:
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(root).as_posix()
        lines.append(f"{sha256(path)}  {relative}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"已生成：{output}（{len(lines)}个文件）")


if __name__ == "__main__":
    main()
