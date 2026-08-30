#!/usr/bin/env python3
"""Scan knowledge-butler material and determine scene routing.

专为"知识管家"（knowledge-butler）定制。扫描用户知识管家根目录下的两个路径：
  - 1-素材/文稿/    作为用户原创素材（正向学习输入）
  - 1-素材/收藏/    作为外部参考素材（反向学习输入，用于禁用清单）

知识管家根目录自动识别规则：
  - 优先使用 --base 传入的路径
  - 否则从当前目录向上递归，找同时包含 `1-素材/` 和 `3-AI档案/` 的目录

Usage:
  python material_scanner.py                          # 自动识别知识管家根
  python material_scanner.py --base <kb_root_path>    # 显式传根路径
  python material_scanner.py --has-spec               # 告诉 scanner 用户已有说明书
  python material_scanner.py --user-provided          # 用户在对话中直接提供了素材

Output JSON:
  {
    "scene": "场景一：首次学习" | "场景二：内容不够" | "场景三：引导提供素材" | "场景四：持续校准",
    "reason": "...",
    "workspace_root": "/path/to/知识管家",
    "original_path": ".../1-素材/文稿",
    "original_path_exists": true,
    "original_count": 5,
    "original_files": [{"name": "...", "type": "text", "size": 1234}, ...],
    "reference_path": ".../1-素材/收藏",
    "reference_path_exists": true,
    "reference_count": 3,
    "reference_files": [...],
    "unrecognized_files": [...]
  }
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Supported file extensions and their categories
TEXT_EXTS = {".txt", ".md"}
DOC_EXTS = {".docx", ".pdf"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
ALL_VALID_EXTS = TEXT_EXTS | DOC_EXTS | IMAGE_EXTS

# Unrecognized file categories for user guidance
ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"}
BINARY_EXTS = {".exe", ".dmg", ".apk", ".app", ".iso"}


def _categorize_ext(ext: str) -> str:
    """Return file category: 'text', 'document', 'image', 'archive', 'binary', or 'unknown'."""
    ext = ext.lower()
    if ext in TEXT_EXTS:
        return "text"
    if ext in DOC_EXTS:
        return "document"
    if ext in IMAGE_EXTS:
        return "image"
    if ext in ARCHIVE_EXTS:
        return "archive"
    if ext in BINARY_EXTS:
        return "binary"
    return "unknown"


def scan_directory(dir_path: str) -> tuple[list[dict], list[dict]]:
    """Scan a directory for valid content files. Returns (valid_files, unrecognized_files)."""
    if not os.path.isdir(dir_path):
        return [], []
    valid_files = []
    unrecognized_files = []

    for fname in sorted(os.listdir(dir_path)):
        # Skip hidden and temp files
        if fname.startswith(".") or fname.startswith("~"):
            continue
        fpath = os.path.join(dir_path, fname)
        if not os.path.isfile(fpath):
            continue
        _, ext = os.path.splitext(fname)
        category = _categorize_ext(ext)

        file_info = {
            "name": fname,
            "ext": ext.lower(),
            "size": os.path.getsize(fpath),
            "path": fpath,
        }

        if category in ("archive", "binary", "unknown"):
            unrecognized_files.append({**file_info, "category": category})
            continue

        if category in ("text", "document", "image"):
            meta = {"status": "active", "tags": []}
            if ext.lower() == ".md":
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                        if first_line == "---":
                            content = f.read()
                            end_idx = content.find("---")
                            if end_idx != -1:
                                yaml_content = content[:end_idx]
                                import re
                                status_match = re.search(r"status:\s*[\"']?(\w+)[\"']?", yaml_content)
                                if status_match:
                                    meta["status"] = status_match.group(1)
                                tags_match = re.findall(r"-\s*[\"']?([\w/]+)[\"']?", yaml_content)
                                if tags_match:
                                    meta["tags"] = tags_match
                except Exception:
                    pass

            valid_files.append({
                **file_info,
                "type": category,
                "meta": meta,
            })

    return valid_files, unrecognized_files


def determine_scene(
    has_spec: bool,
    user_provided: bool,
    original_count: int,
) -> tuple[str, str]:
    """Apply the SKILL.md scene routing logic. Returns (scene, reason)."""
    # Priority 1: existing style spec
    if has_spec:
        return "场景四：持续校准", "悟空记忆中已有《风格说明书》"
    # Priority 2: user provided content in current conversation
    if user_provided:
        return "场景三：用户主动提供素材", "用户在当前对话中提供了原创内容"
    # Priority 3: scan knowledge-butler 1-素材/文稿/
    if original_count >= 3:
        return "场景一：首次学习", f"找到 {original_count} 篇原创，≥3 篇可开始学习"
    if original_count >= 1:
        return "场景二：内容不够", f"找到 {original_count} 篇原创，不足 3 篇"
    return "场景三：引导提供素材", "知识管家 1-素材/文稿/ 中无原创内容"


def find_workspace_root(start_path: str = None) -> str:
    """
    从 start_path 开始向上递归查找知识管家根目录。
    判定标准：目录下**同时存在** `1-素材/` 和 `3-AI档案/` 子目录——
    这是知识管家（knowledge-butler）的唯一结构特征。
    若未找到，返回当前目录作为兜底（后续扫描会返回空结果，走场景三引导流程）。
    """
    if not start_path:
        start_path = os.getcwd()

    current = os.path.abspath(start_path)
    while True:
        if (os.path.isdir(os.path.join(current, "1-素材")) and
            os.path.isdir(os.path.join(current, "3-AI档案"))):
            return current

        parent = os.path.dirname(current)
        if parent == current:  # 已到文件系统根
            break
        current = parent

    # 未找到：返回起始目录作为兜底
    return os.path.abspath(start_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan knowledge-butler material library and route scene"
    )
    parser.add_argument(
        "--base",
        help="Knowledge-butler root path (containing 1-素材/ and 3-AI档案/)"
    )
    parser.add_argument(
        "--has-spec",
        action="store_true",
        help="User already has a style spec in memory"
    )
    parser.add_argument(
        "--user-provided",
        action="store_true",
        help="User provided content in current conversation"
    )
    args = parser.parse_args()

    # Resolve base path
    if args.base:
        base_dir = os.path.abspath(args.base)
    else:
        base_dir = find_workspace_root()

    # 知识管家约定的两个路径
    original_dir = os.path.join(base_dir, "1-素材", "文稿")
    reference_dir = os.path.join(base_dir, "1-素材", "收藏")

    original_files, orig_unrecognized = scan_directory(original_dir)
    reference_files, ref_unrecognized = scan_directory(reference_dir)

    scene, reason = determine_scene(
        has_spec=args.has_spec,
        user_provided=args.user_provided,
        original_count=len(original_files),
    )

    result = {
        "scene": scene,
        "reason": reason,
        "workspace_root": base_dir,
        "original_path": original_dir,
        "original_path_exists": os.path.isdir(original_dir),
        "original_count": len(original_files),
        "original_files": original_files,
        "reference_path": reference_dir,
        "reference_path_exists": os.path.isdir(reference_dir),
        "reference_count": len(reference_files),
        "reference_files": reference_files,
        "unrecognized_files": orig_unrecognized + ref_unrecognized,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
