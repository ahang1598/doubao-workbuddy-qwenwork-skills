#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_to_docx.py  — 新增
统一输入格式:.doc / .docx → .docx

设计目标
--------
- 接收任意 Word 合同文件(.doc 或 .docx),统一输出 .docx 路径
- .docx 直接返回(不重打包,避免破坏修订标记)
- .doc 调用本地 libreoffice/soffice 进行无头转换
- 任何一条链路不可用时,退出码 ≠ 0,并在 stdout 输出结构化 JSON
  告知调用方降级路径(提示用户另存为 .docx 后重传)

设计约束
--------
- **审查质量优先**:.docx 文件原样返回,绝不 re-save
  (python-docx 的 Document.save 会重写 XML,可能改变修订结构)
- .doc 转换后 **必须保留原文件备份**,供用户核对
- 若原 .doc 含 Word Track Changes,转换后 LibreOffice 通常能保留,
  但无法 100% 保证 → 在输出 JSON 中显式设置 warnings 字段,
  SKILL.md Step 0.1 会把该警告转达给用户

用法
----
    python3 convert_to_docx.py <input_file> [--out-dir DIR]

退出码
------
    0   成功(结果 JSON 的 success=true)
    1   输入错误(文件不存在/扩展名不支持)
    2   转换失败(libreoffice 不可用或转换异常)

stdout JSON 结构
----------------
{
  "success": true,
  "input_path": "/abs/path/input.doc",
  "output_path": "/abs/path/input.docx",
  "original_format": "doc",
  "converted": true,
  "backup_path": "/abs/path/input_original.doc",  // 仅 .doc 转换时
  "warnings": [
    "原 .doc 文件已转换为 .docx。若原文件含 Word 修订痕迹,转换过程可能丢失部分修订标记,请用户核对。"
  ],
  "notes": "审查请基于 output_path。原文件已备份为 backup_path。"
}
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile


SUPPORTED_EXTS = (".doc", ".docx")


def is_valid_docx(path: str) -> bool:
    """轻量验证:.docx 本质是 zip,且必须包含 word/document.xml。"""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            return "word/document.xml" in names
    except (zipfile.BadZipFile, FileNotFoundError, IsADirectoryError):
        return False


def find_libreoffice() -> str | None:
    """按优先级探测 libreoffice/soffice 可执行路径。"""
    for name in ("libreoffice", "soffice"):
        path = shutil.which(name)
        if path:
            return path
    # 常见固定路径兜底
    for fixed in (
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "/opt/libreoffice/program/soffice",
    ):
        if os.path.isfile(fixed) and os.access(fixed, os.X_OK):
            return fixed
    return None


def backup_original_doc(doc_path: str) -> str:
    """备份原 .doc 为 <basename>_original.doc,避免转换后丢失源文件。"""
    base, ext = os.path.splitext(doc_path)
    backup = f"{base}_original{ext}"
    if not os.path.exists(backup):
        shutil.copy2(doc_path, backup)
    return backup


def convert_doc_with_libreoffice(doc_path: str, out_dir: str, soffice: str) -> str:
    """调用 libreoffice 无头模式转换 .doc → .docx,返回生成的 docx 路径。"""
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        soffice,
        "--headless",
        "--norestore",
        "--nolockcheck",
        "--convert-to",
        "docx",
        "--outdir",
        out_dir,
        doc_path,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("libreoffice 转换超时(>300s)")

    if proc.returncode != 0:
        raise RuntimeError(
            f"libreoffice 转换失败 rc={proc.returncode}\n"
            f"stdout: {proc.stdout[:500]}\nstderr: {proc.stderr[:500]}"
        )

    base = os.path.splitext(os.path.basename(doc_path))[0]
    out_docx = os.path.join(out_dir, f"{base}.docx")
    if not os.path.isfile(out_docx):
        raise RuntimeError(f"转换完成但未找到输出文件: {out_docx}")
    if not is_valid_docx(out_docx):
        raise RuntimeError(f"转换产物不是合法 docx: {out_docx}")
    return out_docx


def emit(result: dict, exit_code: int = 0):
    """统一输出 JSON 到 stdout 并退出。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def main():
    parser = argparse.ArgumentParser(description="统一输入格式为 .docx")
    parser.add_argument("input", help="输入合同文件 (.doc 或 .docx)")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="输出目录(默认与输入同目录)",
    )
    args = parser.parse_args()

    in_path = os.path.abspath(args.input)
    if not os.path.isfile(in_path):
        emit(
            {
                "success": False,
                "error": f"文件不存在: {in_path}",
                "suggestion": "请确认文件路径是否正确。",
            },
            exit_code=1,
        )

    ext = os.path.splitext(in_path)[1].lower()
    if ext not in SUPPORTED_EXTS:
        emit(
            {
                "success": False,
                "error": f"不支持的文件类型: {ext}",
                "suggestion": "当前仅支持 .doc 和 .docx。请将文件另存为 .docx 后重传。",
            },
            exit_code=1,
        )

    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.dirname(in_path)

    # Case A: 已是 .docx → 原样返回,不做任何修改
    if ext == ".docx":
        if not is_valid_docx(in_path):
            emit(
                {
                    "success": False,
                    "error": "文件扩展名是 .docx 但结构损坏(非合法 zip 或缺 word/document.xml)",
                    "suggestion": "请用 Word 另存为新的 .docx 文件后重传。",
                },
                exit_code=1,
            )
        emit(
            {
                "success": True,
                "input_path": in_path,
                "output_path": in_path,
                "original_format": "docx",
                "converted": False,
                "warnings": [],
                "notes": "输入已是 .docx,原样使用,未做任何修改。",
            },
            exit_code=0,
        )

    # Case B: .doc → 需要 libreoffice 转换
    soffice = find_libreoffice()
    if not soffice:
        emit(
            {
                "success": False,
                "error": "当前环境未安装 libreoffice/soffice,无法转换 .doc 文件",
                "suggestion": (
                    "降级路径:请在本地用 Word 打开该 .doc 文件,"
                    "另存为 .docx(文件 → 另存为 → 类型选 Word 文档 .docx)后重新上传。"
                ),
            },
            exit_code=2,
        )

    try:
        backup_path = backup_original_doc(in_path)
        out_docx = convert_doc_with_libreoffice(in_path, out_dir, soffice)
    except Exception as exc:
        emit(
            {
                "success": False,
                "error": f"libreoffice 转换失败: {exc}",
                "suggestion": (
                    "降级路径:请用 Word 将 .doc 另存为 .docx 后重传。"
                    "如原文件含修订痕迹,请在另存前先决定是否接受全部修订。"
                ),
            },
            exit_code=2,
        )

    emit(
        {
            "success": True,
            "input_path": in_path,
            "output_path": out_docx,
            "original_format": "doc",
            "converted": True,
            "backup_path": backup_path,
            "warnings": [
                "原 .doc 文件已转换为 .docx。若原文件含 Word 修订痕迹,"
                "libreoffice 转换通常能保留,但无法 100% 保证。"
                "请在审查摘要中提示用户核对修订标记是否完整。"
            ],
            "notes": (
                "审查请基于 output_path。原 .doc 文件已备份为 backup_path,"
                "供用户回溯核对。后续 preprocess_contract.py 请传入 output_path。"
            ),
        },
        exit_code=0,
    )


if __name__ == "__main__":
    main()
